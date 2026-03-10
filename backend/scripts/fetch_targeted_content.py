#!/usr/bin/env python3
"""
Targeted content fetch - smaller, focused queries for testing the pipeline.
"""
import sys
import json
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, '/app')

from elasticsearch import Elasticsearch
from app.config import settings
from jobs.pipeline_orchestrator import ContentPipelineOrchestrator

def main():
    """Fetch a small amount of targeted content."""
    print("="*70)
    print("TARGETED CONTENT FETCH - Testing Pipeline Flow")
    print("="*70)
    
    # Initialize Elasticsearch
    es_client = Elasticsearch(hosts=[settings.elasticsearch_url])
    
    if not es_client.ping():
        print("❌ Cannot connect to Elasticsearch")
        return False
    
    print("✅ Connected to Elasticsearch")
    
    # Get initial counts
    initial_content = es_client.count(index=settings.content_index)['count']
    initial_review = es_client.count(
        index=settings.review_index,
        body={"query": {"term": {"status": "pending"}}}
    )['count']
    
    print(f"\n📊 Initial Counts:")
    print(f"  Content: {initial_content}")
    print(f"  Review Queue (pending): {initial_review}")
    
    # Initialize orchestrator with specific settings
    config = {
        'enable_pubmed': True,
        'enable_youtube': False,  # No API key
        'enable_github': True,
        'enable_discourse': False,  # Skip for speed
        'enable_wiki': False,  # Skip for speed
        'enable_ai_enhancement': False,  # Disable for speed
        'enable_relationships': False,
        'auto_approve_threshold': 0.8,  # Higher threshold to get more in review
        'batch_size': 5
    }
    
    orchestrator = ContentPipelineOrchestrator(
        es_client=es_client,
        config=config
    )
    
    print("\n🔍 Fetching targeted content...")
    
    # 1. Try PubMed with very specific recent query
    print("\n📚 Fetching from PubMed...")
    try:
        from jobs.article_classifier.retriever import ArticleRetriever
        retriever = ArticleRetriever()
        
        # Very specific queries likely to return new content
        queries = [
            '"OHDSI" AND "2024"[Publication Date]',
            '"OMOP" AND "network study" AND "2024"[Publication Date]',
            'Hripcsak G[Author] AND "2024"[Publication Date]'
        ]
        
        all_pmids = []
        for query in queries:
            print(f"  Query: {query}")
            pmids = retriever.search_pubmed(query, max_results=3)
            if pmids:
                print(f"    Found {len(pmids)} articles: {pmids}")
                all_pmids.extend(pmids)
            else:
                print(f"    No results")
        
        if all_pmids:
            # Remove duplicates
            unique_pmids = list(set(all_pmids))
            print(f"\n  Fetching details for {len(unique_pmids)} unique articles...")
            
            # Fetch full details
            articles = retriever.fetch_article_details(unique_pmids[:5])  # Limit to 5
            
            if articles:
                print(f"  Processing {len(articles)} articles through pipeline...")
                
                # Add source metadata
                for article in articles:
                    article['source'] = 'pubmed'
                
                # Process through pipeline
                processed = orchestrator._process_content_batch(articles)
                
                print(f"  ✅ Processed {len(processed)} articles")
                
                # Check what happened to each
                for item in processed:
                    if 'title' in item:
                        print(f"    - {item['title'][:50]}...")
                        if item.get('indexed'):
                            print(f"      Status: {item.get('approval_status', 'unknown')}")
                            
    except Exception as e:
        print(f"  ❌ PubMed error: {e}")
        import traceback
        traceback.print_exc()
    
    # 2. Try GitHub with very recent repos
    print("\n💻 Fetching from GitHub...")
    try:
        from jobs.github_scanner.scanner import GitHubScanner
        scanner = GitHubScanner()
        
        # Search for very recent OHDSI repos
        query = 'OHDSI created:>2024-06-01 stars:>0'
        print(f"  Query: {query}")
        
        repos = scanner.search(query, max_results=5)
        
        if repos:
            print(f"  Found {len(repos)} repositories")
            
            # Add source metadata
            for repo in repos:
                repo['source'] = 'github'
            
            # Process through pipeline
            processed = orchestrator._process_content_batch(repos)
            
            print(f"  ✅ Processed {len(processed)} repositories")
            
    except Exception as e:
        print(f"  ❌ GitHub error: {e}")
    
    # Final counts
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    
    final_content = es_client.count(index=settings.content_index)['count']
    final_review = es_client.count(
        index=settings.review_index,
        body={"query": {"term": {"status": "pending"}}}
    )['count']
    
    print(f"\n📊 Final Counts:")
    print(f"  Content: {final_content} (change: {final_content - initial_content:+d})")
    print(f"  Review Queue: {final_review} (change: {final_review - initial_review:+d})")
    
    # Show what's in the review queue
    if final_review > initial_review:
        print(f"\n✅ Successfully added {final_review - initial_review} items to review queue!")
        
        # Show the new items
        print("\n📋 New items in review queue:")
        query = {
            'size': 5,
            'query': {'term': {'status': 'pending'}},
            'sort': [{'submitted_date': {'order': 'desc'}}]
        }
        
        response = es_client.search(index=settings.review_index, body=query)
        
        for hit in response['hits']['hits']:
            doc = hit['_source']
            print(f"  - {doc.get('title', 'No title')[:60]}...")
            print(f"    Score: {doc.get('final_score', 0):.3f}, Source: {doc.get('source')}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)