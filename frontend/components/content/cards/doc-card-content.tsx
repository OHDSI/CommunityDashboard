import {
  BookOpen,
  Timer,
  Clock,
} from 'lucide-react'
import { formatRelativeTime, formatReadTime } from '@/lib/utils/format'

export interface DocCardContentProps {
  section_count?: number
  read_time?: number
  updated_at?: string
}

export function DocCardContent({
  section_count,
  read_time,
  updated_at,
}: DocCardContentProps) {
  return (
    <div className="space-y-2 mb-3">
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        {section_count && (
          <div className="flex items-center gap-1">
            <BookOpen className="h-3 w-3" />
            <span>{section_count} sections</span>
          </div>
        )}
        {read_time && (
          <div className="flex items-center gap-1">
            <Timer className="h-3 w-3" />
            <span>{formatReadTime(read_time)}</span>
          </div>
        )}
      </div>

      {updated_at && (
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>Updated {formatRelativeTime(updated_at)}</span>
        </div>
      )}
    </div>
  )
}
