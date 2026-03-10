#!/usr/bin/env python3
"""
Backfill per-instance classification_factors for existing ES documents.

Loads the trained model + feature extractor, re-computes feature values
for each article, and calculates value × importance for the top 7
non-TF-IDF features. Updates only the classification_factors field in ES.

No GPT calls, no re-scoring, no re-routing. Just feature extraction + math.

Usage:
    # Dry run (show what would be updated)
    python backfill_classification_factors.py --dry-run

    # Full run
    python backfill_classification_factors.py

    # Only update docs with missing/empty factors
    python backfill_classification_factors.py --only-missing
"""

import argparse
import json
import logging
import os
import sys
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, scan

# Add parent paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'jobs', 'article_classifier'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_model_and_extractor(model_dir=None):
    """Load trained model and feature extractor from metadata_v2.pkl."""
    if model_dir is None:
        # Try container path first, then local
        for candidate in ['/app/jobs/article_classifier/models',
                          os.path.join(os.path.dirname(__file__), '..', 'jobs', 'article_classifier', 'models')]:
            if os.path.exists(os.path.join(candidate, 'metadata_v2.pkl')):
                model_dir = candidate
                break

    if model_dir is None:
        raise FileNotFoundError("Could not find models directory with metadata_v2.pkl")

    metadata_path = os.path.join(model_dir, 'metadata_v2.pkl')
    logger.info(f"Loading metadata from {metadata_path}")
    with open(metadata_path, 'rb') as f:
        metadata = pickle.load(f)

    feature_extractor = metadata.get('feature_extractor')
    if feature_extractor is None:
        raise ValueError("No feature_extractor found in metadata_v2.pkl")

    # Load the model to get feature_importances_
    # Model filename follows pattern: {model_type}_model_v2.pkl
    model_type = metadata.get('model_type', 'randomforest')
    model_path = os.path.join(model_dir, f'{model_type}_model_v2.pkl')
    if not os.path.exists(model_path):
        # Fallback: try any *_model_v2.pkl file
        import glob
        candidates = glob.glob(os.path.join(model_dir, '*_model_v2.pkl'))
        if candidates:
            model_path = candidates[0]
        else:
            raise FileNotFoundError(f"No model file found in {model_dir}")
    logger.info(f"Loading model from {model_path}")
    with open(model_path, 'rb') as f:
        model = pickle.load(f)

    if not hasattr(model, 'feature_importances_'):
        raise ValueError("Model does not have feature_importances_ attribute")

    # Get feature names
    feature_names = feature_extractor.NON_TFIDF_FEATURES.copy()
    n_tfidf = feature_extractor.n_tfidf_features
    feature_names += [f'tfidf_{i}' for i in range(n_tfidf)]

    logger.info(f"Loaded model ({type(model).__name__}) with {len(feature_names)} features")
    logger.info(f"Feature extractor has {len(feature_extractor.topic_authors_)} topic authors, "
                f"{len(feature_extractor.topic_keywords_)} topic keywords")

    return model, feature_extractor, feature_names


def compute_instance_factors(model, feature_extractor, feature_names, article_dict):
    """
    Compute per-instance feature contributions using treeinterpreter.

    Returns list of top 7 factors: [{feature, value, contribution}, ...]
    Contributions are signed: positive = pushes toward OHDSI, negative = away.
    """
    from treeinterpreter import treeinterpreter as ti

    # Build DataFrame for feature extraction
    df = pd.DataFrame([article_dict])
    try:
        X = feature_extractor.transform(df)
    except Exception as e:
        logger.warning(f"Feature extraction failed for {article_dict.get('pmid', '?')}: {e}")
        return []

    X_arr = X.values if hasattr(X, 'values') else X
    if X_arr.ndim == 1:
        X_arr = X_arr.reshape(1, -1)

    # Tree path decomposition: prediction = bias + sum(contributions)
    _, _, contributions = ti.predict(model, X_arr)
    contribs = contributions[0, :, 1]  # class 1 (positive) contributions

    instance_factors = []
    for i, fname in enumerate(feature_names):
        if fname.startswith('tfidf_'):
            continue
        val = float(X_arr[0, i])
        instance_factors.append({
            'feature': fname.replace('_', ' ').title(),
            'value': round(val, 3),
            'contribution': round(float(contribs[i]), 6),
        })

    instance_factors.sort(key=lambda x: abs(x['contribution']), reverse=True)
    return instance_factors[:7]


def es_doc_to_article(doc):
    """Convert an ES document _source to the format expected by feature_extractor.transform()."""
    src = doc
    article = {
        'abstract': src.get('abstract', ''),
        'authors': src.get('authors', []),
        'keywords': src.get('keywords', []),
        'mesh_terms': src.get('mesh_terms', []),
        'doi': src.get('doi', ''),
        'pmid': src.get('pmid', ''),
    }

    # Feature extractor looks for 'ID' field with PMID prefix for citation lookup
    if article['pmid']:
        article['ID'] = f"PMID{article['pmid']}"
    elif src.get('id', '').startswith('PMID'):
        article['ID'] = src['id']
        article['pmid'] = src['id'].replace('PMID', '')

    return article


def main():
    parser = argparse.ArgumentParser(description='Backfill classification_factors in ES')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without writing')
    parser.add_argument('--only-missing', action='store_true',
                        help='Only update docs with missing/empty classification_factors')
    parser.add_argument('--index', type=str, default=None,
                        help='Specific index to update (default: both content and review)')
    parser.add_argument('--batch-size', type=int, default=100, help='Bulk update batch size')
    parser.add_argument('--limit', type=int, default=0, help='Max docs to process (0=all)')
    args = parser.parse_args()

    # Connect to ES
    es_host = os.getenv('ELASTICSEARCH_URL', 'http://elasticsearch:9200')
    es = Elasticsearch(es_host, request_timeout=30, max_retries=3)
    if not es.ping():
        logger.error(f"Cannot connect to Elasticsearch at {es_host}")
        sys.exit(1)
    logger.info(f"Connected to Elasticsearch at {es_host}")

    # Load model
    model, feature_extractor, feature_names = load_model_and_extractor()

    # Determine indices to process
    indices = []
    if args.index:
        indices = [args.index]
    else:
        for idx in ['ohdsi_content_v3', 'ohdsi_review_queue_v3']:
            if es.indices.exists(index=idx):
                indices.append(idx)
    logger.info(f"Processing indices: {indices}")

    # Build query
    if args.only_missing:
        query = {
            "bool": {
                "should": [
                    {"bool": {"must_not": {"exists": {"field": "classification_factors"}}}},
                    {"term": {"classification_factors": []}},
                ]
            }
        }
    else:
        query = {"match_all": {}}

    total_updated = 0
    total_skipped = 0
    total_errors = 0

    for index in indices:
        count = es.count(index=index, body={"query": query})['count']
        logger.info(f"\n{'='*60}")
        logger.info(f"Index: {index} — {count} docs to process")
        logger.info(f"{'='*60}")

        actions = []
        processed = 0

        for hit in scan(es, index=index, query={"query": query},
                        _source=True, size=500, scroll='5m'):
            doc_id = hit['_id']
            src = hit['_source']

            article = es_doc_to_article(src)
            factors = compute_instance_factors(model, feature_extractor, feature_names, article)

            if not factors:
                total_skipped += 1
                continue

            if args.dry_run:
                title = src.get('title', '?')[:60]
                ml_score = src.get('ml_score', 0)
                top_feat = factors[0]['feature'] if factors else '?'
                top_val = factors[0]['value'] if factors else 0
                logger.info(f"  [{doc_id}] ml={ml_score:.2f} | top: {top_feat}={top_val} | {title}")
                total_updated += 1
            else:
                actions.append({
                    '_op_type': 'update',
                    '_index': index,
                    '_id': doc_id,
                    'doc': {'classification_factors': factors}
                })

                if len(actions) >= args.batch_size:
                    success, errors = bulk(es, actions, raise_on_error=False, stats_only=True)
                    total_updated += success
                    total_errors += errors
                    if errors:
                        logger.warning(f"  Batch had {errors} errors")
                    actions = []

            processed += 1
            if processed % 500 == 0:
                logger.info(f"  Processed {processed}/{count}...")

            if args.limit and processed >= args.limit:
                logger.info(f"  Reached limit of {args.limit}")
                break

        # Flush remaining actions
        if actions and not args.dry_run:
            success, errors = bulk(es, actions, raise_on_error=False, stats_only=True)
            total_updated += success
            total_errors += errors

        logger.info(f"  {index}: {processed} processed")

    logger.info(f"\n{'='*60}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"  Updated:  {total_updated}")
    logger.info(f"  Skipped:  {total_skipped}")
    logger.info(f"  Errors:   {total_errors}")
    if args.dry_run:
        logger.info(f"  (DRY RUN — no changes written)")


if __name__ == '__main__':
    main()
