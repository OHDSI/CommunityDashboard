'use client';

/**
 * Graphic Walker Wrapper
 *
 * Transforms ES query result data into flat tabular format for Graphic Walker
 * interactive exploration. Handles both aggregation buckets and document items.
 */

import { useMemo } from 'react';
import { GraphicWalker } from '@kanaries/graphic-walker';
import type { QueryExecutionResult } from '@/lib/analytics-api';

interface GraphicWalkerWrapperProps {
  result: QueryExecutionResult;
}

interface FieldSpec {
  fid: string;
  name: string;
  analyticType: 'dimension' | 'measure';
  semanticType: 'nominal' | 'quantitative' | 'ordinal' | 'temporal';
}

function inferFieldSpec(key: string, sampleValue: any): FieldSpec {
  const lowerKey = key.toLowerCase();

  // Temporal fields
  if (lowerKey === 'year' || lowerKey.includes('date') || lowerKey.includes('month')) {
    return {
      fid: key,
      name: formatFieldName(key),
      analyticType: 'dimension',
      semanticType: 'temporal',
    };
  }

  // Numeric fields → measures
  if (typeof sampleValue === 'number' && !lowerKey.includes('id')) {
    return {
      fid: key,
      name: formatFieldName(key),
      analyticType: 'measure',
      semanticType: 'quantitative',
    };
  }

  // Everything else → dimension
  return {
    fid: key,
    name: formatFieldName(key),
    analyticType: 'dimension',
    semanticType: 'nominal',
  };
}

function formatFieldName(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Transform aggregation data into flat rows for Graphic Walker.
 * Handles simple buckets [{key, value}] and nested aggregations.
 */
function transformAggregationsToRows(aggregations: Record<string, any>): any[] {
  const rows: any[] = [];
  const firstAgg = Object.values(aggregations)[0];

  if (!Array.isArray(firstAgg)) return rows;

  for (const bucket of firstAgg) {
    const row: any = { name: bucket.key, count: bucket.value || bucket.doc_count || 0 };

    // Handle nested sub-aggregations
    for (const [subKey, subValue] of Object.entries(bucket)) {
      if (subKey === 'key' || subKey === 'value' || subKey === 'doc_count') continue;
      if (Array.isArray(subValue)) {
        // Nested buckets — flatten: create a row per sub-bucket
        for (const subBucket of subValue as any[]) {
          rows.push({
            name: bucket.key,
            [subKey]: subBucket.key,
            count: subBucket.value || subBucket.doc_count || 0,
          });
        }
      }
    }

    // If no nested data was expanded, add the main row
    if (!Object.keys(bucket).some(k => k !== 'key' && k !== 'value' && Array.isArray(bucket[k]))) {
      rows.push(row);
    }
  }

  return rows;
}

/**
 * Transform document items into flat rows, handling nested objects.
 */
function transformItemsToRows(items: any[]): any[] {
  return items.map(item => {
    const row: any = {};
    for (const [key, value] of Object.entries(item)) {
      if (key === 'embedding' || key.startsWith('_')) continue;
      if (Array.isArray(value)) {
        // Flatten arrays to comma-separated strings
        if (value.length > 0 && typeof value[0] === 'object') {
          row[key] = value.map((v: any) => v.name || v.key || JSON.stringify(v)).join(', ');
        } else {
          row[key] = value.join(', ');
        }
      } else if (typeof value === 'object' && value !== null) {
        // Skip complex nested objects
        continue;
      } else {
        row[key] = value;
      }
    }
    return row;
  });
}

export default function GraphicWalkerWrapper({ result }: GraphicWalkerWrapperProps) {
  const { data: tableData, fields } = useMemo(() => {
    let rows: any[] = [];

    // Prefer aggregation data, fall back to items
    const hasAggregations = Object.keys(result.data.aggregations).length > 0;
    const hasItems = result.data.items.length > 0;

    if (hasAggregations) {
      rows = transformAggregationsToRows(result.data.aggregations);
    }

    if (rows.length === 0 && hasItems) {
      rows = transformItemsToRows(result.data.items);
    }

    if (rows.length === 0) {
      return { data: [], fields: [] };
    }

    // Generate field specs from first row
    const sampleRow = rows[0];
    const fieldSpecs: FieldSpec[] = Object.keys(sampleRow).map(key =>
      inferFieldSpec(key, sampleRow[key])
    );

    return { data: rows, fields: fieldSpecs };
  }, [result]);

  if (tableData.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        <p>No data available for interactive exploration</p>
      </div>
    );
  }

  return (
    <div className="w-full min-h-[500px]">
      <GraphicWalker
        data={tableData}
        fields={fields}
        dark="light"
      />
    </div>
  );
}
