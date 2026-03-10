'use client'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { OHDSIIcon } from '@/components/ui/ohdsi-logo'
import { AIEnhancementIndicator } from '@/components/ui/ai-enhancement-indicator'
import { 
  ArrowLeft,
  Bookmark,
  Share2,
  ExternalLink,
  Calendar,
  Users,
  BarChart,
  Brain,
  Target,
  FileText,
  Video,
  Code,
  MessageSquare,
  BookOpen,
  Eye,
  Clock,
  Star
} from 'lucide-react'
import { format } from 'date-fns'
import { useRouter } from 'next/navigation'
import { ContentSource, SourceConfig, formatViews, formatDuration } from '../../utils/sourceDetector'

interface ContentHeaderProps {
  content: any
  source: ContentSource
}

const SOURCE_CONFIGS: Record<ContentSource, SourceConfig> = {
  pubmed: {
    icon: FileText,
    color: 'blue',
    label: 'Research Article',
    primaryAction: 'View on PubMed',
    gradient: 'from-blue-500/10 to-blue-600/10'
  },
  youtube: {
    icon: Video,
    color: 'red',
    label: 'Video Content',
    primaryAction: 'Watch on YouTube',
    gradient: 'from-red-500/10 to-red-600/10'
  },
  github: {
    icon: Code,
    color: 'purple',
    label: 'Repository',
    primaryAction: 'View on GitHub',
    gradient: 'from-purple-500/10 to-purple-600/10'
  },
  discourse: {
    icon: MessageSquare,
    color: 'green',
    label: 'Discussion',
    primaryAction: 'View Thread',
    gradient: 'from-green-500/10 to-green-600/10'
  },
  wiki: {
    icon: BookOpen,
    color: 'orange',
    label: 'Documentation',
    primaryAction: 'View Original',
    gradient: 'from-orange-500/10 to-orange-600/10'
  }
}

export function ContentHeader({ content, source }: ContentHeaderProps) {
  const router = useRouter()
  const config = SOURCE_CONFIGS[source]
  const SourceIcon = config.icon

  // Build external URL based on source
  const getExternalUrl = () => {
    switch (source) {
      case 'pubmed':
        if (content.pmid) return `https://pubmed.ncbi.nlm.nih.gov/${content.pmid}/`
        break
      case 'youtube':
        if (content.videoId || content.video_id) return `https://youtube.com/watch?v=${content.videoId || content.video_id}`
        break
      case 'github':
        if (content.repoName) return `https://github.com/${content.owner || 'OHDSI'}/${content.repoName}`
        break
      case 'discourse':
        if (content.topicId) return `https://forums.ohdsi.org/t/${content.topicId}`
        break
      case 'wiki':
        return content.url
    }
    return content.url
  }

  // Get source-specific metadata
  const getMetadataItems = () => {
    const items = []
    
    // Common metadata
    if (content.publishedDate) {
      items.push({
        icon: Calendar,
        text: format(new Date(content.publishedDate), 'MMM d, yyyy')
      })
    }

    // Source-specific metadata
    switch (source) {
      case 'pubmed':
        if (content.authors?.length) {
          items.push({
            icon: Users,
            text: `${content.authors.length} authors`
          })
        }
        if (content.citations?.cited_by_count) {
          items.push({
            icon: BarChart,
            text: `${content.citations.cited_by_count} citations`
          })
        }
        break
      
      case 'youtube':
        if (content.viewCount) {
          items.push({
            icon: Eye,
            text: `${formatViews(content.viewCount)} views`
          })
        }
        if (content.duration) {
          items.push({
            icon: Clock,
            text: formatDuration(content.duration)
          })
        }
        break
      
      case 'github':
        if (content.starsCount) {
          items.push({
            icon: Star,
            text: `${content.starsCount} stars`
          })
        }
        if (content.language) {
          items.push({
            icon: Code,
            text: content.language
          })
        }
        break
      
      case 'discourse':
        if (content.replyCount) {
          items.push({
            icon: MessageSquare,
            text: `${content.replyCount} replies`
          })
        }
        if (content.solved) {
          items.push({
            icon: Target,
            text: 'Solved'
          })
        }
        break
      
      case 'wiki':
        if (content.docType) {
          items.push({
            icon: BookOpen,
            text: content.docType
          })
        }
        if (content.lastModified) {
          items.push({
            icon: Clock,
            text: `Updated ${format(new Date(content.lastModified), 'MMM yyyy')}`
          })
        }
        break
    }

    return items
  }

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href)
    // TODO: Add toast notification
  }

  return (
    <div className="space-y-4">
      {/* Back Button */}
      <Button
        variant="ghost"
        onClick={() => router.back()}
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back
      </Button>

      {/* Header Card */}
      <div className={`bg-gradient-to-r ${config.gradient} rounded-t-lg border-b`}>
        <div className="px-6 py-4">
          {/* Badges Row */}
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <Badge 
              variant="outline" 
              className="bg-white"
            >
              <SourceIcon className="h-3 w-3 mr-1" />
              {config.label}
            </Badge>
            
            {content.mlScore && (
              <Badge 
                variant={content.mlScore > 0.8 ? "success" : "secondary"}
                className="flex items-center gap-1"
              >
                <Brain className="h-3 w-3" />
                ML: {(content.mlScore * 100).toFixed(0)}%
              </Badge>
            )}
            
            {content.aiEnhanced && (
              <AIEnhancementIndicator
                aiEnhanced={content.aiEnhanced}
                aiConfidence={content.aiConfidence}
                aiSummary={content.aiSummary}
                aiTools={content.aiTools}
                variant="badge"
              />
            )}
            
            {content.approvalStatus === 'approved' && (
              <Badge variant="success">
                <Target className="h-3 w-3 mr-1" />
                OHDSI Verified
              </Badge>
            )}
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold text-foreground mb-3">
            {content.title}
          </h1>

          {/* Metadata Row */}
          <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
            {getMetadataItems().map((item, idx) => {
              const Icon = item.icon
              return (
                <div key={idx} className="flex items-center gap-1">
                  <Icon className="h-3 w-3" />
                  {item.text}
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-between px-6">
        <div className="flex gap-2">
          {/* Primary External Link */}
          {getExternalUrl() && (
            <Button variant="default" size="sm" asChild>
              <a href={getExternalUrl()} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4 mr-2" />
                {config.primaryAction}
              </a>
            </Button>
          )}
          
          {/* Additional source-specific actions */}
          {source === 'pubmed' && content.doi && (
            <Button variant="outline" size="sm" asChild>
              <a href={`https://doi.org/${content.doi}`} target="_blank" rel="noopener noreferrer">
                DOI
              </a>
            </Button>
          )}
        </div>

        <div className="flex gap-2">
          <Button variant="ghost" size="icon" title="Save to library">
            <Bookmark className="h-4 w-4" />
          </Button>
          <Button 
            variant="ghost" 
            size="icon" 
            title="Share"
            onClick={handleShare}
          >
            <Share2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}