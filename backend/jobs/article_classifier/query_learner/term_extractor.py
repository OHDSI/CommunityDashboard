"""
Discriminative term extraction from a corpus of positive articles.

Extracts terms from multiple sources (TF-IDF, MeSH, keywords) and scores
them by discriminative power — how well they distinguish positives from
background/negatives.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

# MeSH terms that are too generic to be useful in any topic's queries
GENERIC_MESH = {
    'Humans', 'Female', 'Male', 'Adult', 'Aged', 'Middle Aged',
    'Young Adult', 'Adolescent', 'Child', 'Infant', 'Animals',
    'United States', 'Retrospective Studies', 'Prospective Studies',
    'Cross-Sectional Studies', 'Risk Factors', 'Treatment Outcome',
    'Time Factors', 'Prognosis', 'Prevalence', 'Incidence',
    'Follow-Up Studies', 'Aged, 80 and over', 'Child, Preschool',
    'Infant, Newborn',
}

# Universal scientific/English stop words that should never be brand terms.
# These appear in virtually all scientific papers regardless of field.
# NOTE: Domain terms like "database", "cohort", "observational" are NOT here
# because they CAN be useful as context terms in AND queries.
GENERIC_SCIENTIFIC_TERMS = {
    # General English
    'using', 'based', 'used', 'use', 'new', 'approach', 'including',
    'compared', 'different', 'significant', 'associated', 'available',
    'current', 'specific', 'general', 'potential', 'total',
    'high', 'low', 'large', 'small', 'developed', 'development',
    # Scientific boilerplate
    'study', 'studies', 'results', 'method', 'methods', 'analysis',
    'data', 'model', 'models', 'research', 'report', 'reports',
    'patients', 'patient', 'group', 'groups', 'review',
    'design', 'case', 'cases',
    # Common but not discriminative in any field
    'common', 'outcomes', 'outcome', 'effect', 'effects',
    'risk', 'treatment', 'time', 'information',
    'national', 'international', 'control',
}


@dataclass
class TermCandidate:
    """A candidate term for query construction."""
    term: str
    source: str           # 'tfidf', 'mesh', 'keyword', 'brand'
    coverage: float       # Fraction of positives containing this term
    specificity: float    # 1 - fraction of negatives containing it
    score: float          # Combined discriminative score
    is_phrase: bool       # Whether to quote in PubMed query
    pubmed_tag: str = ''  # Optional: [MeSH], [Author], etc.
    doc_count: int = 0    # Number of positive articles containing term


class TermExtractor:
    """
    Extract discriminative terms from a corpus of positive articles,
    optionally using negatives as background for contrast scoring.
    """

    def __init__(self, positives: List[Dict], negatives: Optional[List[Dict]] = None):
        self.positives = positives
        self.negatives = negatives or []
        self.n_pos = len(positives)
        self.n_neg = len(self.negatives)

        # Build searchable text for each article
        self._pos_texts = [self._build_text(a) for a in positives]
        self._neg_texts = [self._build_text(a) for a in self.negatives]

    @staticmethod
    def _build_text(article: Dict) -> str:
        """Build searchable text from article metadata."""
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
        return ' '.join(parts)

    def extract_all(self) -> Dict[str, List[TermCandidate]]:
        """
        Run all extraction strategies. Returns categorized candidates.
        """
        logger.info(f"Extracting terms from {self.n_pos} positives"
                     f"{f' with {self.n_neg} negatives for contrast' if self.n_neg else ''}")

        results = {
            'brand_terms': self._extract_brand_terms(),
            'phrases': self._extract_discriminative_phrases(),
            'mesh_terms': self._extract_mesh_terms(),
            'keywords': self._extract_keywords(),
        }

        for category, terms in results.items():
            logger.info(f"  {category}: {len(terms)} candidates")

        return results

    def _extract_brand_terms(self) -> List[TermCandidate]:
        """
        Find terms that appear in a very high fraction of positives.
        These are the identity terms (e.g., "OHDSI", "OMOP").
        """
        # Use unigram TF-IDF on positives only
        tfidf = TfidfVectorizer(
            ngram_range=(1, 1), max_features=1000,
            stop_words='english', min_df=0.10,  # Must appear in >=10% of positives
        )
        pos_matrix = tfidf.fit_transform(self._pos_texts)
        feature_names = tfidf.get_feature_names_out()

        # Coverage: fraction of positives where term has non-zero TF-IDF
        pos_nonzero = (pos_matrix > 0).toarray()
        pos_coverage = pos_nonzero.mean(axis=0)

        # Specificity against negatives
        if self._neg_texts:
            neg_matrix = tfidf.transform(self._neg_texts)
            neg_nonzero = (neg_matrix > 0).toarray()
            neg_coverage = neg_nonzero.mean(axis=0)
        else:
            # Estimate from IDF — higher IDF = rarer in general corpus = more specific
            idf = tfidf.idf_
            max_idf = idf.max()
            neg_coverage = 1.0 - (idf / max_idf)  # Rough estimate

        specificity = 1.0 - neg_coverage

        candidates = []
        for i, term in enumerate(feature_names):
            cov = float(pos_coverage[i])
            spec = float(specificity[i])

            # Skip common scientific terms — these are fragments of phrases
            # that would match millions of PubMed articles
            if term.lower() in GENERIC_SCIENTIFIC_TERMS:
                continue

            # Brand terms: high coverage (>20%) AND very high specificity (>95%)
            # The high specificity threshold ensures only true identity terms
            # pass (e.g., "OHDSI", "OMOP", not "model" or "common")
            if cov >= 0.20 and spec >= 0.95:
                score = cov * spec ** 2
                candidates.append(TermCandidate(
                    term=term, source='brand', coverage=cov,
                    specificity=spec, score=score,
                    is_phrase=False, doc_count=int(cov * self.n_pos),
                ))

        candidates.sort(key=lambda c: c.score, reverse=True)
        logger.info(f"  Brand terms found: {len(candidates)}"
                     f" (top: {[c.term for c in candidates[:5]]})")
        return candidates

    def _extract_discriminative_phrases(self) -> List[TermCandidate]:
        """
        Use TF-IDF (1-3 grams) to find discriminative phrases.
        If negatives are available, uses contrast scoring.
        """
        tfidf = TfidfVectorizer(
            ngram_range=(1, 3), max_features=5000,
            stop_words='english', min_df=max(3, int(0.01 * self.n_pos)),
        )
        pos_matrix = tfidf.fit_transform(self._pos_texts)
        feature_names = tfidf.get_feature_names_out()

        # Mean TF-IDF score across positives (how important is this term in the corpus)
        pos_means = np.asarray(pos_matrix.mean(axis=0)).flatten()

        # Coverage (document frequency in positives)
        pos_df = np.asarray((pos_matrix > 0).sum(axis=0)).flatten()
        pos_coverage = pos_df / self.n_pos

        if self._neg_texts:
            neg_matrix = tfidf.transform(self._neg_texts)
            neg_means = np.asarray(neg_matrix.mean(axis=0)).flatten()
            neg_df = np.asarray((neg_matrix > 0).sum(axis=0)).flatten()
            neg_coverage = neg_df / max(self.n_neg, 1)

            # Contrast score: positive importance minus negative importance
            contrast = pos_means - neg_means
            specificity = 1.0 - neg_coverage
        else:
            # No negatives — use IDF as weak proxy for specificity
            idf = tfidf.idf_
            max_idf = idf.max()
            contrast = pos_means  # Just use positive importance
            specificity = np.clip(idf / max_idf, 0, 1)

        candidates = []
        for i, term in enumerate(feature_names):
            cov = float(pos_coverage[i])
            spec = float(specificity[i])
            cont = float(contrast[i])

            if cov < 0.03:  # Skip very rare terms
                continue
            if cont <= 0 and self._neg_texts:  # Skip terms more common in negatives
                continue

            score = cov * spec ** 2
            is_phrase = ' ' in term
            candidates.append(TermCandidate(
                term=term, source='tfidf', coverage=cov,
                specificity=spec, score=score,
                is_phrase=is_phrase, doc_count=int(pos_df[i]),
            ))

        candidates.sort(key=lambda c: c.score, reverse=True)

        # Deduplicate: prefer longer phrases that subsume shorter ones
        candidates = self._deduplicate_phrases(candidates)

        return candidates[:200]  # Return top 200

    def _extract_mesh_terms(self) -> List[TermCandidate]:
        """Extract MeSH descriptors enriched in positives."""
        pos_mesh: Counter = Counter()
        neg_mesh: Counter = Counter()

        for a in self.positives:
            seen = set()
            for mesh in a.get('mesh_terms', []):
                name = mesh.get('descriptor_name', '') if isinstance(mesh, dict) else str(mesh)
                if name and name not in seen and name not in GENERIC_MESH:
                    pos_mesh[name] += 1
                    seen.add(name)

        for a in self.negatives:
            seen = set()
            for mesh in a.get('mesh_terms', []):
                name = mesh.get('descriptor_name', '') if isinstance(mesh, dict) else str(mesh)
                if name and name not in seen and name not in GENERIC_MESH:
                    neg_mesh[name] += 1
                    seen.add(name)

        candidates = []
        for term, count in pos_mesh.most_common():
            cov = count / self.n_pos
            if cov < 0.03:
                continue

            if self.n_neg > 0:
                neg_count = neg_mesh.get(term, 0)
                spec = 1.0 - (neg_count / self.n_neg)
            else:
                # Assume moderately specific if no negatives
                spec = max(0.3, 1.0 - cov * 0.5)

            score = cov * spec ** 2
            candidates.append(TermCandidate(
                term=term, source='mesh', coverage=cov,
                specificity=spec, score=score,
                is_phrase=' ' in term or ',' in term,
                pubmed_tag='[MeSH]', doc_count=count,
            ))

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:100]

    def _extract_keywords(self) -> List[TermCandidate]:
        """Extract author-assigned keywords enriched in positives."""
        pos_kw: Counter = Counter()
        neg_kw: Counter = Counter()

        for a in self.positives:
            seen = set()
            for kw in a.get('keywords', []):
                term = kw if isinstance(kw, str) else kw.get('term', '')
                term = term.strip().lower()
                if term and term not in seen:
                    pos_kw[term] += 1
                    seen.add(term)

        for a in self.negatives:
            seen = set()
            for kw in a.get('keywords', []):
                term = kw if isinstance(kw, str) else kw.get('term', '')
                term = term.strip().lower()
                if term and term not in seen:
                    neg_kw[term] += 1
                    seen.add(term)

        candidates = []
        for term, count in pos_kw.most_common():
            cov = count / self.n_pos
            if cov < 0.02:
                continue

            if self.n_neg > 0:
                neg_count = neg_kw.get(term, 0)
                spec = 1.0 - (neg_count / self.n_neg)
            else:
                spec = max(0.3, 1.0 - cov * 0.3)

            score = cov * spec ** 2
            candidates.append(TermCandidate(
                term=term, source='keyword', coverage=cov,
                specificity=spec, score=score,
                is_phrase=' ' in term, doc_count=count,
            ))

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:100]

    @staticmethod
    def _deduplicate_phrases(candidates: List[TermCandidate]) -> List[TermCandidate]:
        """
        Remove shorter phrases that are subsumed by higher-scoring longer phrases.
        E.g., if "electronic health records" scores higher than "electronic health",
        drop the shorter one.
        """
        kept = []
        kept_terms: Set[str] = set()

        for c in candidates:
            # Check if this term is subsumed by an already-kept longer term
            subsumed = False
            for existing in kept_terms:
                if c.term in existing and c.term != existing:
                    subsumed = True
                    break
            if not subsumed:
                kept.append(c)
                kept_terms.add(c.term)

        return kept
