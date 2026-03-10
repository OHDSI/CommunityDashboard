export type ContentSource = 'pubmed' | 'youtube' | 'github' | 'discourse' | 'wiki'

export interface SourceConfig {
  icon: any // Will be imported from lucide-react
  color: string
  label: string
  primaryAction: string
  gradient: string
}

export function detectSource(content: any): ContentSource {
  // Explicit source field (most reliable)
  if (content.source) {
    return content.source as ContentSource
  }
  
  // Fallback detection by unique fields
  if (content.pmid || content.journal || content.meshTerms) {
    return 'pubmed'
  }
  
  if (content.video_id || content.videoId || content.channel_name || content.channelName || content.duration) {
    return 'youtube'
  }
  
  if (content.repoName || content.starsCount || content.forksCount) {
    return 'github'
  }
  
  if (content.topicId || content.solved !== undefined || content.replyCount) {
    return 'discourse'
  }
  
  if (content.docType || content.tableOfContents || content.sectionCount) {
    return 'wiki'
  }
  
  // Default fallback to pubmed (most common)
  return 'pubmed'
}

export function getTabsForSource(source: ContentSource): string[] {
  const tabConfigurations: Record<ContentSource, string[]> = {
    pubmed: ['abstract', 'details', 'citations', 'related'],
    youtube: ['video', 'transcript', 'details', 'related'],
    github: ['readme', 'code', 'contributors', 'related'],
    discourse: ['discussion', 'replies', 'participants', 'related'],
    wiki: ['content', 'navigation', 'references', 'related']
  }
  
  return tabConfigurations[source]
}

export function getDefaultTabForSource(source: ContentSource): string {
  const defaults: Record<ContentSource, string> = {
    pubmed: 'abstract',
    youtube: 'video',
    github: 'readme',
    discourse: 'discussion',
    wiki: 'content'
  }
  
  return defaults[source]
}

// Helper to format duration for YouTube videos
export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return ''
  
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}

// Helper to format view counts
export function formatViews(count: number | null | undefined): string {
  if (!count) return '0'
  
  if (count >= 1000000) {
    return `${(count / 1000000).toFixed(1)}M`
  }
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`
  }
  return count.toString()
}