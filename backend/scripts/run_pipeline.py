#!/usr/bin/env python3
"""
Consolidated OHDSI content pipeline runner.

Replaces the former run_full_pipeline.py, run_official_pipeline.py, and
run_content_pipelines.py scripts.

Usage:
    # Full pipeline: all sources with background monitoring and v3 schema validation
    python run_pipeline.py --mode full

    # Official pipeline: PubMed articles with broader OHDSI search terms
    python run_pipeline.py --mode official

    # Content pipeline: YouTube, GitHub, and Discourse sources
    python run_pipeline.py --mode content

    # Run only specific content sources
    python run_pipeline.py --mode content --sources youtube github

    # Adjust limits
    python run_pipeline.py --mode official --max-items 20
    python run_pipeline.py --mode full --batch-size 10
"""
import sys
import os
import json
import time
import argparse
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add the app directory to the path
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/jobs')
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from elasticsearch import Elasticsearch
from app.config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def get_es_client(url: Optional[str] = None) -> Elasticsearch:
    """Create and validate an Elasticsearch client."""
    host = url or settings.elasticsearch_url
    es_client = Elasticsearch(hosts=[host])
    if not es_client.ping():
        logger.error("Cannot connect to Elasticsearch at %s", host)
        sys.exit(1)
    logger.info("Connected to Elasticsearch")
    return es_client


def get_index_counts(es_client: Elasticsearch) -> Dict[str, int]:
    """Get current document counts from content and review indices."""
    counts: Dict[str, int] = {}

    # Content index
    try:
        counts['content_total'] = es_client.count(index=settings.content_index)['count']
        for status in ['approved', 'pending', 'rejected']:
            query = {"query": {"term": {"approval_status": status}}}
            counts[f'content_{status}'] = es_client.count(
                index=settings.content_index, body=query
            )['count']
    except Exception as e:
        logger.warning("Error counting content index: %s", e)

    # Review index
    try:
        counts['review_total'] = es_client.count(index=settings.review_index)['count']
        for status in ['pending', 'approved', 'rejected']:
            query = {"query": {"term": {"status": status}}}
            counts[f'review_{status}'] = es_client.count(
                index=settings.review_index, body=query
            )['count']
    except Exception as e:
        logger.warning("Error counting review index: %s", e)

    return counts


def print_counts(counts: Dict[str, int], initial: Optional[Dict[str, int]] = None):
    """Print document counts, optionally showing deltas from initial."""
    for key, value in counts.items():
        if initial:
            prev = initial.get(key, 0)
            change = value - prev
            if change != 0:
                sign = "+" if change > 0 else ""
                logger.info("  %s: %d (%s%d)", key, value, sign, change)
            else:
                logger.info("  %s: %d", key, value)
        else:
            logger.info("  %s: %d", key, value)


def check_ingestion_results(es_client: Elasticsearch):
    """Aggregate content by type and source, and summarise the review queue."""
    logger.info("\n" + "=" * 60)
    logger.info("INGESTION RESULTS")
    logger.info("=" * 60)

    try:
        response = es_client.search(
            index=settings.content_index,
            body={
                'aggs': {
                    'by_type': {'terms': {'field': 'content_type'}},
                    'by_source': {'terms': {'field': 'source'}},
                },
                'size': 0,
            }
        )

        logger.info("Content by Type:")
        for bucket in response['aggregations']['by_type']['buckets']:
            logger.info("  %s: %d", bucket['key'], bucket['doc_count'])

        logger.info("Content by Source:")
        for bucket in response['aggregations']['by_source']['buckets']:
            logger.info("  %s: %d", bucket['key'], bucket['doc_count'])
    except Exception as e:
        logger.warning("Could not aggregate content index: %s", e)

    try:
        response = es_client.search(
            index=settings.review_index,
            body={
                'query': {'term': {'status': 'pending'}},
                'aggs': {'by_type': {'terms': {'field': 'content_type'}}},
                'size': 0,
            }
        )
        logger.info("Pending in Review Queue: %d", response['hits']['total']['value'])
        for bucket in response['aggregations']['by_type']['buckets']:
            logger.info("  %s: %d", bucket['key'], bucket['doc_count'])
    except Exception as e:
        logger.warning("Could not aggregate review index: %s", e)


# ---------------------------------------------------------------------------
# v3 schema validation (used by full pipeline)
# ---------------------------------------------------------------------------

def validate_document(doc: Dict[str, Any], warnings: List[str]) -> bool:
    """Validate that a document has proper v3 fields."""
    required_v3_fields = ['ml_score', 'ai_confidence', 'final_score', 'categories']
    old_fields = ['gpt_score', 'combined_score', 'predicted_categories', 'quality_score']

    valid = True
    for field in required_v3_fields:
        if field not in doc:
            warnings.append(f"Document missing v3 field: {field}")
            valid = False

    for field in old_fields:
        if field in doc:
            warnings.append(f"Document still has old field: {field}")

    return valid


def sample_and_validate(es_client: Elasticsearch, warnings: List[str]):
    """Sample recent documents and validate their v3 structure."""
    try:
        response = es_client.search(
            index=settings.content_index,
            body={
                "size": 5,
                "query": {"match_all": {}},
                "sort": [{"indexed_date": {"order": "desc"}}],
            }
        )

        logger.info("\nValidating recent documents...")
        for hit in response['hits']['hits']:
            doc_id = hit['_id']
            doc = hit['_source']
            if validate_document(doc, warnings):
                logger.info("  Document %s: Valid v3 structure", doc_id)
            else:
                logger.warning("  Document %s: Invalid structure", doc_id)

    except Exception as e:
        logger.warning("Error sampling documents: %s", e)


# ---------------------------------------------------------------------------
# Mode: full
# ---------------------------------------------------------------------------

def run_full_pipeline(es_client: Elasticsearch, args):
    """
    Run the full OHDSI pipeline with background monitoring and v3 validation.

    All sources enabled (PubMed, GitHub, Discourse, Wiki), pipeline runs in a
    background thread while the main thread monitors progress.
    """
    from jobs.pipeline_orchestrator import ContentPipelineOrchestrator

    logger.info("=" * 70)
    logger.info("OHDSI PIPELINE FULL TEST - v3 Schema Validation")
    logger.info("=" * 70)

    errors: List[str] = []
    warnings: List[str] = []

    # Initial counts
    logger.info("\nInitial document counts:")
    initial_counts = get_index_counts(es_client)
    print_counts(initial_counts)

    pipeline_results: Dict[str, Any] = {}

    def _run_pipeline():
        nonlocal pipeline_results
        try:
            logger.info("\nStarting pipeline orchestrator...")

            config = {
                'enable_pubmed': True,
                'enable_youtube': False,
                'enable_github': True,
                'enable_discourse': True,
                'enable_wiki': True,
                'enable_ai_enhancement': False,
                'enable_relationships': False,
                'auto_approve_threshold': 0.7,
                'batch_size': args.batch_size,
            }

            orchestrator = ContentPipelineOrchestrator(
                es_client=es_client, config=config
            )

            logger.info("\nFetching content from all sources (max %d per source)...", args.max_items)
            results = orchestrator.process_all_sources(max_items_per_source=args.max_items)

            logger.info("\nPipeline completed!")
            logger.info("Results: %s", json.dumps(results, indent=2))
            pipeline_results.update(results)

        except Exception as e:
            errors.append(f"Pipeline error: {e}")
            import traceback
            traceback.print_exc()

    # Start in background thread
    pipeline_thread = threading.Thread(target=_run_pipeline, daemon=True)
    pipeline_thread.start()

    logger.info("\nPipeline running in background...")
    logger.info("Monitoring progress (press Ctrl+C to stop)...\n")

    check_interval = 5  # seconds
    max_checks = 24  # 2 minutes max

    for i in range(max_checks):
        time.sleep(check_interval)
        current_counts = get_index_counts(es_client)

        logger.info("\n[%s] Status Update #%d:", datetime.now().strftime('%H:%M:%S'), i + 1)
        changes = False
        for key in current_counts:
            initial = initial_counts.get(key, 0)
            current = current_counts[key]
            if current != initial:
                change = current - initial
                sign = "+" if change > 0 else ""
                logger.info("  %s: %d (%s%d)", key, current, sign, change)
                changes = True

        if not changes:
            logger.info("  No changes yet...")

        if not pipeline_thread.is_alive():
            logger.info("\nPipeline thread completed")
            break

        if errors:
            logger.error("Errors detected:")
            for error in errors[-3:]:
                logger.error("  - %s", error)

    pipeline_thread.join(timeout=10)

    # Final validation
    logger.info("\n" + "=" * 70)
    logger.info("FINAL VALIDATION")
    logger.info("=" * 70)

    sample_and_validate(es_client, warnings)

    logger.info("\nFinal document counts:")
    final_counts = get_index_counts(es_client)
    print_counts(final_counts, initial_counts)

    if pipeline_results:
        logger.info("\nPipeline Statistics:")
        logger.info("  Total fetched: %d", pipeline_results.get('total_fetched', 0))
        logger.info("  Total processed: %d", pipeline_results.get('total_processed', 0))
        logger.info("  Total indexed: %d", pipeline_results.get('total_indexed', 0))
        logger.info("  Duplicates found: %d", pipeline_results.get('duplicates_found', 0))
        logger.info("  Errors: %d", pipeline_results.get('errors', 0))

        if 'by_source' in pipeline_results:
            logger.info("\n  By Source:")
            for source, count in pipeline_results['by_source'].items():
                logger.info("    %s: %d", source, count)

        if 'by_type' in pipeline_results:
            logger.info("\n  By Type:")
            for content_type, count in pipeline_results['by_type'].items():
                logger.info("    %s: %d", content_type, count)

    # Summary
    logger.info("\n" + "=" * 70)
    if errors:
        logger.warning("Pipeline completed with errors:")
        for error in errors:
            logger.error("  - %s", error)
    else:
        logger.info("Pipeline completed successfully!")

    if warnings:
        logger.warning("Warnings:")
        for warning in set(warnings):
            logger.warning("  - %s", warning)
    logger.info("=" * 70)

    return len(errors) == 0


# ---------------------------------------------------------------------------
# Mode: official
# ---------------------------------------------------------------------------

def run_official_pipeline(es_client: Elasticsearch, args):
    """
    Run the official OHDSI article classification pipeline with broader PubMed
    search terms and the ArticleClassifierWrapper.
    """
    from backend.jobs.article_classifier.wrapper import ArticleClassifierWrapper

    logger.info("=" * 60)
    logger.info("Running Official OHDSI Pipeline")
    logger.info("Time: %s", datetime.now().isoformat())
    logger.info("=" * 60)

    wrapper = ArticleClassifierWrapper(
        es_client=es_client,
        threshold=0.5,
        auto_approve_threshold=0.7,
        use_enhanced=True,
        use_v2=True,
    )

    logger.info("Using classifier: %s", wrapper.classifier.__class__.__name__)
    logger.info("Model type: %s", wrapper.classifier.model_type)
    logger.info("Indices: content=%s, review=%s", wrapper.content_index, wrapper.review_index)

    # Initial counts
    content_before = es_client.count(index=wrapper.content_index)['count']
    review_before = es_client.count(index=wrapper.review_index)['count']
    pending_before = es_client.count(
        index=wrapper.review_index,
        body={'query': {'term': {'status': 'pending'}}}
    )['count']

    logger.info("\nBefore processing:")
    logger.info("  Content: %d", content_before)
    logger.info("  Review: %d", review_before)
    logger.info("  Pending: %d", pending_before)

    # Broader OHDSI search terms
    search_terms = [
        "OHDSI",
        "OMOP CDM",
        "OMOP Common Data Model",
        "ATLAS OHDSI",
        "HADES OHDSI",
        "Observational Health Data Sciences",
        "ACHILLES OHDSI",
        "THEMIS OHDSI",
        "DataQualityDashboard OHDSI",
        "CohortMethod",
        "PatientLevelPrediction",
        "OHDSI network study",
        "OHDSI community",
        "OHDSI collaborative",
        "OMOP standardized vocabulary",
    ]

    logger.info("\nSearching for %d different OHDSI-related terms...", len(search_terms))

    total_processed = 0
    total_auto_approved = 0
    total_sent_to_review = 0
    total_errors = 0

    for term in search_terms:
        logger.info("\nSearching: '%s'...", term)
        try:
            articles = wrapper.fetch_and_classify_articles(
                query=term,
                max_articles=args.max_items,
            )

            if articles:
                processed = len(articles)
                total_processed += processed

                for article in articles:
                    ml_score = article.get('ml_score', 0)
                    if ml_score >= 0.7:
                        total_auto_approved += 1
                    elif ml_score >= 0.3:
                        total_sent_to_review += 1

                logger.info("  Processed %d articles", processed)
            else:
                logger.info("  No new articles found")

        except Exception as e:
            logger.error("  Error processing '%s': %s", term, e)
            total_errors += 1

    # Final counts
    content_after = es_client.count(index=wrapper.content_index)['count']
    review_after = es_client.count(index=wrapper.review_index)['count']
    pending_after = es_client.count(
        index=wrapper.review_index,
        body={'query': {'term': {'status': 'pending'}}}
    )['count']

    content_added = content_after - content_before
    review_added = review_after - review_before
    pending_added = pending_after - pending_before

    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 60)

    logger.info("\nProcessing Summary:")
    logger.info("  Search terms used: %d", len(search_terms))
    logger.info("  Articles processed: %d", total_processed)
    logger.info("  Auto-approved (high confidence): ~%d", total_auto_approved)
    logger.info("  Sent to review: ~%d", total_sent_to_review)
    logger.info("  Errors: %d", total_errors)

    logger.info("\nIndex Changes:")
    logger.info("  Content added: %d", content_added)
    logger.info("  Review queue added: %d", review_added)
    logger.info("  New pending items: %d", pending_added)

    logger.info("\nFinal Counts:")
    logger.info("  Total content: %d", content_after)
    logger.info("  Total in review: %d", review_after)
    logger.info("  Pending review: %d", pending_after)

    if pending_added > 0:
        logger.info("Successfully added %d new articles to review queue!", pending_added)
    else:
        logger.info("No new articles were added to the review queue")

    return True


# ---------------------------------------------------------------------------
# Mode: content
# ---------------------------------------------------------------------------

def _run_single_source_pipeline(
    es_client: Elasticsearch,
    source_name: str,
    enable_key: str,
    fetch_fn,
    max_items: int = 5,
):
    """Run a single content source pipeline (youtube, github, or discourse)."""
    from jobs.pipeline_orchestrator import ContentPipelineOrchestrator

    logger.info("\n" + "=" * 60)
    logger.info("%s CONTENT PIPELINE", source_name.upper())
    logger.info("=" * 60)

    try:
        config = {
            'enable_youtube': False,
            'enable_github': False,
            'enable_discourse': False,
            'enable_pubmed': False,
            'enable_wiki': False,
            'auto_approve_threshold': 0.5,
        }
        config[enable_key] = True

        orchestrator = ContentPipelineOrchestrator(es_client=es_client, config=config)

        fetcher = orchestrator.fetchers.get(source_name)
        if not fetcher:
            logger.warning("%s fetcher not available", source_name.capitalize())
            return

        items = fetch_fn(fetcher)
        logger.info("Found %d %s items", len(items), source_name)

        processed = 0
        approved = 0
        for item in items[:max_items]:
            result = orchestrator._process_single_item(item)
            if result:
                processed += 1
                if result.get('approval_status') == 'approved':
                    approved += 1
                title = item.get('title', item.get('name', 'Unknown'))
                logger.info(
                    "  - %s... (Score: %.2f)",
                    title[:60],
                    result.get('ml_score', 0),
                )

        logger.info("Processed: %d, Approved: %d", processed, approved)

    except Exception as e:
        logger.error("Error in %s pipeline: %s", source_name, e)
        import traceback
        traceback.print_exc()


def run_content_pipelines(es_client: Elasticsearch, args):
    """
    Run non-article content pipelines (YouTube, GitHub, Discourse).

    Optionally filter to specific sources via --sources.
    """
    logger.info("Running Non-Article Content Pipelines")
    logger.info("=" * 60)
    logger.info("Started at: %s", datetime.now().isoformat())

    available_sources = args.sources or ['youtube', 'github', 'discourse']

    if 'youtube' in available_sources:
        from jobs.youtube_fetcher.fetcher import YouTubeFetcher  # noqa: F401

        def fetch_youtube(fetcher):
            return fetcher.fetch_ohdsi_content(max_results_per_query=10)

        _run_single_source_pipeline(
            es_client, 'youtube', 'enable_youtube', fetch_youtube, args.max_items,
        )

    if 'github' in available_sources:
        from jobs.github_scanner.scanner import GitHubScanner  # noqa: F401

        def fetch_github(fetcher):
            return fetcher.fetch_org_repositories('OHDSI', max_results=10)

        _run_single_source_pipeline(
            es_client, 'github', 'enable_github', fetch_github, args.max_items,
        )

    if 'discourse' in available_sources:
        from jobs.discourse_fetcher.fetcher import DiscourseFetcher  # noqa: F401

        def fetch_discourse(fetcher):
            return fetcher.fetch_latest_topics(max_topics=10)

        _run_single_source_pipeline(
            es_client, 'discourse', 'enable_discourse', fetch_discourse, args.max_items,
        )

    check_ingestion_results(es_client)

    logger.info("\n" + "=" * 60)
    logger.info("Completed at: %s", datetime.now().isoformat())
    logger.info("All pipelines completed!")

    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run OHDSI content ingestion pipelines.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python run_pipeline.py --mode full\n"
            "  python run_pipeline.py --mode official --max-items 20\n"
            "  python run_pipeline.py --mode content --sources youtube github\n"
        ),
    )
    parser.add_argument(
        '--mode',
        required=True,
        choices=['full', 'official', 'content'],
        help=(
            "Pipeline mode. "
            "'full': all sources with monitoring and v3 validation. "
            "'official': PubMed articles with broader OHDSI search terms. "
            "'content': YouTube, GitHub, and Discourse sources."
        ),
    )
    parser.add_argument(
        '--sources',
        nargs='+',
        choices=['youtube', 'github', 'discourse'],
        default=None,
        help="(content mode only) Specific sources to run. Default: all three.",
    )
    parser.add_argument(
        '--max-items',
        type=int,
        default=5,
        help="Maximum items to process per source/search-term. Default: 5.",
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=5,
        help="(full mode only) Batch size for pipeline orchestrator. Default: 5.",
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    es_client = get_es_client()

    mode_dispatch = {
        'full': run_full_pipeline,
        'official': run_official_pipeline,
        'content': run_content_pipelines,
    }

    success = mode_dispatch[args.mode](es_client, args)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
