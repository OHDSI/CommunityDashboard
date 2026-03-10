"""
Base fetcher class for all content sources.
Provides common functionality for rate limiting, error handling, and logging.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib
import json

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """
    Abstract base class for all content fetchers.
    Provides rate limiting, caching, and error handling.
    """
    
    def __init__(self, 
                 source_name: str,
                 rate_limit: float = 1.0,
                 cache_ttl: int = 3600,
                 max_retries: int = 3):
        """
        Initialize base fetcher.
        
        Args:
            source_name: Name of the content source (e.g., 'pubmed', 'youtube')
            rate_limit: Minimum seconds between API calls
            cache_ttl: Cache time-to-live in seconds
            max_retries: Maximum number of retries on failure
        """
        self.source_name = source_name
        self.rate_limit = rate_limit
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        self.last_request_time = 0
        self.request_count = 0
        self.error_count = 0
        self.cache = {}
        
        # Statistics tracking
        self.stats = {
            'total_fetched': 0,
            'total_errors': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'start_time': datetime.now()
        }
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between API calls."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            wait_time = self.rate_limit - elapsed
            logger.debug(f"{self.source_name}: Rate limiting, waiting {wait_time:.2f}s")
            time.sleep(wait_time)
        self.last_request_time = time.time()
    
    def _get_cache_key(self, query: Dict[str, Any]) -> str:
        """Generate cache key from query parameters."""
        query_str = json.dumps(query, sort_keys=True)
        return hashlib.md5(query_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if not expired."""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if datetime.now() - entry['timestamp'] < timedelta(seconds=self.cache_ttl):
                self.stats['cache_hits'] += 1
                logger.debug(f"{self.source_name}: Cache hit for key {cache_key}")
                return entry['data']
        return None
    
    def _save_to_cache(self, cache_key: str, data: Any):
        """Save data to cache."""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry."""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                self.error_count += 1
                
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"{self.source_name}: Attempt {attempt + 1} failed, "
                        f"retrying in {wait_time}s. Error: {str(e)[:200]}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"{self.source_name}: All {self.max_retries} attempts failed. "
                        f"Last error: {str(e)}"
                    )
        
        self.stats['total_errors'] += 1
        raise last_exception
    
    def fetch_batch(self, queries: List[Dict[str, Any]], 
                   use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Fetch multiple items in a batch.
        
        Args:
            queries: List of query parameters
            use_cache: Whether to use caching
            
        Returns:
            List of fetched content items
        """
        results = []
        
        for query in queries:
            try:
                # Check cache first
                if use_cache:
                    cache_key = self._get_cache_key(query)
                    cached_data = self._get_from_cache(cache_key)
                    if cached_data:
                        results.extend(cached_data)
                        continue
                
                # Enforce rate limiting
                self._enforce_rate_limit()
                
                # Fetch with retry logic
                data = self._retry_with_backoff(self._fetch_single, query)
                
                # Save to cache
                if use_cache and data:
                    self._save_to_cache(cache_key, data)
                
                results.extend(data)
                self.stats['total_fetched'] += len(data)
                self.stats['api_calls'] += 1
                
            except Exception as e:
                logger.error(f"{self.source_name}: Failed to fetch for query {query}: {e}")
                continue
        
        return results
    
    @abstractmethod
    def _fetch_single(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch content for a single query.
        Must be implemented by subclasses.
        
        Args:
            query: Query parameters
            
        Returns:
            List of content items
        """
        pass
    
    @abstractmethod
    def search(self, query: str, max_results: int = 100, 
              filters: Dict[str, Any] = None) -> List[str]:
        """
        Search for content IDs matching the query.
        Must be implemented by subclasses.
        
        Args:
            query: Search query string
            max_results: Maximum number of results
            filters: Additional filters
            
        Returns:
            List of content IDs
        """
        pass
    
    @abstractmethod
    def fetch_details(self, content_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch detailed information for content IDs.
        Must be implemented by subclasses.
        
        Args:
            content_ids: List of content IDs
            
        Returns:
            List of content details
        """
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get fetcher statistics."""
        runtime = datetime.now() - self.stats['start_time']
        return {
            **self.stats,
            'source': self.source_name,
            'runtime_seconds': runtime.total_seconds(),
            'avg_fetch_rate': self.stats['total_fetched'] / max(runtime.total_seconds(), 1),
            'cache_hit_rate': self.stats['cache_hits'] / max(self.stats['api_calls'] + self.stats['cache_hits'], 1),
            'error_rate': self.stats['total_errors'] / max(self.stats['api_calls'], 1)
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            'total_fetched': 0,
            'total_errors': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'start_time': datetime.now()
        }