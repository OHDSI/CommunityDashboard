import {
  FileText,
  Video,
  Code,
  MessageSquare,
  BookOpen,
  Github,
  type LucideIcon
} from 'lucide-react'

/**
 * Source color scheme for styling badges, hover states, and accents.
 */
export interface SourceColors {
  badge: string
  hover: string
  accent: string
}

/**
 * Returns the appropriate Lucide icon component for a given content source.
 * Handles both source strings and icon type hints.
 *
 * @param source - The content source identifier (e.g. 'pubmed', 'github')
 * @param iconType - Optional icon type hint from display fields
 * @returns The Lucide icon component
 */
export function getSourceIcon(source?: string, iconType?: string): LucideIcon {
  if (iconType === 'play-circle' || source === 'youtube') return Video
  if (iconType === 'code' || source === 'github') return Github
  if (iconType === 'chat-bubble' || source === 'discourse') return MessageSquare
  if (iconType === 'book-open' || source === 'wiki') return BookOpen
  if (iconType === 'document-text' || source === 'pubmed') return FileText
  return FileText
}

/**
 * Returns color classes for styling based on content source.
 * Provides badge, hover, and accent color variants.
 *
 * @param source - The content source identifier
 * @returns Object with badge, hover, and accent CSS class strings
 */
export function getSourceColors(source?: string): SourceColors {
  switch (source) {
    case 'youtube':
      return {
        badge: 'bg-red-100 text-red-800 border-red-300',
        hover: 'hover:shadow-red-200/50',
        accent: 'text-red-600'
      }
    case 'github':
      return {
        badge: 'bg-gray-100 text-gray-800 border-gray-300',
        hover: 'hover:shadow-gray-200/50',
        accent: 'text-gray-600'
      }
    case 'discourse':
      return {
        badge: 'bg-blue-100 text-blue-800 border-blue-300',
        hover: 'hover:shadow-blue-200/50',
        accent: 'text-blue-600'
      }
    case 'wiki':
      return {
        badge: 'bg-amber-100 text-amber-800 border-amber-300',
        hover: 'hover:shadow-amber-200/50',
        accent: 'text-amber-600'
      }
    case 'pubmed':
      return {
        badge: 'bg-green-100 text-green-800 border-green-300',
        hover: 'hover:shadow-green-200/50',
        accent: 'text-green-600'
      }
    default:
      return {
        badge: 'bg-gray-100 text-gray-800 border-gray-300',
        hover: 'hover:shadow-gray-200/50',
        accent: 'text-gray-600'
      }
  }
}

/**
 * Returns a human-readable display label for a content source.
 *
 * @param source - The content source identifier
 * @param fallback - Optional fallback label if source is unknown
 * @returns The display label string
 */
export function getSourceLabel(source?: string, fallback?: string): string {
  switch (source) {
    case 'pubmed':
      return 'PubMed'
    case 'github':
      return 'GitHub'
    case 'youtube':
      return 'YouTube'
    case 'discourse':
      return 'Forum'
    case 'wiki':
      return 'Wiki'
    default:
      return fallback || 'Content'
  }
}

/**
 * GitHub language colors for popular programming languages.
 *
 * @param language - The programming language name
 * @returns A hex color string
 */
export function getLanguageColor(language?: string): string {
  const colors: Record<string, string> = {
    'JavaScript': '#f1e05a',
    'TypeScript': '#3178c6',
    'Python': '#3572A5',
    'Java': '#b07219',
    'C++': '#f34b7d',
    'C#': '#239120',
    'PHP': '#4F5D95',
    'Ruby': '#701516',
    'Go': '#00ADD8',
    'Rust': '#dea584',
    'Swift': '#ffac45',
    'Kotlin': '#A97BFF',
    'R': '#198CE7'
  }
  return colors[language || ''] || '#6B7280'
}
