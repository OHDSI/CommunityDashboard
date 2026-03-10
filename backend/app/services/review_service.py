from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from elasticsearch import Elasticsearch

from ..config import settings
from ..schemas import ReviewItem, ReviewStats

logger = logging.getLogger(__name__)

class ReviewService:
    def __init__(self, es_client: Elasticsearch):
        self.es = es_client
        self.review_index = settings.review_index
        self.content_index = settings.content_index
    
    def get_queue(
        self,
        status: str = "pending",
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None
    ) -> List[ReviewItem]:
        """Get items from review queue with optional score filtering"""

        # Build query based on filters
        query_filters = [{"term": {"status": status}}]

        # Add source filter if specified
        if source and source != "all":
            query_filters.append({"term": {"source": source}})

        # Add score range filter if specified
        if min_score is not None or max_score is not None:
            score_range = {}
            if min_score is not None:
                score_range["gte"] = min_score
            if max_score is not None:
                score_range["lte"] = max_score
            query_filters.append({"range": {"final_score": score_range}})

        # Sort order depends on status
        # Pending: final_score (highest first) → priority → oldest first
        # Rejected/Approved: newest first only (show recent activity)
        if status == "pending":
            sort_order = [
                {"final_score": {"order": "desc"}},
                {"priority": {"order": "desc"}},
                {"submitted_date": {"order": "asc"}}
            ]
        else:
            # For rejected/approved, only sort by date (newest first)
            sort_order = [
                {"submitted_date": {"order": "desc"}}
            ]

        search_body = {
            "size": limit,
            "from": offset,
            "query": {
                "bool": {
                    "filter": query_filters
                }
            },
            "sort": sort_order
        }
        
        try:
            response = self.es.search(index=self.review_index, body=search_body)
            items = []
            for hit in response["hits"]["hits"]:
                item = hit["_source"]
                item["id"] = hit["_id"]
                # Ensure url field exists (even if empty)
                if "url" not in item:
                    item["url"] = ""
                
                # Map v3 fields with backward compatibility
                # ai_confidence replaces gpt_score
                if "ai_confidence" not in item:
                    item["ai_confidence"] = item.get("gpt_score", 0.0)
                
                # final_score replaces combined_score
                if "final_score" not in item:
                    if "combined_score" in item:
                        item["final_score"] = item["combined_score"]
                    else:
                        ml_score = item.get("ml_score", 0)
                        ai_confidence = item.get("ai_confidence", 0)
                        item["final_score"] = (ml_score + ai_confidence) / 2.0

                # quality_score defaults to 0.5 if not present
                if "quality_score" not in item:
                    item["quality_score"] = 0.5

                # ai_summary replaces gpt_reasoning
                if "ai_summary" not in item:
                    item["ai_summary"] = item.get("gpt_reasoning", "")
                
                # categories replaces predicted_categories
                if "categories" not in item:
                    item["categories"] = item.get("predicted_categories", [])

                # Map old category names to new 4-category system
                if item.get("categories"):
                    from config.ohdsi_categories import map_old_categories
                    item["categories"] = map_old_categories(item["categories"])
                
                # Keep old fields for backward compatibility in ReviewItem
                if "gpt_score" not in item:
                    item["gpt_score"] = item.get("ai_confidence", 0.0)
                if "combined_score" not in item:
                    item["combined_score"] = item.get("final_score", 0.0)
                if "gpt_reasoning" not in item:
                    item["gpt_reasoning"] = item.get("ai_summary", "")
                
                # Handle null submitted_date - use current time as fallback
                if item.get("submitted_date") is None:
                    item["submitted_date"] = datetime.now()
                elif isinstance(item["submitted_date"], str):
                    try:
                        # Parse ISO format datetime string
                        item["submitted_date"] = datetime.fromisoformat(item["submitted_date"].replace('Z', '+00:00'))
                    except:
                        item["submitted_date"] = datetime.now()
                
                items.append(ReviewItem(**item))
            return items
        except Exception as e:
            logger.error(f"Failed to get review queue: {e}")
            return []
    
    def get_stats(self) -> ReviewStats:
        """Get review queue statistics"""
        # Get pending count and avg score from review queue
        review_stats_body = {
            "size": 0,
            "query": {"term": {"status": "pending"}},
            "aggs": {
                "avg_ml_score": {
                    "avg": {"field": "ml_score"}
                }
            }
        }

        # Get today's approved from content index using approved_at
        approved_body = {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"approval_status": "approved"}},
                        {"range": {"approved_at": {"gte": "now/d"}}}
                    ]
                }
            }
        }

        # Get today's rejected from review queue using review_date
        rejected_body = {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"status": "rejected"}},
                        {"range": {"review_date": {"gte": "now/d"}}}
                    ]
                }
            }
        }

        try:
            review_response = self.es.search(index=self.review_index, body=review_stats_body)
            pending_count = review_response["hits"]["total"]["value"]
            avg_score = review_response["aggregations"]["avg_ml_score"]["value"] or 0.0

            approved_response = self.es.search(index=self.content_index, body=approved_body)
            approved_today = approved_response["hits"]["total"]["value"]

            rejected_response = self.es.search(index=self.review_index, body=rejected_body)
            rejected_today = rejected_response["hits"]["total"]["value"]

            return ReviewStats(
                pending=pending_count,
                approved_today=approved_today,
                rejected_today=rejected_today,
                avg_ml_score=avg_score
            )
        except Exception as e:
            logger.error(f"Failed to get review stats: {e}")
            return ReviewStats(pending=0, approved_today=0, rejected_today=0, avg_ml_score=0.0)
    
    async def approve_content(
        self,
        item_id: str,
        categories: List[str],
        reviewer_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """Approve content and move to main index"""
        logger.info(f"Attempting to approve content {item_id} with categories {categories}")
        try:
            # Get the FULL item from review queue to preserve all data
            item_response = self.es.get(index=self.review_index, id=item_id)
            review_doc = item_response["_source"]
            
            # CRITICAL: Start with the complete document to preserve ALL fields
            # including citations with enriched metadata, embeddings, AI fields, etc.
            content = review_doc.copy()
            
            # Calculate correct final score using v3 fields
            ml_score = content.get("ml_score", 0)
            ai_confidence = content.get("ai_confidence", content.get("gpt_score", 0))
            final_score = (ml_score + ai_confidence) / 2.0
            
            # Update approval-specific fields using v3 schema
            content.update({
                "approval_status": "approved",
                "categories": categories,  # v3: consolidated categories field
                "approved_at": datetime.now().isoformat(),
                "approved_by": reviewer_id,
                "review_notes": notes,
                "ai_confidence": ai_confidence,  # v3: replaces gpt_score
                "final_score": final_score,  # v3: replaces combined_score
                "updated_at": datetime.now().isoformat()
            })
            
            # Remove review-queue-specific fields that shouldn't be in content index
            review_only_fields = [
                'status',           # Review status (pending/approved/rejected)
                'priority',         # Priority score
                'priority_level',   # Priority level (high/medium/low)
                'submitted_date',   # When submitted to review
                'reviewed_date',    # When reviewed
                'reviewer_id',      # Redundant with approved_by
                'rejection_reason'  # Only for rejected items
            ]
            
            for field in review_only_fields:
                content.pop(field, None)
            
            # Ensure required fields for content index
            if 'view_count' not in content:
                content['view_count'] = 0
            if 'bookmark_count' not in content:
                content['bookmark_count'] = 0
            if 'share_count' not in content:
                content['share_count'] = 0
            
            # Add suggest field for search if title exists
            if content.get('title'):
                content['suggest'] = {'input': content['title']}
            
            # IMPORTANT: At this point, content has ALL original fields including:
            # - citations (with full enriched metadata structure)
            # - embeddings (if they were generated)
            # - AI enhancement fields
            # - All source-specific fields (video_id, repo_name, etc.)
            # - Relationships
            # - Any other fields from the original document
            
            # Index the COMPLETE document in main content index
            self.es.index(index=self.content_index, id=item_id, body=content)
            
            # Update review queue item
            self.es.update(
                index=self.review_index,
                id=item_id,
                body={
                    "doc": {
                        "status": "approved",
                        "reviewer_id": reviewer_id,
                        "review_date": datetime.now().isoformat(),
                        "review_notes": notes
                    }
                }
            )
            
            logger.info(f"Successfully approved content {item_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to approve content {item_id}: {e}", exc_info=True)
            return False
    
    async def reject_content(
        self,
        item_id: str,
        reason: str,
        reviewer_id: str
    ) -> bool:
        """Reject content with reason"""
        logger.info(f"Attempting to reject content {item_id} with reason: {reason}")
        try:
            # Update review queue item
            self.es.update(
                index=self.review_index,
                id=item_id,
                body={
                    "doc": {
                        "status": "rejected",
                        "reviewer_id": reviewer_id,
                        "review_date": datetime.now().isoformat(),
                        "review_notes": reason
                    }
                }
            )
            
            logger.info(f"Successfully rejected content {item_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to reject content {item_id}: {e}", exc_info=True)
            return False
    
    async def move_to_pending(
        self,
        item_id: str,
        reviewer_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """Move an approved or rejected item back to pending status"""
        try:
            # Check if item exists in review queue
            if self.es.exists(index=self.review_index, id=item_id):
                # Update review queue item
                self.es.update(
                    index=self.review_index,
                    id=item_id,
                    body={
                        "doc": {
                            "status": "pending",
                            "reviewer_id": reviewer_id,
                            "review_date": datetime.now().isoformat(),
                            "review_notes": notes or "Moved back to pending for re-review"
                        }
                    }
                )
                
                # If item was approved, remove from content index
                if self.es.exists(index=self.content_index, id=item_id):
                    self.es.delete(index=self.content_index, id=item_id)
                
                return True
            else:
                # If not in review queue, check if it's in content index (was approved)
                if self.es.exists(index=self.content_index, id=item_id):
                    # Get the content
                    content_response = self.es.get(index=self.content_index, id=item_id)
                    content = content_response["_source"]
                    
                    # Create review queue item
                    review_item = {
                        "title": content["title"],
                        "abstract": content.get("abstract"),
                        "content_type": content["content_type"],
                        "source": content.get("source"),  # Preserve source field
                        "display_type": content.get("display_type"),  # Preserve display metadata
                        "icon_type": content.get("icon_type"),
                        "content_category": content.get("content_category"),
                        "url": content.get("url"),
                        "ml_score": content.get("ml_score", 0.5),
                        "gpt_score": content.get("gpt_score", 0),
                        "combined_score": content.get("combined_score", content.get("ml_score", 0.5)),
                        "predicted_categories": content.get("predicted_categories", content.get("ohdsi_categories", [])),
                        "gpt_reasoning": content.get("gpt_reasoning", ""),
                        "status": "pending",
                        "submitted_date": content.get("published_date", datetime.now().isoformat()),
                        "priority": 5,
                        "authors": content.get("authors", []),
                        "journal": content.get("journal"),
                        "doi": content.get("doi"),
                        "keywords": content.get("keywords", []),
                        "year": content.get("year")
                    }
                    
                    # Index in review queue
                    self.es.index(index=self.review_index, id=item_id, body=review_item)
                    
                    # Remove from content index
                    self.es.delete(index=self.content_index, id=item_id)
                    
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"Failed to move content {item_id} to pending: {e}")
            return False
    
    async def bulk_action(
        self,
        item_ids: List[str],
        action: str,
        reviewer_id: str,
        categories: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """Perform bulk approve/reject actions"""
        results = {"success": [], "failed": []}
        
        for item_id in item_ids:
            try:
                if action == "approve" and categories:
                    success = await self.approve_content(
                        item_id, categories, reviewer_id, notes
                    )
                elif action == "reject":
                    success = await self.reject_content(
                        item_id, notes or "Bulk rejection", reviewer_id
                    )
                else:
                    success = False
                
                if success:
                    results["success"].append(item_id)
                else:
                    results["failed"].append(item_id)
            except Exception as e:
                logger.error(f"Bulk action failed for {item_id}: {e}")
                results["failed"].append(item_id)
        
        return results