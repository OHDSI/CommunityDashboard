#!/usr/bin/env python3
"""
End-to-end pipeline evaluation using known positive/negative articles.

Fetches articles fresh from PubMed by PMID, runs through the full
ArticleClassifierWrapper pipeline (citation enrichment, ML classification,
GPT scoring, tiered routing), and reports evaluation metrics.

Usage:
    docker compose exec backend python /app/scripts/evaluate_pipeline.py \
        --positives /app/jobs/article_classifier/data/enriched/positive_enriched.json \
        --negatives /app/jobs/article_classifier/data/enriched/negative_enriched.json \
        --batch-size 50 \
        --wipe-first
"""

import argparse
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Add paths for imports
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/jobs/article_classifier')
sys.path.insert(0, '/app/jobs')

os.environ.setdefault('CELERY_WORKER_RUNNING', '1')

from elasticsearch import Elasticsearch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_pmids(filepath: str) -> list[str]:
    """Extract PMIDs from an enriched JSON file."""
    with open(filepath) as f:
        articles = json.load(f)
    pmids = [str(a['pmid']) for a in articles if a.get('pmid')]
    logger.info(f"Loaded {len(pmids)} PMIDs from {Path(filepath).name}")
    return pmids


def wipe_indices(es: Elasticsearch, content_index: str, review_index: str):
    """Delete all documents from content and review indices."""
    for index_name in [content_index, review_index]:
        try:
            count = es.count(index=index_name)['count']
            if count > 0:
                es.delete_by_query(
                    index=index_name,
                    body={"query": {"match_all": {}}},
                    refresh=True,
                    wait_for_completion=True
                )
                logger.info(f"Wiped {count} documents from {index_name}")
            else:
                logger.info(f"{index_name} already empty")
        except Exception as e:
            logger.warning(f"Could not wipe {index_name}: {e}")


def query_index_pmids(es: Elasticsearch, index_name: str) -> dict[str, dict]:
    """Query all PMIDs and their scores from an ES index."""
    results = {}
    try:
        # Use scroll for large result sets
        resp = es.search(
            index=index_name,
            body={
                "query": {"match_all": {}},
                "_source": ["pmid", "ml_score", "ai_confidence", "final_score",
                            "quality_score", "status", "priority_level"],
                "size": 10000
            }
        )
        for hit in resp['hits']['hits']:
            src = hit['_source']
            pmid = src.get('pmid')
            if pmid:
                results[str(pmid)] = src
    except Exception as e:
        logger.error(f"Error querying {index_name}: {e}")
    return results


def compute_metrics(
    positive_pmids: set[str],
    negative_pmids: set[str],
    content_results: dict[str, dict],
    review_results: dict[str, dict]
) -> dict:
    """Compute evaluation metrics from routing results."""
    metrics = {
        'true_positives': [],       # Positives auto-approved
        'false_positives': [],      # Negatives auto-approved
        'true_negatives_rejected': [],  # Negatives auto-rejected
        'true_negatives_review': [],    # Negatives sent to review
        'false_negatives_rejected': [], # Positives auto-rejected
        'false_negatives_review': [],   # Positives sent to review (not necessarily wrong)
        'positives_in_review': [],      # Positives in review queue (any status)
        'missing_positives': [],    # Positives not found in either index
        'missing_negatives': [],    # Negatives not found in either index
    }

    # Check where each positive landed
    for pmid in positive_pmids:
        if pmid in content_results:
            metrics['true_positives'].append({
                'pmid': pmid,
                **content_results[pmid]
            })
        elif pmid in review_results:
            info = review_results[pmid]
            status = info.get('status', 'unknown')
            entry = {'pmid': pmid, **info}
            metrics['positives_in_review'].append(entry)
            if status == 'rejected':
                metrics['false_negatives_rejected'].append(entry)
            else:
                metrics['false_negatives_review'].append(entry)
        else:
            metrics['missing_positives'].append(pmid)

    # Check where each negative landed
    for pmid in negative_pmids:
        if pmid in content_results:
            metrics['false_positives'].append({
                'pmid': pmid,
                **content_results[pmid]
            })
        elif pmid in review_results:
            info = review_results[pmid]
            status = info.get('status', 'unknown')
            entry = {'pmid': pmid, **info}
            if status == 'rejected':
                metrics['true_negatives_rejected'].append(entry)
            else:
                metrics['true_negatives_review'].append(entry)
        else:
            metrics['missing_negatives'].append(pmid)

    return metrics


def print_report(
    metrics: dict,
    positive_count: int,
    negative_count: int,
    elapsed: float,
    content_total: int,
    review_total: int
):
    """Print evaluation report."""
    tp = len(metrics['true_positives'])
    fp = len(metrics['false_positives'])
    tn_rejected = len(metrics['true_negatives_rejected'])
    tn_review = len(metrics['true_negatives_review'])
    fn_rejected = len(metrics['false_negatives_rejected'])
    fn_review = len(metrics['false_negatives_review'])
    missing_pos = len(metrics['missing_positives'])
    missing_neg = len(metrics['missing_negatives'])

    total_processed = tp + fp + tn_rejected + tn_review + fn_rejected + fn_review

    print("\n" + "=" * 70)
    print("END-TO-END PIPELINE EVALUATION")
    print("=" * 70)
    print(f"\nDataset: {positive_count} positives, {negative_count} negatives")
    print(f"Time: {elapsed:.0f}s ({elapsed/max(total_processed,1):.1f}s per article)")
    print(f"\nIndex counts: content={content_total}, review={review_total}")

    print(f"\n--- ROUTING SUMMARY ---")
    print(f"  Auto-approved (content index):  {tp + fp}")
    print(f"    Known positives (TP):         {tp}")
    print(f"    Known negatives (FP):         {fp}")
    print(f"  Review queue:                   {tn_review + fn_review}")
    print(f"    Known positives:              {fn_review}")
    print(f"    Known negatives:              {tn_review}")
    print(f"  Auto-rejected:                  {tn_rejected + fn_rejected}")
    print(f"    Known negatives (TN):         {tn_rejected}")
    print(f"    Known positives (FN):         {fn_rejected}")
    print(f"  Missing (fetch failed):         {missing_pos + missing_neg}")
    print(f"    Positives:                    {missing_pos}")
    print(f"    Negatives:                    {missing_neg}")

    # Precision/Recall for auto-approve decision
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    # Recall = positives auto-approved / all positives that were fetched
    fetched_positives = positive_count - missing_pos
    recall = tp / fetched_positives if fetched_positives > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # False positive rate = FP / all negatives fetched
    fetched_negatives = negative_count - missing_neg
    fp_rate = fp / fetched_negatives if fetched_negatives > 0 else 0

    # False negative rate (auto-rejected positives)
    fn_rate = fn_rejected / fetched_positives if fetched_positives > 0 else 0

    print(f"\n--- CLASSIFICATION METRICS (auto-approve decision) ---")
    print(f"  Precision:           {precision:.4f} ({tp}/{tp+fp})")
    print(f"  Recall:              {recall:.4f} ({tp}/{fetched_positives})")
    print(f"  F1:                  {f1:.4f}")
    print(f"  False positive rate: {fp_rate:.4f} ({fp}/{fetched_negatives})")
    print(f"  False negative rate: {fn_rate:.4f} ({fn_rejected}/{fetched_positives})")

    # Show false positives
    if metrics['false_positives']:
        print(f"\n--- FALSE POSITIVES (negatives auto-approved) ---")
        for item in metrics['false_positives']:
            print(f"  PMID {item['pmid']} (ml={item.get('ml_score',0):.3f}, "
                  f"ai={item.get('ai_confidence',0):.3f}, "
                  f"final={item.get('final_score',0):.3f})")

    # Show false negatives (auto-rejected positives)
    if metrics['false_negatives_rejected']:
        print(f"\n--- FALSE NEGATIVES (positives auto-rejected) ---")
        for item in metrics['false_negatives_rejected']:
            print(f"  PMID {item['pmid']} (ml={item.get('ml_score',0):.3f}, "
                  f"ai={item.get('ai_confidence',0):.3f}, "
                  f"final={item.get('final_score',0):.3f})")

    # Show positives in review (not auto-approved but not rejected either)
    if metrics['false_negatives_review']:
        print(f"\n--- POSITIVES IN REVIEW (need human review, not auto-approved) ---")
        for item in sorted(metrics['false_negatives_review'],
                          key=lambda x: x.get('final_score', 0)):
            print(f"  PMID {item['pmid']} (ml={item.get('ml_score',0):.3f}, "
                  f"final={item.get('final_score',0):.3f}, "
                  f"priority={item.get('priority_level','?')})")

    # Score distribution summary
    all_scores = []
    for item in metrics['true_positives']:
        all_scores.append(('pos', 'approved', item.get('ml_score', 0), item.get('final_score', 0)))
    for item in metrics['false_positives']:
        all_scores.append(('neg', 'approved', item.get('ml_score', 0), item.get('final_score', 0)))
    for item in metrics['true_negatives_rejected']:
        all_scores.append(('neg', 'rejected', item.get('ml_score', 0), item.get('final_score', 0)))
    for item in metrics['false_negatives_rejected']:
        all_scores.append(('pos', 'rejected', item.get('ml_score', 0), item.get('final_score', 0)))

    if all_scores:
        pos_scores = [s[3] for s in all_scores if s[0] == 'pos']
        neg_scores = [s[3] for s in all_scores if s[0] == 'neg']
        if pos_scores:
            print(f"\n--- SCORE DISTRIBUTIONS (final_score) ---")
            print(f"  Positives: min={min(pos_scores):.3f}, "
                  f"median={sorted(pos_scores)[len(pos_scores)//2]:.3f}, "
                  f"max={max(pos_scores):.3f}, n={len(pos_scores)}")
        if neg_scores:
            print(f"  Negatives: min={min(neg_scores):.3f}, "
                  f"median={sorted(neg_scores)[len(neg_scores)//2]:.3f}, "
                  f"max={max(neg_scores):.3f}, n={len(neg_scores)}")

    print("\n" + "=" * 70)

    return {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'fp_rate': fp_rate,
        'fn_rate': fn_rate,
        'tp': tp, 'fp': fp,
        'tn_rejected': tn_rejected, 'tn_review': tn_review,
        'fn_rejected': fn_rejected, 'fn_review': fn_review,
        'missing_pos': missing_pos, 'missing_neg': missing_neg,
    }


def main():
    parser = argparse.ArgumentParser(
        description="End-to-end pipeline evaluation with known positive/negative articles"
    )
    parser.add_argument('--positives', required=True,
                        help='Path to positive_enriched.json')
    parser.add_argument('--negatives', required=True,
                        help='Path to negative_enriched.json')
    parser.add_argument('--batch-size', type=int, default=50,
                        help='PubMed fetch batch size (default: 50)')
    parser.add_argument('--wipe-first', action='store_true',
                        help='Wipe content and review indices before evaluation')
    parser.add_argument('--output', default='/app/jobs/article_classifier/data/enriched/evaluation_results.json',
                        help='Path to save detailed results JSON')
    parser.add_argument('--positives-only', action='store_true',
                        help='Only process positive articles')
    parser.add_argument('--negatives-only', action='store_true',
                        help='Only process negative articles')

    args = parser.parse_args()

    # Load PMIDs
    positive_pmids = load_pmids(args.positives)
    negative_pmids = load_pmids(args.negatives)

    if args.positives_only:
        negative_pmids = []
    elif args.negatives_only:
        positive_pmids = []

    all_pmids = positive_pmids + negative_pmids
    positive_set = set(positive_pmids)
    negative_set = set(negative_pmids)

    print(f"\nLoaded {len(positive_pmids)} positive + {len(negative_pmids)} negative = {len(all_pmids)} total PMIDs")

    # Init ES
    es = Elasticsearch("http://elasticsearch:9200", timeout=30, max_retries=3)
    if not es.ping():
        logger.error("Cannot connect to Elasticsearch")
        sys.exit(1)

    # Init wrapper (this loads the ML model)
    from article_classifier.wrapper import ArticleClassifierWrapper
    wrapper = ArticleClassifierWrapper(es_client=es)

    print(f"Classifier loaded. Thresholds: approve={wrapper.auto_approve_threshold:.2f}, "
          f"priority={wrapper.priority_threshold:.3f}, reject={wrapper.reject_threshold:.2f}")
    print(f"GPT scoring: {'ENABLED' if os.getenv('USE_GPT_SCORING', 'false').lower() == 'true' else 'DISABLED'}")

    # Wipe if requested
    if args.wipe_first:
        print("\nWiping existing indices...")
        wipe_indices(es, wrapper.content_index, wrapper.review_index)

    # Count before
    before_content = es.count(index=wrapper.content_index)['count']
    before_review = es.count(index=wrapper.review_index)['count']
    print(f"\nBefore: content={before_content}, review={before_review}")

    # Process in batches
    start_time = time.time()
    batch_size = args.batch_size
    total_fetched = 0
    total_classified = 0
    fetch_failures = []

    for i in range(0, len(all_pmids), batch_size):
        batch_pmids = all_pmids[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(all_pmids) + batch_size - 1) // batch_size

        # Count pos/neg in this batch
        batch_pos = sum(1 for p in batch_pmids if p in positive_set)
        batch_neg = len(batch_pmids) - batch_pos

        print(f"\n--- Batch {batch_num}/{total_batches}: {len(batch_pmids)} PMIDs "
              f"({batch_pos} pos, {batch_neg} neg) ---")

        # Fetch fresh from PubMed
        try:
            articles = wrapper.retriever.fetch_article_details(batch_pmids)
            total_fetched += len(articles)

            if len(articles) < len(batch_pmids):
                fetched_set = {str(a.get('pmid', '')) for a in articles}
                missing = [p for p in batch_pmids if p not in fetched_set]
                fetch_failures.extend(missing)
                logger.warning(f"  Failed to fetch {len(missing)} PMIDs: {missing[:5]}...")

            if articles:
                print(f"  Fetched {len(articles)} articles, classifying...")
                result = wrapper._enrich_classify_and_route(articles)
                classified = result.get('classified', len(articles))
                total_classified += classified
                print(f"  Result: {json.dumps(result)}")
            else:
                print("  No articles fetched for this batch")
        except Exception as e:
            logger.error(f"  Batch {batch_num} failed: {e}")
            fetch_failures.extend(batch_pmids)

    elapsed = time.time() - start_time

    # Let ES refresh
    es.indices.refresh(index=wrapper.content_index)
    es.indices.refresh(index=wrapper.review_index)

    # Count after
    after_content = es.count(index=wrapper.content_index)['count']
    after_review = es.count(index=wrapper.review_index)['count']

    print(f"\nAfter: content={after_content} (+{after_content - before_content}), "
          f"review={after_review} (+{after_review - before_review})")
    print(f"Fetched: {total_fetched}/{len(all_pmids)}, Fetch failures: {len(fetch_failures)}")

    # Query both indices to see where articles landed
    print("\nQuerying indices for evaluation...")
    content_results = query_index_pmids(es, wrapper.content_index)
    review_results = query_index_pmids(es, wrapper.review_index)

    # Compute metrics
    metrics = compute_metrics(positive_set, negative_set, content_results, review_results)

    # Print report
    summary = print_report(
        metrics, len(positive_pmids), len(negative_pmids),
        elapsed, after_content, after_review
    )

    # Save detailed results
    output_data = {
        'timestamp': datetime.now().isoformat(),
        'config': {
            'auto_approve_threshold': wrapper.auto_approve_threshold,
            'priority_threshold': wrapper.priority_threshold,
            'reject_threshold': wrapper.reject_threshold,
            'gpt_scoring': os.getenv('USE_GPT_SCORING', 'false'),
            'batch_size': batch_size,
        },
        'dataset': {
            'positives': len(positive_pmids),
            'negatives': len(negative_pmids),
            'total': len(all_pmids),
        },
        'summary': summary,
        'fetch_failures': fetch_failures,
        'false_positives': metrics['false_positives'],
        'false_negatives_rejected': metrics['false_negatives_rejected'],
        'positives_in_review': metrics['positives_in_review'],
        'missing_positives': metrics['missing_positives'],
        'missing_negatives': metrics['missing_negatives'],
    }

    try:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        print(f"\nDetailed results saved to {args.output}")
    except Exception as e:
        logger.error(f"Could not save results: {e}")


if __name__ == '__main__':
    main()
