#!/usr/bin/env python3
"""
Verify that the content pipeline is properly set up and all fetchers are working.
"""

import sys
import os
import logging
from datetime import datetime

# Add paths
sys.path.insert(0, "/app/jobs")
sys.path.insert(0, "/app")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def check_environment():
    """Check environment variables and API keys."""
    logger.info("=" * 60)
    logger.info("ENVIRONMENT CHECK")
    logger.info("=" * 60)
    
    env_vars = {
        'YOUTUBE_API_KEY': os.getenv('YOUTUBE_API_KEY'),
        'GITHUB_TOKEN': os.getenv('GITHUB_TOKEN'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'NCBI_ENTREZ_EMAIL': os.getenv('NCBI_ENTREZ_EMAIL'),
        'DISCOURSE_API_KEY': os.getenv('DISCOURSE_API_KEY'),
    }
    
    for key, value in env_vars.items():
        if value:
            logger.info(f"✅ {key}: Set ({len(value)} chars)")
        else:
            logger.info(f"⚠️  {key}: Not set")
    
    return env_vars


def check_database_connections():
    """Check Elasticsearch and Redis connections."""
    logger.info("\n" + "=" * 60)
    logger.info("DATABASE CONNECTIONS")
    logger.info("=" * 60)
    
    results = {}
    
    # Check Elasticsearch
    try:
        from app.database import es_client
        from app.config import settings
        
        if es_client.ping():
            logger.info("✅ Elasticsearch: Connected")
            
            # Check indices
            indices = es_client.indices.get_alias(index="*").keys()
            content_index = settings.content_index
            review_index = settings.review_index
            
            if content_index in indices:
                logger.info(f"  ✅ Content index exists: {content_index}")
            else:
                logger.info(f"  ⚠️  Content index missing: {content_index}")
            
            if review_index in indices:
                logger.info(f"  ✅ Review index exists: {review_index}")
            else:
                logger.info(f"  ⚠️  Review index missing: {review_index}")
            
            results['elasticsearch'] = True
        else:
            logger.info("❌ Elasticsearch: Not connected")
            results['elasticsearch'] = False
    except Exception as e:
        logger.info(f"❌ Elasticsearch: Error - {e}")
        results['elasticsearch'] = False
    
    # Check Redis
    try:
        from app.database import redis_client
        
        if redis_client and redis_client.ping():
            logger.info("✅ Redis: Connected")
            results['redis'] = True
        else:
            logger.info("⚠️  Redis: Not connected (optional)")
            results['redis'] = False
    except Exception as e:
        logger.info(f"⚠️  Redis: Error - {e} (optional)")
        results['redis'] = False
    
    return results


def check_fetchers():
    """Check that all fetchers can be initialized."""
    logger.info("\n" + "=" * 60)
    logger.info("FETCHER INITIALIZATION")
    logger.info("=" * 60)
    
    fetchers = {}
    
    # PubMed
    try:
        from jobs.article_classifier.retriever import PubMedRetriever
        retriever = PubMedRetriever()
        fetchers['pubmed'] = True
        logger.info("✅ PubMed: Initialized")
    except Exception as e:
        fetchers['pubmed'] = False
        logger.info(f"❌ PubMed: {e}")
    
    # YouTube
    try:
        from jobs.youtube_fetcher.fetcher import YouTubeFetcher
        fetcher = YouTubeFetcher()
        fetchers['youtube'] = True
        if os.getenv('YOUTUBE_API_KEY'):
            logger.info("✅ YouTube: Initialized with API key")
        else:
            logger.info("⚠️  YouTube: Initialized but no API key")
    except Exception as e:
        fetchers['youtube'] = False
        logger.info(f"❌ YouTube: {e}")
    
    # GitHub
    try:
        from jobs.github_scanner.scanner import GitHubScanner
        scanner = GitHubScanner()
        fetchers['github'] = True
        if os.getenv('GITHUB_TOKEN'):
            logger.info("✅ GitHub: Initialized with token")
        else:
            logger.info("⚠️  GitHub: Initialized but no token (rate limited)")
    except Exception as e:
        fetchers['github'] = False
        logger.info(f"❌ GitHub: {e}")
    
    # Discourse
    try:
        from jobs.discourse_fetcher.fetcher import DiscourseFetcher
        fetcher = DiscourseFetcher()
        fetchers['discourse'] = True
        logger.info("✅ Discourse: Initialized")
    except Exception as e:
        fetchers['discourse'] = False
        logger.info(f"❌ Discourse: {e}")
    
    # Wiki
    try:
        from jobs.wiki_scraper.scraper import WikiScraper
        scraper = WikiScraper()
        fetchers['wiki'] = True
        logger.info("✅ Wiki: Initialized")
    except Exception as e:
        fetchers['wiki'] = False
        logger.info(f"❌ Wiki: {e}")
    
    return fetchers


def check_pipeline_orchestrator():
    """Check that the pipeline orchestrator can be initialized."""
    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE ORCHESTRATOR")
    logger.info("=" * 60)
    
    try:
        from jobs.pipeline_orchestrator import ContentPipelineOrchestrator
        from app.database import es_client, redis_client
        
        config = {
            'enable_pubmed': True,
            'enable_youtube': True,
            'enable_github': True,
            'enable_discourse': True,
            'enable_wiki': True,
            'enable_ai_enhancement': False,  # Skip AI for this test
        }
        
        orchestrator = ContentPipelineOrchestrator(
            es_client=es_client,
            redis_client=redis_client,
            config=config
        )
        
        logger.info("✅ Pipeline orchestrator initialized")
        
        # Check fetchers
        logger.info("\nRegistered fetchers:")
        for name in orchestrator.fetchers.keys():
            logger.info(f"  - {name}")
        
        return True
        
    except Exception as e:
        logger.info(f"❌ Pipeline orchestrator failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_celery_tasks():
    """Check that Celery tasks are importable."""
    logger.info("\n" + "=" * 60)
    logger.info("CELERY TASKS")
    logger.info("=" * 60)
    
    try:
        from app.workers.content_pipeline_task import (
            run_comprehensive_pipeline,
            fetch_source_incremental,
            fetch_missing_supplementary_data,
            optimize_fetch_schedule,
            run_parallel_source_fetch
        )
        
        logger.info("✅ All Celery tasks imported successfully")
        logger.info("  - run_comprehensive_pipeline")
        logger.info("  - fetch_source_incremental")
        logger.info("  - fetch_missing_supplementary_data")
        logger.info("  - optimize_fetch_schedule")
        logger.info("  - run_parallel_source_fetch")
        
        return True
        
    except Exception as e:
        logger.info(f"❌ Celery tasks import failed: {e}")
        return False


def test_simple_fetch():
    """Test a simple fetch from one source."""
    logger.info("\n" + "=" * 60)
    logger.info("SIMPLE FETCH TEST")
    logger.info("=" * 60)
    
    try:
        from jobs.discourse_fetcher.fetcher import DiscourseFetcher
        
        logger.info("Testing Discourse fetcher (no API key required)...")
        fetcher = DiscourseFetcher()
        
        # Fetch just 1 topic
        topics = fetcher.fetch_latest_topics(max_topics=1)
        
        if topics:
            logger.info(f"✅ Fetched {len(topics)} topic")
            topic = topics[0]
            logger.info(f"  Title: {topic.get('title', 'No title')[:50]}...")
            logger.info(f"  URL: {topic.get('url', 'No URL')}")
            return True
        else:
            logger.info("⚠️  No topics fetched (forum might be down)")
            return False
            
    except Exception as e:
        logger.info(f"❌ Simple fetch failed: {e}")
        return False


def main():
    """Run all verification checks."""
    logger.info("🚀 OHDSI CONTENT PIPELINE VERIFICATION")
    logger.info("=" * 60)
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Run checks
    env_vars = check_environment()
    db_status = check_database_connections()
    fetchers = check_fetchers()
    orchestrator_ok = check_pipeline_orchestrator()
    celery_ok = check_celery_tasks()
    fetch_ok = test_simple_fetch()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    
    # Count successes
    api_keys_available = sum(1 for v in env_vars.values() if v)
    fetchers_working = sum(1 for v in fetchers.values() if v)
    
    logger.info(f"API Keys: {api_keys_available}/5 configured")
    logger.info(f"Databases: {'✅' if db_status.get('elasticsearch') else '❌'} Elasticsearch, {'✅' if db_status.get('redis') else '⚠️'} Redis")
    logger.info(f"Fetchers: {fetchers_working}/5 initialized")
    logger.info(f"Orchestrator: {'✅' if orchestrator_ok else '❌'}")
    logger.info(f"Celery Tasks: {'✅' if celery_ok else '❌'}")
    logger.info(f"Test Fetch: {'✅' if fetch_ok else '❌'}")
    
    # Overall status
    logger.info("\n" + "=" * 60)
    if orchestrator_ok and db_status.get('elasticsearch') and fetchers_working >= 3:
        logger.info("✅ PIPELINE IS READY TO USE")
        logger.info("Note: Some sources may have limited functionality without API keys")
    else:
        logger.info("⚠️  PIPELINE NEEDS CONFIGURATION")
        logger.info("Please check the errors above and configure missing components")
    
    logger.info("=" * 60)


if __name__ == "__main__":
    main()