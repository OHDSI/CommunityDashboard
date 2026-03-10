"""
Boolean query construction from extracted terms.

Combines discriminative terms into PubMed-compatible boolean queries
following proven patterns (brand OR, phrase AND context, MeSH queries).
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import numpy as np

from .term_extractor import TermCandidate

logger = logging.getLogger(__name__)

# Context terms that are too vague to be useful in AND clauses.
# These appear in virtually every scientific paper and would not restrict
# a PubMed query meaningfully. Domain terms like "database", "cohort",
# "observational" are intentionally NOT here — they make effective context.
CONTEXT_STOP_WORDS = {
    'using', 'based', 'used', 'use', 'new', 'approach', 'study',
    'studies', 'results', 'method', 'methods', 'analysis', 'data',
    'research', 'patients', 'patient', 'report', 'model', 'models',
    'compared', 'significant', 'associated', 'review', 'including',
    'available', 'design', 'group', 'groups', 'developed', 'total',
    'case', 'cases', 'specific', 'general', 'different',
}


@dataclass
class CandidateQuery:
    """A candidate PubMed search query with metadata."""
    name: str
    query_str: str
    strategy: str       # 'brand', 'phrase_context', 'mesh', 'combined'
    terms_used: List[str] = field(default_factory=list)
    estimated_coverage: float = 0.0


class QueryBuilder:
    """
    Combine extracted terms into PubMed-compatible boolean queries.

    Strategies mirror the patterns proven effective in the OHDSI query set:
    - Brand query: "TERM1 OR TERM2" (highest recall, most specific)
    - Phrase + context: "phrase" AND ("ctx1" OR "ctx2")
    - MeSH queries: "MeSH term"[MeSH] AND "context"
    - Combined: ("phrase1" OR "phrase2") AND ("ctx1" OR "ctx2")
    """

    def __init__(self, terms: Dict[str, List[TermCandidate]],
                 positive_texts: List[str]):
        """
        Args:
            terms: Categorized terms from TermExtractor.extract_all()
            positive_texts: Searchable text for each positive article
                (for computing co-occurrence statistics)
        """
        self.terms = terms
        self.positive_texts = [t.lower() for t in positive_texts]
        self.n_articles = len(positive_texts)

    def build_queries(self, max_queries: int = 30,
                      negatives: Optional[List[Dict]] = None) -> List[CandidateQuery]:
        """
        Generate candidate queries from all strategies.
        Returns more than needed — the optimizer will select the best subset.

        Args:
            max_queries: Maximum total candidates to return
            negatives: Optional negative articles for gap-recovery TF-IDF contrast
        """
        candidates = []

        # Strategy A: Brand query
        brand = self._build_brand_query()
        if brand:
            candidates.append(brand)

        # Strategy B: Phrase + context queries
        candidates.extend(self._build_phrase_context_queries())

        # Strategy C: MeSH-based queries
        candidates.extend(self._build_mesh_queries())

        # Strategy D: Combined broad queries
        candidates.extend(self._build_combined_queries())

        # Strategy E: Gap-recovery queries
        # These target the ~30% of articles that don't mention brand terms.
        # Uses broader domain terms paired with moderate context.
        candidates.extend(self._build_gap_recovery_queries(negatives))

        logger.info(f"Built {len(candidates)} candidate queries")
        return candidates[:max_queries * 2]  # Give optimizer plenty to choose from

    def _build_brand_query(self) -> Optional[CandidateQuery]:
        """Build a query from high-coverage brand terms (OR'd together)."""
        brand_terms = self.terms.get('brand_terms', [])
        if not brand_terms:
            return None

        # Take top brand terms (coverage > 30%, specificity > 80%)
        top = [t for t in brand_terms if t.coverage >= 0.10 and t.specificity >= 0.80]
        if not top:
            return None

        # Limit to top 5 to avoid overly broad queries
        top = top[:5]
        terms_str = [self._quote_if_phrase(t.term) for t in top]
        query = ' OR '.join(terms_str)

        # Estimate combined coverage
        coverage = self._estimate_or_coverage([t.term for t in top])

        return CandidateQuery(
            name='brand terms',
            query_str=query,
            strategy='brand',
            terms_used=[t.term for t in top],
            estimated_coverage=coverage,
        )

    def _build_phrase_context_queries(self) -> List[CandidateQuery]:
        """
        Build queries: "discriminative phrase" AND ("ctx1" OR "ctx2" OR "ctx3")
        """
        phrases = self.terms.get('phrases', [])
        candidates = []

        # Select primary phrases: coverage > 5%, specificity > 50%
        primary_phrases = [
            t for t in phrases
            if t.coverage >= 0.05 and t.specificity >= 0.50 and t.is_phrase
        ][:20]  # Top 20 phrase candidates

        # Also include high-coverage unigrams as potential primaries
        strong_unigrams = [
            t for t in phrases
            if t.coverage >= 0.10 and t.specificity >= 0.60 and not t.is_phrase
        ][:10]

        for primary in primary_phrases + strong_unigrams:
            context_terms = self._find_context_terms(primary.term)
            if not context_terms:
                continue

            ctx_str = ' OR '.join(f'"{c}"' for c in context_terms)
            primary_str = f'"{primary.term}"'
            query = f'{primary_str} AND ({ctx_str})'

            candidates.append(CandidateQuery(
                name=f'phrase: {primary.term}',
                query_str=query,
                strategy='phrase_context',
                terms_used=[primary.term] + context_terms,
                estimated_coverage=primary.coverage * 0.8,  # Rough estimate
            ))

        return candidates

    def _build_mesh_queries(self) -> List[CandidateQuery]:
        """Build MeSH-based queries with context qualifiers."""
        mesh_terms = self.terms.get('mesh_terms', [])
        candidates = []

        # Top MeSH terms with reasonable coverage
        top_mesh = [t for t in mesh_terms if t.coverage >= 0.05][:15]

        for mesh in top_mesh:
            # Find context terms that co-occur with this MeSH term
            context_terms = self._find_context_terms(mesh.term.lower())
            mesh_str = f'"{mesh.term}"[MeSH]'

            if context_terms:
                ctx_str = ' OR '.join(f'"{c}"' for c in context_terms)
                query = f'{mesh_str} AND ({ctx_str})'
            else:
                # MeSH alone (only if specificity is high)
                if mesh.specificity < 0.80:
                    continue
                query = mesh_str

            candidates.append(CandidateQuery(
                name=f'mesh: {mesh.term}',
                query_str=query,
                strategy='mesh',
                terms_used=[mesh.term] + (context_terms or []),
                estimated_coverage=mesh.coverage * 0.7,
            ))

        return candidates

    def _build_combined_queries(self) -> List[CandidateQuery]:
        """Build broader queries by OR-ing related phrases with shared context."""
        phrases = self.terms.get('phrases', [])
        candidates = []

        # Group related phrases by co-occurrence
        groups = self._find_phrase_groups(phrases)

        for group_name, group_terms in groups.items():
            if len(group_terms) < 2:
                continue

            # Find context terms shared across the group
            context = self._find_shared_context(group_terms)
            if not context:
                continue

            primary_str = ' OR '.join(f'"{t}"' for t in group_terms[:4])
            ctx_str = ' OR '.join(f'"{c}"' for c in context[:3])
            query = f'({primary_str}) AND ({ctx_str})'

            combined_cov = self._estimate_or_coverage(group_terms)

            candidates.append(CandidateQuery(
                name=f'combined: {group_name}',
                query_str=query,
                strategy='combined',
                terms_used=group_terms + context,
                estimated_coverage=combined_cov * 0.7,
            ))

        return candidates

    def _build_gap_recovery_queries(self, negatives: Optional[List[Dict]] = None) -> List[CandidateQuery]:
        """
        Build queries targeting articles that DON'T mention brand terms.

        These are the hardest to find — clinical studies by topic researchers
        that use general biomedical terminology. The strategy:
        1. Identify which positives are NOT caught by brand terms
        2. Run TF-IDF on these gap articles vs negatives to find their
           distinguishing phrases
        3. Build broader AND queries from these gap-specific phrases
        """
        from sklearn.feature_extraction.text import TfidfVectorizer

        # Find gap articles (not caught by brand terms)
        brand_terms = self.terms.get('brand_terms', [])
        brand_words = {t.term.lower() for t in brand_terms}

        gap_indices = []
        for i, text in enumerate(self.positive_texts):
            caught = any(word in text for word in brand_words)
            if not caught:
                gap_indices.append(i)

        if len(gap_indices) < 10:
            logger.info(f"  Gap recovery: only {len(gap_indices)} gap articles, skipping")
            return []

        logger.info(f"  Gap recovery: analyzing {len(gap_indices)} articles not caught by brand terms")

        gap_texts = [self.positive_texts[i] for i in gap_indices]

        # TF-IDF on gap articles
        tfidf = TfidfVectorizer(
            ngram_range=(1, 3), max_features=2000,
            stop_words='english', min_df=max(2, int(0.05 * len(gap_texts))),
        )
        gap_matrix = tfidf.fit_transform(gap_texts)
        feature_names = tfidf.get_feature_names_out()

        gap_df = np.asarray((gap_matrix > 0).sum(axis=0)).flatten()
        gap_coverage = gap_df / len(gap_texts)

        # If negatives available, compute contrast
        if negatives:
            neg_texts = [self._build_text_static(a) for a in negatives]
            neg_matrix = tfidf.transform(neg_texts)
            neg_df = np.asarray((neg_matrix > 0).sum(axis=0)).flatten()
            neg_coverage = neg_df / max(len(neg_texts), 1)
        else:
            idf = tfidf.idf_
            neg_coverage = 1.0 - np.clip(idf / idf.max(), 0, 1)

        specificity = 1.0 - neg_coverage

        # Score gap-specific terms
        gap_terms = []
        for i, term in enumerate(feature_names):
            cov = float(gap_coverage[i])
            spec = float(specificity[i])
            if cov < 0.08 or spec < 0.50:
                continue
            if term.lower() in CONTEXT_STOP_WORDS:
                continue
            gap_terms.append((term, cov, spec, cov * spec))

        gap_terms.sort(key=lambda x: x[3], reverse=True)

        # Build queries from top gap terms
        candidates = []
        used_primary = set()

        for primary_term, cov, spec, score in gap_terms[:30]:
            if primary_term in used_primary:
                continue

            # Find context terms from other gap terms
            context = []
            for ctx_term, ctx_cov, ctx_spec, _ in gap_terms:
                if ctx_term == primary_term:
                    continue
                if ctx_term in primary_term or primary_term in ctx_term:
                    continue
                if ctx_term.lower() in CONTEXT_STOP_WORDS:
                    continue
                # Check co-occurrence in gap articles
                co_count = sum(
                    1 for text in gap_texts
                    if primary_term.lower() in text and ctx_term.lower() in text
                )
                if co_count / len(gap_texts) >= 0.15:
                    context.append(ctx_term)
                if len(context) >= 3:
                    break

            if not context:
                continue

            primary_str = f'"{primary_term}"' if ' ' in primary_term else f'"{primary_term}"'
            ctx_str = ' OR '.join(f'"{c}"' for c in context)
            query = f'{primary_str} AND ({ctx_str})'

            candidates.append(CandidateQuery(
                name=f'gap: {primary_term}',
                query_str=query,
                strategy='gap_recovery',
                terms_used=[primary_term] + context,
                estimated_coverage=cov * 0.5 * (len(gap_indices) / self.n_articles),
            ))
            used_primary.add(primary_term)

            if len(candidates) >= 15:
                break

        logger.info(f"  Gap recovery: generated {len(candidates)} queries")
        return candidates

    @staticmethod
    def _build_text_static(article: Dict) -> str:
        """Build searchable text (static version for use without instance)."""
        parts = [
            article.get('title', '') or '',
            article.get('abstract', '') or '',
        ]
        for kw in article.get('keywords', []):
            if isinstance(kw, str):
                parts.append(kw)
            elif isinstance(kw, dict):
                parts.append(kw.get('term', ''))
        for mesh in article.get('mesh_terms', []):
            if isinstance(mesh, str):
                parts.append(mesh)
            elif isinstance(mesh, dict):
                parts.append(mesh.get('descriptor_name', ''))
        return ' '.join(parts).lower()

    def _find_context_terms(self, primary_term: str, n: int = 3) -> List[str]:
        """
        Find the best context terms that co-occur with the primary term.

        For articles containing `primary_term`, find other frequent terms
        that are broad enough to not over-restrict the AND query.
        """
        primary_lower = primary_term.lower()

        # Find articles containing the primary term
        containing_indices = [
            i for i, text in enumerate(self.positive_texts)
            if primary_lower in text
        ]
        if len(containing_indices) < 3:
            return []

        # All phrase candidates (from TF-IDF), excluding the primary itself
        all_terms = self.terms.get('phrases', []) + self.terms.get('keywords', [])

        scored_context = []
        for candidate in all_terms:
            cterm = candidate.term.lower()

            if cterm == primary_lower:
                continue
            if cterm in primary_lower or primary_lower in cterm:
                continue  # Skip overlapping terms

            # Skip context stop words — these match too broadly on PubMed
            # and make queries like "databases AND using" which are useless
            if cterm in CONTEXT_STOP_WORDS:
                continue

            # Also skip single-char or very short terms
            if len(cterm) <= 2:
                continue

            # Co-occurrence: how often does this term appear in articles
            # that also contain the primary term?
            co_count = sum(
                1 for i in containing_indices
                if cterm in self.positive_texts[i]
            )
            co_coverage = co_count / len(containing_indices)

            # Good context terms have high co-coverage AND are broadly useful
            if co_coverage < 0.30:
                continue

            # Weight by specificity — prefer context terms that are somewhat
            # discriminative, not just frequent in all scientific literature
            context_score = co_coverage * candidate.coverage * candidate.specificity
            scored_context.append((candidate.term, context_score))

        scored_context.sort(key=lambda x: x[1], reverse=True)

        # Return diverse context terms (not too similar to each other)
        selected = []
        for term, _ in scored_context:
            if len(selected) >= n:
                break
            # Check this isn't too similar to already-selected context
            overlap = any(
                term in s or s in term
                for s in selected
            )
            if not overlap:
                selected.append(term)

        return selected

    def _find_phrase_groups(self, phrases: List[TermCandidate]) -> Dict[str, List[str]]:
        """
        Group related phrases by topic similarity (simple word overlap).
        """
        groups: Dict[str, List[str]] = {}
        used: Set[str] = set()

        # Only consider phrases with reasonable coverage
        eligible = [p for p in phrases if p.coverage >= 0.05 and p.is_phrase][:30]

        for i, p1 in enumerate(eligible):
            if p1.term in used:
                continue

            words1 = set(p1.term.split())
            group = [p1.term]
            used.add(p1.term)

            for p2 in eligible[i+1:]:
                if p2.term in used:
                    continue
                words2 = set(p2.term.split())
                # Share at least one content word
                overlap = words1 & words2
                if overlap and any(len(w) > 3 for w in overlap):
                    group.append(p2.term)
                    used.add(p2.term)

            if len(group) >= 2:
                groups[p1.term.split()[0]] = group

        return groups

    def _find_shared_context(self, terms: List[str]) -> List[str]:
        """Find context terms that co-occur with ALL terms in the group."""
        # Articles containing any of the group terms
        combined_indices = set()
        for term in terms:
            term_lower = term.lower()
            for i, text in enumerate(self.positive_texts):
                if term_lower in text:
                    combined_indices.add(i)

        if len(combined_indices) < 5:
            return []

        # Find terms frequent across this combined set
        all_candidates = self.terms.get('phrases', [])
        scored = []

        for candidate in all_candidates:
            cterm = candidate.term.lower()
            if candidate.term in terms:
                continue
            if any(candidate.term in t or t in candidate.term for t in terms):
                continue
            if cterm in CONTEXT_STOP_WORDS:
                continue

            co_count = sum(
                1 for i in combined_indices
                if cterm in self.positive_texts[i]
            )
            co_coverage = co_count / len(combined_indices)
            if co_coverage >= 0.30:
                scored.append((candidate.term, co_coverage * candidate.specificity))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in scored[:3]]

    def _estimate_or_coverage(self, terms: List[str]) -> float:
        """Estimate the fraction of positives matched by OR-ing terms."""
        matched = set()
        for term in terms:
            term_lower = term.lower()
            for i, text in enumerate(self.positive_texts):
                if term_lower in text:
                    matched.add(i)
        return len(matched) / self.n_articles if self.n_articles else 0

    @staticmethod
    def _quote_if_phrase(term: str) -> str:
        """Add quotes around multi-word terms for PubMed."""
        if ' ' in term:
            return f'"{term}"'
        return term
