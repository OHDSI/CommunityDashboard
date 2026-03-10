#!/usr/bin/env python3
"""
Fetch new OHDSI content with wider search parameters.
This script uses broader queries and date filters to find recent content.
"""
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add the app directory to the path
sys.path.insert(0, '/app')

from elasticsearch import Elasticsearch
from app.config import settings
from jobs.pipeline_orchestrator import ContentPipelineOrchestrator

def get_existing_ids(es_client) -> set:
    """Get all existing content IDs to help identify new content."""
    existing_ids = set()
    
    # Get from content index
    try:
        response = es_client.search(
            index=settings.content_index,
            body={
                "size": 10000,
                "_source": ["source_id", "pmid", "url"],
                "query": {"match_all": {}}
            }
        )
        for hit in response['hits']['hits']:
            doc = hit['_source']
            if 'pmid' in doc:
                existing_ids.add(doc['pmid'])
            if 'source_id' in doc:
                existing_ids.add(doc['source_id'])
            if 'url' in doc:
                existing_ids.add(doc['url'])
    except Exception as e:
        print(f"Error getting existing IDs: {e}")
    
    print(f"📊 Found {len(existing_ids)} existing content items")
    return existing_ids

def fetch_recent_pubmed(orchestrator, max_items=50) -> List[Dict]:
    """Fetch recent PubMed articles with expanded queries."""
    print("\n🔬 Fetching recent PubMed articles...")
    
    try:
        from jobs.article_classifier.retriever import ArticleRetriever
        retriever = ArticleRetriever()
        
        # Expanded search queries for broader coverage
        queries = [
            # Core OHDSI terms
            'OHDSI',
            '"Observational Health Data Sciences and Informatics"',
            '"OMOP CDM" OR "OMOP Common Data Model"',
            
            # OHDSI tools
            'Atlas OHDSI',
            'HADES OHDSI',
            'Achilles OHDSI',
            '"Data Quality Dashboard" OHDSI',
            'WebAPI OHDSI',
            
            # Network studies
            'OHDSI network study',
            'OHDSI collaborative',
            'OHDSI consortium',
            
            # Specific research areas
            'OHDSI COVID',
            'OHDSI vaccine',
            'OHDSI drug safety',
            'OHDSI phenotype',
            
            # Recent conferences
            'OHDSI symposium 2024',
            'OHDSI Europe 2024',
            
            # Key authors (top OHDSI contributors)
            'Hripcsak G[Author] AND OHDSI',
            'Ryan PB[Author] AND OHDSI',
            'Rijnbeek PR[Author] AND OHDSI',
            'Suchard MA[Author] AND OHDSI'
        ]
        
        all_articles = []
        seen_pmids = set()
        
        for query in queries:
            print(f"  Searching: {query[:50]}...")
            try:
                # Search with date filter for recent content
                pmids = retriever.search_pubmed(
                    query=query,
                    max_results=10,  # Smaller per query to get variety
                    min_date='2024/01/01'  # Focus on 2024 content
                )
                
                # Filter out duplicates
                new_pmids = [p for p in pmids if p not in seen_pmids]
                if new_pmids:
                    print(f"    Found {len(new_pmids)} new PMIDs")
                    seen_pmids.update(new_pmids)
                    
                    # Fetch full details
                    articles = retriever.fetch_article_details(new_pmids)
                    
                    # Add citation data
                    citations = retriever.fetch_citations(new_pmids, fetch_metadata=True)
                    for article in articles:
                        pmid = article.get('pmid')
                        if pmid in citations:
                            article['citations'] = citations[pmid]
                    
                    all_articles.extend(articles)
                    
            except Exception as e:
                print(f"    Error with query '{query}': {e}")
                continue
        
        print(f"  Total articles found: {len(all_articles)}")
        return all_articles[:max_items]
        
    except Exception as e:
        print(f"  Error fetching PubMed: {e}")
        return []

def fetch_recent_github(orchestrator, max_items=30) -> List[Dict]:
    """Fetch recent GitHub repositories."""
    print("\n💻 Fetching recent GitHub repositories...")
    
    try:
        from jobs.github_scanner.scanner import GitHubScanner
        scanner = GitHubScanner()
        
        all_repos = []
        
        # Search queries focused on recent OHDSI activity
        search_queries = [
            'OHDSI created:>2024-01-01',
            'OMOP CDM created:>2024-01-01',
            'Atlas OHDSI pushed:>2024-01-01',
            'HADES language:R created:>2023-06-01',
            'DataQualityDashboard pushed:>2024-01-01',
            'PhenotypeLibrary created:>2023-01-01',
            'CohortDiagnostics pushed:>2024-01-01'
        ]
        
        for query in search_queries:
            print(f"  Searching: {query}")
            try:
                repos = scanner.search(
                    query=query,
                    max_results=10,
                    filters={'sort': 'updated', 'order': 'desc'}
                )
                all_repos.extend(repos)
            except Exception as e:
                print(f"    Error: {e}")
        
        # Also get repos from OHDSI organizations
        for org in ['OHDSI', 'OHDSI-Studies']:
            print(f"  Fetching from org: {org}")
            try:
                org_repos = scanner.fetch_org_repositories(
                    org_name=org,
                    max_results=15
                )
                all_repos.extend(org_repos)
            except Exception as e:
                print(f"    Error: {e}")
        
        # Deduplicate by repo name
        unique_repos = {}
        for repo in all_repos:
            name = repo.get('name') or repo.get('full_name')
            if name and name not in unique_repos:
                unique_repos[name] = repo
        
        print(f"  Total unique repos found: {len(unique_repos)}")
        return list(unique_repos.values())[:max_items]
        
    except Exception as e:
        print(f"  Error fetching GitHub: {e}")
        return []

def fetch_recent_discourse(orchestrator, max_items=30) -> List[Dict]:
    """Fetch recent Discourse discussions."""
    print("\n💬 Fetching recent Discourse discussions...")
    
    try:
        from jobs.discourse_fetcher.fetcher import DiscourseFetcher
        fetcher = DiscourseFetcher()
        
        all_topics = []
        
        # Fetch from key categories
        categories = [
            'announcements',
            'researchers', 
            'implementers',
            'developers',
            'study-questions'
        ]
        
        for category in categories:
            print(f"  Fetching from category: {category}")
            try:
                topics = fetcher.fetch_category_topics(
                    category_slug=category,
                    max_topics=10
                )
                all_topics.extend(topics)
            except Exception as e:
                print(f"    Error: {e}")
        
        # Also get latest overall topics
        print("  Fetching latest topics...")
        try:
            latest = fetcher.fetch_latest_topics(max_topics=20)
            all_topics.extend(latest)
        except Exception as e:
            print(f"    Error: {e}")
        
        # Deduplicate by topic ID
        unique_topics = {}
        for topic in all_topics:
            topic_id = topic.get('id')
            if topic_id and topic_id not in unique_topics:
                unique_topics[topic_id] = topic
        
        print(f"  Total unique topics found: {len(unique_topics)}")
        return list(unique_topics.values())[:max_items]
        
    except Exception as e:
        print(f"  Error fetching Discourse: {e}")
        return []

def main():
    """Main entry point for wider content search."""
    print("="*70)
    print("OHDSI CONTENT WIDER SEARCH - Finding New Content")
    print("="*70)
    
    # Initialize Elasticsearch
    es_client = Elasticsearch(hosts=[settings.elasticsearch_url])
    
    if not es_client.ping():
        print("❌ Cannot connect to Elasticsearch")
        return False
    
    print("✅ Connected to Elasticsearch")
    
    # Get existing content IDs
    existing_ids = get_existing_ids(es_client)
    
    # Initialize orchestrator with enhanced settings
    config = {
        'enable_pubmed': True,
        'enable_youtube': False,  # Skip if no API key
        'enable_github': True,
        'enable_discourse': True,
        'enable_wiki': True,
        'enable_ai_enhancement': False,  # Disable for speed
        'enable_relationships': False,
        'auto_approve_threshold': 0.75,  # Slightly higher to get more in review
        'batch_size': 10
    }
    
    orchestrator = ContentPipelineOrchestrator(
        es_client=es_client,
        config=config
    )
    
    # Track what we fetch
    all_content = []
    
    # 1. Fetch PubMed articles
    pubmed_articles = fetch_recent_pubmed(orchestrator, max_items=30)
    if pubmed_articles:
        print(f"✅ Got {len(pubmed_articles)} PubMed articles")
        for article in pubmed_articles:
            article['source'] = 'pubmed'
        all_content.extend(pubmed_articles)
    
    # 2. Fetch GitHub repos
    github_repos = fetch_recent_github(orchestrator, max_items=20)
    if github_repos:
        print(f"✅ Got {len(github_repos)} GitHub repositories")
        for repo in github_repos:
            repo['source'] = 'github'
        all_content.extend(github_repos)
    
    # 3. Fetch Discourse topics
    discourse_topics = fetch_recent_discourse(orchestrator, max_items=20)
    if discourse_topics:
        print(f"✅ Got {len(discourse_topics)} Discourse topics")
        for topic in discourse_topics:
            topic['source'] = 'discourse'
        all_content.extend(discourse_topics)
    
    print(f"\n📊 Total content fetched: {len(all_content)}")
    
    if not all_content:
        print("⚠️ No content fetched")
        return False
    
    # Process through the pipeline
    print("\n🔄 Processing content through pipeline...")
    
    # Process in smaller batches
    batch_size = 10
    total_processed = 0
    total_indexed = 0
    total_review = 0
    total_approved = 0
    
    for i in range(0, len(all_content), batch_size):
        batch = all_content[i:i+batch_size]
        print(f"\n  Processing batch {i//batch_size + 1} ({len(batch)} items)...")
        
        try:
            # Process through the pipeline
            processed = orchestrator._process_content_batch(batch)
            total_processed += len(processed)
            
            # Check results
            for item in processed:
                if item.get('indexed'):
                    total_indexed += 1
                    if item.get('approval_status') == 'approved':
                        total_approved += 1
                    elif item.get('status') == 'pending':
                        total_review += 1
                        
        except Exception as e:
            print(f"    Error processing batch: {e}")
            continue
    
    # Final statistics
    print("\n" + "="*70)
    print("FINAL RESULTS")
    print("="*70)
    
    print(f"📥 Total fetched: {len(all_content)}")
    print(f"⚙️ Total processed: {total_processed}")
    print(f"💾 Total indexed: {total_indexed}")
    print(f"✅ Auto-approved: {total_approved}")
    print(f"📋 Sent to review: {total_review}")
    
    # Check new counts
    print("\n📊 Checking updated counts...")
    
    try:
        content_count = es_client.count(index=settings.content_index)
        print(f"  Content index: {content_count['count']} documents")
        
        review_count = es_client.count(
            index=settings.review_index,
            body={"query": {"term": {"status": "pending"}}}
        )
        print(f"  Review queue (pending): {review_count['count']} documents")
        
    except Exception as e:
        print(f"  Error checking counts: {e}")
    
    print("\n✅ Wide search completed!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)