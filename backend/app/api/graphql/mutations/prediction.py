"""
Prediction mutation resolvers.

Handles predict_text, predict_pubmed, submit_prediction,
and trigger_article_pipeline mutations.
"""
import logging
from typing import Optional, List
from strawberry.types import Info

from ..types.prediction import (
    PredictionFactor, PredictionResult, ArticleData, PubMedPrediction,
)
from ..helpers import require_admin
from ..services import prediction_service

logger = logging.getLogger(__name__)


def resolve_predict_text(
    title: str,
    abstract: str,
    authors: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None
) -> PredictionResult:
    """Predict OHDSI relevance for submitted text"""
    result = prediction_service.predict_text(
        title=title,
        abstract=abstract,
        authors=authors,
        keywords=keywords
    )

    return PredictionResult(
        is_ohdsi_related=result['is_ohdsi_related'],
        confidence_score=result['confidence_score'],
        predicted_categories=result['predicted_categories'],
        top_factors=[
            PredictionFactor(feature=f['feature'], score=f['score'])
            for f in result['top_factors']
        ],
        recommendation=result['recommendation'],
        already_known=result['already_known']
    )


def resolve_predict_pubmed(pmid: str) -> PubMedPrediction:
    """Predict OHDSI relevance for a PubMed article"""
    result = prediction_service.predict_pubmed(pmid)

    article_data = result['article']
    prediction_data = result['prediction']

    return PubMedPrediction(
        article=ArticleData(
            pmid=article_data.get('pmid'),
            title=article_data['title'],
            abstract=article_data['abstract'],
            authors=article_data['authors'],
            journal=article_data.get('journal'),
            year=article_data.get('year'),
            doi=article_data.get('doi'),
            url=article_data.get('url')
        ),
        prediction=PredictionResult(
            is_ohdsi_related=prediction_data['is_ohdsi_related'],
            confidence_score=prediction_data['confidence_score'],
            predicted_categories=prediction_data['predicted_categories'],
            top_factors=[
                PredictionFactor(feature=f['feature'], score=f['score'])
                for f in prediction_data['top_factors']
            ],
            recommendation=prediction_data['recommendation'],
            already_known=prediction_data['already_known']
        )
    )


def resolve_submit_prediction(
    title: str,
    abstract: str,
    confidence_score: float,
    predicted_categories: List[str],
    authors: Optional[List[str]] = None
) -> bool:
    """Submit predicted content for review or auto-approval"""
    prediction_result = {
        'confidence_score': confidence_score,
        'predicted_categories': predicted_categories,
        'article': {
            'title': title,
            'abstract': abstract,
            'authors': authors or []
        }
    }

    return prediction_service.submit_for_review(
        prediction_result=prediction_result,
        submitted_by='anonymous'  # In production, get from auth
    )


def resolve_trigger_article_pipeline(info: Info) -> bool:
    """Manually trigger the article classification pipeline (requires admin)"""
    require_admin(info)
    from ....workers.celery_app import celery_app

    try:
        result = celery_app.send_task('app.workers.tasks.run_article_classifier')
        return True
    except Exception as e:
        logger.error(f"Failed to trigger pipeline: {e}")
        return False
