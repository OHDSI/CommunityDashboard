import {
  Star,
  GitFork,
  Github,
  Clock,
  Hash,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { formatRelativeTime } from '@/lib/utils/format'

export interface RepoCardContentProps {
  owner?: string
  stars_count?: number
  forks_count?: number
  topics?: string[]
  last_commit?: string
}

export function RepoCardContent({
  owner,
  stars_count,
  forks_count,
  topics,
  last_commit,
}: RepoCardContentProps) {
  return (
    <div className="space-y-2 mb-3">
      <div className="flex items-center justify-between">
        {owner && (
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <Github className="h-3 w-3" />
            <span className="font-medium">{owner}</span>
          </div>
        )}
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          {stars_count !== undefined && stars_count !== null && (
            <div className="flex items-center gap-1">
              <Star className="h-3 w-3 fill-current text-yellow-500" />
              <span className="font-medium">{stars_count.toLocaleString()}</span>
            </div>
          )}
          {forks_count !== undefined && forks_count !== null && (
            <div className="flex items-center gap-1">
              <GitFork className="h-3 w-3" />
              <span>{forks_count.toLocaleString()}</span>
            </div>
          )}
        </div>
      </div>

      {topics && topics.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {topics.slice(0, 4).map((topic) => (
            <Badge key={topic} variant="secondary" className="text-xs">
              <Hash className="h-2 w-2 mr-1" />
              {topic}
            </Badge>
          ))}
          {topics.length > 4 && (
            <Badge variant="secondary" className="text-xs">
              +{topics.length - 4}
            </Badge>
          )}
        </div>
      )}

      {last_commit && (
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>Updated {formatRelativeTime(last_commit)}</span>
        </div>
      )}
    </div>
  )
}
