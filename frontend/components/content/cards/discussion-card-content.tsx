import {
  MessageSquare,
  Clock,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { formatRelativeTime } from '@/lib/utils/format'

export interface DiscussionCardContentProps {
  reply_count?: number
  category?: string
  last_activity?: string
  tags?: string[]
}

export function DiscussionCardContent({
  reply_count,
  category,
  last_activity,
  tags,
}: DiscussionCardContentProps) {
  return (
    <div className="space-y-2 mb-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          {reply_count !== undefined && (
            <div className="flex items-center gap-1">
              <MessageSquare className="h-3 w-3" />
              <span className="font-medium">{reply_count} replies</span>
            </div>
          )}
          {category && (
            <Badge variant="secondary" className="text-xs">
              {category}
            </Badge>
          )}
        </div>

        {last_activity && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span>{formatRelativeTime(last_activity)}</span>
          </div>
        )}
      </div>

      {tags && tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {tags.slice(0, 3).map((tag) => (
            <Badge key={tag} variant="outline" className="text-xs">
              {tag}
            </Badge>
          ))}
          {tags.length > 3 && (
            <Badge variant="outline" className="text-xs">
              +{tags.length - 3}
            </Badge>
          )}
        </div>
      )}
    </div>
  )
}
