"""
Topic-agnostic PubMed query learner.

Given a set of known positive articles, automatically discovers the best
PubMed search queries to maximize retrieval recall.
"""

from .term_extractor import TermExtractor, TermCandidate
from .query_builder import QueryBuilder, CandidateQuery
from .query_optimizer import QueryOptimizer, OptimizationResult
