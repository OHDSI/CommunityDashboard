#!/usr/bin/env python3
"""
Run training articles through the full pipeline with proper enrichment.
This script:
1. Clears existing indexes (optional)
2. Loads PMIDs from BibTeX training data
3. Fetches complete metadata using PubMedRetriever
4. Processes through full pipeline with ML classification and AI enhancement
5. Stores in Elasticsearch with proper schema
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import bibtexparser
from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import NotFoundError

# Import pipeline components
from jobs.article_classifier.retriever import PubMedRetriever
from jobs.pipeline_orchestrator import ContentPipelineOrchestrator
from jobs.shared.content_normalizer import ContentNormalizer
from jobs.shared.ml_classifier import UnifiedMLClassifier
from jobs.shared.ai_enhancer import AIEnhancer
from jobs.shared.utils.quality_scorer import QualityScorer
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TrainingDataPipelineRunner:
    """Run training articles through the full enrichment pipeline."""
    
    def __init__(self, clear_indexes: bool = False):
        """
        Initialize the pipeline runner.
        
        Args:
            clear_indexes: Whether to clear existing indexes before starting
        """
        self.clear_indexes = clear_indexes
        
        # Initialize Elasticsearch
        self.es_client = Elasticsearch(
            hosts=[settings.elasticsearch_url],
            timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        
        # Initialize pipeline orchestrator with full configuration
        self.pipeline_config = {
            'enable_pubmed': True,
            'enable_youtube': False,  # Only process PubMed articles
            'enable_github': False,
            'enable_discourse': False,
            'enable_wiki': False,
            'enable_ai_enhancement': True,
            'use_gpt': True,
            'gpt_model': 'gpt-4o-mini',
            'generate_embeddings': True,
            'auto_approve_threshold': 0.7,  # Training data should score high
            'priority_threshold': 0.5,
            'similarity_threshold': 0.85,
            'batch_size': 10,
            'content_index': settings.content_index,
            'review_index': settings.review_index
        }
        
        # Initialize the orchestrator
        self.orchestrator = ContentPipelineOrchestrator(
            es_client=self.es_client,
            config=self.pipeline_config
        )
        
        # Initialize PubMedRetriever directly for more control
        self.pubmed_retriever = PubMedRetriever()
        
        # Statistics
        self.stats = {
            'total_articles': 0,
            'successfully_processed': 0,
            'failed': 0,
            'skipped': 0,
            'pmids_not_found': [],
            'processing_errors': []
        }
    
    def clear_elasticsearch_indexes(self):
        """Clear existing Elasticsearch indexes if requested."""
        if not self.clear_indexes:
            return
        
        logger.warning("Clearing existing Elasticsearch indexes...")
        
        indexes_to_clear = [
            settings.content_index,
            settings.review_index
        ]
        
        for index in indexes_to_clear:
            try:
                if self.es_client.indices.exists(index=index):
                    # Delete all documents in the index
                    response = self.es_client.delete_by_query(
                        index=index,
                        body={"query": {"match_all": {}}},
                        wait_for_completion=True
                    )
                    logger.info(f"Cleared {response['deleted']} documents from {index}")
                else:
                    logger.info(f"Index {index} does not exist, skipping")
            except Exception as e:
                logger.error(f"Error clearing index {index}: {e}")
    
    def load_pmids_from_bibtex(self, bibtex_file: str) -> List[str]:
        """
        Load PMIDs from BibTeX file.
        
        Args:
            bibtex_file: Path to BibTeX file
            
        Returns:
            List of PMIDs
        """
        logger.info(f"Loading PMIDs from {bibtex_file}")
        
        pmids = []
        
        try:
            with open(bibtex_file, 'r') as f:
                bib_db = bibtexparser.load(f)
            
            for entry in bib_db.entries:
                # Extract PMID from ID field (e.g., "PMID36357392")
                entry_id = entry.get('ID', '')
                if entry_id.startswith('PMID'):
                    pmid = entry_id.replace('PMID', '')
                    pmids.append(pmid)
                # Also check for pmid field
                elif 'pmid' in entry:
                    pmids.append(entry['pmid'])
            
            logger.info(f"Loaded {len(pmids)} PMIDs from BibTeX file")
            return pmids
            
        except Exception as e:
            logger.error(f"Error loading BibTeX file: {e}")
            return []
    
    def process_articles_batch(self, pmids: List[str], batch_size: int = 50) -> None:
        """
        Process articles in batches through the full pipeline.
        
        Args:
            pmids: List of PMIDs to process
            batch_size: Number of articles to process at once
        """
        total_pmids = len(pmids)
        logger.info(f"Processing {total_pmids} articles in batches of {batch_size}")
        
        for i in range(0, total_pmids, batch_size):
            batch_pmids = pmids[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_pmids + batch_size - 1) // batch_size
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_pmids)} articles)")
            logger.info(f"{'='*60}")
            
            try:
                # Fetch complete article details from PubMed
                logger.info("Fetching article details from PubMed...")
                articles = self.pubmed_retriever.fetch_article_details(batch_pmids)
                
                if not articles:
                    logger.warning(f"No articles returned for batch {batch_num}")
                    self.stats['pmids_not_found'].extend(batch_pmids)
                    continue
                
                logger.info(f"Retrieved {len(articles)} articles from PubMed")
                
                # Process each article through the full pipeline
                for article in articles:
                    try:
                        pmid = article.get('pmid', '')
                        title = article.get('title', 'No title')[:100]
                        
                        logger.info(f"Processing PMID{pmid}: {title}...")
                        
                        # Add source metadata
                        article['source'] = 'pubmed'
                        article['content_type'] = 'article'
                        
                        # Process through the pipeline
                        processed = self.orchestrator._process_single_item(article)
                        
                        if processed:
                            # Log enrichment results
                            authors = processed.get('authors', [])
                            categories = processed.get('categories', [])
                            ai_confidence = processed.get('ai_confidence', 0)
                            
                            logger.info(f"✓ PMID{pmid} processed successfully:")
                            logger.info(f"  - Authors: {len(authors)} parsed")
                            logger.info(f"  - Categories: {categories}")
                            logger.info(f"  - AI Confidence: {ai_confidence:.2f}")
                            
                            self.stats['successfully_processed'] += 1
                        else:
                            logger.warning(f"✗ PMID{pmid} processing returned None")
                            self.stats['skipped'] += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing article {article.get('pmid', 'unknown')}: {e}")
                        self.stats['failed'] += 1
                        self.stats['processing_errors'].append({
                            'pmid': article.get('pmid', 'unknown'),
                            'error': str(e)
                        })
                
                # Small delay between batches to avoid overwhelming the API
                if i + batch_size < total_pmids:
                    logger.info("Waiting 2 seconds before next batch...")
                    time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {e}")
                self.stats['failed'] += len(batch_pmids)
    
    def print_summary(self):
        """Print processing summary."""
        logger.info("\n" + "="*60)
        logger.info("PROCESSING SUMMARY")
        logger.info("="*60)
        logger.info(f"Total articles attempted: {self.stats['total_articles']}")
        logger.info(f"Successfully processed: {self.stats['successfully_processed']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Skipped (duplicates): {self.stats['skipped']}")
        
        if self.stats['pmids_not_found']:
            logger.warning(f"\nPMIDs not found in PubMed ({len(self.stats['pmids_not_found'])} total):")
            for pmid in self.stats['pmids_not_found'][:10]:
                logger.warning(f"  - {pmid}")
            if len(self.stats['pmids_not_found']) > 10:
                logger.warning(f"  ... and {len(self.stats['pmids_not_found']) - 10} more")
        
        if self.stats['processing_errors']:
            logger.error(f"\nProcessing errors ({len(self.stats['processing_errors'])} total):")
            for error in self.stats['processing_errors'][:5]:
                logger.error(f"  - PMID{error['pmid']}: {error['error']}")
            if len(self.stats['processing_errors']) > 5:
                logger.error(f"  ... and {len(self.stats['processing_errors']) - 5} more")
        
        # Query Elasticsearch to verify
        try:
            count = self.es_client.count(index=settings.content_index)['count']
            logger.info(f"\nTotal documents in {settings.content_index}: {count}")
        except Exception as e:
            logger.error(f"Could not query Elasticsearch: {e}")
    
    def run(self, bibtex_file: str, test_mode: bool = False):
        """
        Run the full pipeline process.
        
        Args:
            bibtex_file: Path to BibTeX file with training data
            test_mode: If True, only process first 5 articles
        """
        logger.info("Starting training data pipeline runner")
        logger.info(f"Configuration:")
        logger.info(f"  - Clear indexes: {self.clear_indexes}")
        logger.info(f"  - Test mode: {test_mode}")
        logger.info(f"  - AI Enhancement: {self.pipeline_config['enable_ai_enhancement']}")
        logger.info(f"  - Content index: {settings.content_index}")
        
        # Step 1: Clear indexes if requested
        if self.clear_indexes:
            self.clear_elasticsearch_indexes()
        
        # Step 2: Load PMIDs from BibTeX
        pmids = self.load_pmids_from_bibtex(bibtex_file)
        if not pmids:
            logger.error("No PMIDs loaded, exiting")
            return
        
        # Step 3: Apply test mode limit if requested
        if test_mode:
            logger.info(f"TEST MODE: Processing only first 5 articles")
            pmids = pmids[:5]
        
        self.stats['total_articles'] = len(pmids)
        
        # Step 4: Process articles through pipeline
        self.process_articles_batch(pmids)
        
        # Step 5: Print summary
        self.print_summary()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run training articles through full enrichment pipeline'
    )
    parser.add_argument(
        '--bibtex-file',
        type=str,
        default='jobs/article_classifier/data/enriched_articles_ohdsi_reformatted.bib',
        help='Path to BibTeX file with training data'
    )
    parser.add_argument(
        '--clear-indexes',
        action='store_true',
        help='Clear existing Elasticsearch indexes before starting'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode - only process first 5 articles'
    )
    
    args = parser.parse_args()
    
    # Verify BibTeX file exists
    if not os.path.exists(args.bibtex_file):
        logger.error(f"BibTeX file not found: {args.bibtex_file}")
        return
    
    # Create and run pipeline
    runner = TrainingDataPipelineRunner(clear_indexes=args.clear_indexes)
    runner.run(args.bibtex_file, test_mode=args.test)


if __name__ == "__main__":
    main()