"""
Unified Pipeline Orchestrator with AI enrichment and Elasticsearch integration.
Coordinates multi-source content fetching, processing, and indexing.

This is the main pipeline orchestrator for the OHDSI content pipeline.
It fetches content from multiple sources (PubMed, YouTube, GitHub, Discourse, Wiki),
normalizes it to a unified schema, classifies it with ML, enhances it with AI,
and stores it in Elasticsearch for search and retrieval.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from elasticsearch import Elasticsearch, helpers
import redis
from celery import Celery

# Import fetchers
from jobs.youtube_fetcher import YouTubeFetcher
from jobs.github_scanner import GitHubScanner
from jobs.discourse_fetcher import DiscourseFetcher
from jobs.wiki_scraper import WikiScraper
from jobs.article_classifier.retriever import PubMedRetriever

# Import shared components
from jobs.shared.content_normalizer import ContentNormalizer
from jobs.shared.ml_classifier import UnifiedMLClassifier
from jobs.shared.queue_manager import QueueManager
from jobs.shared.ai_enhancer import AIEnhancer
from jobs.shared.utils.deduplication import Deduplicator
from jobs.shared.utils.quality_scorer import QualityScorer
from jobs.shared.utils.rate_limiter import MultiServiceRateLimiter

# Configuration
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentPipelineOrchestrator:
    """
    Enhanced orchestrator for multi-source content pipeline with AI enrichment.
    """
    
    def __init__(
        self,
        es_client: Elasticsearch = None,
        redis_client: redis.Redis = None,
        config: Dict[str, Any] = None
    ):
        """
        Initialize enhanced pipeline orchestrator.
        
        Args:
            es_client: Elasticsearch client
            redis_client: Redis client for caching
            config: Configuration dictionary
        """
        self.config = config or self._get_default_config()
        
        # Initialize Elasticsearch
        if es_client:
            self.es_client = es_client
        else:
            self.es_client = Elasticsearch(
                hosts=[settings.elasticsearch_url],
                timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
        
        # Initialize Redis
        if redis_client:
            self.redis_client = redis_client
        else:
            try:
                self.redis_client = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    decode_responses=False
                )
                self.redis_client.ping()
            except:
                logger.warning("Redis not available, caching disabled")
                self.redis_client = None
        
        # Initialize components
        self._initialize_components()
        
        # Statistics
        self.stats = {
            'total_fetched': 0,
            'total_processed': 0,
            'total_indexed': 0,
            'duplicates_found': 0,
            'errors': 0,
            'by_source': {},
            'by_type': {}
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            # Source enablement
            'enable_pubmed': True,
            'enable_youtube': True,
            'enable_github': True,
            'enable_discourse': True,
            'enable_wiki': True,
            
            # AI enhancement
            'enable_ai_enhancement': True,
            'use_gpt': True,
            'gpt_model': 'gpt-4o-mini',
            'generate_embeddings': True,
            
            # Processing settings
            'auto_approve_threshold': 0.7,
            'priority_threshold': 0.5,
            'similarity_threshold': 0.85,
            'batch_size': 10,
            
            # Elasticsearch
            'content_index': 'ohdsi_content_v3',
            'review_index': 'ohdsi_review_queue_v3',
            
            # Rate limiting (requests per second)
            'rate_limits': {
                'pubmed': 3.0,
                'youtube': 10.0,
                'github': 5.0,
                'discourse': 2.0,
                'wiki': 1.0
            },
            
            # Cache TTL (seconds)
            'cache_ttl': {
                'pubmed': 3600,
                'youtube': 3600,
                'github': 21600,
                'discourse': 10800,
                'wiki': 86400
            }
        }
    
    def _initialize_components(self):
        """Initialize all pipeline components."""
        logger.info("Initializing pipeline components...")
        
        # Initialize fetchers
        self.fetchers = {}
        
        if self.config.get('enable_pubmed'):
            try:
                self.fetchers['pubmed'] = PubMedRetriever()
                logger.info("PubMed fetcher initialized")
            except Exception as e:
                logger.error(f"Failed to initialize PubMed fetcher: {e}")
        
        if self.config.get('enable_youtube'):
            youtube_api_key = os.getenv('YOUTUBE_API_KEY')
            if youtube_api_key:
                self.fetchers['youtube'] = YouTubeFetcher(api_key=youtube_api_key)
                logger.info("YouTube fetcher initialized")
            else:
                logger.warning("YouTube API key not found")
        
        if self.config.get('enable_github'):
            github_token = os.getenv('GITHUB_TOKEN')
            self.fetchers['github'] = GitHubScanner(github_token=github_token)
            logger.info("GitHub scanner initialized")
        
        if self.config.get('enable_discourse'):
            self.fetchers['discourse'] = DiscourseFetcher()
            logger.info("Discourse fetcher initialized")
        
        if self.config.get('enable_wiki'):
            self.fetchers['wiki'] = WikiScraper()
            logger.info("Wiki scraper initialized")
        
        # Initialize processing components
        self.normalizer = ContentNormalizer()
        self.ml_classifier = UnifiedMLClassifier(
            use_gpt=self.config.get('use_gpt', False)
        )
        self.queue_manager = QueueManager(
            es_client=self.es_client,
            auto_approve_threshold=self.config.get('auto_approve_threshold', 0.7),
            priority_threshold=self.config.get('priority_threshold', 0.5)
        )
        self.deduplicator = Deduplicator(
            es_client=self.es_client,
            similarity_threshold=self.config.get('similarity_threshold', 0.85)
        )
        self.quality_scorer = QualityScorer()
        
        # Initialize AI enhancer
        if self.config.get('enable_ai_enhancement'):
            self.ai_enhancer = AIEnhancer(
                redis_client=self.redis_client,
                model=self.config.get('gpt_model', 'gpt-4o-mini')
            )
            logger.info("AI enhancer initialized")
        else:
            self.ai_enhancer = None
        
        # Initialize rate limiter
        # Convert simple rate limits to format expected by MultiServiceRateLimiter
        rate_limits = self.config.get('rate_limits', {})
        custom_limits = {
            service: {'rate': rate, 'burst': int(rate * 3)}
            for service, rate in rate_limits.items()
        }
        self.rate_limiter = MultiServiceRateLimiter(custom_limits=custom_limits)
        
        logger.info(f"Initialized {len(self.fetchers)} fetchers")
    
    def process_all_sources(
        self,
        max_items_per_source: int = 50
    ) -> Dict[str, Any]:
        """
        Process content from all enabled sources.
        
        Args:
            max_items_per_source: Maximum items to fetch per source
            
        Returns:
            Processing statistics
        """
        logger.info(f"Starting multi-source content processing (max {max_items_per_source} per source)")
        
        all_content = []
        
        # Fetch from each source
        for source_name, fetcher in self.fetchers.items():
            logger.info(f"Fetching from {source_name}...")
            
            try:
                if source_name == 'pubmed':
                    # Special handling for PubMed
                    content_items = self._fetch_pubmed_articles(max_items_per_source)
                elif source_name == 'youtube':
                    content_items = fetcher.fetch_ohdsi_content(max_results_per_query=max_items_per_source)
                elif source_name == 'github':
                    content_items = fetcher.fetch_ohdsi_content(max_results_per_query=max_items_per_source)
                elif source_name == 'discourse':
                    content_items = fetcher.fetch_ohdsi_content(max_results_per_category=max_items_per_source)
                elif source_name == 'wiki':
                    # Wiki has a different method name, handle both for compatibility
                    if hasattr(fetcher, 'fetch_ohdsi_documentation'):
                        content_items = fetcher.fetch_ohdsi_documentation(max_pages=max_items_per_source)
                    elif hasattr(fetcher, 'fetch_ohdsi_content'):
                        content_items = fetcher.fetch_ohdsi_content(max_pages=max_items_per_source)
                    else:
                        logger.warning(f"Wiki fetcher missing expected method")
                        content_items = []
                else:
                    content_items = []
                
                logger.info(f"Fetched {len(content_items)} items from {source_name}")
                
                # Add source metadata
                for item in content_items:
                    item['source'] = source_name
                
                all_content.extend(content_items)
                
                self.stats['by_source'][source_name] = len(content_items)
                self.stats['total_fetched'] += len(content_items)
                
            except Exception as e:
                logger.error(f"Error fetching from {source_name}: {e}")
                self.stats['errors'] += 1
        
        # Process all content
        # Note: The queue_manager handles indexing during routing,
        # so we don't need to index again here
        processed_content = self._process_content_batch(all_content)
        
        # Don't index here - queue_manager already handles it during routing
        # self._index_content_batch(processed_content)
        
        # Generate summary
        self._generate_summary()
        
        return self.stats
    
    def _fetch_pubmed_articles(self, max_items: int) -> List[Dict[str, Any]]:
        """
        Fetch articles from PubMed with citation information.
        """
        try:
            retriever = self.fetchers.get('pubmed')
            if not retriever:
                return []
            
            # Use OHDSI-specific queries
            queries = [
                'OHDSI',
                'OMOP CDM',
                'Observational Health Data Sciences',
                'OHDSI AND network study'
            ]
            
            all_articles = []
            items_per_query = max_items // len(queries)
            
            for query in queries:
                # First search for PMIDs
                pmids = retriever.search_pubmed(query, max_results=items_per_query)
                if pmids:
                    # Then fetch full article details
                    articles = retriever.fetch_article_details(pmids)
                    
                    # Fetch enriched citation information for these articles
                    logger.info(f"Fetching enriched citations for {len(pmids)} articles...")
                    citations = retriever.fetch_citations(pmids, fetch_metadata=True)
                    
                    # Add enriched citation data to each article
                    for article in articles:
                        pmid = article.get('pmid')
                        if pmid and pmid in citations:
                            article['citations'] = citations[pmid]
                            # Log if we got enriched citations
                            cited_by = citations[pmid].get('cited_by', [])
                            if cited_by and isinstance(cited_by[0], dict):
                                logger.debug(f"✅ Article {pmid} has enriched citations with metadata")
                        else:
                            article['citations'] = {
                                'cited_by': [],
                                'references': [],
                                'similar': []
                            }
                    
                    all_articles.extend(articles)
            
            logger.info(f"Fetched {len(all_articles)} articles with citation data")
            return all_articles[:max_items]
            
        except Exception as e:
            logger.error(f"Error fetching PubMed articles: {e}")
            return []
    
    def _process_content_batch(
        self,
        content_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process a batch of content items.
        """
        processed_items = []
        
        for item in content_items:
            try:
                processed = self._process_single_item(item)
                if processed:
                    processed_items.append(processed)
                    self.stats['total_processed'] += 1
                    
                    # Track by type
                    content_type = processed.get('content_type', 'unknown')
                    self.stats['by_type'][content_type] = self.stats['by_type'].get(content_type, 0) + 1
                    
            except Exception as e:
                logger.error(f"Error processing item: {e}")
                logger.exception(e)
                self.stats['errors'] += 1
        
        return processed_items
    
    def _process_single_item(
        self,
        item: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single content item through the pipeline.
        """
        try:
            # Step 1: Determine content type
            content_type = self._determine_content_type(item)
            item['content_type'] = content_type
            
            # Step 2: Normalize content
            normalized = self.normalizer.normalize(item, content_type)
            
            # Step 3: Check for duplicates
            is_duplicate, existing_id = self.deduplicator.check_duplicate(normalized)
            if is_duplicate:
                logger.info(f"Duplicate found: {normalized.get('title', '')[:50]}")
                self.stats['duplicates_found'] += 1
                
                # Check if we have enriched citations to update
                if normalized.get('citations'):
                    cited_by = normalized.get('citations', {}).get('cited_by', [])
                    if cited_by and isinstance(cited_by[0], dict) and 'title' in cited_by[0]:
                        # We have enriched citations - update the existing document
                        logger.info(f"Updating existing document {existing_id} with {len(cited_by)} enriched citations")
                        try:
                            # Update just the citations field in the existing document
                            self.es_client.update(
                                index=self.config['content_index'],
                                id=existing_id,
                                body={
                                    'doc': {
                                        'citations': normalized['citations'],
                                        'updated_at': datetime.utcnow().isoformat()
                                    }
                                }
                            )
                            self.stats['documents_updated'] = self.stats.get('documents_updated', 0) + 1
                            logger.info(f"Successfully updated citations for {existing_id}")
                        except Exception as e:
                            logger.error(f"Failed to update citations for {existing_id}: {e}")
                
                return None
            
            # Step 4: Calculate quality score (internal use only, not stored in v3 schema)
            quality_score = self.quality_scorer.calculate_quality_score(normalized)
            # Don't add quality_score to normalized - it's calculated internally for routing decisions
            
            # Step 5: ML classification
            classification = self.ml_classifier.classify(normalized)
            normalized.update(classification)
            
            # Step 6: AI enhancement (if enabled)
            if self.ai_enhancer and self.config.get('enable_ai_enhancement'):
                normalized = self.ai_enhancer.enhance_content(
                    normalized,
                    content_type
                )
                
                # Extract key AI fields for easier searching
                if 'ai_enrichment' in normalized:
                    enrichment = normalized['ai_enrichment']
                    normalized['ai_enhanced'] = True
                    normalized['ai_is_ohdsi'] = enrichment.get('is_ohdsi_related', False)
                    normalized['ai_confidence'] = enrichment.get('confidence_score', 0)
                    normalized['categories'] = enrichment.get('predicted_categories', [])  # v3: use 'categories'
                    normalized['ai_summary'] = enrichment.get('summary', '')
                    # Don't store ai_quality_score in v3 schema - use ai_confidence instead
                    normalized['ai_tools'] = enrichment.get('ohdsi_tools_mentioned', [])
                    
                    # Store main embedding for semantic search
                    if 'embeddings' in enrichment and 'summary_embedding' in enrichment['embeddings']:
                        normalized['embedding'] = enrichment['embeddings']['summary_embedding']
            
            # Step 7: Find relationships with existing content
            if self.ai_enhancer and self.config.get('enable_relationships', True):
                try:
                    # Get sample of existing content for relationship discovery
                    existing_sample = self._get_existing_content_sample(size=50)  # Reduced sample size
                    relationships = self.ai_enhancer.discover_relationships(
                        normalized,
                        existing_sample
                    )
                    normalized['relationships'] = relationships
                    logger.debug(f"Found {len(relationships.get('related_content', []))} related items")
                except Exception as e:
                    logger.warning(f"Relationship discovery failed: {e}")
                    # Continue without relationships rather than failing
                    normalized['relationships'] = {}
            
            # Step 8: Add metadata and ensure content categorization
            normalized['indexed_date'] = datetime.utcnow().isoformat()
            normalized['pipeline_version'] = '2.0'
            
            # Ensure content type and source are clearly set for filtering
            normalized['content_type'] = content_type  # article, video, repository, discussion, documentation
            # Only set source if normalizer didn't already set it (normalizers set correct value based on content type)
            if 'source' not in normalized or not normalized['source']:
                normalized['source'] = item.get('source', 'unknown')  # pubmed, youtube, github, discourse, wiki
            
            # Add display metadata for UI
            normalized['display_type'] = self._get_display_type(content_type)
            normalized['icon_type'] = self._get_icon_type(content_type)
            normalized['content_category'] = self._get_content_category(content_type)
            
            # Step 9: Route to appropriate queue (after all fields are set)
            routing = self.queue_manager.route_content(normalized, classification)
            
            # Map routing destination to proper approval status
            if routing['destination'] == 'approved':
                normalized['approval_status'] = 'approved'
            elif routing['destination'] in ['review_high', 'review_low']:
                normalized['approval_status'] = 'pending'
            elif routing['destination'] == 'rejected':
                normalized['approval_status'] = 'rejected'
            else:
                normalized['approval_status'] = 'pending'  # Default to pending
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error processing item: {e}")
            return None
    
    def _determine_content_type(self, item: Dict[str, Any]) -> str:
        """
        Determine the content type based on source and metadata.
        """
        source = item.get('source', '')
        
        if source == 'pubmed':
            return 'article'
        elif source == 'youtube':
            return 'video'
        elif source == 'github':
            return 'repository'
        elif source == 'discourse':
            return 'discussion'
        elif source == 'wiki':
            return 'documentation'
        else:
            # Try to infer from content
            if 'video_id' in item or 'channel_name' in item:
                return 'video'
            elif 'repo_name' in item or 'stars_count' in item:
                return 'repository'
            elif 'topic_id' in item or 'reply_count' in item:
                return 'discussion'
            elif 'doc_type' in item:
                return 'documentation'
            else:
                return 'article'
    
    def _get_display_type(self, content_type: str) -> str:
        """
        Get human-readable display type for UI.
        """
        display_types = {
            'article': 'Research Article',
            'video': 'Video Content',
            'repository': 'Code Repository',
            'discussion': 'Forum Discussion',
            'documentation': 'Documentation'
        }
        return display_types.get(content_type, content_type.title())
    
    def _get_icon_type(self, content_type: str) -> str:
        """
        Get icon identifier for UI display.
        """
        icon_types = {
            'article': 'document-text',
            'video': 'play-circle',
            'repository': 'code',
            'discussion': 'chat-bubble',
            'documentation': 'book-open'
        }
        return icon_types.get(content_type, 'document')
    
    def _get_content_category(self, content_type: str) -> str:
        """
        Get broader category for filtering.
        """
        categories = {
            'article': 'research',
            'video': 'media',
            'repository': 'code',
            'discussion': 'community',
            'documentation': 'reference'
        }
        return categories.get(content_type, 'other')
    
    def _get_existing_content_sample(self, size: int = 100) -> List[Dict[str, Any]]:
        """
        Get a sample of existing content for relationship discovery.
        """
        if not self.es_client:
            return []
        
        try:
            response = self.es_client.search(
                index=self.config.get('content_index', 'ohdsi_content_v3'),
                body={
                    "size": size,
                    "query": {
                        "function_score": {
                            "query": {"match_all": {}},
                            "random_score": {}
                        }
                    },
                    "_source": ["id", "title", "content_type", "ai_enrichment.embeddings"]
                }
            )
            
            return [hit['_source'] for hit in response['hits']['hits']]
            
        except Exception as e:
            logger.error(f"Error fetching existing content: {e}")
            return []
    
    def _index_content_batch(
        self,
        content_items: List[Dict[str, Any]]
    ):
        """
        Index content batch to Elasticsearch.
        """
        if not self.es_client or not content_items:
            return
        
        index_name = self.config.get('content_index', 'ohdsi_content_v3')
        
        try:
            # Prepare bulk actions
            actions = []
            for item in content_items:
                action = {
                    "_index": index_name,
                    "_id": item.get('id', item.get('fingerprint')),
                    "_source": item
                }
                actions.append(action)
            
            # Bulk index
            success, failed = helpers.bulk(
                self.es_client,
                actions,
                stats_only=True,
                raise_on_error=False
            )
            
            logger.info(f"Indexed {success} items to {index_name}")
            if failed:
                logger.warning(f"Failed to index {failed} items")
            
            self.stats['total_indexed'] = success
            
        except Exception as e:
            logger.error(f"Error indexing to Elasticsearch: {e}")
    
    def _generate_summary(self):
        """
        Generate processing summary.
        """
        logger.info("\n" + "="*60)
        logger.info("PIPELINE PROCESSING SUMMARY")
        logger.info("="*60)
        logger.info(f"Total fetched: {self.stats['total_fetched']}")
        logger.info(f"Total processed: {self.stats['total_processed']}")
        logger.info(f"Total indexed: {self.stats['total_indexed']}")
        logger.info(f"Duplicates found: {self.stats['duplicates_found']}")
        logger.info(f"Errors: {self.stats['errors']}")
        
        logger.info("\nBy Source:")
        for source, count in self.stats['by_source'].items():
            logger.info(f"  {source}: {count}")
        
        logger.info("\nBy Type:")
        for content_type, count in self.stats['by_type'].items():
            logger.info(f"  {content_type}: {count}")
        
        if self.ai_enhancer:
            ai_stats = self.ai_enhancer.get_stats()
            logger.info("\nAI Enhancement:")
            logger.info(f"  Processed: {ai_stats.get('processed', 0)}")
            logger.info(f"  Cached: {ai_stats.get('cached', 0)}")
            logger.info(f"  API calls: {ai_stats.get('api_calls', 0)}")
        
        logger.info("="*60 + "\n")
    
    def run_daily_fetch(self) -> Dict[str, Any]:
        """
        Run daily content fetch with configured limits.
        """
        logger.info("Starting daily content fetch...")
        
        # Daily limits per source
        daily_limits = {
            'pubmed': 100,
            'youtube': 20,
            'github': 30,
            'discourse': 50,
            'wiki': 10
        }
        
        results = {}
        
        for source_name, limit in daily_limits.items():
            if source_name in self.fetchers:
                try:
                    logger.info(f"Fetching {limit} items from {source_name}...")
                    
                    # Process this source
                    source_stats = self._process_single_source(source_name, limit)
                    results[source_name] = source_stats
                    
                except Exception as e:
                    logger.error(f"Error processing {source_name}: {e}")
                    results[source_name] = {'error': str(e)}
        
        # Overall summary
        results['summary'] = self.stats
        
        return results
    
    def run_daily_fetch_with_limits(self, fetch_limits: Dict[str, int]) -> Dict[str, Any]:
        """
        Run daily content fetch with custom limits per source.
        
        Args:
            fetch_limits: Dictionary mapping source name to max items
            
        Returns:
            Processing statistics
        """
        logger.info(f"Starting content fetch with custom limits: {fetch_limits}")
        
        results = {}
        
        for source_name, limit in fetch_limits.items():
            if source_name in self.fetchers:
                try:
                    logger.info(f"Fetching {limit} items from {source_name}...")
                    
                    # Process this source
                    source_stats = self._process_single_source(source_name, limit)
                    results[source_name] = source_stats
                    
                except Exception as e:
                    logger.error(f"Error processing {source_name}: {e}")
                    results[source_name] = {'error': str(e)}
        
        # Overall summary
        results['summary'] = self.stats
        
        return results
    
    def _process_single_source(
        self,
        source_name: str,
        max_items: int
    ) -> Dict[str, Any]:
        """
        Process a single source.
        """
        fetcher = self.fetchers.get(source_name)
        if not fetcher:
            return {'error': f'Fetcher not found for {source_name}'}
        
        # Fetch content
        try:
            if source_name == 'pubmed':
                content_items = self._fetch_pubmed_articles(max_items)
            elif source_name == 'youtube':
                content_items = fetcher.fetch_ohdsi_content(max_results_per_query=max_items)
            elif source_name == 'github':
                content_items = fetcher.fetch_ohdsi_content(max_results_per_query=max_items)
            elif source_name == 'discourse':
                content_items = fetcher.fetch_ohdsi_content(max_results_per_category=max_items)
            elif source_name == 'wiki':
                # Wiki has a different method name, handle both for compatibility
                if hasattr(fetcher, 'fetch_ohdsi_documentation'):
                    content_items = fetcher.fetch_ohdsi_documentation(max_pages=max_items)
                elif hasattr(fetcher, 'fetch_ohdsi_content'):
                    content_items = fetcher.fetch_ohdsi_content(max_pages=max_items)
                else:
                    logger.warning(f"Wiki fetcher missing expected method")
                    content_items = []
            else:
                content_items = []
        except Exception as e:
            logger.error(f"Error fetching from {source_name}: {e}")
            content_items = []
        
        # Add source metadata
        for item in content_items:
            item['source'] = source_name
        
        # Process and index
        processed = self._process_content_batch(content_items)
        self._index_content_batch(processed)
        
        return {
            'fetched': len(content_items),
            'processed': len(processed),
            'indexed': len(processed)
        }


# Celery task wrapper
app = Celery('ohdsi_pipeline')

@app.task(bind=True, max_retries=3)
def run_enhanced_pipeline(self):
    """
    Celery task to run the enhanced pipeline.
    """
    try:
        orchestrator = ContentPipelineOrchestrator()
        results = orchestrator.run_daily_fetch()
        return results
    except Exception as exc:
        logger.error(f"Pipeline task failed: {exc}")
        raise self.retry(exc=exc, countdown=300)  # Retry after 5 minutes


def main():
    """
    Main entry point for testing.
    """
    orchestrator = ContentPipelineOrchestrator()
    
    # Test with very small batch
    results = orchestrator.process_all_sources(max_items_per_source=2)
    
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()