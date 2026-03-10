"""
ArticleClassifier module for OHDSI Dashboard.
Provides ML-based article classification and retrieval from PubMed.
"""

from .retriever import PubMedRetriever
from .wrapper import ArticleClassifierWrapper

__all__ = [
    'PubMedRetriever',
    'ArticleClassifierWrapper'
]

__version__ = '2.0.0'