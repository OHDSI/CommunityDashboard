"""
Content-related GraphQL types.

Includes Author, ContentMetrics, Content, and SearchResult types.
"""
import strawberry
from strawberry.scalars import JSON
from typing import Optional, List

from ..helpers import compute_display_fields
from ..services import search_service


@strawberry.type
class Author:
    name: str
    email: Optional[str] = None
    affiliation: Optional[str] = None
    orcid: Optional[str] = None  # Added for ES schema v3


@strawberry.type
class ContentMetrics:
    view_count: int = 0
    bookmark_count: int = 0
    share_count: int = 0
    citation_count: int = 0  # Added for ES schema v3


@strawberry.type
class Content:
    id: str
    title: str
    abstract: Optional[str]
    content_type: str

    # Multimodal fields
    source: Optional[str] = None  # pubmed, youtube, github, discourse, wiki
    display_type: Optional[str] = None  # Research Article, Video Content, Code Repository, etc.
    icon_type: Optional[str] = None  # document-text, play-circle, code, chat-bubble, book-open
    content_category: Optional[str] = None  # research, media, code, community, reference

    authors: List[Author]
    published_date: Optional[str]  # Changed to str to handle date-only format
    created_at: Optional[str] = None  # Changed to str for flexibility
    ml_score: Optional[float]
    ai_confidence: Optional[float] = None  # Consolidated from gpt_score
    final_score: Optional[float] = None  # Consolidated from combined_score
    categories: List[str]  # Consolidated categories field
    metrics: ContentMetrics
    url: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    keywords: List[str] = strawberry.field(default_factory=list)
    year: Optional[int] = None

    # Source-specific fields
    # YouTube
    video_id: Optional[str] = None
    duration: Optional[int] = None  # in seconds
    channel_name: Optional[str] = None
    thumbnail_url: Optional[str] = None
    transcript: Optional[str] = None

    # GitHub
    owner: Optional[str] = None
    repo_name: Optional[str] = None
    stars_count: Optional[int] = None
    watchers_count: Optional[int] = None
    forks_count: Optional[int] = None
    open_issues_count: Optional[int] = None
    contributors_count: Optional[int] = None
    contributors: List[str] = strawberry.field(default_factory=list)
    readme_content: Optional[str] = None
    language: Optional[str] = None
    license: Optional[str] = None
    topics: List[str] = strawberry.field(default_factory=list)  # Added for ES schema v3
    last_commit: Optional[str] = None  # Changed to str for flexibility

    # Discourse
    topic_id: Optional[str] = None
    reply_count: Optional[int] = None
    solved: Optional[bool] = None

    # Wiki
    doc_type: Optional[str] = None
    section_count: Optional[int] = None
    last_modified: Optional[str] = None  # Changed to str for flexibility

    # Citations (simplified structure for ES schema v3)
    pmid: Optional[str] = None
    citations: Optional[JSON] = None  # Simplified: {cited_by_count, references_count, cited_by_ids[], reference_ids[]}

    # PubMed specific fields (added for ES schema v3)
    journal: Optional[str] = None
    mesh_terms: List[str] = strawberry.field(default_factory=list)

    # AI Enhancement fields
    ai_enhanced: Optional[bool] = None
    ai_is_ohdsi: Optional[bool] = None
    ai_summary: Optional[str] = None
    ai_tools: List[str] = strawberry.field(default_factory=list)

    @strawberry.field
    async def related_content(self, limit: int = 5) -> List["Content"]:
        """Get related content"""
        related = await search_service.get_related(self.id, limit)
        related_items = []
        for item in related:
            # Process authors - only extract the fields we need
            authors = []
            if item.authors:
                for author_data in item.authors:
                    # Handle author data whether it's a dict or object
                    if hasattr(author_data, '__dict__'):
                        author_dict = author_data.__dict__
                    else:
                        author_dict = author_data

                    author = Author(
                        name=author_dict.get("name", ""),
                        email=author_dict.get("email"),
                        affiliation=author_dict.get("affiliation")
                    )
                    authors.append(author)

            # Compute display fields for related content
            computed_fields = compute_display_fields(getattr(item, 'source', ''), item.content_type)

            related_items.append(Content(
                id=item.id,
                title=item.title,
                abstract=item.abstract,
                content_type=item.content_type,

                # Multimodal fields (with computed fallbacks for ES schema v3)
                source=getattr(item, 'source', None),
                display_type=getattr(item, 'display_type', computed_fields['display_type']),
                icon_type=getattr(item, 'icon_type', computed_fields['icon_type']),
                content_category=getattr(item, 'content_category', computed_fields['content_category']),

                authors=authors,
                published_date=str(item.published_date) if item.published_date else None,
                ml_score=item.ml_score,
                categories=getattr(item, 'categories', []),
                # Handle metrics as either object or dict
                metrics=ContentMetrics(**item.metrics.__dict__) if hasattr(item.metrics, '__dict__') else ContentMetrics(**item.metrics) if item.metrics else ContentMetrics(),
                journal=getattr(item, 'journal', None),
                doi=getattr(item, 'doi', None),
                keywords=getattr(item, 'keywords', []),
                year=getattr(item, 'year', None)
            ))
        return related_items


@strawberry.type
class SearchResult:
    total: int
    items: List[Content]
    aggregations: strawberry.scalars.JSON
    took_ms: int
