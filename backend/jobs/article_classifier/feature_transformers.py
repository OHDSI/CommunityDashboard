"""
sklearn-compatible feature transformer for OHDSI article classification.

Encapsulates all stateful feature derivation with proper fit/transform semantics
to prevent data leakage during cross-validation. Features derived from the positive
training set (topic authors, keywords, citation data) are computed only from
the training fold in fit(), then applied to any data in transform().

For production inference, fit() on ALL known data is legitimate.
For honest evaluation, fit() must be called per CV fold.
"""

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Set, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

CITATION_GRAPH_PATH = Path(__file__).parent / 'data' / 'enriched' / 'citation_graph.json'


class OHDSIFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    sklearn-compatible transformer that extracts all features for OHDSI article
    classification with proper train/test separation.

    fit(X_df, y): Learn topic_authors, topic_keywords, citation sets,
                  TF-IDF from training data only.
    transform(X_df): Compute all features using learned state.

    Feature groups:
        Intrinsic (stateless): abstract_length, num_authors, keyword_count,
            mesh_count, mentions_*, has_*, is_large_collaboration
        Network (stateful): topic_author_count, shared_keyword_count,
            cites_ohdsi_count, cited_by_ohdsi_count, ohdsi_citation_ratio,
            has_ohdsi_citation, tfidf_0..tfidf_N
    """

    # Fixed order of non-TF-IDF feature names
    NON_TFIDF_FEATURES = [
        # Intrinsic features (no state needed)
        'abstract_length', 'num_authors', 'keyword_count',
        'mesh_count', 'has_observational_mesh', 'has_database_mesh',
        'mentions_ohdsi', 'mentions_omop', 'mentions_cdm',
        'mentions_cohort', 'mentions_database', 'mentions_real_world',
        'mentions_network_study', 'has_statistics',
        'has_observational_keywords', 'has_database_keywords',
        'has_orcid', 'has_known_institution', 'is_large_collaboration',
        # Network features (require fit state)
        'topic_author_count', 'shared_keyword_count',
        'cites_ohdsi_count', 'cited_by_ohdsi_count',
        'ohdsi_citation_ratio', 'has_ohdsi_citation',
    ]

    def __init__(self, n_tfidf_features: int = 100,
                 citation_graph_path: Optional[str] = None,
                 min_author_articles: int = 2):
        self.n_tfidf_features = n_tfidf_features
        self.citation_graph_path = citation_graph_path
        self.min_author_articles = min_author_articles

    def fit(self, X, y=None):
        """
        Learn stateful features from training data.

        Args:
            X: DataFrame with columns: abstract, author/authors, keywords,
               mesh_terms, cites, ID/pmid, doi, citations (optional)
            y: array-like of labels (1=positive, 0=negative)
        """
        if y is None:
            raise ValueError("y is required to identify positive examples")

        y_arr = np.asarray(y)
        positive_indices = np.where(y_arr == 1)[0]

        # --- Topic authors (from positive examples only) ---
        # Count how many positive articles each author appears in,
        # then keep only those appearing in >= min_author_articles.
        # This eliminates one-hit-wonder name collisions (74% of authors
        # appear in only 1 article and are prone to matching unrelated researchers).
        author_col = self._get_author_col(X)
        author_article_count = Counter()
        if author_col:
            for val in X.iloc[positive_indices][author_col].fillna(''):
                article_authors = set()
                self._collect_author_names(val, article_authors)
                for name in article_authors:
                    author_article_count[name] += 1

        self.topic_authors_ = {
            name for name, count in author_article_count.items()
            if count >= self.min_author_articles
        }
        logger.info(f"Topic authors: {len(self.topic_authors_)} "
                     f"(filtered from {len(author_article_count)} total, "
                     f"threshold >= {self.min_author_articles} articles)")

        # --- Topic keywords (from positive examples only) ---
        self.topic_keywords_ = set()
        if 'keywords' in X.columns:
            for kws in X.iloc[positive_indices]['keywords'].fillna(''):
                if isinstance(kws, str):
                    for kw in kws.split(';'):
                        if kw.strip():
                            self.topic_keywords_.add(kw.strip().lower())
                elif isinstance(kws, list):
                    for kw in kws:
                        if isinstance(kw, str) and kw.strip():
                            self.topic_keywords_.add(kw.strip().lower())

        # --- Positive PMIDs (for citation features) ---
        self.positive_pmids_ = set()
        pos_df = X.iloc[positive_indices]
        if 'pmid' in pos_df.columns:
            self.positive_pmids_.update(
                pos_df['pmid'].dropna().astype(str).values
            )
        # Also extract from ID field (format: PMID12345678)
        if 'ID' in pos_df.columns:
            for val in pos_df['ID'].dropna().astype(str):
                pmid = val.replace('PMID', '')
                if pmid:
                    self.positive_pmids_.add(pmid)

        # --- Topic institutions (from positive examples, learned not hardcoded) ---
        self.topic_institutions_ = set()
        if 'authors' in X.columns:
            inst_counter = Counter()
            for authors in X.iloc[positive_indices]['authors']:
                if isinstance(authors, list):
                    for a in authors:
                        if isinstance(a, dict):
                            aff = str(a.get('affiliation', '')).lower()
                            if aff:
                                # Extract institution-level tokens
                                for token in ['columbia', 'janssen', 'iqvia', 'erasmus',
                                              'oxford', 'northeastern', 'ucla', 'duke',
                                              'stanford', 'michigan', 'korea', 'ajou',
                                              'inha', 'catholic']:
                                    if token in aff:
                                        inst_counter[token] += 1
            # Keep institutions appearing in >= 5 positive articles
            self.topic_institutions_ = {inst for inst, cnt in inst_counter.items() if cnt >= 5}
            logger.info(f"Learned {len(self.topic_institutions_)} topic institutions from data: {sorted(self.topic_institutions_)}")

        # --- Load citation graph (pre-computed by enrich_citations.py) ---
        self.citation_graph_ = self._load_citation_graph()

        # --- TF-IDF (fit on training abstracts only) ---
        self.tfidf_ = TfidfVectorizer(
            max_features=self.n_tfidf_features,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.tfidf_.fit(X['abstract'].fillna(''))

        logger.info(
            f"OHDSIFeatureExtractor fit: {len(self.topic_authors_)} authors, "
            f"{len(self.topic_keywords_)} keywords, "
            f"{len(self.positive_pmids_)} positive PMIDs, "
            f"{len(self.citation_graph_)} citation graph entries"
        )

        return self

    def transform(self, X):
        """
        Compute all features using learned state from fit().

        Args:
            X: DataFrame with the same columns as fit()

        Returns:
            numpy array of shape (n_samples, n_features)
        """
        n = len(X)
        features = {}

        # ===== INTRINSIC FEATURES (no state needed) =====

        features['abstract_length'] = X['abstract'].fillna('').str.len().values.astype(float)

        author_col = self._get_author_col(X)
        if author_col:
            features['num_authors'] = X[author_col].fillna('').apply(
                self._count_authors
            ).values.astype(float)
        else:
            features['num_authors'] = np.zeros(n)

        if 'keywords' in X.columns:
            features['keyword_count'] = X['keywords'].fillna('').apply(
                lambda x: len(x) if isinstance(x, list) else
                          (len([k for k in x.split(';') if k.strip()]) if isinstance(x, str) and x else 0)
            ).values.astype(float)
        else:
            features['keyword_count'] = np.zeros(n)

        # MeSH features
        if 'mesh_terms' in X.columns:
            mesh_data = X['mesh_terms'].apply(self._extract_mesh_features)
            features['mesh_count'] = mesh_data.apply(lambda x: x['count']).values.astype(float)
            features['has_observational_mesh'] = mesh_data.apply(lambda x: x['has_observational_mesh']).values.astype(float)
            features['has_database_mesh'] = mesh_data.apply(lambda x: x['has_database_mesh']).values.astype(float)
        else:
            features['mesh_count'] = np.zeros(n)
            features['has_observational_mesh'] = np.zeros(n)
            features['has_database_mesh'] = np.zeros(n)

        # Text pattern features (hardcoded regex - no leakage)
        abstract_lower = X['abstract'].fillna('').str.lower()
        features['mentions_ohdsi'] = abstract_lower.str.contains('ohdsi|observational health data', na=False).astype(int).values.astype(float)
        features['mentions_omop'] = abstract_lower.str.contains('omop|observational medical outcomes', na=False).astype(int).values.astype(float)
        features['mentions_cdm'] = abstract_lower.str.contains('common data model|cdm', na=False).astype(int).values.astype(float)
        features['mentions_cohort'] = abstract_lower.str.contains('cohort', na=False).astype(int).values.astype(float)
        features['mentions_database'] = abstract_lower.str.contains('database|data source', na=False).astype(int).values.astype(float)
        features['mentions_real_world'] = abstract_lower.str.contains('real.world|real world', na=False).astype(int).values.astype(float)
        features['mentions_network_study'] = abstract_lower.str.contains('network study|multi.?database|distributed', na=False).astype(int).values.astype(float)
        features['has_statistics'] = X['abstract'].fillna('').str.contains(
            r'p\s*[<=]\s*0\.\d+|95%|confidence interval', case=False, regex=True, na=False
        ).astype(int).values.astype(float)

        # Keyword category features
        if 'keywords' in X.columns:
            kw_str = X['keywords'].apply(
                lambda x: ';'.join(x) if isinstance(x, list) else str(x) if x else ''
            ).str.lower()
            features['has_observational_keywords'] = kw_str.str.contains(
                'observational|cohort|retrospective|prospective', na=False
            ).astype(int).values.astype(float)
            features['has_database_keywords'] = kw_str.str.contains(
                'database|claims|ehr|registry', na=False
            ).astype(int).values.astype(float)
        else:
            features['has_observational_keywords'] = np.zeros(n)
            features['has_database_keywords'] = np.zeros(n)

        # Author metadata features
        if 'authors' in X.columns:
            features['has_orcid'] = X['authors'].apply(
                lambda x: int(any(a.get('orcid') for a in x if isinstance(a, dict)))
                if isinstance(x, list) else 0
            ).values.astype(float)
            # Use institutions learned from training data in fit()
            learned_insts = getattr(self, 'topic_institutions_', set())
            features['has_known_institution'] = X['authors'].apply(
                lambda x: int(any(
                    any(inst in str(a.get('affiliation', '')).lower() for inst in learned_insts)
                    for a in x if isinstance(a, dict)
                )) if isinstance(x, list) and learned_insts else 0
            ).values.astype(float)
        else:
            features['has_orcid'] = np.zeros(n)
            features['has_known_institution'] = np.zeros(n)

        features['is_large_collaboration'] = (features['num_authors'] > 10).astype(float)

        # ===== NETWORK FEATURES (use learned state from fit) =====

        # Topic author count
        if author_col:
            features['topic_author_count'] = X[author_col].fillna('').apply(
                lambda x: self._count_topic_authors(x, self.topic_authors_)
            ).values.astype(float)
        else:
            features['topic_author_count'] = np.zeros(n)

        # Shared keyword count
        if 'keywords' in X.columns:
            features['shared_keyword_count'] = X['keywords'].fillna('').apply(
                lambda x: self._count_shared_keywords(x, self.topic_keywords_)
            ).values.astype(float)
        else:
            features['shared_keyword_count'] = np.zeros(n)

        # Citation features (using ELink data from citation_graph)
        citation_arrays = X.apply(
            lambda row: self._compute_citation_features(row), axis=1
        )
        features['cites_ohdsi_count'] = citation_arrays.apply(lambda x: x[0]).values.astype(float)
        features['cited_by_ohdsi_count'] = citation_arrays.apply(lambda x: x[1]).values.astype(float)
        features['ohdsi_citation_ratio'] = citation_arrays.apply(lambda x: x[2]).values.astype(float)
        features['has_ohdsi_citation'] = citation_arrays.apply(lambda x: x[3]).values.astype(float)

        # ===== TF-IDF FEATURES (using fitted vectorizer) =====
        tfidf_matrix = self.tfidf_.transform(X['abstract'].fillna('')).toarray()

        # Build result: non-tfidf features in fixed order, then tfidf
        result = np.column_stack(
            [features[name] for name in self.NON_TFIDF_FEATURES]
        )
        result = np.hstack([result, tfidf_matrix])

        return result

    def get_feature_names_out(self):
        """Return ordered list of all feature names."""
        names = list(self.NON_TFIDF_FEATURES)
        if hasattr(self, 'tfidf_'):
            n_tfidf = len(self.tfidf_.get_feature_names_out())
        else:
            n_tfidf = self.n_tfidf_features
        names.extend([f'tfidf_{i}' for i in range(n_tfidf)])
        return names

    # ─── Citation feature computation ─────────────────────────────────────

    def _load_citation_graph(self) -> Dict:
        """Load pre-computed citation graph from enrich_citations.py output."""
        path = Path(self.citation_graph_path) if self.citation_graph_path else CITATION_GRAPH_PATH
        if path.exists():
            with open(path) as f:
                return json.load(f)
        logger.warning(f"Citation graph not found at {path}. "
                       "Citation features will be zeros. "
                       "Run enrich_citations.py to generate it.")
        return {}

    def _get_article_pmid(self, row) -> str:
        """Extract PMID from a DataFrame row."""
        pmid = row.get('pmid', '')
        if pmid:
            return str(pmid)
        art_id = row.get('ID', '')
        if art_id:
            return str(art_id).replace('PMID', '')
        return ''

    def _compute_citation_features(self, row) -> tuple:
        """Compute citation features for a single article.

        Returns:
            (cites_ohdsi_count, cited_by_ohdsi_count, ohdsi_citation_ratio,
             has_ohdsi_citation)
        """
        pmid = self._get_article_pmid(row)

        # Try to get citation data from the pre-computed graph
        citation_data = self.citation_graph_.get(pmid, {})
        references = set(str(r) for r in citation_data.get('references', []))
        cited_by = set(str(c) for c in citation_data.get('cited_by', []))

        # Also check for inline citations field (runtime articles from ELink)
        if not references and not cited_by:
            inline_citations = row.get('citations', {})
            if isinstance(inline_citations, dict):
                references = set(str(r) for r in inline_citations.get('references', []))
                cited_by = set(str(c) for c in inline_citations.get('cited_by', []))

        # Count overlap with positive training PMIDs
        cites_ohdsi = len(references & self.positive_pmids_)
        cited_by_ohdsi = len(cited_by & self.positive_pmids_)

        total = len(references) + len(cited_by)
        ratio = (cites_ohdsi + cited_by_ohdsi) / max(total, 1)
        has_citation = float(cites_ohdsi + cited_by_ohdsi > 0)

        return (float(cites_ohdsi), float(cited_by_ohdsi), ratio, has_citation)

    # ─── Helper methods ────────────────────────────────────────────────────

    @staticmethod
    def _get_author_col(df):
        """Return the author column name present in the DataFrame."""
        if 'authors' in df.columns:
            return 'authors'
        elif 'author' in df.columns:
            return 'author'
        return None

    @staticmethod
    def _collect_author_names(val, target_set):
        """Extract author names from various formats into a set."""
        if isinstance(val, str):
            for a in val.split(';'):
                if a.strip():
                    target_set.add(a.strip())
        elif isinstance(val, list):
            for a in val:
                if isinstance(a, dict):
                    name = a.get('name', '').strip()
                    if name:
                        target_set.add(name)
                elif isinstance(a, str) and a.strip():
                    target_set.add(a.strip())

    @staticmethod
    def _count_authors(val):
        """Count authors from various formats."""
        if isinstance(val, str) and val:
            return len([a for a in val.split(';') if a.strip()])
        elif isinstance(val, list):
            return len(val)
        return 0

    @staticmethod
    def _count_topic_authors(authors_data, topic_authors):
        """Count how many authors are known OHDSI contributors."""
        if isinstance(authors_data, str):
            authors = [a.strip() for a in authors_data.split(';') if a.strip()]
        elif isinstance(authors_data, list):
            if authors_data and isinstance(authors_data[0], dict):
                authors = [a.get('name', '').strip() for a in authors_data if a.get('name')]
            else:
                authors = [str(a).strip() for a in authors_data]
        else:
            return 0
        return sum(1 for a in authors if a in topic_authors)

    @staticmethod
    def _count_shared_keywords(keywords_data, topic_keywords):
        """Count keyword overlap with OHDSI topic keywords."""
        if not keywords_data:
            return 0
        if isinstance(keywords_data, list):
            keywords = set(k.lower() for k in keywords_data if k)
        else:
            keywords = set(
                k.strip().lower() for k in str(keywords_data).split(';') if k.strip()
            )
        return len(keywords & topic_keywords)

    @staticmethod
    def _extract_mesh_features(mesh_terms):
        """Extract MeSH term count and category indicators."""
        if not mesh_terms:
            return {'count': 0, 'has_observational_mesh': 0, 'has_database_mesh': 0}

        count = len(mesh_terms) if isinstance(mesh_terms, list) else 0
        has_database_mesh = 0
        has_observational_mesh = 0

        if isinstance(mesh_terms, list):
            for term in mesh_terms:
                if isinstance(term, dict):
                    descriptor = term.get('descriptor_name', '').lower()
                elif isinstance(term, str):
                    descriptor = term.lower()
                else:
                    continue

                if any(kw in descriptor for kw in ['database', 'registr', 'data collection']):
                    has_database_mesh = 1
                if any(kw in descriptor for kw in ['observational', 'cohort', 'retrospective', 'prospective']):
                    has_observational_mesh = 1

        return {
            'count': count,
            'has_observational_mesh': has_observational_mesh,
            'has_database_mesh': has_database_mesh,
        }
