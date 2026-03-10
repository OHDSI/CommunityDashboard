#!/usr/bin/env python3
"""
Verify that documents have enriched citations stored.

Usage:
    docker-compose exec backend python /app/scripts/verify_citations_enriched.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from elasticsearch import Elasticsearch
from app.config import settings
import random

def verify_citations():
    """Check random documents for enriched citations."""
    
    print("\n" + "="*60)
    print("CITATION ENRICHMENT VERIFICATION")
    print("="*60)
    
    es = Elasticsearch(hosts=[settings.elasticsearch_url])
    
    # Get total count
    total = es.count(index='ohdsi_content_v3')['count']
    print(f"\nTotal documents in index: {total}")
    
    # Search for documents that have citations field
    response = es.search(
        index='ohdsi_content_v3',
        body={
            'query': {
                'exists': {'field': 'citations.cited_by'}
            },
            'size': 100
        }
    )
    
    docs_with_citations = response['hits']['hits']
    print(f"Documents with citations field: {len(docs_with_citations)}")
    
    # Check how many have enriched citations
    enriched_count = 0
    plain_count = 0
    sample_enriched = []
    
    for hit in docs_with_citations:
        doc = hit['_source']
        citations = doc.get('citations', {})
        cited_by = citations.get('cited_by', [])
        
        if cited_by:
            # Check if enriched (has metadata) or plain (just PMIDs)
            if isinstance(cited_by[0], dict) and 'title' in cited_by[0]:
                enriched_count += 1
                if len(sample_enriched) < 5:
                    sample_enriched.append({
                        'id': hit['_id'],
                        'pmid': doc.get('pmid', 'N/A'),
                        'title': doc.get('title', '')[:60],
                        'cited_by_count': len(cited_by),
                        'first_citation': cited_by[0].get('title', '')[:60]
                    })
            else:
                plain_count += 1
    
    print(f"\nCitation Enrichment Status:")
    print(f"  ✅ Enriched citations: {enriched_count}")
    print(f"  ❌ Plain citations: {plain_count}")
    print(f"  Enrichment rate: {enriched_count / (enriched_count + plain_count) * 100:.1f}%" if (enriched_count + plain_count) > 0 else "N/A")
    
    if sample_enriched:
        print(f"\nSample of documents with enriched citations:")
        for i, doc in enumerate(sample_enriched, 1):
            print(f"\n  {i}. Document ID: {doc['id']}")
            print(f"     PMID: {doc['pmid']}")
            print(f"     Title: {doc['title']}...")
            print(f"     Cited by: {doc['cited_by_count']} articles")
            print(f"     First citation: {doc['first_citation']}...")
    
    # Check documents without any citations
    no_citations = es.search(
        index='ohdsi_content_v3',
        body={
            'query': {
                'bool': {
                    'must_not': [
                        {'exists': {'field': 'citations.cited_by'}}
                    ]
                }
            },
            'size': 0
        }
    )
    
    docs_without_citations = no_citations['hits']['total']['value']
    print(f"\nDocuments without citations: {docs_without_citations}")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total documents: {total}")
    print(f"With enriched citations: {enriched_count}")
    print(f"With plain citations: {plain_count}")
    print(f"Without citations: {docs_without_citations}")
    
    if enriched_count > 0:
        print("\n✅ Citation enrichment is working!")
    else:
        print("\n❌ No enriched citations found")

if __name__ == "__main__":
    verify_citations()