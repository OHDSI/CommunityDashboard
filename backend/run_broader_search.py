#!/usr/bin/env python3
"""Run the official OHDSI article search with broader search terms."""

import sys
import os
sys.path.append('/app')

from jobs.article_classifier.wrapper import ArticleClassifierWrapper
from elasticsearch import Elasticsearch
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run broader OHDSI article search."""
    logger.info("Starting broader OHDSI article search...")
    
    # Initialize Elasticsearch client
    es_client = Elasticsearch(['http://elasticsearch:9200'])
    
    # Initialize wrapper with v2 classifier
    wrapper = ArticleClassifierWrapper(
        es_client=es_client,
        threshold=0.5,  # Lower threshold for broader search
        auto_approve_threshold=0.7,
        use_enhanced=True,
        use_v2=True
    )
    
    # Run broader search with multiple terms
    search_queries = [
        "OHDSI",
        "OMOP CDM",
        "Observational Health Data Sciences",
        "ATLAS OHDSI", 
        "HADES OHDSI",
        "ACHILLES OHDSI",
        "WebAPI OHDSI",
        "FeatureExtraction OHDSI",
        "PatientLevelPrediction",
        "CohortMethod OHDSI",
        "DataQualityDashboard OHDSI",
        "Common Data Model healthcare"
    ]
    
    total_fetched = 0
    total_auto_approved = 0
    total_for_review = 0
    
    for query in search_queries:
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Searching for: {query}")
            logger.info(f"{'='*60}")
            
            # Search and process articles
            result = wrapper.fetch_and_classify_articles(
                query=query,
                max_results=20,  # 20 per query to avoid overwhelming
                days_back=365  # Look back 1 year for broader search
            )
            
            if result:
                logger.info(f"Results for '{query}':")
                logger.info(f"  Articles fetched: {result.get('articles_fetched', 0)}")
                logger.info(f"  Auto-approved: {result.get('auto_approved', 0)}")
                logger.info(f"  Sent for review: {result.get('for_review', 0)}")
                logger.info(f"  Duplicates found: {result.get('duplicates_found', 0)}")
                
                total_fetched += result.get('articles_fetched', 0)
                total_auto_approved += result.get('auto_approved', 0) 
                total_for_review += result.get('for_review', 0)
            else:
                logger.warning(f"No results returned for query: {query}")
                
        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")
            continue
    
    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total articles fetched: {total_fetched}")
    logger.info(f"Total auto-approved: {total_auto_approved}")
    logger.info(f"Total for review: {total_for_review}")
    logger.info(f"Total processed: {total_auto_approved + total_for_review}")
    
    if total_auto_approved + total_for_review > 0:
        approval_rate = (total_auto_approved / (total_auto_approved + total_for_review)) * 100
        logger.info(f"Auto-approval rate: {approval_rate:.1f}%")
    
    logger.info("\nBroader search completed successfully!")

if __name__ == "__main__":
    main()