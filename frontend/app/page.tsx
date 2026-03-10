'use client'

import { useState, useEffect } from 'react'
import { useRouter } from "next/navigation"
import { useQuery } from '@apollo/client'
import { SearchBar } from '@/components/search/search-bar'
import { FilterPanel } from '@/components/search/filter-panel'
import { ContentGrid } from '@/components/content/content-grid-simple'
import { SEARCH_CONTENT, HYBRID_SEARCH } from '@/lib/graphql/queries'
import { Card, CardContent } from '@/components/ui/card'
import { FileText, ArrowRight, Database, PlayCircle, Code2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function HomePage() {
  const [query, setQuery] = useState('')
  const router = useRouter()
  const [filters, setFilters] = useState<Record<string, any>>({ content_type: ['article'] })
  const [mounted, setMounted] = useState(false)
  
  // Use useEffect to ensure client-side only execution
  useEffect(() => {
    setMounted(true)
  }, [])
  
  const { data, loading, error } = useQuery(query ? HYBRID_SEARCH : SEARCH_CONTENT, {
    variables: query ? {
      query: query,
      filters: Object.keys(filters).length > 0 ? filters : null,
      size: 20,
      offset: 0,
      keywordWeight: 0.5,
      semanticWeight: 0.5,
      sortBy: "best-match"
    } : {
      query: null,
      filters: Object.keys(filters).length > 0 ? filters : null,
      size: 20,
      offset: 0,
      sortBy: "date-desc"
    },
    skip: false,  // Always fetch articles to show default content
  })

  // Query to get overall stats - force refetch on mount
  const { data: statsData, loading: statsLoading, error: statsError, refetch: refetchStats } = useQuery(SEARCH_CONTENT, {
    variables: { 
      query: null,
      filters: null,
      size: 0,
      offset: 0,
      sortBy: "date-desc"
    },
    fetchPolicy: mounted ? 'network-only' : 'cache-first', // Force network request after mount
    notifyOnNetworkStatusChange: true,
  })
  
  useEffect(() => {
    if (mounted && !statsData && !statsLoading && !statsError) {
      refetchStats()
    }
  }, [mounted, statsData, statsLoading, statsError, refetchStats])

  const searchResults = data?.searchContent || data?.hybridSearch
  const totalContent = statsData?.searchContent?.total || 0
  
  return (
    <div className="flex flex-col">
      {/* Hero Section with Gradient Background */}
      <div className="relative bg-gradient-to-b from-primary/5 via-accent/5 to-background">
        {/* Decorative elements */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-20 left-10 w-72 h-72 bg-accent/20 rounded-full blur-3xl" />
          <div className="absolute bottom-20 right-10 w-96 h-96 bg-primary/20 rounded-full blur-3xl" />
        </div>
        
        <div className="container py-12 relative">
          <div className="flex flex-col gap-8">
            {/* Main Hero Content */}
            <div className="text-center space-y-4">
              <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight">
                <span className="bg-gradient-to-r from-primary via-primary to-accent bg-clip-text text-transparent">
                  Community Intelligence
                </span>
              </h1>
              <p className="text-lg sm:text-xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
                Discover and explore research, tools, and knowledge from the global OHDSI community.
                Access {totalContent || '700+'} articles, studies, and resources.
              </p>
            </div>

            {/* Search Bar with Shadow */}
            <div className="max-w-3xl mx-auto w-full">
              <div className="relative">
                <SearchBar 
                  value={query} 
                  onChange={setQuery}
                  placeholder="Search for OMOP CDM, Atlas, HADES, authors, or any OHDSI topic..."
                  className="shadow-lg"
                />
              </div>
            </div>

            {/* Quick Stats Cards */}
            {!query && !loading && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-5xl mx-auto w-full">
                <Card className="group hover:shadow-lg transition-all duration-200 hover:-translate-y-1 border-l-4 border-l-primary">
                  <CardContent className="p-6 text-center" onClick={() => router.push("/search?sort=date-desc")}>
                    <div className="inline-flex p-2 rounded-lg bg-gradient-to-br from-primary/10 to-accent/10 mb-3">
                      <Database className="h-8 w-8 text-primary group-hover:scale-110 transition-transform" />
                    </div>
                    <div className="text-3xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                      {totalContent || 0}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">Total Content</div>
                  </CardContent>
                </Card>
                
                <Card className="group hover:shadow-lg transition-all duration-200 hover:-translate-y-1 border-l-4 border-l-accent" onClick={() => router.push("/search?source=pubmed&sort=date-desc")}>
                  <CardContent className="p-6 text-center" onClick={() => router.push("/search?source=pubmed&sort=date-desc")}>
                    <div className="inline-flex p-2 rounded-lg bg-gradient-to-br from-accent/10 to-primary/10 mb-3">
                      <FileText className="h-8 w-8 text-accent group-hover:scale-110 transition-transform" />
                    </div>
                    <div className="text-3xl font-bold text-accent">
                      {statsData?.searchContent?.aggregations?.sources?.buckets?.find((b: any) => b.key === 'pubmed')?.doc_count || 0}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">Research Papers</div>
                  </CardContent>
                </Card>
                
                <Card className="group hover:shadow-lg transition-all duration-200 hover:-translate-y-1 border-l-4 border-l-primary">
                  <CardContent className="p-6 text-center">
                    <div className="inline-flex p-2 rounded-lg bg-gradient-to-br from-primary/10 to-accent/10 mb-3">
                      <PlayCircle className="h-8 w-8 text-primary group-hover:scale-110 transition-transform" />
                    </div>
                    <div className="text-3xl font-bold text-primary">
                      {statsData?.searchContent?.aggregations?.sources?.buckets?.find((b: any) => b.key === 'youtube')?.doc_count || 0}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">Videos</div>
                  </CardContent>
                </Card>
                
                <Card className="group hover:shadow-lg transition-all duration-200 hover:-translate-y-1 border-l-4 border-l-accent">
                  <CardContent className="p-6 text-center">
                    <div className="inline-flex p-2 rounded-lg bg-gradient-to-br from-accent/10 to-primary/10 mb-3">
                      <Code2 className="h-8 w-8 text-accent group-hover:scale-110 transition-transform" />
                    </div>
                    <div className="text-3xl font-bold text-accent">
                      {statsData?.searchContent?.aggregations?.sources?.buckets?.find((b: any) => b.key === 'github')?.doc_count || 0}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">Repositories</div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>

            {/* View All Button */}
            <div className="mt-8 text-center">
              <Button
                size="lg"
                variant="default"
                onClick={() => router.push("/search?sort=date-desc")}
                className="gap-2"
              >
                View All Content
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
        </div>
      </div>

      {/* Search Results Section - Always show to display default content */}
      <div className="container py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Filter Sidebar */}
          <div className="md:col-span-1">
            <FilterPanel
              filters={filters}
              onChange={setFilters}
              aggregations={statsData?.searchContent?.aggregations || searchResults?.aggregations}
            />
          </div>

          {/* Results Grid */}
          <div className="md:col-span-3">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-2xl font-semibold">
                    {!query
                      ? `Recent Articles`
                      : searchResults?.total
                      ? `${searchResults.total} Results`
                      : loading
                      ? 'Searching...'
                      : 'No results found'}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    {query
                      ? `Searching for "${query}"`
                      : `Showing ${searchResults?.total || 0} articles from the OHDSI community`}
                  </p>
                </div>
              </div>
              
              <>
              <ContentGrid 
                items={searchResults?.items || []}
                loading={loading}
                onItemClick={(item) => {
                  window.location.href = `/content/${item.id}`
                }}
              />
              
              {error && (
                <Card className="border-destructive/50 bg-destructive/5">
                  <CardContent className="p-6 text-center">
                    <p className="text-destructive">
                      Error loading results. Please try again.
                    </p>
                  </CardContent>
                </Card>
              )}</>
          </div>
        </div>
      </div>
    </div>
  )
}