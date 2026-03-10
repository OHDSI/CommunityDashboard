"""
Celery task wrapper for ArticleClassifier integration with OHDSI Dashboard.
Handles article retrieval from PubMed, classification, and storage in Elasticsearch.
"""

import logging
import json
import time
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
from celery import shared_task
from elasticsearch import Elasticsearch

from .enhanced_classifier_v2 import EnhancedOHDSIClassifierV2
from .retriever import PubMedRetriever

logger = logging.getLogger(__name__)


class ArticleClassifierWrapper:
    """
    Wrapper to integrate ArticleClassifier with OHDSI Dashboard.
    Fetches articles from PubMed, classifies them, and stores in Elasticsearch.
    """
    
    def __init__(self, es_client: Elasticsearch,
                 threshold: float = 0.7,
                 auto_approve_threshold: float = 0.7,
                 priority_threshold: float = 0.5,
                 reject_threshold: float = 0.3,
                 approval_mode: str = 'combined',
                 data_dir: str = None,
                 topic_name: str = 'ohdsi'):
        """
        Initialize the wrapper.

        Args:
            es_client: Elasticsearch client
            threshold: Minimum probability threshold for positive classification (deprecated, use tiered thresholds)
            auto_approve_threshold: Threshold for auto-approval (default 0.7, aligns with QueueManager)
            priority_threshold: Threshold for high-priority review queue (default 0.5)
            reject_threshold: Threshold below which content is auto-rejected (default 0.3)
            approval_mode: 'combined' (default), 'either', or 'both' for approval logic
            data_dir: Directory containing training data
            topic_name: Topic name for loading learned queries and author configs (default 'ohdsi')

        Tiered Routing (aligned with QueueManager):
            - >= auto_approve_threshold (0.7): Auto-approved to content index
            - >= priority_threshold (0.5): High-priority review queue
            - >= reject_threshold (0.3): Low-priority review queue
            - < reject_threshold (0.3): Auto-rejected
        """
        self.es_client = es_client
        self.threshold = threshold
        self.auto_approve_threshold = auto_approve_threshold
        self.priority_threshold = priority_threshold
        self.reject_threshold = reject_threshold
        self.approval_mode = approval_mode
        self.topic_name = topic_name

        logger.info("Using V2 enhanced classifier with improved features and regularization")
        self.classifier = EnhancedOHDSIClassifierV2(data_dir=data_dir, model_type="randomforest")
        
        self.retriever = PubMedRetriever(
            email=os.getenv('NCBI_ENTREZ_EMAIL'),
            api_key=os.getenv('NCBI_ENTREZ_API_KEY'),
        )

        # Elasticsearch indices
        self.review_index = "ohdsi_review_queue_v3"
        self.content_index = "ohdsi_content_v3"

        # Ensure classifier is trained
        self._ensure_trained()

        # Load calibrated thresholds from model metadata if available
        calibrated = getattr(self.classifier, 'metadata_', {}).get('calibrated_thresholds')
        if calibrated:
            self.auto_approve_threshold = calibrated['auto_approve']
            self.reject_threshold = calibrated['auto_reject']
            self.priority_threshold = calibrated.get(
                'priority_review',
                (self.auto_approve_threshold + self.reject_threshold) / 2
            )
            logger.info(
                f"Using calibrated thresholds: approve={self.auto_approve_threshold:.2f}, "
                f"priority={self.priority_threshold:.2f}, reject={self.reject_threshold:.2f}"
            )
    
    def _should_auto_approve(self, ml_score: float, gpt_score: float = 0.0, combined_score: float = 0.0) -> bool:
        """
        Determine if article should be auto-approved based on approval mode.
        
        Args:
            ml_score: ML model probability score
            gpt_score: GPT model probability score
            combined_score: Combined probability score
            
        Returns:
            True if should auto-approve, False otherwise
        """
        if self.approval_mode == 'combined':
            # Default: use combined score
            return combined_score >= self.auto_approve_threshold
        elif self.approval_mode == 'either':
            # Either ML or GPT exceeds threshold
            return ml_score >= self.auto_approve_threshold or gpt_score >= self.auto_approve_threshold
        elif self.approval_mode == 'both':
            # Both ML and GPT must exceed threshold
            return ml_score >= self.auto_approve_threshold and gpt_score >= self.auto_approve_threshold
        else:
            # Fallback to combined mode
            return combined_score >= self.auto_approve_threshold
    
    def _ensure_trained(self):
        """Ensure the classifier model is trained."""
        try:
            self.classifier.load_model()
            logger.info("Loaded existing classifier model")
        except FileNotFoundError:
            logger.info("Training new classifier model...")
            metrics = self.classifier.train()
            logger.info(f"Model trained: {metrics}")
    
    def fetch_and_classify_articles(self, 
                                   query: str = None,
                                   max_results: int = 100,
                                   days_back: int = 30) -> Dict:
        """
        Fetch articles from PubMed and classify them.
        
        Args:
            query: PubMed search query (if None, uses default OHDSI-relevant query)
            max_results: Maximum number of articles to fetch
            days_back: Number of days to look back
            
        Returns:
            Dictionary with statistics and results
        """
        # Use default OHDSI-relevant query if not provided
        if query is None:
            # Broader search terms that find OHDSI-relevant articles without using direct keywords
            query = """(
                "observational data" OR "drug safety" OR "health risk" OR 
                "clinical databases" OR "electronic health records" OR 
                "adverse drug" OR "pharmacovigilance" OR "comparative effectiveness" OR
                "self-controlled case" OR "cohort study design" OR
                "real world evidence" OR "patient level prediction" OR
                "population health" OR "medical informatics" OR
                "health data science" OR "clinical phenotyping" OR
                "drug utilization" OR "treatment pathways" OR
                "network study" OR "distributed analysis"
            ) AND ("database" OR "cohort" OR "observational")"""
        
        logger.info(f"Fetching articles with query: {query[:100]}...")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Fetch articles from PubMed
        articles = self.retriever.search_and_fetch(
            query=query,
            max_results=max_results,
            start_date=start_date.strftime("%Y/%m/%d"),
            end_date=end_date.strftime("%Y/%m/%d")
        )
        
        logger.info(f"Fetched {len(articles)} articles from PubMed")

        return self._enrich_classify_and_route(articles)

    def _enrich_classify_and_route(self, articles: List[Dict]) -> Dict:
        """
        Enrich articles with citation data, classify them, and route to
        appropriate queues. Shared by fetch_and_classify_articles and run_daily_fetch.

        Args:
            articles: List of article dicts from PubMed fetch

        Returns:
            Dictionary with classification statistics
        """
        # Fetch citation data for new articles so citation features work at inference
        pmids_for_citations = [str(a.get('pmid', '')) for a in articles if a.get('pmid')]
        if pmids_for_citations:
            try:
                citation_data = self.retriever.fetch_citations(
                    pmids_for_citations, batch_size=100, fetch_metadata=False
                )
                for article in articles:
                    pmid = str(article.get('pmid', ''))
                    if pmid in citation_data:
                        article['citations'] = citation_data[pmid]
                logger.info(f"Fetched citation data for {len(citation_data)} articles")
            except Exception as e:
                logger.warning(f"Could not fetch citation data: {e}. Citation features will be zeros.")

        if not articles:
            return {
                "status": "no_articles",
                "fetched": 0,
                "classified": 0,
                "positive": 0,
                "queued": 0,
                "auto_approved": 0,
            }

        # Classify articles using V2 enhanced classifier
        positive_count = 0
        queued_count = 0
        auto_approved_count = 0

        for idx, article in enumerate(articles):
            # Get enhanced prediction
            result = self.classifier.predict_from_article(article)

            # Add classification results to article using v3 fields
            article['ml_score'] = float(result.get('ml_probability', 0))
            article['ai_confidence'] = float(result.get('ai_confidence', result.get('gpt_probability', 0)))
            article['final_score'] = float(result.get('final_score', result.get('combined_probability', 0)))
            article['quality_score'] = float(result.get('quality_score', 0.5))
            article['categories'] = result.get('categories', result.get('predicted_categories', []))
            article['ai_summary'] = result.get('gpt_reasoning', '')

            # Keep old fields for backward compatibility during migration
            article['gpt_score'] = article['ai_confidence']
            article['combined_score'] = article['final_score']
            article['predicted_categories'] = article['categories']
            article['gpt_reasoning'] = article['ai_summary']
            article['classification_factors'] = result.get('instance_factors', [])

            # Check if already known
            if result.get('already_known', False):
                logger.debug(f"Article already known: {article.get('title')}")
                continue

            # Tiered routing based on final_score
            final_score = article['final_score']
            has_known_author = result.get('has_known_author', True)

            if final_score >= self.auto_approve_threshold:
                # Tier 1: Auto-approve
                positive_count += 1
                if self._should_auto_approve(article['ml_score'], article['ai_confidence'], final_score):
                    self._add_to_content_index(article)
                    auto_approved_count += 1
                    logger.info(f"Auto-approved (score={final_score:.2f}): {article.get('title', '')[:50]}")
                else:
                    self._add_to_review_queue(article, priority='high')
                    queued_count += 1
                    logger.info(f"High-priority review (score={final_score:.2f}): {article.get('title', '')[:50]}")

            elif final_score >= self.priority_threshold:
                # Tier 2: High-priority review queue
                positive_count += 1
                self._add_to_review_queue(article, priority='high')
                queued_count += 1
                logger.info(f"High-priority review (score={final_score:.2f}): {article.get('title', '')[:50]}")

            elif final_score >= self.reject_threshold:
                # Tier 3: Review queue — boost to high priority if unknown author
                priority = 'high' if not has_known_author else 'low'
                self._add_to_review_queue(article, priority=priority)
                queued_count += 1
                if not has_known_author:
                    logger.info(f"Priority-boosted review (unknown author, score={final_score:.2f}): {article.get('title', '')[:50]}")
                else:
                    logger.info(f"Low-priority review (score={final_score:.2f}): {article.get('title', '')[:50]}")

            else:
                # Tier 4: Auto-reject
                article['auto_rejected'] = True
                self._add_to_review_queue(article, status='rejected')
                logger.info(f"Auto-rejected (score={final_score:.2f}): {article.get('title', '')[:50]}")

        return {
            "status": "success",
            "fetched": len(articles),
            "classified": len(articles),
            "positive": positive_count,
            "queued": queued_count,
            "auto_approved": auto_approved_count
        }
    
    def _add_to_review_queue(self, article: Dict, status: str = "pending", priority: str = None):
        """Add article to the review queue in Elasticsearch.

        Args:
            article: Article data dictionary
            status: Queue status ('pending', 'rejected')
            priority: Priority level ('high', 'low') - determines priority score
        """
        # Format authors as objects with comprehensive metadata
        authors = []
        for author in article.get("authors", []):
            if isinstance(author, str):
                authors.append({"name": author})
            elif isinstance(author, dict):
                # Preserve all author metadata including ORCID
                authors.append(author)

        # Calculate priority score based on tier
        if priority == 'high':
            priority_score = self._calculate_priority(article)  # 5-9 range
            priority_level = 'high'
        elif priority == 'low':
            priority_score = max(1, self._calculate_priority(article) - 4)  # 1-5 range
            priority_level = 'low'
        else:
            priority_score = self._calculate_priority(article)
            priority_level = 'medium'

        doc = {
            "id": article.get("id"),
            "source": "pubmed",  # Always set source for proper badge colors
            "pmid": article.get("pmid"),
            "pmc_id": article.get("pmc_id"),
            "title": article.get("title"),
            "vernacular_title": article.get("vernacular_title"),
            "abstract": article.get("abstract"),
            "abstract_sections": article.get("abstract_sections", {}),
            "url": article.get("url"),
            "pmc_url": article.get("pmc_url"),
            "content_type": "article",
            "authors": authors,
            "author_count": article.get("author_count", len(authors)),
            "submitted_date": datetime.now().isoformat(),
            "published_date": article.get("published_date"),
            "electronic_date": article.get("electronic_date"),
            "print_date": article.get("print_date"),
            "received_date": article.get("received_date"),
            "accepted_date": article.get("accepted_date"),
            "revised_date": article.get("revised_date"),
            "pubmed_date": article.get("pubmed_date"),
            "medline_date": article.get("medline_date"),
            "ml_score": article.get("ml_score", 0),
            "ai_confidence": article.get("ai_confidence", article.get("gpt_score", 0)),  # v3: use ai_confidence
            "final_score": article.get("final_score", article.get("combined_score", article.get("ml_score", 0))),  # v3: use final_score
            "quality_score": article.get("quality_score", 0.5),  # Include quality score for transparency
            "categories": article.get("categories", article.get("predicted_categories", [])),  # v3: use categories
            "ai_summary": article.get("ai_summary", article.get("gpt_reasoning", "")),  # v3: use ai_summary
            # Keep old fields for backward compatibility during migration
            "gpt_score": article.get("ai_confidence", article.get("gpt_score", 0)),
            "combined_score": article.get("final_score", article.get("combined_score", article.get("ml_score", 0))),
            "predicted_categories": article.get("categories", article.get("predicted_categories", [])),
            "gpt_reasoning": article.get("ai_summary", article.get("gpt_reasoning", "")),
            "status": status,
            "priority": priority_score,
            "priority_level": priority_level,
            "classification_factors": article.get("classification_factors", []),
            "journal": article.get("journal"),
            "journal_info": article.get("journal_info", {}),
            "year": article.get("year"),
            "doi": article.get("doi"),
            "volume": article.get("volume"),
            "issue": article.get("issue"),
            "pages": article.get("pages"),
            "keywords": article.get("keywords", []),
            # Convert mesh_terms to simple string list for Elasticsearch
            "mesh_terms": self._extract_mesh_term_names(article.get("mesh_terms", [])),
            "publication_types": article.get("publication_types", []),
            # Convert chemicals to simple string list for Elasticsearch
            "chemicals": self._extract_chemical_names(article.get("chemicals", [])),
            "language": article.get("language", "eng"),
            "grants": article.get("grants", []),
            "has_funding": article.get("has_funding", False),
            "reference_count": article.get("reference_count", 0),
            "medline_status": article.get("medline_status"),
            "indexing_method": article.get("indexing_method"),
            "has_pmc_full_text": article.get("has_pmc_full_text", False)
        }

        try:
            self.es_client.index(
                index=self.review_index,
                id=doc["id"],
                body=doc
            )
            logger.info(f"Added to review queue: {doc['title'][:50]}...")
        except Exception as e:
            logger.error(f"Failed to add to review queue: {e}")
    
    def _add_to_content_index(self, article: Dict):
        """Add article directly to content index (auto-approved)."""
        # Format authors as objects with comprehensive metadata
        authors = []
        for author in article.get("authors", []):
            if isinstance(author, str):
                authors.append({"name": author})
            elif isinstance(author, dict):
                # Preserve all author metadata including ORCID
                authors.append(author)

        doc = {
            "id": article.get("id"),
            "source": "pubmed",  # Always set source for proper badge colors
            "pmid": article.get("pmid"),
            "pmc_id": article.get("pmc_id"),
            "title": article.get("title"),
            "vernacular_title": article.get("vernacular_title"),
            "abstract": article.get("abstract"),
            "abstract_sections": article.get("abstract_sections", {}),
            "content": article.get("content", article.get("abstract")),
            "url": article.get("url"),
            "pmc_url": article.get("pmc_url"),
            "content_type": "article",
            "authors": authors,
            "author_count": article.get("author_count", len(authors)),
            "published_date": article.get("published_date", datetime.now().isoformat()),
            "electronic_date": article.get("electronic_date"),
            "print_date": article.get("print_date"),
            "received_date": article.get("received_date"),
            "accepted_date": article.get("accepted_date"),
            "revised_date": article.get("revised_date"),
            "pubmed_date": article.get("pubmed_date"),
            "medline_date": article.get("medline_date"),
            "ml_score": article.get("ml_score", 0),
            "ai_confidence": article.get("ai_confidence", article.get("gpt_score", 0)),  # v3: use ai_confidence
            "final_score": article.get("final_score", (article.get("ml_score", 0) + article.get("ai_confidence", 0)) / 2.0),  # v3: use final_score
            "approval_status": "approved",
            "categories": article.get("categories", article.get("predicted_categories", [])),  # v3: use categories
            "ai_summary": article.get("ai_summary", article.get("gpt_reasoning", "")),  # v3: use ai_summary
            # Keep old fields for backward compatibility
            "gpt_score": article.get("ai_confidence", article.get("gpt_score", 0)),
            "combined_score": article.get("final_score", (article.get("ml_score", 0) + article.get("ai_confidence", 0)) / 2.0),
            "ohdsi_categories": article.get("categories", article.get("predicted_categories", [])),
            "predicted_categories": article.get("categories", article.get("predicted_categories", [])),
            "gpt_reasoning": article.get("ai_summary", article.get("gpt_reasoning", "")),
            "view_count": 0,
            "bookmark_count": 0,
            "references": article.get("references", []),
            "cited_by": article.get("cited_by", []),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "suggest": {"input": article.get("title", "")},
            "journal": article.get("journal"),
            "journal_info": article.get("journal_info", {}),
            "year": article.get("year"),
            "doi": article.get("doi"),
            "volume": article.get("volume"),
            "issue": article.get("issue"),
            "pages": article.get("pages"),
            "keywords": article.get("keywords", []),
            # Convert mesh_terms to simple string list for Elasticsearch
            "mesh_terms": self._extract_mesh_term_names(article.get("mesh_terms", [])),
            "publication_types": article.get("publication_types", []),
            # Convert chemicals to simple string list for Elasticsearch
            "chemicals": self._extract_chemical_names(article.get("chemicals", [])),
            "language": article.get("language", "eng"),
            "grants": article.get("grants", []),
            "has_funding": article.get("has_funding", False),
            "reference_count": article.get("reference_count", 0),
            "medline_status": article.get("medline_status"),
            "indexing_method": article.get("indexing_method"),
            "has_pmc_full_text": article.get("has_pmc_full_text", False)
        }

        try:
            self.es_client.index(
                index=self.content_index,
                id=doc["id"],
                body=doc
            )
            logger.info(f"Auto-approved to content: {doc['title'][:50]}...")
        except Exception as e:
            logger.error(f"Failed to add to content index: {e}")
    
    def _extract_mesh_term_names(self, mesh_terms):
        """
        Extract descriptor names from mesh_terms structure.
        Handles both dict and string formats.
        """
        if not mesh_terms:
            return []
        
        result = []
        for term in mesh_terms:
            if isinstance(term, dict):
                # Extract descriptor_name from dict format
                descriptor = term.get('descriptor_name', '')
                if descriptor:
                    result.append(descriptor)
            elif isinstance(term, str):
                # Already a string, keep as is
                result.append(term)
        
        return result

    def _extract_chemical_names(self, chemicals):
        """
        Extract chemical substance names from chemicals structure.
        Handles both dict and string formats.
        """
        if not chemicals:
            return []

        result = []
        for chem in chemicals:
            if isinstance(chem, dict):
                name = chem.get('name', '')
                if name:
                    result.append(name)
            elif isinstance(chem, str):
                result.append(chem)

        return result

    def _calculate_priority(self, article: Dict) -> int:
        """
        Calculate priority score for review queue (0-10).
        """
        score = article.get("ml_score", 0)
        
        if score >= 0.9:
            return 9
        elif score >= 0.8:
            return 7
        elif score >= 0.7:
            return 5
        else:
            return 3
    
    def _load_topic_queries(self) -> List[str]:
        """
        Load topic queries from learned config file, falling back to
        hardcoded OHDSI queries if no config exists.
        """
        config_path = Path(__file__).parent / 'data' / f'{self.topic_name}_queries.json'
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
            queries = [q['query'] for q in config.get('queries', [])]
            if queries:
                logger.info(f"Loaded {len(queries)} learned queries from {config_path.name}")
                return queries
            logger.warning(f"Query config {config_path.name} has no queries, using defaults")

        # Fallback: hardcoded OHDSI queries (audited recall: 91.8%)
        return [
            "OHDSI OR OMOP",
            '"observational health" AND ("data" OR "methods")',
            '"drug safety" AND ("database" OR "observational")',
            '"pharmacovigilance" AND ("real world" OR "electronic health")',
            '"comparative effectiveness" AND ("observational" OR "database")',
            '"common data model" AND ("health" OR "clinical" OR "medical")',
            '"claims data" AND ("study" OR "analysis" OR "cohort")',
            '"electronic health records" AND ("cohort" OR "retrospective" OR "claims")',
            '"propensity score" AND ("observational" OR "claims" OR "electronic health")',
            '"incidence" AND ("cohort" OR "database" OR "claims")',
            '"prediction model" AND ("clinical" OR "patient" OR "health")',
            '"data quality" AND ("electronic health" OR "clinical data" OR "medical")',
            '"phenotyping" AND ("electronic health record" OR "clinical data" OR "algorithm")',
            '"COVID-19" AND ("electronic health records" OR "claims" OR "cohort study")',
        ]

    def _load_author_queries(self) -> List[str]:
        """Build PubMed author queries from the core authors config file."""
        config_path = Path(__file__).parent / 'data' / f'{self.topic_name}_core_authors.json'
        if not config_path.exists():
            logger.warning(f"Author config not found at {config_path}. "
                           "Run learn_queries.py or audit_retrieval.py to generate.")
            return []

        with open(config_path) as f:
            config = json.load(f)

        authors = [a['name'] for a in config.get('authors', [])]
        if not authors:
            return []

        # Split into batches of 10 authors per query
        queries = []
        for i in range(0, len(authors), 10):
            batch = authors[i:i+10]
            terms = ' OR '.join(f'"{name}"[Author]' for name in batch)
            queries.append(f"({terms})")

        logger.info(f"Built {len(queries)} author monitoring queries for {len(authors)} authors")
        return queries

    def run_daily_fetch(self) -> Dict:
        """
        Run the daily fetch and classification job.
        Fetches articles from the last 24 hours using optimized queries
        with cross-query deduplication.

        Queries are loaded from data/{topic_name}_queries.json if available
        (generated by query_learner), falling back to hardcoded OHDSI defaults.
        """
        topic_queries = self._load_topic_queries()
        author_queries = self._load_author_queries()

        all_queries = topic_queries + author_queries

        # === Phase 1: Collect unique PMIDs across all queries ===
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        start_str = start_date.strftime("%Y/%m/%d")
        end_str = end_date.strftime("%Y/%m/%d")

        all_pmids = set()
        query_stats = {}

        for query in all_queries:
            try:
                pmids = self.retriever.search_pubmed(
                    query=query, max_results=50,
                    start_date=start_str, end_date=end_str
                )
                new_pmids = set(pmids) - all_pmids
                query_stats[query[:60]] = {'total': len(pmids), 'new': len(new_pmids)}
                all_pmids.update(pmids)
                logger.info(f"Query '{query[:60]}...': {len(pmids)} results, {len(new_pmids)} new")
            except Exception as e:
                logger.error(f"Query failed: {query[:60]}... - {e}")

            time.sleep(0.5)  # Rate limiting between searches

        logger.info(f"Search phase complete: {len(all_pmids)} unique PMIDs from {len(all_queries)} queries")

        if not all_pmids:
            return {
                "status": "no_articles",
                "fetched": 0, "classified": 0, "positive": 0,
                "queued": 0, "auto_approved": 0,
                "queries_run": len(all_queries),
            }

        # === Phase 2: Fetch article details and classify ===
        pmid_list = list(all_pmids)
        logger.info(f"Fetching details for {len(pmid_list)} unique PMIDs")
        articles = self.retriever.fetch_article_details(pmid_list)
        logger.info(f"Fetched {len(articles)} article details")

        stats = self._enrich_classify_and_route(articles)

        total_stats = {
            "status": stats.get("status", "error"),
            "queries_run": len(all_queries),
            "unique_pmids": len(all_pmids),
            "fetched": stats.get("fetched", 0),
            "classified": stats.get("classified", 0),
            "positive": stats.get("positive", 0),
            "queued": stats.get("queued", 0),
            "auto_approved": stats.get("auto_approved", 0),
            "query_breakdown": query_stats,
        }

        logger.info(f"Daily fetch complete: {len(all_pmids)} unique PMIDs, "
                     f"{total_stats['classified']} classified, "
                     f"{total_stats['positive']} positive, "
                     f"{total_stats['auto_approved']} auto-approved")
        return total_stats
    
    def retrain_model(self, force: bool = False) -> Dict:
        """
        Retrain the classifier model with latest data.
        
        Args:
            force: Force retraining even if model exists
            
        Returns:
            Training metrics
        """
        logger.info("Retraining classifier model...")
        
        # Optionally fetch approved articles from Elasticsearch to update training data
        # This would require exporting approved articles to BibTeX format
        
        metrics = self.classifier.train(force_retrain=force)
        logger.info(f"Model retrained: {metrics}")
        return metrics


# Celery tasks
@shared_task
def run_article_classifier_daily():
    """
    Celery task to run daily article classification.

    Tiered Routing Thresholds (aligned with QueueManager):
        - AUTO_APPROVE_THRESHOLD (default 0.7): Auto-approve to content index
        - PRIORITY_THRESHOLD (default 0.5): High-priority review queue
        - REJECT_THRESHOLD (default 0.3): Below this is auto-rejected
    """
    from app.database import es_client
    from app.config import settings

    wrapper = ArticleClassifierWrapper(
        es_client=es_client,
        threshold=settings.classifier_threshold,
        auto_approve_threshold=float(os.getenv('AUTO_APPROVE_THRESHOLD', '0.7')),
        priority_threshold=float(os.getenv('PRIORITY_THRESHOLD', '0.5')),
        reject_threshold=float(os.getenv('REJECT_THRESHOLD', '0.3')),
        approval_mode=os.getenv('APPROVAL_MODE', 'combined'),
        topic_name=os.getenv('TOPIC_NAME', 'ohdsi'),
    )

    return wrapper.run_daily_fetch()


@shared_task
def classify_single_article(article_data: Dict):
    """
    Classify a single article.

    Args:
        article_data: Dictionary with article metadata

    Returns:
        Classification results
    """
    from app.database import es_client
    from app.config import settings

    wrapper = ArticleClassifierWrapper(
        es_client=es_client,
        threshold=settings.classifier_threshold,
        auto_approve_threshold=float(os.getenv('AUTO_APPROVE_THRESHOLD', '0.7')),
        priority_threshold=float(os.getenv('PRIORITY_THRESHOLD', '0.5')),
        reject_threshold=float(os.getenv('REJECT_THRESHOLD', '0.3')),
        approval_mode=os.getenv('APPROVAL_MODE', 'combined'),
    )

    classifier = wrapper.classifier
    result = classifier.predict_from_article(article_data)

    # Add to appropriate index based on tiered thresholds
    article_data.update(result)
    final_score = result.get('final_score', result.get('probability', 0))

    if final_score >= wrapper.auto_approve_threshold:
        # Tier 1: Auto-approve
        wrapper._add_to_content_index(article_data)
    elif final_score >= wrapper.priority_threshold:
        # Tier 2: High-priority review
        wrapper._add_to_review_queue(article_data, priority='high')
    elif final_score >= wrapper.reject_threshold:
        # Tier 3: Low-priority review
        wrapper._add_to_review_queue(article_data, priority='low')
    else:
        # Tier 4: Auto-reject
        article_data['auto_rejected'] = True
        wrapper._add_to_review_queue(article_data, status='rejected')

    return result


@shared_task
def retrain_classifier(force: bool = False):
    """
    Celery task to retrain the classifier model.
    """
    from app.database import es_client
    from app.config import settings

    wrapper = ArticleClassifierWrapper(
        es_client=es_client,
        threshold=settings.classifier_threshold,
        auto_approve_threshold=float(os.getenv('AUTO_APPROVE_THRESHOLD', '0.7')),
        priority_threshold=float(os.getenv('PRIORITY_THRESHOLD', '0.5')),
        reject_threshold=float(os.getenv('REJECT_THRESHOLD', '0.3')),
        approval_mode=os.getenv('APPROVAL_MODE', 'combined'),
    )

    return wrapper.retrain_model(force=force)


if __name__ == "__main__":
    # Test the wrapper
    import sys
    from elasticsearch import Elasticsearch
    
    es = Elasticsearch("http://localhost:9200")
    wrapper = ArticleClassifierWrapper(es_client=es, threshold=0.7)
    
    if len(sys.argv) > 1 and sys.argv[1] == "fetch":
        results = wrapper.run_daily_fetch()
        print(f"Results: {results}")
    elif len(sys.argv) > 1 and sys.argv[1] == "train":
        metrics = wrapper.retrain_model(force=True)
        print(f"Training metrics: {metrics}")
    else:
        print("Usage: python wrapper.py [fetch|train]")