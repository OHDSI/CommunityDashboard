#!/usr/bin/env python3
"""
Complete database reingest script for OHDSI Dashboard.
Wipes existing data and reingests with proper citation networks.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from app.config import settings
from jobs.article_classifier.retriever import PubMedRetriever
from jobs.pipeline_orchestrator import ContentPipelineOrchestrator
from bibtexparser import load as bib_load
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseReingestor:
    """Handles complete database wipe and reingest with proper citations."""
    
    def __init__(self):
        """Initialize the reingestor."""
        self.es = Elasticsearch(
            hosts=[settings.elasticsearch_url],
            timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        self.retriever = PubMedRetriever()
        self.content_index = settings.content_index
        self.review_index = settings.review_index
        
    def wipe_database(self, confirm: bool = False):
        """
        Wipe all content from Elasticsearch indices.
        
        Args:
            confirm: Must be True to actually wipe data
        """
        if not confirm:
            logger.error("Wipe not confirmed. Set confirm=True to proceed.")
            return False
            
        logger.warning("⚠️ WIPING ALL CONTENT FROM ELASTICSEARCH!")
        
        try:
            # Delete all documents from content index
            if self.es.indices.exists(index=self.content_index):
                result = self.es.delete_by_query(
                    index=self.content_index,
                    body={"query": {"match_all": {}}}
                )
                logger.info(f"Deleted {result['deleted']} documents from {self.content_index}")
            
            # Delete all documents from review index
            if self.es.indices.exists(index=self.review_index):
                result = self.es.delete_by_query(
                    index=self.review_index,
                    body={"query": {"match_all": {}}}
                )
                logger.info(f"Deleted {result['deleted']} documents from {self.review_index}")
            
            # Refresh indices
            self.es.indices.refresh(index=self.content_index)
            self.es.indices.refresh(index=self.review_index)
            
            logger.info("✅ Database wiped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error wiping database: {e}")
            return False
    
    def load_training_articles(self, bibtex_path: str) -> List[Dict]:
        """
        Load articles from BibTeX file.
        
        Args:
            bibtex_path: Path to BibTeX file
            
        Returns:
            List of article dictionaries
        """
        logger.info(f"Loading articles from {bibtex_path}")
        
        articles = []
        with open(bibtex_path, 'r', encoding='utf-8') as fh:
            parser = BibTexParser()
            parser.customization = convert_to_unicode
            db = parser.parse_file(fh)
        
        for entry in db.entries:
            # Extract PMID from ID field (format: PMID12345678)
            article_id = entry.get('ID', '')
            pmid = None
            
            if article_id.startswith('PMID'):
                pmid = article_id.replace('PMID', '')
            elif 'pmid' in entry:
                pmid = entry['pmid']
            
            if pmid:
                articles.append({
                    'pmid': pmid,
                    'title': entry.get('title', ''),
                    'abstract': entry.get('abstract', ''),
                    'year': entry.get('year', ''),
                    'doi': entry.get('doi', ''),
                    'keywords': entry.get('keywords', ''),
                    'author': entry.get('author', '')
                })
        
        logger.info(f"Loaded {len(articles)} articles with PMIDs")
        return articles
    
    def fetch_and_enrich_batch(self, articles: List[Dict], batch_size: int = 20) -> List[Dict]:
        """
        Fetch full details and citations for a batch of articles.
        
        Args:
            articles: List of article dicts with PMIDs
            batch_size: Batch size for API calls
            
        Returns:
            List of enriched articles
        """
        enhanced_articles = []
        pmids = [a['pmid'] for a in articles if a.get('pmid')]
        
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i+batch_size]
            batch_num = i//batch_size + 1
            total_batches = (len(pmids) + batch_size - 1) // batch_size
            
            logger.info(f"Fetching batch {batch_num}/{total_batches} ({len(batch_pmids)} articles)")
            
            try:
                # Fetch full article details
                detailed_articles = self.retriever.fetch_article_details(batch_pmids)
                
                # Fetch enriched citations with metadata
                citations = self.retriever.fetch_citations(batch_pmids, fetch_metadata=True)
                
                # Merge details and citations
                for article in detailed_articles:
                    pmid = article.get('pmid')
                    if pmid and pmid in citations:
                        article['citations'] = citations[pmid]
                        
                        # Log citation counts
                        cited_by = citations[pmid].get('cited_by', [])
                        references = citations[pmid].get('references', [])
                        logger.info(f"  PMID {pmid}: {len(cited_by)} citations, {len(references)} references")
                    
                    enhanced_articles.append(article)
                    
            except Exception as e:
                logger.error(f"Error fetching batch {batch_num}: {e}")
                continue
        
        return enhanced_articles
    
    def process_through_pipeline(self, articles: List[Dict]) -> Dict:
        """
        Process articles through the full enrichment pipeline.
        
        Args:
            articles: List of enriched articles
            
        Returns:
            Processing statistics
        """
        # Configure pipeline for true positives
        config = {
            'enable_pubmed': False,  # We're manually providing articles
            'enable_youtube': False,
            'enable_github': False,
            'enable_discourse': False,
            'enable_wiki': False,
            
            'enable_ai_enhancement': True,  # Enable AI enrichment
            'enable_relationships': True,
            'use_gpt': True,
            'gpt_model': 'gpt-4o-mini',
            'generate_embeddings': True,
            
            'auto_approve_threshold': 0.6,  # Lower threshold for known positives
            'priority_threshold': 0.4,
            
            'content_index': self.content_index,
            'review_index': self.review_index
        }
        
        logger.info("Initializing content pipeline orchestrator...")
        orchestrator = ContentPipelineOrchestrator(config=config)
        
        stats = {
            'total': len(articles),
            'indexed': 0,
            'duplicates': 0,
            'errors': 0
        }
        
        batch_size = 50
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i+batch_size]
            batch_num = i//batch_size + 1
            total_batches = (len(articles) + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} articles)")
            
            for article in batch:
                try:
                    # Ensure required fields
                    article['source'] = 'pubmed'
                    article['content_type'] = 'article'
                    
                    # Process through pipeline
                    results = orchestrator._process_content_batch([article])
                    
                    if results:
                        stats['indexed'] += len(results)
                    else:
                        stats['duplicates'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing article {article.get('pmid', 'unknown')}: {e}")
                    stats['errors'] += 1
        
        return stats
    
    def verify_citation_networks(self) -> Dict:
        """
        Verify that citation networks were properly created.
        
        Returns:
            Verification statistics
        """
        logger.info("Verifying citation networks...")
        
        # Count total documents
        total_count = self.es.count(index=self.content_index)['count']
        
        # Count documents with citations
        with_citations = self.es.count(
            index=self.content_index,
            body={
                "query": {
                    "exists": {
                        "field": "citations"
                    }
                }
            }
        )['count']
        
        # Sample some documents to check citation structure
        sample = self.es.search(
            index=self.content_index,
            body={
                "size": 5,
                "query": {
                    "exists": {
                        "field": "citations.cited_by"
                    }
                }
            }
        )
        
        sample_stats = []
        for hit in sample['hits']['hits']:
            doc = hit['_source']
            citations = doc.get('citations', {})
            cited_by = citations.get('cited_by', [])
            references = citations.get('references', [])
            
            # Check if citations have metadata
            has_metadata = False
            if cited_by and isinstance(cited_by[0], dict):
                has_metadata = 'title' in cited_by[0]
            
            sample_stats.append({
                'id': doc.get('pmid', doc.get('id')),
                'title': doc.get('title', '')[:50],
                'cited_by_count': len(cited_by),
                'references_count': len(references),
                'has_metadata': has_metadata
            })
        
        return {
            'total_documents': total_count,
            'documents_with_citations': with_citations,
            'percentage_with_citations': (with_citations / total_count * 100) if total_count > 0 else 0,
            'sample_documents': sample_stats
        }
    
    def run_full_reingest(self, bibtex_path: str = None, confirm_wipe: bool = False) -> Dict:
        """
        Run the complete reingest process.
        
        Args:
            bibtex_path: Path to BibTeX file with true positives
            confirm_wipe: Must be True to wipe existing data
            
        Returns:
            Complete statistics
        """
        start_time = datetime.now()
        
        print("\n" + "="*60)
        print("OHDSI DATABASE REINGEST")
        print("="*60)
        
        # Default path to training data
        if not bibtex_path:
            bibtex_path = "/app/jobs/article_classifier/data/enriched_articles_ohdsi_reformatted.bib"
        
        if not os.path.exists(bibtex_path):
            logger.error(f"BibTeX file not found: {bibtex_path}")
            return {'error': 'BibTeX file not found'}
        
        # Step 1: Wipe database
        if confirm_wipe:
            print("\n[Step 1/5] Wiping existing database...")
            if not self.wipe_database(confirm=True):
                return {'error': 'Failed to wipe database'}
        else:
            print("\n[Step 1/5] Skipping database wipe (confirm_wipe=False)")
        
        # Step 2: Load training articles
        print("\n[Step 2/5] Loading training articles...")
        articles = self.load_training_articles(bibtex_path)
        if not articles:
            return {'error': 'No articles loaded'}
        
        # Step 3: Fetch and enrich with citations
        print("\n[Step 3/5] Fetching full details and citations from PubMed...")
        enhanced_articles = self.fetch_and_enrich_batch(articles)
        print(f"Enhanced {len(enhanced_articles)} articles with citations")
        
        # Step 4: Process through pipeline
        print("\n[Step 4/5] Processing through enrichment pipeline...")
        process_stats = self.process_through_pipeline(enhanced_articles)
        
        # Step 5: Verify results
        print("\n[Step 5/5] Verifying citation networks...")
        verify_stats = self.verify_citation_networks()
        
        # Calculate total time
        elapsed = datetime.now() - start_time
        
        # Print summary
        print("\n" + "="*60)
        print("REINGEST COMPLETE")
        print("="*60)
        print(f"Time elapsed: {elapsed}")
        print(f"Articles processed: {process_stats['total']}")
        print(f"Successfully indexed: {process_stats['indexed']}")
        print(f"Duplicates skipped: {process_stats['duplicates']}")
        print(f"Errors: {process_stats['errors']}")
        print(f"\nDocuments with citations: {verify_stats['documents_with_citations']}/{verify_stats['total_documents']} " +
              f"({verify_stats['percentage_with_citations']:.1f}%)")
        
        if verify_stats['sample_documents']:
            print("\nSample documents with citations:")
            for doc in verify_stats['sample_documents']:
                print(f"  • {doc['title']}...")
                print(f"    Cited by: {doc['cited_by_count']}, References: {doc['references_count']}, " +
                      f"Has metadata: {doc['has_metadata']}")
        
        return {
            'elapsed_time': str(elapsed),
            'process_stats': process_stats,
            'verify_stats': verify_stats
        }


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Reingest OHDSI database with proper citations')
    parser.add_argument('--bibtex', type=str, 
                       default='/app/jobs/article_classifier/data/enriched_articles_ohdsi_reformatted.bib',
                       help='Path to BibTeX file with true positive articles')
    parser.add_argument('--wipe', action='store_true',
                       help='Wipe existing database before reingest')
    parser.add_argument('--confirm', action='store_true',
                       help='Confirm database wipe (required with --wipe)')
    
    args = parser.parse_args()
    
    if args.wipe and not args.confirm:
        print("\n⚠️ WARNING: --wipe requires --confirm to actually wipe the database")
        print("Run with: --wipe --confirm")
        sys.exit(1)
    
    reingestor = DatabaseReingestor()
    results = reingestor.run_full_reingest(
        bibtex_path=args.bibtex,
        confirm_wipe=(args.wipe and args.confirm)
    )
    
    if 'error' in results:
        logger.error(f"Reingest failed: {results['error']}")
        sys.exit(1)
    
    print("\n✅ Reingest completed successfully!")


if __name__ == "__main__":
    main()