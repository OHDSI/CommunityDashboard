#!/usr/bin/env python3
"""
Ingest articles from a list of PMIDs.

This script is designed for ground truth datasets or curated PMID lists.
It extracts PMIDs from a text file and processes them through the full pipeline.

Usage:
    # Process all PMIDs from file
    docker-compose exec backend python /app/scripts/ingest/ingest_pmid_list.py --file /path/to/pmid_list.txt

    # Dry run (test without indexing)
    docker-compose exec backend python /app/scripts/ingest/ingest_pmid_list.py --file /path/to/pmid_list.txt --dry-run

    # Process with batch size limit
    docker-compose exec backend python /app/scripts/ingest/ingest_pmid_list.py --file /path/to/pmid_list.txt --batch-size 50

    # Enable AI enhancement
    docker-compose exec backend python /app/scripts/ingest/ingest_pmid_list.py --file /path/to/pmid_list.txt --enable-ai

File format:
    The script extracts PMIDs using the pattern "PubMed PMID: XXXXXXXX"
    Works with citation formats, ground truth lists, etc.
"""

import sys
import re
import logging
from pathlib import Path
from typing import Dict, Any, List

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from jobs.article_classifier.retriever import PubMedRetriever
from scripts.ingest.base_ingestion import BaseIngestion, create_argument_parser

logger = logging.getLogger(__name__)


class PMIDListIngestion(BaseIngestion):
    """
    Ingest articles from a curated list of PMIDs.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize PMID list ingestion."""
        super().__init__(source_name='pubmed', content_type='article', config=config)
        self.retriever = PubMedRetriever()
        logger.info("PMID list ingestion initialized")

    def extract_pmids_from_file(self, file_path: str) -> List[str]:
        """
        Extract PMIDs from a text file.

        Supports formats like:
        - "PubMed PMID: 12345678"
        - "PMID: 12345678"
        - Just numbers on separate lines

        Args:
            file_path: Path to file containing PMIDs

        Returns:
            List of unique PMIDs
        """
        logger.info(f"Extracting PMIDs from {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Try multiple patterns
            pmids = set()

            # Pattern 1: "PubMed PMID: XXXXXXXX"
            pattern1 = r'PubMed PMID:\s*(\d+)'
            matches1 = re.findall(pattern1, content)
            pmids.update(matches1)

            # Pattern 2: "PMID: XXXXXXXX" or "PMID XXXXXXXX"
            pattern2 = r'PMID:?\s*(\d{7,8})'
            matches2 = re.findall(pattern2, content, re.IGNORECASE)
            pmids.update(matches2)

            # Pattern 3: Lines with just numbers (7-8 digits)
            pattern3 = r'^\s*(\d{7,8})\s*$'
            matches3 = re.findall(pattern3, content, re.MULTILINE)
            pmids.update(matches3)

            pmids = sorted(list(pmids))
            logger.info(f"Extracted {len(pmids)} unique PMIDs")

            return pmids

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return []
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return []

    def fetch_content(
        self,
        max_items: int = None,
        pmid_file: str = None,
        pmids: List[str] = None,
        batch_size: int = 50,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch articles for a list of PMIDs.

        Args:
            pmid_file: Path to file containing PMIDs
            pmids: Direct list of PMIDs (alternative to file)
            batch_size: Number of PMIDs to fetch per batch

        Returns:
            List of articles
        """
        # Get PMIDs from file or direct list
        if pmid_file:
            pmid_list = self.extract_pmids_from_file(pmid_file)
        elif pmids:
            pmid_list = pmids
        else:
            logger.error("Must provide either pmid_file or pmids")
            return []

        if not pmid_list:
            logger.warning("No PMIDs found to fetch")
            return []

        # Limit to max_items if specified
        if max_items and max_items < len(pmid_list):
            logger.info(f"Limiting to first {max_items} PMIDs (out of {len(pmid_list)})")
            pmid_list = pmid_list[:max_items]

        logger.info(f"Fetching {len(pmid_list)} articles in batches of {batch_size}")

        all_articles = []
        total_batches = (len(pmid_list) + batch_size - 1) // batch_size

        # Process in batches
        for i in range(0, len(pmid_list), batch_size):
            batch_num = i // batch_size + 1
            batch = pmid_list[i:i + batch_size]

            logger.info(f"Batch {batch_num}/{total_batches}: Fetching {len(batch)} articles")

            try:
                # Fetch article details
                articles = self.retriever.fetch_article_details(batch)

                if articles:
                    logger.info(f"  ✓ Fetched {len(articles)} articles")

                    # Fetch citations for batch
                    try:
                        logger.info(f"  Fetching citations for batch {batch_num}...")
                        citations = self.retriever.fetch_citations(batch, fetch_metadata=True)

                        # Add citation data to articles
                        for article in articles:
                            pmid = article.get('pmid')
                            if pmid and pmid in citations:
                                article['citations'] = citations[pmid]
                                article['citation_count'] = len(citations[pmid].get('cited_by', []))
                                article['reference_count'] = len(citations[pmid].get('references', []))
                            else:
                                article['citations'] = {'cited_by': [], 'references': [], 'similar': []}
                                article['citation_count'] = 0
                                article['reference_count'] = 0
                    except Exception as e:
                        logger.warning(f"  Could not fetch citations: {e}")
                        # Continue without citations
                        for article in articles:
                            article['citations'] = {'cited_by': [], 'references': [], 'similar': []}
                            article['citation_count'] = 0
                            article['reference_count'] = 0

                    all_articles.extend(articles)
                else:
                    logger.warning(f"  No articles returned for batch {batch_num}")

            except Exception as e:
                logger.error(f"  Error fetching batch {batch_num}: {e}")
                continue

        logger.info(f"Total articles fetched: {len(all_articles)}/{len(pmid_list)}")

        # Report any missing PMIDs
        fetched_pmids = {a.get('pmid') for a in all_articles}
        missing_pmids = set(pmid_list) - fetched_pmids
        if missing_pmids:
            logger.warning(f"Failed to fetch {len(missing_pmids)} articles")
            logger.debug(f"Missing PMIDs: {sorted(list(missing_pmids))[:10]}...")

        return all_articles

    def validate_content(self, item: Dict[str, Any]) -> bool:
        """
        Validate article has required fields.

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

        return True

    def process_item(self, item: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Process a single article through the pipeline.

        Args:
            item: Raw article data
            dry_run: If True, skip indexing

        Returns:
            Processed article or None if failed
        """
        # Ensure proper ID format
        if 'pmid' in item and 'id' not in item:
            item['id'] = item['pmid']

        # Process through base pipeline
        processed = super().process_item(item, dry_run=dry_run)

        if processed:
            # Ensure citations are preserved
            if 'citations' in item:
                processed['citations'] = item['citations']

            # Add metadata
            processed['source_type'] = 'scientific_article'
            processed['peer_reviewed'] = True

        return processed


def main():
    """Main entry point for PMID list ingestion."""
    # Create argument parser with base arguments
    parser = create_argument_parser()
    parser.description = "Ingest articles from a list of PMIDs"

    # Add PMID-specific arguments
    parser.add_argument(
        '--file',
        type=str,
        required=True,
        help='Path to file containing PMIDs'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of PMIDs to fetch per batch (default: 50)'
    )

    args = parser.parse_args()

    # Validate file exists
    if not Path(args.file).exists():
        logger.error(f"File not found: {args.file}")
        sys.exit(1)

    # Configure
    config = {
        'enable_ai_enhancement': args.enable_ai,
        'auto_approve_threshold': 0.7,
        'priority_threshold': 0.5
    }

    # Initialize ingestion
    ingestion = PMIDListIngestion(config=config)

    # Run ingestion
    # If max_items not specified, use 999999 to effectively process all PMIDs
    max_items_value = args.max_items if hasattr(args, 'max_items') and args.max_items else 999999
    stats = ingestion.ingest(
        max_items=max_items_value,
        pmid_file=args.file,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )

    # Print summary
    print("\n" + "=" * 80)
    print("INGESTION SUMMARY")
    print("=" * 80)
    print(f"Total fetched:      {stats.get('fetched', 0)}")
    print(f"Successfully processed: {stats.get('processed', 0)}")
    print(f"Indexed:           {stats.get('indexed', 0)}")
    print(f"Duplicates:        {stats.get('duplicates', 0)}")
    print(f"Errors:            {stats.get('errors', 0)}")
    print(f"Auto-approved:     {stats.get('auto_approved', 0)}")
    print(f"Sent to review:    {stats.get('sent_to_review', 0)}")
    print("=" * 80)

    # Save progress if requested
    if args.save_progress:
        ingestion.save_progress()

    return stats


if __name__ == "__main__":
    stats = main()

    # Exit with error code if there were errors
    if stats.get('errors', 0) > 0:
        logger.warning(f"Completed with {stats.get('errors')} errors")
        sys.exit(1)
