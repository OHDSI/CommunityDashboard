import {
  FileText,
  User,
  TrendingUp,
  Building,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'

export interface ArticleCardContentProps {
  journal?: string
  citationCount?: number
  authorNames: string[]
  institutions?: string[]
  mesh_terms?: string[]
}

export function ArticleCardContent({
  journal,
  citationCount,
  authorNames,
  institutions,
  mesh_terms,
}: ArticleCardContentProps) {
  return (
    <div className="space-y-2 mb-3">
      {journal && (
        <div className="flex items-center gap-1 text-sm text-muted-foreground">
          <FileText className="h-3 w-3" />
          <span className="font-medium">{journal}</span>
          {citationCount && (
            <>
              <span className="mx-1">&bull;</span>
              <TrendingUp className="h-3 w-3" />
              <span>{citationCount} citations</span>
            </>
          )}
        </div>
      )}

      {authorNames.length > 0 && (
        <div className="flex items-center gap-1 text-sm text-muted-foreground">
          <User className="h-3 w-3" />
          <span className="line-clamp-1">
            {authorNames.slice(0, 3).join(', ')}
            {authorNames.length > 3 && ` +${authorNames.length - 3} more`}
          </span>
        </div>
      )}

      {institutions && institutions.length > 0 && (
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Building className="h-3 w-3" />
          <span className="line-clamp-1">
            {institutions.slice(0, 2).join(', ')}
            {institutions.length > 2 && ` +${institutions.length - 2} more`}
          </span>
        </div>
      )}

      {mesh_terms && mesh_terms.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {mesh_terms.slice(0, 3).map((term) => (
            <Badge key={term} variant="outline" className="text-xs">
              {term}
            </Badge>
          ))}
          {mesh_terms.length > 3 && (
            <Badge variant="outline" className="text-xs">
              +{mesh_terms.length - 3}
            </Badge>
          )}
        </div>
      )}
    </div>
  )
}
