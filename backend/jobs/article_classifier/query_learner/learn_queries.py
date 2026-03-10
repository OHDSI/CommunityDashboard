"""
CLI entry point for learning PubMed queries from a set of positive articles.

Usage:
    python -m query_learner.learn_queries \
        --positives data/enriched/positive_enriched.json \
        --negatives data/enriched/negative_enriched.json \
        --topic ohdsi \
        --output-dir data/ \
        --target-recall 0.90 \
        --max-queries 15 \
        --min-author-articles 10

Output:
    data/{topic}_queries.json       -- Topic queries config (loadable by wrapper.py)
    data/{topic}_core_authors.json  -- Author monitoring config
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Allow running from the article_classifier directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from audit_retrieval import extract_top_authors, check_author_coverage
from query_learner.term_extractor import TermExtractor
from query_learner.query_builder import QueryBuilder
from query_learner.query_optimizer import QueryOptimizer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)


def load_articles(path: str) -> list:
    """Load articles from JSON file."""
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and 'articles' in data:
        return data['articles']
    else:
        raise ValueError(f"Unexpected format in {path}. Expected list or dict with 'articles' key.")


def main():
    parser = argparse.ArgumentParser(
        description='Learn PubMed queries from a set of known positive articles.'
    )
    parser.add_argument('--positives', required=True,
                        help='Path to positive articles JSON file')
    parser.add_argument('--negatives', default=None,
                        help='Path to negative articles JSON file (optional, improves specificity)')
    parser.add_argument('--topic', required=True,
                        help='Topic name (used in output filenames)')
    parser.add_argument('--output-dir', default='data/',
                        help='Output directory for config files')
    parser.add_argument('--target-recall', type=float, default=0.90,
                        help='Target recall for query optimization (default: 0.90)')
    parser.add_argument('--max-queries', type=int, default=15,
                        help='Maximum number of queries to select (default: 15)')
    parser.add_argument('--min-author-articles', type=int, default=10,
                        help='Minimum articles for author monitoring (default: 10)')

    args = parser.parse_args()
    start_time = time.time()

    # === 1. Load data ===
    print("=" * 80)
    print(f"QUERY LEARNER: {args.topic}")
    print("=" * 80)

    positives = load_articles(args.positives)
    print(f"\nLoaded {len(positives)} positive articles from {args.positives}")

    negatives = []
    if args.negatives:
        negatives = load_articles(args.negatives)
        print(f"Loaded {len(negatives)} negative articles from {args.negatives}")
    else:
        print("No negatives provided — using frequency-based scoring (less precise)")

    # === 2. Extract discriminative terms ===
    print(f"\n{'='*80}")
    print("PHASE 1: TERM EXTRACTION")
    print(f"{'='*80}")

    extractor = TermExtractor(positives, negatives if negatives else None)
    terms = extractor.extract_all()

    # Print top terms per category
    for category, candidates in terms.items():
        if candidates:
            print(f"\n  {category.upper()} (top 10):")
            for c in candidates[:10]:
                print(f"    {c.term:40s}  cov={c.coverage:.1%}  spec={c.specificity:.1%}  score={c.score:.4f}")

    # === 3. Build candidate queries ===
    print(f"\n{'='*80}")
    print("PHASE 2: QUERY CONSTRUCTION")
    print(f"{'='*80}")

    pos_texts = [extractor._build_text(a) for a in positives]
    builder = QueryBuilder(terms, pos_texts)
    candidates = builder.build_queries(
        max_queries=args.max_queries * 2,
        negatives=negatives if negatives else None,
    )

    print(f"\nGenerated {len(candidates)} candidate queries:")
    for i, q in enumerate(candidates[:20]):
        print(f"  [{q.strategy:15s}] {q.name}: {q.query_str[:80]}")

    # === 4. Optimize query selection ===
    print(f"\n{'='*80}")
    print("PHASE 3: QUERY OPTIMIZATION (greedy set cover)")
    print(f"{'='*80}")
    print(f"Target recall: {args.target_recall:.0%}, max queries: {args.max_queries}\n")

    optimizer = QueryOptimizer(positives, candidates)
    result = optimizer.optimize(
        target_recall=args.target_recall,
        max_queries=args.max_queries,
    )

    # Print recall progression
    print(f"\n{'Rank':<5} {'Matches':>8} {'New':>5} {'Cum.Recall':>11}  Query")
    print("-" * 80)
    for entry in result.recall_progression:
        print(f"  {entry['rank']:<3}  {entry['total_matches']:>6}   {entry['new_matches']:>4}   "
              f"{entry['cumulative_recall']:>9.1f}%  {entry['name'][:50]}")

    print(f"\nQuery recall: {result.total_recall:.1%} ({len(result.gap_articles)} articles remaining in gap)")

    # === 5. Extract core authors ===
    print(f"\n{'='*80}")
    print("PHASE 4: AUTHOR MONITORING")
    print(f"{'='*80}")

    top_authors = extract_top_authors(positives, min_articles=args.min_author_articles)
    print(f"\n{len(top_authors)} core authors (>= {args.min_author_articles} articles):")
    for a in top_authors[:15]:
        print(f"  {a['name']:25s}  {a['articles']} articles")
    if len(top_authors) > 15:
        print(f"  ... and {len(top_authors) - 15} more")

    # Check author coverage of gap articles
    if result.gap_articles:
        author_covered, _ = check_author_coverage(result.gap_articles, top_authors)
        total_with_authors = (
            int(result.total_recall * len(positives)) + author_covered
        )
        recall_with_authors = total_with_authors / len(positives)
        uncatchable = len(result.gap_articles) - author_covered
        print(f"\nAuthor monitoring recovers {author_covered}/{len(result.gap_articles)} gap articles")
        print(f"Projected recall with authors: {recall_with_authors:.1%}")
        print(f"Truly uncatchable: {uncatchable}")
    else:
        recall_with_authors = result.total_recall
        uncatchable = 0

    # === 6. Generate config files ===
    print(f"\n{'='*80}")
    print("PHASE 5: GENERATING CONFIG FILES")
    print(f"{'='*80}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Query config
    query_config = {
        'topic_name': args.topic,
        'generated': datetime.now().strftime('%Y-%m-%d'),
        'method': 'query_learner',
        'input_stats': {
            'n_positives': len(positives),
            'n_negatives': len(negatives),
        },
        'parameters': {
            'target_recall': args.target_recall,
            'max_queries': args.max_queries,
            'min_author_articles': args.min_author_articles,
        },
        'queries': [
            {
                'name': f"Q{entry['rank']:02d}: {entry['name']}",
                'query': entry['query'],
                'strategy': entry['strategy'],
                'matches': entry['total_matches'],
                'new_matches': entry['new_matches'],
                'cumulative_recall': entry['cumulative_recall'],
            }
            for entry in result.recall_progression
        ],
        'recall_metrics': {
            'queries_only': round(result.total_recall, 4),
            'with_authors': round(recall_with_authors, 4),
            'gap_count': len(result.gap_articles),
            'uncatchable_count': uncatchable,
        },
    }

    query_path = output_dir / f'{args.topic}_queries.json'
    with open(query_path, 'w') as f:
        json.dump(query_config, f, indent=2)
    print(f"\n  Queries config: {query_path}")

    # Author config (same format as ohdsi_core_authors.json)
    author_config = {
        'description': f'Core authors for {args.topic} PubMed monitoring. Generated by query_learner.',
        'generated': datetime.now().strftime('%Y-%m-%d'),
        'threshold': f'>={args.min_author_articles} articles in positive training set',
        'authors': [
            {'name': a['name'], 'articles': a['articles']}
            for a in top_authors
        ],
    }

    author_path = output_dir / f'{args.topic}_core_authors.json'
    with open(author_path, 'w') as f:
        json.dump(author_config, f, indent=2)
    print(f"  Authors config: {author_path}")

    # === 7. Summary ===
    elapsed = time.time() - start_time
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"\n  Topic: {args.topic}")
    print(f"  Positives: {len(positives)}, Negatives: {len(negatives)}")
    print(f"  Queries selected: {len(result.recall_progression)}")
    print(f"  Query recall: {result.total_recall:.1%}")
    print(f"  Authors for monitoring: {len(top_authors)}")
    print(f"  Recall with authors: {recall_with_authors:.1%}")
    print(f"  Uncatchable: {uncatchable}")
    print(f"  Time: {elapsed:.1f}s")
    print(f"\n  Output files:")
    print(f"    {query_path}")
    print(f"    {author_path}")

    # Gap article analysis
    if result.gap_analysis:
        print(f"\n  Gap analysis (articles not caught by any query or author):")
        for key, values in result.gap_analysis.items():
            if values:
                print(f"    {key}:")
                items = values[:5] if isinstance(values, list) else list(values.items())[:5]
                for item in items:
                    if isinstance(item, tuple):
                        print(f"      {item[0]}: {item[1]}")


if __name__ == '__main__':
    main()
