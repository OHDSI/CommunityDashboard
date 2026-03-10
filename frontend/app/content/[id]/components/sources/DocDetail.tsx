'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  BookOpen,
  FileText,
  Link as LinkIcon,
  ExternalLink,
  ChevronRight,
  Target,
  Code,
  AlertCircle,
  Clock,
  Calendar,
  Hash,
  Brain
} from 'lucide-react'
import Link from 'next/link'
import { format } from 'date-fns'

interface DocDetailProps {
  content: any
}

interface TOCItem {
  id: string
  title: string
  level: number
  children?: TOCItem[]
}

export function DocDetail({ content }: DocDetailProps) {
  const docUrl = content.url
  
  // Parse table of contents if available
  const parseTableOfContents = (toc: any): TOCItem[] => {
    if (!toc) return []
    if (typeof toc === 'string') {
      // Simple parsing of string TOC
      return toc.split('\n').map((line, idx) => ({
        id: `section-${idx}`,
        title: line.trim(),
        level: line.startsWith('  ') ? 2 : 1
      }))
    }
    if (Array.isArray(toc)) {
      return toc
    }
    return []
  }
  
  const tableOfContents = parseTableOfContents(content.tableOfContents)
  
  const renderTOC = (items: TOCItem[], level = 0) => {
    return items.map((item) => (
      <div key={item.id} style={{ marginLeft: `${level * 16}px` }}>
        <a
          href={`#${item.id}`}
          className="flex items-center gap-2 py-1 text-sm hover:text-primary transition-colors"
        >
          {level > 0 && <ChevronRight className="h-3 w-3" />}
          <span className={level === 0 ? 'font-medium' : ''}>{item.title}</span>
        </a>
        {item.children && renderTOC(item.children, level + 1)}
      </div>
    ))
  }
  
  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* Main Content */}
      <div className="lg:col-span-3 space-y-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Documentation</CardTitle>
              {docUrl && (
                <Button variant="outline" size="sm" asChild>
                  <a href={docUrl} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="h-4 w-4 mr-2" />
                    View Original
                  </a>
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="content">
              <TabsList>
                <TabsTrigger value="content">Content</TabsTrigger>
                {content.codeExamples && <TabsTrigger value="examples">Code Examples</TabsTrigger>}
                <TabsTrigger value="metadata">Details</TabsTrigger>
                <TabsTrigger value="related">Related</TabsTrigger>
              </TabsList>
              
              <TabsContent value="content" className="mt-4">
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
                
                {/* Main Documentation Content */}
                <div className="prose prose-sm max-w-none">
                  {content.content ? (
                    <div 
                      dangerouslySetInnerHTML={{ __html: content.htmlContent || content.content }}
                      className="doc-content"
                    />
                  ) : content.abstract ? (
                    <p className="whitespace-pre-wrap">{content.abstract}</p>
                  ) : (
                    <div className="text-center py-8">
                      <BookOpen className="h-12 w-12 text-muted-foreground/30 mx-auto mb-3" />
                      <p className="text-muted-foreground">Documentation content not available.</p>
                      {docUrl && (
                        <Button variant="outline" size="sm" className="mt-3" asChild>
                          <a href={docUrl} target="_blank" rel="noopener noreferrer">
                            View on Original Site
                          </a>
                        </Button>
                      )}
                    </div>
                  )}
                </div>
                
                {/* Learning Objectives */}
                {content.learningObjectives && content.learningObjectives.length > 0 && (
                  <div className="mt-6 p-4 bg-muted/30 rounded-lg">
                    <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                      <Target className="h-4 w-4 text-primary" />
                      Learning Objectives
                    </h3>
                    <ul className="space-y-2">
                      {content.learningObjectives.map((objective: string, idx: number) => (
                        <li key={idx} className="flex items-start gap-2 text-sm">
                          <span className="text-primary mt-0.5">•</span>
                          <span>{objective}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </TabsContent>
              
              {content.codeExamples && (
                <TabsContent value="examples" className="mt-4">
                  <div className="space-y-4">
                    {content.codeExamples.map((example: any, idx: number) => (
                      <div key={idx} className="border rounded-lg overflow-hidden">
                        <div className="bg-muted px-4 py-2 flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Code className="h-4 w-4" />
                            <span className="text-sm font-medium">
                              {example.title || `Example ${idx + 1}`}
                            </span>
                          </div>
                          {example.language && (
                            <Badge variant="secondary" className="text-xs">
                              {example.language}
                            </Badge>
                          )}
                        </div>
                        <pre className="p-4 bg-black text-white overflow-x-auto">
                          <code className="text-sm">{example.code}</code>
                        </pre>
                        {example.description && (
                          <div className="p-4 bg-muted/30 text-sm">
                            {example.description}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </TabsContent>
              )}
              
              <TabsContent value="metadata" className="mt-4 space-y-4">
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
                
                {/* Document Info */}
                <div>
                  <h3 className="text-sm font-medium mb-3">Document Information</h3>
                  <dl className="grid grid-cols-2 gap-4 text-sm">
                    {content.docType && (
                      <>
                        <dt className="text-muted-foreground">Type</dt>
                        <dd>{content.docType}</dd>
                      </>
                    )}
                    {content.version && (
                      <>
                        <dt className="text-muted-foreground">Version</dt>
                        <dd>{content.version}</dd>
                      </>
                    )}
                    {content.lastModified && (
                      <>
                        <dt className="text-muted-foreground">Last Updated</dt>
                        <dd>{format(new Date(content.lastModified), 'MMM d, yyyy')}</dd>
                      </>
                    )}
                    {content.sectionCount && (
                      <>
                        <dt className="text-muted-foreground">Sections</dt>
                        <dd>{content.sectionCount}</dd>
                      </>
                    )}
                    {content.wordCount && (
                      <>
                        <dt className="text-muted-foreground">Word Count</dt>
                        <dd>{content.wordCount.toLocaleString()}</dd>
                      </>
                    )}
                    {content.readingTime && (
                      <>
                        <dt className="text-muted-foreground">Reading Time</dt>
                        <dd>{content.readingTime} min</dd>
                      </>
                    )}
                  </dl>
                </div>
                
                {/* Prerequisites */}
                {content.prerequisites && content.prerequisites.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-orange-500" />
                      Prerequisites
                    </h3>
                    <ul className="space-y-1">
                      {content.prerequisites.map((prereq: string, idx: number) => (
                        <li key={idx} className="text-sm text-muted-foreground">
                          • {prereq}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {/* Tools Mentioned */}
                {content.aiTools && content.aiTools.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium mb-3">OHDSI Tools Mentioned</h3>
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
              </TabsContent>
              
              <TabsContent value="related" className="mt-4">
                {content.relatedContent && content.relatedContent.length > 0 ? (
                  <div className="space-y-3">
                    {content.relatedContent
                      .filter((item: any) => item.source === 'wiki' || item.contentType === 'documentation')
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
                                {related.docType && (
                                  <Badge variant="outline" className="text-xs">
                                    {related.docType}
                                  </Badge>
                                )}
                                {related.lastModified && (
                                  <span className="flex items-center gap-1">
                                    <Clock className="h-3 w-3" />
                                    {format(new Date(related.lastModified), 'MMM yyyy')}
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
                    <FileText className="h-12 w-12 text-muted-foreground/30 mx-auto mb-3" />
                    <p className="text-muted-foreground">No related documentation found.</p>
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
      
      {/* Sidebar */}
      <div className="space-y-6">
        {/* Table of Contents */}
        {tableOfContents.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <Hash className="h-4 w-4" />
                Table of Contents
              </CardTitle>
            </CardHeader>
            <CardContent>
              <nav className="space-y-1">
                {renderTOC(tableOfContents)}
              </nav>
            </CardContent>
          </Card>
        )}
        
        {/* Quick Info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Quick Info</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 text-sm">
              {content.docType && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Type</span>
                  <Badge variant="outline">{content.docType}</Badge>
                </div>
              )}
              {content.readingTime && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Reading Time</span>
                  <span>{content.readingTime} min</span>
                </div>
              )}
              {content.lastModified && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Updated</span>
                  <span>{format(new Date(content.lastModified), 'MMM yyyy')}</span>
                </div>
              )}
              {content.version && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Version</span>
                  <span>{content.version}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
        
        {/* External Links */}
        {(content.references || content.externalLinks) && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">References</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {(content.references || content.externalLinks || []).map((link: any, idx: number) => (
                  <a
                    key={idx}
                    href={link.url || link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-sm text-primary hover:underline"
                  >
                    <LinkIcon className="h-3 w-3" />
                    <span className="truncate">{link.title || link.url || link}</span>
                  </a>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}