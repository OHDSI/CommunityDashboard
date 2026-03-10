"""
GitHub scanner for OHDSI-related repositories.
Searches for and analyzes repositories related to OHDSI, OMOP, and related tools.
"""

import os
import re
import logging
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

# GitHub API client
try:
    from github import Github
    from github.GithubException import GithubException, RateLimitExceededException
    GITHUB_API_AVAILABLE = True
except ImportError:
    GITHUB_API_AVAILABLE = False
    logging.warning("PyGithub not available. Install with: pip install PyGithub")

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.base_fetcher import BaseFetcher
from shared.ohdsi_constants import (
    GITHUB_SEARCH_QUERIES,
    GITHUB_OHDSI_ORGS,
    OHDSI_KEYWORDS,
    OHDSI_TAG_KEYWORDS,
)
from shared.content_relevance import is_ohdsi_related

logger = logging.getLogger(__name__)


class GitHubScanner(BaseFetcher):
    """
    Scans GitHub for OHDSI-related repositories.
    """

    # OHDSI organizations and users to monitor
    OHDSI_ORGS = GITHUB_OHDSI_ORGS

    # Search queries for finding OHDSI-related repos
    SEARCH_QUERIES = GITHUB_SEARCH_QUERIES
    
    # File patterns that indicate OHDSI-related projects
    OHDSI_FILE_PATTERNS = [
        'inst/sql/sql_server/*.sql',  # OHDSI R packages pattern
        'inst/cohorts/*.json',         # Atlas cohort definitions
        'extras/CodeToRun.R',          # OHDSI study pattern
        '**/ConceptSets/*.json',       # Concept sets
        '**/CohortDefinitions/*.json'  # Cohort definitions
    ]
    
    def __init__(self, github_token: str = None):
        """
        Initialize GitHub scanner.
        
        Args:
            github_token: GitHub personal access token
        """
        super().__init__(
            source_name='github',
            rate_limit=1.0,  # GitHub allows 5000 requests/hour with auth
            cache_ttl=3600 * 6  # Cache for 6 hours
        )
        
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        
        if not self.github_token:
            logger.warning("No GitHub token provided. API rate limits will be restrictive.")
        
        if GITHUB_API_AVAILABLE:
            try:
                self.github = Github(self.github_token) if self.github_token else Github()
                # Test connection and get rate limit info
                try:
                    rate_limit = self.github.get_rate_limit()
                    if hasattr(rate_limit, 'core'):
                        logger.info(f"GitHub API initialized. Rate limit: {rate_limit.core.remaining}/{rate_limit.core.limit}")
                    else:
                        logger.info("GitHub API initialized (anonymous access)")
                except Exception as rate_error:
                    logger.info(f"GitHub API initialized but couldn't get rate limit: {rate_error}")
            except Exception as e:
                logger.error(f"Failed to initialize GitHub API: {e}")
                self.github = None
        else:
            self.github = None
    
    def search(self, query: str, max_results: int = 100, 
              filters: Dict[str, Any] = None) -> List[str]:
        """
        Search for repositories on GitHub.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            filters: Additional filters (language, stars, etc.)
            
        Returns:
            List of repository full names (owner/repo)
        """
        if not self.github:
            logger.error("GitHub API client not initialized")
            return []
        
        repo_names = []
        filters = filters or {}
        
        try:
            # Build search query with filters
            search_query = query
            
            # Add language filter
            if filters.get('language'):
                search_query += f" language:{filters['language']}"
            
            # Add star filter
            if filters.get('min_stars'):
                search_query += f" stars:>={filters['min_stars']}"
            
            # Add date filter
            if filters.get('created_after'):
                search_query += f" created:>={filters['created_after']}"
            if filters.get('pushed_after'):
                search_query += f" pushed:>={filters['pushed_after']}"
            
            # Search repositories
            repositories = self.github.search_repositories(
                query=search_query,
                sort=filters.get('sort', 'stars'),
                order=filters.get('order', 'desc')
            )
            
            # Collect results up to max_results
            for i, repo in enumerate(repositories):
                if i >= max_results:
                    break
                repo_names.append(repo.full_name)
            
            logger.info(f"Found {len(repo_names)} repositories for query: {query}")
            
        except RateLimitExceededException:
            logger.error("GitHub API rate limit exceeded")
        except GithubException as e:
            logger.error(f"GitHub API error during search: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during GitHub search: {e}")
        
        return repo_names
    
    def fetch_details(self, repo_names: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch detailed information for repositories.
        
        Args:
            repo_names: List of repository full names (owner/repo)
            
        Returns:
            List of repository details
        """
        if not self.github:
            logger.error("GitHub API client not initialized")
            return []
        
        if not repo_names:
            return []
        
        repositories = []
        
        for repo_name in repo_names:
            try:
                repo = self.github.get_repo(repo_name)
                repo_data = self._parse_repository(repo)
                if repo_data:
                    repositories.append(repo_data)
                    
            except RateLimitExceededException:
                logger.error("GitHub API rate limit exceeded")
                break
            except GithubException as e:
                logger.error(f"Error fetching repo {repo_name}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error fetching repo {repo_name}: {e}")
        
        logger.info(f"Fetched details for {len(repositories)} repositories")
        
        return repositories
    
    def fetch_org_repositories(self, org_name: str, 
                             max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch all repositories from an organization.
        
        Args:
            org_name: GitHub organization name
            max_results: Maximum number of repositories
            
        Returns:
            List of repository details
        """
        if not self.github:
            logger.error("GitHub API client not initialized")
            return []
        
        repositories = []
        
        try:
            org = self.github.get_organization(org_name)
            
            for i, repo in enumerate(org.get_repos()):
                if i >= max_results:
                    break
                
                repo_data = self._parse_repository(repo)
                if repo_data:
                    repositories.append(repo_data)
            
            logger.info(f"Fetched {len(repositories)} repositories from org {org_name}")
            
        except RateLimitExceededException:
            logger.error("GitHub API rate limit exceeded")
        except GithubException as e:
            logger.error(f"Error fetching org {org_name}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching org {org_name}: {e}")
        
        return repositories
    
    def fetch_ohdsi_content(self, max_results_per_query: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch OHDSI-related repositories from multiple sources.
        
        Args:
            max_results_per_query: Maximum results per search query
            
        Returns:
            List of OHDSI-related repositories
        """
        all_repos = []
        seen_repos = set()
        
        # Fetch from known OHDSI organizations
        for org_name in self.OHDSI_ORGS:
            repos = self.fetch_org_repositories(org_name, max_results_per_query)
            for repo in repos:
                repo_id = repo.get('full_name')
                if repo_id and repo_id not in seen_repos:
                    all_repos.append(repo)
                    seen_repos.add(repo_id)
        
        # Search for OHDSI-related repositories
        for query in self.SEARCH_QUERIES:
            repo_names = self.search(query, max_results_per_query)
            repos = self.fetch_details(repo_names)
            
            for repo in repos:
                repo_id = repo.get('full_name')
                if repo_id and repo_id not in seen_repos:
                    # Additional filtering for relevance
                    if self._is_ohdsi_related(repo):
                        all_repos.append(repo)
                        seen_repos.add(repo_id)
        
        logger.info(f"Found {len(all_repos)} unique OHDSI-related repositories")
        
        return all_repos
    
    def _parse_repository(self, repo) -> Optional[Dict[str, Any]]:
        """Parse GitHub repository object to our format."""
        try:
            # Get README content
            readme_content = self._get_readme(repo)
            
            # Get primary language stats
            languages = {}
            try:
                languages = repo.get_languages()
            except:
                pass
            
            # Get contributors count (limited API call)
            contributor_count = 0
            top_contributors = []
            try:
                contributors = repo.get_contributors()
                for i, contributor in enumerate(contributors):
                    if i < 5:  # Get top 5 contributors
                        top_contributors.append(contributor.login)
                    contributor_count += 1
                    if i >= 30:  # Limit to prevent excessive API calls
                        contributor_count = 30  # Cap at 30 to avoid excessive API calls
                        break
            except:
                pass
            
            # Check for OHDSI-specific files
            has_ohdsi_structure = self._check_ohdsi_structure(repo)
            
            return {
                'repo_id': str(repo.id),
                'full_name': repo.full_name,
                'name': repo.name,
                'title': repo.name,  # Add title field for normalizer
                'owner': repo.owner.login,
                'description': repo.description or '',
                'readme': readme_content,
                'url': repo.html_url,  # Use 'url' instead of 'html_url' for normalizer
                'html_url': repo.html_url,
                'clone_url': repo.clone_url,
                'created_at': repo.created_at.isoformat() if repo.created_at else None,
                'updated_at': repo.updated_at.isoformat() if repo.updated_at else None,
                'pushed_at': repo.pushed_at.isoformat() if repo.pushed_at else None,
                'year': repo.created_at.year if repo.created_at else datetime.now().year,
                'language': repo.language,
                'languages': languages,
                'stargazers_count': repo.stargazers_count,
                'watchers_count': repo.watchers_count,
                'forks_count': repo.forks_count,
                'open_issues_count': repo.open_issues_count,
                'license': repo.license.name if repo.license else None,
                'topics': repo.get_topics(),
                'size': repo.size,  # KB
                'default_branch': repo.default_branch,
                'has_issues': repo.has_issues,
                'has_wiki': repo.has_wiki,
                'has_downloads': repo.has_downloads,
                'archived': repo.archived,
                'contributors': top_contributors,
                'contributor_count': contributor_count,
                'has_ohdsi_structure': has_ohdsi_structure,
                'content_type': 'repository',
                'source': 'github',
                # Add repository_metadata field for enhanced schema
                'repository_metadata': {
                    'readme_content': readme_content,
                    'license': repo.license.name if repo.license else None,
                    'contributors': top_contributors,
                    'has_issues': repo.has_issues,
                    'has_wiki': repo.has_wiki,
                    'archived': repo.archived,
                    'size': repo.size,
                    'default_branch': repo.default_branch,
                    'languages': languages,
                    'has_ohdsi_structure': has_ohdsi_structure
                }
            }
        except Exception as e:
            logger.error(f"Error parsing repository {repo.full_name}: {e}")
            return None
    
    def _get_readme(self, repo) -> str:
        """Get README content from repository."""
        try:
            readme = repo.get_readme()
            # Decode content from base64
            content = base64.b64decode(readme.content).decode('utf-8')
            # Limit README size to prevent huge documents
            return content[:50000]  # First 50KB
        except Exception as e:
            logger.debug(f"Could not fetch README for {repo.full_name}: {e}")
            # Return description as fallback
            return repo.description or ""
    
    def _check_ohdsi_structure(self, repo) -> bool:
        """
        Check if repository has OHDSI-specific structure.
        
        Args:
            repo: GitHub repository object
            
        Returns:
            True if repository appears to follow OHDSI patterns
        """
        try:
            # Check for common OHDSI directories
            contents = repo.get_contents("")
            
            ohdsi_indicators = [
                'inst/sql',           # SQL files for different databases
                'inst/cohorts',       # Cohort definitions
                'inst/settings',      # Settings for OHDSI studies
                'extras',             # Common in OHDSI R packages
                'R',                  # R package structure
                'man',                # R documentation
                'DESCRIPTION',        # R package file
                'renv.lock',          # R environment lock file
                'ConceptSets',        # Concept set definitions
                'CohortDefinitions'   # Cohort definitions
            ]
            
            found_indicators = 0
            for item in contents:
                if item.name in ohdsi_indicators or item.path in ohdsi_indicators:
                    found_indicators += 1
            
            return found_indicators >= 2  # At least 2 indicators
            
        except:
            return False
    
    def _is_ohdsi_related(self, repo: Dict[str, Any]) -> bool:
        """
        Check if a repository is likely OHDSI-related.

        Args:
            repo: Repository details

        Returns:
            True if repository appears OHDSI-related
        """
        # Check repository name and description (handle None values)
        name = repo.get('name') or ''
        description = repo.get('description') or ''
        text = f"{name} {description}"

        if is_ohdsi_related(text):
            return True

        # Check README content (handle None values)
        readme = repo.get('readme') or ''
        if readme and is_ohdsi_related(readme[:5000]):
            return True

        # Check topics
        topics = repo.get('topics', [])
        if topics:
            topics_lower = [topic.lower() for topic in topics if topic]
            for keyword in OHDSI_TAG_KEYWORDS:
                if keyword in topics_lower:
                    return True

        # Check if from OHDSI organization (handle None values)
        owner = repo.get('owner') or ''
        if owner and 'ohdsi' in owner.lower():
            return True

        # Check for OHDSI structure
        if repo.get('has_ohdsi_structure'):
            return True

        # Check language (OHDSI uses a lot of R and SQL) - handle None values
        language = repo.get('language') or ''
        text_lower = text.lower()
        if language and language.lower() in ['r', 'sql'] and any(kw in text_lower for kw in ['cohort', 'patient', 'clinical']):
            return True

        return False
    
    def analyze_repository_quality(self, repo: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze repository quality metrics.
        
        Args:
            repo: Repository details
            
        Returns:
            Quality metrics
        """
        quality = {
            'documentation_score': 0.0,
            'maintenance_score': 0.0,
            'community_score': 0.0,
            'code_quality_score': 0.0,
            'overall_score': 0.0
        }
        
        # Documentation score
        if repo.get('readme'):
            readme_length = len(repo['readme'])
            if readme_length > 5000:
                quality['documentation_score'] += 0.4
            elif readme_length > 1000:
                quality['documentation_score'] += 0.2
            
            # Check for sections in README
            readme_lower = repo['readme'].lower()
            if 'installation' in readme_lower:
                quality['documentation_score'] += 0.1
            if 'usage' in readme_lower or 'example' in readme_lower:
                quality['documentation_score'] += 0.1
            if 'license' in readme_lower:
                quality['documentation_score'] += 0.05
            if 'contributing' in readme_lower:
                quality['documentation_score'] += 0.05
        
        if repo.get('has_wiki'):
            quality['documentation_score'] += 0.1
        
        if repo.get('license'):
            quality['documentation_score'] += 0.1
        
        # Maintenance score
        if repo.get('pushed_at'):
            try:
                last_push = datetime.fromisoformat(repo['pushed_at'].replace('Z', '+00:00'))
                age = datetime.now() - last_push
                if age < timedelta(days=30):
                    quality['maintenance_score'] += 0.5
                elif age < timedelta(days=90):
                    quality['maintenance_score'] += 0.3
                elif age < timedelta(days=180):
                    quality['maintenance_score'] += 0.2
                elif age < timedelta(days=365):
                    quality['maintenance_score'] += 0.1
            except:
                pass
        
        if not repo.get('archived'):
            quality['maintenance_score'] += 0.2
        
        if repo.get('open_issues_count', 0) < 50:
            quality['maintenance_score'] += 0.1
        
        # Community score
        stars = repo.get('stargazers_count', 0)
        if stars > 100:
            quality['community_score'] += 0.3
        elif stars > 10:
            quality['community_score'] += 0.15
        elif stars > 0:
            quality['community_score'] += 0.05
        
        forks = repo.get('forks_count', 0)
        if forks > 50:
            quality['community_score'] += 0.2
        elif forks > 10:
            quality['community_score'] += 0.1
        elif forks > 0:
            quality['community_score'] += 0.05
        
        contributors = repo.get('contributor_count', 0)
        if isinstance(contributors, str) or contributors > 10:
            quality['community_score'] += 0.2
        elif contributors > 3:
            quality['community_score'] += 0.1
        elif contributors > 1:
            quality['community_score'] += 0.05
        
        # Code quality indicators
        if repo.get('has_ohdsi_structure'):
            quality['code_quality_score'] += 0.3
        
        if repo.get('topics'):
            quality['code_quality_score'] += 0.1
        
        if repo.get('language'):
            quality['code_quality_score'] += 0.1
        
        # Calculate overall score
        quality['overall_score'] = (
            quality['documentation_score'] * 0.3 +
            quality['maintenance_score'] * 0.3 +
            quality['community_score'] * 0.2 +
            quality['code_quality_score'] * 0.2
        )
        
        return quality
    
    def _fetch_single(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Implementation of abstract method from BaseFetcher.
        
        Args:
            query: Query parameters
            
        Returns:
            List of repositories
        """
        query_type = query.get('type', 'search')
        
        if query_type == 'search':
            repo_names = self.search(
                query.get('q', 'OHDSI'),
                query.get('max_results', 30),
                query.get('filters')
            )
            return self.fetch_details(repo_names)
        
        elif query_type == 'org':
            return self.fetch_org_repositories(
                query.get('org_name'),
                query.get('max_results', 30)
            )
        
        elif query_type == 'repo_names':
            return self.fetch_details(query.get('repo_names', []))
        
        else:
            logger.warning(f"Unknown query type: {query_type}")
            return []