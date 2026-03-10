'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { 
  MessageSquare,
  User,
  Calendar,
  Clock,
  CheckCircle,
  ExternalLink,
  ThumbsUp,
  Eye,
  Target,
  AlertCircle,
  Users
} from 'lucide-react'
import Link from 'next/link'
import { format, formatDistanceToNow } from 'date-fns'

interface DiscussionDetailProps {
  content: any
}

interface Reply {
  id: string
  author: string
  content: string
  createdAt: string
  likes?: number
  isAccepted?: boolean
}

export function DiscussionDetail({ content }: DiscussionDetailProps) {
  const forumUrl = content.url || `https://forums.ohdsi.org/t/${content.topicId}`
  
  // Parse replies if available
  const replies: Reply[] = content.replies || []
  
  return (
    <div className="space-y-6">
      {/* Discussion Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-blue-500" />
              <div>
                <p className="text-2xl font-bold">{content.replyCount || 0}</p>
                <p className="text-xs text-muted-foreground">Replies</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Eye className="h-4 w-4 text-green-500" />
              <div>
                <p className="text-2xl font-bold">{content.viewCount || 0}</p>
                <p className="text-xs text-muted-foreground">Views</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <ThumbsUp className="h-4 w-4 text-purple-500" />
              <div>
                <p className="text-2xl font-bold">{content.likeCount || 0}</p>
                <p className="text-xs text-muted-foreground">Likes</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-orange-500" />
              <div>
                <p className="text-2xl font-bold">{content.participantCount || 1}</p>
                <p className="text-xs text-muted-foreground">Participants</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Main Discussion */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CardTitle>Discussion</CardTitle>
              {content.solved && (
                <Badge variant="success" className="flex items-center gap-1">
                  <CheckCircle className="h-3 w-3" />
                  Solved
                </Badge>
              )}
              {content.pinned && (
                <Badge variant="secondary">
                  📌 Pinned
                </Badge>
              )}
            </div>
            <Button variant="outline" size="sm" asChild>
              <a href={forumUrl} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4 mr-2" />
                View on Forum
              </a>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="discussion">
            <TabsList>
              <TabsTrigger value="discussion">Original Post</TabsTrigger>
              <TabsTrigger value="replies">Replies ({replies.length})</TabsTrigger>
              <TabsTrigger value="participants">Participants</TabsTrigger>
              <TabsTrigger value="related">Related</TabsTrigger>
            </TabsList>
            
            <TabsContent value="discussion" className="mt-4">
              {/* Original Post */}
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <Avatar>
                    <AvatarFallback>
                      {content.author ? content.author[0].toUpperCase() : 'A'}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <p className="font-medium">{content.author || 'Unknown'}</p>
                      {content.authorBadges && content.authorBadges.includes('moderator') && (
                        <Badge variant="outline" className="text-xs">Moderator</Badge>
                      )}
                      {content.publishedDate && (
                        <span className="text-xs text-muted-foreground">
                          • {formatDistanceToNow(new Date(content.publishedDate), { addSuffix: true })}
                        </span>
                      )}
                    </div>
                    
                    {/* Post Content */}
                    <div className="prose prose-sm max-w-none">
                      {content.abstract || content.description ? (
                        <div 
                          dangerouslySetInnerHTML={{ 
                            __html: content.htmlContent || content.abstract || content.description 
                          }}
                          className="whitespace-pre-wrap"
                        />
                      ) : (
                        <p className="text-muted-foreground">No content available</p>
                      )}
                    </div>
                    
                    {/* Categories/Tags */}
                    {content.categories && content.categories.length > 0 && (
                      <div className="mt-4">
                        <p className="text-sm font-medium mb-2 flex items-center gap-2">
                          <Target className="h-4 w-4 text-primary" />
                          OHDSI Categories
                        </p>
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
                    
                    {/* Forum Tags */}
                    {content.tags && content.tags.length > 0 && (
                      <div className="mt-3">
                        <p className="text-sm font-medium mb-2">Forum Tags</p>
                        <div className="flex flex-wrap gap-1">
                          {content.tags.map((tag: string) => (
                            <Badge key={tag} variant="outline" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="replies" className="mt-4">
              {replies.length > 0 ? (
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {replies.map((reply, idx) => (
                    <div 
                      key={reply.id || idx}
                      className={`p-4 rounded-lg border ${
                        reply.isAccepted ? 'bg-green-50 border-green-200' : 'bg-muted/30'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <Avatar className="h-8 w-8">
                          <AvatarFallback>
                            {reply.author ? reply.author[0].toUpperCase() : 'R'}
                          </AvatarFallback>
                        </Avatar>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <p className="font-medium text-sm">{reply.author}</p>
                            {reply.isAccepted && (
                              <Badge variant="success" className="text-xs">
                                <CheckCircle className="h-3 w-3 mr-1" />
                                Accepted Answer
                              </Badge>
                            )}
                            {reply.createdAt && (
                              <span className="text-xs text-muted-foreground">
                                • {formatDistanceToNow(new Date(reply.createdAt), { addSuffix: true })}
                              </span>
                            )}
                          </div>
                          <div className="text-sm prose prose-sm max-w-none">
                            <p className="whitespace-pre-wrap">{reply.content}</p>
                          </div>
                          {reply.likes && reply.likes > 0 && (
                            <div className="flex items-center gap-1 mt-2">
                              <ThumbsUp className="h-3 w-3 text-muted-foreground" />
                              <span className="text-xs text-muted-foreground">{reply.likes}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <MessageSquare className="h-12 w-12 text-muted-foreground/30 mx-auto mb-3" />
                  <p className="text-muted-foreground">No replies yet.</p>
                  <Button variant="outline" size="sm" className="mt-3" asChild>
                    <a href={forumUrl} target="_blank" rel="noopener noreferrer">
                      Join the discussion
                    </a>
                  </Button>
                </div>
              )}
            </TabsContent>
            
            <TabsContent value="participants" className="mt-4">
              {content.participants && content.participants.length > 0 ? (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {content.participants.map((participant: any) => (
                    <div key={participant.name} className="flex items-center gap-2">
                      <Avatar className="h-8 w-8">
                        <AvatarFallback>
                          {participant.name ? participant.name[0].toUpperCase() : 'P'}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{participant.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {participant.posts || 1} {participant.posts === 1 ? 'post' : 'posts'}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No participant information available
                </p>
              )}
            </TabsContent>
            
            <TabsContent value="related" className="mt-4">
              {content.relatedContent && content.relatedContent.length > 0 ? (
                <div className="space-y-3">
                  {content.relatedContent
                    .filter((item: any) => item.source === 'discourse')
                    .slice(0, 5)
                    .map((related: any) => (
                      <Link
                        key={related.id}
                        href={`/content/${related.id}`}
                        className="block p-4 border rounded-lg hover:bg-muted/50 hover:border-primary/30 transition-all group"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <p className="font-medium group-hover:text-primary transition-colors line-clamp-2">
                              {related.title}
                            </p>
                            <div className="flex items-center gap-3 mt-2 text-sm text-muted-foreground">
                              {related.solved && (
                                <Badge variant="success" className="text-xs">
                                  <CheckCircle className="h-3 w-3 mr-1" />
                                  Solved
                                </Badge>
                              )}
                              {related.replyCount && (
                                <span className="flex items-center gap-1">
                                  <MessageSquare className="h-3 w-3" />
                                  {related.replyCount}
                                </span>
                              )}
                              {related.publishedDate && (
                                <span className="flex items-center gap-1">
                                  <Clock className="h-3 w-3" />
                                  {formatDistanceToNow(new Date(related.publishedDate), { addSuffix: true })}
                                </span>
                              )}
                            </div>
                          </div>
                          {related.mlScore && (
                            <Badge 
                              variant={related.mlScore > 0.8 ? "success" : "secondary"}
                              className="ml-3"
                            >
                              {(related.mlScore * 100).toFixed(0)}%
                            </Badge>
                          )}
                        </div>
                      </Link>
                    ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <MessageSquare className="h-12 w-12 text-muted-foreground/30 mx-auto mb-3" />
                  <p className="text-muted-foreground">No related discussions found.</p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}