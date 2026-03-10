'use client'

import { useQuery } from '@apollo/client'
import { GET_CONTENT } from '@/lib/graphql/queries'
import { detectSource } from './utils/sourceDetector'
import { ContentHeader } from './components/shared/ContentHeader'
import { ArticleDetail } from './components/sources/ArticleDetail'
import { VideoDetail } from './components/sources/VideoDetail'
import { RepoDetail } from './components/sources/RepoDetail'
import { DiscussionDetail } from './components/sources/DiscussionDetail'
import { DocDetail } from './components/sources/DocDetail'
import { Suspense } from 'react'

// Loading skeleton component
function ContentSkeleton() {
  return (
    <div className="container py-6">
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-3/4 mb-4"></div>
        <div className="h-4 bg-gray-200 rounded w-1/2 mb-8"></div>
        <div className="space-y-3">
          <div className="h-4 bg-gray-200 rounded"></div>
          <div className="h-4 bg-gray-200 rounded"></div>
          <div className="h-4 bg-gray-200 rounded"></div>
        </div>
      </div>
    </div>
  )
}

// Error component
function ContentError({ message }: { message: string }) {
  return (
    <div className="container py-6">
      <div className="text-center py-12">
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">
          Content Not Found
        </h2>
        <p className="text-gray-600 mb-6">{message}</p>
        <button
          onClick={() => window.history.back()}
          className="px-4 py-2 bg-primary text-white rounded hover:bg-primary/90"
        >
          Go Back
        </button>
      </div>
    </div>
  )
}

export default function ContentDetailPage({ params }: { params: { id: string } }) {
  const { data, loading, error } = useQuery(GET_CONTENT, {
    variables: { id: params.id },
  })

  if (loading) {
    return <ContentSkeleton />
  }

  if (error || !data?.content) {
    return (
      <ContentError 
        message={error?.message || 'The requested content could not be found.'}
      />
    )
  }

  const content = data.content
  const source = detectSource(content)

  // Render source-specific component based on detected source
  const renderSourceContent = () => {
    switch (source) {
      case 'pubmed':
        return <ArticleDetail content={content} />
      
      case 'youtube':
        return <VideoDetail content={content} />
      
      case 'github':
        return <RepoDetail content={content} />
      
      case 'discourse':
        return <DiscussionDetail content={content} />
      
      case 'wiki':
        return <DocDetail content={content} />
      
      default:
        // Fallback to article display for unknown sources
        return <ArticleDetail content={content} />
    }
  }

  return (
    <div className="container py-6 max-w-7xl mx-auto">
      <div className="space-y-6">
        {/* Unified header component */}
        <ContentHeader content={content} source={source} />
        
        {/* Source-specific content display */}
        <Suspense fallback={<ContentSkeleton />}>
          {renderSourceContent()}
        </Suspense>
      </div>
    </div>
  )
}