/**
 * Utility functions for computing display fields from content source and type.
 * These fields are no longer stored in Elasticsearch but computed at query time.
 */

export interface DisplayFields {
  display_type: string
  icon_type: string
  content_category: string
}

/**
 * Get display fields based on source and content type.
 * This replaces the previously stored fields in Elasticsearch.
 * 
 * @param item - Object with source and/or content_type fields
 * @returns DisplayFields with computed display values
 */
export function getDisplayFields(item: { source?: string; content_type?: string }): DisplayFields {
  const source = item.source || ''
  const contentType = item.content_type || ''
  
  // Check by source first (most specific)
  if (source === 'youtube' || contentType === 'video') {
    return {
      display_type: 'Video Content',
      icon_type: 'play-circle',
      content_category: 'media'
    }
  } else if (source === 'pubmed' || contentType === 'article') {
    return {
      display_type: 'Research Article',
      icon_type: 'document-text',
      content_category: 'research'
    }
  } else if (source === 'github' || contentType === 'repository') {
    return {
      display_type: 'Code Repository',
      icon_type: 'code',
      content_category: 'code'
    }
  } else if (source === 'discourse' || contentType === 'discussion') {
    return {
      display_type: 'Forum Discussion',
      icon_type: 'chat-bubble',
      content_category: 'community'
    }
  } else if (source === 'wiki' || contentType === 'documentation') {
    return {
      display_type: 'Documentation',
      icon_type: 'book-open',
      content_category: 'reference'
    }
  }
  
  // Default fallback
  return {
    display_type: 'Content',
    icon_type: 'document',
    content_category: 'other'
  }
}