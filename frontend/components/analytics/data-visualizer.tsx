'use client';

/**
 * Data Visualizer Component
 *
 * Renders appropriate visualization based on data type and visualization_type.
 * Supports: bar charts, line charts, pie charts, tables, metrics, scatter plots.
 */

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface DataVisualizerProps {
  data: {
    items: any[];
    aggregations: Record<string, any>;
    total: number;
  };
  visualizationType: string;
  title?: string;
  onDrilldown?: (clickedKey: string, clickedField: string) => void;
}

// Colors for charts (OHDSI brand colors)
const COLORS = [
  '#0066cc', // Primary blue
  '#3399ff', // Light blue
  '#004499', // Dark blue
  '#ffcc00', // Gold
  '#059669', // Emerald
  '#d97706', // Amber
  '#dc2626', // Red
  '#7c3aed', // Purple
];

/**
 * Transform nested aggregations into multi-series format for Recharts
 * Example: [{key: "2010", by_org: [{key: "Stanford", value: 5}]}]
 * Becomes: [{name: "2010", Stanford: 5, Columbia: 3}, ...]
 */
function transformNestedAggregations(nestedData: any[], topN: number = 10) {
  // Find the nested aggregation key (e.g., "by_organization", "top_topics", "by_category")
  const nestedKey = Object.keys(nestedData[0] || {}).find(
    key => key !== 'key' && key !== 'value' && Array.isArray(nestedData[0][key])
  );

  if (!nestedKey) return [];

  // Determine if this is organization data (needs cleaning) or other data (use as-is)
  const isOrganizationData = nestedKey.includes('organization') || nestedKey.includes('affiliation');

  // Collect all unique series names and their total counts
  const seriesCounts: Record<string, number> = {};
  nestedData.forEach(bucket => {
    const nestedBuckets = bucket[nestedKey] || [];
    nestedBuckets.forEach((nested: any) => {
      const seriesName = isOrganizationData
        ? cleanOrganizationName(nested.key)
        : cleanSeriesName(nested.key);
      seriesCounts[seriesName] = (seriesCounts[seriesName] || 0) + nested.value;
    });
  });

  // Get top N series by total count
  const topSeries = Object.entries(seriesCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, topN)
    .map(([name]) => name);

  // Transform data into multi-series format
  const transformedData = nestedData.map(bucket => {
    const dataPoint: any = {
      name: bucket.key
    };

    const nestedBuckets = bucket[nestedKey] || [];
    nestedBuckets.forEach((nested: any) => {
      const seriesName = isOrganizationData
        ? cleanOrganizationName(nested.key)
        : cleanSeriesName(nested.key);
      if (topSeries.includes(seriesName)) {
        dataPoint[seriesName] = nested.value;
      }
    });

    return dataPoint;
  });

  return { data: transformedData, series: topSeries };
}

/**
 * Clean up general series names (keywords, categories, etc.)
 */
function cleanSeriesName(name: string): string {
  if (!name) return 'Unknown';

  // Truncate if too long
  if (name.length > 40) {
    return name.substring(0, 37) + '...';
  }

  return name;
}

/**
 * Clean up organization names for better display
 */
function cleanOrganizationName(name: string): string {
  if (!name) return 'Unknown';

  // Remove email addresses
  name = name.replace(/\s*[\w\.-]+@[\w\.-]+\.\w+\s*/g, '');

  // Extract just the institution name (before first comma)
  const parts = name.split(',');
  let cleaned = parts[0].trim();

  // Remove common suffixes
  cleaned = cleaned
    .replace(/\s+(USA?|UK|Netherlands|Germany|France|Spain|Italy|China|Japan)\.?$/i, '')
    .replace(/\s+\d{5}(-\d{4})?$/, '') // Remove ZIP codes
    .trim();

  // Truncate if still too long
  if (cleaned.length > 50) {
    cleaned = cleaned.substring(0, 47) + '...';
  }

  return cleaned || 'Unknown';
}

/**
 * Derive the ES field name from an aggregation key name.
 * e.g., "by_source" -> "source.keyword", "by_year" -> "year"
 */
function deriveFieldFromAggName(aggName: string): string {
  // Note: source, categories, content_type are already keyword type — no .keyword suffix
  const mapping: Record<string, string> = {
    by_source: 'source',
    by_category: 'categories',
    by_content_type: 'content_type',
    by_year: 'year',
    by_month: 'published_date',
    by_journal: 'journal',
    by_channel: 'channel_name',
    top_authors: 'authors.name.keyword',
    top_journals: 'journal',
    top_channels: 'channel_name',
    organizations: 'authors.affiliation.keyword',
  };
  if (mapping[aggName]) return mapping[aggName];
  // Fallback: strip "by_" prefix, use as-is (most fields are already keyword type)
  const stripped = aggName.replace(/^by_/, '');
  return stripped;
}

export function DataVisualizer({ data, visualizationType, title, onDrilldown }: DataVisualizerProps) {
  // Derive the field from the first aggregation key
  const firstAggName = Object.keys(data.aggregations)[0] || '';
  const clickedField = deriveFieldFromAggName(firstAggName);

  const handleBarClick = onDrilldown
    ? (entry: any) => {
        const key = entry?.name || entry?.activeLabel;
        if (key) onDrilldown(key, clickedField);
      }
    : undefined;

  // Transform aggregation data for charts
  const prepareChartData = () => {
    const { aggregations } = data;
    const firstAgg = Object.values(aggregations)[0];

    if (Array.isArray(firstAgg)) {
      // Check if this is hierarchical/nested data
      const hasNestedAggs = firstAgg.some(item =>
        Object.keys(item).some(key =>
          key !== 'key' && key !== 'value' && Array.isArray(item[key])
        )
      );

      if (hasNestedAggs) {
        // Transform nested aggregations into multi-series format
        return transformNestedAggregations(firstAgg);
      }

      // Array of {key, value} objects (flat structure)
      return firstAgg.map(item => ({
        name: item.key || item.name || 'Unknown',
        value: item.value || item.doc_count || item.count || 0
      }));
    } else if (firstAgg && typeof firstAgg === 'object' && 'buckets' in firstAgg) {
      // Elasticsearch aggregation format
      return firstAgg.buckets.map((bucket: any) => ({
        name: bucket.key_as_string || bucket.key || 'Unknown',
        value: bucket.doc_count
      }));
    }

    return [];
  };

  const renderVisualization = () => {
    const chartData = prepareChartData();

    switch (visualizationType.toLowerCase()) {
      case 'bar_chart':
      case 'bar':
        return <BarChartViz chartData={chartData} onBarClick={handleBarClick} />;

      case 'line_chart':
      case 'line':
        return <LineChartViz chartData={chartData} onDotClick={handleBarClick} />;

      case 'pie_chart':
      case 'pie':
        return <PieChartViz data={prepareChartData()} onSliceClick={handleBarClick} />;

      case 'table':
        return <TableViz items={data.items} />;

      case 'stacked_area':
        return <StackedAreaChartViz chartData={chartData} />;

      case 'metric':
      case 'metric_card':
        return <MetricViz data={data} label={title || 'Total'} />;

      default:
        return (
          <div className="flex items-center justify-center h-64 text-muted-foreground">
            <div className="text-center">
              <p>Visualization type &quot;{visualizationType}&quot; not yet implemented</p>
              <p className="text-sm mt-2">Available: bar_chart, line_chart, pie_chart, table, metric</p>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="w-full">
      {title && (
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
      )}
      {onDrilldown && visualizationType !== 'table' && visualizationType !== 'metric_card' && (
        <p className="text-xs text-muted-foreground mb-2">Click a data point to drill down</p>
      )}
      {renderVisualization()}
    </div>
  );
}

// Bar Chart Component
function BarChartViz({ chartData, onBarClick }: { chartData: any; onBarClick?: (entry: any) => void }) {
  // Handle both simple and multi-series data
  const isMultiSeries = chartData && typeof chartData === 'object' && 'series' in chartData;
  const data = isMultiSeries ? chartData.data : chartData;
  const series = isMultiSeries ? chartData.series : null;

  if (!data || data.length === 0) {
    return <EmptyState message="No data available for bar chart" />;
  }

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart
        data={data}
        margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
        onClick={onBarClick ? (e) => { if (e?.activePayload?.[0]) onBarClick(e.activePayload[0].payload); } : undefined}
        style={onBarClick ? { cursor: 'pointer' } : undefined}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="name"
          angle={-45}
          textAnchor="end"
          height={100}
          tick={{ fill: '#6b7280', fontSize: 12 }}
        />
        <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} />
        <Tooltip
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '6px'
          }}
        />
        <Legend />
        {series ? (
          // Multi-series: one bar per series
          series.map((seriesName: string, idx: number) => (
            <Bar
              key={seriesName}
              dataKey={seriesName}
              name={seriesName}
              fill={COLORS[idx % COLORS.length]}
              radius={[4, 4, 0, 0]}
            />
          ))
        ) : (
          // Single series
          <Bar dataKey="value" fill={COLORS[0]} radius={[4, 4, 0, 0]} />
        )}
      </BarChart>
    </ResponsiveContainer>
  );
}

// Line Chart Component
function LineChartViz({ chartData, onDotClick }: { chartData: any; onDotClick?: (entry: any) => void }) {
  // Handle both simple and multi-series data
  const isMultiSeries = chartData && typeof chartData === 'object' && 'series' in chartData;
  const data = isMultiSeries ? chartData.data : chartData;
  const series = isMultiSeries ? chartData.series : null;

  if (!data || data.length === 0) {
    return <EmptyState message="No data available for line chart" />;
  }

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart
        data={data}
        margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
        onClick={onDotClick ? (e) => { if (e?.activePayload?.[0]) onDotClick(e.activePayload[0].payload); } : undefined}
        style={onDotClick ? { cursor: 'pointer' } : undefined}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="name"
          angle={-45}
          textAnchor="end"
          height={100}
          tick={{ fill: '#6b7280', fontSize: 12 }}
        />
        <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} />
        <Tooltip
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '6px'
          }}
        />
        <Legend />
        {series ? (
          // Multi-series: one line per series
          series.map((seriesName: string, idx: number) => (
            <Line
              key={seriesName}
              type="monotone"
              dataKey={seriesName}
              name={seriesName}
              stroke={COLORS[idx % COLORS.length]}
              strokeWidth={2}
              dot={{ fill: COLORS[idx % COLORS.length], r: 4 }}
              activeDot={{ r: 6 }}
            />
          ))
        ) : (
          // Single series
          <Line
            type="monotone"
            dataKey="value"
            stroke={COLORS[0]}
            strokeWidth={2}
            dot={{ fill: COLORS[0], r: 4 }}
            activeDot={{ r: 6 }}
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}

// Pie Chart Component
function PieChartViz({ data, onSliceClick }: { data: Array<{ name: string; value: number }>; onSliceClick?: (entry: any) => void }) {
  if (!data || data.length === 0) {
    return <EmptyState message="No data available for pie chart" />;
  }

  const RADIAN = Math.PI / 180;
  const renderCustomizedLabel = ({
    cx,
    cy,
    midAngle,
    innerRadius,
    outerRadius,
    percent
  }: any) => {
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        fontSize={12}
        fontWeight="bold"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <div className="flex flex-col md:flex-row items-center justify-center gap-8">
      <ResponsiveContainer width="100%" height={400}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomizedLabel}
            outerRadius={120}
            fill="#8884d8"
            dataKey="value"
            onClick={onSliceClick ? (_: any, index: number) => onSliceClick(data[index]) : undefined}
            style={onSliceClick ? { cursor: 'pointer' } : undefined}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '6px'
            }}
          />
        </PieChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="space-y-2">
        {data.map((entry, index) => (
          <div
            key={index}
            className={`flex items-center gap-2 ${onSliceClick ? 'cursor-pointer hover:bg-accent rounded px-1' : ''}`}
            onClick={onSliceClick ? () => onSliceClick(entry) : undefined}
          >
            <div
              className="w-4 h-4 rounded"
              style={{ backgroundColor: COLORS[index % COLORS.length] }}
            />
            <span className="text-sm">
              {entry.name} ({entry.value})
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Table Component
function TableViz({ items }: { items: any[] }) {
  if (!items || items.length === 0) {
    return <EmptyState message="No data available for table" />;
  }

  // Get all unique keys from items
  const keys = Array.from(
    new Set(items.flatMap(item => Object.keys(item)))
  ).filter(key => !key.startsWith('_') && key !== 'embedding'); // Filter out internal fields

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b">
            {keys.slice(0, 6).map((key) => (
              <th
                key={key}
                className="text-left p-3 text-sm font-semibold text-muted-foreground"
              >
                {key}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.slice(0, 10).map((item, idx) => (
            <tr key={idx} className="border-b hover:bg-accent">
              {keys.slice(0, 6).map((key) => (
                <td key={key} className="p-3 text-sm">
                  {renderCellValue(item[key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {items.length > 10 && (
        <div className="text-center py-3 text-sm text-muted-foreground">
          Showing 10 of {items.length} items
        </div>
      )}
    </div>
  );
}

// Metric Card Component
function MetricViz({ data, label }: { data: { items: any[]; aggregations: Record<string, any>; total: number }; label: string }) {
  const firstAgg = Object.values(data.aggregations)[0];

  // If aggregations contain stats-like array (from _extract_stats_as_buckets), render each stat
  if (Array.isArray(firstAgg) && firstAgg.length > 0 && firstAgg[0]?.key) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {firstAgg.map((stat: { key: string; value: number }, idx: number) => (
          <Card key={idx} className="p-6 text-center">
            <div className="text-3xl font-bold text-primary mb-1">
              {typeof stat.value === 'number' ? stat.value.toLocaleString() : stat.value}
            </div>
            <div className="text-sm text-muted-foreground capitalize">{stat.key}</div>
          </Card>
        ))}
      </div>
    );
  }

  // Single value metric (e.g., cardinality)
  if (firstAgg && typeof firstAgg === 'object' && 'value' in firstAgg) {
    return (
      <Card className="p-8 text-center">
        <div className="text-5xl font-bold text-primary mb-2">
          {typeof firstAgg.value === 'number' ? firstAgg.value.toLocaleString() : firstAgg.value}
        </div>
        <div className="text-lg text-muted-foreground">{label}</div>
      </Card>
    );
  }

  // Fallback to total
  return (
    <Card className="p-8 text-center">
      <div className="text-5xl font-bold text-primary mb-2">
        {data.total.toLocaleString()}
      </div>
      <div className="text-lg text-muted-foreground">{label}</div>
    </Card>
  );
}

// Stacked Area Chart Component
function StackedAreaChartViz({ chartData }: { chartData: any }) {
  const isMultiSeries = chartData && typeof chartData === 'object' && 'series' in chartData;
  const data = isMultiSeries ? chartData.data : chartData;
  const series = isMultiSeries ? chartData.series : null;

  if (!data || data.length === 0) {
    return <EmptyState message="No data available for stacked area chart" />;
  }

  // If not multi-series, try to extract series from data keys
  const derivedSeries = series || (data.length > 0
    ? Object.keys(data[0]).filter(k => k !== 'name' && k !== 'year' && k !== 'value')
    : []);

  if (derivedSeries.length === 0) {
    return <EmptyState message="No series data available for stacked area chart" />;
  }

  const xKey = 'year' in (data[0] || {}) ? 'year' : 'name';

  return (
    <ResponsiveContainer width="100%" height={400}>
      <AreaChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey={xKey}
          tick={{ fill: '#6b7280', fontSize: 12 }}
        />
        <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} />
        <Tooltip
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '6px'
          }}
        />
        <Legend />
        {derivedSeries.map((s: string, idx: number) => (
          <Area
            key={s}
            type="monotone"
            dataKey={s}
            name={cleanSeriesName(s)}
            stackId="1"
            stroke={COLORS[idx % COLORS.length]}
            fill={COLORS[idx % COLORS.length]}
            fillOpacity={0.6}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}

// Narrative Text Component for analytical results
export function NarrativeViz({ narrative }: { narrative: string }) {
  if (!narrative) return null;

  // Simple markdown-like rendering: **bold**, *italic*, \n for line breaks
  const parts = narrative.split(/(\*\*[^*]+\*\*|\*[^*]+\*|\n)/g);

  return (
    <div className="prose prose-sm max-w-none p-4 bg-muted/50 rounded-lg border text-sm leading-relaxed">
      {parts.map((part, i) => {
        if (part === '\n') return <br key={i} />;
        if (part.startsWith('**') && part.endsWith('**'))
          return <strong key={i}>{part.slice(2, -2)}</strong>;
        if (part.startsWith('*') && part.endsWith('*'))
          return <em key={i}>{part.slice(1, -1)}</em>;
        if (part.startsWith('- '))
          return <span key={i} className="block ml-4">{part}</span>;
        return <span key={i}>{part}</span>;
      })}
    </div>
  );
}

// Empty State Component
function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-64 text-muted-foreground">
      <p>{message}</p>
    </div>
  );
}

// Helper function to render cell values
function renderCellValue(value: any): React.ReactNode {
  if (value === null || value === undefined) {
    return <span className="text-muted-foreground">—</span>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-muted-foreground">—</span>;
    if (value.length > 3) {
      return (
        <div className="flex flex-wrap gap-1">
          {value.slice(0, 3).map((v, i) => (
            <Badge key={i} variant="outline" className="text-xs">
              {String(v)}
            </Badge>
          ))}
          <Badge variant="outline" className="text-xs">
            +{value.length - 3}
          </Badge>
        </div>
      );
    }
    return (
      <div className="flex flex-wrap gap-1">
        {value.map((v, i) => (
          <Badge key={i} variant="outline" className="text-xs">
            {String(v)}
          </Badge>
        ))}
      </div>
    );
  }

  if (typeof value === 'object') {
    return <span className="text-muted-foreground text-xs">[Object]</span>;
  }

  if (typeof value === 'boolean') {
    return value ? '✓' : '✗';
  }

  const stringValue = String(value);
  if (stringValue.length > 100) {
    return <span className="line-clamp-2" title={stringValue}>{stringValue}</span>;
  }

  return stringValue;
}
