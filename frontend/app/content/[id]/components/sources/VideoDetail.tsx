'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { 
  Play,
  FileText,
  Info,
  Link as LinkIcon,
  Eye,
  ThumbsUp,
  Clock,
  Calendar,
  ExternalLink,
  Target,
  Brain
} from 'lucide-react'
import Link from 'next/link'
import { format } from 'date-fns'
import { formatViews, formatDuration } from '../../utils/sourceDetector'

interface VideoDetailProps {
  content: any
}

export function VideoDetail({ content }: VideoDetailProps) {
  const [activeTimestamp, setActiveTimestamp] = useState<number>(0)
  
  // Parse transcript with timestamps if available
  const parseTranscript = (transcript: string | undefined) => {
    if (!transcript) return []
    
    // Simple parsing - assumes format like "[00:00] Text here"
    const lines = transcript.split('\n')
    return lines.map(line => {
      const match = line.match(/\[(\d+:\d+)\]\s*(.*)/)
      if (match) {
        const [_, time, text] = match
        const [minutes, seconds] = time.split(':').map(Number)
        return {
          timestamp: minutes * 60 + seconds,
          time,
          text
        }
      }
      return { timestamp: 0, time: '0:00', text: line }
    })
  }

  const transcriptParts = parseTranscript(content.transcript)

  const handleTimestampClick = (timestamp: number) => {
    setActiveTimestamp(timestamp)
    // Scroll to video
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Main Video Column */}
      <div className="lg:col-span-2 space-y-6">
        {/* YouTube Embed */}
        <Card className="overflow-hidden">
          <div className="aspect-video bg-black">
            {(content.videoId || content.video_id) ? (
              <iframe
                src={`https://www.youtube.com/embed/${content.videoId || content.video_id}?start=${activeTimestamp}`}
                className="w-full h-full"
                allowFullScreen
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                title={content.title}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-white">
                <p>Video unavailable</p>
              </div>
            )}
          </div>
        </Card>
        
        {/* Video Info Tabs */}
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-xl">{content.title}</CardTitle>
                <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                  {content.viewCount && (
                    <span className="flex items-center gap-1">
                      <Eye className="h-3 w-3" />
                      {formatViews(content.viewCount)} views
                    </span>
                  )}
                  {content.publishedDate && (
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {format(new Date(content.publishedDate), 'MMM d, yyyy')}
                    </span>
                  )}
                  {content.duration && (
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDuration(content.duration)}
                    </span>
                  )}
                </div>
              </div>
              {(content.videoId || content.video_id) && (
                <Button variant="outline" size="sm" asChild>
                  <a 
                    href={`https://youtube.com/watch?v=${content.videoId || content.video_id}`} 
                    target="_blank" 
                    rel="noopener noreferrer"
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    YouTube
                  </a>
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="description">
              <TabsList>
                <TabsTrigger value="description">Description</TabsTrigger>
                {content.transcript && <TabsTrigger value="transcript">Transcript</TabsTrigger>}
                <TabsTrigger value="details">Details</TabsTrigger>
              </TabsList>
              
              <TabsContent value="description" className="mt-4">
                {/* AI Summary if available */}
                {content.aiSummary && (
                  <div className="mb-4 p-4 rounded-lg bg-gradient-to-r from-primary/5 to-accent/5 border border-primary/20">
                    <div className="flex items-start gap-3">
                      <Brain className="h-5 w-5 text-primary mt-0.5" />
                      <div className="flex-1">
                        <h4 className="text-sm font-medium mb-2">AI Summary</h4>
                        <p className="text-sm leading-relaxed">{content.aiSummary}</p>
                      </div>
                    </div>
                  </div>
                )}
                
                <p className="text-sm whitespace-pre-wrap">
                  {content.abstract || content.description || 'No description available'}
                </p>
              </TabsContent>
              
              {content.transcript && (
                <TabsContent value="transcript" className="mt-4">
                  <div className="max-h-96 overflow-y-auto space-y-2 pr-2">
                    {transcriptParts.map((part, idx) => (
                      <div 
                        key={idx}
                        className="flex gap-3 p-2 rounded hover:bg-muted/50 cursor-pointer transition-colors"
                        onClick={() => handleTimestampClick(part.timestamp)}
                      >
                        <span className="text-xs font-mono text-primary whitespace-nowrap">
                          {part.time}
                        </span>
                        <span className="text-sm flex-1">{part.text}</span>
                      </div>
                    ))}
                    {transcriptParts.length === 0 && (
                      <p className="text-sm text-muted-foreground">
                        {content.transcript}
                      </p>
                    )}
                  </div>
                </TabsContent>
              )}
              
              <TabsContent value="details" className="mt-4 space-y-4">
                {/* Categories */}
                {content.categories && content.categories.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium mb-2 flex items-center gap-2">
                      <Target className="h-4 w-4 text-primary" />
                      OHDSI Categories
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {content.categories.map((category: string) => (
                        <Link
                          key={category}
                          href={`/explorer?category=${encodeURIComponent(category)}`}
                        >
                          <Badge 
                            variant="secondary" 
                            className="cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors"
                          >
                            {category}
                          </Badge>
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Tags */}
                {content.tags && content.tags.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium mb-2">Video Tags</h3>
                    <div className="flex flex-wrap gap-1">
                      {content.tags.map((tag: string) => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
      
      {/* Sidebar */}
      <div className="space-y-6">
        {/* Channel Info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Channel</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <Avatar>
                <AvatarFallback>
                  {(content.channelName || content.channel_name) ? (content.channelName || content.channel_name)[0].toUpperCase() : 'C'}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1">
                <p className="font-medium">{content.channelName || content.channel_name || 'Unknown Channel'}</p>
                {(content.channelId || content.channel_id) && (
                  <Button variant="outline" size="sm" className="mt-1" asChild>
                    <a 
                      href={`https://youtube.com/channel/${content.channelId || content.channel_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      View Channel
                    </a>
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
        
        {/* Video Stats */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Statistics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {content.viewCount && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Views</span>
                  <span className="font-medium">{content.viewCount.toLocaleString()}</span>
                </div>
              )}
              {content.likeCount && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Likes</span>
                  <span className="font-medium">{content.likeCount.toLocaleString()}</span>
                </div>
              )}
              {content.commentCount && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Comments</span>
                  <span className="font-medium">{content.commentCount.toLocaleString()}</span>
                </div>
              )}
              {content.duration && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Duration</span>
                  <span className="font-medium">{formatDuration(content.duration)}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
        
        {/* Related Content */}
        {content.relatedContent && content.relatedContent.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Related Content</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {content.relatedContent
                  .slice(0, 5)
                  .map((related: any) => (
                    <Link
                      key={related.id}
                      href={`/content/${related.id}`}
                      className="block group"
                    >
                      <p className="text-sm font-medium line-clamp-2 group-hover:text-primary transition-colors">
                        {related.title}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {related.source === 'youtube' ? 'Video' : 
                           related.source === 'pubmed' ? 'Article' :
                           related.source === 'github' ? 'Repository' :
                           related.contentType}
                        </Badge>
                        {related.source === 'youtube' && (
                          <span className="text-xs text-muted-foreground">
                            {related.channel_name || related.channelName}
                          </span>
                        )}
                        {related.mlScore && (
                          <span className="text-xs text-muted-foreground ml-auto">
                            {(related.mlScore * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                    </Link>
                  ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}