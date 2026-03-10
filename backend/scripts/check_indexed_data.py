#!/usr/bin/env python3
"""
Check what data was actually indexed in Elasticsearch.

Usage:
    docker-compose exec backend python /app/scripts/check_indexed_data.py
"""

import sys
from pathlib import Path
from elasticsearch import Elasticsearch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

def check_indexed_data():
    """Check the indexed documents for data quality."""
    
    es = Elasticsearch(hosts=[settings.elasticsearch_url])
    index = settings.content_index
    
    # Get total count
    total = es.count(index=index)['count']
    print(f"\nTotal documents in {index}: {total}")
    
    # Check documents with citations
    with_citations = es.count(
        index=index,
        body={"query": {"exists": {"field": "citations.cited_by"}}}
    )['count']
    print(f"Documents with citations field: {with_citations}")
    
    # Check for enriched citations (nested structure with title)
    try:
        enriched = es.count(
            index=index,
            body={
                "query": {
                    "nested": {
                        "path": "citations.cited_by",
                        "query": {
                            "exists": {"field": "citations.cited_by.title"}
                        }
                    }
                }
            }
        )['count']
        print(f"Documents with enriched citations: {enriched}")
    except:
        print("Could not check for enriched citations (nested query failed)")
    
    # Get sample documents
    print("\n" + "="*60)
    print("SAMPLE DOCUMENTS")
    print("="*60)
    
    result = es.search(
        index=index,
        body={
            "size": 3,
            "_source": ["pmid", "title", "authors", "citations"],
            "query": {"match_all": {}}
        }
    )
    
    for i, hit in enumerate(result['hits']['hits'], 1):
        doc = hit['_source']
        print(f"\n{i}. Document ID: {hit['_id']}")
        print(f"   PMID: {doc.get('pmid', 'N/A')}")
        print(f"   Title: {doc.get('title', 'N/A')[:60]}...")
        
        # Check authors
        authors = doc.get('authors', [])
        if authors:
            if isinstance(authors[0], dict):
                print(f"   Authors: {len(authors)} (structured)")
                if 'first_name' in authors[0]:
                    print(f"     Example: {authors[0].get('first_name', '')} {authors[0].get('last_name', '')}")
                else:
                    print(f"     Example: {authors[0].get('name', '')}")
            else:
                print(f"   Authors: {len(authors)} (string format)")
        else:
            print("   Authors: None")
        
        # Check citations
        citations = doc.get('citations', {})
        cited_by = citations.get('cited_by', [])
        references = citations.get('references', [])
        
        print(f"   Citations:")
        print(f"     - Cited by: {len(cited_by)} articles")
        print(f"     - References: {len(references)} articles")
        
        if cited_by and len(cited_by) > 0:
            first_cite = cited_by[0]
            if isinstance(first_cite, dict):
                print(f"     - First citation (enriched): {first_cite.get('title', 'No title')[:40]}...")
            else:
                print(f"     - First citation (PMID only): {first_cite}")
    
    # Check PMID format
    print("\n" + "="*60)
    print("PMID FORMAT CHECK")
    print("="*60)
    
    # Check for PMIDs with prefix
    with_prefix = es.count(
        index=index,
        body={
            "query": {
                "wildcard": {
                    "pmid": "PMID*"
                }
            }
        }
    )['count']
    
    without_prefix = es.count(
        index=index,
        body={
            "query": {
                "regexp": {
                    "pmid": "[0-9]+"
                }
            }
        }
    )['count']
    
    print(f"PMIDs with 'PMID' prefix: {with_prefix}")
    print(f"PMIDs without prefix (numbers only): {without_prefix}")
    
    # Show specific examples
    if with_prefix > 0:
        result = es.search(
            index=index,
            body={
                "size": 2,
                "_source": ["pmid"],
                "query": {"wildcard": {"pmid": "PMID*"}}
            }
        )
        print("\nExamples with prefix:")
        for hit in result['hits']['hits']:
            print(f"  - {hit['_source']['pmid']}")


if __name__ == "__main__":
    check_indexed_data()