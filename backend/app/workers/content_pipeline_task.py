"""
Enhanced content pipeline task for comprehensive multi-source fetching.
Implements intelligent scheduling with proper intervals and supplementary data collection.
"""

import os
import sys
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from celery import shared_task, group, chain
import json

# Add jobs directory to path
sys.path.insert(0, "/app/jobs")

from jobs.pipeline_orchestrator import ContentPipelineOrchestrator
from ..database import es_client, redis_client
from ..config import settings

logger = logging.getLogger(__name__)


class IntelligentScheduler:
    """
    Intelligent scheduling for content fetching based on source characteristics.
    """
    
    # Source-specific optimal intervals (in hours)
    OPTIMAL_INTERVALS = {
        'pubmed': 24,       # Daily - new articles published daily
        'youtube': 12,      # Twice daily - videos can go viral quickly  
        'github': 6,        # 4x daily - code updates frequently
        'discourse': 4,     # 6x daily - discussions are real-time
        'wiki': 168,        # Weekly - documentation changes slowly
    }
    
    # Breadth configuration (items per fetch)
    FETCH_BREADTH = {
        'pubmed': {
            'min': 10,
            'normal': 50,
            'max': 200,
            'burst': 500  # For initial population
        },
        'youtube': {
            'min': 5,
            'normal': 20,
            'max': 50,
            'burst': 100
        },
        'github': {
            'min': 5,
            'normal': 30,
            'max': 100,
            'burst': 300
        },
        'discourse': {
            'min': 10,
            'normal': 50,
            'max': 200,
            'burst': 500
        },
        'wiki': {
            'min': 2,
            'normal': 10,
            'max': 30,
            'burst': 50
        }
    }
    
    @classmethod
    def get_fetch_config(cls, source: str, mode: str = 'normal') -> Dict[str, Any]:
        """
        Get optimal fetch configuration for a source.
        
        Args:
            source: Content source name
            mode: 'min', 'normal', 'max', or 'burst'
            
        Returns:
            Configuration dictionary
        """
        return {
            'interval_hours': cls.OPTIMAL_INTERVALS.get(source, 24),
            'max_items': cls.FETCH_BREADTH.get(source, {}).get(mode, 50),
            'enable_supplementary': True,
            'fetch_transcripts': source == 'youtube',
            'fetch_readme': source == 'github',
            'fetch_full_content': source in ['discourse', 'wiki']
        }


@shared_task(bind=True, max_retries=3)
def run_comprehensive_pipeline(self, mode: str = 'normal'):
    """
    Run comprehensive content pipeline with all sources and supplementary data.
    
    Args:
        mode: Fetch mode - 'min', 'normal', 'max', or 'burst'
    """
    try:
        logger.info(f"Starting comprehensive pipeline in {mode} mode")
        
        # Initialize orchestrator with enhanced configuration
        config = {
            'enable_pubmed': True,
            'enable_youtube': True,
            'enable_github': True,
            'enable_discourse': True,
            'enable_wiki': True,
            'enable_ai_enhancement': True,
            'enable_relationships': True,
            'fetch_supplementary_data': True,
            'auto_approve_threshold': 0.7,
            'priority_threshold': 0.5,
        }
        
        orchestrator = ContentPipelineOrchestrator(
            es_client=es_client,
            redis_client=redis_client,
            config=config
        )
        
        # Get fetch limits based on mode
        scheduler = IntelligentScheduler()
        fetch_limits = {}
        for source in ['pubmed', 'youtube', 'github', 'discourse', 'wiki']:
            source_config = scheduler.get_fetch_config(source, mode)
            fetch_limits[source] = source_config['max_items']
            
            # Configure supplementary data fetching
            if source == 'youtube' and source_config['fetch_transcripts']:
                fetcher = orchestrator.fetchers.get('youtube')
                if fetcher:
                    fetcher.fetch_transcripts = True
                    logger.info("✅ YouTube transcript fetching enabled")
        
        # Run pipeline with configured limits
        results = orchestrator.run_daily_fetch_with_limits(fetch_limits)
        
        # Store run statistics
        if redis_client:
            stats_key = f"pipeline:stats:{datetime.utcnow().isoformat()}"
            redis_client.setex(stats_key, 86400, json.dumps(results))
        
        logger.info(f"Pipeline completed successfully: {results.get('summary', {})}")
        return results
        
    except Exception as exc:
        logger.error(f"Pipeline task failed: {exc}")
        raise self.retry(exc=exc, countdown=300)  # Retry after 5 minutes


@shared_task(bind=True)
def fetch_source_incremental(self, source: str, since_hours: int = None):
    """
    Fetch incremental updates from a specific source.
    
    Args:
        source: Content source to fetch from
        since_hours: Fetch content from last N hours (default: source-specific)
    """
    try:
        scheduler = IntelligentScheduler()
        
        # Use optimal interval if not specified
        if since_hours is None:
            since_hours = scheduler.OPTIMAL_INTERVALS.get(source, 24)
        
        logger.info(f"Fetching incremental updates from {source} (last {since_hours} hours)")
        
        # Calculate date filter
        since_date = (datetime.utcnow() - timedelta(hours=since_hours)).isoformat()
        
        # Initialize orchestrator
        orchestrator = ContentPipelineOrchestrator(
            es_client=es_client,
            redis_client=redis_client
        )
        
        # Get the fetcher
        fetcher = orchestrator.fetchers.get(source)
        if not fetcher:
            logger.error(f"Fetcher not found for source: {source}")
            return {'error': f'Fetcher not found for {source}'}
        
        # Fetch with date filter
        if source == 'pubmed':
            # PubMed supports date filtering
            query = f'OHDSI AND "{since_date}"[PDAT]'
            content_items = fetcher.search_pubmed(query, max_results=50)
        elif source == 'youtube':
            # YouTube supports publishedAfter
            filters = {'published_after': since_date + 'Z'}
            content_items = fetcher.search('OHDSI', max_results=20, filters=filters)
        elif source == 'github':
            # GitHub supports created/updated filters
            filters = {'created_after': since_date}
            content_items = fetcher.search('OHDSI', max_results=30, filters=filters)
        elif source == 'discourse':
            # Discourse - fetch latest topics
            content_items = fetcher.fetch_latest_topics(max_topics=50)
            # Filter by date client-side
            content_items = [
                item for item in content_items
                if item.get('created_at', '') > since_date
            ]
        elif source == 'wiki':
            # Wiki - check last modified
            content_items = fetcher.fetch_ohdsi_documentation(max_pages=10)
            # Filter by last_modified if available
            content_items = [
                item for item in content_items
                if item.get('last_modified', since_date) > since_date
            ]
        else:
            content_items = []
        
        # Process the fetched content
        for item in content_items:
            item['source'] = source
        
        processed = orchestrator._process_content_batch(content_items)
        
        logger.info(f"Incremental fetch from {source}: {len(content_items)} fetched, {len(processed)} processed")
        
        return {
            'source': source,
            'fetched': len(content_items),
            'processed': len(processed),
            'since_date': since_date
        }
        
    except Exception as e:
        logger.error(f"Incremental fetch failed for {source}: {e}")
        return {'error': str(e), 'source': source}


@shared_task
def fetch_missing_supplementary_data():
    """
    Fetch missing supplementary data for existing content.
    E.g., transcripts for videos without them.
    """
    try:
        logger.info("Checking for missing supplementary data...")
        
        # Query for YouTube videos without transcripts
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"source": "youtube"}},
                        {"term": {"content_type": "video"}}
                    ],
                    "must_not": [
                        {"exists": {"field": "transcript"}}
                    ]
                }
            },
            "size": 100
        }
        
        response = es_client.search(index=settings.content_index, body=query)
        videos_without_transcripts = response['hits']['hits']
        
        if not videos_without_transcripts:
            logger.info("No videos missing transcripts")
            return {'updated': 0}
        
        logger.info(f"Found {len(videos_without_transcripts)} videos without transcripts")
        
        # Initialize transcript processor
        from jobs.youtube_fetcher.transcript_processor import TranscriptProcessor
        processor = TranscriptProcessor()
        
        updated_count = 0
        for hit in videos_without_transcripts:
            video = hit['_source']
            video_id = video.get('video_id') or video.get('id')
            
            if not video_id:
                continue
            
            # Fetch transcript
            transcript = processor.fetch_transcript(video_id)
            
            if transcript:
                # Process transcript
                processed = processor.process_transcript(transcript)
                
                # Update document
                update_body = {
                    "doc": {
                        "transcript": transcript,
                        "transcript_data": processed,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                }
                
                es_client.update(
                    index=settings.content_index,
                    id=hit['_id'],
                    body=update_body
                )
                
                updated_count += 1
                logger.info(f"✅ Added transcript for video: {video.get('title', '')[:50]}...")
        
        logger.info(f"Successfully added {updated_count} transcripts")
        return {'updated': updated_count, 'total_checked': len(videos_without_transcripts)}
        
    except Exception as e:
        logger.error(f"Failed to fetch supplementary data: {e}")
        return {'error': str(e)}


@shared_task
def optimize_fetch_schedule():
    """
    Analyze content patterns and optimize fetch schedule.
    Adjusts intervals based on content velocity and engagement.
    """
    try:
        logger.info("Analyzing content patterns for schedule optimization...")
        
        optimization_results = {}
        
        for source in ['pubmed', 'youtube', 'github', 'discourse', 'wiki']:
            # Analyze recent content velocity
            query = {
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"source": source}},
                            {"range": {"indexed_date": {"gte": "now-7d"}}}
                        ]
                    }
                },
                "aggs": {
                    "daily_count": {
                        "date_histogram": {
                            "field": "indexed_date",
                            "calendar_interval": "day"
                        }
                    },
                    "avg_score": {
                        "avg": {"field": "ml_score"}
                    },
                    "high_quality_count": {
                        "filter": {"range": {"ml_score": {"gte": 0.8}}}
                    }
                }
            }
            
            response = es_client.search(
                index=settings.content_index,
                body=query,
                size=0
            )
            
            # Calculate metrics
            total_items = response['hits']['total']['value']
            avg_daily = total_items / 7 if total_items > 0 else 0
            avg_score = response['aggregations']['avg_score']['value'] or 0
            high_quality = response['aggregations']['high_quality_count']['doc_count']
            
            # Determine optimal interval
            scheduler = IntelligentScheduler()
            current_interval = scheduler.OPTIMAL_INTERVALS[source]
            
            # Adjust based on velocity and quality
            if avg_daily > 20 and avg_score > 0.7:
                # High velocity, high quality - increase frequency
                new_interval = max(current_interval * 0.75, 1)  # Min 1 hour
                fetch_mode = 'max'
            elif avg_daily < 5:
                # Low velocity - decrease frequency
                new_interval = min(current_interval * 1.5, 168)  # Max 1 week
                fetch_mode = 'min'
            else:
                new_interval = current_interval
                fetch_mode = 'normal'
            
            optimization_results[source] = {
                'current_interval': current_interval,
                'recommended_interval': new_interval,
                'fetch_mode': fetch_mode,
                'avg_daily_items': avg_daily,
                'avg_quality_score': avg_score,
                'high_quality_percentage': (high_quality / total_items * 100) if total_items > 0 else 0
            }
        
        # Store optimization results
        if redis_client:
            redis_client.setex(
                "pipeline:optimization:latest",
                86400,
                json.dumps(optimization_results)
            )
        
        logger.info(f"Schedule optimization complete: {optimization_results}")
        return optimization_results
        
    except Exception as e:
        logger.error(f"Schedule optimization failed: {e}")
        return {'error': str(e)}


@shared_task
def run_parallel_source_fetch():
    """
    Fetch from all sources in parallel for maximum efficiency.
    """
    try:
        logger.info("Starting parallel source fetch...")
        
        # Create parallel task group
        job = group(
            fetch_source_incremental.s('pubmed'),
            fetch_source_incremental.s('youtube'),
            fetch_source_incremental.s('github'),
            fetch_source_incremental.s('discourse'),
            fetch_source_incremental.s('wiki')
        )
        
        # Execute in parallel
        result = job.apply_async()
        
        # Wait for completion and aggregate results
        results = result.get(timeout=600)  # 10 minute timeout
        
        total_fetched = sum(r.get('fetched', 0) for r in results)
        total_processed = sum(r.get('processed', 0) for r in results)
        
        summary = {
            'total_fetched': total_fetched,
            'total_processed': total_processed,
            'source_results': results,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Parallel fetch complete: {total_fetched} fetched, {total_processed} processed")
        return summary
        
    except Exception as e:
        logger.error(f"Parallel fetch failed: {e}")
        return {'error': str(e)}