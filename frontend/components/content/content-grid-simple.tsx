'use client'

import { ContentCard } from './content-card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { AlertCircle, RefreshCw, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ContentGridProps {
  items: any[]
  loading?: boolean
  error?: Error
  viewMode?: 'grid' | 'list'
  onItemClick?: (item: any) => void
  onRetry?: () => void
  className?: string
  emptyMessage?: string
}

export function ContentGrid({
  items,
  loading = false,
  error,
  viewMode = 'grid',
  onItemClick,
  onRetry,
  className,
  emptyMessage = "No content found. Try adjusting your search or filters."
}: ContentGridProps) {
  
  // Handle loading state
  if (loading) {
    return (
      <div className={cn(
        "grid gap-4",
        viewMode === 'grid' ? "md:grid-cols-2 lg:grid-cols-3" : "grid-cols-1",
        className
      )}>
        {[...Array(6)].map((_, i) => (
          <div key={i} className="rounded-lg border bg-muted animate-pulse p-4 space-y-3">
            <div className="flex justify-between">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-3 w-12" />
            </div>
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-2/3" />
            <div className="flex gap-2 pt-2">
              <Skeleton className="h-5 w-16" />
              <Skeleton className="h-5 w-12" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  // Handle error state
  if (error) {
    return (
      <div className={cn("flex flex-col items-center justify-center py-12 text-center", className)}>
        <AlertCircle className="h-12 w-12 text-destructive mb-4" />
        <h3 className="text-lg font-semibold mb-2">Something went wrong</h3>
        <p className="text-muted-foreground max-w-md mb-4">
          {error.message || "An unexpected error occurred while loading content."}
        </p>
        {onRetry && (
          <Button onClick={onRetry} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Try Again
          </Button>
        )}
      </div>
    )
  }

  // Handle empty state
  if (!items || items.length === 0) {
    return (
      <div className={cn("flex flex-col items-center justify-center py-12 text-center", className)}>
        <Search className="h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">No results found</h3>
        <p className="text-muted-foreground max-w-md">
          {emptyMessage}
        </p>
      </div>
    )
  }

  // Render items
  return (
    <div className={cn(
      "grid gap-4",
      viewMode === 'grid' ? "md:grid-cols-2 lg:grid-cols-3" : "grid-cols-1",
      className
    )}>
      {items.map((item) => {
        // Map the GraphQL response to ContentCard props
        const cardProps = {
          id: item.id,
          title: item.title,
          abstract: item.abstract,
          content_type: item.contentType || item.content_type,
          source: item.source,
          display_type: item.displayType || item.display_type,
          icon_type: item.iconType || item.icon_type,
          content_category: item.contentCategory || item.content_category,
          authors: item.authors || [],
          published_date: item.publishedDate || item.published_date,
          categories: item.categories || [],
          ml_score: item.mlScore || item.ml_score,
          final_score: item.finalScore || item.final_score,
          ai_confidence: item.aiConfidence || item.ai_confidence,
          ai_summary: item.aiSummary || item.ai_summary,
          metrics: item.metrics,
          url: item.url,
          
          // YouTube specific
          video_id: item.videoId || item.video_id,
          duration: item.duration,
          channel_name: item.channelName || item.channel_name,
          thumbnail_url: item.thumbnailUrl || item.thumbnail_url,
          
          // GitHub specific
          repo_name: item.repoName || item.repo_name,
          stars_count: item.starsCount || item.stars_count,
          forks_count: item.forksCount || item.forks_count,
          language: item.language,
          
          // Discourse specific
          topic_id: item.topicId || item.topic_id,
          reply_count: item.replyCount || item.reply_count,
          solved: item.solved,
          
          // Wiki specific
          doc_type: item.docType || item.doc_type,
          section_count: item.sectionCount || item.section_count,
        }
        
        return (
          <ContentCard
            key={item.id}
            {...cardProps}
            onClick={() => onItemClick?.(item)}
            className="h-full"
          />
        )
      })}
    </div>
  )
}