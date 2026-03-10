'use client';

/**
 * Analytics Page
 *
 * LLM-powered natural language query interface for OHDSI content exploration.
 * Users can ask questions in plain English and get visualizations of the data.
 */

import { useState, useRef, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { Send, Loader2, AlertCircle, TrendingUp, BarChart3, Info, Code, Sparkles, ChevronRight, Activity, BarChart2, PieChart as PieChartIcon, MousePointerClick } from 'lucide-react';

const GraphicWalkerWrapper = dynamic(
  () => import('@/components/analytics/graphic-walker-wrapper'),
  { ssr: false, loading: () => <div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div> }
);
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { DataVisualizer, NarrativeViz } from '@/components/analytics/data-visualizer';
import {
  analyticsAPI,
  type QueryGenerationResponse,
  type QueryExecutionResult,
  type ChainData,
  type ConversationEntry,
} from '@/lib/analytics-api';

interface QueryHistoryItem {
  id: string;
  query: string;
  timestamp: Date;
  response?: QueryGenerationResponse;
  result?: QueryExecutionResult;
  error?: string;
}

interface DrilldownBreadcrumb {
  label: string;
  field: string;
  value: string;
  response: QueryGenerationResponse;
  result: QueryExecutionResult;
  esQuery: Record<string, any>;
}

export default function AnalyticsPage() {
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentResponse, setCurrentResponse] = useState<QueryGenerationResponse | null>(null);
  const [currentResult, setCurrentResult] = useState<QueryExecutionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [drilldownStack, setDrilldownStack] = useState<DrilldownBreadcrumb[]>([]);
  const [isDrilling, setIsDrilling] = useState(false);
  const [lastChainData, setLastChainData] = useState<ChainData | null>(null);
  const [queryRetries, setQueryRetries] = useState(0);
  const [wasChained, setWasChained] = useState(false);
  const [analyticalResult, setAnalyticalResult] = useState<any>(null);
  const [analyticalLoading, setAnalyticalLoading] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);

  // Example queries to show users
  const exampleQueries = [
    "Show me publications by year",
    "Top 10 authors by publication count",
    "Count articles by source",
    "Average ML score by category",
    "Show videos with high engagement",
    "Publications about OMOP CDM in 2024"
  ];

  const handleSubmitQuery = async (queryText: string) => {
    if (!queryText.trim()) return;

    setIsLoading(true);
    setError(null);
    setCurrentResponse(null);
    setCurrentResult(null);
    setDrilldownStack([]);

    try {
      // Build conversation history from recent successful queries
      const conversationHistory: ConversationEntry[] = history
        .filter(h => h.result?.success)
        .slice(0, 3)
        .map(h => {
          const aggKeys = h.result?.data?.aggregations
            ? Object.values(h.result.data.aggregations)?.[0]
            : null;
          const topKeys = Array.isArray(aggKeys)
            ? aggKeys.slice(0, 3).map((b: any) => b.key).join(', ')
            : 'n/a';
          return {
            query: h.query,
            summary: `${h.result?.total ?? 0} results, viz: ${h.result?.visualization_type ?? '?'}, top: ${topKeys}`,
          };
        });

      // Track whether we're passing chain data for this query
      const chainDataForQuery = lastChainData || undefined;

      // Generate and execute query with chain data and conversation context (server-side auto-retry)
      const { queryResponse, executionResult, retries } = await analyticsAPI.queryAndExecute(
        queryText,
        undefined,
        chainDataForQuery,
        conversationHistory.length > 0 ? conversationHistory : undefined,
      );

      setWasChained(!!chainDataForQuery && chainDataForQuery.bucket_keys.length > 0);

      // Update state
      setCurrentResponse(queryResponse);
      setCurrentResult(executionResult);

      // Store chain data for next query
      if (executionResult.chain_data) {
        setLastChainData(executionResult.chain_data);
      }

      // Track if query was auto-corrected
      setQueryRetries(retries || 0);

      // Add to history
      const historyItem: QueryHistoryItem = {
        id: Date.now().toString(),
        query: queryText,
        timestamp: new Date(),
        response: queryResponse,
        result: executionResult
      };
      setHistory(prev => [historyItem, ...prev]);

      // Get follow-up suggestions
      if (executionResult.success) {
        try {
          const { suggestions: newSuggestions } = await analyticsAPI.suggestFollowUp(
            queryText,
            {
              total: executionResult.total,
              visualization_type: executionResult.visualization_type,
              aggregations: executionResult.data.aggregations
            }
          );
          setSuggestions(newSuggestions);
        } catch (err) {
          console.error('Failed to get suggestions:', err);
        }
      }

      setQuery('');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);

      // Add error to history
      const historyItem: QueryHistoryItem = {
        id: Date.now().toString(),
        query: queryText,
        timestamp: new Date(),
        error: errorMessage
      };
      setHistory(prev => [historyItem, ...prev]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmitQuery(query);
    }
  };

  const handleExampleClick = (example: string) => {
    setQuery(example);
    handleSubmitQuery(example);
  };

  const handleDrilldown = async (clickedKey: string, clickedField: string) => {
    if (!currentResponse || !currentResult) return;
    setIsDrilling(true);

    try {
      // Save current state to stack
      const breadcrumb: DrilldownBreadcrumb = {
        label: drilldownStack.length === 0 ? 'Root' : `${clickedField.replace('.keyword', '')}: ${clickedKey}`,
        field: clickedField,
        value: clickedKey,
        response: currentResponse,
        result: currentResult,
        esQuery: currentResponse.elasticsearch_query,
      };

      const parentEsQuery = currentResponse.elasticsearch_query;
      const depth = drilldownStack.length;

      const drilldownResult = await analyticsAPI.drilldown(
        parentEsQuery,
        clickedField,
        clickedKey,
        depth
      );

      // Push current state and update display with drilldown result
      setDrilldownStack(prev => [...prev, breadcrumb]);

      // Create a synthetic response for the drilldown
      const drilldownResponse: QueryGenerationResponse = {
        elasticsearch_query: parentEsQuery,
        visualization_type: drilldownResult.visualization_type,
        explanation: `Drilled into ${clickedField.replace('.keyword', '')}: "${clickedKey}"`,
        warnings: [],
        estimated_complexity: 'low',
      };

      setCurrentResponse(drilldownResponse);
      setCurrentResult(drilldownResult);
    } catch (err) {
      console.error('Drilldown failed:', err);
      setError(err instanceof Error ? err.message : 'Drilldown failed');
    } finally {
      setIsDrilling(false);
    }
  };

  const handleDrillUp = (index: number) => {
    if (index < 0 || index >= drilldownStack.length) return;

    const target = drilldownStack[index];
    setCurrentResponse(target.response);
    setCurrentResult(target.result);
    setDrilldownStack(prev => prev.slice(0, index));
  };

  const handleResetDrilldown = () => {
    if (drilldownStack.length > 0) {
      const root = drilldownStack[0];
      setCurrentResponse(root.response);
      setCurrentResult(root.result);
      setDrilldownStack([]);
    }
  };

  const handlePrebuiltAnalysis = async (analysisType: string) => {
    setAnalyticalLoading(analysisType);
    setAnalyticalResult(null);
    setError(null);
    try {
      let result;
      switch (analysisType) {
        case 'temporal-share':
          result = await analyticsAPI.temporalShare();
          break;
        case 'surge-detection':
          result = await analyticsAPI.surgeDetection();
          break;
        case 'concentration':
          result = await analyticsAPI.concentration();
          break;
      }
      setAnalyticalResult({ type: analysisType, ...result });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setAnalyticalLoading(null);
    }
  };

  const getComplexityColor = (complexity: string) => {
    switch (complexity) {
      case 'low': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'high': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-gradient-to-r from-primary to-primary/85 rounded-lg">
            <Sparkles className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-4xl font-semibold">Analytics Explorer</h1>
        </div>
        <p className="text-muted-foreground text-lg">
          Ask questions in natural language and explore OHDSI content data with AI-powered insights
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Query Area - 2/3 width on large screens */}
        <div className="lg:col-span-2 space-y-6">
          {/* Query Input Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Ask a Question
              </CardTitle>
              <CardDescription>
                Type your question in plain English, and AI will generate and execute the query
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Input
                  ref={inputRef}
                  type="text"
                  placeholder="e.g., Show me publications by year..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  disabled={isLoading}
                  className="flex-1"
                />
                <Button
                  onClick={() => handleSubmitQuery(query)}
                  disabled={isLoading || !query.trim()}
                >
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>

              {/* Example Queries */}
              {!currentResponse && !isLoading && (
                <div className="mt-4">
                  <p className="text-sm text-muted-foreground mb-2">Try an example:</p>
                  <div className="flex flex-wrap gap-2">
                    {exampleQueries.map((example, idx) => (
                      <Badge
                        key={idx}
                        variant="outline"
                        className="cursor-pointer hover:bg-accent"
                        onClick={() => handleExampleClick(example)}
                      >
                        {example}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Pre-built Analyses */}
          {!currentResponse && !isLoading && !analyticalResult && (
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground mb-3">Pre-built Analyses</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <Card
                  className="cursor-pointer hover:border-primary transition-colors"
                  onClick={() => handlePrebuiltAnalysis('temporal-share')}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Activity className="h-4 w-4 text-primary" />
                      <span className="font-medium text-sm">Publication Share Over Time</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      How top organizations&apos; publication share evolves year over year
                    </p>
                  </CardContent>
                </Card>
                <Card
                  className="cursor-pointer hover:border-primary transition-colors"
                  onClick={() => handlePrebuiltAnalysis('surge-detection')}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <BarChart2 className="h-4 w-4 text-primary" />
                      <span className="font-medium text-sm">Publication Surge Detection</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Find publication spikes correlated with OHDSI milestones
                    </p>
                  </CardContent>
                </Card>
                <Card
                  className="cursor-pointer hover:border-primary transition-colors"
                  onClick={() => handlePrebuiltAnalysis('concentration')}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <PieChartIcon className="h-4 w-4 text-primary" />
                      <span className="font-medium text-sm">Distribution Concentration</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Gini analysis of author/organization concentration over time
                    </p>
                  </CardContent>
                </Card>
              </div>
            </div>
          )}

          {/* Analytical Loading */}
          {analyticalLoading && (
            <Card>
              <CardContent className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary mr-3" />
                <span className="text-muted-foreground">Running {analyticalLoading} analysis...</span>
              </CardContent>
            </Card>
          )}

          {/* Analytical Result Display */}
          {analyticalResult && !analyticalLoading && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">
                    {analyticalResult.type === 'temporal-share' && 'Publication Share Over Time'}
                    {analyticalResult.type === 'surge-detection' && 'Publication Surge Detection'}
                    {analyticalResult.type === 'concentration' && 'Distribution Concentration'}
                  </CardTitle>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setAnalyticalResult(null)}
                  >
                    Clear
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Narrative */}
                {analyticalResult.narrative && (
                  <NarrativeViz narrative={analyticalResult.narrative} />
                )}

                {/* Charts */}
                <div className="border rounded-lg p-4">
                  {analyticalResult.type === 'temporal-share' && analyticalResult.chart_data && (
                    <DataVisualizer
                      data={{
                        items: [],
                        aggregations: { temporal: analyticalResult.chart_data },
                        total: 0,
                      }}
                      visualizationType="stacked_area"
                    />
                  )}
                  {analyticalResult.type === 'surge-detection' && analyticalResult.chart_data?.timeline && (
                    <DataVisualizer
                      data={{
                        items: [],
                        aggregations: {
                          timeline: analyticalResult.chart_data.timeline.map((d: any) => ({
                            key: d.year,
                            value: d.publications,
                          })),
                        },
                        total: 0,
                      }}
                      visualizationType="line_chart"
                    />
                  )}
                  {analyticalResult.type === 'concentration' && analyticalResult.chart_data?.gini_trend && (
                    <DataVisualizer
                      data={{
                        items: [],
                        aggregations: {
                          gini: analyticalResult.chart_data.gini_trend.map((d: any) => ({
                            key: d.year,
                            value: d.gini,
                          })),
                        },
                        total: 0,
                      }}
                      visualizationType="line_chart"
                    />
                  )}
                </div>

                {/* Surge details */}
                {analyticalResult.type === 'surge-detection' && analyticalResult.surges?.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold">Detected Surges</h4>
                    {analyticalResult.surges.map((surge: any, idx: number) => (
                      <div key={idx} className="flex items-center gap-2 text-sm">
                        <Badge variant="outline" className="bg-amber-50 text-amber-800">
                          {surge.year}
                        </Badge>
                        <span>+{surge.increase_pct}% increase</span>
                        {surge.event !== 'No known event' && (
                          <Badge variant="secondary">{surge.event}</Badge>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Concentration trend */}
                {analyticalResult.type === 'concentration' && analyticalResult.concentration_trend && (
                  <div className="text-sm">
                    <span className="font-medium">Trend: </span>
                    <Badge variant={
                      analyticalResult.concentration_trend === 'increasing' ? 'destructive' :
                      analyticalResult.concentration_trend === 'decreasing' ? 'default' : 'secondary'
                    }>
                      {analyticalResult.concentration_trend}
                    </Badge>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Results Display */}
          {currentResponse && currentResult && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Results</CardTitle>
                  <div className="flex items-center gap-2">
                    <Badge className={getComplexityColor(currentResponse.estimated_complexity)}>
                      {currentResponse.estimated_complexity} complexity
                    </Badge>
                    <Badge variant="outline">
                      {currentResult.total} results in {currentResult.execution_time_ms}ms
                    </Badge>
                    {queryRetries > 0 && (
                      <Badge variant="secondary" className="bg-amber-100 text-amber-800">
                        Auto-corrected
                      </Badge>
                    )}
                    {wasChained && (
                      <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                        Chained
                      </Badge>
                    )}
                  </div>
                </div>
                <CardDescription>{currentResponse.explanation}</CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="visualization" className="w-full">
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="visualization">
                      <BarChart3 className="h-4 w-4 mr-2" />
                      Visualization
                    </TabsTrigger>
                    <TabsTrigger value="explore">
                      <MousePointerClick className="h-4 w-4 mr-2" />
                      Explore
                    </TabsTrigger>
                    <TabsTrigger value="data">
                      <Info className="h-4 w-4 mr-2" />
                      Data
                    </TabsTrigger>
                    <TabsTrigger value="query">
                      <Code className="h-4 w-4 mr-2" />
                      Query
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="visualization" className="mt-4">
                    {/* Drilldown Breadcrumbs */}
                    {drilldownStack.length > 0 && (
                      <div className="flex items-center gap-1 mb-3 text-sm flex-wrap">
                        <button
                          className="text-primary hover:underline font-medium"
                          onClick={handleResetDrilldown}
                        >
                          Root
                        </button>
                        {drilldownStack.map((crumb, idx) => (
                          <span key={idx} className="flex items-center gap-1">
                            <ChevronRight className="h-3 w-3 text-muted-foreground" />
                            <button
                              className="text-primary hover:underline"
                              onClick={() => handleDrillUp(idx)}
                            >
                              {crumb.field.replace('.keyword', '')}: {crumb.value}
                            </button>
                          </span>
                        ))}
                        <ChevronRight className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">(current)</span>
                      </div>
                    )}

                    <div className="min-h-[400px] border rounded-lg p-4 relative">
                      {isDrilling && (
                        <div className="absolute inset-0 bg-background/50 flex items-center justify-center z-10 rounded-lg">
                          <Loader2 className="h-8 w-8 animate-spin text-primary" />
                        </div>
                      )}
                      <DataVisualizer
                        data={currentResult.data}
                        visualizationType={currentResult.visualization_type || currentResponse.visualization_type}
                        onDrilldown={handleDrilldown}
                      />
                    </div>
                  </TabsContent>

                  <TabsContent value="explore" className="mt-4">
                    <div className="min-h-[500px] border rounded-lg p-4">
                      <GraphicWalkerWrapper result={currentResult} />
                    </div>
                  </TabsContent>

                  <TabsContent value="data" className="mt-4">
                    <div className="space-y-4">
                      {/* Aggregations */}
                      {Object.keys(currentResult.data.aggregations).length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold mb-2">Aggregations</h4>
                          <pre className="bg-muted p-4 rounded-lg overflow-auto text-xs">
                            {JSON.stringify(currentResult.data.aggregations, null, 2)}
                          </pre>
                        </div>
                      )}

                      {/* Items */}
                      {currentResult.data.items.length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold mb-2">
                            Items ({currentResult.data.items.length})
                          </h4>
                          <div className="space-y-2">
                            {currentResult.data.items.slice(0, 5).map((item, idx) => (
                              <div key={idx} className="border rounded p-3 text-sm">
                                <div className="font-medium">{item.title || item.id}</div>
                                {item.source && (
                                  <Badge variant="outline" className="mt-1">
                                    {item.source}
                                  </Badge>
                                )}
                              </div>
                            ))}
                            {currentResult.data.items.length > 5 && (
                              <p className="text-sm text-muted-foreground text-center py-2">
                                + {currentResult.data.items.length - 5} more items
                              </p>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </TabsContent>

                  <TabsContent value="query" className="mt-4">
                    <div className="space-y-4">
                      {/* Visualization Type */}
                      <div>
                        <h4 className="text-sm font-semibold mb-2">Visualization Type</h4>
                        <Badge>{currentResponse.visualization_type}</Badge>
                      </div>

                      {/* Elasticsearch Query */}
                      <div>
                        <h4 className="text-sm font-semibold mb-2">Elasticsearch Query</h4>
                        <pre className="bg-muted p-4 rounded-lg overflow-auto text-xs max-h-[400px]">
                          {JSON.stringify(currentResponse.elasticsearch_query, null, 2)}
                        </pre>
                      </div>

                      {/* Warnings */}
                      {currentResponse.warnings.length > 0 && (
                        <Alert>
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>
                            <div className="space-y-1">
                              {currentResponse.warnings.map((warning, idx) => (
                                <div key={idx}>• {warning}</div>
                              ))}
                            </div>
                          </AlertDescription>
                        </Alert>
                      )}
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          )}

          {/* Follow-up Suggestions */}
          {suggestions.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Suggested Follow-up Questions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {suggestions.map((suggestion, idx) => (
                    <Button
                      key={idx}
                      variant="outline"
                      className="w-full justify-start text-left h-auto py-3"
                      onClick={() => handleExampleClick(suggestion)}
                    >
                      {suggestion}
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar - Query History */}
        <div className="lg:col-span-1">
          <Card className="sticky top-4">
            <CardHeader>
              <CardTitle className="text-sm">Query History</CardTitle>
              <CardDescription>Your recent queries</CardDescription>
            </CardHeader>
            <CardContent>
              {history.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No queries yet. Try asking a question!
                </p>
              ) : (
                <div className="space-y-3 max-h-[600px] overflow-y-auto">
                  {history.map((item) => (
                    <div
                      key={item.id}
                      className="border rounded-lg p-3 cursor-pointer hover:bg-accent transition-colors"
                      onClick={() => {
                        if (item.response && item.result) {
                          setCurrentResponse(item.response);
                          setCurrentResult(item.result);
                        }
                      }}
                    >
                      <div className="text-sm font-medium line-clamp-2 mb-1">
                        {item.query}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {item.timestamp.toLocaleTimeString()}
                      </div>
                      {item.error && (
                        <Badge variant="destructive" className="mt-2 text-xs">
                          Error
                        </Badge>
                      )}
                      {item.response && (
                        <Badge className={`mt-2 text-xs ${getComplexityColor(item.response.estimated_complexity)}`}>
                          {item.response.estimated_complexity}
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
