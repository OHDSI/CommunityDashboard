from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ReviewItem(BaseModel):
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
    
    # v3 fields (primary)
    ai_confidence: Optional[float] = 0.0  # Replaces gpt_score
    final_score: Optional[float] = 0.0    # Replaces combined_score
    quality_score: Optional[float] = 0.5  # Quality score used in final_score calculation
    categories: Optional[List[str]] = []  # Replaces predicted_categories
    ai_summary: Optional[str] = ""        # Replaces gpt_reasoning
    
    # Keep old fields for backward compatibility during migration
    gpt_score: Optional[float] = 0.0
    combined_score: Optional[float] = 0.0
    predicted_categories: Optional[List[str]] = []  # Make optional for backward compat
    gpt_reasoning: Optional[str] = ""
    
    classification_factors: Optional[List[dict]] = []

    status: str = "pending"  # pending, approved, rejected
    submitted_date: datetime
    priority: int = Field(0, ge=0, le=10)
    
    class Config:
        from_attributes = True

class ReviewAction(BaseModel):
    action: str  # approve, reject
    categories: Optional[List[str]] = None
    notes: Optional[str] = None

class ReviewStats(BaseModel):
    pending: int
    approved_today: int
    rejected_today: int
    avg_ml_score: float