from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class Author(BaseModel):
    name: str
    email: Optional[str] = None
    affiliation: Optional[str] = None

class ContentMetrics(BaseModel):
    view_count: int = 0
    bookmark_count: int = 0
    share_count: int = 0
    citation_count: int = 0  # Added to match frontend expectations

class ContentBase(BaseModel):
    title: str
    abstract: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None
    content_type: str  # article, video, github, dataset
    authors: List[Author] = []
    published_date: Optional[str] = None  # Changed to str to handle date-only format
    categories: List[str] = []  # Changed from ohdsi_categories to match ingested data

class ContentCreate(ContentBase):
    ml_score: Optional[float] = None
    predicted_categories: List[str] = []

class ContentResponse(ContentBase):
    id: str
    ml_score: Optional[float]
    # Support both field names for backward compatibility
    ai_confidence: Optional[float] = None  # New field name
    gpt_score: Optional[float] = None  # Legacy field name
    final_score: Optional[float] = None  # New field name
    combined_score: Optional[float] = None  # Legacy field name
    gpt_reasoning: Optional[str] = None
    predicted_categories: List[str] = []
    approval_status: str = "approved"
    metrics: ContentMetrics = ContentMetrics()
    created_at: Optional[str] = None  # Changed to str for flexibility
    updated_at: Optional[str] = None  # Changed to str for flexibility  
    indexed_date: Optional[str] = None  # Added to match ingested data
    approved_at: Optional[str] = None  # Added to match ingested data
    approved_by: Optional[str] = None  # Added to match ingested data
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    keywords: List[str] = []
    pmid: Optional[str] = None  # Added for PubMed articles
    ai_summary: Optional[str] = None  # Added for AI enhancement
    
    # Multimodal fields
    source: Optional[str] = None  # pubmed, youtube, github, discourse, wiki
    display_type: Optional[str] = None  # Research Article, Video Content, etc.
    icon_type: Optional[str] = None  # document-text, play-circle, code, etc.
    content_category: Optional[str] = None  # research, media, code, community, reference
    
    # YouTube specific
    video_id: Optional[str] = None
    duration: Optional[int] = None
    channel_name: Optional[str] = None
    thumbnail_url: Optional[str] = None
    
    # GitHub specific
    repo_name: Optional[str] = None
    stars_count: Optional[int] = None
    forks_count: Optional[int] = None
    language: Optional[str] = None
    last_commit: Optional[str] = None  # Changed to str for flexibility
    
    # Discourse specific
    topic_id: Optional[int] = None
    reply_count: Optional[int] = None
    solved: Optional[bool] = None
    
    # Wiki specific
    doc_type: Optional[str] = None
    section_count: Optional[int] = None
    last_updated: Optional[str] = None  # Changed to str for flexibility
    
    class Config:
        from_attributes = True

class ContentSearch(BaseModel):
    query: Optional[str] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    size: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    sort_by: str = "relevance"  # relevance, date, popularity

class SearchResult(BaseModel):
    total: int
    items: List[ContentResponse]
    aggregations: Dict[str, Any]
    took_ms: int