#!/usr/bin/env python3
"""
Update missing citations for articles in Elasticsearch.

This script fetches enriched citations from PubMed for articles that:
1. Have no citations field
2. Have empty citation arrays

Usage:
    docker-compose exec backend python /app/scripts/update_missing_citations.py
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
import time

from elasticsearch import Elasticsearch, helpers
from jobs.article_classifier.retriever import PubMedRetriever
from app.config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_articles_missing_citations(es: Elasticsearch, batch_size: int = 100) -> List[Dict]:
    """
    Find articles that have no citations or empty citation arrays.
    """
    articles_missing_citations = []
    
    # Query for all articles
    query = {
        'query': {
            'bool': {
                'must': [
                    {'term': {'content_type': 'article'}},
                    {'exists': {'field': 'pmid'}}
                ]
            }
        },
        'size': batch_size,
        '_source': ['pmid', 'title', 'citations', 'year']
    }
    
    # Use scroll API for large result sets
    response = es.search(
        index=settings.content_index,
        body=query,
        scroll='2m'
    )
    
    scroll_id = response['_scroll_id']
    hits = response['hits']['hits']
    
    while hits:
        for hit in hits:
            doc = hit['_source']
            pmid = doc.get('pmid')
            citations = doc.get('citations', {})
            
            # Check if citations are missing or empty
            cited_by = citations.get('cited_by', [])
            references = citations.get('references', [])
            similar = citations.get('similar', [])
            
            # Check if citations need updating
            needs_update = False
            
            # No citations at all
            if not citations:
                needs_update = True
            # All arrays are empty
            elif not cited_by and not references and not similar:
                needs_update = True
            # Citations exist but aren't enriched
            elif cited_by and not isinstance(cited_by[0] if cited_by else None, dict):
                needs_update = True
            
            if needs_update and pmid:
                articles_missing_citations.append({
                    'id': hit['_id'],
                    'pmid': pmid,
                    'title': doc.get('title', ''),
                    'year': doc.get('year'),
                    'has_citations': bool(citations),
                    'cited_by_count': len(cited_by),
                    'references_count': len(references)
                })
        
        # Get next batch
        response = es.scroll(scroll_id=scroll_id, scroll='2m')
        scroll_id = response['_scroll_id']
        hits = response['hits']['hits']
    
    # Clear scroll
    es.clear_scroll(scroll_id=scroll_id)
    
    return articles_missing_citations


def update_citations_batch(
    es: Elasticsearch,
    retriever: PubMedRetriever,
    articles: List[Dict],
    batch_size: int = 50
) -> Dict[str, int]:
    """
    Update citations for a batch of articles.
    """
    stats = {
        'updated': 0,
        'failed': 0,
        'no_citations': 0,
        'errors': 0
    }
    
    # Extract PMIDs
    pmids = [a['pmid'] for a in articles if a.get('pmid')]
    
    if not pmids:
        return stats
    
    logger.info(f"Fetching citations for {len(pmids)} articles...")
    
    try:
        # Fetch enriched citations
        citations = retriever.fetch_citations(pmids, fetch_metadata=True)
        
        # Prepare bulk update operations
        bulk_operations = []
        
        for article in articles:
            pmid = article['pmid']
            doc_id = article['id']
            
            if pmid in citations:
                citation_data = citations[pmid]
                
                # Check if we got any citations
                cited_by = citation_data.get('cited_by', [])
                references = citation_data.get('references', [])
                similar = citation_data.get('similar', [])
                
                if cited_by or references or similar:
                    # Prepare update
                    bulk_operations.append({
                        '_op_type': 'update',
                        '_index': settings.content_index,
                        '_id': doc_id,
                        'doc': {
                            'citations': citation_data,
                            'updated_at': datetime.utcnow().isoformat()
                        }
                    })
                    
                    logger.info(
                        f"✅ {pmid}: {len(cited_by)} cited_by, "
                        f"{len(references)} references, {len(similar)} similar"
                    )
                    stats['updated'] += 1
                else:
                    logger.debug(f"⚠️ {pmid}: No citations found")
                    stats['no_citations'] += 1
            else:
                logger.warning(f"❌ {pmid}: Failed to fetch citations")
                stats['failed'] += 1
        
        # Execute bulk update
        if bulk_operations:
            success, errors = helpers.bulk(
                es,
                bulk_operations,
                raise_on_error=False,
                stats_only=False
            )
            
            if errors:
                logger.error(f"Bulk update had {len(errors)} errors")
                stats['errors'] += len(errors)
                for error in errors[:5]:  # Log first 5 errors
                    logger.error(f"  Error: {error}")
            
            logger.info(f"Bulk updated {success} documents")
        
    except Exception as e:
        logger.error(f"Error fetching/updating citations: {e}")
        stats['errors'] += len(pmids)
    
    return stats


def main():
    """Main function to update missing citations."""
    
    print("\n" + "="*60)
    print("UPDATE MISSING CITATIONS")
    print("="*60)
    
    # Initialize Elasticsearch
    es = Elasticsearch(
        hosts=[settings.elasticsearch_url],
        timeout=30,
        max_retries=3,
        retry_on_timeout=True
    )
    
    # Initialize PubMed retriever
    retriever = PubMedRetriever()
    
    # Check connection
    if not es.ping():
        logger.error("Failed to connect to Elasticsearch")
        sys.exit(1)
    
    print(f"\n✅ Connected to Elasticsearch")
    print(f"📚 Index: {settings.content_index}")
    
    # Find articles missing citations
    print("\n[1/3] Finding articles with missing or empty citations...")
    articles_missing = get_articles_missing_citations(es)
    
    print(f"\n📊 Found {len(articles_missing)} articles needing citation updates")
    
    if not articles_missing:
        print("✨ All articles have citations!")
        return
    
    # Show sample
    print("\nSample of articles missing citations:")
    for article in articles_missing[:5]:
        print(f"  - {article['pmid']}: {article['title'][:50]}...")
        print(f"    Has citations: {article['has_citations']}, "
              f"Cited by: {article['cited_by_count']}, "
              f"References: {article['references_count']}")
    
    if len(articles_missing) > 5:
        print(f"  ... and {len(articles_missing) - 5} more")
    
    # Auto-confirm in batch mode
    print(f"\n🚀 Starting citation update for {len(articles_missing)} articles...")
    
    # Process in batches
    print("\n[2/3] Fetching and updating citations...")
    batch_size = 50
    total_stats = {
        'updated': 0,
        'failed': 0,
        'no_citations': 0,
        'errors': 0
    }
    
    for i in range(0, len(articles_missing), batch_size):
        batch = articles_missing[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(articles_missing) + batch_size - 1) // batch_size
        
        print(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} articles)...")
        
        # Process batch
        batch_stats = update_citations_batch(es, retriever, batch, batch_size)
        
        # Update totals
        for key, value in batch_stats.items():
            total_stats[key] += value
        
        # Rate limiting
        time.sleep(1)
    
    # Summary
    print("\n[3/3] Summary")
    print("="*60)
    print(f"✅ Successfully updated: {total_stats['updated']}")
    print(f"⚠️ No citations found: {total_stats['no_citations']}")
    print(f"❌ Failed to fetch: {total_stats['failed']}")
    print(f"⚠️ Update errors: {total_stats['errors']}")
    print(f"📊 Total processed: {len(articles_missing)}")
    
    # Verify a sample
    if total_stats['updated'] > 0:
        print("\n🔍 Verifying a sample update...")
        sample = articles_missing[0]
        result = es.get(index=settings.content_index, id=sample['id'])
        citations = result['_source'].get('citations', {})
        
        if citations:
            cited_by = citations.get('cited_by', [])
            if cited_by and isinstance(cited_by[0] if cited_by else None, dict):
                print(f"✅ Verification successful! Article {sample['pmid']} has enriched citations")
                print(f"   Example: {cited_by[0].get('title', '')[:60]}...")
            else:
                print(f"⚠️ Article {sample['pmid']} has citations but they're not enriched")
        else:
            print(f"❌ Article {sample['pmid']} still has no citations")
    
    print("\n✨ Citation update complete!")


if __name__ == "__main__":
    main()