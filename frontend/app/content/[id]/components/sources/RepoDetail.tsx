'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { 
  Star,
  GitFork,
  Eye,
  Code,
  Users,
  Calendar,
  GitBranch,
  ExternalLink,
  Copy,
  CheckCircle,
  Target,
  FileText
} from 'lucide-react'
import Link from 'next/link'
import { format } from 'date-fns'
import { useState } from 'react'

interface RepoDetailProps {
  content: any
}

interface LanguageBreakdown {
  name: string
  percentage: number
  color: string
}

export function RepoDetail({ content }: RepoDetailProps) {
  const [copiedClone, setCopiedClone] = useState(false)
  const repoUrl = content.url || `https://github.com/${content.owner || 'OHDSI'}/${content.repoName}`
  const cloneUrl = `${repoUrl}.git`

  const handleCopyClone = () => {
    navigator.clipboard.writeText(`git clone ${cloneUrl}`)
    setCopiedClone(true)
    setTimeout(() => setCopiedClone(false), 2000)
  }

  // Mock language breakdown if not provided
  const languageBreakdown: LanguageBreakdown[] = content.languages || [
    { name: content.language || 'Unknown', percentage: 100, color: '#3178c6' }
  ]

  return (
    <div className="space-y-6">
      {/* Repository Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Star className="h-4 w-4 text-yellow-500" />
              <div>
                <p className="text-2xl font-bold">{content.starsCount || 0}</p>
                <p className="text-xs text-muted-foreground">Stars</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <GitFork className="h-4 w-4 text-blue-500" />
              <div>
                <p className="text-2xl font-bold">{content.forksCount || 0}</p>
                <p className="text-xs text-muted-foreground">Forks</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Eye className="h-4 w-4 text-green-500" />
              <div>
                <p className="text-2xl font-bold">{content.watchersCount || 0}</p>
                <p className="text-xs text-muted-foreground">Watchers</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-purple-500" />
              <div>
                <p className="text-2xl font-bold">{content.contributorsCount || 1}</p>
                <p className="text-xs text-muted-foreground">Contributors</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Main Content */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Repository</CardTitle>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" asChild>
                <a href={repoUrl} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  View on GitHub
                </a>
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                onClick={handleCopyClone}
              >
                {copiedClone ? (
                  <>
                    <CheckCircle className="h-4 w-4 mr-2 text-green-500" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4 mr-2" />
                    Clone
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="readme">
            <TabsList>
              <TabsTrigger value="readme">README</TabsTrigger>
              <TabsTrigger value="code">Code Info</TabsTrigger>
              <TabsTrigger value="contributors">Contributors</TabsTrigger>
              <TabsTrigger value="related">Related</TabsTrigger>
            </TabsList>
            
            <TabsContent value="readme" className="mt-4">
              {content.readmeContent ? (
                <div className="prose prose-sm max-w-none">
                  <div 
                    dangerouslySetInnerHTML={{ __html: content.readmeContent }}
                    className="markdown-body"
                  />
                </div>
              ) : content.abstract ? (
                <div className="prose prose-sm max-w-none">
                  <p className="whitespace-pre-wrap">{content.abstract}</p>
                </div>
              ) : (
                <p className="text-muted-foreground">No README available</p>
              )}
              
              {/* Clone Command */}
              <div className="mt-6 p-4 bg-muted rounded-lg">
                <p className="text-sm font-medium mb-2">Clone this repository:</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 p-2 bg-background rounded text-xs font-mono">
                    git clone {cloneUrl}
                  </code>
                  <Button 
                    size="sm" 
                    variant="ghost"
                    onClick={handleCopyClone}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="code" className="mt-4 space-y-4">
              {/* Language Breakdown */}
              <div>
                <h3 className="text-sm font-medium mb-3">Languages</h3>
                <div className="space-y-2">
                  {languageBreakdown.map((lang) => (
                    <div key={lang.name} className="flex items-center gap-3">
                      <div 
                        className="w-3 h-3 rounded-full" 
                        style={{ backgroundColor: lang.color }}
                      />
                      <span className="text-sm flex-1">{lang.name}</span>
                      <span className="text-sm text-muted-foreground">
                        {lang.percentage.toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              
              {/* Topics */}
              {content.topics && content.topics.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium mb-3">Topics</h3>
                  <div className="flex flex-wrap gap-2">
                    {content.topics.map((topic: string) => (
                      <Badge key={topic} variant="secondary">
                        {topic}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Categories */}
              {content.categories && content.categories.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
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
              
              {/* Repository Info */}
              <div>
                <h3 className="text-sm font-medium mb-3">Repository Information</h3>
                <dl className="grid grid-cols-2 gap-4 text-sm">
                  {content.license && (
                    <>
                      <dt className="text-muted-foreground">License</dt>
                      <dd>{content.license}</dd>
                    </>
                  )}
                  {content.createdAt && (
                    <>
                      <dt className="text-muted-foreground">Created</dt>
                      <dd>{format(new Date(content.createdAt), 'MMM yyyy')}</dd>
                    </>
                  )}
                  {content.lastCommit && (
                    <>
                      <dt className="text-muted-foreground">Last Commit</dt>
                      <dd>{format(new Date(content.lastCommit), 'MMM d, yyyy')}</dd>
                    </>
                  )}
                  {content.openIssuesCount !== undefined && (
                    <>
                      <dt className="text-muted-foreground">Open Issues</dt>
                      <dd>{content.openIssuesCount}</dd>
                    </>
                  )}
                </dl>
              </div>
            </TabsContent>
            
            <TabsContent value="contributors" className="mt-4">
              {content.contributors && content.contributors.length > 0 ? (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {content.contributors.slice(0, 12).map((contributor: any) => (
                    <div key={contributor.login} className="flex items-center gap-2">
                      <Avatar className="h-8 w-8">
                        <AvatarFallback>
                          {contributor.login ? contributor.login[0].toUpperCase() : 'C'}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {contributor.login}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {contributor.contributions} commits
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No contributor information available
                </p>
              )}
            </TabsContent>
            
            <TabsContent value="related" className="mt-4">
              {content.relatedContent && content.relatedContent.length > 0 ? (
                <div className="space-y-3">
                  {content.relatedContent.map((related: any) => (
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
                            <Badge variant="outline" className="text-xs">
                              {related.source === 'github' ? 'Repository' : related.contentType}
                            </Badge>
                            {related.starsCount && (
                              <span className="flex items-center gap-1">
                                <Star className="h-3 w-3" />
                                {related.starsCount}
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
                  <Code className="h-12 w-12 text-muted-foreground/30 mx-auto mb-3" />
                  <p className="text-muted-foreground">No related repositories found.</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Check back later as we discover more connections.
                  </p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}