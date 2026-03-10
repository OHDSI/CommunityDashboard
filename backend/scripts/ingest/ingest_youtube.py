#!/usr/bin/env python3
"""
Ingest YouTube videos for OHDSI Dashboard.
Fetches videos from specific OHDSI channels and playlists.

Usage:
    docker-compose exec backend python /app/scripts/ingest/ingest_youtube.py --max-items 50
    
Options:
    --max-items: Number of videos to fetch (default: 50)
    --channel: Specific channel ID to fetch from
    --playlist: Specific playlist ID to fetch from
    --enable-ai: Enable AI enhancement
    --dry-run: Test without indexing
"""

import sys
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from jobs.youtube_fetcher import YouTubeFetcher
from scripts.ingest.base_ingestion import BaseIngestion, create_argument_parser

logger = logging.getLogger(__name__)


class YouTubeIngestion(BaseIngestion):
    """
    YouTube video ingestion for OHDSI content.
    """
    
    # OHDSI-related YouTube channels
    OHDSI_CHANNELS = [
        'UC2RFIQnptl-nk8GbjFfqztw',  # OHDSI official channel (CORRECT ID)
        'UCntSDvY-hXt6f_Ot2VV78lQ',  # OHDSI Phenotype Development and Evaluation WG
        'UCvC_SUGUXoRf7BpWgSwiOjA',  # OHDSI Health Economics & Value Assessment
        'UCBiuZWty0r5mp698kn2ue5g',  # OHDSI APAC
        'UCsOR8mFElU53pGNav_XffrA',  # OHDSI India
        'UCsGVAO4QYUOEtshWAgDRoPg',  # OHDSI China
        'UCgU-r-g-HihYIROQr4lX-MQ',  # OHDSI Korea
        'UC56nnjw1_Lubwk_w7RFy9cg',  # OHDSI Brasil
    ]

    # OHDSI playlists from official channel - discovered 2025-10-01
    OHDSI_PLAYLISTS = [
        # High-priority playlists (large content)
        'PLpzbqK7kvfeXuBFxyAxuYR2mTDyiS32KX',  # Community Calls (450 videos)
        'PLpzbqK7kvfeVNc1_F64-d017EByvdWn-V',  # Features (100 videos)
        'PLpzbqK7kvfeXRQktX0PV-cRpb3EFA2e7Z',  # Tutorials & Workshops (87 videos)
        'PLpzbqK7kvfeX5v0QvInJT-yfMgMEN45eP',  # Workgroups (64 videos)
        'PLpzbqK7kvfeWryJzt81vwbCalRCdLJrOt',  # Get To Know The OHDSI Workgroups (28 videos)

        # Symposium playlists
        'PLpzbqK7kvfeUrGeNiP_M7wmIn_rqmXekv',  # 2025 Europe Symposium
        'PLpzbqK7kvfeUB5UayRa1e4J6dHOz8KQlu',  # 2024 Global Symposium
        'PLpzbqK7kvfeWakmMgOSm8f5pKMPRwftdd',  # 2024 Europe Symposium
        'PLpzbqK7kvfeXhzxlQfuCjKn_4aBOVoRpO',  # 2023 Global Symposium
        'PLpzbqK7kvfeVrb-VzyO-lHY0cZ-qXIgFe',  # 2023 APAC Symposium
        'PLpzbqK7kvfeUBtHRA2ZF0Rd4R8fYElSCo',  # 2023 Europe Symposium
        'PLpzbqK7kvfeUqFu43qn46mZRJnZFPN675',  # 2022 Symposium
        'PLpzbqK7kvfeXsIfV3-55LB7kNExMNoss_',  # 2022 European Symposium
        'PLpzbqK7kvfeXn7I3vjrnUoDQ3bqgNAc_x',  # 2021 Global Symposium
        'PLpzbqK7kvfeVqGU_4o4eiOZz7ecJXMC6c',  # 2020 APAC Symposium
        'PLpzbqK7kvfeVWF10Annouw6vtl41BIADy',  # 2020 Global Symposium
        'PLpzbqK7kvfeVzlAXenD6iWhRxWvmlfdHN',  # 2019 Korea Symposium
        'PLpzbqK7kvfeVWtDEc4VGmI1F_EBi_sJOF',  # 2019 U.S. Symposium
        'PLpzbqK7kvfeUjSiJd7R0sGtg7teqePP7H',  # 2019 European Symposium

        # DevCon and special events
        'PLpzbqK7kvfeUEhufmMUhLNrjNSEaQdKz2',  # DevCon 2025
        'PLpzbqK7kvfeXxv51TXJ-QSDYBdiDmmspE',  # DevCon 2024
        'PLpzbqK7kvfeVNBpenS1VKgY2b3KqnAvwX',  # DevCon 2023
        'PLpzbqK7kvfeXLful4VMGXoDVJDowoGIhC',  # DevCon 2022
        'PLpzbqK7kvfeVGZiT1eKO6KxQiN7nzBFKt',  # COVID-19 Study-A-Thon (27 videos)
        'PLpzbqK7kvfeW6BcJXi55tcUmcO0qbLKit',  # SOS Challenge (20 videos)
        'PLpzbqK7kvfeX3v0QvInJT-yfMgMEN45eP',  # Phenotype Phebruary 2024

        # Tool-specific and special series
        'PLpzbqK7kvfeUXjgnpNMFoff3PDOwv61lZ',  # ATLAS Tutorials (19 videos)
        'PLpzbqK7kvfeVfRF4kj89mMiKSTX9fqhVB',  # CBER BEST Seminar Series (10 videos)
        'PLpzbqK7kvfeW8QKFZgqB1HgmE88QhCsVu',  # 2022 Collaborator Showcase
        'PLpzbqK7kvfeWgzjtqgXKZDXCJLa_npIZc',  # Europe Community Calls
    ]
    
    # Search queries for OHDSI content - strict OHDSI/OMOP criteria only
    SEARCH_QUERIES = [
        # Core OHDSI terms - highest priority
        'OHDSI',
        'OMOP CDM',
        'OHDSI OMOP',
        'OHDSI Atlas',
        'HADES OHDSI',
        'OMOP Common Data Model OHDSI',

        # OHDSI events and community - official channels
        'OHDSI community call',
        'OHDSI symposium',
        'OHDSI tutorial',
        'OHDSI workgroup',
        'Book of OHDSI',
        'OHDSI Collaborator',
        'OHDSI Chapter',
        'OHDSI Europe',
        'OHDSI Asia',

        # OHDSI HADES tools - core packages
        'Achilles OHDSI',
        'CohortMethod OHDSI',
        'PatientLevelPrediction OHDSI',
        'FeatureExtraction OHDSI',
        'DataQualityDashboard OHDSI',
        'SqlRender OHDSI',
        'DatabaseConnector OHDSI',

        # OHDSI HADES tools - additional packages
        'Usagi OHDSI',
        'WhiteRabbit OHDSI',
        'Rabbit-in-a-Hat OHDSI',
        'Calypso OHDSI',
        'Perseus OHDSI',
        'Ares OHDSI',
        'CirceR OHDSI',
        'PhenotypeLibrary OHDSI',
        'CohortGenerator OHDSI',
        'Eunomia OHDSI',
        'Cyclops OHDSI',
        'EmpiricalCalibration OHDSI',

        # OHDSI network studies
        'LEGEND OHDSI',
        'CHARYBDIS OHDSI',

        # OHDSI workgroups
        'OHDSI Vocabulary workgroup',
        'OHDSI CDM workgroup',
        'OHDSI Methods workgroup',
        'OHDSI Quality workgroup',

        # CDM versions
        'OMOP CDM v5.4',
        'OMOP CDM v6',

        # Additional strict OHDSI-specific terms
        'OHDSI CDM',
        'OHDSI Vocabulary',
        'OHDSI Network',
        'OHDSI WebAPI',
        'OHDSI R packages'
    ]
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize YouTube ingestion."""
        super().__init__(source_name='youtube', content_type='video', config=config)
        
        # Initialize YouTube fetcher
        try:
            self.fetcher = YouTubeFetcher()
            logger.info("YouTube ingestion initialized")
        except Exception as e:
            logger.error(f"Failed to initialize YouTube fetcher: {e}")
            raise
    
    def fetch_content(
        self,
        max_items: int = 50,
        channel_id: str = None,
        playlist_id: str = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch videos from YouTube.
        
        Args:
            max_items: Maximum number of videos to fetch
            channel_id: Specific channel to fetch from
            playlist_id: Specific playlist to fetch from
            
        Returns:
            List of video data
        """
        all_videos = []
        
        # If specific channel/playlist provided
        if channel_id:
            logger.info(f"Fetching from channel: {channel_id}")
            videos = self._fetch_from_channel(channel_id, max_items)
            all_videos.extend(videos)
        elif playlist_id:
            logger.info(f"Fetching from playlist: {playlist_id}")
            videos = self._fetch_from_playlist(playlist_id, max_items)
            all_videos.extend(videos)
        else:
            # Fetch from all OHDSI sources
            items_per_source = max(1, max_items // (len(self.OHDSI_CHANNELS) + len(self.OHDSI_PLAYLISTS) + len(self.SEARCH_QUERIES)))
            
            # Fetch from channels
            for channel in self.OHDSI_CHANNELS:
                if len(all_videos) >= max_items:
                    break
                videos = self._fetch_from_channel(channel, items_per_source)
                all_videos.extend(videos)
            
            # Fetch from playlists
            for playlist in self.OHDSI_PLAYLISTS:
                if len(all_videos) >= max_items:
                    break
                videos = self._fetch_from_playlist(playlist, items_per_source)
                all_videos.extend(videos)
            
            # Search for additional content
            for query in self.SEARCH_QUERIES:
                if len(all_videos) >= max_items:
                    break
                videos = self._search_videos(query, items_per_source)
                all_videos.extend(videos)
        
        # Limit to max_items
        all_videos = all_videos[:max_items]
        
        logger.info(f"Total videos fetched: {len(all_videos)}")
        return all_videos
    
    def _fetch_from_channel(self, channel_id: str, max_results: int) -> List[Dict[str, Any]]:
        """Fetch videos from a specific channel."""
        try:
            logger.info(f"Fetching up to {max_results} videos from channel {channel_id}")
            videos = self.fetcher.fetch_channel_videos(channel_id, max_results=max_results)
            
            # Process each video
            processed = []
            for video in videos:
                # Add YouTube-specific fields
                video['source'] = 'youtube'
                video['content_type'] = 'video'
                video['channel_id'] = channel_id
                
                # Ensure ID field
                if 'video_id' in video and 'id' not in video:
                    video['id'] = f"youtube_{video['video_id']}"
                
                processed.append(video)
            
            logger.info(f"Fetched {len(processed)} videos from channel")
            return processed
            
        except Exception as e:
            logger.error(f"Error fetching from channel {channel_id}: {e}")
            return []
    
    def _fetch_from_playlist(self, playlist_id: str, max_results: int) -> List[Dict[str, Any]]:
        """Fetch videos from a specific playlist."""
        try:
            logger.info(f"Fetching up to {max_results} videos from playlist {playlist_id}")
            videos = self.fetcher.fetch_playlist_videos(playlist_id, max_results=max_results)
            
            # Process each video
            processed = []
            for video in videos:
                # Add YouTube-specific fields
                video['source'] = 'youtube'
                video['content_type'] = 'video'
                video['playlist_id'] = playlist_id
                
                # Ensure ID field
                if 'video_id' in video and 'id' not in video:
                    video['id'] = f"youtube_{video['video_id']}"
                
                processed.append(video)
            
            logger.info(f"Fetched {len(processed)} videos from playlist")
            return processed
            
        except Exception as e:
            logger.error(f"Error fetching from playlist {playlist_id}: {e}")
            return []
    
    def _search_videos(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search for videos by query."""
        try:
            logger.info(f"Searching for '{query}' (max {max_results} results)")
            videos = self.fetcher.search(query, max_results=max_results)
            
            # Process each video
            processed = []
            for video in videos:
                # Add YouTube-specific fields
                video['source'] = 'youtube'
                video['content_type'] = 'video'
                video['search_query'] = query
                
                # Ensure ID field
                if 'video_id' in video and 'id' not in video:
                    video['id'] = f"youtube_{video['video_id']}"
                
                processed.append(video)
            
            logger.info(f"Found {len(processed)} videos for query '{query}'")
            return processed
            
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
            return []
    
    def validate_content(self, item: Dict[str, Any]) -> bool:
        """
        Validate that a YouTube video has required fields.
        
        Args:
            item: Video to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['video_id', 'title']
        
        for field in required_fields:
            if not item.get(field):
                logger.warning(f"Missing required field '{field}' in video")
                return False
        
        # Strict OHDSI relevance check - must have OHDSI or OMOP in title/description
        title = item.get('title', '').lower()
        description = item.get('description', '').lower()
        transcript = item.get('transcript', '').lower()

        # Primary keywords that MUST be present (at least one)
        primary_keywords = ['ohdsi', 'omop']

        # Check title and description (most reliable)
        title_desc = f"{title} {description}"
        has_primary = any(keyword in title_desc for keyword in primary_keywords)

        if not has_primary:
            # Check transcript as fallback
            has_primary_transcript = any(keyword in transcript for keyword in primary_keywords)
            if not has_primary_transcript:
                logger.info(f"Video '{item.get('title', '')[:50]}...' rejected - no OHDSI/OMOP keywords")
                return False

        # Additional validation - check for secondary indicators
        secondary_keywords = ['atlas', 'hades', 'achilles', 'cohort', 'cdm', 'vocabulary',
                              'observational health', 'common data model']
        has_secondary = any(keyword in title_desc for keyword in secondary_keywords)

        if has_primary and has_secondary:
            logger.debug(f"Video '{item.get('title', '')[:50]}...' has strong OHDSI indicators")

        return True
    
    def process_item(self, item: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """
        Process a YouTube video with special handling.
        
        Args:
            item: Raw video data
            
        Returns:
            Processed video
        """
        # Process through base pipeline
        processed = super().process_item(item, dry_run=dry_run)
        
        if processed:
            # Add YouTube-specific metadata
            processed['source_type'] = 'media'
            processed['display_type'] = 'Video'
            processed['icon_type'] = 'play-circle'
            processed['content_category'] = 'media'
            
            # Generate URL if not present
            if 'url' not in processed and 'video_id' in processed:
                processed['url'] = f"https://www.youtube.com/watch?v={processed['video_id']}"
            
            # Extract duration in seconds if present
            if 'duration' in processed and isinstance(processed['duration'], str):
                processed['duration'] = self._parse_duration(processed['duration'])
            
            # Set published date from upload date
            if 'upload_date' in processed and 'published_date' not in processed:
                processed['published_date'] = processed['upload_date']
        
        return processed
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse ISO 8601 duration to seconds."""
        try:
            # Format: PT#H#M#S or PT#M#S or PT#S
            match = re.match(r'PT(?:([0-9]+)H)?(?:([0-9]+)M)?(?:([0-9]+)S)?', duration_str)
            if match:
                hours = int(match.group(1) or 0)
                minutes = int(match.group(2) or 0)
                seconds = int(match.group(3) or 0)
                return hours * 3600 + minutes * 60 + seconds
        except Exception as e:
            logger.warning(f"Could not parse duration '{duration_str}': {e}")
        return 0


def main():
    """Main entry point for YouTube ingestion."""
    # Parse arguments
    parser = create_argument_parser()
    parser.description = "Ingest YouTube videos for OHDSI Dashboard"
    parser.add_argument(
        '--channel',
        type=str,
        help='Specific channel ID to fetch from'
    )
    parser.add_argument(
        '--playlist',
        type=str,
        help='Specific playlist ID to fetch from'
    )
    args = parser.parse_args()
    
    # Configure - strict thresholds for OHDSI-only content
    config = {
        'enable_ai_enhancement': args.enable_ai,
        'auto_approve_threshold': 0.7,  # Strict threshold for videos (same as articles)
        'priority_threshold': 0.5  # Higher threshold for manual review
    }
    
    # Initialize and run ingestion
    ingestion = YouTubeIngestion(config=config)
    
    # Run ingestion
    stats = ingestion.ingest(
        max_items=args.max_items,
        channel_id=args.channel,
        playlist_id=args.playlist,
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