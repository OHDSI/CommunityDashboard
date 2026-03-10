import { gql } from '@apollo/client'

export const SEARCH_CONTENT = gql`
  query SearchContent($query: String, $filters: JSON, $size: Int, $offset: Int, $sortBy: String) {
    searchContent(query: $query, filters: $filters, size: $size, offset: $offset, sortBy: $sortBy) {
      total
      items {
        id
        title
        abstract
        contentType
        
        # Multimodal fields
        source
        displayType
        iconType
        contentCategory
        
        authors {
          name
          email
          affiliation
        }
        publishedDate
        createdAt
        mlScore
        finalScore
        categories
        
        # AI Enhancement fields (snake_case in backend, camelCase in GraphQL)
        aiEnhanced
        aiIsOhdsi
        aiConfidence
        aiSummary
        aiTools
        
        
        metrics {
          viewCount
          bookmarkCount
          shareCount
        }
        url
        journal
        year
        
        # YouTube specific
        videoId
        duration
        channelName
        thumbnailUrl
        
        # GitHub specific
        repoName
        starsCount
        forksCount
        language
        
        # Discourse specific
        topicId
        replyCount
        solved
        
        # Wiki specific
        docType
        sectionCount
      }
      aggregations
      tookMs
    }
  }
`

export const GET_CONTENT = gql`
  query GetContent($id: String!) {
    content(id: $id) {
      id
      title
      abstract
      contentType
      
      # Multimodal fields
      source
      displayType
      iconType
      contentCategory
      
      authors {
        name
        email
        affiliation
      }
      publishedDate
      mlScore
      finalScore
      categories
      
      # AI Enhancement fields
      aiEnhanced
      aiIsOhdsi
      aiConfidence
      aiSummary
      aiTools
      
      # Citations (stored as JSON)
      citations
      
      
      metrics {
        viewCount
        bookmarkCount
        shareCount
      }
      url
      journal
      doi
      keywords
      year
      
      # YouTube specific
      videoId
      duration
      channelName
      thumbnailUrl
      
      # GitHub specific
      repoName
      starsCount
      watchersCount
      forksCount
      openIssuesCount
      contributorsCount
      contributors
      readmeContent
      language
      license
      topics
      lastCommit
      
      # Discourse specific
      topicId
      replyCount
      solved
      
      # Wiki specific
      docType
      sectionCount
      lastModified
      
      relatedContent {
        id
        title
        contentType
        source
        displayType
        mlScore
        publishedDate
        aiEnhanced
        aiConfidence
      }
    }
  }
`

export const GET_REVIEW_QUEUE = gql`
  query GetReviewQueue($status: String, $source: String) {
    reviewQueue(status: $status, source: $source) {
      id
      title
      abstract
      contentType
      source
      displayType
      iconType
      contentCategory
      url
      mlScore
      finalScore
      qualityScore
      categories

      # AI Enhancement fields
      aiEnhanced
      aiIsOhdsi
      aiConfidence
      aiSummary
      aiTools

      status
      submittedDate
      priority
    }
  }
`

export const GET_ME = gql`
  query GetMe {
    me {
      id
      email
      fullName
      organization
      role
    }
  }
`

export const LIST_USERS = gql`
  query ListUsers {
    listUsers {
      id
      email
      fullName
      role
      isActive
      createdAt
      lastLogin
    }
  }
`

export const SEMANTIC_SEARCH = gql`
  query SemanticSearch($query: String!, $filters: JSON, $size: Int, $offset: Int, $minScore: Float, $sortBy: String) {
    semanticSearch(query: $query, filters: $filters, size: $size, offset: $offset, minScore: $minScore, sortBy: $sortBy) {
      total
      items {
        id
        title
        abstract
        contentType
        source
        displayType
        iconType
        contentCategory
        authors {
          name
        }
        publishedDate
        mlScore
        finalScore
        aiConfidence
        categories
        metrics {
          viewCount
          bookmarkCount
          shareCount
          citationCount
        }
        url
      }
      aggregations
      tookMs
    }
  }
`

export const HYBRID_SEARCH = gql`
  query HybridSearch($query: String!, $filters: JSON, $size: Int, $offset: Int, $keywordWeight: Float, $semanticWeight: Float, $sortBy: String) {
    hybridSearch(query: $query, filters: $filters, size: $size, offset: $offset, keywordWeight: $keywordWeight, semanticWeight: $semanticWeight, sortBy: $sortBy) {
      total
      items {
        id
        title
        abstract
        contentType
        source
        displayType
        iconType
        contentCategory
        authors {
          name
        }
        publishedDate
        mlScore
        finalScore
        aiConfidence
        categories
        metrics {
          viewCount
          bookmarkCount
          shareCount
          citationCount
        }
        url
      }
      aggregations
      tookMs
    }
  }
`