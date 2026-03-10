"""
Enhanced ArticleClassifier V2 with improved features and regularization to prevent overfitting.
This version replaces memorization features with generalizable patterns.
"""

import logging
import pickle
import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, roc_auc_score, f1_score
from sklearn.isotonic import IsotonicRegression
from sklearn.pipeline import Pipeline

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logging.warning("XGBoost not available. Using RandomForest as fallback.")

import openai
from openai import OpenAI

# Import sklearn-compatible feature transformer — single source of truth for all features
try:
    from jobs.article_classifier.feature_transformers import OHDSIFeatureExtractor
except ImportError:
    try:
        from feature_transformers import OHDSIFeatureExtractor
    except ImportError:
        OHDSIFeatureExtractor = None
        logging.warning("OHDSIFeatureExtractor not available — training/inference will fail")

from Bio import Entrez, Medline
from bibtexparser import load as bib_load, dumps
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Entrez
Entrez.email = os.getenv("NCBI_ENTREZ_EMAIL", "ohdsi@example.com")

# Import comprehensive category system
try:
    import sys
    sys.path.append('/app')
    from config.ohdsi_categories import get_all_categories, suggest_categories as suggest_cats
    OHDSI_CATEGORIES = get_all_categories()
    logger.info(f"Loaded {len(OHDSI_CATEGORIES)} categories from ohdsi_categories module")
except ImportError as e:
    logger.warning(f"Could not import category system: {e}. Using defaults.")
    OHDSI_CATEGORIES = [
        "Observational data standards and management",
        "Methodological research",
        "Open-source analytics development",
        "Clinical applications",
    ]


class EnhancedOHDSIClassifierV2:
    """
    Enhanced article classifier V2 with improved features and regularization.
    Focuses on generalizable patterns rather than memorization.
    """
    
    def __init__(self, data_dir: str = None, model_dir: str = None, model_type: str = "randomforest"):
        """
        Initialize the enhanced classifier V2.
        
        Args:
            data_dir: Directory containing training BibTeX files
            model_dir: Directory to save/load trained models
            model_type: "xgboost" or "randomforest"
        """
        self.data_dir = Path(data_dir) if data_dir else Path("/app/jobs/article_classifier/data")
        self.model_dir = Path(model_dir) if model_dir else Path("/app/jobs/article_classifier/models")
        
        # Default to RandomForest to match original predictor.ipynb
        self.model_type = model_type if XGBOOST_AVAILABLE else "randomforest"
        if model_type == "xgboost" and not XGBOOST_AVAILABLE:
            logger.warning("XGBoost requested but not available. Using RandomForest.")
        
        # Ensure directories exist
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Model paths - use v2 suffix to distinguish
        self.model_path = self.model_dir / f"{self.model_type}_model_v2.pkl"
        self.vectorizer_path = self.model_dir / "tfidf_v2.pkl"
        self.metadata_path = self.model_dir / "metadata_v2.pkl"
        
        # Training data paths
        self.positive_bib = self.data_dir / "enriched_articles_ohdsi_reformatted.bib"
        self.negative_bib = self.data_dir / "No_OHDSI_Citations.bib"
        
        # Initialize components
        self.model = None
        self.feature_extractor = None  # OHDSIFeatureExtractor — single source of truth
        self.topic_authors = set()  # Preserved for GPT prompt context
        self.topic_keywords = set()  # Preserved for category matching
        self.feature_names = []
        
        # Define keyword categories for domain-specific features
        self.methodology_terms = {
            'cohort', 'observational', 'retrospective', 'prospective',
            'longitudinal', 'cross-sectional', 'case-control', 'randomized',
            'systematic review', 'meta-analysis', 'validation'
        }
        
        self.database_terms = {
            'database', 'claims', 'ehr', 'registry', 'administrative',
            'electronic health records', 'health records', 'data source',
            'real-world data', 'clinical data', 'patient data'
        }
        
        self.analysis_terms = {
            'comparative', 'effectiveness', 'safety', 'risk', 'prediction',
            'association', 'outcome', 'exposure', 'incidence', 'prevalence',
            'hazard', 'survival', 'propensity'
        }
        
        # Initialize OpenAI client if API key is available
        self.openai_client = None
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = OpenAI(api_key=api_key)
            logger.info("OpenAI GPT-4o-mini integration enabled")
        else:
            logger.warning("No OpenAI API key found. GPT classification disabled.")
    
    def compute_author_features(self, df: pd.DataFrame, topic_authors: Set[str]) -> pd.DataFrame:
        """
        DEPRECATED: Kept for backward compatibility with legacy model pickles.
        New models use OHDSIFeatureExtractor.transform() which computes identical features.
        """
        df = df.copy()
        
        # PRIMARY FEATURE: Topic author count (matching original)
        def count_topic_authors(authors_data):
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
            
            return sum(1 for author in authors if author in topic_authors)
        
        # Use 'authors' if available, otherwise 'author'
        author_col = 'authors' if 'authors' in df.columns else 'author'
        df['topic_author_count'] = df[author_col].fillna('').apply(count_topic_authors)
        
        # Simple author count feature
        def get_author_count(authors):
            if isinstance(authors, str):
                return len(authors.split(';')) if authors else 0
            elif isinstance(authors, list):
                return len(authors)
            return 0
        
        df['num_authors'] = df[author_col].fillna('').apply(get_author_count)
        
        # Keep minimal ORCID feature
        if 'authors' in df.columns:
            df['has_orcid'] = df['authors'].apply(
                lambda x: int(any(a.get('orcid') for a in x if isinstance(a, dict))) if isinstance(x, list) else 0
            )
        else:
            df['has_orcid'] = 0
        
        # Simplified institution check - only major OHDSI institutions
        if 'authors' in df.columns:
            ohdsi_institutions = ['columbia', 'janssen', 'iqvia', 'erasmus']
            df['has_known_institution'] = df['authors'].apply(
                lambda x: int(any(
                    any(inst in str(a.get('affiliation', '')).lower() for inst in ohdsi_institutions)
                    for a in x if isinstance(a, dict)
                )) if isinstance(x, list) else 0
            )
        else:
            df['has_known_institution'] = 0
        
        # Remove complex institution diversity - not in original
        
        # Simplified collaboration features
        df['is_large_collaboration'] = (df['num_authors'] > 10).astype(int)
        
        # Remove ORCID ratio - not in original
        
        # Remove geographic diversity - not in original
        
        # Remove network patterns - not in original
        
        # Remove name diversity - not in original
        
        return df
    
    def compute_keyword_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        DEPRECATED: Kept for backward compatibility with legacy model pickles.
        New models use OHDSIFeatureExtractor.transform() which computes identical features.
        """
        df = df.copy()
        
        # PRIMARY FEATURE: Shared keyword count (matching original)
        def count_shared_keywords(keywords_data):
            """Count overlap with OHDSI topic keywords."""
            if not keywords_data:
                return 0
            if isinstance(keywords_data, list):
                keywords = set(k.lower() for k in keywords_data if k)
            else:
                keywords = set(k.strip().lower() for k in str(keywords_data).split(';') if k.strip())
            
            return len(keywords & self.topic_keywords)
        
        df['shared_keyword_count'] = df['keywords'].fillna('').apply(count_shared_keywords)
        
        # Keep minimal category checks for basic signals
        # Convert keywords to string first if it's a list
        df['keywords_str'] = df['keywords'].apply(
            lambda x: ';'.join(x) if isinstance(x, list) else str(x) if x else ''
        )
        df['has_observational_keywords'] = df['keywords_str'].str.lower().str.contains(
            'observational|cohort|retrospective|prospective', na=False
        ).astype(int)
        df['has_database_keywords'] = df['keywords_str'].str.lower().str.contains(
            'database|claims|ehr|registry', na=False
        ).astype(int)
        
        # Simple keyword count
        df['keyword_count'] = df['keywords'].fillna('').apply(
            lambda x: len(x) if isinstance(x, list) else len(x.split(';')) if x else 0
        )
        
        # Simplified MeSH term features - just count and basic categories
        if 'mesh_terms' in df.columns:
            def extract_mesh_features(mesh_terms):
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
                    'has_database_mesh': has_database_mesh
                }
            
            mesh_features = df['mesh_terms'].apply(extract_mesh_features)
            df['mesh_count'] = mesh_features.apply(lambda x: x['count'])
            df['has_observational_mesh'] = mesh_features.apply(lambda x: x['has_observational_mesh'])
            df['has_database_mesh'] = mesh_features.apply(lambda x: x['has_database_mesh'])
        else:
            df['mesh_count'] = 0
            df['has_observational_mesh'] = 0
            df['has_database_mesh'] = 0
        
        # Remove funding features - not in original
        
        return df
    
    def compute_text_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        DEPRECATED: Kept for backward compatibility only.
        Use OHDSIFeatureExtractor (feature_transformers.py) instead.

        Compute simplified text features focusing on key OHDSI indicators.
        """
        df = df.copy()
        
        # Basic text length feature
        df['abstract_length'] = df['abstract'].fillna('').str.len()
        
        # Core OHDSI-related mentions only
        abstract_lower = df['abstract'].fillna('').str.lower()
        df['mentions_cohort'] = abstract_lower.str.contains('cohort').astype(int)
        df['mentions_database'] = abstract_lower.str.contains('database|data source').astype(int)
        df['mentions_real_world'] = abstract_lower.str.contains('real.world|real world').astype(int)
        
        # Essential OHDSI-specific indicators only
        df['mentions_ohdsi'] = abstract_lower.str.contains('ohdsi|observational health data').astype(int)
        df['mentions_omop'] = abstract_lower.str.contains('omop|observational medical outcomes').astype(int)
        df['mentions_cdm'] = abstract_lower.str.contains('common data model|cdm').astype(int)
        df['mentions_network_study'] = abstract_lower.str.contains('network study|multi.?database|distributed').astype(int)
        
        # Remove title-specific features - not in original
        
        # Basic statistical content indicator
        df['has_statistics'] = df['abstract'].fillna('').str.contains(
            r'p\s*[<=]\s*0\.\d+|95%|confidence interval',
            case=False, regex=True
        ).astype(int)
        
        # Remove journal features - not in original
        
        # Remove publication type features - not in original
        
        # Remove PMC and funding features - not in original
        
        return df
    
    def train(self, force_retrain: bool = False, include_feedback: bool = True) -> Dict:
        """
        Train the enhanced classifier V2 using OHDSIFeatureExtractor as the
        single source of truth for feature engineering.
        """
        if not force_retrain and self.model_path.exists():
            logger.info("Loading existing V2 model...")
            self.load_model()
            return {"status": "loaded", "message": "Model V2 loaded from disk"}

        if OHDSIFeatureExtractor is None:
            raise ImportError("OHDSIFeatureExtractor required for training but not available")

        logger.info(f"Training {self.model_type} classifier V2...")

        # Load training data from enriched JSON (canonical source)
        enriched_dir = Path(self.data_dir) / 'enriched'
        positive_path = enriched_dir / 'positive_enriched.json'
        negative_path = enriched_dir / 'negative_enriched.json'

        with open(positive_path) as f:
            positives = json.load(f)
        with open(negative_path) as f:
            negatives = json.load(f)

        for a in positives:
            a['label'] = 1
        for a in negatives:
            a['label'] = 0

        all_data = pd.DataFrame(positives + negatives)
        logger.info(f"Loaded {len(positives)} positive and {len(negatives)} negative articles")

        # Optionally merge reviewer feedback data
        if include_feedback:
            feedback_path = enriched_dir / 'feedback_articles.json'
            if feedback_path.exists():
                with open(feedback_path) as f:
                    feedback = json.load(f)
                feedback_df = pd.DataFrame(feedback)
                existing_pmids = set(all_data['pmid'].dropna().astype(str))
                new_feedback = feedback_df[~feedback_df['pmid'].astype(str).isin(existing_pmids)]
                if len(new_feedback) > 0:
                    all_data = pd.concat([all_data, new_feedback], ignore_index=True)
                    logger.info(f"Added {len(new_feedback)} feedback articles to training data")

        y = all_data['label'].values

        # Use OHDSIFeatureExtractor as single source of truth for all features
        citation_graph_path = enriched_dir / 'citation_graph.json'
        self.feature_extractor = OHDSIFeatureExtractor(
            n_tfidf_features=100,
            citation_graph_path=str(citation_graph_path) if citation_graph_path.exists() else None
        )
        self.feature_extractor.fit(all_data, y)
        X = self.feature_extractor.transform(all_data)
        self.feature_names = list(self.feature_extractor.get_feature_names_out())

        # Preserve for GPT prompt context and compatibility
        self.topic_authors = self.feature_extractor.topic_authors_
        self.topic_keywords = self.feature_extractor.topic_keywords_
        
        # Split: 80% train, 20% test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Build and train model on full training set
        if self.model_type == "xgboost" and XGBOOST_AVAILABLE:
            self.model = xgb.XGBClassifier(
                n_estimators=100, max_depth=3, learning_rate=0.1,
                reg_alpha=1.0, reg_lambda=2.0, min_child_weight=10,
                gamma=0.1, subsample=0.7, colsample_bytree=0.5,
                objective='binary:logistic', random_state=42,
                use_label_encoder=False, eval_metric='logloss'
            )
        else:
            self.model = RandomForestClassifier(random_state=42)
        self.model.fit(X_train, y_train)

        # Calibrate probabilities using cross-validated OOF predictions.
        # Previous approach fitted the calibrator on a model trained on 90%
        # of training data, then refitted the model on 100% — the calibrator
        # mapped from the wrong probability space. OOF predictions from 5-fold
        # CV approximate the full model's behavior on unseen data, making the
        # calibration mapping correct for production use.
        from sklearn.model_selection import cross_val_predict
        oof_proba = cross_val_predict(
            self.model, X_train, y_train,
            cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
            method='predict_proba'
        )[:, 1]
        self.calibrator = IsotonicRegression(out_of_bounds='clip')
        self.calibrator.fit(oof_proba, y_train)
        logger.info(f"Probability calibrator fitted on {len(y_train)} OOF predictions (5-fold CV)")

        # Evaluate on test set
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]

        report = classification_report(y_test, y_pred, output_dict=True)
        auc_score = roc_auc_score(y_test, y_pred_proba)

        # Cross-validation on pre-computed features (NOTE: these scores have
        # feature leakage since features were derived from all data before split.
        # Use evaluate() for decontaminated metrics.)
        cv_scores = cross_val_score(self.model, X, y, cv=5, scoring='f1')
        
        # Save model
        self.save_model()
        
        # Log performance
        logger.info(f"Model V2 trained with accuracy: {report['accuracy']:.3f}, AUC: {auc_score:.3f}")
        logger.info(f"Cross-validation F1 scores: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
        
        # Analyze score distribution to check for overfitting
        train_proba = self.model.predict_proba(X_train)[:, 1]
        test_proba = y_pred_proba
        
        logger.info(f"Training set score distribution:")
        logger.info(f"  < 0.1: {np.sum(train_proba < 0.1)}/{len(train_proba)}")
        logger.info(f"  0.1-0.9: {np.sum((train_proba >= 0.1) & (train_proba <= 0.9))}/{len(train_proba)}")
        logger.info(f"  > 0.9: {np.sum(train_proba > 0.9)}/{len(train_proba)}")
        
        logger.info(f"Test set score distribution:")
        logger.info(f"  < 0.1: {np.sum(test_proba < 0.1)}/{len(test_proba)}")
        logger.info(f"  0.1-0.9: {np.sum((test_proba >= 0.1) & (test_proba <= 0.9))}/{len(test_proba)}")
        logger.info(f"  > 0.9: {np.sum(test_proba > 0.9)}/{len(test_proba)}")
        
        return {
            "status": "trained",
            "model_type": self.model_type,
            "accuracy": report['accuracy'],
            "precision": report['1']['precision'],
            "recall": report['1']['recall'],
            "f1": report['1']['f1-score'],
            "auc": auc_score,
            "cv_f1_mean": cv_scores.mean(),
            "cv_f1_std": cv_scores.std(),
            "support": len(all_data),
            "features": len(self.feature_names)
        }
    
    def build_pipeline(self, model_type: str = None) -> Pipeline:
        """
        Build an sklearn Pipeline with decontaminated feature extraction.
        Features are derived per-fold during cross-validation.

        Args:
            model_type: "xgboost" or "randomforest" (defaults to self.model_type)

        Returns:
            sklearn Pipeline with OHDSIFeatureExtractor + classifier
        """
        if OHDSIFeatureExtractor is None:
            raise ImportError("OHDSIFeatureExtractor not available")

        model_type = model_type or self.model_type

        if model_type == "xgboost" and XGBOOST_AVAILABLE:
            clf = xgb.XGBClassifier(
                n_estimators=100, max_depth=3, learning_rate=0.1,
                reg_alpha=1.0, reg_lambda=2.0, min_child_weight=10,
                gamma=0.1, subsample=0.7, colsample_bytree=0.5,
                objective='binary:logistic', random_state=42,
                use_label_encoder=False, eval_metric='logloss'
            )
        else:
            clf = RandomForestClassifier(random_state=42)

        citation_graph_path = Path(self.data_dir) / 'enriched' / 'citation_graph.json'
        return Pipeline([
            ('features', OHDSIFeatureExtractor(
                n_tfidf_features=100,
                citation_graph_path=str(citation_graph_path) if citation_graph_path.exists() else None
            )),
            ('classifier', clf),
        ])

    def evaluate(self, n_folds: int = 5, model_type: str = None) -> Dict:
        """
        Run decontaminated cross-validation where features are derived per-fold.
        This gives honest performance metrics without data leakage.

        Args:
            n_folds: Number of CV folds
            model_type: "xgboost" or "randomforest"

        Returns:
            Dictionary with honest metrics and per-fold details
        """
        if OHDSIFeatureExtractor is None:
            raise ImportError("OHDSIFeatureExtractor not available")

        # Load from enriched JSON — same canonical source as train()
        enriched_dir = Path(self.data_dir) / 'enriched'
        with open(enriched_dir / 'positive_enriched.json') as f:
            positives = json.load(f)
        with open(enriched_dir / 'negative_enriched.json') as f:
            negatives = json.load(f)
        for a in positives:
            a['label'] = 1
        for a in negatives:
            a['label'] = 0
        all_data = pd.DataFrame(positives + negatives)
        y = all_data['label'].values

        logger.info(f"Running {n_folds}-fold decontaminated CV on {len(all_data)} articles...")

        skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
        oof_proba = np.zeros(len(all_data))
        oof_pred = np.zeros(len(all_data))
        fold_metrics = []

        for fold_idx, (train_idx, test_idx) in enumerate(skf.split(all_data, y)):
            train_df = all_data.iloc[train_idx]
            test_df = all_data.iloc[test_idx]
            y_train = y[train_idx]
            y_test = y[test_idx]

            pipeline = self.build_pipeline(model_type=model_type)
            pipeline.fit(train_df, y_train)

            proba = pipeline.predict_proba(test_df)[:, 1]
            pred = (proba >= 0.5).astype(int)

            oof_proba[test_idx] = proba
            oof_pred[test_idx] = pred

            fold_f1 = f1_score(y_test, pred)
            fold_auc = roc_auc_score(y_test, proba)
            fold_metrics.append({'fold': fold_idx + 1, 'f1': fold_f1, 'auc': fold_auc})
            logger.info(f"  Fold {fold_idx + 1}: F1={fold_f1:.4f}, AUC={fold_auc:.4f}")

        # Overall metrics
        overall_f1 = f1_score(y, oof_pred)
        overall_auc = roc_auc_score(y, oof_proba)
        report = classification_report(y, oof_pred, output_dict=True)

        logger.info(f"Decontaminated CV: F1={overall_f1:.4f}, AUC={overall_auc:.4f}")

        return {
            'f1': overall_f1,
            'auc': overall_auc,
            'precision': report['1']['precision'],
            'recall': report['1']['recall'],
            'accuracy': report['accuracy'],
            'fold_metrics': fold_metrics,
            'oof_proba': oof_proba,
            'oof_pred': oof_pred,
            'y_true': y,
        }

    def _load_citation_graph(self) -> Dict:
        """Load pre-computed citation graph from enrich_citations.py output."""
        path = Path(self.data_dir) / 'enriched' / 'citation_graph.json'
        if path.exists():
            with open(path) as f:
                return json.load(f)
        logging.warning(f"Citation graph not found at {path}. Citation features will be zeros.")
        return {}

    def _compute_citation_features(self, df: pd.DataFrame, related_df: pd.DataFrame) -> pd.DataFrame:
        """Compute citation features using ELink data (replaces broken graph features)."""
        citation_graph = self._load_citation_graph()

        # Build set of positive PMIDs (stored on self for save_model)
        positive_pmids = set()
        if 'pmid' in related_df.columns:
            positive_pmids.update(related_df['pmid'].dropna().astype(str).values)
        if 'ID' in related_df.columns:
            for val in related_df['ID'].dropna().astype(str):
                positive_pmids.add(val.replace('PMID', ''))
        self._positive_pmids = positive_pmids

        df = df.copy()

        def _get_pmid(row):
            pmid = row.get('pmid', '')
            if pmid:
                return str(pmid)
            art_id = row.get('ID', '')
            if art_id:
                return str(art_id).replace('PMID', '')
            return ''

        def _citation_features(row):
            pmid = _get_pmid(row)
            data = citation_graph.get(pmid, {})
            references = set(str(r) for r in data.get('references', []))
            cited_by = set(str(c) for c in data.get('cited_by', []))

            cites_ohdsi = len(references & positive_pmids)
            cited_by_ohdsi = len(cited_by & positive_pmids)
            total = len(references) + len(cited_by)
            ratio = (cites_ohdsi + cited_by_ohdsi) / max(total, 1)
            has_citation = int(cites_ohdsi + cited_by_ohdsi > 0)

            return pd.Series({
                'cites_ohdsi_count': cites_ohdsi,
                'cited_by_ohdsi_count': cited_by_ohdsi,
                'ohdsi_citation_ratio': ratio,
                'has_ohdsi_citation': has_citation,
            })

        citation_df = df.apply(_citation_features, axis=1)
        for col in citation_df.columns:
            df[col] = citation_df[col]

        return df

    def _legacy_feature_extraction(self, article: Dict, df: pd.DataFrame) -> np.ndarray:
        """
        Legacy feature extraction for models saved before OHDSIFeatureExtractor unification.
        Uses the old manual feature computation methods + separate TF-IDF vectorizer.
        """
        df = self.compute_author_features(df, self.topic_authors)
        df = self.compute_keyword_features(df)
        df = self.compute_text_pattern_features(df)

        # TF-IDF features via legacy vectorizer
        abstracts = df['abstract'].fillna('')
        if hasattr(self, 'vectorizer') and self.vectorizer:
            tfidf_features = self.vectorizer.transform(abstracts).toarray()
            tfidf_df = pd.DataFrame(
                tfidf_features,
                columns=[f'tfidf_{i}' for i in range(tfidf_features.shape[1])]
            )
            df = pd.concat([df.reset_index(drop=True), tfidf_df], axis=1)

        # Citation features from ELink data (if available on article)
        citations = article.get('citations', {})
        positive_pmids = getattr(self, 'positive_pmids', set())
        refs = set(str(r) for r in citations.get('references', []))
        cited = set(str(c) for c in citations.get('cited_by', []))
        cites_ohdsi = len(refs & positive_pmids) if positive_pmids else 0
        cited_by_ohdsi = len(cited & positive_pmids) if positive_pmids else 0
        total_cit = len(refs) + len(cited)
        df['cites_ohdsi_count'] = cites_ohdsi
        df['cited_by_ohdsi_count'] = cited_by_ohdsi
        df['ohdsi_citation_ratio'] = (cites_ohdsi + cited_by_ohdsi) / max(total_cit, 1)
        df['has_ohdsi_citation'] = int(cites_ohdsi + cited_by_ohdsi > 0)

        return df[self.feature_names].fillna(0)

    def calibrate_probability(self, raw_prob: float) -> float:
        """
        Apply isotonic regression calibration to raw model probability.
        Falls back to identity if no calibrator is available.
        """
        if hasattr(self, 'calibrator') and self.calibrator is not None:
            return float(np.clip(self.calibrator.predict([raw_prob])[0], 0.0, 1.0))
        return raw_prob
    
    def save_model(self):
        """Save trained model and metadata to disk."""
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)

        # Build positive PMIDs from the feature extractor
        positive_pmids = set()
        if self.feature_extractor and hasattr(self.feature_extractor, 'positive_pmids_'):
            positive_pmids = self.feature_extractor.positive_pmids_

        # Load calibrated thresholds if available
        calibrated_thresholds = None
        thresholds_path = Path(self.data_dir) / 'enriched' / 'calibrated_thresholds.json'
        if thresholds_path.exists():
            with open(thresholds_path) as f:
                cal_data = json.load(f)
            calibrated_thresholds = cal_data.get('calibrated_thresholds')

        metadata = {
            'model_type': self.model_type,
            'feature_extractor': self.feature_extractor,  # single source of truth
            'topic_authors': self.topic_authors,
            'feature_names': self.feature_names,
            'topic_keywords': self.topic_keywords,
            'positive_pmids': positive_pmids,
            'calibrated_thresholds': calibrated_thresholds,
            'calibrator': getattr(self, 'calibrator', None),
        }
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(metadata, f)

        logger.info(f"Enhanced V2 {self.model_type} model saved to {self.model_dir}")
    
    def load_model(self):
        """Load trained model and metadata from disk."""
        if not self.model_path.exists():
            raise FileNotFoundError(f"No trained V2 model found at {self.model_path}")

        with open(self.model_path, 'rb') as f:
            self.model = pickle.load(f)

        if self.metadata_path.exists():
            with open(self.metadata_path, 'rb') as f:
                metadata = pickle.load(f)
                self.model_type = metadata.get('model_type', 'unknown')
                self.topic_authors = metadata.get('topic_authors', set())
                self.feature_names = metadata.get('feature_names', [])
                self.topic_keywords = metadata.get('topic_keywords', set())
                self.positive_pmids = metadata.get('positive_pmids', set())
                self.metadata_ = metadata

                # Restore the fitted feature extractor (new unified path)
                self.feature_extractor = metadata.get('feature_extractor', None)
                if self.feature_extractor:
                    self.topic_authors = self.feature_extractor.topic_authors_
                    self.topic_keywords = self.feature_extractor.topic_keywords_
                    logger.info("Loaded OHDSIFeatureExtractor from model metadata")
                else:
                    # Legacy model without feature_extractor — load vectorizer
                    logger.warning("No feature_extractor in metadata — loading legacy vectorizer")
                    if self.vectorizer_path.exists():
                        with open(self.vectorizer_path, 'rb') as f:
                            self.vectorizer = pickle.load(f)

                # Restore probability calibrator
                self.calibrator = metadata.get('calibrator', None)
                if self.calibrator:
                    logger.info("Loaded isotonic probability calibrator from model metadata")

                # Restore keyword term sets for legacy compatibility
                self.methodology_terms = metadata.get('methodology_terms', self.methodology_terms)
                self.database_terms = metadata.get('database_terms', self.database_terms)
                self.analysis_terms = metadata.get('analysis_terms', self.analysis_terms)

        logger.info(f"Enhanced V2 {self.model_type} model loaded successfully")
    
    def classify_with_gpt(self, article: Dict) -> Dict:
        """
        Classify article using GPT-4o-mini with enriched metadata.
        """
        if not self.openai_client:
            return {
                "is_ohdsi_related": None,
                "confidence": 0.0,
                "categories": [],
                "reasoning": "OpenAI API not configured"
            }
        
        # Prepare article text with enriched metadata
        # Handle authors as either strings or dicts with full information
        authors = article.get('authors', [])
        author_info = []
        if authors and isinstance(authors[0], dict):
            for author in authors:
                name = author.get("name", "")
                affiliation = author.get("affiliation", "")
                orcid = author.get("orcid", "")
                
                # Build author string with available info
                author_str = name
                if affiliation:
                    author_str += f" ({affiliation})"
                if orcid:
                    author_str += f" [ORCID: {orcid}]"
                author_info.append(author_str)
        elif isinstance(authors, list):
            author_info = authors
        
        # Extract MeSH terms - handle both string and dict formats
        mesh_terms_raw = article.get('mesh_terms', [])
        mesh_terms = []
        for term in mesh_terms_raw:
            if isinstance(term, dict):
                # Extract descriptor_name from dict format
                mesh_terms.append(term.get('descriptor_name', ''))
            elif isinstance(term, str):
                # Already a string
                mesh_terms.append(term)
        mesh_str = ', '.join(filter(None, mesh_terms)) if mesh_terms else 'None'
        
        # Extract funding information
        grants = article.get('grants', [])
        funding_str = 'Yes' if grants else 'No'
        if grants and isinstance(grants[0], dict):
            funding_agencies = [g.get('agency', '') for g in grants if g.get('agency')]
            if funding_agencies:
                # Convert to list to allow slicing, then take first 3 unique agencies
                unique_agencies = list(set(funding_agencies))[:3]
                funding_str = f"Yes (Agencies: {', '.join(unique_agencies)})"
        
        article_text = f"""
Title: {article.get('title', '')}
Abstract: {article.get('abstract', '')}
Keywords: {', '.join(article.get('keywords', []))}
MeSH Terms: {mesh_str}
Journal: {article.get('journal', '')}
Year: {article.get('year', '')}
Authors: {'; '.join(author_info[:10])}  # Limit to first 10 authors
Publication Types: {', '.join(article.get('publication_types', []))}
Funding: {funding_str}
Reference Count: {article.get('reference_count', 0)}
"""
        
        categories_list = '\n'.join([f'- {cat}' for cat in OHDSI_CATEGORIES])
        
        system_prompt = f"""You are an expert in OHDSI (Observational Health Data Sciences and Informatics) research classification.

OHDSI is a collaborative that focuses on:
- OMOP Common Data Model (CDM) for standardizing observational health data
- Tools like Atlas for cohort definition and HADES for analytics
- Network studies across multiple databases
- Real-world evidence generation
- Drug safety and pharmacovigilance
- Comparative effectiveness research
- Patient-level prediction models
- Population-level estimation
- Clinical characterization and phenotyping

Classify the given article and return a JSON response with this EXACT structure:
{{
  "is_ohdsi_related": boolean,
  "confidence": float (0.0 to 1.0),
  "categories": [list of up to 5 categories from the provided list below],
  "reasoning": "Brief explanation of classification decision"
}}

IMPORTANT: You MUST only use categories from this exact list:
{categories_list}
ALWAYS SELECT AT LEAST ONE CATEGORY, REGARDLESS OF WHETHER THE ARTICLE IS OHDSI-RELATED OR NOT.

Be conservative - only classify as OHDSI-related if there's clear relevance to OHDSI methods, tools, or community work.

**Important Classification Factors**:
1. Direct mentions of OHDSI tools (OMOP CDM, Atlas, HADES, Achilles, etc.)
2. Author affiliations with known OHDSI institutions (Columbia, Janssen, IQVIA, etc.)
3. MeSH terms related to observational studies, pharmacovigilance, or data standards
4. Authors who are known OHDSI contributors (check names and ORCID IDs)
5. Funding from OHDSI-supporting organizations

Focus on actual OHDSI involvement, not just topical relevance.
"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Classify this article:\n\n{article_text}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validate categories
            returned_categories = result.get("categories", [])
            valid_categories = [cat for cat in returned_categories if cat in OHDSI_CATEGORIES]
            
            return {
                "is_ohdsi_related": bool(result.get("is_ohdsi_related", False)),
                "confidence": float(result.get("confidence", 0.0)),
                "categories": valid_categories[:5],
                "reasoning": result.get("reasoning", "")
            }
            
        except Exception as e:
            logger.error(f"GPT classification failed: {e}")
            return {
                "is_ohdsi_related": None,
                "confidence": 0.0,
                "categories": [],
                "reasoning": f"Error: {str(e)}"
            }
    
    def predict_from_article(self, article: Dict) -> Dict:
        """
        Predict if an article is OHDSI-related using ML model (and optionally GPT).
        Uses OHDSIFeatureExtractor for feature computation — same path as training.
        """
        if not self.model:
            self.load_model()

        # Build DataFrame from article for feature extraction
        article_for_df = article.copy()

        # Ensure required fields exist with sensible defaults
        if 'mesh_terms' not in article_for_df:
            article_for_df['mesh_terms'] = []
        if 'abstract' not in article_for_df:
            article_for_df['abstract'] = ''

        # Use OHDSIFeatureExtractor — same feature path as training and evaluation
        df = pd.DataFrame([article_for_df])

        if self.feature_extractor is not None:
            X = self.feature_extractor.transform(df)
        else:
            # Legacy fallback: model loaded from old pickle without feature_extractor
            logger.warning("No feature_extractor found — using legacy feature computation")
            X = self._legacy_feature_extraction(article_for_df, df)
        
        # ML model prediction (X is numpy array from transform() or legacy path)
        X_arr = X.values if hasattr(X, 'values') else X
        if X_arr.ndim == 2 and X_arr.shape[0] != 1:
            X_arr = X_arr[0:1]
        ml_prob_raw = self.model.predict_proba(X_arr)[0, 1]
        ml_prob = self.calibrate_probability(ml_prob_raw)  # Apply calibration
        
        # Get per-instance feature contributions via tree path decomposition
        top_factors = []
        instance_factors = []
        try:
            from treeinterpreter import treeinterpreter as ti
            ti_input = X_arr if X_arr.ndim == 2 else X_arr.reshape(1, -1)
            _, _, contributions = ti.predict(self.model, ti_input)
            contribs = contributions[0, :, 1]  # class 1 (positive) contributions

            for i, fname in enumerate(self.feature_names):
                if fname.startswith('tfidf_'):
                    continue
                val = float(X_arr[0, i]) if X_arr.ndim == 2 else float(X_arr[i])
                instance_factors.append({
                    'feature': fname.replace('_', ' ').title(),
                    'value': round(val, 3),
                    'contribution': round(float(contribs[i]), 6),
                })
            instance_factors.sort(key=lambda x: abs(x['contribution']), reverse=True)
            instance_factors = instance_factors[:7]
            top_factors = [f['feature'] for f in instance_factors]
        except Exception as e:
            logger.warning(f"treeinterpreter unavailable, using global importances: {e}")
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
                indices = np.argsort(importances)[::-1][:7]
                for i in indices:
                    if i < len(self.feature_names) and not self.feature_names[i].startswith('tfidf_'):
                        top_factors.append(self.feature_names[i].replace('_', ' ').title())
        
        # GPT classification (optional — controlled by USE_GPT_SCORING env var)
        use_gpt = os.getenv('USE_GPT_SCORING', 'false').lower() == 'true'

        if use_gpt and self.openai_client:
            gpt_result = self.classify_with_gpt(article)

            # Dynamic weighting - trust ML model more, especially when confident
            if ml_prob_raw > 0.98 or ml_prob_raw < 0.02:
                weight_ml, weight_gpt = 0.7, 0.3
            elif ml_prob_raw > 0.8 or ml_prob_raw < 0.2:
                weight_ml, weight_gpt = 0.65, 0.35
            else:
                weight_ml, weight_gpt = 0.6, 0.4

            combined_confidence = weight_ml * ml_prob + weight_gpt * gpt_result['confidence']
            categories = gpt_result['categories'] if gpt_result['categories'] else []
        else:
            gpt_result = {'confidence': 0.0, 'categories': [], 'reasoning': 'GPT disabled'}
            weight_ml, weight_gpt = 1.0, 0.0
            combined_confidence = ml_prob
            categories = []

        # Default category assignment when GPT doesn't provide them
        if not categories:
            if combined_confidence > 0.9:
                categories = ["Methodological research", "Open-source analytics development"]
            elif combined_confidence > 0.8:
                categories = ["Methodological research"]
            elif combined_confidence > 0.7:
                categories = ["Clinical applications"]

        # Check if any authors are known OHDSI community members
        has_known_author = False
        if self.topic_authors:
            authors = article.get('authors', article.get('author', []))
            if isinstance(authors, list):
                for a in authors:
                    name = a.get('name', '') if isinstance(a, dict) else str(a)
                    if name.strip() in self.topic_authors:
                        has_known_author = True
                        break
            elif isinstance(authors, str):
                for a in authors.split(';'):
                    if a.strip() in self.topic_authors:
                        has_known_author = True
                        break

        return {
            'is_ohdsi_related': combined_confidence > 0.5,
            'ml_probability': float(ml_prob),
            'ml_probability_raw': float(ml_prob_raw),
            'gpt_probability': gpt_result['confidence'],
            'combined_probability': float(combined_confidence),
            'ml_weight': weight_ml,
            'gpt_weight': weight_gpt,
            'predicted_categories': categories,
            'gpt_reasoning': gpt_result.get('reasoning', ''),
            'top_factors': top_factors,
            'instance_factors': instance_factors,
            'model_type': self.model_type,
            'has_known_author': has_known_author,
        }