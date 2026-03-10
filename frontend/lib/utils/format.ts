/**
 * Formatting utilities for dates, durations, and read times.
 * These provide custom formatting logic beyond what date-fns offers
 * (compact relative times, duration from seconds, read time estimates).
 */

/**
 * Formats a date string into a human-readable format.
 * Uses Intl.DateTimeFormat for locale-aware short date display.
 *
 * @param dateString - ISO date string to format
 * @returns Formatted date string (e.g. "Mar 6, 2026") or null if input is falsy
 */
export function formatDate(dateString?: string): string | null {
  if (!dateString) return null
  const date = new Date(dateString)
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  }).format(date)
}

/**
 * Formats a date string into a compact relative time representation.
 * Returns "Just now", "Xm ago", "Xh ago", "Xd ago", or falls back to formatDate.
 *
 * Note: This provides more compact output than date-fns formatDistanceToNow()
 * (e.g. "5m ago" vs "5 minutes ago"), which is important for card layouts.
 *
 * @param dateString - ISO date string to format
 * @returns Compact relative time string or null if input is falsy
 */
export function formatRelativeTime(dateString?: string): string | null {
  if (!dateString) return null
  const date = new Date(dateString)
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (diffInSeconds < 60) return 'Just now'
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`
  return formatDate(dateString)
}

/**
 * Formats a duration in seconds to a readable time format.
 * Used primarily for YouTube video durations.
 *
 * @param seconds - Duration in seconds
 * @returns Formatted duration string (e.g. "1:23:45" or "5:30") or null if input is falsy
 */
export function formatDuration(seconds?: number): string | null {
  if (!seconds) return null
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60

  if (hours > 0) return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}

/**
 * Formats a read time estimate in minutes to a human-readable string.
 *
 * @param minutes - Estimated read time in minutes
 * @returns Read time string (e.g. "5 min read") or null if input is falsy
 */
export function formatReadTime(minutes?: number): string | null {
  if (!minutes) return null
  if (minutes < 1) return '< 1 min read'
  return `${Math.round(minutes)} min read`
}
