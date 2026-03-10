#!/usr/bin/env python3
"""
Ingest training data - true positive OHDSI articles with enriched citations.
This script loads approximately 700 known OHDSI articles and processes them through the pipeline.

Usage:
    docker-compose exec backend python /app/scripts/ingest_training_data.py
    
Options:
    --batch-size: Number of articles to process at once (default: 20)
    --skip-ai: Skip AI enhancement for faster processing
"""

import os
import sys
import logging
import bibtexparser
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from elasticsearch import Elasticsearch
from app.config import settings
from jobs.pipeline_orchestrator import ContentPipelineOrchestrator
from jobs.article_classifier.retriever import PubMedRetriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_bibtex_file(filepath: str) -> List[Dict[str, Any]]:
    """Load articles from BibTeX file."""
    logger.info(f"Loading BibTeX file: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)
    
    articles = []
    for entry in bib_database.entries:
        # Convert BibTeX entry to article format
        # Extract PMID - remove 'PMID' prefix if present
        pmid = entry.get('pmid', entry.get('ID', ''))
        if pmid.startswith('PMID'):
            pmid = pmid[4:]  # Remove 'PMID' prefix for API calls
        
        # Parse authors properly - handle both semicolon and 'and' separators
        author_string = entry.get('author', '')
        if ';' in author_string:
            author_list = author_string.split(';')
        else:
            author_list = author_string.split(' and ')
        
        authors = []
        for i, author_name in enumerate(author_list):
            author_name = author_name.strip()
            if author_name:
                # Parse "LastName, FirstName" or "FirstName LastName" format
                if ',' in author_name:
                    parts = author_name.split(',', 1)
                    last_name = parts[0].strip()
                    first_name = parts[1].strip() if len(parts) > 1 else ''
                else:
                    # Assume last word is last name
                    parts = author_name.rsplit(' ', 1)
                    if len(parts) == 2:
                        first_name = parts[0].strip()
                        last_name = parts[1].strip()
                    else:
                        first_name = ''
                        last_name = author_name
                
                authors.append({
                    'name': author_name,
                    'first_name': first_name,
                    'last_name': last_name,
                    'position': i + 1
                })
        
        article = {
            'pmid': pmid,
            'title': entry.get('title', ''),
            'abstract': entry.get('abstract', ''),
            'authors': authors,
            'journal': entry.get('journal', ''),
            'year': entry.get('year', ''),
            'doi': entry.get('doi', ''),
            'keywords': entry.get('keywords', '').split(';') if entry.get('keywords') else [],
            'source': 'pubmed',
            'content_type': 'article'
        }
        
        # DEBUG: Check what PMID we're storing
        if pmid.startswith('PMID'):
            logger.error(f"ERROR: PMID still has prefix after cleaning: {pmid}")
        else:
            logger.debug(f"PMID cleaned correctly: {pmid}")
        
        # Only add if we have at least a title and PMID
        if article['title'] and article['pmid']:
            articles.append(article)
    
    logger.info(f"Loaded {len(articles)} articles from BibTeX")
    return articles


def fetch_full_details(articles: List[Dict[str, Any]], batch_size: int = 10) -> List[Dict[str, Any]]:
    """Fetch full details including enriched citations for articles."""
    logger.info(f"Fetching full details for {len(articles)} articles")
    
    retriever = PubMedRetriever()
    enhanced_articles = []
    
    # Track statistics
    with_citations = 0
    with_enriched = 0
    replaced_count = 0
    
    # Create a mapping of PMIDs to original articles for merging
    pmid_to_article = {a['pmid']: a for a in articles if a.get('pmid')}
    
    # Process in batches to avoid overwhelming the API
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i+batch_size]
        pmids = [a['pmid'] for a in batch if a.get('pmid', '').isdigit()]
        
        if pmids:
            try:
                # Fetch full details from PubMed
                logger.info(f"Fetching details for batch {i//batch_size + 1} ({len(pmids)} articles)")
                detailed_articles = retriever.fetch_article_details(pmids)
                
                # Fetch citations WITH METADATA (enriched)
                logger.info(f"Fetching enriched citations for batch {i//batch_size + 1}")
                citations = retriever.fetch_citations(pmids, fetch_metadata=True)
                
                # Replace BibTeX data with enriched PubMed data
                for pubmed_article in detailed_articles:
                    pmid = pubmed_article.get('pmid')
                    if pmid:
                        # Start with original BibTeX article as base
                        original = pmid_to_article.get(pmid, {})
                        
                        # Replace with enriched PubMed data but preserve any BibTeX-only fields
                        # IMPORTANT: Don't let PubMed overwrite citations - we'll add them explicitly
                        pubmed_data_without_citations = {k: v for k, v in pubmed_article.items() if k != 'citations'}
                        enhanced_article = {
                            **original,  # Start with BibTeX data
                            **pubmed_data_without_citations,  # Override with PubMed data (except citations)
                        }
                        
                        # Add enriched citations - this MUST come after the merge to ensure they're not overwritten
                        if pmid in citations:
                            enhanced_article['citations'] = citations[pmid]
                            with_citations += 1
                            
                            # Check if citations are enriched
                            cited_by = citations[pmid].get('cited_by', [])
                            if cited_by and isinstance(cited_by[0], dict):
                                with_enriched += 1
                                logger.info(f"✅ Article {pmid} has {len(cited_by)} enriched citations")
                        else:
                            # Ensure we have at least an empty citations structure
                            enhanced_article['citations'] = {
                                'cited_by': [],
                                'references': [],
                                'similar': []
                            }
                            logger.debug(f"Article {pmid} has no citations")
                        
                        enhanced_articles.append(enhanced_article)
                        replaced_count += 1
                        
                        # Remove from batch to avoid duplicates
                        batch = [a for a in batch if a.get('pmid') != pmid]
                
            except Exception as e:
                logger.error(f"Error fetching batch {i//batch_size + 1}: {e}")
                # Fall back to original data for this batch
                pass
        
        # Add any remaining articles that weren't replaced
        enhanced_articles.extend(batch)
    
    logger.info(f"Enhanced {len(enhanced_articles)} articles with full details")
    logger.info(f"  - Replaced with PubMed data: {replaced_count}")
    logger.info(f"  - With citations: {with_citations}")
    logger.info(f"  - With enriched metadata: {with_enriched}")
    return enhanced_articles


def check_citation_mapping(es, index_name):
    """Check if index has proper enriched citation mapping."""
    try:
        mapping = es.indices.get_mapping(index=index_name)
        properties = mapping[index_name]['mappings'].get('properties', {})
        citations_mapping = properties.get('citations', {})
        
        if citations_mapping.get('type') == 'object':
            cited_by = citations_mapping.get('properties', {}).get('cited_by', {})
            if cited_by.get('type') == 'nested':
                cited_by_props = cited_by.get('properties', {})
                if 'title' in cited_by_props and 'year' in cited_by_props:
                    return True
        return False
    except:
        return False


def main():
    """Main function to ingest true positive articles with enriched citations."""
    
    print("\n" + "="*60)
    print("TRAINING DATA INGESTION")
    print("True Positive OHDSI Articles with Enriched Citations")
    print("="*60)
    
    # Path to the positive training data
    bibtex_path = "/app/jobs/article_classifier/data/enriched_articles_ohdsi_reformatted.bib"
    
    if not os.path.exists(bibtex_path):
        logger.error(f"BibTeX file not found: {bibtex_path}")
        sys.exit(1)
    
    # Initialize Elasticsearch
    es = Elasticsearch(
        hosts=[settings.elasticsearch_url],
        timeout=30,
        max_retries=3,
        retry_on_timeout=True
    )
    
    # Check if index has proper citation mapping
    index_name = settings.content_index
    if not check_citation_mapping(es, index_name):
        logger.warning(f"⚠️ {index_name} may not have proper enriched citation mapping")
        logger.warning("Run this first: docker-compose exec backend python /app/scripts/initialize_database.py")
        print("\nContinuing anyway, but citations may not be stored properly...\n")
    else:
        logger.info(f"✅ {index_name} has proper enriched citation mapping")
    
    # Check initial counts
    initial_count = es.count(index=index_name)['count']
    print(f"\nInitial content count in {index_name}: {initial_count}")
    
    # Load articles from BibTeX
    print("\n[1/4] Loading articles from BibTeX file...")
    articles = load_bibtex_file(bibtex_path)
    print(f"Loaded {len(articles)} articles")
    
    # Fetch full details including citations
    print("\n[2/4] Fetching full details and citations from PubMed...")
    enhanced_articles = fetch_full_details(articles, batch_size=20)
    
    # Configure pipeline
    config = {
        'enable_pubmed': False,  # We're manually providing articles
        'enable_youtube': False,
        'enable_github': False,
        'enable_discourse': False,
        'enable_wiki': False,
        
        'enable_ai_enhancement': True,
        'enable_relationships': True,
        'use_gpt': True,
        'gpt_model': 'gpt-4o-mini',
        'generate_embeddings': True,
        
        'auto_approve_threshold': 0.6,  # Lower threshold for known positives
        'priority_threshold': 0.4,
        
        'content_index': settings.content_index,
        'review_index': settings.review_index
    }
    
    # Initialize orchestrator
    print("\n[3/4] Processing articles through pipeline...")
    orchestrator = ContentPipelineOrchestrator(config=config)
    
    # Process articles through the full pipeline to ensure proper normalization
    # The pipeline will handle:
    # - Normalizing to unified schema
    # - Deduplication checking
    # - Quality scoring
    # - ML classification (even though these are known positives)
    # - AI enhancement (summaries, categories, relationships)
    # - Embedding generation
    # - Proper indexing with all required fields
    
    batch_size = 50
    total_indexed = 0
    total_duplicates = 0
    total_errors = 0
    
    for i in range(0, len(enhanced_articles), batch_size):
        batch = enhanced_articles[i:i+batch_size]
        batch_num = i//batch_size + 1
        total_batches = (len(enhanced_articles) + batch_size - 1) // batch_size
        
        print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} articles)...")
        
        processed = 0
        batch_indexed = 0
        batch_duplicates = 0
        batch_errors = 0
        
        for article in batch:
            try:
                # Ensure article has required fields for pipeline processing
                article['source'] = 'pubmed'
                article['content_type'] = 'article'
                
                # The orchestrator will:
                # 1. Normalize the content (ContentNormalizer)
                # 2. Check for duplicates (Deduplicator)
                # 3. Calculate quality score (QualityScorer)
                # 4. Classify with ML (UnifiedMLClassifier)
                # 5. Enhance with AI if enabled (AIEnhancer)
                # 6. Generate embeddings (AIEnhancer)
                # 7. Discover relationships (AIEnhancer)
                # 8. Route to appropriate queue (QueueManager)
                # 9. Index to Elasticsearch
                
                # Process through the complete pipeline
                results = orchestrator._process_content_batch([article])
                
                if results:
                    # results is a list of processed items
                    batch_indexed += len(results)
                    total_indexed += len(results)
                else:
                    # Empty list means it was a duplicate or error
                    batch_duplicates += 1
                    total_duplicates += 1
                    
                processed += 1
                
                # Log progress every 10 articles
                if processed % 10 == 0:
                    print(f"  Processed {processed}/{len(batch)} in current batch...")
                    
            except Exception as e:
                logger.error(f"Error processing article {article.get('pmid', 'unknown')}: {e}")
                total_errors += 1
                batch_errors += 1
        
        print(f"Batch {batch_num} complete: {batch_indexed} indexed, {batch_duplicates} duplicates, {batch_errors} errors")
    
    # Check final counts
    print("\n[4/4] Verifying results...")
    final_count = es.count(index=settings.content_index)['count']
    
    # Get articles with citations
    citation_count = es.count(
        index=settings.content_index,
        body={"query": {"exists": {"field": "citations.references"}}}
    )['count']
    
    # Get articles with embeddings
    embedding_count = es.count(
        index=settings.content_index,
        body={"query": {"exists": {"field": "embedding"}}}
    )['count']
    
    print("\n" + "="*60)
    print("INGESTION COMPLETE")
    print("="*60)
    print(f"Articles processed: {len(enhanced_articles)}")
    print(f"Successfully indexed: {total_indexed}")
    print(f"Duplicates found: {total_duplicates}")
    print(f"Errors: {total_errors}")
    print()
    print(f"Total content: {initial_count} → {final_count} (+{final_count - initial_count})")
    print(f"Documents with citations: {citation_count}")
    print(f"Documents with embeddings: {embedding_count}")
    
    # Get breakdown by source
    agg_response = es.search(
        index=settings.content_index,
        body={
            "size": 0,
            "aggs": {
                "by_source": {"terms": {"field": "source", "size": 10}},
                "pubmed_articles": {
                    "filter": {"term": {"source": "pubmed"}},
                    "aggs": {
                        "total": {"value_count": {"field": "_id"}}
                    }
                }
            }
        }
    )
    
    print("\nContent by source:")
    for bucket in agg_response['aggregations']['by_source']['buckets']:
        print(f"  {bucket['key']}: {bucket['doc_count']}")
    
    print("\n✅ Training data ingestion complete!")


if __name__ == "__main__":
    main()