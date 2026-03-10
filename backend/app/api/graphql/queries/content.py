"""
Content query resolvers.

Handles search_content, semantic_search, hybrid_search, content, and get_categories queries.
"""
import logging
from typing import Optional, List
from strawberry.scalars import JSON

from ..types.content import Author, Content, ContentMetrics, SearchResult
from ..helpers import compute_display_fields
from ..services import search_service
from ....config import settings
from ....database import es_client

logger = logging.getLogger(__name__)

try:
    import sys
    sys.path.append('/app')
    from config.ohdsi_categories import map_old_categories as _map_old_cats
except ImportError:
    def _map_old_cats(cats):
        return cats


async def resolve_search_content(
    query: Optional[str] = None,
    filters: Optional[JSON] = None,
    size: int = 20,
    offset: int = 0,
    sort_by: Optional[str] = None
) -> SearchResult:
    """Search content with filters and pagination"""
    result = await search_service.search(
        query=query,
        filters=filters or {},
        size=size,
        offset=offset,
        sort_by=sort_by or "date-desc"
    )

    items = []
    for item in result.items:
        items.append(_build_content_from_search_item(item))

    return SearchResult(
        total=result.total,
        items=items,
        aggregations=result.aggregations,
        took_ms=result.took_ms
    )


async def resolve_semantic_search(
    query: str,
    filters: Optional[JSON] = None,
    size: int = 20,
    offset: int = 0,
    sort_by: Optional[str] = None,
    min_score: float = 0.0
) -> SearchResult:
    """Semantic similarity search using embeddings"""
    result = await search_service.semantic_search(
        query=query,
        filters=filters or {},
        size=size,
        offset=offset,
        sort_by=sort_by or "date-desc",
        min_score=min_score
    )

    items = []
    for item in result.items:
        items.append(_build_content_from_search_item(item))

    return SearchResult(
        total=result.total,
        items=items,
        aggregations=result.aggregations,
        took_ms=result.took_ms
    )


async def resolve_hybrid_search(
    query: str,
    filters: Optional[JSON] = None,
    size: int = 20,
    offset: int = 0,
    sort_by: Optional[str] = None,
    keyword_weight: float = 0.5,
    semantic_weight: float = 0.5
) -> SearchResult:
    """Hybrid search combining keyword and semantic search"""
    result = await search_service.hybrid_search(
        query=query,
        filters=filters or {},
        size=size,
        offset=offset,
        sort_by=sort_by or "date-desc",
        keyword_weight=keyword_weight,
        semantic_weight=semantic_weight
    )

    items = []
    for item in result.items:
        items.append(_build_content_from_search_item(item))

    return SearchResult(
        total=result.total,
        items=items,
        aggregations=result.aggregations,
        took_ms=result.took_ms
    )


async def resolve_content(id: str) -> Optional[Content]:
    """Get single content item"""
    try:
        logger.info(f"Fetching content with id: {id}")

        # Try direct ID first
        try:
            response = es_client.get(index=settings.content_index, id=id)
            item = response["_source"]
            item_id = response["_id"]
        except Exception:
            # If direct ID fails, try searching by URL or other fields
            search_query = {
                "query": {
                    "bool": {
                        "should": [
                            {"term": {"_id": id}},
                            {"match": {"url": id}},
                            {"match": {"pmid": id}},
                            {"match": {"pmid": id.replace("PMID", "")}} if id.startswith("PMID") else {"match_none": {}}
                        ]
                    }
                }
            }
            search_result = es_client.search(index=settings.content_index, body=search_query, size=1)

            if search_result["hits"]["total"]["value"] == 0:
                logger.warning(f"No content found for id: {id}")
                return None

            hit = search_result["hits"]["hits"][0]
            item = hit["_source"]
            item_id = hit["_id"]

        # Process authors - only extract the fields we need
        authors = []
        for author_data in item.get("authors", []):
            # Extract only the fields that Author type expects
            author = Author(
                name=author_data.get("name", ""),
                email=author_data.get("email"),
                affiliation=author_data.get("affiliation")
            )
            authors.append(author)

        # Parse published_date if it's a string
        published_date = item.get("published_date")
        if published_date and isinstance(published_date, str):
            try:
                from dateutil import parser
                published_date = parser.parse(published_date)
            except Exception:
                published_date = None

        return Content(
            id=item_id,
            title=item["title"],
            abstract=item.get("abstract"),
            content_type=item["content_type"],

            # Multimodal fields
            source=item.get("source"),
            display_type=item.get("display_type"),
            icon_type=item.get("icon_type"),
            content_category=item.get("content_category"),

            authors=authors,
            published_date=published_date,
            ml_score=item.get("ml_score"),
            ai_confidence=item.get("ai_confidence") or item.get("gpt_score"),  # Backward compatibility
            final_score=item.get("final_score") or item.get("combined_score"),  # Backward compatibility
            categories=_map_old_cats(item.get("categories") or item.get("ohdsi_categories", [])),
            metrics=ContentMetrics(
                view_count=item.get("view_count", 0),
                bookmark_count=item.get("bookmark_count", 0)
            ),
            url=item.get("url"),
            journal=item.get("journal"),
            doi=item.get("doi"),
            keywords=item.get("keywords", []),
            year=item.get("year"),

            # YouTube specific
            video_id=item.get("video_id") or (item_id if item.get("source") == "youtube" else None),
            duration=item.get("duration"),
            channel_name=item.get("channel_name"),
            thumbnail_url=item.get("thumbnail_url"),
            transcript=item.get("transcript"),

            # GitHub specific
            repo_name=item.get("repo_name"),
            stars_count=item.get("stars_count"),
            watchers_count=item.get("watchers_count"),
            forks_count=item.get("forks_count"),
            open_issues_count=item.get("open_issues_count"),
            contributors_count=item.get("contributors_count"),
            contributors=item.get("contributors", []),
            readme_content=item.get("readme_content"),
            language=item.get("language"),
            license=item.get("license"),
            last_commit=item.get("last_commit"),

            # Discourse specific
            topic_id=item.get("topic_id"),
            reply_count=item.get("reply_count"),
            solved=item.get("solved"),

            # Wiki specific
            doc_type=item.get("doc_type"),
            section_count=item.get("section_count"),
            last_modified=item.get("last_modified") or item.get("last_updated"),

            # Citations (for PubMed articles)
            pmid=item.get("pmid"),
            citations=item.get("citations")
        )
    except Exception as e:
        logger.error(f"Error fetching content {id}: {str(e)}")
        return None


def resolve_get_categories() -> List[str]:
    """Get all available OHDSI categories"""
    try:
        # Import the category system
        import sys
        sys.path.append('/app')
        from config.ohdsi_categories import get_all_categories
        categories = get_all_categories()
        logger.info(f"Returning {len(categories)} categories")
        return categories
    except ImportError as e:
        logger.warning(f"Could not import category system: {e}")
        return [
            "Observational data standards and management",
            "Methodological research",
            "Open-source analytics development",
            "Clinical applications",
        ]


def _build_content_from_search_item(item) -> Content:
    """Build a Content object from a search result item.

    Shared helper to avoid duplicating the Content construction logic
    across search_content, semantic_search, and hybrid_search resolvers.
    """
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

    # Use categories field (consolidated in ES schema v3), mapped to new 4-category system
    categories = _map_old_cats(
        getattr(item, 'categories', []) or getattr(item, 'ohdsi_categories', []) or getattr(item, 'predicted_categories', [])
    )

    # Compute display fields if not provided (for ES schema v3)
    computed_fields = compute_display_fields(getattr(item, 'source', ''), item.content_type)

    return Content(
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
        created_at=str(getattr(item, 'created_at', None)) if getattr(item, 'created_at', None) else None,
        ml_score=item.ml_score,
        ai_confidence=getattr(item, 'ai_confidence', getattr(item, 'gpt_score', None)),  # Map old field to new
        final_score=getattr(item, 'final_score', getattr(item, 'combined_score', None)),  # Map old field to new
        categories=categories,
        # Handle metrics as either object or dict
        metrics=ContentMetrics(**item.metrics.__dict__) if hasattr(item.metrics, '__dict__') else ContentMetrics(**item.metrics) if item.metrics else ContentMetrics(),
        url=item.url or '',
        journal=getattr(item, 'journal', None),
        doi=getattr(item, 'doi', None),
        keywords=getattr(item, 'keywords', []),
        year=getattr(item, 'year', None),

        # YouTube specific
        video_id=getattr(item, 'video_id', None) or (item.id if getattr(item, 'source', None) == 'youtube' else None),
        duration=getattr(item, 'duration', None),
        channel_name=getattr(item, 'channel_name', None),
        thumbnail_url=getattr(item, 'thumbnail_url', None),
        transcript=getattr(item, 'transcript', None),

        # GitHub specific
        owner=getattr(item, 'owner', None),
        repo_name=getattr(item, 'repo_name', None),
        stars_count=getattr(item, 'stars_count', None),
        watchers_count=getattr(item, 'watchers_count', None),
        forks_count=getattr(item, 'forks_count', None),
        open_issues_count=getattr(item, 'open_issues_count', None),
        contributors_count=getattr(item, 'contributors_count', None),
        contributors=getattr(item, 'contributors', []),
        readme_content=getattr(item, 'readme_content', None),
        language=getattr(item, 'language', None),
        license=getattr(item, 'license', None),
        topics=getattr(item, 'topics', []),  # Added for ES schema v3
        last_commit=str(getattr(item, 'last_commit', None)) if getattr(item, 'last_commit', None) else None,

        # Discourse specific
        topic_id=getattr(item, 'topic_id', None),
        reply_count=getattr(item, 'reply_count', None),
        solved=getattr(item, 'solved', None),

        # Wiki specific
        doc_type=getattr(item, 'doc_type', None),
        section_count=getattr(item, 'section_count', None),
        last_modified=str(getattr(item, 'last_modified', getattr(item, 'last_updated', None))) if getattr(item, 'last_modified', getattr(item, 'last_updated', None)) else None,  # Map old field to new

        # Citations (for PubMed articles)
        pmid=getattr(item, 'pmid', None),
        citations=getattr(item, 'citations', None),

        # AI Enhancement fields
        ai_enhanced=getattr(item, 'ai_enhanced', None),
        ai_is_ohdsi=getattr(item, 'ai_is_ohdsi', None),
        ai_summary=getattr(item, 'ai_summary', None),
        ai_tools=getattr(item, 'ai_tools', [])
    )
