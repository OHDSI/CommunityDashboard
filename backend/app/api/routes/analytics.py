"""
Analytics API Routes

Endpoints for LLM-powered natural language query generation and execution.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.services.llm_query_generator import LLMQueryGenerator, QueryGenerationResponse
from app.services.search_service import SearchService
from app.services.analytical_query_executor import AnalyticalQueryExecutor
from app.database import es_client, redis_client
from app.api.routes.auth import get_current_user
from app.models.user import User


# Optional user authentication dependency
def get_current_user_optional(authorization: Optional[str] = None) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    if not authorization:
        return None
    try:
        return get_current_user(authorization)
    except:
        return None


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class QueryRequest(BaseModel):
    """Request model for query generation."""
    query: str = Field(..., description="Natural language query", min_length=3)
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context (previous queries, preferences, etc.)")
    previous_result_summary: Optional[Dict[str, Any]] = Field(None, description="Chain data from previous query result")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="Last 2-3 query/result summaries")


class QueryRefinementRequest(BaseModel):
    """Request model for query refinement."""
    original_query: str
    previous_elasticsearch_query: Dict[str, Any]  # Previous ES query
    refinement: str
    error_message: Optional[str] = None


class ExecuteQueryRequest(BaseModel):
    """Request model for query execution."""
    elasticsearch_query: Dict[str, Any]  # Direct ES query
    visualization_type: str
    size: Optional[int] = 100
    offset: Optional[int] = 0


class SuggestionsRequest(BaseModel):
    """Request model for follow-up suggestions."""
    query: str
    results_summary: Dict[str, Any]


class DrilldownRequest(BaseModel):
    """Request for drilling into a specific data point."""
    parent_es_query: Dict[str, Any]
    clicked_field: str
    clicked_key: str
    drilldown_depth: int = 0


class AnalyticalRequest(BaseModel):
    """Request model for pre-built analytical queries."""
    entity_field: str = Field("authors.affiliation.keyword", description="Field to analyze")
    time_field: str = Field("year", description="Temporal field")
    time_window: Optional[List[int]] = Field(None, description="Time range [start, end]")
    top_n: int = Field(10, description="Number of top entities", ge=1, le=50)


# Initialize services
query_generator = LLMQueryGenerator()
search_service = SearchService(es_client, redis_client)
analytical_executor = AnalyticalQueryExecutor(search_service)


@router.post("/generate-query", response_model=QueryGenerationResponse)
async def generate_query(
    request: QueryRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Generate a structured query from natural language.

    This endpoint uses GPT-4o to convert natural language questions
    into structured query specifications that can be executed against
    the OHDSI content database.

    Args:
        request: Query generation request with natural language query
        current_user: Optional authenticated user for personalization

    Returns:
        QueryGenerationResponse with intermediate representation, GraphQL, and explanation

    Raises:
        HTTPException: If query generation fails
    """
    try:
        logger.info(f"Generating query for: {request.query}")

        # Add user context if available
        context = request.context or {}
        if current_user:
            context["user_id"] = str(current_user.id)
            context["user_role"] = current_user.role

        # Detect query chaining from previous results
        if request.previous_result_summary:
            chain_data = LLMQueryGenerator.detect_chain_intent(
                request.query, request.previous_result_summary
            )
            if chain_data:
                context["chain_data"] = chain_data
                logger.info(f"Chain detected: {chain_data['chain_type']} on {chain_data['reference_field']}")

        # Add conversation history
        if request.conversation_history:
            context["conversation_history"] = request.conversation_history[-3:]

        # Generate query
        response = await query_generator.generate_query(
            natural_language_query=request.query,
            context=context
        )

        logger.info(f"Query generated: {response.visualization_type} ({response.estimated_complexity})")
        return response

    except ValueError as e:
        logger.error(f"Query generation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in query generation: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate query")


@router.post("/refine-query", response_model=QueryGenerationResponse)
async def refine_query(
    request: QueryRefinementRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Refine an existing query based on feedback or errors.

    This endpoint allows iterative refinement of queries, either to fix errors
    or to adjust the query based on user feedback.

    Args:
        request: Refinement request with original query, previous ES query, and refinement details
        current_user: Optional authenticated user

    Returns:
        Refined QueryGenerationResponse

    Raises:
        HTTPException: If refinement fails
    """
    try:
        # Refine query
        response = await query_generator.refine_query(
            original_query=request.original_query,
            previous_es_query=request.previous_elasticsearch_query,
            refinement=request.refinement,
            error_message=request.error_message
        )

        return response

    except ValueError as e:
        logger.error(f"Query refinement failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in query refinement: {e}")
        raise HTTPException(status_code=500, detail="Failed to refine query")


@router.post("/execute-query")
async def execute_query(
    request: ExecuteQueryRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Execute an Elasticsearch query against the content database.

    This endpoint takes a complete Elasticsearch query and executes it directly,
    returning results formatted for visualization.

    Args:
        request: Query execution request with ES query
        current_user: Optional authenticated user

    Returns:
        Query results with data and aggregations

    Raises:
        HTTPException: If execution fails
    """
    try:
        es_query = request.elasticsearch_query
        visualization_type = request.visualization_type

        logger.info(f"Executing ES query (visualization: {visualization_type})")
        logger.debug(f"ES query: {json.dumps(es_query, indent=2)}")

        # Add approval status filter to query
        query = es_query.get("query", {"match_all": {}})
        if "bool" not in query:
            query = {
                "bool": {
                    "must": [query],
                    "filter": [{"term": {"approval_status": "approved"}}]
                }
            }
        else:
            if "filter" not in query["bool"]:
                query["bool"]["filter"] = []
            query["bool"]["filter"].append({"term": {"approval_status": "approved"}})

        # Build search body
        search_body = {
            "size": es_query.get("size", 0),
            "query": query,
            "aggs": es_query.get("aggs", {})
        }

        # Execute query directly against Elasticsearch
        logger.info(f"Executing query with {len(search_body['aggs'])} aggregations")
        response = search_service.es.search(index=search_service.index, body=search_body)

        # Extract results
        aggregations = response.get("aggregations", {})

        # DEBUG: Log raw ES response to diagnose nested aggregation issue
        logger.info(f"Raw ES aggregations: {json.dumps(aggregations, indent=2)}")
        total = response["hits"]["total"]["value"]
        took_ms = response.get("took", 0)

        # Format aggregations for visualization
        formatted_aggs = {}
        agg_types = []
        for agg_name, agg_data in aggregations.items():
            agg_type = _classify_aggregation_type(agg_data)
            agg_types.append(agg_type)

            if agg_type == "bucket":
                formatted_agg = _extract_buckets_from_aggregation(agg_data)
                formatted_aggs[agg_name] = formatted_agg if formatted_agg else agg_data
            elif agg_type == "stats":
                formatted_aggs[agg_name] = _extract_stats_as_buckets(agg_data)
            else:
                # single_metric or unknown — pass through
                formatted_aggs[agg_name] = agg_data

        # Auto-correct visualization type based on actual data shape
        if agg_types and all(t in ("stats", "single_metric") for t in agg_types):
            if visualization_type not in ("metric", "metric_card", "table"):
                logger.info(f"Auto-corrected visualization type from {visualization_type} to metric_card for stats aggregation")
                visualization_type = "metric_card"

        # Extract items if query requested documents (size > 0)
        items = []
        if search_body.get("size", 0) > 0:
            items = [hit["_source"] for hit in response["hits"]["hits"]]

        logger.info(f"Query executed: {len(formatted_aggs)} aggregations, {total} total docs")

        # Extract chain data for follow-up queries
        chain_data = LLMQueryGenerator.extract_result_chain_data(
            es_query,
            {"data": {"aggregations": formatted_aggs}, "total": total}
        )

        return {
            "success": True,
            "data": {
                "items": items,
                "aggregations": formatted_aggs,
                "total": total
            },
            "visualization_type": visualization_type,
            "total": total,
            "execution_time_ms": took_ms,
            "chain_data": chain_data,
        }

    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Failed to execute query: {str(e)}")


@router.post("/suggest-followup")
async def suggest_follow_up(
    request: SuggestionsRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Suggest follow-up queries based on results.

    This endpoint analyzes query results and suggests interesting
    follow-up questions that could provide additional insights.

    Args:
        request: Suggestions request with query and results summary
        current_user: Optional authenticated user

    Returns:
        List of suggested follow-up questions

    Raises:
        HTTPException: If suggestion generation fails
    """
    try:
        suggestions = await query_generator.suggest_follow_up(
            query=request.query,
            results_summary=request.results_summary
        )

        return {
            "suggestions": suggestions
        }

    except Exception as e:
        logger.error(f"Failed to generate suggestions: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate suggestions")


class QueryAndExecuteRequest(BaseModel):
    """Request model for combined generate-and-execute with auto-retry."""
    query: str = Field(..., description="Natural language query", min_length=3)
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context")
    previous_result_summary: Optional[Dict[str, Any]] = Field(None, description="Chain data from previous query result")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="Last 2-3 query/result summaries")


@router.post("/query-and-execute")
async def query_and_execute(
    request: QueryAndExecuteRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Generate and execute a query in one call with automatic error recovery.

    If the generated ES query fails, automatically retries using refine_query()
    with the error message as context. Returns the result along with retry count.
    """
    context = request.context or {}
    if current_user:
        context["user_id"] = str(current_user.id)
        context["user_role"] = current_user.role

    # Detect query chaining
    if request.previous_result_summary:
        chain_data = LLMQueryGenerator.detect_chain_intent(
            request.query, request.previous_result_summary
        )
        if chain_data:
            context["chain_data"] = chain_data

    if request.conversation_history:
        context["conversation_history"] = request.conversation_history[-3:]

    retries = 0
    original_response = None

    try:
        # Step 1: Generate query
        query_response = await query_generator.generate_query(
            natural_language_query=request.query,
            context=context
        )
        original_response = query_response

        # Step 2: Try executing
        try:
            exec_result = await _execute_es_query(
                query_response.elasticsearch_query,
                query_response.visualization_type
            )
        except Exception as exec_err:
            logger.warning(f"First query execution failed, attempting auto-correction: {exec_err}")
            retries = 1

            # Step 3: Refine and retry
            query_response = await query_generator.refine_query(
                original_query=request.query,
                previous_es_query=original_response.elasticsearch_query,
                refinement="Fix the query so it executes successfully",
                error_message=str(exec_err)
            )

            try:
                exec_result = await _execute_es_query(
                    query_response.elasticsearch_query,
                    query_response.visualization_type
                )
            except Exception as retry_err:
                logger.error(f"Retry also failed: {retry_err}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Query failed after auto-correction. Original error: {exec_err}. Retry error: {retry_err}"
                )

        return {
            **exec_result,
            "query_response": query_response.model_dump(),
            "retries": retries,
            "original_query_response": original_response.model_dump() if retries > 0 else None,
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Query-and-execute failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")


async def _execute_es_query(es_query: Dict[str, Any], visualization_type: str) -> Dict[str, Any]:
    """Execute an ES query and return formatted results. Used by query-and-execute endpoint."""
    query = es_query.get("query", {"match_all": {}})
    if "bool" not in query:
        query = {
            "bool": {
                "must": [query],
                "filter": [{"term": {"approval_status": "approved"}}]
            }
        }
    else:
        if "filter" not in query["bool"]:
            query["bool"]["filter"] = []
        query["bool"]["filter"].append({"term": {"approval_status": "approved"}})

    search_body = {
        "size": es_query.get("size", 0),
        "query": query,
        "aggs": es_query.get("aggs", {})
    }

    response = search_service.es.search(index=search_service.index, body=search_body)

    aggregations = response.get("aggregations", {})
    total = response["hits"]["total"]["value"]
    took_ms = response.get("took", 0)

    formatted_aggs = {}
    agg_types = []
    for agg_name, agg_data in aggregations.items():
        agg_type = _classify_aggregation_type(agg_data)
        agg_types.append(agg_type)
        if agg_type == "bucket":
            formatted_agg = _extract_buckets_from_aggregation(agg_data)
            formatted_aggs[agg_name] = formatted_agg if formatted_agg else agg_data
        elif agg_type == "stats":
            formatted_aggs[agg_name] = _extract_stats_as_buckets(agg_data)
        else:
            formatted_aggs[agg_name] = agg_data

    if agg_types and all(t in ("stats", "single_metric") for t in agg_types):
        if visualization_type not in ("metric", "metric_card", "table"):
            visualization_type = "metric_card"

    items = []
    if search_body.get("size", 0) > 0:
        items = [hit["_source"] for hit in response["hits"]["hits"]]

    chain_data = LLMQueryGenerator.extract_result_chain_data(
        es_query,
        {"data": {"aggregations": formatted_aggs}, "total": total}
    )

    return {
        "success": True,
        "data": {
            "items": items,
            "aggregations": formatted_aggs,
            "total": total
        },
        "visualization_type": visualization_type,
        "total": total,
        "execution_time_ms": took_ms,
        "chain_data": chain_data,
    }


@router.get("/schema-docs")
async def get_schema_docs():
    """
    Get schema documentation.

    Returns the comprehensive schema documentation used for LLM context.
    Useful for debugging and understanding available fields.

    Returns:
        Schema documentation as markdown text
    """
    from app.services.schema_documentor import SchemaDocumentor

    return {
        "documentation": SchemaDocumentor.get_schema_documentation(),
        "examples": SchemaDocumentor.get_example_queries()
    }



# Drilldown dimension mapping: after filtering by a field, show breakdown by next dimension
# Note: source, categories, content_type are already keyword type — no .keyword suffix needed
DRILLDOWN_NEXT_DIMENSION = {
    "source": ("categories", "by_category"),
    "source.keyword": ("categories", "by_category"),
    "categories": ("source", "by_source"),
    "categories.keyword": ("source", "by_source"),
    "content_type": ("year", "by_year"),
    "content_type.keyword": ("year", "by_year"),
    "year": ("source", "by_source"),
    "authors.name.keyword": ("year", "by_year"),
    "journal": ("year", "by_year"),
    "journal.keyword": ("year", "by_year"),
}
DEFAULT_DRILLDOWN_DIMENSION = ("source", "by_source")
MAX_DRILLDOWN_DEPTH = 2


# Nested field paths in ES index — term filters on these must be wrapped in nested queries
NESTED_FIELD_PATHS = {"authors"}


def _make_term_filter(field: str, value: str) -> Dict[str, Any]:
    """Create a term filter, wrapping in a nested query if the field is under a nested path."""
    term_clause = {"term": {field: value}}
    for nested_path in NESTED_FIELD_PATHS:
        if field.startswith(f"{nested_path}."):
            return {"nested": {"path": nested_path, "query": term_clause}}
    return term_clause


@router.post("/drilldown")
async def drilldown_query(
    request: DrilldownRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Drill into a specific data point by adding a filter and showing the next dimension.

    Deterministic — no LLM call. Adds a term filter for the clicked value and
    aggregates by the next logical dimension.
    """
    try:
        parent_query = request.parent_es_query
        clicked_field = request.clicked_field
        clicked_key = request.clicked_key
        depth = request.drilldown_depth

        logger.info(f"Drilldown request: field={clicked_field}, key={clicked_key}, depth={depth}")

        # At max depth, return top documents instead of more aggregations
        if depth >= MAX_DRILLDOWN_DEPTH:
            query = parent_query.get("query", {"match_all": {}})
            # Wrap in bool if needed and add clicked filter
            if "bool" not in query:
                query = {"bool": {"must": [query], "filter": []}}
            if "filter" not in query["bool"]:
                query["bool"]["filter"] = []
            query["bool"]["filter"].append(_make_term_filter(clicked_field, clicked_key))
            # Ensure approval_status filter
            query["bool"]["filter"].append({"term": {"approval_status": "approved"}})

            search_body = {
                "size": 20,
                "query": query,
                "_source": ["title", "source", "content_type", "year", "categories", "authors", "ai_confidence", "abstract"],
                "sort": [{"ai_confidence": {"order": "desc"}}]
            }

            response = search_service.es.search(index=search_service.index, body=search_body)
            items = [hit["_source"] for hit in response["hits"]["hits"]]
            total = response["hits"]["total"]["value"]

            return {
                "success": True,
                "data": {
                    "items": items,
                    "aggregations": {},
                    "total": total
                },
                "visualization_type": "table",
                "total": total,
                "execution_time_ms": response.get("took", 0),
                "drilldown_depth": depth + 1,
                "is_max_depth": True
            }

        # Build drilldown query: parent query + new term filter
        query = parent_query.get("query", {"match_all": {}})
        if "bool" not in query:
            query = {"bool": {"must": [query], "filter": []}}
        if "filter" not in query["bool"]:
            query["bool"]["filter"] = []
        query["bool"]["filter"].append(_make_term_filter(clicked_field, clicked_key))
        query["bool"]["filter"].append({"term": {"approval_status": "approved"}})

        # Choose next dimension
        next_field, next_agg_name = DRILLDOWN_NEXT_DIMENSION.get(
            clicked_field, DEFAULT_DRILLDOWN_DIMENSION
        )
        # If next dimension is same as clicked, fall back to default
        if next_field == clicked_field:
            next_field, next_agg_name = DEFAULT_DRILLDOWN_DIMENSION
            if next_field == clicked_field:
                next_field, next_agg_name = ("year", "by_year")

        search_body = {
            "size": 0,
            "query": query,
            "aggs": {
                next_agg_name: {
                    "terms": {"field": next_field, "size": 20}
                }
            }
        }

        response = search_service.es.search(index=search_service.index, body=search_body)
        aggregations = response.get("aggregations", {})
        total = response["hits"]["total"]["value"]

        # Format aggregations
        formatted_aggs = {}
        for agg_name, agg_data in aggregations.items():
            formatted_agg = _extract_buckets_from_aggregation(agg_data)
            formatted_aggs[agg_name] = formatted_agg if formatted_agg else agg_data

        return {
            "success": True,
            "data": {
                "items": [],
                "aggregations": formatted_aggs,
                "total": total
            },
            "visualization_type": "bar_chart",
            "total": total,
            "execution_time_ms": response.get("took", 0),
            "drilldown_depth": depth + 1,
            "drilldown_field": next_field,
            "is_max_depth": False
        }

    except Exception as e:
        logger.error(f"Drilldown query failed: {e}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Failed to execute drilldown: {str(e)}")


@router.post("/temporal-share")
async def temporal_share_analysis(
    request: AnalyticalRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Analyze how top entities' publication share evolves over time."""
    try:
        time_window = tuple(request.time_window) if request.time_window and len(request.time_window) == 2 else None
        result = await analytical_executor.execute_temporal_share_analysis(
            entity_field=request.entity_field,
            time_field=request.time_field,
            time_window=time_window,
            top_n=request.top_n,
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Temporal share analysis failed: {e}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Temporal share analysis failed: {str(e)}")


@router.post("/surge-detection")
async def surge_detection(
    request: AnalyticalRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Detect publication surges and correlate with OHDSI milestone events."""
    try:
        result = await analytical_executor.detect_publication_surges(
            time_field=request.time_field,
            entity_field=request.entity_field if request.entity_field != "authors.affiliation.keyword" else None,
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Surge detection failed: {e}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Surge detection failed: {str(e)}")


@router.post("/concentration")
async def concentration_analysis(
    request: AnalyticalRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Analyze distribution concentration using Gini coefficient."""
    try:
        time_window = tuple(request.time_window) if request.time_window and len(request.time_window) == 2 else None
        result = await analytical_executor.analyze_distribution_concentration(
            entity_field=request.entity_field,
            time_field=request.time_field,
            time_window=time_window,
        )
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Concentration analysis failed: {e}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Concentration analysis failed: {str(e)}")


# Helper functions for live query execution

def _classify_aggregation_type(agg_data: Dict[str, Any]) -> str:
    """Classify an ES aggregation response as bucket, stats, or single_metric."""
    if "buckets" in agg_data:
        return "bucket"
    # Check for nested structure that contains buckets
    for value in agg_data.values():
        if isinstance(value, dict) and "buckets" in value:
            return "bucket"
    # Stats aggregation returns count, min, max, avg, sum
    stats_keys = {"count", "min", "max", "avg", "sum"}
    if stats_keys.issubset(set(agg_data.keys())):
        return "stats"
    # Extended stats
    if "std_deviation" in agg_data or "variance" in agg_data:
        return "stats"
    # Single metric (value key)
    if "value" in agg_data and len(agg_data) <= 2:
        return "single_metric"
    # Percentiles
    if "values" in agg_data:
        return "stats"
    return "bucket"


def _extract_stats_as_buckets(agg_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert a stats/metric aggregation into bucket-like format for visualization."""
    # Percentiles have a "values" dict
    if "values" in agg_data and isinstance(agg_data["values"], dict):
        return [
            {"key": f"p{k}", "value": v}
            for k, v in agg_data["values"].items()
            if v is not None
        ]
    # Stats aggregation: count, min, max, avg, sum
    display_keys = ["count", "min", "max", "avg", "sum"]
    result = []
    for k in display_keys:
        if k in agg_data and agg_data[k] is not None:
            val = agg_data[k]
            # Round floats for display
            if isinstance(val, float):
                val = round(val, 4)
            result.append({"key": k, "value": val})
    # Extended stats extras
    for k in ["std_deviation", "variance"]:
        if k in agg_data and agg_data[k] is not None:
            result.append({"key": k, "value": round(agg_data[k], 4)})
    # Single metric fallback
    if not result and "value" in agg_data:
        val = agg_data["value"]
        if isinstance(val, float):
            val = round(val, 4)
        result.append({"key": "value", "value": val})
    return result


def _extract_buckets_from_aggregation(agg_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Recursively extract buckets from aggregation data, preserving nested sub-aggregations.

    Handles nested aggregations where buckets may be nested within sub-aggregations.
    For example, nested aggregations have structure:
      {"doc_count": N, "nested_agg_name": {"buckets": [...]}}

    Returns buckets with their sub-aggregations included, allowing hierarchical visualization.
    """
    # Direct buckets at this level
    if "buckets" in agg_data:
        result_buckets = []
        for bucket in agg_data["buckets"]:
            bucket_obj = {
                "key": _format_bucket_key(bucket["key"]),
                "value": bucket["doc_count"]
            }

            # Check for sub-aggregations within this bucket
            for key, value in bucket.items():
                # Skip standard bucket fields
                if key in ["key", "doc_count", "doc_count_error_upper_bound", "key_as_string", "doc_count_error_upper_bound", "sum_other_doc_count"]:
                    continue

                # Recursively extract sub-aggregations
                if isinstance(value, dict):
                    # Check if this is an ES aggregation response with buckets
                    if "buckets" in value:
                        # Extract the buckets array and flatten it
                        sub_buckets = _extract_buckets_from_aggregation(value)
                        if sub_buckets:
                            # Add sub-aggregation with a descriptive name
                            bucket_obj[key] = sub_buckets
                    else:
                        # Try recursive extraction for nested structures
                        sub_buckets = _extract_buckets_from_aggregation(value)
                        if sub_buckets:
                            bucket_obj[key] = sub_buckets

            result_buckets.append(bucket_obj)

        return result_buckets

    # Search for buckets in nested sub-aggregations (for nested/filter aggregations)
    for key, value in agg_data.items():
        if isinstance(value, dict):
            # Skip metadata fields
            if key in ["doc_count", "doc_count_error_upper_bound", "sum_other_doc_count"]:
                continue

            # Recursively search for buckets
            buckets = _extract_buckets_from_aggregation(value)
            if buckets:
                return buckets

    return None


def _format_bucket_key(key: Any) -> str:
    """
    Format bucket keys for display.

    Handles special cases like date timestamps.
    """
    # Check if key is a date timestamp (milliseconds since epoch)
    if isinstance(key, (int, float)) and key > 1000000000000:  # Likely a millisecond timestamp
        from datetime import datetime
        try:
            # Convert milliseconds to seconds and create datetime
            dt = datetime.fromtimestamp(key / 1000)
            # Format as readable date
            return dt.strftime("%Y-%m-%d")
        except:
            pass

    return str(key)
