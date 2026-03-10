'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Users,
  Calendar,
  Brain,
  Target,
  Database,
  TrendingUp,
  GitBranch,
  FileText,
  Link as LinkIcon
} from 'lucide-react'
import Link from 'next/link'
import { format } from 'date-fns'

interface ArticleDetailProps {
  content: any
}

export function ArticleDetail({ content }: ArticleDetailProps) {
  const [showAllAuthors, setShowAllAuthors] = useState(false)
  // Extract PubMed ID
  const pubmedId = content.pmid || 
                   (content.id?.startsWith('PMID') ? content.id.replace('PMID', '') : content.id) ||
                   content.url?.match(/pubmed\/(\d+)/)?.[1] || 
                   content.pubmedId
  
  // Process citations
  const citations = content.citations
  let citationCount = 0
  let referenceCount = 0
  let similarCount = 0
  let enrichedCitations = []
  let enrichedReferences = []
  
  if (citations) {
    if (Array.isArray(citations)) {
      enrichedCitations = citations
      citationCount = citations.length
    } else if (citations.cited_by_count !== undefined) {
      citationCount = citations.cited_by_count || 0
      referenceCount = citations.references_count || 0
      similarCount = citations.similar?.length || 0
      
      if (citations.cited_by_ids?.[0]?.pmid) {
        enrichedCitations = citations.cited_by_ids
      }
      if (citations.reference_ids?.[0]?.pmid) {
        enrichedReferences = citations.reference_ids
      }
    }
  }

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-6">
        <Tabs defaultValue="abstract" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="abstract">Abstract</TabsTrigger>
            <TabsTrigger value="details">Details</TabsTrigger>
            {citations && (citationCount > 0 || referenceCount > 0) && (
              <TabsTrigger value="citations">Citations</TabsTrigger>
            )}
            <TabsTrigger value="related">Related</TabsTrigger>
          </TabsList>
          
          <TabsContent value="abstract" className="mt-6">
            {/* AI Summary if available */}
            {content.aiSummary && (
              <div className="mb-6 p-4 rounded-lg bg-gradient-to-r from-primary/5 to-accent/5 border border-primary/20">
                <div className="flex items-start gap-3">
                  <Brain className="h-5 w-5 text-primary mt-0.5" />
                  <div className="flex-1">
                    <h4 className="text-sm font-medium mb-2">AI Summary</h4>
                    <p className="text-sm leading-relaxed">{content.aiSummary}</p>
                  </div>
                </div>
              </div>
            )}
            
            {content.abstract ? (
              <div className="prose prose-sm max-w-none">
                <p className="leading-relaxed text-foreground whitespace-pre-wrap">
                  {content.abstract}
                </p>
              </div>
            ) : (
              <p className="text-muted-foreground text-center py-8">
                No abstract available for this article.
              </p>
            )}
          </TabsContent>
          
          <TabsContent value="details" className="space-y-6 mt-6">
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

            {/* Keywords/MeSH Terms */}
            {content.keywords && content.keywords.length > 0 && (
              <div>
                <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <Brain className="h-4 w-4 text-accent" />
                  Medical Subject Headings
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {content.keywords.map((keyword: string) => (
                    <Link
                      key={keyword}
                      href={`/search?q=${encodeURIComponent(keyword)}`}
                    >
                      <Badge 
                        variant="outline" 
                        className="text-xs cursor-pointer hover:bg-accent/10 hover:text-accent hover:border-accent transition-colors"
                      >
                        {keyword}
                      </Badge>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* AI Tools */}
            {content.aiTools && content.aiTools.length > 0 && (
              <div>
                <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <Database className="h-4 w-4 text-blue-600" />
                  OHDSI Tools Mentioned
                </h3>
                <div className="flex flex-wrap gap-2">
                  {content.aiTools.map((tool: string) => (
                    <Badge 
                      key={tool}
                      variant="secondary" 
                      className="bg-blue-50 text-blue-700 border-blue-200"
                    >
                      {tool}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Authors */}
            {content.authors && content.authors.length > 0 && (
              <div>
                <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <Users className="h-4 w-4 text-primary" />
                  Authors ({content.authors.length})
                </h3>
                <div className="grid gap-3">
                  {(showAllAuthors ? content.authors : content.authors.slice(0, 5)).map((author: any, index: number) => (
                    <div key={index} className="flex items-start justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
                      <div>
                        <p className="font-medium">{author.name}</p>
                        {author.affiliation && (
                          <p className="text-sm text-muted-foreground">{author.affiliation}</p>
                        )}
                      </div>
                      {author.email && (
                        <Button variant="ghost" size="sm" asChild>
                          <a href={`mailto:${author.email}`}>Contact</a>
                        </Button>
                      )}
                    </div>
                  ))}
                  {content.authors.length > 5 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowAllAuthors(!showAllAuthors)}
                    >
                      {showAllAuthors
                        ? 'Show fewer authors'
                        : `Show all ${content.authors.length} authors`
                      }
                    </Button>
                  )}
                </div>
              </div>
            )}

            {/* Metadata */}
            <div>
              <h3 className="text-sm font-medium mb-3">Article Information</h3>
              <dl className="grid grid-cols-2 gap-4 text-sm">
                {pubmedId && (
                  <>
                    <dt className="text-muted-foreground">PubMed ID</dt>
                    <dd className="font-mono">{pubmedId}</dd>
                  </>
                )}
                {content.doi && (
                  <>
                    <dt className="text-muted-foreground">DOI</dt>
                    <dd className="font-mono text-xs break-all">{content.doi}</dd>
                  </>
                )}
                {content.journal && (
                  <>
                    <dt className="text-muted-foreground">Journal</dt>
                    <dd>{content.journal}</dd>
                  </>
                )}
                {content.year && (
                  <>
                    <dt className="text-muted-foreground">Year</dt>
                    <dd>{content.year}</dd>
                  </>
                )}
              </dl>
            </div>
          </TabsContent>
          
          {/* Citations Tab */}
          {citations && (citationCount > 0 || referenceCount > 0) && (
            <TabsContent value="citations" className="mt-6">
              <div className="space-y-6">
                {/* Citation Summary */}
                <div className="grid gap-4 md:grid-cols-3">
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-primary" />
                        Cited By
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-2xl font-bold text-primary">{citationCount}</p>
                      <p className="text-xs text-muted-foreground mt-1">Papers citing this work</p>
                    </CardContent>
                  </Card>
                  
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <GitBranch className="h-4 w-4 text-green-600" />
                        References
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-2xl font-bold text-green-600">{referenceCount}</p>
                      <p className="text-xs text-muted-foreground mt-1">Papers referenced</p>
                    </CardContent>
                  </Card>
                  
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <Brain className="h-4 w-4 text-purple-600" />
                        Similar Papers
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-2xl font-bold text-purple-600">{similarCount}</p>
                      <p className="text-xs text-muted-foreground mt-1">Related research</p>
                    </CardContent>
                  </Card>
                </div>
                
                {/* Visualization Button */}
                {pubmedId && (
                  <div className="text-center py-6">
                    <Button asChild size="lg">
                      <Link href={`/citations?paper=${pubmedId}`}>
                        <GitBranch className="h-5 w-5 mr-2" />
                        Explore Full Citation Network
                      </Link>
                    </Button>
                    <p className="text-sm text-muted-foreground mt-2">
                      Interactive visualization with {citationCount + referenceCount} connections
                    </p>
                  </div>
                )}
              </div>
            </TabsContent>
          )}
          
          <TabsContent value="related" className="mt-6">
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
                            {related.contentType}
                          </Badge>
                          {related.publishedDate && (
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {format(new Date(related.publishedDate), 'MMM yyyy')}
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
                <Brain className="h-12 w-12 text-muted-foreground/30 mx-auto mb-3" />
                <p className="text-muted-foreground">No related content found yet.</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Check back later as we discover more connections.
                </p>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}