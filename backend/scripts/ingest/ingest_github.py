#!/usr/bin/env python3
"""
Ingest GitHub repositories for OHDSI Dashboard.
Scans OHDSI organizations and searches for relevant repositories.

Usage:
    docker-compose exec backend python /app/scripts/ingest/ingest_github.py --max-items 50
    
Options:
    --max-items: Number of repositories to fetch (default: 50)
    --org: Specific organization to scan
    --query: Search query for repositories
    --enable-ai: Enable AI enhancement
    --dry-run: Test without indexing
"""

import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from jobs.github_scanner.scanner import GitHubScanner
from scripts.ingest.base_ingestion import BaseIngestion, create_argument_parser

logger = logging.getLogger(__name__)


class GitHubIngestion(BaseIngestion):
    """
    GitHub repository ingestion for OHDSI content.
    """
    
    # OHDSI organizations to monitor
    OHDSI_ORGS = [
        'OHDSI',           # Main OHDSI organization
        'OHDSI-Studies',   # OHDSI studies organization
    ]
    
    # Search queries for OHDSI repositories
    SEARCH_QUERIES = [
        'OHDSI',
        'OMOP CDM',
        'OHDSI HADES',
        'OHDSI Atlas',
        'PatientLevelPrediction',
        'CohortMethod',
        'FeatureExtraction',
        'DataQualityDashboard',
        'Achilles OHDSI'
    ]
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize GitHub ingestion."""
        super().__init__(source_name='github', content_type='repository', config=config)
        
        try:
            self.scanner = GitHubScanner()
            logger.info("GitHub ingestion initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub scanner: {e}")
            raise
    
    def fetch_content(
        self,
        max_items: int = 50,
        org_name: str = None,
        search_query: str = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch repositories from GitHub.
        
        Args:
            max_items: Maximum number of repositories to fetch
            org_name: Specific organization to scan
            search_query: Custom search query
            
        Returns:
            List of repository data
        """
        all_repos = []
        
        # If specific org or query provided
        if org_name:
            logger.info(f"Scanning organization: {org_name}")
            repos = self._fetch_org_repos(org_name, max_items)
            all_repos.extend(repos)
        elif search_query:
            logger.info(f"Searching: {search_query}")
            repos = self._search_repos(search_query, max_items)
            all_repos.extend(repos)
        else:
            # Fetch from all OHDSI sources
            items_per_source = max(1, max_items // (len(self.OHDSI_ORGS) + len(self.SEARCH_QUERIES)))
            
            # Scan organizations
            for org in self.OHDSI_ORGS:
                if len(all_repos) >= max_items:
                    break
                repos = self._fetch_org_repos(org, items_per_source)
                all_repos.extend(repos)
            
            # Search for additional repositories
            for query in self.SEARCH_QUERIES:
                if len(all_repos) >= max_items:
                    break
                repos = self._search_repos(query, items_per_source)
                all_repos.extend(repos)
        
        # Remove duplicates (same repo might appear in org and search)
        unique_repos = self._deduplicate_repos(all_repos)
        
        # Limit to max_items
        unique_repos = unique_repos[:max_items]
        
        logger.info(f"Total repositories fetched: {len(unique_repos)}")
        return unique_repos
    
    def _fetch_org_repos(self, org_name: str, max_results: int) -> List[Dict[str, Any]]:
        """Fetch repositories from a specific organization."""
        try:
            logger.info(f"Fetching up to {max_results} repos from {org_name}")
            repos = self.scanner.fetch_org_repositories(org_name, max_results=max_results)
            
            # Process each repository
            processed = []
            for repo in repos:
                # Add GitHub-specific fields
                repo['source'] = 'github'
                repo['content_type'] = 'repository'
                repo['organization'] = org_name
                
                # Ensure ID field
                if 'full_name' in repo and 'id' not in repo:
                    repo['id'] = f"github_{repo['full_name'].replace('/', '_')}"
                
                # Extract key metrics
                repo['stars_count'] = repo.get('stargazers_count', 0)
                repo['forks_count'] = repo.get('forks_count', 0)
                repo['open_issues_count'] = repo.get('open_issues_count', 0)
                
                processed.append(repo)
            
            logger.info(f"Fetched {len(processed)} repositories from {org_name}")
            return processed
            
        except Exception as e:
            logger.error(f"Error fetching from org {org_name}: {e}")
            return []
    
    def _search_repos(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search for repositories by query."""
        try:
            logger.info(f"Searching for '{query}' (max {max_results} results)")
            
            # Add filters for better results
            filters = {
                'min_stars': 5,  # At least 5 stars
                'language': None,  # Any language
                'created_after': None  # Any age
            }
            
            repos = self.scanner.search(query, max_results=max_results, filters=filters)
            
            # Process each repository
            processed = []
            for repo in repos:
                # Add GitHub-specific fields
                repo['source'] = 'github'
                repo['content_type'] = 'repository'
                repo['search_query'] = query
                
                # Ensure ID field
                if 'full_name' in repo and 'id' not in repo:
                    repo['id'] = f"github_{repo['full_name'].replace('/', '_')}"
                
                # Extract key metrics
                repo['stars_count'] = repo.get('stargazers_count', 0)
                repo['forks_count'] = repo.get('forks_count', 0)
                repo['open_issues_count'] = repo.get('open_issues_count', 0)
                
                processed.append(repo)
            
            logger.info(f"Found {len(processed)} repositories for query '{query}'")
            return processed
            
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
            return []
    
    def _deduplicate_repos(self, repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate repositories based on full_name."""
        seen = set()
        unique = []
        
        for repo in repos:
            key = repo.get('full_name', repo.get('id', ''))
            if key and key not in seen:
                seen.add(key)
                unique.append(repo)
        
        if len(repos) > len(unique):
            logger.info(f"Removed {len(repos) - len(unique)} duplicate repositories")
        
        return unique
    
    def validate_content(self, item: Dict[str, Any]) -> bool:
        """
        Validate that a GitHub repository has required fields.
        
        Args:
            item: Repository to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['full_name', 'name']
        
        for field in required_fields:
            if not item.get(field):
                logger.warning(f"Missing required field '{field}' in repository")
                return False
        
        # Check for OHDSI relevance
        name = item.get('name', '').lower()
        description = item.get('description', '').lower()
        readme = item.get('readme_content', '').lower()
        topics = [t.lower() for t in item.get('topics', [])]
        
        ohdsi_keywords = ['ohdsi', 'omop', 'observational health', 'atlas', 'hades', 
                         'achilles', 'cohort', 'cdm', 'common data model']
        
        # Check if any OHDSI keyword appears
        content_text = f"{name} {description} {readme} {' '.join(topics)}"
        has_ohdsi_content = any(keyword in content_text for keyword in ohdsi_keywords)
        
        if not has_ohdsi_content:
            logger.debug(f"Repository '{item.get('full_name', '')}' has no OHDSI keywords")
            # Still return True to process, let ML classifier decide relevance
        
        return True
    
    def process_item(self, item: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Process a GitHub repository with special handling.
        
        Args:
            item: Raw repository data
            
        Returns:
            Processed repository
        """
        # Process through base pipeline
        processed = super().process_item(item, dry_run=dry_run)
        
        if processed:
            # Add GitHub-specific metadata
            processed['source_type'] = 'code'
            processed['display_type'] = 'Code Repository'
            processed['icon_type'] = 'code'
            processed['content_category'] = 'code'
            
            # Generate URL if not present
            if 'url' not in processed and 'html_url' in item:
                processed['url'] = item['html_url']
            elif 'url' not in processed and 'full_name' in item:
                processed['url'] = f"https://github.com/{item['full_name']}"
            
            # Set dates
            if 'created_at' in item and 'published_date' not in processed:
                processed['published_date'] = item['created_at']
            
            if 'updated_at' in item:
                processed['last_updated'] = item['updated_at']
            
            # Add programming language
            if 'language' in item:
                processed['language'] = item['language']
            
            # Add topics as tags
            if 'topics' in item and item['topics']:
                processed['tags'] = item['topics']
            
            # Calculate activity score
            if 'pushed_at' in item:
                try:
                    pushed_date = datetime.fromisoformat(item['pushed_at'].replace('Z', '+00:00'))
                    days_since_push = (datetime.now(pushed_date.tzinfo) - pushed_date).days
                    if days_since_push < 30:
                        processed['activity_level'] = 'high'
                    elif days_since_push < 90:
                        processed['activity_level'] = 'medium'
                    else:
                        processed['activity_level'] = 'low'
                except:
                    processed['activity_level'] = 'unknown'
        
        return processed


def main():
    """Main entry point for GitHub ingestion."""
    # Parse arguments
    parser = create_argument_parser()
    parser.description = "Ingest GitHub repositories for OHDSI Dashboard"
    parser.add_argument(
        '--org',
        type=str,
        help='Specific organization to scan'
    )
    parser.add_argument(
        '--query',
        type=str,
        help='Search query for repositories'
    )
    args = parser.parse_args()
    
    # Configure
    config = {
        'enable_ai_enhancement': args.enable_ai,
        'auto_approve_threshold': 0.65,  # Lower threshold for repositories
        'priority_threshold': 0.45
    }
    
    # Initialize and run ingestion
    ingestion = GitHubIngestion(config=config)
    
    # Run ingestion
    stats = ingestion.ingest(
        max_items=args.max_items,
        org_name=args.org,
        search_query=args.query,
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