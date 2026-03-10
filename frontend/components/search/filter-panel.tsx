'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

interface FilterOption {
  key: string
  doc_count: number
}

interface FilterSection {
  title: string
  field: string
  options: FilterOption[]
}

interface FilterPanelProps {
  filters: Record<string, any>
  onChange: (filters: Record<string, any>) => void
  aggregations?: Record<string, any>
  className?: string
}

// Static content types to show even when filtered
const CONTENT_TYPES = [
  { key: 'article', label: 'Articles' },
  { key: 'video', label: 'Videos' },
  { key: 'repository', label: 'Repositories' },
  { key: 'discussion', label: 'Discussions' },
  { key: 'documentation', label: 'Documentation' },
]

export function FilterPanel({
  filters,
  onChange,
  aggregations,
  className
}: FilterPanelProps) {
  // Default to expanded - use 'content_type' to match field name
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['content_type', 'categories'])
  )

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev)
      if (next.has(section)) {
        next.delete(section)
      } else {
        next.add(section)
      }
      return next
    })
  }

  const handleFilterChange = (field: string, value: string, checked: boolean) => {
    const currentValues = filters[field] || []
    let newValues: string[]
    
    if (checked) {
      newValues = [...currentValues, value]
    } else {
      newValues = currentValues.filter((v: string) => v !== value)
    }
    
    const newFilters = { ...filters }
    if (newValues.length > 0) {
      newFilters[field] = newValues
    } else {
      delete newFilters[field]
    }
    
    onChange(newFilters)
  }

  const clearFilters = () => {
    onChange({})
  }

  // Build filter sections - use static content types merged with aggregation counts
  const filterSections: FilterSection[] = []

  // Always show all content types, merge with aggregation counts when available
  const contentTypeAggBuckets = aggregations?.content_types?.buckets || []
  const contentTypeOptions = CONTENT_TYPES.map(ct => {
    const aggBucket = contentTypeAggBuckets.find((b: FilterOption) => b.key === ct.key)
    return {
      key: ct.key,
      doc_count: aggBucket?.doc_count || 0
    }
  })

  filterSections.push({
    title: 'Content Type',
    field: 'content_type',
    options: contentTypeOptions
  })

  if (aggregations?.categories?.buckets) {
    filterSections.push({
      title: 'Categories',
      field: 'categories',
      options: aggregations.categories.buckets
    })
  }

  const hasActiveFilters = Object.keys(filters).length > 0

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Filters</h3>
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearFilters}
            className="h-auto p-0 text-xs"
          >
            Clear all
          </Button>
        )}
      </div>

      {filterSections.map((section) => (
        <div key={section.field} className="border-t pt-4">
          <button
            className="flex w-full items-center justify-between text-left"
            onClick={() => toggleSection(section.field)}
          >
            <span className="text-sm font-medium">{section.title}</span>
            {expandedSections.has(section.field) ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </button>
          
          {expandedSections.has(section.field) && (
            <div className="mt-3 space-y-2">
              {section.options.slice(0, 10).map((option) => {
                const isChecked = filters[section.field]?.includes(option.key)
                return (
                  <div key={option.key} className="flex items-center space-x-2">
                    <Checkbox
                      id={`${section.field}-${option.key}`}
                      checked={isChecked}
                      onCheckedChange={(checked) => 
                        handleFilterChange(section.field, option.key, checked as boolean)
                      }
                    />
                    <Label
                      htmlFor={`${section.field}-${option.key}`}
                      className="flex-1 text-sm font-normal cursor-pointer capitalize"
                    >
                      {/* Use label from CONTENT_TYPES if available, otherwise capitalize key */}
                      {section.field === 'content_type'
                        ? CONTENT_TYPES.find(ct => ct.key === option.key)?.label || option.key
                        : option.key}
                      <span className="ml-1 text-xs text-muted-foreground">
                        ({option.doc_count})
                      </span>
                    </Label>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      ))}
      
      {/* Date Range Filter */}
      <div className="border-t pt-4">
        <span className="text-sm font-medium">Date Range</span>
        <div className="mt-3 space-y-2">
          <Button 
            variant={filters.dateRange === 'last7days' ? 'default' : 'outline'} 
            size="sm" 
            className="w-full justify-start"
            onClick={() => {
              const sevenDaysAgo = new Date()
              sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
              onChange({
                ...filters,
                dateRange: 'last7days',
                publishedAfter: sevenDaysAgo.toISOString()
              })
            }}
          >
            Last 7 days
          </Button>
          <Button 
            variant={filters.dateRange === 'last30days' ? 'default' : 'outline'} 
            size="sm" 
            className="w-full justify-start"
            onClick={() => {
              const thirtyDaysAgo = new Date()
              thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
              onChange({
                ...filters,
                dateRange: 'last30days',
                publishedAfter: thirtyDaysAgo.toISOString()
              })
            }}
          >
            Last 30 days
          </Button>
          <Button 
            variant={filters.dateRange === 'lastyear' ? 'default' : 'outline'} 
            size="sm" 
            className="w-full justify-start"
            onClick={() => {
              const oneYearAgo = new Date()
              oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1)
              onChange({
                ...filters,
                dateRange: 'lastyear',
                publishedAfter: oneYearAgo.toISOString()
              })
            }}
          >
            Last year
          </Button>
          {filters.dateRange && (
            <Button 
              variant="ghost" 
              size="sm" 
              className="w-full justify-start text-xs"
              onClick={() => {
                const newFilters = { ...filters }
                delete newFilters.dateRange
                delete newFilters.publishedAfter
                onChange(newFilters)
              }}
            >
              Clear date filter
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}