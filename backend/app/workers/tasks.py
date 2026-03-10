from celery import shared_task
from datetime import datetime, timedelta
import logging
import json
import sys
import os

# Add jobs directory to path for ArticleClassifier import
sys.path.insert(0, "/app/jobs")

from ..database import es_client, redis_client
from ..config import settings

logger = logging.getLogger(__name__)

@shared_task
def run_article_classifier():
    """Run ArticleClassifier to fetch and classify new articles"""
    try:
        # Import ArticleClassifier wrapper
        from article_classifier.wrapper import ArticleClassifierWrapper
        
        # Use V2 classifier by default with environment override
        use_v2 = os.getenv('USE_V2_CLASSIFIER', 'true').lower() == 'true'
        auto_approve_threshold = float(os.getenv('AUTO_APPROVE_THRESHOLD', '0.85'))
        approval_mode = os.getenv('APPROVAL_MODE', 'combined')
        
        wrapper = ArticleClassifierWrapper(
            es_client=es_client,
            threshold=settings.classifier_threshold,
            auto_approve_threshold=auto_approve_threshold,
            approval_mode=approval_mode,
        )
        
        # Run daily fetch and classification
        results = wrapper.run_daily_fetch()
        
        logger.info(f"ArticleClassifier completed (V2={use_v2}): {results}")
        return results
    except Exception as e:
        logger.error(f"ArticleClassifier failed: {e}")
        raise

@shared_task
def update_trending_content():
    """Update trending content cache"""
    try:
        # Calculate trending scores based on recent activity
        query = {
            "size": 50,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"approval_status": "approved"}},
                        {"range": {"published_date": {"gte": "now-7d"}}}
                    ]
                }
            },
            "sort": [
                {"view_count": {"order": "desc"}},
                {"bookmark_count": {"order": "desc"}}
            ]
        }
        
        response = es_client.search(index=settings.content_index, body=query)
        
        # Cache results in Redis
        trending_items = []
        for hit in response["hits"]["hits"]:
            item = {
                "id": hit["_id"],
                "title": hit["_source"]["title"],
                "score": hit["_source"].get("view_count", 0) + 
                        (hit["_source"].get("bookmark_count", 0) * 2)
            }
            trending_items.append(item)
        
        # Store in Redis with expiration
        redis_client.setex(
            "trending:week",
            3600,  # 1 hour expiration
            json.dumps(trending_items)
        )
        
        logger.info(f"Updated trending content: {len(trending_items)} items")
        return len(trending_items)
    except Exception as e:
        logger.error(f"Failed to update trending content: {e}")
        raise

@shared_task
def cleanup_old_reviews():
    """Clean up old rejected reviews"""
    try:
        # Delete rejected reviews older than 30 days
        cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
        
        query = {
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"status": "rejected"}},
                        {"range": {"review_date": {"lt": cutoff_date}}}
                    ]
                }
            }
        }
        
        response = es_client.delete_by_query(
            index=settings.review_index,
            body=query
        )
        
        deleted_count = response.get("deleted", 0)
        logger.info(f"Cleaned up {deleted_count} old rejected reviews")
        return deleted_count
    except Exception as e:
        logger.error(f"Failed to cleanup old reviews: {e}")
        raise

@shared_task
def process_content_batch(content_ids: list):
    """Process a batch of content for ML scoring"""
    try:
        processed = 0
        for content_id in content_ids:
            # Fetch content
            doc = es_client.get(index=settings.review_index, id=content_id)
            content = doc["_source"]
            
            # Here you would run ML scoring
            # For now, using a placeholder score
            ml_score = 0.75  # Placeholder
            
            # Update with ML score
            es_client.update(
                index=settings.review_index,
                id=content_id,
                body={
                    "doc": {
                        "ml_score": ml_score,
                        "predicted_categories": ["Observational data standards and management"]  # Placeholder
                    }
                }
            )
            processed += 1
        
        logger.info(f"Processed {processed} content items")
        return processed
    except Exception as e:
        logger.error(f"Failed to process content batch: {e}")
        raise

@shared_task
def increment_view_count(content_id: str):
    """Increment view count for content"""
    try:
        es_client.update(
            index=settings.content_index,
            id=content_id,
            body={
                "script": {
                    "source": "ctx._source.view_count += 1",
                    "lang": "painless"
                }
            }
        )
        return True
    except Exception as e:
        logger.error(f"Failed to increment view count for {content_id}: {e}")
        return False