"""
API endpoints for content pipeline management.
Provides manual triggers and monitoring for scheduled tasks.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import logging

from ...database import es_client, redis_client
from ...config import settings
from ...utils.auth import AuthService
from ...models.user import User
from app.workers.content_pipeline_task import (
    run_comprehensive_pipeline,
    fetch_source_incremental,
    fetch_missing_supplementary_data,
    optimize_fetch_schedule,
    run_parallel_source_fetch,
    IntelligentScheduler
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/trigger/comprehensive")
async def trigger_comprehensive_pipeline(
    mode: str = "normal",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(AuthService.has_role("admin"))
):
    """
    Manually trigger comprehensive pipeline fetch.
    
    Args:
        mode: Fetch mode - 'min', 'normal', 'max', or 'burst'
    """
    try:
        # Validate mode
        if mode not in ['min', 'normal', 'max', 'burst']:
            raise HTTPException(status_code=400, detail="Invalid mode")
        
        # Trigger async task
        task = run_comprehensive_pipeline.delay(mode=mode)
        
        return {
            "status": "triggered",
            "task_id": task.id,
            "mode": mode,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to trigger pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/source/{source}")
async def trigger_source_fetch(
    source: str,
    since_hours: Optional[int] = None,
    current_user: User = Depends(AuthService.has_role("admin")),
):
    """
    Manually trigger fetch for a specific source.
    
    Args:
        source: Source name (pubmed, youtube, github, discourse, wiki)
        since_hours: Fetch content from last N hours
    """
    try:
        valid_sources = ['pubmed', 'youtube', 'github', 'discourse', 'wiki']
        if source not in valid_sources:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid source. Must be one of: {valid_sources}"
            )
        
        # Trigger async task
        task = fetch_source_incremental.delay(source=source, since_hours=since_hours)
        
        return {
            "status": "triggered",
            "task_id": task.id,
            "source": source,
            "since_hours": since_hours,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to trigger source fetch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/supplementary")
async def trigger_supplementary_fetch(
    current_user: User = Depends(AuthService.has_role("admin")),
):
    """
    Manually trigger fetch for missing supplementary data (transcripts, etc).
    """
    try:
        # Trigger async task
        task = fetch_missing_supplementary_data.delay()
        
        return {
            "status": "triggered",
            "task_id": task.id,
            "target": "supplementary_data",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to trigger supplementary fetch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/parallel")
async def trigger_parallel_fetch(
    current_user: User = Depends(AuthService.has_role("admin")),
):
    """
    Manually trigger parallel fetch from all sources.
    """
    try:
        # Trigger async task
        task = run_parallel_source_fetch.delay()
        
        return {
            "status": "triggered",
            "task_id": task.id,
            "type": "parallel_all_sources",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to trigger parallel fetch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/latest")
async def get_pipeline_status(
    current_user: User = Depends(AuthService.has_role("admin")),
):
    """
    Get latest pipeline run status and statistics.
    """
    try:
        status = {}
        
        # Get latest stats from Redis
        if redis_client:
            # Find most recent stats key
            keys = redis_client.keys("pipeline:stats:*")
            if keys:
                latest_key = sorted(keys)[-1]  # Most recent by timestamp
                stats_json = redis_client.get(latest_key)
                if stats_json:
                    status['latest_run'] = json.loads(stats_json)
            
            # Get optimization results
            opt_json = redis_client.get("pipeline:optimization:latest")
            if opt_json:
                status['optimization'] = json.loads(opt_json)
        
        # Get content counts by source from Elasticsearch
        query = {
            "aggs": {
                "by_source": {
                    "terms": {
                        "field": "source",
                        "size": 10
                    },
                    "aggs": {
                        "recent": {
                            "filter": {
                                "range": {
                                    "indexed_date": {"gte": "now-24h"}
                                }
                            }
                        }
                    }
                }
            },
            "size": 0
        }
        
        response = es_client.search(index=settings.content_index, body=query)
        
        source_counts = {}
        for bucket in response['aggregations']['by_source']['buckets']:
            source_counts[bucket['key']] = {
                'total': bucket['doc_count'],
                'last_24h': bucket['recent']['doc_count']
            }
        
        status['content_counts'] = source_counts
        
        # Get schedule information
        scheduler = IntelligentScheduler()
        status['schedule'] = {
            'intervals': scheduler.OPTIMAL_INTERVALS,
            'breadth': scheduler.FETCH_BREADTH
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get pipeline status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedule")
async def get_pipeline_schedule(
    current_user: User = Depends(AuthService.has_role("admin")),
):
    """
    Get current pipeline schedule configuration.
    """
    try:
        scheduler = IntelligentScheduler()
        
        schedule = {
            "sources": {}
        }
        
        for source in ['pubmed', 'youtube', 'github', 'discourse', 'wiki']:
            schedule["sources"][source] = {
                "interval_hours": scheduler.OPTIMAL_INTERVALS[source],
                "fetch_breadth": scheduler.FETCH_BREADTH[source],
                "next_run": _calculate_next_run(source, scheduler.OPTIMAL_INTERVALS[source])
            }
        
        # Add comprehensive pipeline schedule
        schedule["comprehensive"] = {
            "frequency": "daily",
            "time": "01:00 UTC",
            "mode": "normal"
        }
        
        # Add supplementary tasks
        schedule["supplementary"] = {
            "transcripts": {
                "frequency": "twice_daily",
                "times": ["00:30 UTC", "12:30 UTC"]
            },
            "optimization": {
                "frequency": "weekly",
                "day": "Sunday",
                "time": "00:00 UTC"
            }
        }
        
        return schedule
        
    except Exception as e:
        logger.error(f"Failed to get schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize")
async def trigger_schedule_optimization(
    current_user: User = Depends(AuthService.has_role("admin")),
):
    """
    Manually trigger schedule optimization analysis.
    """
    try:
        # Trigger async task
        task = optimize_fetch_schedule.delay()
        
        return {
            "status": "triggered",
            "task_id": task.id,
            "type": "schedule_optimization",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to trigger optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_pipeline_metrics(
    days: int = 7,
    current_user: User = Depends(AuthService.has_role("admin")),
):
    """
    Get pipeline performance metrics.
    
    Args:
        days: Number of days to look back
    """
    try:
        # Query for content velocity and quality metrics
        query = {
            "query": {
                "range": {
                    "indexed_date": {
                        "gte": f"now-{days}d"
                    }
                }
            },
            "aggs": {
                "daily_metrics": {
                    "date_histogram": {
                        "field": "indexed_date",
                        "calendar_interval": "day"
                    },
                    "aggs": {
                        "by_source": {
                            "terms": {
                                "field": "source"
                            }
                        },
                        "avg_score": {
                            "avg": {"field": "ml_score"}
                        },
                        "high_quality": {
                            "filter": {
                                "range": {"ml_score": {"gte": 0.8}}
                            }
                        }
                    }
                },
                "source_quality": {
                    "terms": {
                        "field": "source"
                    },
                    "aggs": {
                        "avg_score": {
                            "avg": {"field": "ml_score"}
                        },
                        "with_transcript": {
                            "filter": {
                                "exists": {"field": "transcript"}
                            }
                        }
                    }
                }
            },
            "size": 0
        }
        
        response = es_client.search(index=settings.content_index, body=query)
        
        # Process metrics
        metrics = {
            "period_days": days,
            "daily_trends": [],
            "source_performance": {}
        }
        
        # Daily trends
        for bucket in response['aggregations']['daily_metrics']['buckets']:
            daily = {
                "date": bucket['key_as_string'],
                "total_content": bucket['doc_count'],
                "avg_quality": bucket['avg_score']['value'] or 0,
                "high_quality_count": bucket['high_quality']['doc_count'],
                "by_source": {}
            }
            
            for source_bucket in bucket['by_source']['buckets']:
                daily['by_source'][source_bucket['key']] = source_bucket['doc_count']
            
            metrics['daily_trends'].append(daily)
        
        # Source performance
        for bucket in response['aggregations']['source_quality']['buckets']:
            source = bucket['key']
            metrics['source_performance'][source] = {
                "total_items": bucket['doc_count'],
                "avg_quality_score": bucket['avg_score']['value'] or 0,
                "with_supplementary_data": bucket['with_transcript']['doc_count']
            }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _calculate_next_run(source: str, interval_hours: int) -> str:
    """
    Calculate next scheduled run time for a source.
    """
    now = datetime.utcnow()
    
    # Simplified calculation - would need to check actual schedule
    if source == 'wiki':
        # Weekly on Monday
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0 and now.hour >= 0:
            days_until_monday = 7
        next_run = now + timedelta(days=days_until_monday)
        next_run = next_run.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # Regular interval
        next_run = now + timedelta(hours=interval_hours)
    
    return next_run.isoformat()