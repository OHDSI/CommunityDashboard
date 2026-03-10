import {
  Video,
  Eye,
} from 'lucide-react'

export interface VideoCardContentProps {
  channel_name?: string
  viewCount?: number
}

export function VideoCardContent({
  channel_name,
  viewCount,
}: VideoCardContentProps) {
  return (
    <div className="space-y-2 mb-3">
      <div className="flex items-center justify-between">
        {channel_name && (
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <Video className="h-3 w-3" />
            <span className="font-medium">{channel_name}</span>
          </div>
        )}
        {viewCount !== undefined && viewCount !== null && viewCount > 0 && (
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            <Eye className="h-3 w-3" />
            <span className="font-medium">{viewCount.toLocaleString()} views</span>
          </div>
        )}
      </div>
    </div>
  )
}
