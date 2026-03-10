"""
Discourse forum fetcher for OHDSI community discussions.
Fetches and processes discussions from OHDSI forums.
"""

import os
import re
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from urllib.parse import urljoin

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.base_fetcher import BaseFetcher
from shared.ohdsi_constants import (
    DISCOURSE_MONITORED_CATEGORIES,
    DISCOURSE_SEARCH_TERMS,
    OHDSI_KEYWORDS,
    OHDSI_TAG_KEYWORDS,
    OHDSI_DISCOURSE_CATEGORY_IDS,
)
from shared.content_relevance import is_ohdsi_related

logger = logging.getLogger(__name__)


class DiscourseFetcher(BaseFetcher):
    """
    Fetches discussions from OHDSI Discourse forums.
    """

    # OHDSI Forum URL
    OHDSI_FORUM_URL = "https://forums.ohdsi.org"

    # Categories to monitor
    MONITORED_CATEGORIES = DISCOURSE_MONITORED_CATEGORIES

    # Search terms for finding relevant discussions
    SEARCH_TERMS = DISCOURSE_SEARCH_TERMS
    
    def __init__(self, forum_url: str = None, api_key: str = None):
        """
        Initialize Discourse fetcher.
        
        Args:
            forum_url: Base URL of the Discourse forum
            api_key: Optional API key for authenticated requests
        """
        super().__init__(
            source_name='discourse',
            rate_limit=2.0,  # 2 requests per second
            cache_ttl=3600 * 3  # Cache for 3 hours
        )
        
        self.forum_url = forum_url or self.OHDSI_FORUM_URL
        self.api_key = api_key or os.getenv('DISCOURSE_API_KEY')
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'OHDSI-Dashboard/1.0',
            'Accept': 'application/json'
        })
        
        if self.api_key:
            self.session.headers['Api-Key'] = self.api_key
            self.session.headers['Api-Username'] = 'system'
            logger.info("Discourse API key configured")
        else:
            logger.warning("No Discourse API key provided. Some features may be limited.")
    
    def fetch_latest_topics(self, max_topics: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch the latest topics from the forum.
        
        Args:
            max_topics: Maximum number of topics to fetch
            
        Returns:
            List of topic details
        """
        topics = []
        page = 0
        
        while len(topics) < max_topics:
            try:
                # Fetch latest topics
                url = urljoin(self.forum_url, f'/latest.json?page={page}')
                response = self.session.get(url)
                response.raise_for_status()
                
                data = response.json()
                topic_list = data.get('topic_list', {})
                
                if not topic_list.get('topics'):
                    break
                
                for topic_data in topic_list['topics']:
                    topic = self._parse_topic(topic_data, data.get('users', []))
                    if topic:
                        topics.append(topic)
                        
                        if len(topics) >= max_topics:
                            break
                
                page += 1
                
                # Rate limiting
                self._enforce_rate_limit()
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching latest topics: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error fetching topics: {e}")
                break
        
        logger.info(f"Fetched {len(topics)} latest topics")
        return topics[:max_topics]
    
    def fetch_category_topics(self, category_slug: str, 
                            max_topics: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch topics from a specific category.
        
        Args:
            category_slug: Category slug/name
            max_topics: Maximum number of topics
            
        Returns:
            List of topic details
        """
        topics = []
        page = 0
        
        while len(topics) < max_topics:
            try:
                # Fetch category topics
                url = urljoin(self.forum_url, f'/c/{category_slug}.json?page={page}')
                response = self.session.get(url)
                
                if response.status_code == 404:
                    logger.warning(f"Category not found: {category_slug}")
                    break
                
                response.raise_for_status()
                data = response.json()
                
                topic_list = data.get('topic_list', {})
                if not topic_list.get('topics'):
                    break
                
                for topic_data in topic_list['topics']:
                    topic = self._parse_topic(topic_data, data.get('users', []))
                    if topic:
                        topics.append(topic)
                        
                        if len(topics) >= max_topics:
                            break
                
                page += 1
                
                # Rate limiting
                self._enforce_rate_limit()
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching category {category_slug}: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                break
        
        logger.info(f"Fetched {len(topics)} topics from category {category_slug}")
        return topics[:max_topics]
    
    def fetch_topic_details(self, topic_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed information about a specific topic.
        
        Args:
            topic_id: Topic ID
            
        Returns:
            Topic details with posts
        """
        try:
            url = urljoin(self.forum_url, f'/t/{topic_id}.json')
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse topic with posts
            topic = {
                'topic_id': data.get('id'),
                'title': data.get('title'),
                'category_id': data.get('category_id'),
                'created_at': data.get('created_at'),
                'posts_count': data.get('posts_count'),
                'views': data.get('views'),
                'like_count': data.get('like_count'),
                'tags': data.get('tags', []),
                'posts': []
            }
            
            # Parse posts
            post_stream = data.get('post_stream', {})
            posts = post_stream.get('posts', [])
            
            for post_data in posts[:20]:  # Limit to first 20 posts
                post = {
                    'post_number': post_data.get('post_number'),
                    'username': post_data.get('username'),
                    'cooked': post_data.get('cooked'),  # HTML content
                    'created_at': post_data.get('created_at'),
                    'updated_at': post_data.get('updated_at'),
                    'likes': post_data.get('actions_summary', [{}])[0].get('count', 0)
                        if post_data.get('actions_summary') else 0,
                    'reply_count': post_data.get('reply_count', 0)
                }
                topic['posts'].append(post)
            
            # Rate limiting
            self._enforce_rate_limit()
            
            return topic
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching topic {topic_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    def search_topics(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Search for topics matching a query.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of matching topics
        """
        topics = []
        
        try:
            url = urljoin(self.forum_url, '/search.json')
            params = {
                'q': query,
                'type': 'topics'
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            for topic_data in data.get('topics', [])[:max_results]:
                topic = self._parse_search_result(topic_data)
                if topic:
                    topics.append(topic)
            
            # Rate limiting
            self._enforce_rate_limit()
            
            logger.info(f"Found {len(topics)} topics for query: {query}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching topics: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        
        return topics
    
    def fetch_ohdsi_content(self, max_results_per_category: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch OHDSI-related discussions from multiple sources.
        
        Args:
            max_results_per_category: Maximum results per category
            
        Returns:
            List of OHDSI-related discussions
        """
        all_topics = []
        seen_ids = set()
        
        # Fetch from monitored categories
        for category in self.MONITORED_CATEGORIES:
            topics = self.fetch_category_topics(category, max_results_per_category)
            for topic in topics:
                topic_id = topic.get('topic_id')
                if topic_id and topic_id not in seen_ids:
                    all_topics.append(topic)
                    seen_ids.add(topic_id)
        
        # Search for OHDSI-specific terms
        for term in self.SEARCH_TERMS[:5]:  # Limit to avoid too many API calls
            topics = self.search_topics(term, max_results_per_category)
            for topic in topics:
                topic_id = topic.get('topic_id')
                if topic_id and topic_id not in seen_ids:
                    all_topics.append(topic)
                    seen_ids.add(topic_id)
        
        # Fetch latest topics and filter for OHDSI relevance
        latest_topics = self.fetch_latest_topics(100)
        for topic in latest_topics:
            topic_id = topic.get('topic_id')
            if topic_id and topic_id not in seen_ids:
                if self._is_ohdsi_related(topic):
                    all_topics.append(topic)
                    seen_ids.add(topic_id)
        
        logger.info(f"Found {len(all_topics)} unique OHDSI-related topics")
        
        # Sort by activity (replies + views)
        all_topics.sort(
            key=lambda x: x.get('reply_count', 0) + x.get('views', 0), 
            reverse=True
        )
        
        return all_topics
    
    def _parse_topic(self, topic_data: Dict[str, Any], 
                    users: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Parse topic data from API response."""
        try:
            # Find user details
            poster_username = None
            if topic_data.get('posters'):
                first_poster = topic_data['posters'][0] if topic_data['posters'] else {}
                user_id = first_poster.get('user_id')
                for user in users:
                    if user.get('id') == user_id:
                        poster_username = user.get('username')
                        break
            
            return {
                'topic_id': topic_data.get('id'),
                'title': topic_data.get('title'),
                'slug': topic_data.get('slug'),
                'category_id': topic_data.get('category_id'),
                'created_at': topic_data.get('created_at'),
                'last_posted_at': topic_data.get('last_posted_at'),
                'bumped_at': topic_data.get('bumped_at'),
                'views': topic_data.get('views', 0),
                'reply_count': topic_data.get('reply_count', 0),
                'like_count': topic_data.get('like_count', 0),
                'posts_count': topic_data.get('posts_count', 0),
                'pinned': topic_data.get('pinned', False),
                'visible': topic_data.get('visible', True),
                'closed': topic_data.get('closed', False),
                'archived': topic_data.get('archived', False),
                'tags': topic_data.get('tags', []),
                'excerpt': topic_data.get('excerpt', ''),
                'poster_username': poster_username,
                'url': urljoin(self.forum_url, f'/t/{topic_data.get("slug")}/{topic_data.get("id")}'),
                'content_type': 'discussion',
                'source': 'discourse'
            }
        except Exception as e:
            logger.error(f"Error parsing topic: {e}")
            return None
    
    def _parse_search_result(self, topic_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse search result topic."""
        try:
            return {
                'topic_id': topic_data.get('id'),
                'title': topic_data.get('title'),
                'slug': topic_data.get('slug'),
                'category_id': topic_data.get('category_id'),
                'created_at': topic_data.get('created_at'),
                'views': topic_data.get('views', 0),
                'reply_count': topic_data.get('reply_count', 0),
                'like_count': topic_data.get('like_count', 0),
                'posts_count': topic_data.get('posts_count', 0),
                'tags': topic_data.get('tags', []),
                'blurb': topic_data.get('blurb', ''),  # Search excerpt
                'url': urljoin(self.forum_url, f'/t/{topic_data.get("slug")}/{topic_data.get("id")}'),
                'content_type': 'discussion',
                'source': 'discourse'
            }
        except Exception as e:
            logger.error(f"Error parsing search result: {e}")
            return None
    
    def _is_ohdsi_related(self, topic: Dict[str, Any]) -> bool:
        """
        Check if a topic is OHDSI-related.

        Args:
            topic: Topic details

        Returns:
            True if topic appears OHDSI-related
        """
        # Check title
        title = topic.get('title', '')
        if is_ohdsi_related(title):
            return True

        # Check excerpt/blurb
        excerpt = topic.get('excerpt', '') or topic.get('blurb', '')
        if excerpt and is_ohdsi_related(excerpt):
            return True

        # Check tags
        tags = [tag.lower() for tag in topic.get('tags', [])]
        for keyword in OHDSI_TAG_KEYWORDS:
            if keyword in tags:
                return True

        # Check if in OHDSI-specific category
        category_id = topic.get('category_id')
        if category_id in OHDSI_DISCOURSE_CATEGORY_IDS:
            return True

        return False
    
    def analyze_discussion_quality(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze discussion quality metrics.
        
        Args:
            topic: Topic details
            
        Returns:
            Quality metrics
        """
        quality = {
            'engagement_score': 0.0,
            'activity_score': 0.0,
            'content_score': 0.0,
            'overall_score': 0.0
        }
        
        # Engagement score (views, likes, replies)
        views = topic.get('views', 0)
        if views > 1000:
            quality['engagement_score'] += 0.3
        elif views > 100:
            quality['engagement_score'] += 0.15
        elif views > 10:
            quality['engagement_score'] += 0.05
        
        reply_count = topic.get('reply_count', 0)
        if reply_count > 20:
            quality['engagement_score'] += 0.3
        elif reply_count > 5:
            quality['engagement_score'] += 0.15
        elif reply_count > 0:
            quality['engagement_score'] += 0.05
        
        like_count = topic.get('like_count', 0)
        if like_count > 10:
            quality['engagement_score'] += 0.2
        elif like_count > 3:
            quality['engagement_score'] += 0.1
        elif like_count > 0:
            quality['engagement_score'] += 0.05
        
        # Activity score (recency)
        if topic.get('last_posted_at'):
            try:
                last_posted = datetime.fromisoformat(
                    topic['last_posted_at'].replace('Z', '+00:00')
                )
                age = datetime.now() - last_posted
                if age < timedelta(days=7):
                    quality['activity_score'] += 0.5
                elif age < timedelta(days=30):
                    quality['activity_score'] += 0.3
                elif age < timedelta(days=90):
                    quality['activity_score'] += 0.2
                elif age < timedelta(days=365):
                    quality['activity_score'] += 0.1
            except:
                pass
        
        # Content score
        if topic.get('pinned'):
            quality['content_score'] += 0.3
        
        if topic.get('tags'):
            quality['content_score'] += 0.1
        
        excerpt = topic.get('excerpt', '') or topic.get('blurb', '')
        if len(excerpt) > 200:
            quality['content_score'] += 0.2
        elif len(excerpt) > 50:
            quality['content_score'] += 0.1
        
        # Check for OHDSI-specific content
        if self._is_ohdsi_related(topic):
            quality['content_score'] += 0.3
        
        # Calculate overall score
        quality['overall_score'] = (
            quality['engagement_score'] * 0.4 +
            quality['activity_score'] * 0.3 +
            quality['content_score'] * 0.3
        )
        
        return quality
    
    def _fetch_single(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Implementation of abstract method from BaseFetcher.
        
        Args:
            query: Query parameters
            
        Returns:
            List of topics
        """
        query_type = query.get('type', 'latest')
        
        if query_type == 'latest':
            return self.fetch_latest_topics(query.get('max_results', 50))
        
        elif query_type == 'category':
            return self.fetch_category_topics(
                query.get('category'),
                query.get('max_results', 50)
            )
        
        elif query_type == 'search':
            return self.search_topics(
                query.get('q', 'OHDSI'),
                query.get('max_results', 50)
            )
        
        elif query_type == 'topic_details':
            topic = self.fetch_topic_details(query.get('topic_id'))
            return [topic] if topic else []
        
        else:
            logger.warning(f"Unknown query type: {query_type}")
            return []
    
    def search(self, query: str, max_results: int = 100, 
              filters: Dict[str, Any] = None) -> List[str]:
        """
        Search for discussion IDs matching the query.
        
        Args:
            query: Search query string
            max_results: Maximum number of results
            filters: Additional filters
            
        Returns:
            List of topic IDs as strings
        """
        topics = self.search_topics(query, max_results)
        return [str(topic['topic_id']) for topic in topics if topic.get('topic_id')]
    
    def fetch_details(self, content_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch detailed information for topic IDs.
        
        Args:
            content_ids: List of topic IDs as strings
            
        Returns:
            List of topic details
        """
        results = []
        for topic_id in content_ids:
            try:
                topic = self.fetch_topic_details(int(topic_id))
                if topic:
                    results.append(topic)
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid topic ID {topic_id}: {e}")
            except Exception as e:
                logger.error(f"Error fetching topic {topic_id}: {e}")
        return results