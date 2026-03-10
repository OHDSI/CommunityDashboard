#!/usr/bin/env python3
"""
Ingest Wiki/Documentation for OHDSI Dashboard.
Scrapes OHDSI Wiki, Book of OHDSI, and other documentation sources.

Usage:
    docker-compose exec backend python /app/scripts/ingest/ingest_wiki.py --max-items 50
    
Options:
    --max-items: Number of pages to fetch (default: 50)
    --source: Specific documentation source to fetch from
    --enable-ai: Enable AI enhancement
    --dry-run: Test without indexing
"""

import sys
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import hashlib

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from jobs.wiki_scraper.scraper import WikiScraper
from scripts.ingest.base_ingestion import BaseIngestion, create_argument_parser

logger = logging.getLogger(__name__)


class WikiIngestion(BaseIngestion):
    """
    Wiki/Documentation ingestion for OHDSI knowledge base.
    """
    
    # Documentation sources to scrape
    DOCUMENTATION_SOURCES = [
        {
            'name': 'OHDSI Wiki',
            'base_url': 'https://www.ohdsi.org/web/wiki/doku.php',
            'type': 'dokuwiki',
            'priority': 'high'
        },
        {
            'name': 'Book of OHDSI',
            'base_url': 'https://ohdsi.github.io/TheBookOfOhdsi/',
            'type': 'gitbook',
            'priority': 'high'
        },
        {
            'name': 'HADES Documentation',
            'base_url': 'https://ohdsi.github.io/Hades/',
            'type': 'mkdocs',
            'priority': 'high'
        },
        {
            'name': 'OMOP CDM Documentation',
            'base_url': 'https://ohdsi.github.io/CommonDataModel/',
            'type': 'mkdocs',
            'priority': 'high'
        },
        {
            'name': 'Atlas Documentation',
            'base_url': 'https://github.com/OHDSI/Atlas/wiki',
            'type': 'github_wiki',
            'priority': 'medium'
        }
    ]
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Wiki ingestion."""
        super().__init__(source_name='wiki', content_type='documentation', config=config)
        
        try:
            self.scraper = WikiScraper()
            logger.info("Wiki ingestion initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Wiki scraper: {e}")
            raise
    
    def fetch_content(
        self,
        max_items: int = 50,
        source_name: str = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch documentation pages from wiki sources.
        
        Args:
            max_items: Maximum number of pages to fetch
            source_name: Specific documentation source to fetch from
            
        Returns:
            List of documentation pages
        """
        all_docs = []
        
        # If specific source provided
        if source_name:
            source = self._get_source_by_name(source_name)
            if source:
                logger.info(f"Fetching from source: {source_name}")
                docs = self._fetch_from_source(source, max_items)
                all_docs.extend(docs)
            else:
                logger.warning(f"Unknown source: {source_name}")
        else:
            # Fetch from all sources based on priority
            high_priority = [s for s in self.DOCUMENTATION_SOURCES if s['priority'] == 'high']
            medium_priority = [s for s in self.DOCUMENTATION_SOURCES if s['priority'] == 'medium']
            
            # Allocate items based on priority
            high_items = int(max_items * 0.7)  # 70% for high priority
            medium_items = max_items - high_items  # 30% for medium priority
            
            # Fetch from high priority sources
            if high_priority:
                items_per_source = max(1, high_items // len(high_priority))
                for source in high_priority:
                    if len(all_docs) >= max_items:
                        break
                    docs = self._fetch_from_source(source, items_per_source)
                    all_docs.extend(docs)
            
            # Fetch from medium priority sources
            if medium_priority and len(all_docs) < max_items:
                remaining = max_items - len(all_docs)
                items_per_source = max(1, min(medium_items, remaining) // len(medium_priority))
                for source in medium_priority:
                    if len(all_docs) >= max_items:
                        break
                    docs = self._fetch_from_source(source, items_per_source)
                    all_docs.extend(docs)
        
        # Remove duplicates
        unique_docs = self._deduplicate_docs(all_docs)
        
        # Limit to max_items
        unique_docs = unique_docs[:max_items]
        
        logger.info(f"Total documentation pages fetched: {len(unique_docs)}")
        return unique_docs
    
    def _get_source_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get source configuration by name."""
        for source in self.DOCUMENTATION_SOURCES:
            if source['name'].lower() == name.lower():
                return source
        return None
    
    def _fetch_from_source(self, source: Dict[str, Any], max_results: int) -> List[Dict[str, Any]]:
        """Fetch documentation from a specific source."""
        try:
            logger.info(f"Fetching up to {max_results} pages from {source['name']}")
            
            # Fetch pages based on source type
            if source['name'] == 'OHDSI Wiki':
                docs = self.scraper.fetch_ohdsi_documentation(max_pages=max_results)
            else:
                # Generic fetch for other sources
                docs = self.scraper.fetch_all_documentation(max_pages_per_source=max_results)
                # Filter to only this source
                docs = [d for d in docs if d.get('source_name') == source['name']]
            
            # Process each document
            processed = []
            for doc in docs:
                # Add wiki-specific fields
                doc['source'] = 'wiki'
                doc['content_type'] = 'documentation'
                doc['source_name'] = source['name']
                doc['source_type'] = source['type']
                
                # Generate unique ID
                if 'url' in doc and 'id' not in doc:
                    # Create ID from URL hash
                    url_hash = hashlib.md5(doc['url'].encode()).hexdigest()[:8]
                    doc['id'] = f"wiki_{source['name'].replace(' ', '_').lower()}_{url_hash}"
                
                processed.append(doc)
            
            logger.info(f"Fetched {len(processed)} pages from {source['name']}")
            return processed
            
        except Exception as e:
            logger.error(f"Error fetching from {source['name']}: {e}")
            return []
    
    def _deduplicate_docs(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate documentation pages based on URL."""
        seen_urls = set()
        seen_titles = set()
        unique = []
        
        for doc in docs:
            url = doc.get('url', '')
            title = doc.get('title', '')
            
            # Check both URL and title to avoid duplicates
            if url and url not in seen_urls:
                seen_urls.add(url)
                if title:
                    seen_titles.add(title.lower())
                unique.append(doc)
            elif title and title.lower() not in seen_titles:
                seen_titles.add(title.lower())
                unique.append(doc)
        
        if len(docs) > len(unique):
            logger.info(f"Removed {len(docs) - len(unique)} duplicate documentation pages")
        
        return unique
    
    def validate_content(self, item: Dict[str, Any]) -> bool:
        """
        Validate that a documentation page has required fields.
        
        Args:
            item: Documentation page to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['title']
        
        for field in required_fields:
            if not item.get(field):
                logger.warning(f"Missing required field '{field}' in documentation")
                return False
        
        # Check for content
        if not item.get('content') and not item.get('abstract'):
            logger.warning(f"Documentation page '{item.get('title', '')}' has no content")
            return False
        
        # Check for OHDSI relevance
        title = item.get('title', '').lower()
        content = item.get('content', '').lower()
        section = item.get('section_path', '').lower()
        
        ohdsi_keywords = ['ohdsi', 'omop', 'observational health', 'atlas', 'hades', 
                         'achilles', 'cohort', 'cdm', 'common data model', 'webapi',
                         'vocabulary', 'concept', 'phenotype', 'characterization',
                         'patient level prediction', 'comparative effectiveness']
        
        # Check if any OHDSI keyword appears
        content_text = f"{title} {content} {section}"
        has_ohdsi_content = any(keyword in content_text for keyword in ohdsi_keywords)
        
        if not has_ohdsi_content:
            logger.debug(f"Documentation '{item.get('title', '')[:50]}...' has no OHDSI keywords")
            # Still return True to process, let ML classifier decide relevance
        
        return True
    
    def process_item(self, item: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Process a documentation page with special handling.
        
        Args:
            item: Raw documentation data
            
        Returns:
            Processed documentation
        """
        # Process through base pipeline
        processed = super().process_item(item, dry_run=dry_run)
        
        if processed:
            # Add wiki-specific metadata
            processed['source_type'] = 'reference'
            processed['display_type'] = 'Documentation'
            processed['icon_type'] = 'document-text'
            processed['content_category'] = 'reference'
            
            # Ensure URL is present
            if 'url' not in processed and 'source_url' in item:
                processed['url'] = item['source_url']
            
            # Set dates (documentation typically doesn't have publish dates)
            if 'last_modified' in item and 'published_date' not in processed:
                processed['published_date'] = item['last_modified']
            elif 'published_date' not in processed:
                # Use current date as fallback
                processed['published_date'] = datetime.now().isoformat()
            
            # Add documentation structure metadata
            if 'section_path' in item:
                processed['section_path'] = item['section_path']
            
            if 'page_title' in item:
                processed['page_title'] = item['page_title']
            
            # Determine documentation type
            source_name = item.get('source_name', '').lower()
            if 'api' in source_name or 'webapi' in processed.get('title', '').lower():
                processed['doc_type'] = 'api_reference'
            elif 'book' in source_name:
                processed['doc_type'] = 'book_chapter'
            elif 'tutorial' in processed.get('title', '').lower():
                processed['doc_type'] = 'tutorial'
            elif 'guide' in processed.get('title', '').lower():
                processed['doc_type'] = 'guide'
            else:
                processed['doc_type'] = 'reference'
            
            # Extract key concepts if present
            if 'key_concepts' in item:
                processed['keywords'] = item['key_concepts']
            
            # Add complexity level if determined
            if 'complexity_level' in item:
                processed['complexity_level'] = item['complexity_level']
            elif 'getting started' in processed.get('title', '').lower():
                processed['complexity_level'] = 'beginner'
            elif 'advanced' in processed.get('title', '').lower():
                processed['complexity_level'] = 'advanced'
            else:
                processed['complexity_level'] = 'intermediate'
        
        return processed


def main():
    """Main entry point for Wiki ingestion."""
    # Parse arguments
    parser = create_argument_parser()
    parser.description = "Ingest Wiki/Documentation for OHDSI Dashboard"
    parser.add_argument(
        '--source',
        type=str,
        help='Specific documentation source to fetch from'
    )
    args = parser.parse_args()
    
    # Configure
    config = {
        'enable_ai_enhancement': args.enable_ai,
        'auto_approve_threshold': 0.75,  # Higher threshold for documentation
        'priority_threshold': 0.5
    }
    
    # Initialize and run ingestion
    ingestion = WikiIngestion(config=config)
    
    # Run ingestion
    stats = ingestion.ingest(
        max_items=args.max_items,
        source_name=args.source,
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