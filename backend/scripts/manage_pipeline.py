#!/usr/bin/env python3
"""
Manage the OHDSI article classification pipeline.
Check status, trigger runs, view history.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import json

# Setup paths
sys.path.insert(0, '/app')

from celery import Celery
from app.workers.celery_app import celery_app
from app.database import es_client, redis_client
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def trigger_pipeline():
    """Manually trigger the article classification pipeline."""
    logger.info("Triggering article classification pipeline...")
    
    try:
        # Trigger the task
        result = celery_app.send_task('app.workers.tasks.run_article_classifier')
        
        logger.info(f"Pipeline triggered successfully! Task ID: {result.id}")
        logger.info("Use 'check_status' to monitor progress")
        
        # Store trigger info in Redis
        redis_client.setex(
            f"pipeline:last_manual_trigger",
            86400,  # 24 hours
            json.dumps({
                "task_id": result.id,
                "triggered_at": datetime.now().isoformat(),
                "triggered_by": "manual"
            })
        )
        
        return result.id
    except Exception as e:
        logger.error(f"Failed to trigger pipeline: {e}")
        return None


def check_status():
    """Check the current status of the pipeline."""
    logger.info("Checking pipeline status...")
    
    try:
        # Check last manual trigger
        manual_trigger = redis_client.get("pipeline:last_manual_trigger")
        if manual_trigger:
            trigger_info = json.loads(manual_trigger)
            logger.info(f"Last manual trigger: {trigger_info['triggered_at']}")
            
            # Check task status
            result = celery_app.AsyncResult(trigger_info['task_id'])
            logger.info(f"Task ID: {trigger_info['task_id']}")
            logger.info(f"Status: {result.status}")
            
            if result.ready():
                if result.successful():
                    logger.info(f"Result: {result.result}")
                else:
                    logger.error(f"Task failed: {result.info}")
        
        # Check scheduled runs from Elasticsearch
        logger.info("\nRecent pipeline runs:")
        
        # Query for recent pipeline metadata
        query = {
            "size": 5,
            "query": {
                "term": {"type": "pipeline_run"}
            },
            "sort": [{"timestamp": {"order": "desc"}}]
        }
        
        try:
            response = es_client.search(index="pipeline_metadata", body=query)
            
            for hit in response['hits']['hits']:
                doc = hit['_source']
                logger.info(f"  - {doc['timestamp']}: Fetched={doc.get('fetched', 0)}, "
                          f"Approved={doc.get('approved', 0)}, Queued={doc.get('queued', 0)}")
        except:
            logger.info("  No metadata index found (will be created on first run)")
        
        # Check Celery Beat schedule
        logger.info("\nScheduled tasks (from Celery Beat):")
        logger.info("  - run_article_classifier: Daily at 2:00 AM UTC")
        logger.info("  - update_trending_content: Every 30 minutes")
        logger.info("  - cleanup_old_reviews: Daily at 3:00 AM UTC")
        
    except Exception as e:
        logger.error(f"Failed to check status: {e}")


def view_queue_stats():
    """View statistics about the review queue."""
    logger.info("Fetching review queue statistics...")
    
    try:
        # Count pending items
        pending_query = {
            "size": 0,
            "query": {"term": {"status": "pending"}},
            "aggs": {
                "avg_score": {"avg": {"field": "ml_score"}},
                "score_ranges": {
                    "range": {
                        "field": "ml_score",
                        "ranges": [
                            {"from": 0, "to": 0.5, "key": "low"},
                            {"from": 0.5, "to": 0.8, "key": "medium"},
                            {"from": 0.8, "to": 1.0, "key": "high"}
                        ]
                    }
                }
            }
        }
        
        response = es_client.search(index=settings.review_index, body=pending_query)
        
        total_pending = response['hits']['total']['value']
        avg_score = response['aggregations']['avg_score']['value'] or 0
        score_ranges = {
            bucket['key']: bucket['doc_count'] 
            for bucket in response['aggregations']['score_ranges']['buckets']
        }
        
        logger.info(f"\nReview Queue Statistics:")
        logger.info(f"  Total Pending: {total_pending}")
        logger.info(f"  Average ML Score: {avg_score:.3f}")
        logger.info(f"  Score Distribution:")
        logger.info(f"    - High (0.8-1.0): {score_ranges.get('high', 0)}")
        logger.info(f"    - Medium (0.5-0.8): {score_ranges.get('medium', 0)}")
        logger.info(f"    - Low (0-0.5): {score_ranges.get('low', 0)}")
        
        # Count approved today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
        approved_query = {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"approval_status": "approved"}},
                        {"range": {"created_at": {"gte": today_start}}}
                    ]
                }
            }
        }
        
        approved_response = es_client.search(index=settings.content_index, body=approved_query)
        approved_today = approved_response['hits']['total']['value']
        
        logger.info(f"\n  Approved Today: {approved_today}")
        
        # Show recent high-confidence items
        high_conf_query = {
            "size": 5,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"status": "pending"}},
                        {"range": {"ml_score": {"gte": 0.8}}}
                    ]
                }
            },
            "sort": [{"ml_score": {"order": "desc"}}]
        }
        
        high_conf_response = es_client.search(index=settings.review_index, body=high_conf_query)
        
        if high_conf_response['hits']['total']['value'] > 0:
            logger.info(f"\n  High Confidence Items Ready for Review:")
            for hit in high_conf_response['hits']['hits']:
                doc = hit['_source']
                logger.info(f"    - [{doc['ml_score']:.3f}] {doc['title'][:60]}...")
        
    except Exception as e:
        logger.error(f"Failed to fetch queue stats: {e}")


def test_fetch():
    """Test article fetching with a small batch."""
    logger.info("Testing article fetch with small batch...")
    
    try:
        sys.path.insert(0, '/app/jobs')
        from article_classifier.wrapper import ArticleClassifierWrapper
        
        wrapper = ArticleClassifierWrapper(
            es_client=es_client,
            threshold=settings.classifier_threshold
        )
        
        # Fetch just a few articles for testing
        results = wrapper.fetch_and_classify_articles(
            query='OHDSI OR "OMOP CDM"',
            max_results=5,
            days_back=7
        )
        
        logger.info(f"\nTest Results:")
        logger.info(f"  Fetched: {results['fetched']}")
        logger.info(f"  Classified: {results['classified']}")
        logger.info(f"  Positive (OHDSI-related): {results['positive']}")
        logger.info(f"  Queued for review: {results['queued']}")
        logger.info(f"  Auto-approved: {results.get('auto_approved', 0)}")
        
    except Exception as e:
        logger.error(f"Test fetch failed: {e}")


def main():
    """Main CLI interface."""
    commands = {
        'trigger': trigger_pipeline,
        'status': check_status,
        'stats': view_queue_stats,
        'test': test_fetch
    }
    
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print("OHDSI Pipeline Manager")
        print("=" * 50)
        print("\nUsage: python manage_pipeline.py <command>")
        print("\nCommands:")
        print("  trigger  - Manually trigger the article classification pipeline")
        print("  status   - Check pipeline status and recent runs")
        print("  stats    - View review queue statistics")
        print("  test     - Test article fetching with a small batch")
        print("\nScheduled Runs:")
        print("  The pipeline runs automatically every day at 2:00 AM UTC")
        print("  Use 'trigger' to run it manually at any time")
        sys.exit(1)
    
    command = sys.argv[1]
    commands[command]()


if __name__ == "__main__":
    main()