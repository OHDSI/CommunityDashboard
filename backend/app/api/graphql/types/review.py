"""
Review-related GraphQL types.

Includes ClassificationFactor, ReviewItem, and QueueStats types.
"""
import strawberry
from typing import Optional, List
from datetime import datetime


@strawberry.type
class ClassificationFactor:
    feature: str
    value: float
    contribution: float


@strawberry.type
class ReviewItem:
    id: str
    title: str
    abstract: Optional[str]
    content_type: str
    source: Optional[str] = None  # pubmed, github, youtube, discourse, wiki
    display_type: Optional[str] = None  # Research Article, Code Repository, Video Content, etc.
    icon_type: Optional[str] = None  # document-text, code, play-circle, chat-bubble, book-open
    content_category: Optional[str] = None  # research, code, media, community, reference
    url: Optional[str]
    ml_score: float
    ai_confidence: Optional[float] = 0.0  # Replaces gpt_score in ES schema v3
    final_score: Optional[float] = 0.0   # Replaces combined_score in ES schema v3
    quality_score: Optional[float] = 0.0  # Quality score used in final_score calculation
    categories: List[str]  # Replaces ohdsi_categories in ES schema v3
    classification_factors: List[ClassificationFactor] = strawberry.field(default_factory=list)

    # AI Enhancement fields
    ai_enhanced: Optional[bool] = None
    ai_is_ohdsi: Optional[bool] = None
    ai_summary: Optional[str] = None
    ai_tools: List[str] = strawberry.field(default_factory=list)

    status: str
    submitted_date: datetime
    priority: int


@strawberry.type
class QueueStats:
    pending: int
    approved: int
    rejected: int
    avgScore: float
    highConfidence: int = 0
    lowConfidence: int = 0
