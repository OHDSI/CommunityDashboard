"""
YouTube fetcher for OHDSI-related videos.
Fetches videos from OHDSI channels and searches for relevant content.
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import isodate

# YouTube API client
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False
    logging.warning("Google API client not available. Install with: pip install google-api-python-client")

# Add parent directory to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.base_fetcher import BaseFetcher
from shared.ohdsi_constants import YOUTUBE_SEARCH_QUERIES, OHDSI_KEYWORDS
from shared.content_relevance import is_ohdsi_related
from youtube_fetcher.transcript_processor import TranscriptProcessor

logger = logging.getLogger(__name__)


class YouTubeFetcher(BaseFetcher):
    """
    Fetches OHDSI-related videos from YouTube.
    """

    # OHDSI-related channels to monitor
    OHDSI_CHANNELS = [
        'UCfh2Qeb3v1qAVt3eXpzlXRQ',  # OHDSI official channel (placeholder - needs real ID)
        # Add more channel IDs as discovered
    ]

    # Search queries for finding OHDSI content
    SEARCH_QUERIES = YOUTUBE_SEARCH_QUERIES
    
    def __init__(self, api_key: str = None):
        """
        Initialize YouTube fetcher.
        
        Args:
            api_key: YouTube Data API key
        """
        super().__init__(
            source_name='youtube',
            rate_limit=0.1,  # YouTube API has quota limits
            cache_ttl=3600 * 24  # Cache for 24 hours
        )
        
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        
        if not self.api_key:
            logger.warning("No YouTube API key provided. Set YOUTUBE_API_KEY environment variable.")
        
        if YOUTUBE_API_AVAILABLE and self.api_key:
            try:
                self.youtube = build('youtube', 'v3', developerKey=self.api_key)
                logger.info("YouTube API client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize YouTube API client: {e}")
                self.youtube = None
        else:
            self.youtube = None
        
        # Initialize transcript processor
        self.transcript_processor = TranscriptProcessor()
        self.fetch_transcripts = True  # Can be configured
    
    def search(self, query: str, max_results: int = 50, 
              filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Search for OHDSI-related videos.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            filters: Additional filters (e.g., date range, duration)
            
        Returns:
            List of video details as dictionaries
        """
        if not self.youtube:
            logger.error("YouTube API client not initialized")
            return []
        
        video_ids = []
        filters = filters or {}
        
        try:
            # Build search parameters
            search_params = {
                'q': query,
                'part': 'id',
                'type': 'video',
                'maxResults': min(50, max_results),  # API limit is 50 per request
                'order': 'relevance'
            }
            
            # Add date filter if provided
            if filters.get('published_after'):
                search_params['publishedAfter'] = filters['published_after']
            if filters.get('published_before'):
                search_params['publishedBefore'] = filters['published_before']
            
            # Add duration filter if provided
            if filters.get('duration'):
                # short (<4min), medium (4-20min), long (>20min)
                search_params['videoDuration'] = filters['duration']
            
            # Execute search
            search_response = self.youtube.search().list(**search_params).execute()
            
            # Extract video IDs
            for item in search_response.get('items', []):
                if item['id']['kind'] == 'youtube#video':
                    video_ids.append(item['id']['videoId'])
            
            # Handle pagination if needed
            next_page_token = search_response.get('nextPageToken')
            while next_page_token and len(video_ids) < max_results:
                search_params['pageToken'] = next_page_token
                search_params['maxResults'] = min(50, max_results - len(video_ids))
                
                search_response = self.youtube.search().list(**search_params).execute()
                
                for item in search_response.get('items', []):
                    if item['id']['kind'] == 'youtube#video':
                        video_ids.append(item['id']['videoId'])
                
                next_page_token = search_response.get('nextPageToken')
            
            logger.info(f"Found {len(video_ids)} videos for query: {query}")
            
        except HttpError as e:
            logger.error(f"YouTube API error during search: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during YouTube search: {e}")
        
        # Fetch full details for the video IDs
        if video_ids:
            return self.fetch_details(video_ids[:max_results])
        return []
    
    def fetch_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch detailed information for videos.
        
        Args:
            video_ids: List of YouTube video IDs
            
        Returns:
            List of video details
        """
        if not self.youtube:
            logger.error("YouTube API client not initialized")
            return []
        
        if not video_ids:
            return []
        
        videos = []
        
        try:
            # YouTube API allows up to 50 IDs per request
            for i in range(0, len(video_ids), 50):
                batch_ids = video_ids[i:i+50]
                
                # Fetch video details
                videos_response = self.youtube.videos().list(
                    part='snippet,contentDetails,statistics',
                    id=','.join(batch_ids)
                ).execute()
                
                for item in videos_response.get('items', []):
                    video = self._parse_video_item(item)
                    if video:
                        # Fetch transcript if enabled
                        if self.fetch_transcripts:
                            video_id = video.get('video_id')
                            if video_id:
                                logger.debug(f"Fetching transcript for video {video_id}")
                                transcript = self.transcript_processor.fetch_transcript(video_id)
                                if transcript:
                                    # Process the transcript to extract structured data
                                    processed = self.transcript_processor.process_transcript(transcript)
                                    video['transcript'] = transcript
                                    video['transcript_data'] = processed
                                    logger.info(f"✅ Fetched transcript for '{video.get('title', '')[:50]}...'")
                                else:
                                    logger.debug(f"No transcript available for video {video_id}")
                        videos.append(video)
            
            logger.info(f"Fetched details for {len(videos)} videos")
            
        except HttpError as e:
            logger.error(f"YouTube API error fetching video details: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching video details: {e}")
        
        return videos
    
    def fetch_channel_videos(self, channel_id: str, 
                           max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch recent videos from a specific channel.
        
        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of videos to fetch
            
        Returns:
            List of video details
        """
        if not self.youtube:
            logger.error("YouTube API client not initialized")
            return []
        
        videos = []
        
        try:
            # Get channel's uploads playlist
            channels_response = self.youtube.channels().list(
                part='contentDetails',
                id=channel_id
            ).execute()
            
            if not channels_response.get('items'):
                logger.warning(f"Channel not found: {channel_id}")
                return []
            
            uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Fetch videos from uploads playlist
            playlist_response = self.youtube.playlistItems().list(
                part='snippet',
                playlistId=uploads_playlist_id,
                maxResults=min(50, max_results)
            ).execute()
            
            video_ids = []
            for item in playlist_response.get('items', []):
                video_ids.append(item['snippet']['resourceId']['videoId'])
            
            # Handle pagination
            next_page_token = playlist_response.get('nextPageToken')
            while next_page_token and len(video_ids) < max_results:
                playlist_response = self.youtube.playlistItems().list(
                    part='snippet',
                    playlistId=uploads_playlist_id,
                    maxResults=min(50, max_results - len(video_ids)),
                    pageToken=next_page_token
                ).execute()
                
                for item in playlist_response.get('items', []):
                    video_ids.append(item['snippet']['resourceId']['videoId'])
                
                next_page_token = playlist_response.get('nextPageToken')
            
            # Fetch full video details
            if video_ids:
                videos = self.fetch_details(video_ids[:max_results])
            
            logger.info(f"Fetched {len(videos)} videos from channel {channel_id}")
            
        except HttpError as e:
            logger.error(f"YouTube API error fetching channel videos: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching channel videos: {e}")
        
        return videos
    
    def fetch_ohdsi_content(self, max_results_per_query: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch OHDSI-related content from multiple sources.
        
        Args:
            max_results_per_query: Maximum results per search query
            
        Returns:
            List of OHDSI-related videos
        """
        all_videos = []
        seen_ids = set()
        
        # Fetch from known OHDSI channels
        for channel_id in self.OHDSI_CHANNELS:
            videos = self.fetch_channel_videos(channel_id, max_results_per_query)
            for video in videos:
                if video['video_id'] not in seen_ids:
                    all_videos.append(video)
                    seen_ids.add(video['video_id'])
        
        # Search for OHDSI-related content
        for query in self.SEARCH_QUERIES:
            # search() now returns full video details, not just IDs
            videos = self.search(query, max_results_per_query)
            
            for video in videos:
                if video['video_id'] not in seen_ids:
                    # Additional filtering for relevance
                    if self._is_ohdsi_related(video):
                        all_videos.append(video)
                        seen_ids.add(video['video_id'])
        
        logger.info(f"Found {len(all_videos)} unique OHDSI-related videos")
        
        return all_videos
    
    def _parse_video_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse YouTube API video item to our format."""
        try:
            snippet = item.get('snippet', {})
            content_details = item.get('contentDetails', {})
            statistics = item.get('statistics', {})
            
            # Parse duration from ISO 8601
            duration_str = content_details.get('duration', 'PT0S')
            try:
                duration = isodate.parse_duration(duration_str)
                duration_seconds = int(duration.total_seconds())
            except:
                duration_seconds = 0
            
            # Parse published date
            published_at = snippet.get('publishedAt', '')
            try:
                published_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            except:
                published_date = datetime.now()
            
            return {
                'video_id': item.get('id'),
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'channel_id': snippet.get('channelId'),
                'channel_name': snippet.get('channelTitle', ''),
                'published_date': published_date.isoformat(),
                'year': published_date.year,
                'duration': duration_seconds,
                'duration_formatted': self._format_duration(duration_seconds),
                'thumbnail_url': self._get_best_thumbnail(snippet.get('thumbnails', {})),
                'tags': snippet.get('tags', []),
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'dislike_count': int(statistics.get('dislikeCount', 0)),
                'comment_count': int(statistics.get('commentCount', 0)),
                'url': f"https://www.youtube.com/watch?v={item.get('id')}",
                'embed_url': f"https://www.youtube.com/embed/{item.get('id')}",
                'content_type': 'video',
                'source': 'youtube'
            }
        except Exception as e:
            logger.error(f"Error parsing video item: {e}")
            return None
    
    def _get_best_thumbnail(self, thumbnails: Dict[str, Any]) -> str:
        """Get the best quality thumbnail URL."""
        # Priority order: maxres > standard > high > medium > default
        for quality in ['maxres', 'standard', 'high', 'medium', 'default']:
            if quality in thumbnails:
                return thumbnails[quality].get('url', '')
        return ''
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to human-readable string."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def _is_ohdsi_related(self, video: Dict[str, Any]) -> bool:
        """
        Check if a video is likely OHDSI-related.

        Args:
            video: Video details

        Returns:
            True if video appears OHDSI-related
        """
        # Check title and description
        text = f"{video.get('title', '')} {video.get('description', '')}"
        if is_ohdsi_related(text):
            return True

        # Check tags
        tags = [tag.lower() for tag in video.get('tags', [])]
        for keyword in OHDSI_KEYWORDS:
            if any(keyword in tag for tag in tags):
                return True

        # Check channel name
        channel = video.get('channel_name', '').lower()
        if any(keyword in channel for keyword in ['ohdsi', 'omop', 'observational']):
            return True

        return False
    
    def _fetch_single(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Implementation of abstract method from BaseFetcher.
        
        Args:
            query: Query parameters
            
        Returns:
            List of videos
        """
        query_type = query.get('type', 'search')
        
        if query_type == 'search':
            # search() now returns full video details, not just IDs
            videos = self.search(
                query.get('q', 'OHDSI'),
                query.get('max_results', 20),
                query.get('filters')
            )
            return videos
        
        elif query_type == 'channel':
            return self.fetch_channel_videos(
                query.get('channel_id'),
                query.get('max_results', 20)
            )
        
        elif query_type == 'video_ids':
            return self.fetch_details(query.get('video_ids', []))
        
        else:
            logger.warning(f"Unknown query type: {query_type}")
            return []