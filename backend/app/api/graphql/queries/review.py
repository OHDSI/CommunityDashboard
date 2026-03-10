"""
Review query resolvers.

Handles review_queue and get_queue_stats queries.
"""
import logging
from datetime import datetime
from typing import Optional, List
from strawberry.types import Info

from ..types.review import ClassificationFactor, ReviewItem, QueueStats
from ..services import review_service
from ....config import settings
from ....database import es_client

try:
    import sys
    sys.path.append('/app')
    from config.ohdsi_categories import map_old_categories as _map_old_cats
except ImportError:
    def _map_old_cats(cats):
        return cats

logger = logging.getLogger(__name__)


async def resolve_review_queue(
    info: Info,
    status: str = "pending",
    source: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None
) -> List[ReviewItem]:
    """Get review queue (requires auth) with optional score filtering"""
    # Note: In production, implement proper auth check here

    # For approved items, search in the main content index
    if status == "approved":
        try:
            # Build filter list
            filters = [
                {"term": {"approval_status": "approved"}}
            ]

            # Add source filter if specified
            if source and source != "all":
                filters.append({"term": {"source": source}})

            query = {
                "size": 100,
                "query": {
                    "bool": {
                        "filter": filters
                    }
                },
                "sort": [
                    {"approved_at": {"order": "desc", "missing": "_last"}},
                    {"created_at": {"order": "desc"}}
                ]
            }

            response = es_client.search(index=settings.content_index, body=query)

            items = []
            for hit in response["hits"]["hits"]:
                doc = hit["_source"]
                # Ensure ml_score is never None
                ml_score = doc.get("ml_score")
                if ml_score is None:
                    ml_score = 0.0

                items.append(ReviewItem(
                    id=hit["_id"],
                    title=doc.get("title", ""),
                    abstract=doc.get("abstract"),
                    content_type=doc.get("content_type", "article"),
                    source=doc.get("source"),
                    display_type=doc.get("display_type"),
                    icon_type=doc.get("icon_type"),
                    content_category=doc.get("content_category"),
                    url=doc.get("url", ""),
                    ml_score=float(ml_score),
                    ai_confidence=doc.get("ai_confidence", doc.get("gpt_score", 0)),  # Map old field to new
                    final_score=doc.get("final_score", doc.get("combined_score", ml_score)),  # Map old field to new
                    quality_score=doc.get("quality_score", 0.5),  # Quality score for transparency
                    categories=_map_old_cats(doc.get("categories", doc.get("ohdsi_categories", []))),
                    classification_factors=[
                        ClassificationFactor(
                            feature=f.get("feature", ""),
                            value=float(f.get("value", 0.0)),
                            contribution=float(f.get("contribution", 0.0))
                        )
                        for f in doc.get("classification_factors", [])
                        if isinstance(f, dict) and "feature" in f
                    ],
                    ai_summary=doc.get("ai_summary", doc.get("gpt_reasoning", "")),  # Map old field to new
                    status=status,
                    submitted_date=datetime.fromisoformat(doc.get("approved_at", doc.get("created_at", datetime.now().isoformat()))),
                    priority=5
                ))
            return items
        except Exception as e:
            logger.error(f"Failed to fetch approved items: {e}")
            return []
    else:
        # For pending and rejected items, use the review service
        items = review_service.get_queue(
            status,
            source=source,
            min_score=min_score,
            max_score=max_score
        )

        return [
            ReviewItem(
                id=item.id,
                title=item.title,
                abstract=item.abstract,
                content_type=item.content_type,
                source=getattr(item, 'source', None),
                display_type=getattr(item, 'display_type', None),
                icon_type=getattr(item, 'icon_type', None),
                content_category=getattr(item, 'content_category', None),
                url=item.url,
                ml_score=item.ml_score,
                ai_confidence=getattr(item, 'ai_confidence', getattr(item, 'gpt_score', 0.0)),
                final_score=getattr(item, 'final_score', getattr(item, 'combined_score', item.ml_score)),
                quality_score=getattr(item, 'quality_score', 0.5),  # Quality score for transparency
                categories=_map_old_cats(getattr(item, 'categories', getattr(item, 'predicted_categories', []))),
                classification_factors=[
                    ClassificationFactor(
                        feature=f.get("feature", ""),
                        value=float(f.get("value", 0.0)),
                        contribution=float(f.get("contribution", 0.0))
                    )
                    for f in getattr(item, 'classification_factors', [])
                    if isinstance(f, dict) and "feature" in f
                ],
                ai_summary=getattr(item, 'ai_summary', getattr(item, 'gpt_reasoning', '')),  # Map old field to new
                status=item.status,
                submitted_date=item.submitted_date,
                priority=item.priority
            )
            for item in items
        ]


async def resolve_get_queue_stats() -> QueueStats:
    """Get review queue statistics"""

    # Count pending items in review queue with stats
    pending_query = {
        "size": 0,
        "query": {"term": {"status": "pending"}},
        "aggs": {
            "avg_score": {"avg": {"field": "final_score"}},
            "high_conf": {
                "filter": {"range": {"final_score": {"gte": 0.8}}}
            },
            "low_conf": {
                "filter": {"range": {"final_score": {"lt": 0.5}}}
            }
        }
    }
    pending_response = es_client.search(index=settings.review_index, body=pending_query)
    pending_count = pending_response["hits"]["total"]["value"]
    avg_score = pending_response['aggregations']['avg_score']['value'] or 0.0
    high_conf = pending_response['aggregations']['high_conf']['doc_count']
    low_conf = pending_response['aggregations']['low_conf']['doc_count']

    # Count approved today (auto + manual) from content index using approved_at
    approved_query = {
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
    approved_response = es_client.search(index=settings.content_index, body=approved_query)
    approved_count = approved_response["hits"]["total"]["value"]

    # Count rejected today (auto + manual) from review queue using review_date
    rejected_query = {
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
        rejected_response = es_client.search(index=settings.review_index, body=rejected_query)
        rejected_count = rejected_response["hits"]["total"]["value"]
    except Exception:
        rejected_count = 0

    return QueueStats(
        pending=pending_count,
        approved=approved_count,
        rejected=rejected_count,
        avgScore=avg_score,
        highConfidence=high_conf,
        lowConfidence=low_conf
    )
