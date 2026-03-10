"""
Greedy set-cover optimization for maximum query recall.

Selects the minimum set of PubMed queries that covers the target fraction
of known positive articles.
"""

import logging
import sys
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple

from .query_builder import CandidateQuery

logger = logging.getLogger(__name__)

# Import query parser from audit_retrieval (same directory level)
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))
from audit_retrieval import parse_query, build_searchable_text, analyze_gaps


@dataclass
class OptimizationResult:
    """Result of query set optimization."""
    selected_queries: List[CandidateQuery]
    total_recall: float
    recall_progression: List[Dict]
    gap_articles: List[Dict]
    gap_analysis: Dict


class QueryOptimizer:
    """
    Select an optimal subset of candidate queries that maximizes
    recall using a greedy set-cover approach.
    """

    def __init__(self, articles: List[Dict], candidates: List[CandidateQuery]):
        """
        Args:
            articles: The positive articles to evaluate against
            candidates: Candidate queries from QueryBuilder
        """
        self.articles = articles
        self.candidates = candidates
        self.n_articles = len(articles)

        # Precompute searchable text for each article
        self._texts = [build_searchable_text(a) for a in articles]

        # Precompute which articles each candidate matches
        self._match_sets: Dict[int, Set[int]] = {}
        logger.info(f"Evaluating {len(candidates)} candidate queries against {self.n_articles} articles...")
        for i, q in enumerate(candidates):
            self._match_sets[i] = self._evaluate_query(q.query_str)

    def optimize(self, target_recall: float = 0.90,
                 max_queries: int = 15) -> OptimizationResult:
        """
        Greedy set-cover to select queries maximizing recall.

        Algorithm:
        1. Pick the query that covers the most uncovered articles
        2. Add to selected set, update uncovered
        3. Stop when target_recall reached or max_queries hit
        """
        selected: List[Tuple[int, CandidateQuery]] = []
        covered: Set[int] = set()
        progression: List[Dict] = []

        for round_num in range(max_queries):
            # Find the candidate with the highest marginal gain
            best_idx = -1
            best_gain = 0
            best_new: Set[int] = set()

            for i, q in enumerate(self.candidates):
                if any(s[0] == i for s in selected):
                    continue  # Already selected
                new_matches = self._match_sets.get(i, set()) - covered
                if len(new_matches) > best_gain:
                    best_gain = len(new_matches)
                    best_idx = i
                    best_new = new_matches

            if best_gain == 0:
                logger.info("No candidate adds new coverage. Stopping.")
                break

            best_query = self.candidates[best_idx]
            covered |= best_new
            selected.append((best_idx, best_query))

            cumulative_recall = len(covered) / self.n_articles
            total_matches = len(self._match_sets.get(best_idx, set()))

            progression.append({
                'rank': round_num + 1,
                'name': best_query.name,
                'query': best_query.query_str,
                'strategy': best_query.strategy,
                'total_matches': total_matches,
                'new_matches': best_gain,
                'cumulative_covered': len(covered),
                'cumulative_recall': round(cumulative_recall * 100, 1),
            })

            logger.info(f"  Q{round_num+1}: +{best_gain} articles "
                         f"(total {total_matches}) → recall {cumulative_recall:.1%} "
                         f"[{best_query.name}]")

            if cumulative_recall >= target_recall:
                logger.info(f"Target recall {target_recall:.0%} reached with {round_num+1} queries.")
                break

        # Identify gap articles
        gap_indices = set(range(self.n_articles)) - covered
        gap_articles = [self.articles[i] for i in sorted(gap_indices)]
        gap_info = analyze_gaps(gap_articles) if gap_articles else {}

        total_recall = len(covered) / self.n_articles if self.n_articles else 0

        return OptimizationResult(
            selected_queries=[q for _, q in selected],
            total_recall=total_recall,
            recall_progression=progression,
            gap_articles=gap_articles,
            gap_analysis=gap_info,
        )

    def _evaluate_query(self, query_str: str) -> Set[int]:
        """Evaluate a query against all articles. Returns matching indices."""
        try:
            matcher = parse_query(query_str)
        except Exception as e:
            logger.warning(f"Failed to parse query '{query_str[:60]}': {e}")
            return set()

        matched = set()
        for i, text in enumerate(self._texts):
            if matcher(text):
                matched.add(i)
        return matched

    def compute_recall_with_authors(self, optimization_result: OptimizationResult,
                                     top_authors: List[Dict]) -> float:
        """
        Compute projected recall if author monitoring is added on top of
        the optimized query set.
        """
        # Start with articles covered by queries
        query_covered = set()
        for i, q in enumerate(self.candidates):
            if q in optimization_result.selected_queries:
                query_covered |= self._match_sets.get(
                    self.candidates.index(q), set()
                )

        # Check gap articles for author coverage
        author_keys = {a['key'] for a in top_authors if 'key' in a}
        gap_indices = set(range(self.n_articles)) - query_covered

        author_recovered = 0
        for idx in gap_indices:
            article = self.articles[idx]
            for auth in article.get('authors', []):
                last = auth.get('last_name', '')
                initials = auth.get('initials', '')
                if not last:
                    name = auth.get('name', '')
                    if ', ' in name:
                        last = name.split(', ')[0]
                        first = name.split(', ')[1]
                        initials = auth.get('initials', first[0] if first else '')
                if last:
                    first_initial = initials[0] if initials else ''
                    key = f"{last.lower()} {first_initial.lower()}"
                    if key in author_keys:
                        author_recovered += 1
                        break

        total_covered = len(query_covered) + author_recovered
        return total_covered / self.n_articles if self.n_articles else 0
