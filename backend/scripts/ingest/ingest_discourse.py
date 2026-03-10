#!/usr/bin/env python3
"""
Ingest Discourse forum discussions for OHDSI Dashboard.
Fetches topics and posts from forums.ohdsi.org.

Usage:
    docker-compose exec backend python /app/scripts/ingest/ingest_discourse.py --max-items 50
    
Options:
    --max-items: Number of topics to fetch (default: 50)
    --category: Specific category to fetch from
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

from jobs.discourse_fetcher.fetcher import DiscourseFetcher
from scripts.ingest.base_ingestion import BaseIngestion, create_argument_parser

logger = logging.getLogger(__name__)


class DiscourseIngestion(BaseIngestion):
    """
    Discourse forum ingestion for OHDSI community discussions.
    """
    
    # Important OHDSI forum categories
    MONITORED_CATEGORIES = [
        'announcements',
        'researchers',
        'implementers',
        'developers',
        'cdm',
        'vocabulary-users',
        'atlas-users',
        'webapi-users',
        'hades-users',
        'study-questions',
        'covid-19',
        'working-groups'
    ]
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Discourse ingestion."""
        super().__init__(source_name='discourse', content_type='discussion', config=config)
        
        try:
            self.fetcher = DiscourseFetcher()
            logger.info("Discourse ingestion initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Discourse fetcher: {e}")
            raise
    
    def fetch_content(
        self,
        max_items: int = 50,
        category_slug: str = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch topics from Discourse forum.
        
        Args:
            max_items: Maximum number of topics to fetch
            category_slug: Specific category to fetch from
            
        Returns:
            List of discussion topics with posts
        """
        all_topics = []
        
        # If specific category provided
        if category_slug:
            logger.info(f"Fetching from category: {category_slug}")
            topics = self._fetch_category_topics(category_slug, max_items)
            all_topics.extend(topics)
        else:
            # Fetch from all monitored categories
            items_per_category = max(1, max_items // len(self.MONITORED_CATEGORIES))
            
            for category in self.MONITORED_CATEGORIES:
                if len(all_topics) >= max_items:
                    break
                topics = self._fetch_category_topics(category, items_per_category)
                all_topics.extend(topics)
            
            # Also fetch latest topics
            if len(all_topics) < max_items:
                remaining = max_items - len(all_topics)
                latest_topics = self._fetch_latest_topics(remaining)
                all_topics.extend(latest_topics)
        
        # Remove duplicates (same topic might appear in multiple categories)
        unique_topics = self._deduplicate_topics(all_topics)
        
        # Fetch full details for each topic
        detailed_topics = self._fetch_topic_details(unique_topics[:max_items])
        
        logger.info(f"Total topics fetched: {len(detailed_topics)}")
        return detailed_topics
    
    def _fetch_category_topics(self, category_slug: str, max_results: int) -> List[Dict[str, Any]]:
        """Fetch topics from a specific category."""
        try:
            logger.info(f"Fetching up to {max_results} topics from category '{category_slug}'")
            topics = self.fetcher.fetch_category_topics(category_slug, max_topics=max_results)
            
            # Process each topic
            processed = []
            for topic in topics:
                # Add Discourse-specific fields
                topic['source'] = 'discourse'
                topic['content_type'] = 'discussion'
                topic['category'] = category_slug
                
                # Ensure ID field
                if 'id' in topic:
                    topic['source_id'] = str(topic['id'])
                    topic['id'] = f"discourse_{topic['id']}"
                
                processed.append(topic)
            
            logger.info(f"Fetched {len(processed)} topics from category '{category_slug}'")
            return processed
            
        except Exception as e:
            logger.error(f"Error fetching from category '{category_slug}': {e}")
            return []
    
    def _fetch_latest_topics(self, max_results: int) -> List[Dict[str, Any]]:
        """Fetch latest topics from the forum."""
        try:
            logger.info(f"Fetching up to {max_results} latest topics")
            topics = self.fetcher.fetch_latest_topics(max_topics=max_results)
            
            # Process each topic
            processed = []
            for topic in topics:
                # Add Discourse-specific fields
                topic['source'] = 'discourse'
                topic['content_type'] = 'discussion'
                
                # Ensure ID field
                if 'id' in topic:
                    topic['source_id'] = str(topic['id'])
                    topic['id'] = f"discourse_{topic['id']}"
                
                processed.append(topic)
            
            logger.info(f"Fetched {len(processed)} latest topics")
            return processed
            
        except Exception as e:
            logger.error(f"Error fetching latest topics: {e}")
            return []
    
    def _fetch_topic_details(self, topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fetch full details for each topic including posts."""
        detailed = []
        
        for topic in topics:
            try:
                # Extract topic ID
                topic_id = topic.get('source_id', '')
                if topic_id and topic_id.isdigit():
                    # Fetch full topic with posts
                    full_topic = self.fetcher.fetch_topic_details(int(topic_id))
                    if full_topic:
                        # Merge with existing data
                        full_topic.update(topic)
                        detailed.append(full_topic)
                    else:
                        # Use partial data if details fetch fails
                        detailed.append(topic)
                else:
                    detailed.append(topic)
            except Exception as e:
                logger.warning(f"Could not fetch details for topic {topic.get('id')}: {e}")
                detailed.append(topic)
        
        return detailed
    
    def _deduplicate_topics(self, topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate topics based on ID."""
        seen = set()
        unique = []
        
        for topic in topics:
            key = topic.get('id', topic.get('source_id', ''))
            if key and key not in seen:
                seen.add(key)
                unique.append(topic)
        
        if len(topics) > len(unique):
            logger.info(f"Removed {len(topics) - len(unique)} duplicate topics")
        
        return unique
    
    def validate_content(self, item: Dict[str, Any]) -> bool:
        """
        Validate that a Discourse topic has required fields.
        
        Args:
            item: Topic to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['title']
        
        for field in required_fields:
            if not item.get(field):
                logger.warning(f"Missing required field '{field}' in topic")
                return False
        
        # Check for OHDSI relevance
        title = item.get('title', '').lower()
        content = item.get('content', '').lower()
        category = item.get('category', '').lower()
        tags = [t.lower() for t in item.get('tags', [])]
        
        ohdsi_keywords = ['ohdsi', 'omop', 'observational health', 'atlas', 'hades', 
                         'achilles', 'cohort', 'cdm', 'common data model', 'webapi',
                         'vocabulary', 'concept', 'phenotype', 'characterization']
        
        # Check if any OHDSI keyword appears
        content_text = f"{title} {content} {category} {' '.join(tags)}"
        has_ohdsi_content = any(keyword in content_text for keyword in ohdsi_keywords)
        
        if not has_ohdsi_content:
            logger.debug(f"Topic '{item.get('title', '')[:50]}...' has no OHDSI keywords")
            # Still return True to process, let ML classifier decide relevance
        
        return True
    
    def process_item(self, item: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Process a Discourse topic with special handling.
        
        Args:
            item: Raw topic data
            
        Returns:
            Processed topic
        """
        # Process through base pipeline
        processed = super().process_item(item, dry_run=dry_run)
        
        if processed:
            # Add Discourse-specific metadata
            processed['source_type'] = 'community'
            processed['display_type'] = 'Forum Discussion'
            processed['icon_type'] = 'chat-bubble-left-right'
            processed['content_category'] = 'community'
            
            # Generate URL if not present
            if 'url' not in processed and 'source_id' in item:
                processed['url'] = f"https://forums.ohdsi.org/t/{item['source_id']}"
            
            # Set dates
            if 'created_at' in item and 'published_date' not in processed:
                processed['published_date'] = item['created_at']
            
            if 'last_posted_at' in item:
                processed['last_activity'] = item['last_posted_at']
            
            # Add engagement metrics
            if 'posts_count' in item:
                processed['post_count'] = item['posts_count']
            if 'reply_count' in item:
                processed['reply_count'] = item['reply_count']
            if 'like_count' in item:
                processed['like_count'] = item['like_count']
            if 'views' in item:
                processed['view_count'] = item['views']
            
            # Determine discussion type
            if 'tags' in item:
                tags_lower = [t.lower() for t in item['tags']]
                if 'solved' in tags_lower or item.get('solution_accepted'):
                    processed['discussion_type'] = 'solved'
                elif 'question' in tags_lower or '?' in item.get('title', ''):
                    processed['discussion_type'] = 'question'
                elif 'announcement' in tags_lower or item.get('category') == 'announcements':
                    processed['discussion_type'] = 'announcement'
                else:
                    processed['discussion_type'] = 'discussion'
            
            # Calculate engagement score
            engagement_score = 0
            if 'views' in item:
                engagement_score += min(item['views'] / 1000, 1.0) * 0.3
            if 'reply_count' in item:
                engagement_score += min(item['reply_count'] / 20, 1.0) * 0.4
            if 'like_count' in item:
                engagement_score += min(item['like_count'] / 10, 1.0) * 0.3
            processed['engagement_score'] = round(engagement_score, 2)
        
        return processed


def main():
    """Main entry point for Discourse ingestion."""
    # Parse arguments
    parser = create_argument_parser()
    parser.description = "Ingest Discourse forum discussions for OHDSI Dashboard"
    parser.add_argument(
        '--category',
        type=str,
        help='Specific category slug to fetch from'
    )
    args = parser.parse_args()
    
    # Configure
    config = {
        'enable_ai_enhancement': args.enable_ai,
        'auto_approve_threshold': 0.6,  # Lower threshold for discussions
        'priority_threshold': 0.4
    }
    
    # Initialize and run ingestion
    ingestion = DiscourseIngestion(config=config)
    
    # Run ingestion
    stats = ingestion.ingest(
        max_items=args.max_items,
        category_slug=args.category,
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