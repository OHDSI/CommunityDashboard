#!/usr/bin/env python3
"""
Check the review queue contents, diagnose issues, and optionally ingest a test article.

Consolidates the former check_review_queue.py and check_review_queue_status.py scripts.

Usage:
    # Basic check (pending documents, field validation, ReviewService + GraphQL tests)
    python check_review_queue.py

    # Status overview (all indices, counts by status, sample documents)
    python check_review_queue.py --status

    # Verbose output (combines both views)
    python check_review_queue.py --verbose

    # Ingest a test article and verify it lands in the review queue
    python check_review_queue.py --test-ingest

    # Full diagnostic run
    python check_review_queue.py --verbose --test-ingest
"""
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, '/app')
sys.path.insert(0, str(Path(__file__).parent.parent))

from elasticsearch import Elasticsearch
from app.config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_es_client():
    """Create and validate an Elasticsearch client."""
    es_client = Elasticsearch(hosts=[settings.elasticsearch_url])
    if not es_client.ping():
        logger.error("Cannot connect to Elasticsearch")
        sys.exit(1)
    logger.info("Connected to Elasticsearch")
    return es_client


def check_index_overview(es_client):
    """Check the current state of all Elasticsearch indices (from check_review_queue_status)."""
    logger.info("\n" + "=" * 60)
    logger.info("INDEX OVERVIEW")
    logger.info("=" * 60)

    indices = {
        'content': settings.content_index,
        'review': settings.review_index,
    }

    for name, index in indices.items():
        if es_client.indices.exists(index=index):
            count = es_client.count(index=index)['count']
            logger.info(f"  {name} index exists: {index} ({count} documents)")

            # Show sample documents if any exist
            if count > 0:
                response = es_client.search(
                    index=index,
                    body={'size': 3, 'sort': [{'_doc': 'desc'}]}
                )
                logger.info(f"  Sample documents in {name}:")
                for hit in response['hits']['hits']:
                    doc = hit['_source']
                    if name == 'content':
                        logger.info(
                            f"    - {doc.get('title', 'No title')[:50]}... "
                            f"(score: {doc.get('final_score', 0):.2f})"
                        )
                    else:
                        logger.info(
                            f"    - {doc.get('title', 'No title')[:50]}... "
                            f"(status: {doc.get('status', 'unknown')})"
                        )
        else:
            logger.warning(f"  {name} index does not exist: {index}")

    # Count review queue items by status
    if es_client.indices.exists(index=settings.review_index):
        logger.info("\n  Review queue breakdown:")
        for status in ['pending', 'approved', 'rejected']:
            response = es_client.count(
                index=settings.review_index,
                body={'query': {'term': {'status': status}}}
            )
            logger.info(f"    {status}: {response['count']} items")


def check_review_queue_details(es_client):
    """Detailed review queue check with field validation (from check_review_queue)."""
    logger.info("\n" + "=" * 60)
    logger.info("REVIEW QUEUE DETAILS")
    logger.info("=" * 60)
    logger.info(f"Review index: {settings.review_index}")

    # Check if review queue index exists
    if not es_client.indices.exists(index=settings.review_index):
        logger.error(f"Review queue index '{settings.review_index}' does not exist!")
        return

    # Count total documents
    count_response = es_client.count(index=settings.review_index)
    total_docs = count_response['count']
    logger.info(f"Total documents in review queue: {total_docs}")

    if total_docs == 0:
        logger.warning("No documents in review queue")
        return

    # Count by status (aggregation)
    status_agg = {
        "size": 0,
        "aggs": {
            "by_status": {
                "terms": {"field": "status"}
            }
        }
    }
    status_response = es_client.search(index=settings.review_index, body=status_agg)
    logger.info("Documents by status:")
    for bucket in status_response['aggregations']['by_status']['buckets']:
        logger.info(f"  {bucket['key']}: {bucket['doc_count']}")

    # Get pending documents
    pending_query = {
        "size": 10,
        "query": {"term": {"status": "pending"}},
        "sort": [
            {"priority": {"order": "desc"}},
            {"submitted_date": {"order": "asc"}}
        ]
    }
    pending_response = es_client.search(index=settings.review_index, body=pending_query)
    pending_count = pending_response['hits']['total']['value']
    logger.info(f"\nPending documents: {pending_count}")

    if pending_count > 0:
        logger.info("\nFirst 3 pending documents:")
        for i, hit in enumerate(pending_response['hits']['hits'][:3], 1):
            doc = hit['_source']
            logger.info(f"\n{i}. Document ID: {hit['_id']}")
            logger.info(f"   Title: {doc.get('title', 'N/A')[:80]}...")
            logger.info(f"   Content Type: {doc.get('content_type', 'N/A')}")
            logger.info(f"   Source: {doc.get('source', 'N/A')}")
            logger.info(f"   Status: {doc.get('status', 'N/A')}")
            logger.info(f"   Priority: {doc.get('priority', 'N/A')}")
            logger.info(f"   ML Score: {doc.get('ml_score', 0):.3f}")

            # Check v3 fields
            logger.info("   v3 Fields:")
            logger.info(f"   - ai_confidence: {doc.get('ai_confidence', 'MISSING')}")
            logger.info(f"   - final_score: {doc.get('final_score', 'MISSING')}")
            logger.info(f"   - categories: {doc.get('categories', 'MISSING')}")
            logger.info(f"   - ai_summary: {'Present' if doc.get('ai_summary') else 'MISSING'}")

            # Check if old fields still exist
            old_fields_present = {
                f: doc[f] for f in ['gpt_score', 'combined_score', 'predicted_categories', 'gpt_reasoning']
                if f in doc
            }
            if old_fields_present:
                logger.warning("   Old fields still present:")
                for field, value in old_fields_present.items():
                    display = 'Present' if field == 'gpt_reasoning' else value
                    logger.warning(f"   - {field}: {display}")

            # Check required fields
            logger.info("   Required fields check:")
            required_fields = ['id', 'title', 'content_type', 'ml_score', 'status', 'submitted_date']
            for field in required_fields:
                if field == 'id':
                    logger.info(f"   - {field}: OK (in _id)")
                elif field in doc:
                    logger.info(f"   - {field}: OK")
                else:
                    logger.error(f"   - {field}: MISSING")


def test_review_service(es_client):
    """Test the ReviewService integration."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing ReviewService.get_queue()...")
    logger.info("=" * 60)

    from app.services.review_service import ReviewService

    review_service = ReviewService(es_client)

    try:
        items = review_service.get_queue(status="pending", limit=5)
        logger.info(f"ReviewService returned {len(items)} items")

        if items:
            item = items[0]
            logger.info("First item from ReviewService:")
            logger.info(f"  ID: {item.id}")
            logger.info(f"  Title: {item.title[:80]}...")
            logger.info(f"  Content Type: {item.content_type}")
            logger.info(f"  ML Score: {item.ml_score:.3f}")
            logger.info(f"  AI Confidence: {item.ai_confidence:.3f}")
            logger.info(f"  Final Score: {item.final_score:.3f}")
            logger.info(f"  Categories: {item.categories}")
            logger.info(f"  Status: {item.status}")

            # Check if ReviewItem can be serialized
            try:
                item.dict()
                logger.info("ReviewItem can be serialized to dict")
            except Exception as e:
                logger.error(f"ReviewItem serialization error: {e}")

    except Exception as e:
        logger.error(f"ReviewService error: {e}")
        import traceback
        traceback.print_exc()


def test_graphql_endpoint():
    """Test the GraphQL endpoint for review queue queries."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing GraphQL endpoint...")
    logger.info("=" * 60)

    import requests

    graphql_query = {
        "query": """
            query GetReviewQueue {
                reviewQueue(status: "pending") {
                    id
                    title
                    contentType
                    mlScore
                    aiConfidence
                    finalScore
                    categories
                    status
                }
            }
        """
    }

    try:
        response = requests.post(
            "http://localhost:8000/graphql",
            json=graphql_query,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                logger.error(f"GraphQL errors: {data['errors']}")
            elif 'data' in data and 'reviewQueue' in data['data']:
                items = data['data']['reviewQueue']
                logger.info(f"GraphQL returned {len(items)} items")
                if items:
                    item = items[0]
                    logger.info("First item from GraphQL:")
                    logger.info(f"  ID: {item.get('id')}")
                    logger.info(f"  Title: {item.get('title', '')[:80]}...")
                    logger.info(f"  Categories: {item.get('categories')}")
            else:
                logger.warning(f"Unexpected GraphQL response: {data}")
        else:
            logger.error(f"GraphQL request failed: {response.status_code}")
            logger.error(f"Response: {response.text[:500]}")

    except Exception as e:
        logger.error(f"GraphQL request error: {e}")


def ingest_test_article(es_client):
    """Ingest a test article that should go to review queue (from check_review_queue_status)."""
    logger.info("\n" + "=" * 60)
    logger.info("INGESTING TEST ARTICLE")
    logger.info("=" * 60)

    from jobs.pipeline_orchestrator import ContentPipelineOrchestrator

    config = {
        'enable_pubmed': True,
        'enable_youtube': False,
        'enable_github': False,
        'enable_discourse': False,
        'enable_wiki': False,
        'enable_ai_enhancement': False,
        'auto_approve_threshold': 0.7,
        'use_advanced_classifier': True,
    }

    orchestrator = ContentPipelineOrchestrator(es_client=es_client, config=config)

    # Create a boundary case article (should go to review)
    test_article = {
        'pmid': '99999999',
        'title': 'Real-world evidence from electronic health records: A retrospective cohort study',
        'abstract': (
            'We conducted a retrospective cohort study using electronic health record data '
            'from 5 hospitals. Using propensity score matching, we compared outcomes between '
            'treated and untreated patients. This observational study demonstrates the value '
            'of real-world data for comparative effectiveness research.'
        ),
        'journal': 'Medical Informatics Journal',
        'year': 2023,
        'authors': [
            {'name': 'Smith J', 'affiliation': 'University Hospital'},
            {'name': 'Jones A', 'affiliation': 'Medical Center'},
        ],
        'keywords': ['electronic health records', 'real-world evidence', 'cohort study'],
        'source': 'pubmed',
        'content_type': 'article',
    }

    logger.info(f"Processing article: {test_article['title'][:50]}...")
    logger.info("This is a boundary case - observational study but no OHDSI tools")
    logger.info("Expected: Should go to review queue (score 0.3-0.7)")

    try:
        result = orchestrator._process_single_item(test_article)

        if result:
            logger.info("Article processed successfully")
            logger.info(f"  ML Score: {result.get('ml_score', 0):.3f}")
            logger.info(f"  AI Confidence: {result.get('ai_confidence', 0):.3f}")
            logger.info(f"  Final Score: {result.get('final_score', 0):.3f}")
            logger.info(f"  Approval Status: {result.get('approval_status', 'unknown')}")

            if result.get('approval_status') == 'pending_review':
                logger.info("  Correctly sent to review queue!")
            elif result.get('approval_status') == 'approved':
                logger.info("  Auto-approved (score too high)")
            else:
                logger.info(f"  Status: {result.get('approval_status')}")
        else:
            logger.error("Processing failed - no result returned")

    except Exception as e:
        logger.error(f"Error processing article: {e}")
        import traceback
        traceback.print_exc()

    # Check review queue after processing
    logger.info("\nChecking review queue after processing...")

    response = es_client.search(
        index=settings.review_index,
        body={
            'query': {'match': {'title': 'Real-world evidence electronic health'}},
            'size': 1,
        }
    )

    if response['hits']['total']['value'] > 0:
        logger.info("Article found in review queue!")
        doc = response['hits']['hits'][0]['_source']
        logger.info(f"  Status: {doc.get('status')}")
        logger.info(f"  Score: {doc.get('ml_score', 0):.3f}")
    else:
        logger.warning("Article not found in review queue")

        # Check if it went to content index instead
        response = es_client.search(
            index=settings.content_index,
            body={
                'query': {'match': {'title': 'Real-world evidence electronic health'}},
                'size': 1,
            }
        )

        if response['hits']['total']['value'] > 0:
            logger.info("Article was auto-approved and is in content index")
            doc = response['hits']['hits'][0]['_source']
            logger.info(f"  Final Score: {doc.get('final_score', 0):.3f}")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Check the OHDSI review queue and diagnose issues."
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show index overview with sample documents and status counts.',
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show both the index overview and detailed queue diagnostics.',
    )
    parser.add_argument(
        '--test-ingest',
        action='store_true',
        help='Ingest a test article and verify it lands in the review queue.',
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    es_client = get_es_client()

    if args.status or args.verbose:
        check_index_overview(es_client)

    if not args.status or args.verbose:
        # Default path: detailed queue check + service tests
        check_review_queue_details(es_client)
        test_review_service(es_client)
        test_graphql_endpoint()

    if args.test_ingest:
        ingest_test_article(es_client)
        # Show final state after ingestion
        logger.info("\n" + "=" * 60)
        logger.info("FINAL STATUS")
        logger.info("=" * 60)
        check_index_overview(es_client)


if __name__ == "__main__":
    main()
