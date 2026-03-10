#!/usr/bin/env python3
"""
Ingest PubMed articles for OHDSI Dashboard.
Fetches articles with enriched citation metadata.

Usage:
    docker-compose exec backend python /app/scripts/ingest/ingest_pubmed.py --max-items 100
    
Options:
    --max-items: Number of articles to fetch (default: 50)
    --date-from: Start date YYYY-MM-DD
    --date-to: End date YYYY-MM-DD
    --enable-ai: Enable AI enhancement
    --dry-run: Test without indexing
"""

import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from jobs.article_classifier.retriever import PubMedRetriever
from scripts.ingest.base_ingestion import BaseIngestion, create_argument_parser

logger = logging.getLogger(__name__)


class PubMedIngestion(BaseIngestion):
    """
    PubMed article ingestion with enriched citations.
    """
    
    # OHDSI-specific search queries
    SEARCH_QUERIES = [
        'OHDSI',
        'OMOP CDM',
        'Observational Health Data Sciences',
        'OHDSI AND network study',
        '"Observational Health Data Sciences and Informatics"',
        'OHDSI[Affiliation]',
        'OMOP AND ("common data model" OR CDM)',
        'ATLAS AND OHDSI',
        'HADES AND OHDSI',
        'Achilles AND OHDSI'
    ]
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize PubMed ingestion."""
        super().__init__(source_name='pubmed', content_type='article', config=config)
        self.retriever = PubMedRetriever()
        logger.info("PubMed ingestion initialized")
    
    def fetch_content(
        self,
        max_items: int = 50,
        date_from: str = None,
        date_to: str = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch articles from PubMed with enriched citations.
        
        Args:
            max_items: Maximum number of articles to fetch
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            
        Returns:
            List of articles with citation data
        """
        # Set date range
        if not date_to:
            date_to = datetime.now().strftime("%Y/%m/%d")
        if not date_from:
            # Default to last 30 days
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y/%m/%d")
        else:
            # Convert format for PubMed API
            date_from = date_from.replace('-', '/')
            date_to = date_to.replace('-', '/') if date_to else date_to
        
        logger.info(f"Fetching PubMed articles from {date_from} to {date_to}")
        
        all_articles = []
        items_per_query = max(1, max_items // len(self.SEARCH_QUERIES))
        
        for query in self.SEARCH_QUERIES:
            if len(all_articles) >= max_items:
                break
            
            try:
                # Search for PMIDs
                logger.info(f"Searching: {query}")
                pmids = self.retriever.search_pubmed(
                    query=query,
                    max_results=items_per_query,
                    start_date=date_from,
                    end_date=date_to
                )
                
                if not pmids:
                    logger.info(f"No results for query: {query}")
                    continue
                
                logger.info(f"Found {len(pmids)} articles for query: {query}")
                
                # Fetch full article details
                articles = self.retriever.fetch_article_details(pmids)
                
                # Fetch enriched citations with metadata
                logger.info(f"Fetching enriched citations for {len(pmids)} articles...")
                citations = self.retriever.fetch_citations(pmids, fetch_metadata=True)
                
                # Add enriched citation data to each article
                for article in articles:
                    pmid = article.get('pmid')
                    if pmid and pmid in citations:
                        article['citations'] = citations[pmid]
                        
                        # Log citation counts
                        cited_by = citations[pmid].get('cited_by', [])
                        references = citations[pmid].get('references', [])
                        
                        # Check if citations are enriched (have metadata)
                        if cited_by and isinstance(cited_by[0], dict):
                            logger.debug(f"✅ Article {pmid} has {len(cited_by)} enriched citations")
                        
                        article['citation_count'] = len(cited_by)
                        article['reference_count'] = len(references)
                    else:
                        # Empty citations structure
                        article['citations'] = {
                            'cited_by': [],
                            'references': [],
                            'similar': []
                        }
                        article['citation_count'] = 0
                        article['reference_count'] = 0
                
                all_articles.extend(articles)
                
            except Exception as e:
                logger.error(f"Error with query '{query}': {e}")
                continue
        
        # Limit to max_items
        all_articles = all_articles[:max_items]
        
        logger.info(f"Total articles fetched: {len(all_articles)}")
        return all_articles
    
    def validate_content(self, item: Dict[str, Any]) -> bool:
        """
        Validate that a PubMed article has required fields.
        
        Args:
            item: Article to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['pmid', 'title']
        
        for field in required_fields:
            if not item.get(field):
                logger.warning(f"Missing required field '{field}' in article")
                return False
        
        # Validate citations structure
        citations = item.get('citations', {})
        if not isinstance(citations, dict):
            logger.warning(f"Invalid citations structure for PMID {item.get('pmid')}")
            return False
        
        return True
    
    def process_item(self, item: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Process a PubMed article with special handling for citations.
        
        Args:
            item: Raw article data
            dry_run: If True, skip indexing to Elasticsearch
            
        Returns:
            Processed article
        """
        # Ensure proper ID format
        if 'pmid' in item and 'id' not in item:
            item['id'] = item['pmid']  # Use PMID as ID (without prefix)
        
        # Process through base pipeline
        processed = super().process_item(item, dry_run=dry_run)
        
        if processed:
            # Ensure citations are preserved
            if 'citations' in item:
                processed['citations'] = item['citations']
            
            # Add PubMed-specific metadata
            processed['source_type'] = 'scientific_article'
            processed['peer_reviewed'] = True
            
        return processed


def main():
    """Main entry point for PubMed ingestion."""
    # Parse arguments
    parser = create_argument_parser()
    parser.description = "Ingest PubMed articles with enriched citations"
    args = parser.parse_args()
    
    # Configure
    config = {
        'enable_ai_enhancement': args.enable_ai,
        'auto_approve_threshold': 0.7,
        'priority_threshold': 0.5
    }
    
    # Initialize and run ingestion
    ingestion = PubMedIngestion(config=config)
    
    # Run ingestion
    stats = ingestion.ingest(
        max_items=args.max_items,
        date_from=args.date_from,
        date_to=args.date_to,
        dry_run=args.dry_run
    )
    
    # Save progress if requested
    if args.save_progress:
        ingestion.save_progress()
    
    return stats


if __name__ == "__main__":
    stats = main()
    
    # Exit with error code if there were errors
    if stats.get('errors', 0) > 0:
        sys.exit(1)