"""
Quality scoring utility for different content types.
"""

import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QualityScorer:
    """
    Calculates quality scores for different content types.
    """
    
    # Weight configurations per content type
    QUALITY_WEIGHTS = {
        'article': {
            'completeness': 0.3,
            'authority': 0.3,
            'recency': 0.2,
            'engagement': 0.2
        },
        'video': {
            'completeness': 0.2,
            'authority': 0.3,
            'recency': 0.2,
            'engagement': 0.3
        },
        'repository': {
            'completeness': 0.3,
            'authority': 0.2,
            'recency': 0.3,
            'engagement': 0.2
        },
        'discussion': {
            'completeness': 0.2,
            'authority': 0.3,
            'recency': 0.1,
            'engagement': 0.4
        },
        'documentation': {
            'completeness': 0.3,
            'authority': 0.4,
            'recency': 0.2,
            'engagement': 0.1
        }
    }
    
    def __init__(self):
        """Initialize quality scorer."""
        self.stats = {
            'total_scored': 0,
            'by_type': {},
            'avg_scores': {}
        }
    
    def calculate_quality_score(self, content: Dict[str, Any]) -> float:
        """
        Calculate overall quality score for content.
        
        Args:
            content: Content to score
            
        Returns:
            Quality score between 0 and 1
        """
        content_type = content.get('content_type', 'article')
        
        # Calculate component scores
        completeness = self._score_completeness(content, content_type)
        authority = self._score_authority(content, content_type)
        recency = self._score_recency(content, content_type)
        engagement = self._score_engagement(content, content_type)
        
        # Get weights for content type
        weights = self.QUALITY_WEIGHTS.get(content_type, {
            'completeness': 0.25,
            'authority': 0.25,
            'recency': 0.25,
            'engagement': 0.25
        })
        
        # Calculate weighted score
        quality_score = (
            completeness * weights['completeness'] +
            authority * weights['authority'] +
            recency * weights['recency'] +
            engagement * weights['engagement']
        )
        
        # Update statistics
        self.stats['total_scored'] += 1
        self.stats['by_type'][content_type] = self.stats['by_type'].get(content_type, 0) + 1
        
        if content_type not in self.stats['avg_scores']:
            self.stats['avg_scores'][content_type] = []
        self.stats['avg_scores'][content_type].append(quality_score)
        
        return min(1.0, max(0.0, quality_score))
    
    def _score_completeness(self, content: Dict[str, Any], content_type: str) -> float:
        """Score content completeness."""
        score = 0.0
        
        if content_type == 'article':
            # Check for essential article fields
            if content.get('title'):
                score += 0.15
            if content.get('abstract') and len(content['abstract']) > 100:
                score += 0.25
            if content.get('authors') and len(content['authors']) > 0:
                score += 0.15
            if content.get('doi'):
                score += 0.15
            if content.get('journal'):
                score += 0.1
            if content.get('keywords') or content.get('mesh_terms'):
                score += 0.1
            if content.get('published_date'):
                score += 0.1
        
        elif content_type == 'video':
            # Check for essential video fields
            if content.get('title'):
                score += 0.2
            if content.get('abstract'):  # Description
                score += 0.15
            if content.get('transcript'):
                score += 0.3
            if content.get('media_duration') and content['media_duration'] > 60:
                score += 0.15
            if content.get('channel_name'):
                score += 0.1
            if content.get('thumbnail_url'):
                score += 0.1
        
        elif content_type == 'repository':
            # Check for essential repository fields
            if content.get('title'):
                score += 0.15
            if content.get('abstract'):  # Description
                score += 0.15
            if content.get('content') and len(content['content']) > 100:  # README
                score += 0.25
            if content.get('programming_language'):
                score += 0.1
            if content.get('license'):
                score += 0.15
            if content.get('topics'):
                score += 0.1
            if content.get('last_commit_date'):
                score += 0.1
        
        elif content_type == 'discussion':
            # Check for essential discussion fields
            if content.get('title') or content.get('question'):
                score += 0.2
            if content.get('accepted_answer') or content.get('best_answer'):
                score += 0.4
            if content.get('answer_count') and content['answer_count'] > 0:
                score += 0.2
            if content.get('tags'):
                score += 0.1
            if content.get('solved'):
                score += 0.1
        
        elif content_type == 'documentation':
            # Check for essential documentation fields
            if content.get('title'):
                score += 0.2
            if content.get('content') and len(content['content']) > 200:
                score += 0.3
            if content.get('doc_version'):
                score += 0.15
            if content.get('doc_section'):
                score += 0.15
            if content.get('is_official'):
                score += 0.2
        
        return min(1.0, score)
    
    def _score_authority(self, content: Dict[str, Any], content_type: str) -> float:
        """Score content authority/credibility."""
        score = 0.5  # Base score
        
        if content_type == 'article':
            # Check journal quality, author credentials
            authors = content.get('authors', [])
            if len(authors) > 3:
                score += 0.1
            if len(authors) > 10:
                score += 0.1
            
            # Known good journals
            journal = (content.get('journal') or '').lower()
            if any(term in journal for term in ['nature', 'science', 'lancet', 'nejm', 'jama']):
                score += 0.2
            elif any(term in journal for term in ['plos', 'bmc', 'journal', 'ieee']):
                score += 0.1
        
        elif content_type == 'video':
            # Check channel authority
            channel = (content.get('channel_name') or '').lower()
            if 'ohdsi' in channel:
                score = 1.0  # Official OHDSI content
            elif any(term in channel for term in ['university', 'institute', 'conference']):
                score += 0.3
            
            # View count as proxy for authority
            views = content.get('view_count', 0)
            if views > 10000:
                score += 0.2
            elif views > 1000:
                score += 0.1
        
        elif content_type == 'repository':
            # Check owner and community engagement
            owner = (content.get('owner') or '').lower()
            if owner == 'ohdsi':
                score = 1.0  # Official OHDSI repository
            elif any(term in owner for term in ['university', 'institute', 'lab']):
                score += 0.2
            
            # Stars as proxy for authority
            stars = content.get('stars_count', 0)
            if stars > 100:
                score += 0.3
            elif stars > 10:
                score += 0.15
            
            # Contributors
            if len(content.get('authors', [])) > 5:
                score += 0.1
        
        elif content_type == 'discussion':
            # Check for expert involvement
            if content.get('expert_answered'):
                score += 0.3
            if content.get('solved'):
                score += 0.2
            
            # Answer quality
            answers = content.get('answer_count', 0)
            if answers > 5:
                score += 0.1
        
        elif content_type == 'documentation':
            # Official documentation has high authority
            if content.get('is_official'):
                score = 0.9
            
            # Check source
            source = (content.get('source') or '').lower()
            if source == 'wiki' and content.get('is_official'):
                score = 1.0
        
        return min(1.0, score)
    
    def _score_recency(self, content: Dict[str, Any], content_type: str) -> float:
        """Score content recency."""
        score = 0.5  # Base score
        
        # Get the relevant date field
        date_field = None
        if content_type == 'repository':
            date_field = content.get('last_commit_date') or content.get('updated_date')
        elif content_type == 'documentation':
            date_field = content.get('updated_date')
        else:
            date_field = content.get('published_date')
        
        if not date_field:
            return score
        
        try:
            # Parse date
            if isinstance(date_field, str):
                if 'T' in date_field:
                    date = datetime.fromisoformat(date_field.replace('Z', '+00:00'))
                else:
                    date = datetime.strptime(date_field, '%Y-%m-%d')
            else:
                date = date_field
            
            # Calculate age (handle timezone-aware dates)
            now = datetime.now()
            if date.tzinfo is not None:
                # Date is timezone-aware, make now timezone-aware too
                from datetime import timezone
                now = datetime.now(timezone.utc)
            age = now - date
            
            # Score based on age
            if age < timedelta(days=30):
                score = 1.0  # Very recent
            elif age < timedelta(days=90):
                score = 0.9  # Recent
            elif age < timedelta(days=180):
                score = 0.8  # Fairly recent
            elif age < timedelta(days=365):
                score = 0.7  # Within a year
            elif age < timedelta(days=365 * 2):
                score = 0.6  # Within 2 years
            elif age < timedelta(days=365 * 3):
                score = 0.5  # Within 3 years
            elif age < timedelta(days=365 * 5):
                score = 0.4  # Within 5 years
            else:
                score = 0.3  # Older
            
            # Adjust for content type
            if content_type == 'documentation':
                # Documentation needs to be more recent
                score = score * 0.8 if age > timedelta(days=365) else score
            elif content_type == 'article':
                # Academic articles can be older and still relevant
                score = min(score + 0.1, 1.0)
        
        except Exception as e:
            logger.warning(f"Failed to parse date: {date_field}, error: {e}")
        
        return score
    
    def _score_engagement(self, content: Dict[str, Any], content_type: str) -> float:
        """Score content engagement/popularity."""
        score = 0.3  # Base score
        
        if content_type == 'article':
            # Citations and metrics
            citations = content.get('citations', {})
            if citations.get('citation_count', 0) > 50:
                score += 0.4
            elif citations.get('citation_count', 0) > 10:
                score += 0.2
            elif citations.get('citation_count', 0) > 0:
                score += 0.1
            
            # View/bookmark counts
            if content.get('view_count', 0) > 100:
                score += 0.2
            if content.get('bookmark_count', 0) > 10:
                score += 0.1
        
        elif content_type == 'video':
            # Views and likes
            views = content.get('view_count', 0)
            if views > 10000:
                score += 0.3
            elif views > 1000:
                score += 0.2
            elif views > 100:
                score += 0.1
            
            likes = content.get('like_count', 0)
            if views > 0:
                like_ratio = likes / views
                if like_ratio > 0.1:
                    score += 0.2
                elif like_ratio > 0.05:
                    score += 0.1
        
        elif content_type == 'repository':
            # Stars and forks
            stars = content.get('stars_count', 0)
            if stars > 100:
                score += 0.3
            elif stars > 10:
                score += 0.15
            
            forks = content.get('forks_count', 0)
            if forks > 50:
                score += 0.2
            elif forks > 10:
                score += 0.1
            
            # Recent activity
            if content.get('open_issues_count', 0) > 0:
                score += 0.05  # Active development
        
        elif content_type == 'discussion':
            # Views and answers
            views = content.get('view_count', 0)
            if views > 1000:
                score += 0.2
            elif views > 100:
                score += 0.1
            
            answers = content.get('answer_count', 0)
            if answers > 10:
                score += 0.2
            elif answers > 3:
                score += 0.1
            
            # Likes
            if content.get('like_count', 0) > 10:
                score += 0.1
        
        elif content_type == 'documentation':
            # Documentation engagement is less important
            if content.get('view_count', 0) > 1000:
                score += 0.2
            
            # Child pages indicate comprehensive documentation
            if len(content.get('child_pages', [])) > 5:
                score += 0.2
        
        return min(1.0, score)
    
    def get_quality_details(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed quality breakdown.
        
        Args:
            content: Content to analyze
            
        Returns:
            Detailed quality scores
        """
        content_type = content.get('content_type', 'article')
        
        return {
            'overall': self.calculate_quality_score(content),
            'completeness': self._score_completeness(content, content_type),
            'authority': self._score_authority(content, content_type),
            'recency': self._score_recency(content, content_type),
            'engagement': self._score_engagement(content, content_type),
            'content_type': content_type
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get quality scorer statistics."""
        stats = self.stats.copy()
        
        # Calculate average scores
        for content_type, scores in self.stats['avg_scores'].items():
            if scores:
                stats['avg_scores'][content_type] = sum(scores) / len(scores)
        
        return stats
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            'total_scored': 0,
            'by_type': {},
            'avg_scores': {}
        }