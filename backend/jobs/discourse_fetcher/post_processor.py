"""
Post processor for Discourse forum content.
Extracts structured information from forum posts and discussions.
"""

import os
import sys
import re
import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.ohdsi_constants import OHDSI_TERMS, OHDSI_DISCOURSE_CATEGORY_IDS, OHDSI_TAG_KEYWORDS

logger = logging.getLogger(__name__)


class PostProcessor:
    """
    Processes forum posts to extract structured information.
    """

    def __init__(self):
        """Initialize post processor."""

        # OHDSI-specific terminology (from shared constants)
        self.ohdsi_terms = OHDSI_TERMS
        
        # Common question patterns
        self.question_patterns = [
            r'how (?:do|can|to)',
            r'what (?:is|are|does)',
            r'where (?:is|can|do)',
            r'when (?:should|does|is)',
            r'why (?:is|does|do)',
            r'is (?:it|there|this)',
            r'can (?:i|we|you|someone)',
            r'should (?:i|we)',
            r'has anyone',
            r'does anyone',
            r'looking for',
            r'need help',
            r'seeking advice'
        ]
    
    def process_discussion(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a discussion topic to extract structured information.
        
        Args:
            topic: Raw topic data from Discourse
            
        Returns:
            Processed discussion with extracted information
        """
        processed = {
            'topic_id': topic.get('topic_id'),
            'title': topic.get('title', ''),
            'url': topic.get('url', ''),
            'created_at': topic.get('created_at'),
            'last_activity': topic.get('last_posted_at') or topic.get('bumped_at'),
            'category_id': topic.get('category_id'),
            'tags': topic.get('tags', []),
            'statistics': self._extract_statistics(topic),
            'engagement_metrics': self._calculate_engagement(topic),
            'content_analysis': self._analyze_content(topic),
            'discussion_type': self._classify_discussion(topic),
            'participants': self._extract_participants(topic),
            'key_points': self._extract_key_points(topic),
            'ohdsi_relevance': self._calculate_ohdsi_relevance(topic),
            'quality_score': self._calculate_quality_score(topic)
        }
        
        # Process individual posts if available
        if topic.get('posts'):
            processed['posts_analysis'] = self._analyze_posts(topic['posts'])
        
        return processed
    
    def _extract_statistics(self, topic: Dict[str, Any]) -> Dict[str, int]:
        """Extract discussion statistics."""
        return {
            'views': topic.get('views', 0),
            'replies': topic.get('reply_count', 0),
            'likes': topic.get('like_count', 0),
            'posts': topic.get('posts_count', 0),
            'unique_participants': len(set(
                p.get('username') for p in topic.get('posts', [])
                if p.get('username')
            ))
        }
    
    def _calculate_engagement(self, topic: Dict[str, Any]) -> Dict[str, float]:
        """Calculate engagement metrics."""
        views = topic.get('views', 0)
        replies = topic.get('reply_count', 0)
        likes = topic.get('like_count', 0)
        
        metrics = {
            'reply_rate': replies / max(views, 1),
            'like_rate': likes / max(views, 1),
            'avg_likes_per_post': likes / max(topic.get('posts_count', 1), 1),
            'discussion_depth': min(replies / 10, 1.0)  # Normalized to 0-1
        }
        
        # Engagement score (0-1)
        metrics['engagement_score'] = (
            metrics['reply_rate'] * 0.3 +
            metrics['like_rate'] * 0.3 +
            metrics['avg_likes_per_post'] * 0.2 +
            metrics['discussion_depth'] * 0.2
        )
        
        return metrics
    
    def _analyze_content(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze content of discussion."""
        analysis = {
            'is_question': False,
            'is_announcement': False,
            'is_help_request': False,
            'is_discussion': False,
            'has_solution': False,
            'mentioned_tools': [],
            'mentioned_concepts': [],
            'code_snippets': 0,
            'links_count': 0,
            'images_count': 0
        }
        
        title_lower = topic.get('title', '').lower()
        excerpt = topic.get('excerpt', '').lower() or topic.get('blurb', '').lower()
        
        # Check if it's a question
        if '?' in title_lower or any(
            re.search(pattern, title_lower) for pattern in self.question_patterns
        ):
            analysis['is_question'] = True
        
        # Check if it's an announcement
        if topic.get('pinned') or 'announcement' in title_lower:
            analysis['is_announcement'] = True
        
        # Check if it's a help request
        help_keywords = ['help', 'issue', 'problem', 'error', 'stuck', 'advice']
        if any(keyword in title_lower for keyword in help_keywords):
            analysis['is_help_request'] = True
        
        # Default to discussion if none of the above
        if not (analysis['is_question'] or analysis['is_announcement'] or 
                analysis['is_help_request']):
            analysis['is_discussion'] = True
        
        # Check for mentioned tools and concepts
        combined_text = f"{title_lower} {excerpt}"
        
        for tool in self.ohdsi_terms['tools']:
            if tool in combined_text:
                analysis['mentioned_tools'].append(tool)
        
        for concept in self.ohdsi_terms['concepts']:
            if concept in combined_text:
                analysis['mentioned_concepts'].append(concept)
        
        # Analyze posts if available
        if topic.get('posts'):
            for post in topic['posts']:
                content = post.get('cooked', '')
                if content:
                    # Count code snippets
                    analysis['code_snippets'] += len(
                        re.findall(r'<code>|<pre>', content)
                    )
                    # Count links
                    analysis['links_count'] += len(
                        re.findall(r'<a\s+href=', content)
                    )
                    # Count images
                    analysis['images_count'] += len(
                        re.findall(r'<img\s+', content)
                    )
                    
                    # Check if any post is marked as solution
                    if 'solution' in content.lower() or 'solved' in content.lower():
                        analysis['has_solution'] = True
        
        # Remove duplicates
        analysis['mentioned_tools'] = list(set(analysis['mentioned_tools']))
        analysis['mentioned_concepts'] = list(set(analysis['mentioned_concepts']))
        
        return analysis
    
    def _classify_discussion(self, topic: Dict[str, Any]) -> str:
        """Classify the type of discussion."""
        content_analysis = self._analyze_content(topic)
        
        if content_analysis['is_announcement']:
            return 'announcement'
        elif content_analysis['is_question']:
            if content_analysis['has_solution']:
                return 'solved_question'
            else:
                return 'open_question'
        elif content_analysis['is_help_request']:
            return 'help_request'
        elif content_analysis['code_snippets'] > 3:
            return 'technical_discussion'
        elif len(content_analysis['mentioned_tools']) > 2:
            return 'tool_discussion'
        elif len(content_analysis['mentioned_concepts']) > 2:
            return 'conceptual_discussion'
        else:
            return 'general_discussion'
    
    def _extract_participants(self, topic: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract participant information."""
        participants = {}
        
        # Add original poster
        if topic.get('poster_username'):
            participants[topic['poster_username']] = {
                'username': topic['poster_username'],
                'posts_count': 1,
                'is_original_poster': True,
                'likes_received': 0
            }
        
        # Process posts to get all participants
        if topic.get('posts'):
            for post in topic['posts']:
                username = post.get('username')
                if username:
                    if username not in participants:
                        participants[username] = {
                            'username': username,
                            'posts_count': 0,
                            'is_original_poster': False,
                            'likes_received': 0
                        }
                    
                    participants[username]['posts_count'] += 1
                    participants[username]['likes_received'] += post.get('likes', 0)
        
        # Convert to list and sort by contribution
        participant_list = list(participants.values())
        participant_list.sort(
            key=lambda x: x['posts_count'] + x['likes_received'], 
            reverse=True
        )
        
        return participant_list[:10]  # Top 10 participants
    
    def _extract_key_points(self, topic: Dict[str, Any]) -> List[str]:
        """Extract key points from discussion."""
        key_points = []
        
        # Extract from title
        title = topic.get('title', '')
        if title:
            key_points.append(f"Topic: {title}")
        
        # Extract from posts
        if topic.get('posts'):
            for post in topic['posts'][:5]:  # First 5 posts
                content = post.get('cooked', '')
                if content:
                    # Clean HTML
                    soup = BeautifulSoup(content, 'html.parser')
                    text = soup.get_text()
                    
                    # Extract sentences with key indicators
                    sentences = re.split(r'[.!?]', text)
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if len(sentence) > 50 and len(sentence) < 300:
                            # Check for important markers
                            importance_markers = [
                                'important', 'key', 'note', 'solution',
                                'answer', 'resolved', 'fixed', 'summary'
                            ]
                            if any(marker in sentence.lower() for marker in importance_markers):
                                key_points.append(sentence)
                                if len(key_points) >= 5:
                                    break
                
                if len(key_points) >= 5:
                    break
        
        return key_points[:5]  # Limit to 5 key points
    
    def _calculate_ohdsi_relevance(self, topic: Dict[str, Any]) -> float:
        """Calculate OHDSI relevance score."""
        score = 0.0
        
        content_analysis = self._analyze_content(topic)
        
        # Tool mentions
        tool_count = len(content_analysis['mentioned_tools'])
        if tool_count > 3:
            score += 0.3
        elif tool_count > 1:
            score += 0.2
        elif tool_count > 0:
            score += 0.1
        
        # Concept mentions
        concept_count = len(content_analysis['mentioned_concepts'])
        if concept_count > 3:
            score += 0.3
        elif concept_count > 1:
            score += 0.2
        elif concept_count > 0:
            score += 0.1
        
        # Category relevance
        category_id = topic.get('category_id')
        ohdsi_categories = OHDSI_DISCOURSE_CATEGORY_IDS
        if category_id in ohdsi_categories:
            score += 0.2
        
        # Tag relevance
        tags = [tag.lower() for tag in topic.get('tags', [])]
        ohdsi_tags = OHDSI_TAG_KEYWORDS
        if any(tag in ohdsi_tags for tag in tags):
            score += 0.2
        
        return min(1.0, score)
    
    def _calculate_quality_score(self, topic: Dict[str, Any]) -> float:
        """Calculate overall quality score."""
        score = 0.0
        
        # Engagement metrics (30%)
        engagement = self._calculate_engagement(topic)
        score += engagement['engagement_score'] * 0.3
        
        # Content quality (30%)
        content_analysis = self._analyze_content(topic)
        content_score = 0.0
        
        if content_analysis['has_solution']:
            content_score += 0.3
        if content_analysis['code_snippets'] > 0:
            content_score += 0.2
        if content_analysis['links_count'] > 0:
            content_score += 0.1
        if len(content_analysis['mentioned_tools']) > 0:
            content_score += 0.2
        if len(content_analysis['mentioned_concepts']) > 0:
            content_score += 0.2
        
        score += min(1.0, content_score) * 0.3
        
        # OHDSI relevance (20%)
        score += self._calculate_ohdsi_relevance(topic) * 0.2
        
        # Activity recency (20%)
        if topic.get('last_posted_at'):
            try:
                last_posted = datetime.fromisoformat(
                    topic['last_posted_at'].replace('Z', '+00:00')
                )
                age_days = (datetime.now() - last_posted).days
                if age_days < 7:
                    score += 0.2
                elif age_days < 30:
                    score += 0.15
                elif age_days < 90:
                    score += 0.1
                elif age_days < 365:
                    score += 0.05
            except:
                pass
        
        return min(1.0, score)
    
    def _analyze_posts(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze individual posts in the discussion."""
        analysis = {
            'total_posts': len(posts),
            'unique_authors': len(set(p.get('username') for p in posts if p.get('username'))),
            'total_likes': sum(p.get('likes', 0) for p in posts),
            'avg_post_length': 0,
            'code_examples': 0,
            'external_links': 0,
            'quoted_replies': 0,
            'most_liked_post': None
        }
        
        total_length = 0
        max_likes = 0
        
        for post in posts:
            content = post.get('cooked', '')
            if content:
                # Calculate average length
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text()
                total_length += len(text)
                
                # Count code examples
                analysis['code_examples'] += len(
                    soup.find_all(['code', 'pre'])
                )
                
                # Count external links
                for link in soup.find_all('a', href=True):
                    if 'forums.ohdsi.org' not in link['href']:
                        analysis['external_links'] += 1
                
                # Count quoted replies
                if soup.find('blockquote'):
                    analysis['quoted_replies'] += 1
                
                # Track most liked post
                likes = post.get('likes', 0)
                if likes > max_likes:
                    max_likes = likes
                    analysis['most_liked_post'] = {
                        'post_number': post.get('post_number'),
                        'username': post.get('username'),
                        'likes': likes,
                        'excerpt': text[:200] if text else ''
                    }
        
        if posts:
            analysis['avg_post_length'] = total_length // len(posts)
        
        return analysis
    
    def extract_summary(self, topic: Dict[str, Any], max_length: int = 500) -> str:
        """
        Extract a summary of the discussion.
        
        Args:
            topic: Topic data
            max_length: Maximum summary length
            
        Returns:
            Summary text
        """
        summary_parts = []
        
        # Add title
        title = topic.get('title', 'Untitled Discussion')
        summary_parts.append(f"Discussion: {title}")
        
        # Add excerpt if available
        excerpt = topic.get('excerpt', '') or topic.get('blurb', '')
        if excerpt:
            summary_parts.append(excerpt[:200])
        
        # Add key statistics
        stats = self._extract_statistics(topic)
        summary_parts.append(
            f"Activity: {stats['views']} views, {stats['replies']} replies, "
            f"{stats['likes']} likes"
        )
        
        # Add mentioned tools/concepts
        content_analysis = self._analyze_content(topic)
        if content_analysis['mentioned_tools']:
            summary_parts.append(
                f"Tools discussed: {', '.join(content_analysis['mentioned_tools'][:3])}"
            )
        if content_analysis['mentioned_concepts']:
            summary_parts.append(
                f"Topics: {', '.join(content_analysis['mentioned_concepts'][:3])}"
            )
        
        # Combine and truncate
        summary = ' | '.join(summary_parts)
        if len(summary) > max_length:
            summary = summary[:max_length-3] + '...'
        
        return summary