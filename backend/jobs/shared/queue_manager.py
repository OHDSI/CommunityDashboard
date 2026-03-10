"""
Queue manager for routing content to appropriate queues based on classification scores.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Manages content routing to approval queue or auto-approval based on scores.
    """
    
    def __init__(self, 
                 es_client: Elasticsearch,
                 auto_approve_threshold: float = 0.7,
                 priority_threshold: float = 0.5):
        """
        Initialize queue manager.
        
        Args:
            es_client: Elasticsearch client
            auto_approve_threshold: Score threshold for auto-approval
            priority_threshold: Score threshold for high priority review
        """
        self.es_client = es_client
        self.auto_approve_threshold = auto_approve_threshold
        self.priority_threshold = priority_threshold

        # Initialize sentence transformer for embeddings
        try:
            self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Sentence transformer initialized for embeddings")
        except Exception as e:
            logger.warning(f"Failed to initialize sentence transformer: {e}")
            self.encoder = None

        # Track statistics
        self.stats = {
            'total_processed': 0,
            'auto_approved': 0,
            'high_priority': 0,
            'low_priority': 0,
            'rejected': 0,
            'by_type': {}
        }
    
    def route_content(self, content: Dict[str, Any], 
                     classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route content based on classification scores.
        
        Args:
            content: Normalized content
            classification: Classification results
            
        Returns:
            Routing result with destination and status
        """
        content_type = content.get('content_type', 'article')
        final_score = classification.get('final_score', classification.get('combined_probability', 0))
        
        # Determine routing
        if final_score >= self.auto_approve_threshold:
            result = self._auto_approve(content, classification)
            destination = 'approved'
        elif final_score >= self.priority_threshold:
            result = self._queue_for_review(content, classification, priority='high')
            destination = 'review_high'
        elif final_score >= 0.3:  # Very low scores might be rejected
            result = self._queue_for_review(content, classification, priority='low')
            destination = 'review_low'
        else:
            result = self._reject(content, classification)
            destination = 'rejected'
        
        # Update statistics
        self.stats['total_processed'] += 1
        self.stats['by_type'][content_type] = self.stats['by_type'].get(content_type, 0) + 1
        
        if destination == 'approved':
            self.stats['auto_approved'] += 1
        elif destination == 'review_high':
            self.stats['high_priority'] += 1
        elif destination == 'review_low':
            self.stats['low_priority'] += 1
        elif destination == 'rejected':
            self.stats['rejected'] += 1
        
        return {
            'destination': destination,
            'status': result.get('status'),
            'index': result.get('index'),
            'doc_id': result.get('doc_id'),
            'message': result.get('message')
        }
    
    def _auto_approve(self, content: Dict[str, Any], 
                     classification: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-approve high-scoring content."""
        try:
            # Prepare document for main content index
            doc = self._prepare_approved_document(content, classification)
            
            # Index to main content index
            response = self.es_client.index(
                index="ohdsi_content_v3",
                id=doc["id"],
                body=doc
            )
            
            logger.info(f"Auto-approved: {doc['title'][:50]}... (score: {doc['final_score']:.3f})")
            
            return {
                'status': 'approved',
                'index': 'ohdsi_content',
                'doc_id': doc['id'],
                'message': f"Auto-approved with score {doc['final_score']:.3f}"
            }
            
        except Exception as e:
            logger.error(f"Failed to auto-approve content: {e}")
            # Fall back to review queue
            return self._queue_for_review(content, classification, priority='high')
    
    def _queue_for_review(self, content: Dict[str, Any], 
                         classification: Dict[str, Any],
                         priority: str = 'medium') -> Dict[str, Any]:
        """Queue content for manual review."""
        try:
            # Prepare document for review queue
            doc = self._prepare_review_document(content, classification, priority)
            
            # Index to review queue
            response = self.es_client.index(
                index="ohdsi_review_queue_v3",
                id=doc["id"],
                body=doc
            )
            
            logger.info(
                f"Queued for review ({priority}): {doc['title'][:50]}... "
                f"(score: {doc['final_score']:.3f})"
            )
            
            return {
                'status': 'pending',
                'index': 'review_queue',
                'doc_id': doc['id'],
                'message': f"Queued for {priority} priority review with score {doc['final_score']:.3f}"
            }
            
        except Exception as e:
            logger.error(f"Failed to queue content for review: {e}")
            raise
    
    def _reject(self, content: Dict[str, Any], 
               classification: Dict[str, Any]) -> Dict[str, Any]:
        """Reject very low scoring content and store in review queue."""
        try:
            # Prepare document for review queue with rejected status
            doc = self._prepare_review_document(content, classification, priority='rejected')
            doc['status'] = 'rejected'
            doc['review_date'] = datetime.now().isoformat()
            doc['review_notes'] = f"Auto-rejected with score {classification.get('final_score', 0):.3f}"
            
            # Index to review queue
            response = self.es_client.index(
                index="ohdsi_review_queue_v3",
                id=doc["id"],
                body=doc
            )
            
            logger.info(
                f"Rejected: {content.get('title', 'Unknown')[:50]}... "
                f"(score: {classification.get('final_score', 0):.3f})"
            )
            
            return {
                'status': 'rejected',
                'index': 'ohdsi_review_queue_v3',
                'doc_id': doc['id'],
                'message': f"Rejected with score {classification.get('final_score', 0):.3f}"
            }
        except Exception as e:
            logger.error(f"Failed to index rejected content: {e}")
            return {
                'status': 'error',
                'index': None,
                'doc_id': None,
                'message': f"Failed to reject: {e}"
            }
    
    def _generate_embedding(self, content: Dict[str, Any]) -> Optional[List[float]]:
        """Generate embedding for content."""
        if not self.encoder:
            return None

        try:
            # Combine title and abstract for embedding
            text = content.get("title", "")
            if content.get("abstract"):
                text += " " + content["abstract"][:500]  # Limit abstract length

            if not text.strip():
                return None

            # Generate and return embedding as list
            embedding = self.encoder.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def _prepare_approved_document(self, content: Dict[str, Any],
                                  classification: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare document for the main content index."""
        doc = content.copy()
        
        # Add classification results using v3 field names
        doc.update({
            'ml_score': classification.get('ml_probability', 0),
            'ai_confidence': classification.get('gpt_probability', classification.get('ai_confidence', 0)),
            'final_score': classification.get('final_score', classification.get('combined_probability', 0)),
            'categories': classification.get('categories', classification.get('predicted_categories', [])),
            'ai_summary': classification.get('ai_summary', classification.get('gpt_reasoning', '')),
            'approval_status': 'approved',
            'approved_at': datetime.now().isoformat(),
            'approved_by': 'auto',
            'created_at': content.get('created_at', datetime.now().isoformat()),
            'updated_at': datetime.now().isoformat()
        })
        
        # Add metrics if not present
        if 'view_count' not in doc:
            doc['view_count'] = 0
        if 'bookmark_count' not in doc:
            doc['bookmark_count'] = 0
        if 'share_count' not in doc:
            doc['share_count'] = 0

        # Generate embedding for semantic search
        embedding = self._generate_embedding(content)
        if embedding:
            doc["embedding"] = embedding

        # Ensure ID is string
        doc['id'] = str(doc.get('id', doc.get('source_id', '')))
        
        # Add search suggest field for title
        if doc.get('title'):
            doc['suggest'] = {'input': doc['title']}
        
        return doc
    
    def _prepare_review_document(self, content: Dict[str, Any], 
                                classification: Dict[str, Any],
                                priority: str) -> Dict[str, Any]:
        """
        Prepare document for the review queue.
        IMPORTANT: Keep the full document including citations to prevent data loss.
        """
        # Keep the complete document with all fields
        doc = content.copy()
        
        # Add classification results using v3 field names
        doc.update({
            'ml_score': classification.get('ml_probability', 0),
            'ai_confidence': classification.get('gpt_probability', classification.get('ai_confidence', 0)),
            'final_score': classification.get('final_score', classification.get('combined_probability', 0)),
            'categories': classification.get('categories', classification.get('predicted_categories', [])),
            'ai_summary': classification.get('ai_summary', classification.get('gpt_reasoning', '')),
            'status': 'pending',
            'priority': self._calculate_priority_score(priority, classification),
            'priority_level': priority,
            'submitted_date': datetime.now().isoformat(),
            'created_at': content.get('created_at', datetime.now().isoformat()),
            'updated_at': datetime.now().isoformat()
        })
        
        # Ensure ID is string
        doc['id'] = str(doc.get('id', doc.get('source_id', '')))
        
        # IMPORTANT: Keep citations and all other fields intact
        # This ensures no data is lost when content moves from review to approved
        
        return doc
    
    def _calculate_priority_score(self, priority: str, 
                                 classification: Dict[str, Any]) -> int:
        """
        Calculate numeric priority score for sorting.
        Higher score = higher priority.
        Returns value between 0-10 to match ReviewItem schema.
        """
        base_scores = {
            'high': 7,
            'medium': 5,
            'low': 3
        }
        
        base_score = base_scores.get(priority, 5)
        
        # Adjust based on actual score (add up to 3 points)
        final_score = classification.get('final_score', 0)
        score_bonus = min(3, int(final_score * 3))
        
        # Ensure result is within 0-10 range
        return min(10, base_score + score_bonus)
    
    def batch_route(self, contents: List[Dict[str, Any]], 
                   classifications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Route multiple content items in batch.
        
        Args:
            contents: List of normalized content
            classifications: List of classification results
            
        Returns:
            List of routing results
        """
        results = []
        
        for content, classification in zip(contents, classifications):
            try:
                result = self.route_content(content, classification)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to route content {content.get('id')}: {e}")
                results.append({
                    'destination': 'error',
                    'status': 'error',
                    'message': str(e)
                })
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue manager statistics."""
        total = self.stats['total_processed']
        if total > 0:
            return {
                **self.stats,
                'approval_rate': self.stats['auto_approved'] / total,
                'high_priority_rate': self.stats['high_priority'] / total,
                'rejection_rate': self.stats['rejected'] / total
            }
        return self.stats
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            'total_processed': 0,
            'auto_approved': 0,
            'high_priority': 0,
            'low_priority': 0,
            'rejected': 0,
            'by_type': {}
        }