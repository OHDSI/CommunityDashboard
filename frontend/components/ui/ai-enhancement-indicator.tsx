'use client'

import React from 'react'
import { Badge } from '@/components/ui/badge'
import { 
  Sparkles, 
  Brain, 
  CheckCircle2, 
  AlertCircle,
  TrendingUp
} from 'lucide-react'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

interface AIEnhancementIndicatorProps {
  aiEnhanced?: boolean
  aiConfidence?: number
  aiQualityScore?: number
  aiSummary?: string
  aiTools?: string[]
  aiCategories?: string[]
  variant?: 'badge' | 'inline' | 'detailed'
  className?: string
}

export function AIEnhancementIndicator({
  aiEnhanced,
  aiConfidence,
  aiQualityScore,
  aiSummary,
  aiTools,
  aiCategories,
  variant = 'badge',
  className
}: AIEnhancementIndicatorProps) {
  if (!aiEnhanced) {
    return null
  }

  // Determine confidence level
  const confidenceLevel = aiConfidence 
    ? aiConfidence >= 0.8 ? 'high' 
    : aiConfidence >= 0.6 ? 'medium' 
    : 'low'
    : 'unknown'

  const confidenceColors = {
    high: 'bg-gradient-to-r from-green-500 to-emerald-500',
    medium: 'bg-gradient-to-r from-blue-500 to-cyan-500',
    low: 'bg-gradient-to-r from-amber-500 to-orange-500',
    unknown: 'bg-gradient-to-r from-gray-500 to-slate-500'
  }

  const qualityColors = {
    high: 'text-green-600',
    medium: 'text-blue-600',
    low: 'text-amber-600',
    unknown: 'text-gray-600'
  }

  const qualityLevel = aiQualityScore
    ? aiQualityScore >= 0.8 ? 'high'
    : aiQualityScore >= 0.6 ? 'medium'
    : 'low'
    : 'unknown'

  if (variant === 'badge') {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge 
              className={cn(
                "text-white border-0 px-2 py-0.5",
                confidenceColors[confidenceLevel],
                className
              )}
            >
              <Sparkles className="h-3 w-3 mr-1" />
              AI Enhanced
            </Badge>
          </TooltipTrigger>
          <TooltipContent className="max-w-sm">
            <div className="space-y-2">
              {aiConfidence !== undefined && (
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium">Confidence:</span>
                  <span className="text-xs">{Math.round(aiConfidence * 100)}%</span>
                </div>
              )}
              {aiQualityScore !== undefined && (
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium">Quality Score:</span>
                  <span className="text-xs">{Math.round(aiQualityScore * 100)}%</span>
                </div>
              )}
              {aiSummary && (
                <div className="pt-2 border-t">
                  <p className="text-xs font-medium mb-1">AI Summary:</p>
                  <p className="text-xs text-muted-foreground line-clamp-3">
                    {aiSummary}
                  </p>
                </div>
              )}
              {aiTools && aiTools.length > 0 && (
                <div className="pt-2 border-t">
                  <p className="text-xs font-medium mb-1">OHDSI Tools:</p>
                  <div className="flex flex-wrap gap-1">
                    {aiTools.slice(0, 3).map((tool) => (
                      <Badge key={tool} variant="outline" className="text-xs px-1 py-0">
                        {tool}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  if (variant === 'inline') {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        <Brain className={cn("h-4 w-4", qualityColors[qualityLevel])} />
        <span className="text-sm text-muted-foreground">
          AI: {Math.round((aiConfidence || 0) * 100)}% confidence
        </span>
        {aiQualityScore !== undefined && (
          <>
            <span className="text-muted-foreground">•</span>
            <span className="text-sm text-muted-foreground">
              Quality: {Math.round(aiQualityScore * 100)}%
            </span>
          </>
        )}
      </div>
    )
  }

  // Detailed variant
  return (
    <div className={cn("space-y-3 p-4 rounded-lg bg-muted/30", className)}>
      <div className="flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-primary" />
        <span className="font-medium">AI Enhanced Content</span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {aiConfidence !== undefined && (
          <div className="space-y-1">
            <div className="flex items-center gap-1">
              {confidenceLevel === 'high' ? (
                <CheckCircle2 className="h-3 w-3 text-green-600" />
              ) : confidenceLevel === 'medium' ? (
                <AlertCircle className="h-3 w-3 text-blue-600" />
              ) : (
                <AlertCircle className="h-3 w-3 text-amber-600" />
              )}
              <span className="text-xs font-medium">Confidence</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                <div 
                  className={cn("h-full", confidenceColors[confidenceLevel])}
                  style={{ width: `${aiConfidence * 100}%` }}
                />
              </div>
              <span className="text-xs text-muted-foreground">
                {Math.round(aiConfidence * 100)}%
              </span>
            </div>
          </div>
        )}

        {aiQualityScore !== undefined && (
          <div className="space-y-1">
            <div className="flex items-center gap-1">
              <TrendingUp className={cn("h-3 w-3", qualityColors[qualityLevel])} />
              <span className="text-xs font-medium">Quality</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-primary to-accent"
                  style={{ width: `${aiQualityScore * 100}%` }}
                />
              </div>
              <span className="text-xs text-muted-foreground">
                {Math.round(aiQualityScore * 100)}%
              </span>
            </div>
          </div>
        )}
      </div>

      {aiSummary && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">AI Summary</p>
          <p className="text-sm line-clamp-2">{aiSummary}</p>
        </div>
      )}

      {(aiTools && aiTools.length > 0) || (aiCategories && aiCategories.length > 0) ? (
        <div className="flex flex-wrap gap-1">
          {aiTools?.map((tool) => (
            <Badge key={tool} variant="secondary" className="text-xs">
              {tool}
            </Badge>
          ))}
          {aiCategories?.map((category) => (
            <Badge key={category} variant="outline" className="text-xs">
              {category}
            </Badge>
          ))}
        </div>
      ) : null}
    </div>
  )
}