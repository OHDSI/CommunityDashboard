/**
 * Analytics API Client
 *
 * Client for interacting with the LLM-powered analytics API endpoints.
 */

// Strip trailing /api from NEXT_PUBLIC_API_URL since analytics routes use /api/analytics prefix
const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? '').replace(/\/api\/?$/, '');

export interface QueryGenerationResponse {
  elasticsearch_query: Record<string, any>;
  visualization_type: string;
  explanation: string;
  warnings: string[];
  estimated_complexity: 'low' | 'medium' | 'high';
}

export interface ChainData {
  result_type: 'aggregation' | 'documents';
  primary_agg_field: string | null;
  bucket_keys: string[];
  bucket_values: number[];
  total_docs: number;
  filters_applied: Record<string, any>;
}

export interface ConversationEntry {
  query: string;
  summary: string;
}

export interface QueryExecutionResult {
  success: boolean;
  data: {
    items: any[];
    aggregations: Record<string, any>;
    total: number;
  };
  visualization_type: string;
  total: number;
  execution_time_ms: number;
  chain_data?: ChainData;
  drilldown_depth?: number;
  drilldown_field?: string;
  is_max_depth?: boolean;
}

export interface SuggestionsResponse {
  suggestions: string[];
}

export interface SchemaDocsResponse {
  documentation: string;
  examples: Array<{
    natural_language: string;
    intent: string;
    graphql: string;
    visualization: string;
  }>;
}

/**
 * Analytics API Client
 */
export class AnalyticsAPI {
  private baseUrl: string;
  private token: string | null;

  constructor(token?: string) {
    this.baseUrl = `${API_BASE_URL}/api/analytics`;
    this.token = token || null;
  }

  /**
   * Set authentication token
   */
  setToken(token: string) {
    this.token = token;
  }

  /**
   * Get headers for API requests
   */
  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    return headers;
  }

  /**
   * Generate a query from natural language
   */
  async generateQuery(
    query: string,
    context?: Record<string, any>,
    previousResultSummary?: ChainData,
    conversationHistory?: ConversationEntry[]
  ): Promise<QueryGenerationResponse> {
    const response = await fetch(`${this.baseUrl}/generate-query`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        query,
        context,
        previous_result_summary: previousResultSummary || undefined,
        conversation_history: conversationHistory || undefined,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to generate query');
    }

    return response.json();
  }

  /**
   * Refine an existing query
   */
  async refineQuery(
    originalQuery: string,
    previousElasticsearchQuery: Record<string, any>,
    refinement: string,
    errorMessage?: string
  ): Promise<QueryGenerationResponse> {
    const response = await fetch(`${this.baseUrl}/refine-query`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        original_query: originalQuery,
        previous_elasticsearch_query: previousElasticsearchQuery,
        refinement,
        error_message: errorMessage,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to refine query');
    }

    return response.json();
  }

  /**
   * Execute an Elasticsearch query
   */
  async executeQuery(
    elasticsearchQuery: Record<string, any>,
    visualizationType: string,
    size: number = 100,
    offset: number = 0
  ): Promise<QueryExecutionResult> {
    const response = await fetch(`${this.baseUrl}/execute-query`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        elasticsearch_query: elasticsearchQuery,
        visualization_type: visualizationType,
        size,
        offset
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to execute query');
    }

    return response.json();
  }

  /**
   * Get follow-up query suggestions
   */
  async suggestFollowUp(
    query: string,
    resultsSummary: Record<string, any>
  ): Promise<SuggestionsResponse> {
    const response = await fetch(`${this.baseUrl}/suggest-followup`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        query,
        results_summary: resultsSummary,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to generate suggestions');
    }

    return response.json();
  }

  /**
   * Get schema documentation
   */
  async getSchemaDocs(): Promise<SchemaDocsResponse> {
    const response = await fetch(`${this.baseUrl}/schema-docs`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch schema documentation');
    }

    return response.json();
  }

  /**
   * Drilldown into a specific data point
   */
  async drilldown(
    parentEsQuery: Record<string, any>,
    clickedField: string,
    clickedKey: string,
    drilldownDepth: number = 0
  ): Promise<QueryExecutionResult> {
    const response = await fetch(`${this.baseUrl}/drilldown`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        parent_es_query: parentEsQuery,
        clicked_field: clickedField,
        clicked_key: clickedKey,
        drilldown_depth: drilldownDepth,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to execute drilldown');
    }

    return response.json();
  }

  /**
   * Generate and execute query in one call with server-side auto-retry
   */
  async queryAndExecute(
    naturalLanguageQuery: string,
    context?: Record<string, any>,
    previousResultSummary?: ChainData,
    conversationHistory?: ConversationEntry[]
  ): Promise<{
    queryResponse: QueryGenerationResponse;
    executionResult: QueryExecutionResult;
    retries?: number;
  }> {
    const response = await fetch(`${this.baseUrl}/query-and-execute`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        query: naturalLanguageQuery,
        context,
        previous_result_summary: previousResultSummary || undefined,
        conversation_history: conversationHistory || undefined,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to execute query');
    }

    const result = await response.json();

    // Extract the query response from the combined result
    const queryResponse: QueryGenerationResponse = result.query_response;
    const executionResult: QueryExecutionResult = {
      success: result.success,
      data: result.data,
      visualization_type: result.visualization_type,
      total: result.total,
      execution_time_ms: result.execution_time_ms,
      chain_data: result.chain_data,
    };

    return {
      queryResponse,
      executionResult,
      retries: result.retries,
    };
  }

  /**
   * Pre-built analysis: Temporal share evolution
   */
  async temporalShare(
    entityField: string = 'authors.affiliation.keyword',
    timeField: string = 'year',
    topN: number = 10,
    timeWindow?: [number, number]
  ): Promise<any> {
    const response = await fetch(`${this.baseUrl}/temporal-share`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        entity_field: entityField,
        time_field: timeField,
        top_n: topN,
        time_window: timeWindow || null,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Temporal share analysis failed');
    }

    return response.json();
  }

  /**
   * Pre-built analysis: Publication surge detection
   */
  async surgeDetection(
    timeField: string = 'year',
    entityField?: string
  ): Promise<any> {
    const response = await fetch(`${this.baseUrl}/surge-detection`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        time_field: timeField,
        entity_field: entityField || 'authors.affiliation.keyword',
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Surge detection failed');
    }

    return response.json();
  }

  /**
   * Pre-built analysis: Distribution concentration (Gini)
   */
  async concentration(
    entityField: string = 'authors.affiliation.keyword',
    timeField: string = 'year',
    timeWindow?: [number, number]
  ): Promise<any> {
    const response = await fetch(`${this.baseUrl}/concentration`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        entity_field: entityField,
        time_field: timeField,
        time_window: timeWindow || null,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Concentration analysis failed');
    }

    return response.json();
  }
}

// Export singleton instance
export const analyticsAPI = new AnalyticsAPI();

// Export helper to create authenticated instance
export function createAnalyticsAPI(token: string): AnalyticsAPI {
  return new AnalyticsAPI(token);
}
