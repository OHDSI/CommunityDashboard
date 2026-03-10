"""
Deduplication utility for identifying duplicate and related content.
"""

import re
import hashlib
import logging
from typing import Dict, Any, List, Set, Tuple, Optional
from difflib import SequenceMatcher
from elasticsearch import Elasticsearch

from .identifier_extractor import extract_identifiers as _extract_identifiers_shared

logger = logging.getLogger(__name__)


class Deduplicator:
    """
    Identifies duplicate and related content across different sources.
    """
    
    def __init__(self, 
                 es_client: Elasticsearch = None,
                 similarity_threshold: float = 0.85):
        """
        Initialize deduplicator.
        
        Args:
            es_client: Elasticsearch client for checking existing content
            similarity_threshold: Threshold for considering content as duplicate
        """
        self.es_client = es_client
        self.similarity_threshold = similarity_threshold
        
        # Cache for fingerprints
        self.fingerprint_cache = {}
        
        # Statistics
        self.stats = {
            'total_checked': 0,
            'duplicates_found': 0,
            'related_found': 0
        }
    
    def check_duplicate(self, content: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Check if content is a duplicate of existing content.
        
        Args:
            content: Content to check
            
        Returns:
            Tuple of (is_duplicate, existing_id)
        """
        self.stats['total_checked'] += 1
        
        # Check by fingerprint
        fingerprint = content.get('fingerprint')
        if fingerprint:
            existing_id = self._check_fingerprint(fingerprint)
            if existing_id:
                self.stats['duplicates_found'] += 1
                return True, existing_id
        
        # Check by source ID
        if content.get('source_id'):
            existing_id = self._check_source_id(
                content['source'],
                content['source_id']
            )
            if existing_id:
                self.stats['duplicates_found'] += 1
                return True, existing_id
        
        # Check by title similarity
        if content.get('title'):
            existing_id = self._check_title_similarity(content['title'])
            if existing_id:
                self.stats['duplicates_found'] += 1
                return True, existing_id
        
        return False, None
    
    def find_related_content(self, content: Dict[str, Any], 
                           limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find content related to the given content.
        
        Args:
            content: Content to find relations for
            limit: Maximum number of related items
            
        Returns:
            List of related content items
        """
        related = []
        
        if not self.es_client:
            return related
        
        # Extract identifiers
        identifiers = self._extract_identifiers(content)
        
        # Search for content with matching identifiers
        should_clauses = []
        
        # PMIDs
        for pmid in identifiers['pmids']:
            should_clauses.append({
                "match": {"pmid": pmid}
            })
            should_clauses.append({
                "match": {"content": f"PMID {pmid}"}
            })
        
        # DOIs
        for doi in identifiers['dois']:
            should_clauses.append({
                "match": {"doi": doi}
            })
            should_clauses.append({
                "match": {"content": doi}
            })
        
        # URLs
        for url in identifiers['urls']:
            should_clauses.append({
                "match": {"url": url}
            })
            should_clauses.append({
                "match": {"content": url}
            })
        
        # Title similarity
        if content.get('title'):
            should_clauses.append({
                "match": {
                    "title": {
                        "query": content['title'],
                        "minimum_should_match": "70%"
                    }
                }
            })
        
        if not should_clauses:
            return related
        
        try:
            query = {
                "size": limit,
                "query": {
                    "bool": {
                        "should": should_clauses,
                        "minimum_should_match": 1,
                        "must_not": {
                            "term": {"id": content.get('id', '')}
                        }
                    }
                }
            }
            
            response = self.es_client.search(
                index="ohdsi_content_v3",
                body=query
            )
            
            for hit in response['hits']['hits']:
                related_item = hit['_source']
                related_item['relevance_score'] = hit['_score']
                related.append(related_item)
            
            self.stats['related_found'] += len(related)
            
        except Exception as e:
            logger.error(f"Failed to find related content: {e}")
        
        return related
    
    def _check_fingerprint(self, fingerprint: str) -> Optional[str]:
        """Check if fingerprint exists in Elasticsearch."""
        if not self.es_client:
            return None
        
        # Check cache first
        if fingerprint in self.fingerprint_cache:
            return self.fingerprint_cache[fingerprint]
        
        try:
            query = {
                "size": 1,
                "query": {
                    "term": {"fingerprint": fingerprint}
                }
            }
            
            response = self.es_client.search(
                index="ohdsi_content_v3",
                body=query
            )
            
            if response['hits']['total']['value'] > 0:
                existing_id = response['hits']['hits'][0]['_id']
                self.fingerprint_cache[fingerprint] = existing_id
                return existing_id
            
        except Exception as e:
            logger.error(f"Failed to check fingerprint: {e}")
        
        return None
    
    def _check_source_id(self, source: str, source_id: str) -> Optional[str]:
        """Check if source ID exists."""
        if not self.es_client:
            return None
        
        try:
            query = {
                "size": 1,
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"source": source}},
                            {"term": {"source_id": source_id}}
                        ]
                    }
                }
            }
            
            response = self.es_client.search(
                index="ohdsi_content_v3",
                body=query
            )
            
            if response['hits']['total']['value'] > 0:
                return response['hits']['hits'][0]['_id']
            
        except Exception as e:
            logger.error(f"Failed to check source ID: {e}")
        
        return None
    
    def _check_title_similarity(self, title: str) -> Optional[str]:
        """Check if a very similar title exists."""
        if not self.es_client or not title:
            return None
        
        try:
            # Normalize title for comparison
            normalized_title = self._normalize_text(title)
            
            query = {
                "size": 10,
                "query": {
                    "match": {
                        "title": {
                            "query": title,
                            "minimum_should_match": "80%"
                        }
                    }
                }
            }
            
            response = self.es_client.search(
                index="ohdsi_content_v3",
                body=query
            )
            
            for hit in response['hits']['hits']:
                existing_title = hit['_source'].get('title', '')
                normalized_existing = self._normalize_text(existing_title)
                
                similarity = self._calculate_similarity(
                    normalized_title,
                    normalized_existing
                )
                
                if similarity >= self.similarity_threshold:
                    return hit['_id']
            
        except Exception as e:
            logger.error(f"Failed to check title similarity: {e}")
        
        return None
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation and extra whitespace
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _extract_identifiers(self, content: Dict[str, Any]) -> Dict[str, Set[str]]:
        """Extract various identifiers from content."""
        return _extract_identifiers_shared(content)
    
    def merge_duplicates(self, primary: Dict[str, Any], 
                        duplicate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge duplicate content, keeping the best information from both.
        
        Args:
            primary: Primary content item
            duplicate: Duplicate content item
            
        Returns:
            Merged content
        """
        merged = primary.copy()
        
        # Merge scores (take maximum)
        score_fields = ['ml_score', 'gpt_score', 'combined_score', 
                       'quality_score', 'final_score']
        for field in score_fields:
            if duplicate.get(field, 0) > merged.get(field, 0):
                merged[field] = duplicate[field]
        
        # Merge categories (union)
        categories = set(merged.get('predicted_categories', []))
        categories.update(duplicate.get('predicted_categories', []))
        merged['predicted_categories'] = list(categories)
        merged['ohdsi_categories'] = list(categories)
        
        # Merge keywords (union)
        keywords = set(merged.get('keywords', []))
        keywords.update(duplicate.get('keywords', []))
        merged['keywords'] = list(keywords)
        
        # Keep longer content
        if len(duplicate.get('content', '')) > len(merged.get('content', '')):
            merged['content'] = duplicate['content']
        
        # Update metrics (sum)
        metric_fields = ['view_count', 'bookmark_count', 'share_count',
                        'stars_count', 'forks_count', 'answer_count']
        for field in metric_fields:
            merged[field] = merged.get(field, 0) + duplicate.get(field, 0)
        
        # Add cross-reference
        if 'related_content' not in merged:
            merged['related_content'] = []
        if duplicate.get('id'):
            merged['related_content'].append(duplicate['id'])
        
        return merged
    
    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        total = self.stats['total_checked']
        if total > 0:
            return {
                **self.stats,
                'duplicate_rate': self.stats['duplicates_found'] / total,
                'avg_related': self.stats['related_found'] / total
            }
        return self.stats
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            'total_checked': 0,
            'duplicates_found': 0,
            'related_found': 0
        }
        self.fingerprint_cache.clear()