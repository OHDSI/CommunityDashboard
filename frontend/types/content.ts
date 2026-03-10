/**
 * Content types aligned with Schema v3 structure
 * Supporting multi-source content (PubMed, YouTube, GitHub, Discourse, Wiki)
 */

export interface Author {
  name: string
  email?: string
  affiliation?: string
  orcid?: string
}

export interface ContentMetrics {
  view_count: number
  bookmark_count: number
  share_count: number
  citation_count: number
}

export interface Citations {
  cited_by_count: number
  references_count: number
  cited_by_ids: string[]
  reference_ids: string[]
}

export interface AIEnhancement {
  ai_enhanced: boolean
  ai_confidence?: number  // Schema v3: replaces ai_quality_score
  ai_summary?: string
  ai_tools?: string[]
  ai_categories?: string[]
}

// Base content interface with all source-specific fields
export interface ContentItem extends YouTubeFields, GitHubFields, DiscourseFields, WikiFields, PubMedFields {
  id: string
  title: string
  description?: string
  abstract?: string
  content?: string
  content_type: string
  
  // Source information
  source: 'pubmed' | 'youtube' | 'github' | 'discourse' | 'wiki'
  display_type?: string  // Computed field
  icon_type?: string     // Computed field
  content_category?: string  // Computed field
  
  // Authors and metadata
  authors: Author[]
  
  // Dates
  published_date?: string
  created_at?: string
  updated_at?: string
  last_activity?: string
  last_modified?: string
  
  // Categories and scoring - Schema v3
  categories: string[]
  final_score?: number  // Schema v3: replaces combined_score
  ml_score?: number
  
  // Metrics
  metrics: ContentMetrics
  
  // AI Enhancement - Schema v3
  ai_enhanced?: boolean
  ai_confidence?: number
  ai_summary?: string
  ai_tools?: string[]
  ai_categories?: string[]
  
  // URLs
  url?: string
  thumbnail_url?: string
  
  // Search highlighting
  highlight?: Record<string, string[]>
  
  // Citations
  citations?: Citations
}

// Source-specific fields are included in base ContentItem interface
// YouTube-specific fields
export interface YouTubeFields {
  video_id?: string
  duration?: number
  channel_name?: string
  thumbnail_url?: string
}

// GitHub-specific fields
export interface GitHubFields {
  repo_name?: string
  stars_count?: number
  forks_count?: number
  language?: string
  topics?: string[]
  owner?: string
  last_commit?: string
}

// Discourse-specific fields
export interface DiscourseFields {
  topic_id?: number
  reply_count?: number
  solved?: boolean
  category?: string
  tags?: string[]
}

// Wiki-specific fields
export interface WikiFields {
  doc_type?: string
  section_count?: number
  read_time?: number
}

// PubMed-specific fields
export interface PubMedFields {
  journal?: string
  institutions?: string[]
  mesh_terms?: string[]
  pmid?: string
  doi?: string
  year?: number
}

// Union type for all content types (simplified since ContentItem includes all fields)
export type AnyContentItem = ContentItem

// Sort options
export type SortOption = 'relevance' | 'date' | 'popularity' | 'score' | 'title'

// View modes
export type ViewMode = 'compact' | 'expanded' | 'grouped'
export type LayoutMode = 'list' | 'grid'

// Filter options
export interface ContentFilters {
  sources?: Array<'pubmed' | 'youtube' | 'github' | 'discourse' | 'wiki'>
  categories?: string[]
  dateRange?: {
    start?: string
    end?: string
  }
  scoreRange?: {
    min?: number
    max?: number
  }
  contentTypes?: string[]
  languages?: string[]
}

// Search result structure
export interface SearchResult {
  total: number
  items: ContentItem[]
  aggregations: Record<string, any>
  took_ms: number
}

// Error types
export interface ContentError {
  message: string
  code?: string
  details?: any
}

// Loading state
export interface LoadingState {
  loading: boolean
  error?: ContentError
  progress?: number
}