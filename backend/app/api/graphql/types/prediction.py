"""
Prediction-related GraphQL types.

Includes types for ML prediction results, PubMed predictions,
and model statistics.
"""
import strawberry
from typing import Optional, List


@strawberry.type
class PredictionFactor:
    feature: str
    score: float


@strawberry.type
class PredictionResult:
    is_ohdsi_related: bool
    confidence_score: float
    predicted_categories: List[str]
    top_factors: List[PredictionFactor]
    recommendation: str
    already_known: bool = False


@strawberry.type
class ArticleData:
    pmid: Optional[str] = None
    title: str = ""
    abstract: str = ""
    authors: List[str] = strawberry.field(default_factory=list)
    journal: Optional[str] = None
    year: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None


@strawberry.type
class PubMedPrediction:
    article: ArticleData
    prediction: PredictionResult


@strawberry.type
class ModelStats:
    model_exists: bool
    topic_authors_count: Optional[int] = None
    topic_keywords_count: Optional[int] = None
    known_articles_count: Optional[int] = None
    feature_count: Optional[int] = None
    last_trained: Optional[float] = None
