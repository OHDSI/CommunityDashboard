from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
import logging

from ...database import es_client, redis_client
from ...schemas import ContentSearch, SearchResult
from ...services.search_service import SearchService

router = APIRouter()
logger = logging.getLogger(__name__)
search_service = SearchService(es_client, redis_client)

@router.post("/", response_model=SearchResult)
async def search_content(search_params: ContentSearch):
    """
    Search for content with filters and pagination
    """
    try:
        result = await search_service.search(
            query=search_params.query,
            filters=search_params.filters,
            size=search_params.size,
            offset=search_params.offset,
            sort_by=search_params.sort_by
        )
        return result
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@router.get("/suggest")
async def suggest(
    query: str = Query(..., min_length=2),
    size: int = Query(5, ge=1, le=20)
):
    """
    Get search suggestions based on partial query
    """
    try:
        suggestions = await search_service.get_suggestions(query, size)
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error(f"Suggestion error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get suggestions")

@router.get("/filters")
async def get_available_filters():
    """
    Get available filter options with counts
    """
    try:
        filters = await search_service.get_filter_aggregations()
        return filters
    except Exception as e:
        logger.error(f"Filter aggregation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get filters")

@router.get("/trending")
async def get_trending(
    limit: int = Query(10, ge=1, le=50),
    timeframe: str = Query("week", regex="^(day|week|month)$")
):
    """
    Get trending content based on views and bookmarks
    """
    try:
        trending = await search_service.get_trending(limit, timeframe)
        return {"items": trending, "timeframe": timeframe}
    except Exception as e:
        logger.error(f"Trending error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get trending content")

@router.get("/related/{content_id}")
async def get_related_content(
    content_id: str,
    limit: int = Query(5, ge=1, le=20)
):
    """
    Get content related to a specific item
    """
    try:
        related = await search_service.get_related(content_id, limit)
        return {"items": related}
    except Exception as e:
        logger.error(f"Related content error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get related content")

@router.post("/semantic", response_model=SearchResult)
async def semantic_search(
    query: str = Query(..., min_length=1),
    filters: Optional[Dict[str, Any]] = None,
    size: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    min_score: float = Query(0.5, ge=0.0, le=1.0)
):
    """
    Semantic search using sentence embeddings for similarity matching
    """
    try:
        result = await search_service.semantic_search(
            query=query,
            filters=filters,
            size=size,
            offset=offset,
            min_score=min_score
        )
        return result
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        raise HTTPException(status_code=500, detail="Semantic search failed")

@router.post("/hybrid", response_model=SearchResult)
async def hybrid_search(
    query: str = Query(..., min_length=1),
    filters: Optional[Dict[str, Any]] = None,
    size: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    keyword_weight: float = Query(0.5, ge=0.0, le=1.0),
    semantic_weight: float = Query(0.5, ge=0.0, le=1.0)
):
    """
    Hybrid search combining keyword matching and semantic similarity
    """
    try:
        result = await search_service.hybrid_search(
            query=query,
            filters=filters,
            size=size,
            offset=offset,
            keyword_weight=keyword_weight,
            semantic_weight=semantic_weight
        )
        return result
    except Exception as e:
        logger.error(f"Hybrid search error: {e}")
        raise HTTPException(status_code=500, detail="Hybrid search failed")