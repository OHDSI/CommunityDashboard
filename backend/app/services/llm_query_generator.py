"""
LLM Query Generator Service

Converts natural language queries to GraphQL/Elasticsearch queries
using GPT-5-nano with comprehensive schema context.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.services.schema_documentor import SchemaDocumentor
from app.config import settings


logger = logging.getLogger(__name__)


class QueryFilter(BaseModel):
    """Represents a single filter condition."""
    field: str
    operator: str  # eq, ne, gt, gte, lt, lte, in, range, exists, nested
    value: Any
    boost: Optional[float] = None


class AggregationSpec(BaseModel):
    """Specification for an aggregation."""
    name: str
    type: str  # terms, date_histogram, stats, percentiles, nested, cardinality
    field: str
    size: Optional[int] = 10
    interval: Optional[str] = None  # For date_histogram
    nested_path: Optional[str] = None  # For nested aggregations
    sub_aggs: Optional[Dict[str, 'AggregationSpec']] = None


class AnalyticalQuerySpec(BaseModel):
    """Specification for complex analytical queries."""
    query_type: str = Field(..., description="temporal_share_analysis, surge_detection, distribution_concentration, regional_comparison, normalized_productivity")
    entity_field: str = Field(..., description="Field to analyze (e.g., authors.affiliation.keyword)")
    time_field: str = Field("year", description="Time dimension field")
    time_window: Optional[List[int]] = Field(None, description="[start_year, end_year]")
    top_n: int = Field(10, description="Number of top entities to analyze")
    group_by: Optional[str] = Field(None, description="Field to group/color results by (e.g., categories, content_type)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Additional query-specific parameters")


class IntermediateRepresentation(BaseModel):
    """Structured representation of query intent."""
    intent: str = Field(..., description="Type of query: filter, aggregate, time_series, nested_aggregation, comparison, analytical, etc.")
    filters: list[QueryFilter] = Field(default_factory=list, description="Filter conditions")
    aggregations: list[AggregationSpec] = Field(default_factory=list, description="Aggregation specifications")
    fields: list[str] = Field(default_factory=list, description="Fields to retrieve")
    sort: Optional[Dict[str, str]] = Field(None, description="Sort specification")
    size: int = Field(100, description="Number of results to return")
    visualization_type: str = Field(..., description="Suggested chart type: bar_chart, line_chart, pie_chart, table, scatter, heatmap, metric, mixed, narrative, analytical")
    explanation: str = Field(..., description="User-friendly explanation")
    nested_handling: Optional[str] = Field(None, description="Strategy for nested data")
    requires_nested_query: bool = Field(False, description="Whether nested query syntax is needed")

    # NEW: For complex analytical queries
    analytical_query: Optional[AnalyticalQuerySpec] = Field(None, description="Specification for multi-step analytical queries")


class ElasticsearchQueryResponse(BaseModel):
    """Response from direct Elasticsearch query generation."""
    elasticsearch_query: Dict[str, Any] = Field(..., description="Complete Elasticsearch query DSL")
    visualization_type: str = Field(..., description="Chart type: bar_chart, line_chart, pie_chart, table, metric")
    explanation: str = Field(..., description="User-friendly explanation of what the query does")


class QueryGenerationResponse(BaseModel):
    """Complete response from query generation."""
    elasticsearch_query: Dict[str, Any]
    visualization_type: str
    explanation: str
    warnings: list[str] = Field(default_factory=list)
    estimated_complexity: str = Field("medium", description="low, medium, high")


class LLMQueryGenerator:
    """Generate queries from natural language using GPT-4o."""

    def __init__(self):
        """Initialize the query generator."""
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not configured - analytics features will be disabled")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-5-nano"  # Using GPT-5-nano for improved performance
        self.documentor = SchemaDocumentor()

    async def generate_query(
        self,
        natural_language_query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> QueryGenerationResponse:
        """
        Convert natural language to query specification.

        Args:
            natural_language_query: User's question in natural language
            context: Optional context (previous queries, user preferences, etc.)

        Returns:
            Complete query generation response with IR, GraphQL, and explanation

        Raises:
            ValueError: If query generation fails
        """
        if not self.client:
            raise ValueError("OpenAI API key not configured - analytics features are disabled")

        try:
            # Classify intent and build targeted system prompt
            intents = SchemaDocumentor.classify_query_intent(natural_language_query)
            system_prompt = SchemaDocumentor.get_contextual_system_prompt(intents)

            # Build user message
            user_message = self._build_user_message(natural_language_query, context)

            logger.info(f"Generating query for: {natural_language_query} (intents: {intents}, prompt_chars: {len(system_prompt)})")

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},  # Ensure JSON response
                reasoning_effort="medium"  # Medium reasoning for better quality
            )

            # Parse response
            result_text = response.choices[0].message.content
            result_json = json.loads(result_text)

            # Validate response structure
            if "elasticsearch_query" not in result_json:
                raise ValueError("LLM response missing 'elasticsearch_query' field")
            if "visualization_type" not in result_json:
                raise ValueError("LLM response missing 'visualization_type' field")

            # Create response object
            response_obj = QueryGenerationResponse(
                elasticsearch_query=result_json["elasticsearch_query"],
                visualization_type=result_json["visualization_type"],
                explanation=result_json.get("explanation", "Query generated successfully"),
                warnings=self._validate_es_query(result_json["elasticsearch_query"])
            )

            # Estimate complexity based on query structure
            response_obj.estimated_complexity = self._estimate_es_complexity(result_json["elasticsearch_query"])

            logger.info(f"ES query generated successfully: {response_obj.visualization_type} ({response_obj.estimated_complexity} complexity)")
            return response_obj

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"Query generation failed: {e}")
            raise ValueError(f"Failed to generate query: {str(e)}")

    def _build_user_message(
        self,
        query: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build the user message with query, context, chain data, and conversation history."""
        message = f"User Query: {query}\n\n"

        if context:
            # Standard context
            if context.get("preferred_visualization"):
                message += f"- Preferred visualization: {context['preferred_visualization']}\n"
            if context.get("date_range"):
                message += f"- Date range: {context['date_range']}\n"

            # Chain data from previous query results
            if context.get("chain_data"):
                chain = context["chain_data"]
                message += "\n## Previous Query Results (use for filtering)\n"
                message += f"The previous query aggregated by field: `{chain['reference_field']}`\n"
                message += f"Top results: {json.dumps(chain['values_to_inject'][:15])}\n"
                if chain.get("total_docs"):
                    message += f"Total documents matched: {chain['total_docs']}\n"
                if chain.get("instruction"):
                    message += f"\n**Instruction**: {chain['instruction']}\n"

            # Conversation history (last 3 queries)
            if context.get("conversation_history"):
                message += "\n## Recent Query History\n"
                for entry in context["conversation_history"][-3:]:
                    message += f"- Q: {entry.get('query', '?')} -> {entry.get('summary', 'no summary')}\n"

        message += "\nPlease generate the query specification in the requested JSON format."
        return message

    def _validate_es_query(self, es_query: Dict[str, Any]) -> list[str]:
        """
        Validate Elasticsearch query and return warnings.

        Args:
            es_query: Elasticsearch query dict

        Returns:
            List of warning messages
        """
        warnings = []

        # Check for aggregations
        aggs = es_query.get("aggs", {})

        # Check for too many aggregations
        if len(aggs) > 5:
            warnings.append("Query includes many top-level aggregations which may be slow")

        # Check for nested aggregations
        def count_nested_aggs(agg_dict, depth=0):
            """Recursively count nested aggregations."""
            count = 0
            if depth > 3:
                warnings.append("Deep nesting of aggregations may impact performance")

            for agg_name, agg_spec in agg_dict.items():
                if isinstance(agg_spec, dict):
                    if "nested" in agg_spec:
                        count += 1
                    if "aggs" in agg_spec:
                        count += count_nested_aggs(agg_spec["aggs"], depth + 1)
            return count

        nested_count = count_nested_aggs(aggs)
        if nested_count > 2:
            warnings.append(f"Multiple nested aggregations ({nested_count}) may be slow")

        # Validate field names (basic check)
        known_fields = {
            "id", "title", "abstract", "content", "source", "content_type",
            "authors", "published_date", "year", "ml_score", "ai_confidence",
            "categories", "keywords", "citations", "metrics", "approval_status",
            "journal", "channel_name", "pmid", "video_id", "owner", "repo_name"
        }

        def check_fields(obj):
            """Recursively check field names in query."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == "field" and isinstance(value, str):
                        base_field = value.split(".")[0]
                        if base_field not in known_fields:
                            warnings.append(f"Unknown field: {value}")
                    check_fields(value)
            elif isinstance(obj, list):
                for item in obj:
                    check_fields(item)

        check_fields(es_query)

        return warnings

    def _estimate_es_complexity(self, es_query: Dict[str, Any]) -> str:
        """
        Estimate Elasticsearch query complexity.

        Args:
            es_query: Elasticsearch query dict

        Returns:
            Complexity level: low, medium, high
        """
        score = 0

        # Count query clauses
        query = es_query.get("query", {})
        if "bool" in query:
            bool_query = query["bool"]
            score += len(bool_query.get("must", [])) * 1
            score += len(bool_query.get("filter", [])) * 1
            score += len(bool_query.get("should", [])) * 2

        # Count and weight aggregations
        def score_aggs(agg_dict, depth=0):
            """Recursively score aggregations."""
            agg_score = 0
            for agg_name, agg_spec in agg_dict.items():
                if isinstance(agg_spec, dict):
                    # Nested aggs are more expensive
                    if "nested" in agg_spec:
                        agg_score += 5
                    elif "date_histogram" in agg_spec:
                        agg_score += 3
                    elif "terms" in agg_spec:
                        agg_score += 2
                    else:
                        agg_score += 1

                    # Sub-aggregations
                    if "aggs" in agg_spec:
                        agg_score += score_aggs(agg_spec["aggs"], depth + 1) * (1.5 ** depth)

            return agg_score

        aggs = es_query.get("aggs", {})
        score += score_aggs(aggs)

        # Determine complexity
        if score < 5:
            return "low"
        elif score < 15:
            return "medium"
        else:
            return "high"

    async def refine_query(
        self,
        original_query: str,
        previous_es_query: Dict[str, Any],
        refinement: str,
        error_message: Optional[str] = None
    ) -> QueryGenerationResponse:
        """
        Refine an existing query based on user feedback or errors.

        Args:
            original_query: Original natural language query
            previous_es_query: Previous Elasticsearch query
            refinement: User's refinement request or error details
            error_message: Optional error message if query failed

        Returns:
            Refined query generation response
        """
        if not self.client:
            raise ValueError("OpenAI API key not configured - analytics features are disabled")

        intents = SchemaDocumentor.classify_query_intent(original_query)
        system_prompt = SchemaDocumentor.get_contextual_system_prompt(intents)

        user_message = f"""Original Query: {original_query}

Previous Elasticsearch Query:
{json.dumps(previous_es_query, indent=2)}

Refinement Request: {refinement}
"""

        if error_message:
            user_message += f"\nError Encountered: {error_message}\n\nPlease fix the query to avoid this error."

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                reasoning_effort="medium"  # Medium reasoning for refinements
            )

            result_json = json.loads(response.choices[0].message.content)

            if "elasticsearch_query" not in result_json:
                raise ValueError("LLM response missing 'elasticsearch_query' field")

            return QueryGenerationResponse(
                elasticsearch_query=result_json["elasticsearch_query"],
                visualization_type=result_json.get("visualization_type", "table"),
                explanation=result_json.get("explanation", "Query refined successfully"),
                warnings=self._validate_es_query(result_json["elasticsearch_query"]),
                estimated_complexity=self._estimate_es_complexity(result_json["elasticsearch_query"])
            )

        except Exception as e:
            logger.error(f"Query refinement failed: {e}")
            raise ValueError(f"Failed to refine query: {str(e)}")

    # --- Query Chaining ---

    @staticmethod
    def extract_result_chain_data(
        es_query: Dict[str, Any],
        execution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract chainable data from query results for follow-up queries.

        Walks the ES query to find the primary aggregation field, then extracts
        bucket keys and values from the result. This data can be passed to the
        next query to enable chaining (e.g., "now show those authors over time").

        Returns:
            Dict with result_type, primary_agg_field, bucket_keys, bucket_values,
            total_docs, and filters_applied.
        """
        chain_data: Dict[str, Any] = {
            "result_type": "documents",
            "primary_agg_field": None,
            "bucket_keys": [],
            "bucket_values": [],
            "total_docs": execution_result.get("total", 0),
            "filters_applied": {},
        }

        # Extract the primary aggregation field from the ES query
        aggs = es_query.get("aggs", {})
        if not aggs:
            return chain_data

        chain_data["result_type"] = "aggregation"

        # Walk the aggregation tree to find the leaf terms/date_histogram field
        def find_primary_agg_field(agg_dict: Dict) -> Optional[str]:
            for agg_name, agg_spec in agg_dict.items():
                if not isinstance(agg_spec, dict):
                    continue
                # Check for terms aggregation
                if "terms" in agg_spec:
                    return agg_spec["terms"].get("field")
                if "date_histogram" in agg_spec:
                    return agg_spec["date_histogram"].get("field")
                # Check for nested → inner aggs
                if "nested" in agg_spec and "aggs" in agg_spec:
                    result = find_primary_agg_field(agg_spec["aggs"])
                    if result:
                        return result
                # Check for sub-aggs at top level
                if "aggs" in agg_spec:
                    inner = find_primary_agg_field(agg_spec["aggs"])
                    if inner:
                        return inner
            return None

        chain_data["primary_agg_field"] = find_primary_agg_field(aggs)

        # Extract bucket keys/values from the execution result aggregations
        result_aggs = execution_result.get("data", {}).get("aggregations", {})
        if not result_aggs:
            result_aggs = execution_result.get("aggregations", {})

        def extract_buckets(agg_data) -> List[Dict[str, Any]]:
            """Recursively find the first list of buckets."""
            if isinstance(agg_data, list):
                return agg_data
            if isinstance(agg_data, dict):
                if "buckets" in agg_data:
                    return agg_data["buckets"]
                for v in agg_data.values():
                    result = extract_buckets(v)
                    if result:
                        return result
            return []

        buckets = extract_buckets(result_aggs)
        for bucket in buckets[:20]:  # Cap at 20
            if isinstance(bucket, dict):
                key = bucket.get("key")
                value = bucket.get("doc_count", bucket.get("value"))
                if key is not None:
                    chain_data["bucket_keys"].append(str(key))
                if value is not None:
                    chain_data["bucket_values"].append(value)

        # Extract filters from the query
        query = es_query.get("query", {})
        bool_query = query.get("bool", {})
        for clause_type in ["filter", "must"]:
            for clause in bool_query.get(clause_type, []):
                if isinstance(clause, dict):
                    if "term" in clause:
                        for field, val in clause["term"].items():
                            chain_data["filters_applied"][field] = val
                    elif "terms" in clause:
                        for field, val in clause["terms"].items():
                            chain_data["filters_applied"][field] = val
        # Also check direct term/terms at query root
        if "term" in query:
            for field, val in query["term"].items():
                chain_data["filters_applied"][field] = val

        return chain_data

    CHAIN_KEYWORDS = [
        "those", "them", "these authors", "these organizations",
        "that list", "the same", "from above", "previous",
        "from the last query", "by those", "for those", "from those",
        "their ", "the top ",
    ]

    @staticmethod
    def detect_chain_intent(
        query: str,
        previous_chain_data: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Detect if a query references previous results for chaining.

        Returns None if no chaining detected, otherwise returns chain context
        with the reference field, values to inject, and an instruction for the LLM.
        """
        if not previous_chain_data or not previous_chain_data.get("bucket_keys"):
            return None

        query_lower = query.lower()
        ref_field = previous_chain_data.get("primary_agg_field", "")
        keys = previous_chain_data["bucket_keys"]

        # Explicit chain detection
        explicit = any(kw in query_lower for kw in LLMQueryGenerator.CHAIN_KEYWORDS)

        if not explicit:
            return None

        # Build human-readable field label
        field_label = ref_field.replace(".keyword", "").replace("authors.", "").replace(".", " ")

        return {
            "chain_type": "explicit",
            "reference_field": ref_field,
            "values_to_inject": keys,
            "instruction": (
                f"The user is referring to results from their previous query. "
                f"The previous query returned these top {field_label} values: {json.dumps(keys[:15])}. "
                f"Use these values as a filter in the new query (e.g., terms filter on '{ref_field}')."
            ),
        }

    async def suggest_follow_up(
        self,
        query: str,
        results_summary: Dict[str, Any]
    ) -> list[str]:
        """
        Suggest follow-up queries based on results.

        Args:
            query: Original query
            results_summary: Summary of query results (counts, aggregations, etc.)

        Returns:
            List of suggested follow-up questions
        """
        if not self.client:
            raise ValueError("OpenAI API key not configured - analytics features are disabled")

        prompt = f"""Based on this query and results, suggest 3-5 interesting follow-up questions:

Original Query: {query}

Results Summary:
{json.dumps(results_summary, indent=2)}

Suggest questions that would provide additional insights or drill down into interesting patterns."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data analysis expert. Suggest insightful follow-up questions."},
                    {"role": "user", "content": prompt}
                ],
                reasoning_effort="minimal"  # Minimal reasoning for faster responses
            )

            # Parse suggestions from response
            suggestions_text = response.choices[0].message.content
            suggestions = [
                line.strip("- ").strip()
                for line in suggestions_text.split("\n")
                if line.strip() and line.strip().startswith(("-", "•", "1.", "2.", "3.", "4.", "5."))
            ]

            return suggestions[:5]

        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            return []
