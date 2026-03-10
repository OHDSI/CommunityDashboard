'use client'

import { useEffect, useState } from 'react'
import { useQuery } from '@apollo/client'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { SEARCH_CONTENT } from '@/lib/graphql/queries'
import {
  ArrowLeft,
  ChevronRight,
  Filter,
  Search
} from 'lucide-react'
import { OHDSI_CATEGORIES } from '@/lib/constants/categories'

export default function ExplorerPage() {
  const router = useRouter()
  const [categoryStats, setCategoryStats] = useState<Record<string, number>>({})

  // Fetch aggregations to get category counts
  const { data, loading, error } = useQuery(SEARCH_CONTENT, {
    variables: { 
      query: null,
      filters: null,
      size: 0,  // We only need aggregations, not items
      offset: 0
    }
  })

  useEffect(() => {
    if (data?.searchContent?.aggregations?.categories?.buckets) {
      const stats: Record<string, number> = {}
      data.searchContent.aggregations.categories.buckets.forEach((bucket: any) => {
        stats[bucket.key] = bucket.doc_count
      })
      setCategoryStats(stats)
    }
  }, [data])

  const filteredCategories = OHDSI_CATEGORIES

  // Navigate to search with category filter
  const handleCategoryClick = (categoryName: string) => {
    router.push(`/search?category=${encodeURIComponent(categoryName)}`)
  }

  // Calculate total articles
  const totalContent = data?.searchContent?.total || 0

  return (
    <div className="container py-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push('/')}
          className="mb-4"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Home
        </Button>
        
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
            Explore OHDSI Categories
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Browse {totalContent} articles, studies, and resources organized by topic.
            Select a category to explore related content.
          </p>
        </div>
      </div>

      {/* Categories Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="h-48">
              <CardContent className="p-6">
                <Skeleton className="h-12 w-12 rounded-lg mb-4" />
                <Skeleton className="h-6 w-3/4 mb-2" />
                <Skeleton className="h-4 w-full mb-2" />
                <Skeleton className="h-4 w-2/3" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : error ? (
        <Card className="p-8 text-center">
          <CardContent>
            <p className="text-lg font-medium mb-2">Error loading categories</p>
            <p className="text-muted-foreground">Please try refreshing the page</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          {filteredCategories.map((category) => {
            const Icon = category.icon
            const count = categoryStats[category.name] || 0
            
            return (
              <Card
                key={category.name}
                className={`relative group cursor-pointer hover:shadow-lg transition-all duration-200 hover:-translate-y-1 border-l-4 ${category.borderColor} overflow-hidden`}
                onClick={() => handleCategoryClick(category.name)}
              >
                <div className={`absolute inset-0 bg-gradient-to-br ${category.bgColor} opacity-50`} />
                <CardHeader className="relative pb-3">
                  <div className="flex items-start justify-between mb-2">
                    <div className="p-3 rounded-lg bg-white/80 backdrop-blur-sm shadow-sm">
                      <Icon className={`h-8 w-8 ${category.color} group-hover:scale-110 transition-transform`} />
                    </div>
                    {count > 0 && (
                      <Badge
                        variant="default"
                        size="sm"
                      >
                        {count} {count === 1 ? 'item' : 'items'}
                      </Badge>
                    )}
                  </div>
                  <CardTitle className="text-xl">{category.name}</CardTitle>
                </CardHeader>
                <CardContent className="relative">
                  <p className="text-sm text-muted-foreground mb-3">
                    {category.description}
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">
                      Click to explore
                    </span>
                    <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:translate-x-1 transition-transform" />
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Quick Actions */}
      <div className="mt-12 text-center">
        <div className="inline-flex gap-4">
          <Button
            variant="outline"
            size="lg"
            onClick={() => router.push('/search')}
          >
            <Search className="mr-2 h-4 w-4" />
            Advanced Search
          </Button>
          <Button
            variant="default"
            size="lg"
            onClick={() => router.push('/search?sort=recent')}
          >
            View Recent Content
          </Button>
        </div>
      </div>
    </div>
  )
}