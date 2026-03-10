from celery import Celery
from celery.schedules import crontab
import os

from ..config import settings

# Create Celery app
celery_app = Celery(
    "ohdsi_dashboard",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks", "app.workers.content_pipeline_task"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

# Configure periodic tasks with intelligent scheduling
celery_app.conf.beat_schedule = {
    # Legacy article classifier (kept for compatibility)
    "run-article-classifier": {
        "task": "app.workers.tasks.run_article_classifier",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    
    # Comprehensive pipeline - main daily run
    "comprehensive-pipeline-daily": {
        "task": "app.workers.content_pipeline_task.run_comprehensive_pipeline",
        "schedule": crontab(hour=1, minute=0),  # Daily at 1 AM
        "kwargs": {"mode": "normal"}
    },
    
    # Source-specific incremental fetches with optimal intervals
    "pubmed-incremental": {
        "task": "app.workers.content_pipeline_task.fetch_source_incremental",
        "schedule": crontab(hour="*/24", minute=0),  # Every 24 hours
        "kwargs": {"source": "pubmed"}
    },
    
    "youtube-incremental": {
        "task": "app.workers.content_pipeline_task.fetch_source_incremental",
        "schedule": crontab(hour="*/12", minute=0),  # Every 12 hours
        "kwargs": {"source": "youtube"}
    },
    
    "github-incremental": {
        "task": "app.workers.content_pipeline_task.fetch_source_incremental",
        "schedule": crontab(hour="*/6", minute=0),  # Every 6 hours
        "kwargs": {"source": "github"}
    },
    
    "discourse-incremental": {
        "task": "app.workers.content_pipeline_task.fetch_source_incremental",
        "schedule": crontab(hour="*/4", minute=0),  # Every 4 hours
        "kwargs": {"source": "discourse"}
    },
    
    "wiki-weekly": {
        "task": "app.workers.content_pipeline_task.fetch_source_incremental",
        "schedule": crontab(day_of_week=1, hour=0, minute=0),  # Weekly on Monday
        "kwargs": {"source": "wiki"}
    },
    
    # Supplementary data fetch - twice daily
    "fetch-missing-supplementary": {
        "task": "app.workers.content_pipeline_task.fetch_missing_supplementary_data",
        "schedule": crontab(hour="*/12", minute=30),  # Twice daily at :30
    },
    
    # Schedule optimization - weekly
    "optimize-schedule": {
        "task": "app.workers.content_pipeline_task.optimize_fetch_schedule",
        "schedule": crontab(day_of_week=0, hour=0, minute=0),  # Sunday midnight
    },
    
    # Parallel burst fetch - weekly for comprehensive coverage
    "parallel-burst-fetch": {
        "task": "app.workers.content_pipeline_task.run_parallel_source_fetch",
        "schedule": crontab(day_of_week=6, hour=23, minute=0),  # Saturday 11 PM
    },
    
    # Existing tasks
    "update-trending": {
        "task": "app.workers.tasks.update_trending_content",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
    
    "cleanup-old-reviews": {
        "task": "app.workers.tasks.cleanup_old_reviews",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
    },
}