'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { useSearchParams, useRouter } from 'next/navigation'
import {
  Search,
  Filter,
  X,
  Grid,
  List,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertCircle,
  SlidersHorizontal,
  Calendar
} from 'lucide-react'
import { ContentCard } from '@/components/content/content-card'
import { getDisplayFields } from '@/lib/utils/content-display'
import { cn } from '@/lib/utils'
import { CATEGORY_NAMES } from '@/lib/constants/categories'

// Types
interface Article {
  id: string
  title: string
  abstract: string
  contentType: string
  source?: string
  displayType?: string
  iconType?: string
  contentCategory?: string
  authors: { name: string }[]
  published_date: string
  categories: string[]
  mlScore?: number
  final_score?: number
  url?: string
  thumbnailUrl?: string
  videoId?: string
  duration?: number
  channelName?: string
  repoName?: string
  starsCount?: number
  language?: string
  replyCount?: number
  solved?: boolean
  aiConfidence?: number
  metrics?: {
    view_count: number
    bookmark_count: number
    share_count: number
    citation_count: number
  }
}

interface SearchResult {
  total: number
  items: Article[]
  took_ms: number
  aggregations?: any
}

type ViewMode = 'grid' | 'list'
type SortOption = 'relevance' | 'best-match' | 'date' | 'popularity'

export default function SearchPage() {
  const searchParams = useSearchParams()
  const router = useRouter()

  // Core search state
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [debouncedQuery, setDebouncedQuery] = useState(query)
  const [searchMode, setSearchMode] = useState<'keyword' | 'semantic' | 'hybrid'>('hybrid')
  const [results, setResults] = useState<SearchResult | null>(null)
  const [loading, setLoading] = useState(false)
  
  // Simplified filters - only the essentials
  const [sourceFilter, setSourceFilter] = useState<string>('all')
  const [dateFilter, setDateFilter] = useState<string>('all')
  const [categoryFilter, setCategoryFilter] = useState<string>(searchParams.get('category') || 'all')
  const [showFilters, setShowFilters] = useState(searchParams.get('category') ? true : false)
  
  // UI state
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [sortBy, setSortBy] = useState<SortOption>('best-match')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 20
  
  // Error state
  const [searchError, setSearchError] = useState<string | null>(null)

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, 300)
    return () => clearTimeout(timer)
  }, [query])

  // Auto-search when debounced query or filters change
  useEffect(() => {
    if (debouncedQuery.trim() || sourceFilter !== 'all' || dateFilter !== 'all' || categoryFilter !== 'all') {
      performSearch()
    }
  }, [debouncedQuery, sourceFilter, dateFilter, categoryFilter, searchMode, sortBy])

  // Build filters for GraphQL
  const buildGraphQLFilters = useCallback(() => {
    const filters: any = {}
    
    if (sourceFilter !== 'all') {
      filters.source = sourceFilter
    }
    
    if (dateFilter !== 'all') {
      const now = new Date()
      let dateFrom = new Date()
      
      switch(dateFilter) {
        case 'day':
          dateFrom.setDate(now.getDate() - 1)
          break
        case 'week':
          dateFrom.setDate(now.getDate() - 7)
          break
        case 'month':
          dateFrom.setMonth(now.getMonth() - 1)
          break
        case 'year':
          dateFrom.setFullYear(now.getFullYear() - 1)
          break
      }
      
      if (dateFilter !== 'all') {
        filters.publishedAfter = dateFrom.toISOString()
      }
    }
    
    if (categoryFilter !== 'all') {
      filters.categories = categoryFilter
    }
    
    return filters
  }, [sourceFilter, dateFilter, categoryFilter])

  // Perform search
  const performSearch = async (pageNum = 1) => {
    if (!debouncedQuery.trim() && sourceFilter === 'all' && dateFilter === 'all' && categoryFilter === 'all') {
      setResults(null)
      return
    }

    setLoading(true)
    setSearchError(null)

    try {
      const graphqlFilters = buildGraphQLFilters()
      const offset = (pageNum - 1) * itemsPerPage

      // Build query based on search mode
      let queryName = 'searchContent'
      let queryParams = '$query: String, $filters: JSON, $size: Int, $offset: Int, $sortBy: String'
      let queryArgs = 'query: $query, filters: $filters, size: $size, offset: $offset, sortBy: $sortBy'

      const variables: any = {
        query: debouncedQuery || null,
        filters: Object.keys(graphqlFilters).length > 0 ? graphqlFilters : null,
        size: itemsPerPage,
        offset: offset,
        sortBy: sortBy === 'date' ? 'date-desc' : sortBy
      }

      if (searchMode === 'semantic') {
        queryName = 'semanticSearch'
        queryParams = '$query: String!, $filters: JSON, $size: Int, $offset: Int, $minScore: Float, $sortBy: String'
        queryArgs = 'query: $query, filters: $filters, size: $size, offset: $offset, minScore: $minScore, sortBy: $sortBy'
        variables.query = debouncedQuery || ''
        variables.minScore = 0.0
      } else if (searchMode === 'hybrid') {
        queryName = 'hybridSearch'
        queryParams = '$query: String!, $filters: JSON, $size: Int, $offset: Int, $keywordWeight: Float, $semanticWeight: Float, $sortBy: String'
        queryArgs = 'query: $query, filters: $filters, size: $size, offset: $offset, keywordWeight: $keywordWeight, semanticWeight: $semanticWeight, sortBy: $sortBy'
        variables.query = debouncedQuery || ''
        variables.keywordWeight = 0.5
        variables.semanticWeight = 0.5
      }

      const response = await fetch(process.env.NEXT_PUBLIC_GRAPHQL_URL || '/graphql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: `
            query SearchContent(${queryParams}) {
              ${queryName}(${queryArgs}) {
                total
                tookMs
                aggregations
                items {
                  id
                  title
                  abstract
                  contentType
                  source
                  displayType
                  iconType
                  contentCategory
                  authors {
                    name
                  }
                  publishedDate
                  categories
                  mlScore
                  finalScore
                  aiConfidence
                  url
                  videoId
                  duration
                  channelName
                  thumbnailUrl
                  repoName
                  starsCount
                  language
                  replyCount
                  solved
                  metrics {
                    viewCount
                    bookmarkCount
                    shareCount
                    citationCount
                  }
                }
              }
            }
          `,
          variables
        })
      })

      const data = await response.json()
      
      if (data.errors) {
        throw new Error(data.errors[0].message)
      }

      const searchResult = data.data?.searchContent || data.data?.semanticSearch || data.data?.hybridSearch
      
      if (searchResult) {
        const transformedResult: SearchResult = {
          total: searchResult.total,
          took_ms: searchResult.tookMs || 0,
          aggregations: searchResult.aggregations,
          items: searchResult.items.map((item: any) => {
            const displayFields = getDisplayFields({ source: item.source, content_type: item.contentType })
            
            return {
              id: item.id,
              title: item.title,
              abstract: item.abstract,
              contentType: item.contentType,
              source: item.source,
              displayType: item.displayType || displayFields.display_type,
              iconType: item.iconType || displayFields.icon_type,
              contentCategory: item.contentCategory || displayFields.content_category,
              authors: item.authors || [],
              published_date: item.publishedDate || new Date().toISOString(),
              categories: item.categories || [],
              mlScore: item.mlScore,
              final_score: item.finalScore,
              aiConfidence: item.aiConfidence,
              metrics: item.metrics ? {
                view_count: item.metrics.viewCount || 0,
                bookmark_count: item.metrics.bookmarkCount || 0,
                share_count: item.metrics.shareCount || 0,
                citation_count: item.metrics.citationCount || 0
              } : undefined,
              url: item.url,
              videoId: item.videoId,
              duration: item.duration,
              channelName: item.channelName,
              thumbnailUrl: item.thumbnailUrl,
              repoName: item.repoName,
              starsCount: item.starsCount,
              language: item.language,
              replyCount: item.replyCount,
              solved: item.solved
            }
          })
        }

        setResults(transformedResult)
        setCurrentPage(pageNum)
      }
    } catch (error: any) {
      setSearchError(error.message || 'An error occurred while searching')
    } finally {
      setLoading(false)
    }
  }

  // Pagination
  const totalPages = results ? Math.ceil(results.total / itemsPerPage) : 0

  const handlePageChange = (page: number) => {
    performSearch(page)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="container py-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold mb-2">OHDSI Knowledge Search</h1>
        <p className="text-muted-foreground">
          Discover research, code, and community content
        </p>
      </div>

      {/* Search Bar */}
      <div className="max-w-3xl mx-auto mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
          <Input
            type="search"
            placeholder="Search OHDSI knowledge base..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-10 pr-4 h-12 text-lg"
          />
        </div>

        {/* Search Mode Tabs - Simplified */}
        <div className="mt-4 flex items-center justify-center gap-4">
          <Tabs value={searchMode} onValueChange={(v) => setSearchMode(v as any)} className="w-auto">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="keyword">Keyword</TabsTrigger>
              <TabsTrigger value="semantic">Semantic</TabsTrigger>
              <TabsTrigger value="hybrid">Hybrid</TabsTrigger>
            </TabsList>
          </Tabs>
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            className="gap-2"
          >
            <SlidersHorizontal className="h-4 w-4" />
            Filters
            {(sourceFilter !== 'all' || dateFilter !== 'all' || categoryFilter !== 'all') && (
              <Badge variant="secondary" className="ml-1">
                {[sourceFilter !== 'all', dateFilter !== 'all', categoryFilter !== 'all'].filter(Boolean).length}
              </Badge>
            )}
          </Button>
        </div>

        {/* Simple Filters - Hidden by default */}
        {showFilters && (
          <Card className="mt-4 p-4">
            <div className="flex flex-wrap gap-4">
              <div className="flex-1 min-w-[150px]">
                <label className="text-sm font-medium mb-1 block">Source</label>
                <Select value={sourceFilter} onValueChange={setSourceFilter}>
                  <SelectTrigger className="h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Sources</SelectItem>
                    <SelectItem value="pubmed">PubMed Articles</SelectItem>
                    <SelectItem value="youtube">YouTube Videos</SelectItem>
                    <SelectItem value="github">GitHub Repos</SelectItem>
                    <SelectItem value="discourse">Discussions</SelectItem>
                    <SelectItem value="wiki">Documentation</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex-1 min-w-[150px]">
                <label className="text-sm font-medium mb-1 block">Date Range</label>
                <Select value={dateFilter} onValueChange={setDateFilter}>
                  <SelectTrigger className="h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Time</SelectItem>
                    <SelectItem value="day">Last 24 Hours</SelectItem>
                    <SelectItem value="week">Last Week</SelectItem>
                    <SelectItem value="month">Last Month</SelectItem>
                    <SelectItem value="year">Last Year</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex-1 min-w-[150px]">
                <label className="text-sm font-medium mb-1 block">Category</label>
                <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                  <SelectTrigger className="h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Categories</SelectItem>
                    {CATEGORY_NAMES.map((name) => (
                      <SelectItem key={name} value={name}>{name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex-1 min-w-[150px]">
                <label className="text-sm font-medium mb-1 block">Sort By</label>
                <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortOption)}>
                  <SelectTrigger className="h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="relevance">Relevance</SelectItem>
                    <SelectItem value="best-match">Best Match</SelectItem>
                    <SelectItem value="date">Newest First</SelectItem>
                    <SelectItem value="popularity">Most Popular</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-end gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSourceFilter('all')
                    setDateFilter('all')
                    setCategoryFilter('all')
                  }}
                >
                  Clear Filters
                </Button>
              </div>
            </div>
          </Card>
        )}
      </div>

      {/* Results Header */}
      {results && (
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold">
              {results.total} Results
            </h2>
            {query && (
              <p className="text-sm text-muted-foreground mt-1">
                for "{query}" • {results.took_ms}ms
              </p>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant={viewMode === 'grid' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('grid')}
            >
              <Grid className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('list')}
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="p-6">
              <Skeleton className="h-4 w-3/4 mb-2" />
              <Skeleton className="h-3 w-full mb-2" />
              <Skeleton className="h-3 w-full mb-4" />
              <Skeleton className="h-8 w-20" />
            </Card>
          ))}
        </div>
      )}

      {/* Error State */}
      {searchError && (
        <Card className="p-8 text-center">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <p className="text-lg font-medium mb-2">Search Error</p>
          <p className="text-muted-foreground">{searchError}</p>
        </Card>
      )}

      {/* Results Grid */}
      {results && !loading && (
        <>
          <div className={cn(
            "grid gap-4",
            viewMode === 'grid' ? "md:grid-cols-2 lg:grid-cols-3" : "grid-cols-1"
          )}>
            {results.items.map((article) => (
              <ContentCard
                key={article.id}
                id={article.id}
                title={article.title}
                abstract={article.abstract}
                content_type={article.contentType}
                source={article.source as "pubmed" | "youtube" | "github" | "discourse" | "wiki" | undefined}
                display_type={article.displayType}
                icon_type={article.iconType}
                content_category={article.contentCategory}
                authors={article.authors}
                published_date={article.published_date}
                categories={article.categories}
                ml_score={article.mlScore}
                final_score={article.final_score}
                ai_confidence={article.aiConfidence}
                metrics={article.metrics}
                url={article.url}
                video_id={article.videoId}
                duration={article.duration}
                channel_name={article.channelName}
                thumbnail_url={article.thumbnailUrl}
                repo_name={article.repoName}
                stars_count={article.starsCount}
                language={article.language}
                reply_count={article.replyCount}
                solved={article.solved}
                onClick={() => router.push(`/content/${article.id}`)}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center items-center gap-2 mt-8">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
              >
                Previous
              </Button>
              
              <div className="flex items-center gap-1">
                {[...Array(Math.min(5, totalPages))].map((_, i) => {
                  const pageNum = i + 1
                  return (
                    <Button
                      key={pageNum}
                      variant={currentPage === pageNum ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => handlePageChange(pageNum)}
                      className="w-8 h-8 p-0"
                    >
                      {pageNum}
                    </Button>
                  )
                })}
                {totalPages > 5 && <span className="px-2">...</span>}
                {totalPages > 5 && (
                  <Button
                    variant={currentPage === totalPages ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => handlePageChange(totalPages)}
                    className="w-8 h-8 p-0"
                  >
                    {totalPages}
                  </Button>
                )}
              </div>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}

      {/* Empty State */}
      {!results && !loading && !searchError && (
        <div className="text-center py-12">
          <Search className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">Start Searching</h3>
          <p className="text-muted-foreground max-w-md mx-auto">
            Enter a search term above to discover OHDSI research, tools, and community content
          </p>
        </div>
      )}
    </div>
  )
}