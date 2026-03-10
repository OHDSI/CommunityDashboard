"""
Content normalizer that converts different content types to a unified schema.
"""

import re
import hashlib
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from abc import ABC, abstractmethod

from .utils.identifier_extractor import extract_identifiers as _extract_identifiers_shared

logger = logging.getLogger(__name__)

try:
    import sys
    sys.path.append('/app')
    from config.ohdsi_categories import map_old_categories as _map_cats
except ImportError:
    def _map_cats(cats):
        return cats


class ContentNormalizer:
    """
    Normalizes content from different sources to a unified schema.
    """
    
    def __init__(self):
        """Initialize the content normalizer."""
        self.normalizers = {
            'article': ArticleNormalizer(),
            'video': VideoNormalizer(),
            'repository': RepositoryNormalizer(),
            'discussion': DiscussionNormalizer(),
            'documentation': DocumentationNormalizer()
        }
    
    def normalize(self, content: Dict[str, Any], content_type: str) -> Dict[str, Any]:
        """
        Normalize content to unified schema.
        
        Args:
            content: Raw content from source
            content_type: Type of content (article, video, repository, etc.)
            
        Returns:
            Normalized content dictionary
        """
        if content_type not in self.normalizers:
            raise ValueError(f"Unknown content type: {content_type}")
        
        normalizer = self.normalizers[content_type]
        normalized = normalizer.normalize(content)
        
        # Add common fields
        normalized['content_type'] = content_type
        normalized['fingerprint'] = self._generate_fingerprint(normalized)
        normalized['created_at'] = datetime.now().isoformat()
        normalized['updated_at'] = datetime.now().isoformat()
        
        return normalized
    
    def _generate_fingerprint(self, content: Dict[str, Any]) -> str:
        """
        Generate a unique fingerprint for deduplication.
        
        Args:
            content: Normalized content
            
        Returns:
            Fingerprint hash
        """
        # For sources with unique IDs, use the source ID directly
        source = content.get('source', '')
        source_id = content.get('source_id', '')
        
        # Use source-specific unique identifiers when available
        if source and source_id:
            # For Discourse, GitHub, YouTube - use their unique IDs
            if source in ['discourse', 'github', 'youtube']:
                fingerprint_str = f"{source}|{source_id}"
                return hashlib.md5(fingerprint_str.encode()).hexdigest()
            # For PubMed, use PMID
            elif source == 'pubmed' and source_id:
                fingerprint_str = f"pubmed|{source_id}"
                return hashlib.md5(fingerprint_str.encode()).hexdigest()
        
        # Fallback to content-based fingerprint for other sources or missing IDs
        fingerprint_data = [
            content.get('title', '').lower().strip(),
            content.get('source', ''),
            str(content.get('published_date', ''))[:10] if content.get('published_date') else ''
        ]
        
        # Add primary author for articles or channel for videos
        if content.get('authors'):
            fingerprint_data.append(content['authors'][0].get('name', '').lower())
        elif content.get('channel_name'):
            fingerprint_data.append(content['channel_name'].lower())
        elif content.get('owner'):
            fingerprint_data.append(content['owner'].lower())
        
        fingerprint_str = '|'.join(str(x) for x in fingerprint_data)
        return hashlib.md5(fingerprint_str.encode()).hexdigest()
    
    def find_cross_references(self, content: Dict[str, Any], 
                            existing_content: List[Dict[str, Any]]) -> List[str]:
        """
        Find cross-references between content items.
        
        Args:
            content: New content item
            existing_content: List of existing content items
            
        Returns:
            List of related content IDs
        """
        related_ids = []
        
        # Extract identifiers from content
        identifiers = self._extract_identifiers(content)
        
        for existing in existing_content:
            existing_identifiers = self._extract_identifiers(existing)
            
            # Check for common identifiers
            if identifiers['pmids'] & existing_identifiers['pmids']:
                related_ids.append(existing['id'])
            elif identifiers['dois'] & existing_identifiers['dois']:
                related_ids.append(existing['id'])
            elif identifiers['urls'] & existing_identifiers['urls']:
                related_ids.append(existing['id'])
            
            # Check for title similarity (for different content types)
            if content['content_type'] != existing['content_type']:
                if self._similar_titles(content.get('title', ''), existing.get('title', '')):
                    related_ids.append(existing['id'])
        
        return list(set(related_ids))
    
    def _extract_identifiers(self, content: Dict[str, Any]) -> Dict[str, set]:
        """Extract various identifiers from content."""
        return _extract_identifiers_shared(content)
    
    def _similar_titles(self, title1: str, title2: str, threshold: float = 0.8) -> bool:
        """Check if two titles are similar."""
        # Simple similarity check - can be enhanced with fuzzy matching
        title1_words = set(title1.lower().split())
        title2_words = set(title2.lower().split())
        
        if not title1_words or not title2_words:
            return False
        
        intersection = title1_words & title2_words
        union = title1_words | title2_words
        
        jaccard_similarity = len(intersection) / len(union)
        return jaccard_similarity >= threshold


class BaseNormalizer(ABC):
    """Base class for content-specific normalizers."""
    
    @abstractmethod
    def normalize(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize content to unified schema."""
        pass


class ArticleNormalizer(BaseNormalizer):
    """Normalizer for article content."""
    
    def normalize(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize article to unified schema with simplified structure."""
        # Process citations into simplified structure
        citations_raw = content.get('citations', {})
        if not isinstance(citations_raw, dict):
            citations_raw = {}
        
        # Extract citation IDs and counts
        cited_by = citations_raw.get('cited_by', [])
        references = citations_raw.get('references', [])
        
        # Convert to simple ID arrays
        cited_by_ids = []
        reference_ids = []
        
        for item in cited_by:
            if isinstance(item, dict):
                cited_by_ids.append(str(item.get('id', '')))
            else:
                cited_by_ids.append(str(item))
        
        for item in references:
            if isinstance(item, dict):
                reference_ids.append(str(item.get('id', '')))
            else:
                reference_ids.append(str(item))
        
        # Create simplified citations structure
        simplified_citations = {
            'cited_by_count': len(cited_by_ids),
            'references_count': len(reference_ids),
            'cited_by_ids': cited_by_ids,
            'reference_ids': reference_ids
        }
        
        # Clean PMID - remove 'PMID' prefix if present
        pmid = content.get('pmid', '')
        if pmid and pmid.startswith('PMID'):
            pmid_clean = pmid[4:]  # Remove 'PMID' prefix
        else:
            pmid_clean = pmid
        
        # Generate proper URL
        url = content.get('url', '')
        if not url and pmid_clean:
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid_clean}/"
        
        # DEBUG: Check what we're normalizing
        if pmid and pmid.startswith('PMID'):
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"ArticleNormalizer received PMID with prefix: {pmid} -> cleaned to: {pmid_clean}")
        
        # Normalize mesh_terms to simple strings (not complex objects)
        mesh_terms = content.get('mesh_terms', [])
        if mesh_terms and isinstance(mesh_terms[0], dict):
            # Extract just the descriptor names from complex MeSH objects
            mesh_terms = [term.get('descriptor_name', '') for term in mesh_terms if term.get('descriptor_name')]
        
        # Use consolidated fields structure
        return {
            'id': pmid_clean or content.get('id'),
            'source': 'pubmed',
            'source_id': pmid_clean,
            'title': content.get('title', ''),
            'abstract': content.get('abstract', ''),
            'content': content.get('abstract', ''),  # For articles, content is abstract
            'url': url,
            'authors': content.get('authors', []),
            'published_date': content.get('published_date'),
            'year': content.get('year'),
            'journal': content.get('journal'),
            'doi': content.get('doi'),
            'pmid': pmid_clean,
            'keywords': content.get('keywords', []),
            'mesh_terms': mesh_terms,  # Now normalized to simple strings
            'citations': simplified_citations,  # Use simplified structure
            'ml_score': content.get('ml_score'),
            'ai_confidence': content.get('ai_confidence', content.get('gpt_score')),  # Map to consolidated field
            'final_score': content.get('final_score', content.get('combined_score')),  # Map to consolidated field
            'categories': _map_cats(content.get('categories', content.get('predicted_categories', [])) or []),  # Consolidated categories
            'approval_status': content.get('approval_status', 'pending'),
            # Initialize metrics object
            'metrics': {
                'view_count': content.get('view_count', 0),
                'bookmark_count': content.get('bookmark_count', 0),
                'share_count': content.get('share_count', 0),
                'citation_count': len(cited_by_ids)
            }
        }


class VideoNormalizer(BaseNormalizer):
    """Normalizer for video content."""
    
    def normalize(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize video to unified schema."""
        # Extract authors from channel/presenter info
        authors = []
        if content.get('channel_name'):
            authors.append({'name': content['channel_name'], 'affiliation': 'YouTube'})
        if content.get('presenter'):
            authors.append({'name': content['presenter']})
        
        return {
            'id': content.get('video_id', content.get('id')),
            'source': 'youtube',
            'source_id': content.get('video_id'),
            'title': content.get('title', ''),
            'abstract': content.get('description', ''),
            'content': content.get('transcript', content.get('description', '')),
            'url': content.get('url', f"https://youtube.com/watch?v={content.get('video_id')}"),
            'authors': authors,
            'published_date': content.get('published_date'),
            'year': content.get('year'),
            'channel_name': content.get('channel_name'),
            'duration': content.get('duration'),  # in seconds
            'media_duration': content.get('duration'),  # ML classifier expects this field
            'view_count': content.get('view_count', 0),  # ML classifier expects this field
            'thumbnail_url': content.get('thumbnail_url'),
            'keywords': content.get('tags', []),
            'ml_score': content.get('ml_score'),
            'ai_confidence': content.get('ai_confidence', content.get('gpt_score')),
            'final_score': content.get('final_score', content.get('combined_score')),
            'categories': _map_cats(content.get('categories', content.get('predicted_categories', [])) or []),
            'approval_status': content.get('approval_status', 'pending'),
            # Initialize metrics object
            'metrics': {
                'view_count': content.get('view_count', 0),
                'bookmark_count': content.get('like_count', 0),
                'share_count': 0,
                'citation_count': 0
            },
            # Simplified citations (videos typically don't have citations)
            'citations': {
                'cited_by_count': 0,
                'references_count': 0,
                'cited_by_ids': [],
                'reference_ids': []
            }
        }


class RepositoryNormalizer(BaseNormalizer):
    """Normalizer for repository content."""

    def normalize(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize repository to unified schema."""
        # Extract authors from owner/contributors
        authors = []
        if content.get('owner'):
            authors.append({'name': content['owner'], 'affiliation': 'GitHub'})

        # Add contributors as authors with their usernames
        contributors_list = content.get('contributors', [])
        if isinstance(contributors_list, list):
            for contributor in contributors_list[:5]:  # Top 5 contributors
                if isinstance(contributor, str):
                    authors.append({'name': contributor})

        return {
            'id': content.get('repo_id', content.get('id')),
            'source': 'github',
            'source_id': content.get('full_name'),  # e.g., "OHDSI/Atlas"
            'title': content.get('name', ''),
            'abstract': content.get('description', ''),
            'content': content.get('readme', ''),
            'url': content.get('html_url', content.get('url')),
            'authors': authors,
            'published_date': content.get('created_at'),
            'year': datetime.fromisoformat(content.get('created_at', '2020-01-01')).year,

            # GitHub-specific fields - map all fields from scanner
            'repo_name': content.get('full_name'),  # Full repo name
            'owner': content.get('owner'),
            'language': content.get('language'),
            'stars_count': content.get('stargazers_count', 0),
            'watchers_count': content.get('watchers_count', 0),
            'forks_count': content.get('forks_count', 0),
            'open_issues_count': content.get('open_issues_count', 0),
            'contributors_count': content.get('contributor_count', 0),
            'contributors': content.get('contributors', []),  # List of contributor usernames
            'readme_content': content.get('readme', ''),  # README for display
            'topics': content.get('topics', []),
            'license': content.get('license'),  # License name
            'default_branch': content.get('default_branch', 'main'),
            'created_at': content.get('created_at'),
            'updated_at': content.get('updated_at'),
            'pushed_at': content.get('pushed_at'),
            'last_commit': content.get('pushed_at'),  # Map to last_commit for consistency

            'keywords': content.get('topics', []),
            'ml_score': content.get('ml_score'),
            'ai_confidence': content.get('ai_confidence', content.get('gpt_score')),
            'final_score': content.get('final_score', content.get('combined_score')),
            'categories': _map_cats(content.get('categories', content.get('predicted_categories', [])) or []),
            'approval_status': content.get('approval_status', 'pending'),

            # Initialize metrics object
            'metrics': {
                'view_count': content.get('watchers_count', 0),
                'bookmark_count': content.get('stargazers_count', 0),
                'share_count': content.get('forks_count', 0),
                'citation_count': 0
            },

            # Simplified citations (repos typically don't have citations)
            'citations': {
                'cited_by_count': 0,
                'references_count': 0,
                'cited_by_ids': [],
                'reference_ids': []
            }
        }


class DiscussionNormalizer(BaseNormalizer):
    """Normalizer for forum discussion content."""
    
    def normalize(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize discussion to unified schema."""
        # Extract authors from participants
        authors = []
        if content.get('poster_username'):
            authors.append({'name': content['poster_username']})
        for participant in content.get('participants', [])[:5]:  # Top 5 participants
            if participant.get('username') and participant['username'] != content.get('poster_username'):
                authors.append({'name': participant['username']})
        
        # Use summary or excerpt as abstract
        abstract = content.get('summary', content.get('excerpt', content.get('blurb', '')))
        
        # Extract content from key points or first post
        content_text = abstract
        if content.get('key_points'):
            content_text = '\n'.join(str(x) for x in content['key_points'])
        elif content.get('posts') and len(content['posts']) > 0:
            # Get first post content
            first_post = content['posts'][0]
            if first_post.get('cooked'):
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(first_post['cooked'], 'html.parser')
                content_text = soup.get_text()[:2000]  # First 2000 chars
        
        return {
            'id': content.get('topic_id', content.get('id')),
            'source': 'discourse',
            'source_id': str(content.get('topic_id')),
            'title': content.get('title', ''),
            'abstract': abstract[:500] if abstract else '',
            'content': content_text,
            'url': content.get('url'),
            'authors': authors,
            'published_date': content.get('created_at'),
            'updated_date': content.get('last_posted_at', content.get('bumped_at')),
            'year': datetime.fromisoformat(content.get('created_at', '2020-01-01').replace('Z', '+00:00')).year if content.get('created_at') else datetime.now().year,
            'discussion_type': content.get('discussion_type', 'general_discussion'),
            'reply_count': content.get('reply_count', 0),
            'answer_count': content.get('reply_count', 0),  # ML classifier expects this field
            'posts_count': content.get('posts_count', 0),
            'view_count': content.get('views', 0),
            'like_count': content.get('like_count', 0),
            'solved': content.get('content_analysis', {}).get('has_solution', False),
            'pinned': content.get('pinned', False),
            'closed': content.get('closed', False),
            'archived': content.get('archived', False),
            'tags': content.get('tags', []),
            'category_id': content.get('category_id'),
            'engagement_score': content.get('engagement_metrics', {}).get('engagement_score', 0),
            'ohdsi_relevance': content.get('ohdsi_relevance', 0),
            'keywords': content.get('tags', []),
            'ml_score': content.get('ml_score'),
            'ai_confidence': content.get('ai_confidence', content.get('gpt_score')),
            'final_score': content.get('final_score', content.get('combined_score')),
            'categories': _map_cats(content.get('categories', content.get('predicted_categories', [])) or []),
            'approval_status': content.get('approval_status', 'pending'),
            # Initialize metrics object
            'metrics': {
                'view_count': content.get('views', 0),
                'bookmark_count': content.get('like_count', 0),
                'share_count': 0,
                'citation_count': 0
            },
            # Simplified citations
            'citations': {
                'cited_by_count': 0,
                'references_count': 0,
                'cited_by_ids': [],
                'reference_ids': []
            }
        }


class DocumentationNormalizer(BaseNormalizer):
    """Normalizer for documentation content."""
    
    def normalize(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize documentation to unified schema."""
        # Extract authors from contributors or default to OHDSI
        authors = content.get('authors', [{'name': 'OHDSI Community', 'affiliation': 'OHDSI'}])
        
        # Use content_summary or first part of content as abstract
        abstract = content.get('content_summary', content.get('summary', ''))
        if not abstract and content.get('content'):
            abstract = content['content'][:500]
        
        # Extract keywords from search_keywords or key_concepts
        keywords = content.get('search_keywords', [])
        if not keywords and content.get('key_concepts'):
            keywords = [c.lower() for c in content['key_concepts'][:10]]
        
        return {
            'id': content.get('doc_id', content.get('id')),
            'source': 'wiki',
            'source_id': content.get('doc_id'),
            'title': content.get('title', ''),
            'abstract': abstract[:500] if abstract else '',
            'content': content.get('content', '')[:5000],  # Limit content size
            'url': content.get('url'),
            'authors': authors,
            'published_date': content.get('scraped_at'),
            'updated_date': content.get('last_updated', content.get('scraped_at')),
            'year': datetime.now().year,  # Documentation is current
            'source_name': content.get('source_name'),
            'section': content.get('section'),
            'doc_type': content.get('doc_type', 'reference'),
            'doc_version': content.get('version_info', {}).get('version'),
            'has_code': content.get('has_code', False),
            'code_examples': len(content.get('code_examples', [])),
            'headings': content.get('headings', []),
            'related_tools': content.get('related_tools', []),
            'target_audience': content.get('metadata', {}).get('target_audience', []),
            'complexity_level': content.get('metadata', {}).get('complexity_level', 'intermediate'),
            'quality_indicators': content.get('quality_indicators', {}),
            'learning_objectives': content.get('learning_objectives', []),
            'prerequisites': content.get('prerequisites', []),
            'is_ohdsi': content.get('is_ohdsi', False),
            'ohdsi_mentions': content.get('ohdsi_mentions', {}),
            'keywords': keywords,
            'ml_score': content.get('ml_score'),
            'ai_confidence': content.get('ai_confidence', content.get('gpt_score')),
            'final_score': content.get('final_score', content.get('combined_score')),
            'categories': _map_cats(content.get('categories', content.get('predicted_categories', [])) or []),
            'approval_status': content.get('approval_status', 'pending'),
            'last_modified': content.get('last_updated', content.get('scraped_at')),
            # Initialize metrics object
            'metrics': {
                'view_count': 0,
                'bookmark_count': 0,
                'share_count': 0,
                'citation_count': 0
            },
            # Simplified citations
            'citations': {
                'cited_by_count': 0,
                'references_count': 0,
                'cited_by_ids': [],
                'reference_ids': []
            }
        }