'use client'

import {
  Calendar,
  Eye,
  Bookmark,
  ExternalLink,
  Play,
  CheckCircle,
  Video,
  Share2,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { AIEnhancementIndicator } from '@/components/ui/ai-enhancement-indicator'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { getDisplayFields } from '@/lib/utils/content-display'
import { getSourceIcon, getSourceColors, getLanguageColor } from '@/lib/utils/source-display'
import { formatDate, formatDuration } from '@/lib/utils/format'
import { useState, memo } from 'react'

import { ArticleCardContent } from './cards/article-card-content'
import { VideoCardContent } from './cards/video-card-content'
import { RepoCardContent } from './cards/repo-card-content'
import { DiscussionCardContent } from './cards/discussion-card-content'
import { DocCardContent } from './cards/doc-card-content'

interface ContentCardProps {
  id: string
  title: string
  description?: string
  abstract?: string
  content_type: string

  // Multimodal fields
  source?: 'pubmed' | 'youtube' | 'github' | 'discourse' | 'wiki'
  display_type?: string
  icon_type?: string
  content_category?: string

  // Authors/Contributors
  authors?: any[]

  // Dates
  published_date?: string
  created_at?: string
  updated_at?: string
  last_activity?: string

  // Categories and scoring - Schema v3
  categories?: string[]
  final_score?: number  // Schema v3: replaces combined_score
  ml_score?: number
  view_count?: number
  bookmark_count?: number
  download_count?: number

  // Metrics object (alternative to individual fields)
  metrics?: {
    view_count: number
    bookmark_count: number
    share_count: number
    citation_count: number
  }

  // AI Enhancement fields - Schema v3
  ai_enhanced?: boolean
  ai_confidence?: number  // Schema v3: replaces ai_quality_score
  ai_summary?: string
  ai_tools?: string[]
  ai_categories?: string[]

  // URLs
  url?: string
  thumbnail_url?: string

  // YouTube specific
  video_id?: string
  duration?: number
  channel_name?: string

  // GitHub specific
  repo_name?: string
  stars_count?: number
  forks_count?: number
  language?: string
  topics?: string[]
  owner?: string
  last_commit?: string

  // Discourse specific
  reply_count?: number
  solved?: boolean
  category?: string
  tags?: string[]

  // Wiki specific
  doc_type?: string
  section_count?: number
  read_time?: number

  // PubMed specific
  journal?: string
  institutions?: string[]
  mesh_terms?: string[]

  // Display props
  score?: number
  highlight?: Record<string, string[]>
  className?: string
  onClick?: () => void
  isBookmarked?: boolean
  onBookmark?: () => void
  loading?: boolean
}


export const ContentCard = memo(function ContentCard({
  id,
  title,
  description,
  abstract,
  content_type,
  source,
  display_type,
  icon_type,
  content_category,
  authors,
  published_date,
  created_at,
  updated_at,
  last_activity,
  categories,
  final_score,
  ml_score,
  view_count,
  bookmark_count,
  download_count,
  metrics,
  ai_enhanced,
  ai_confidence,
  ai_summary,
  ai_tools,
  ai_categories,
  url,
  thumbnail_url,
  video_id,
  duration,
  channel_name,
  repo_name,
  stars_count,
  forks_count,
  language,
  topics,
  owner,
  last_commit,
  reply_count,
  solved,
  category,
  tags,
  doc_type,
  section_count,
  read_time,
  journal,
  institutions,
  mesh_terms,
  score,
  highlight,
  className,
  onClick,
  isBookmarked,
  onBookmark,
  loading
}: ContentCardProps) {
  const [imageLoading, setImageLoading] = useState(true)
  const [imageError, setImageError] = useState(false)

  // Use Schema v3 fields with fallbacks
  const actualViewCount = metrics?.view_count ?? view_count
  const actualBookmarkCount = metrics?.bookmark_count ?? bookmark_count
  const actualCitationCount = metrics?.citation_count
  const actualScore = final_score ?? score ?? ml_score

  // Compute display fields if not provided
  const displayFields = getDisplayFields({ source, content_type })
  const actualDisplayType = display_type ?? displayFields.display_type
  const actualIconType = icon_type ?? displayFields.icon_type
  const actualContentCategory = content_category ?? displayFields.content_category

  const displayTitle = highlight?.title?.[0] || title
  const displayDescription = highlight?.abstract?.[0] || highlight?.description?.[0] || abstract || description

  const Icon = getSourceIcon(source, actualIconType)
  const sourceColors = getSourceColors(source)
  const formattedDuration = formatDuration(duration)
  const languageColor = getLanguageColor(language)

  // Extract author names if authors is an array of objects
  const authorNames = authors?.map(a => typeof a === 'string' ? a : a.name).filter(Boolean) || []

  if (loading) {
    return (
      <Card className={cn("animate-pulse", className)}>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between mb-2">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-16" />
          </div>
          <Skeleton className="h-6 w-full mb-2" />
          <Skeleton className="h-4 w-3/4" />
        </CardHeader>
        <CardContent className="pt-0">
          <div className="flex gap-2 mb-3">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-16" />
          </div>
          <div className="flex justify-end">
            <Skeleton className="h-8 w-24" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card
      className={cn(
        "hover:shadow-lg transition-all duration-300 cursor-pointer hover:-translate-y-1 group relative overflow-hidden",
        sourceColors.hover,
        className
      )}
      onClick={onClick}
    >
      {/* Thumbnail for YouTube videos */}
      {source === 'youtube' && thumbnail_url && (
        <div className="relative h-48 w-full overflow-hidden">
          {!imageError ? (
            <>
              <img
                src={thumbnail_url}
                alt={`${title} thumbnail`}
                className={cn(
                  "w-full h-full object-cover transition-transform duration-300 group-hover:scale-105",
                  imageLoading && "opacity-0"
                )}
                onLoad={() => setImageLoading(false)}
                onError={() => {
                  setImageError(true)
                  setImageLoading(false)
                }}
              />
              {imageLoading && (
                <Skeleton className="absolute inset-0 w-full h-full" />
              )}
              {formattedDuration && (
                <Badge className="absolute bottom-2 right-2 bg-black/70 text-white border-0 text-xs">
                  {formattedDuration}
                </Badge>
              )}
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors duration-300 flex items-center justify-center">
                <Play className="h-12 w-12 text-white/0 group-hover:text-white/80 transition-colors duration-300" />
              </div>
            </>
          ) : (
            <div className="w-full h-full bg-muted flex items-center justify-center">
              <Video className="h-12 w-12 text-muted-foreground" />
            </div>
          )}
        </div>
      )}

      <CardHeader className="pb-3">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge
              variant="secondary"
              className={cn("text-xs border", sourceColors.badge)}
            >
              <Icon className="h-3 w-3 mr-1" />
              {actualDisplayType}
            </Badge>

            {/* Source-specific badges */}
            {source === 'github' && language && (
              <Badge variant="outline" className="text-xs">
                <div
                  className="w-2 h-2 rounded-full mr-1"
                  style={{ backgroundColor: languageColor }}
                />
                {language}
              </Badge>
            )}

            {source === 'discourse' && solved && (
              <Badge className="bg-green-100 text-green-800 border-green-300 text-xs">
                <CheckCircle className="h-3 w-3 mr-1" />
                Solved
              </Badge>
            )}

            {source === 'wiki' && doc_type && (
              <Badge variant="outline" className="text-xs">
                {doc_type}
              </Badge>
            )}
            {ai_enhanced && (
              <AIEnhancementIndicator
                aiEnhanced={ai_enhanced}
                aiConfidence={ai_confidence}
                aiSummary={ai_summary}
                aiTools={ai_tools}
                aiCategories={ai_categories}
                variant="badge"
              />
            )}
          </div>

          <div className="flex items-center gap-2">
            {actualScore && (
              <span className="text-xs text-muted-foreground whitespace-nowrap">
                {Math.round(actualScore * 100)}%
              </span>
            )}
            {onBookmark && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={(e) => {
                  e.stopPropagation()
                  onBookmark()
                }}
              >
                <Bookmark className={cn(
                  "h-3 w-3 transition-colors",
                  isBookmarked ? "fill-current text-primary" : "text-muted-foreground"
                )} />
              </Button>
            )}
          </div>
        </div>

        <CardTitle className="line-clamp-2 text-lg group-hover:text-primary transition-colors">
          <span dangerouslySetInnerHTML={{ __html: displayTitle }} />
        </CardTitle>

        {displayDescription && (
          <CardDescription className="line-clamp-3 mt-2">
            <span dangerouslySetInnerHTML={{ __html: displayDescription }} />
          </CardDescription>
        )}
      </CardHeader>

      <CardContent className="pt-0">
        {/* Source-specific metadata — delegated to sub-components */}
        {source === 'youtube' && (
          <VideoCardContent
            channel_name={channel_name}
            viewCount={actualViewCount}
          />
        )}

        {source === 'github' && (
          <RepoCardContent
            owner={owner}
            stars_count={stars_count}
            forks_count={forks_count}
            topics={topics}
            last_commit={last_commit}
          />
        )}

        {source === 'discourse' && (
          <DiscussionCardContent
            reply_count={reply_count}
            category={category}
            last_activity={last_activity}
            tags={tags}
          />
        )}

        {source === 'wiki' && (
          <DocCardContent
            section_count={section_count}
            read_time={read_time}
            updated_at={updated_at}
          />
        )}

        {source === 'pubmed' && (
          <ArticleCardContent
            journal={journal}
            citationCount={actualCitationCount}
            authorNames={authorNames}
            institutions={institutions}
            mesh_terms={mesh_terms}
          />
        )}

        {/* Published Date */}
        {published_date && (
          <div className="flex items-center gap-1 text-sm text-muted-foreground mb-2">
            <Calendar className="h-3 w-3" />
            <span>{formatDate(published_date)}</span>
          </div>
        )}

        {/* Categories */}
        {categories && categories.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {categories.slice(0, 3).map((category) => (
              <Badge key={category} variant="outline" className="text-xs">
                {category}
              </Badge>
            ))}
            {categories.length > 3 && (
              <Badge variant="outline" className="text-xs">
                +{categories.length - 3} more
              </Badge>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-between mt-4">
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            {actualViewCount !== undefined && actualViewCount !== null && actualViewCount > 0 && source !== 'youtube' && (
              <div className="flex items-center gap-1">
                <Eye className="h-3 w-3" />
                <span>{actualViewCount.toLocaleString()}</span>
              </div>
            )}
            {actualBookmarkCount !== undefined && actualBookmarkCount !== null && actualBookmarkCount > 0 && (
              <div className="flex items-center gap-1">
                <Bookmark className="h-3 w-3" />
                <span>{actualBookmarkCount.toLocaleString()}</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 px-2 text-xs"
              onClick={(e) => {
                e.stopPropagation()
                if (navigator.share && url) {
                  navigator.share({
                    title,
                    text: description || abstract,
                    url
                  })
                } else if (url) {
                  navigator.clipboard.writeText(url)
                }
              }}
            >
              <Share2 className="h-3 w-3 mr-1" />
              Share
            </Button>

            {url && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-2 text-xs group-hover:translate-x-1 transition-transform"
                onClick={(e) => {
                  e.stopPropagation()
                  window.open(url, '_blank')
                }}
              >
                <ExternalLink className="h-3 w-3 mr-1" />
                View {source === 'youtube' ? 'Video' : source === 'github' ? 'Repo' : 'Source'}
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
})
