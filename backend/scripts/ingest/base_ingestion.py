#!/usr/bin/env python3
"""
Base ingestion class for all content sources.
Provides common functionality for fetching, processing, and indexing content.
"""

import os
import sys
import json
import logging
import argparse
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from elasticsearch import Elasticsearch
from app.config import settings
from jobs.shared.content_normalizer import ContentNormalizer
from jobs.shared.ml_classifier import UnifiedMLClassifier
from jobs.shared.queue_manager import QueueManager
from jobs.shared.ai_enhancer import AIEnhancer
from jobs.shared.utils.deduplication import Deduplicator
from jobs.shared.utils.quality_scorer import QualityScorer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BaseIngestion(ABC):
    """
    Base class for content ingestion from various sources.
    Handles common processing pipeline and provides hooks for source-specific logic.
    """
    
    def __init__(self, source_name: str, content_type: str, config: Dict[str, Any] = None):
        """
        Initialize base ingestion.
        
        Args:
            source_name: Name of the source (pubmed, youtube, github, etc.)
            content_type: Type of content (article, video, repository, etc.)
            config: Configuration dictionary
        """
        self.source_name = source_name
        self.content_type = content_type
        self.config = config or self._get_default_config()
        
        # Initialize Elasticsearch
        self.es_client = Elasticsearch(
            hosts=[settings.elasticsearch_url],
            timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        
        # Initialize components
        self.normalizer = ContentNormalizer()
        self.classifier = UnifiedMLClassifier()
        self.deduplicator = Deduplicator(es_client=self.es_client)
        self.quality_scorer = QualityScorer()
        self.queue_manager = QueueManager(
            es_client=self.es_client,
            auto_approve_threshold=self.config.get('auto_approve_threshold', 0.7),
            priority_threshold=self.config.get('priority_threshold', 0.5)
        )
        
        # Initialize AI enhancer if enabled
        if self.config.get('enable_ai_enhancement', False):
            try:
                self.ai_enhancer = AIEnhancer(
                    model=self.config.get('gpt_model', 'gpt-4o-mini')
                )
                logger.info(f"AI enhancement enabled for {source_name}")
            except Exception as e:
                logger.warning(f"Could not initialize AI enhancer: {e}")
                self.ai_enhancer = None
        else:
            self.ai_enhancer = None
        
        # Statistics
        self.stats = {
            'fetched': 0,
            'processed': 0,
            'indexed': 0,
            'duplicates': 0,
            'errors': 0,
            'auto_approved': 0,
            'sent_to_review': 0
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'enable_ai_enhancement': bool(os.getenv('OPENAI_API_KEY')),
            'gpt_model': 'gpt-4o-mini',
            'generate_embeddings': True,
            'auto_approve_threshold': 0.7,
            'priority_threshold': 0.5,
            'content_index': settings.content_index,
            'review_index': settings.review_index
        }
    
    @abstractmethod
    def fetch_content(self, max_items: int = 50, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch content from the source.
        Must be implemented by each source-specific class.
        
        Args:
            max_items: Maximum number of items to fetch
            **kwargs: Additional source-specific parameters
            
        Returns:
            List of raw content items
        """
        pass
    
    @abstractmethod
    def validate_content(self, item: Dict[str, Any]) -> bool:
        """
        Validate that a content item has required fields.
        Must be implemented by each source-specific class.
        
        Args:
            item: Content item to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    def process_item(self, item: Dict[str, Any], dry_run: bool = False) -> Optional[Dict[str, Any]]:
        """
        Process a single content item through the pipeline.
        
        Args:
            item: Raw content item
            dry_run: If True, skip indexing to Elasticsearch
            
        Returns:
            Processed item or None if duplicate/error
        """
        try:
            # Add source metadata
            item['source'] = self.source_name
            
            # Normalize content
            normalized = self.normalizer.normalize(item, self.content_type)
            
            # Check for duplicates (skip in dry-run to avoid ES calls)
            if not dry_run:
                is_duplicate, existing_id = self.deduplicator.check_duplicate(normalized)
                if is_duplicate:
                    logger.info(f"Duplicate found: {normalized.get('title', '')[:50]}... (existing: {existing_id})")
                    self.stats['duplicates'] += 1
                    return None
            
            # Calculate quality score
            quality_score = self.quality_scorer.calculate_quality_score(normalized)
            normalized['quality_score'] = quality_score
            
            # ML classification
            classification = self.classifier.classify(normalized)
            normalized.update(classification)
            
            # AI enhancement (if enabled)
            if self.ai_enhancer and self.config.get('enable_ai_enhancement'):
                try:
                    enhanced = self.ai_enhancer.enhance_content(normalized, self.content_type)
                    normalized.update(enhanced)
                    
                    # Discover relationships if enabled
                    if self.config.get('enable_relationships'):
                        relationships = self.ai_enhancer.discover_relationships(normalized, [])
                        if relationships:
                            normalized['relationships'] = relationships
                except Exception as e:
                    logger.warning(f"AI enhancement failed: {e}")
            
            # Route to appropriate queue (skip in dry-run)
            if not dry_run:
                routing = self.queue_manager.route_content(normalized, classification)
                
                # Update statistics
                if routing['destination'] == 'approved':
                    self.stats['auto_approved'] += 1
                else:
                    self.stats['sent_to_review'] += 1
                
                self.stats['indexed'] += 1
            else:
                # Simulate routing for dry-run
                # Use final_score which is the authoritative score from classifier
                final_score = classification.get('final_score', classification.get('combined_probability', 0))
                if final_score >= self.config.get('auto_approve_threshold', 0.7):
                    self.stats['auto_approved'] += 1
                    logger.info(f"[DRY-RUN] Would auto-approve: {normalized.get('title', '')[:50]}... (score: {final_score:.3f})")
                else:
                    self.stats['sent_to_review'] += 1
                    logger.info(f"[DRY-RUN] Would send to review: {normalized.get('title', '')[:50]}... (score: {final_score:.3f})")
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error processing item: {e}")
            self.stats['errors'] += 1
            return None
    
    def ingest(
        self,
        max_items: int = 50,
        dry_run: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Main ingestion method.
        
        Args:
            max_items: Maximum number of items to fetch
            dry_run: If True, don't actually index to Elasticsearch
            **kwargs: Additional source-specific parameters
            
        Returns:
            Statistics dictionary
        """
        logger.info(f"Starting {self.source_name} ingestion (max_items={max_items}, dry_run={dry_run})")
        
        # Fetch content
        try:
            items = self.fetch_content(max_items, **kwargs)
            self.stats['fetched'] = len(items)
            logger.info(f"Fetched {len(items)} items from {self.source_name}")
        except Exception as e:
            logger.error(f"Error fetching content: {e}")
            return self.stats
        
        # Process items
        processed_items = []
        for i, item in enumerate(items, 1):
            # Validate item
            if not self.validate_content(item):
                logger.warning(f"Invalid item skipped: {item.get('id', 'unknown')}")
                continue
            
            # Process through pipeline
            processed = self.process_item(item, dry_run=dry_run)
            if processed:
                processed_items.append(processed)
                self.stats['processed'] += 1
            
            # Log progress
            if i % 10 == 0:
                logger.info(f"Processed {i}/{len(items)} items")
        
        # Log summary
        logger.info(f"\n{self.source_name} Ingestion Complete:")
        logger.info(f"  Fetched: {self.stats['fetched']}")
        logger.info(f"  Processed: {self.stats['processed']}")
        logger.info(f"  Indexed: {self.stats['indexed']}")
        logger.info(f"  Duplicates: {self.stats['duplicates']}")
        logger.info(f"  Errors: {self.stats['errors']}")
        logger.info(f"  Auto-approved: {self.stats['auto_approved']}")
        logger.info(f"  Sent to review: {self.stats['sent_to_review']}")
        
        return self.stats
    
    def save_progress(self, filepath: str = None):
        """Save ingestion progress to file."""
        if not filepath:
            filepath = f"/app/logs/{self.source_name}_progress.json"
        
        progress = {
            'source': self.source_name,
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(progress, f, indent=2)
        
        logger.info(f"Progress saved to {filepath}")


def create_argument_parser():
    """Create common argument parser for ingestion scripts."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--max-items',
        type=int,
        default=50,
        help='Maximum number of items to fetch (default: 50)'
    )
    parser.add_argument(
        '--enable-ai',
        action='store_true',
        help='Enable AI enhancement (requires OPENAI_API_KEY)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without actually indexing to Elasticsearch'
    )
    parser.add_argument(
        '--date-from',
        type=str,
        help='Start date for fetching (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--date-to',
        type=str,
        help='End date for fetching (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--save-progress',
        action='store_true',
        help='Save progress to file'
    )
    return parser