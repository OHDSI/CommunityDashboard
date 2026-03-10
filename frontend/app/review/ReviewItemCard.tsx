'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  AlertCircle,
  Brain,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Info,
  Sparkles,
  Star,
  XCircle
} from 'lucide-react';
import { getSourceIcon, getSourceLabel } from '@/lib/utils/source-display';
import { CATEGORY_NAMES } from '@/lib/constants/categories';

interface ReviewItemProps {
  item: {
    id: string;
    title: string;
    abstract?: string;
    contentType: string;
    source?: 'pubmed' | 'github' | 'youtube' | 'discourse' | 'wiki';
    displayType?: string;
    iconType?: string;
    contentCategory?: string;
    url?: string;
    mlScore: number;
    aiConfidence?: number;
    finalScore?: number;
    qualityScore?: number;  // Quality score used in final score calculation
    categories: string[];
    classificationFactors?: Array<{
      feature: string;
      value: number;
      contribution: number;
    }>;
    aiSummary?: string;  // AI reasoning for classification
    status: string;
    submittedDate: string;
    priority: number;
  };
  selectedCategories: string[];
  onCategoryToggle: (category: string) => void;
  onApprove: () => void;
  onReject: () => void;
  onMoveToPending?: () => void;
  rejectionReason?: string;
  onRejectionReasonChange?: (reason: string) => void;
  showActions?: boolean;
}

function formatFeatureValue(val: number): string {
  if (val === 0 || val === 1) return val === 1 ? 'Yes' : 'No';
  if (Number.isInteger(val)) return val.toString();
  return val.toFixed(2);
}

function formatContribution(c: number): string {
  if (Math.abs(c) < 0.001) return '~0';
  return (c > 0 ? '+' : '') + c.toFixed(3);
}

const allCategories = CATEGORY_NAMES;

export default function ReviewItemCard({
  item,
  selectedCategories,
  onCategoryToggle,
  onApprove,
  onReject,
  onMoveToPending,
  rejectionReason = '',
  onRejectionReasonChange,
  showActions = true
}: ReviewItemProps) {
  const [expanded, setExpanded] = useState(false);
  const [processingAction, setProcessingAction] = useState<'approve' | 'reject' | null>(null);

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreIcon = (score: number) => {
    if (score >= 0.8) return <CheckCircle2 className="w-5 h-5 text-green-600" />;
    if (score >= 0.6) return <AlertCircle className="w-5 h-5 text-yellow-600" />;
    return <XCircle className="w-5 h-5 text-red-600" />;
  };
  
  const SourceIcon = getSourceIcon(item.source);
  const sourceLabel = getSourceLabel(item.source, item.displayType);

  const handleApprove = async () => {
    setProcessingAction('approve');
    await onApprove();
    setProcessingAction(null);
  };

  const handleReject = async () => {
    setProcessingAction('reject');
    await onReject();
    setProcessingAction(null);
  };

  const score = item.finalScore ?? item.mlScore;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <CardTitle className="text-lg">{item.title}</CardTitle>
              {/* Source Badge */}
              {item.source && (
                <Badge variant="outline" className="gap-1">
                  <SourceIcon className="w-4 h-4" />
                  {sourceLabel}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              {/* Combined Score */}
              <span className="flex items-center gap-1">
                {getScoreIcon(score)}
                <span className={getScoreColor(score)}>
                  {(score * 100).toFixed(1)}% confidence
                </span>
              </span>
              
              {/* ML Score */}
              <span className="flex items-center gap-1">
                <Brain className="w-4 h-4" />
                ML: {(item.mlScore * 100).toFixed(0)}%
              </span>
              
              {/* GPT Score if available */}
              {item.aiConfidence !== undefined && item.aiConfidence > 0 && (
                <span className="flex items-center gap-1">
                  <Sparkles className="w-4 h-4" />
                  AI: {(item.aiConfidence * 100).toFixed(0)}%
                </span>
              )}
              
              <span className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {new Date(item.submittedDate).toLocaleDateString()}
              </span>
              
              {item.url && (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 hover:text-primary"
                >
                  <ExternalLink className="w-4 h-4" />
                  View Source
                </a>
              )}
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {/* AI Analysis - Always visible */}
        {item.aiSummary && (
          <div className="bg-purple-50 dark:bg-purple-950/30 rounded-lg p-3 mb-4">
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-4 h-4 text-purple-600" />
              <Label className="text-sm font-medium">AI Analysis:</Label>
            </div>
            <p className="text-sm text-muted-foreground line-clamp-3">{item.aiSummary}</p>
          </div>
        )}

        {/* Categories Display */}
        <div className="mb-4">
          <Label className="text-sm mb-2">Categories:</Label>
          <div className="flex flex-wrap gap-2">
            {item.status === 'pending' ? (
              /* For pending items, show all categories as selectable */
              allCategories.map((cat) => (
                <Badge
                  key={cat}
                  variant={selectedCategories.includes(cat) ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => onCategoryToggle(cat)}
                >
                  {cat}
                </Badge>
              ))
            ) : (
              /* For approved/rejected items, just show the actual categories */
              item.categories && item.categories.length > 0 ? (
                item.categories.map((cat) => (
                  <Badge
                    key={cat}
                    variant="default"
                    className="cursor-default"
                  >
                    {cat}
                  </Badge>
                ))
              ) : (
                <span className="text-sm text-muted-foreground">No categories assigned</span>
              )
            )}
          </div>
          {item.status === 'pending' && item.categories && item.categories.length > 0 && (
            <p className="text-xs text-muted-foreground mt-2">
              AI recommended: {item.categories.join(', ')}
            </p>
          )}
        </div>

        {/* Scores Breakdown - 4-column layout for full transparency */}
        <div className="mb-4 grid grid-cols-4 gap-3">
          {/* RF Classifier Score with Feature Contribution Tooltip */}
          <div className="text-center p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg relative group">
            <div className="flex items-center justify-center gap-1 mb-1">
              <Brain className="w-4 h-4 text-blue-500" />
              <span className="text-xs font-medium">RF Classifier</span>
              {item.classificationFactors && item.classificationFactors.filter(f => f.value !== 0).length > 0 && (
                <Info className="w-3 h-3 text-muted-foreground cursor-help" />
              )}
            </div>
            <span className="text-xl font-bold">{(item.mlScore * 100).toFixed(1)}%</span>

            {/* Feature contribution tooltip — only show features with non-zero values */}
            {item.classificationFactors && item.classificationFactors.filter(f => f.value !== 0).length > 0 && (
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-slate-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10 pointer-events-none">
                <div className="font-semibold mb-1">Top ML Features:</div>
                {item.classificationFactors.filter(f => f.value !== 0).map((f, i) => (
                  <div key={i} className="flex justify-between gap-4">
                    <span>{f.feature}: {formatFeatureValue(f.value)}</span>
                    <span className={`font-mono ${f.contribution > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatContribution(f.contribution)}
                    </span>
                  </div>
                ))}
                <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-slate-900"></div>
              </div>
            )}
          </div>

          {/* AI Score */}
          <div className="text-center p-3 bg-purple-50 dark:bg-purple-950/30 rounded-lg">
            <div className="flex items-center justify-center gap-1 mb-1">
              <Sparkles className="w-4 h-4 text-purple-500" />
              <span className="text-xs font-medium">AI</span>
            </div>
            <span className="text-xl font-bold">
              {item.aiConfidence !== undefined && item.aiConfidence > 0
                ? `${(item.aiConfidence * 100).toFixed(1)}%`
                : 'N/A'}
            </span>
          </div>

          {/* Quality Score */}
          <div className="text-center p-3 bg-amber-50 dark:bg-amber-950/30 rounded-lg">
            <div className="flex items-center justify-center gap-1 mb-1">
              <Star className="w-4 h-4 text-amber-500" />
              <span className="text-xs font-medium">Quality</span>
            </div>
            <span className="text-xl font-bold">
              {item.qualityScore !== undefined
                ? `${(item.qualityScore * 100).toFixed(1)}%`
                : '50.0%'}
            </span>
          </div>

          {/* Final Score with Tooltip */}
          <div className="text-center p-3 bg-green-50 dark:bg-green-950/30 rounded-lg relative group">
            <div className="flex items-center justify-center gap-1 mb-1">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              <span className="text-xs font-medium">Final</span>
              <Info className="w-3 h-3 text-muted-foreground cursor-help" />
            </div>
            <span className="text-xl font-bold">{(score * 100).toFixed(1)}%</span>

            {/* Tooltip showing calculation */}
            <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-slate-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10 pointer-events-none">
              <div className="font-semibold mb-1">Score Calculation:</div>
              <div>ML+AI Combined: {((item.mlScore + (item.aiConfidence || 0)) / 2 * 100).toFixed(1)}%</div>
              <div>Quality Score: {((item.qualityScore ?? 0.5) * 100).toFixed(1)}%</div>
              <div className="border-t border-slate-700 mt-1 pt-1">
                Final = (Combined × 70%) + (Quality × 30%)
              </div>
              <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-slate-900"></div>
            </div>
          </div>
        </div>


        {/* Action Buttons */}
        {showActions && (
          <div className="flex gap-2 mb-4">
            {item.status === 'pending' ? (
              <>
                <Button
                  onClick={handleApprove}
                  variant="default"
                  className="bg-green-600 hover:bg-green-700"
                  disabled={processingAction !== null}
                  title={selectedCategories.length === 0 ? "Warning: No categories selected" : ""}
                >
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  {processingAction === 'approve' ? 'Approving...' : 'Approve'}
                </Button>
                <Button
                  onClick={handleReject}
                  variant="destructive"
                  disabled={processingAction !== null}
                >
                  <XCircle className="w-4 h-4 mr-2" />
                  {processingAction === 'reject' ? 'Rejecting...' : 'Reject'}
                </Button>
                {item.url && (
                  <Button
                    onClick={() => window.open(item.url, '_blank')}
                    variant="outline"
                    disabled={processingAction !== null}
                  >
                    <ExternalLink className="w-4 h-4 mr-2" />
                    View Publication
                  </Button>
                )}
              </>
            ) : (
              /* Show Move to Pending button for approved/rejected items */
              <>
                {onMoveToPending && (
                  <Button 
                    onClick={onMoveToPending}
                    variant="outline"
                    className="flex-1"
                  >
                    <AlertCircle className="w-4 h-4 mr-2" />
                    Move Back to Pending
                  </Button>
                )}
                {item.url && (
                  <Button
                    onClick={() => window.open(item.url, '_blank')}
                    variant="outline"
                    className="flex-1"
                  >
                    <ExternalLink className="w-4 h-4 mr-2" />
                    View Publication
                  </Button>
                )}
              </>
            )}
          </div>
        )}

        {/* Expanded Content */}
        {expanded && (
          <div className="space-y-4 pt-4 border-t">
            {item.abstract && (
              <div>
                <Label className="text-sm mb-2">Abstract:</Label>
                <p className="text-sm text-muted-foreground">{item.abstract}</p>
              </div>
            )}

            {/* Full AI Analysis shown in expanded view if it was truncated */}
            {item.aiSummary && item.aiSummary.length > 200 && (
              <div className="bg-purple-50 dark:bg-purple-950/30 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Brain className="w-4 h-4 text-purple-600" />
                  <Label className="text-sm font-medium">Full AI Analysis:</Label>
                </div>
                <p className="text-sm text-muted-foreground">{item.aiSummary}</p>
              </div>
            )}

            {/* Optional Rejection Reason */}
            {showActions && item.status === 'pending' && (
              <div>
                <Label htmlFor={`reason-${item.id}`}>
                  Rejection Reason (optional):
                </Label>
                <Textarea
                  id={`reason-${item.id}`}
                  placeholder="Optionally provide a reason for rejection..."
                  value={rejectionReason}
                  onChange={(e) => onRejectionReasonChange?.(e.target.value)}
                  rows={2}
                />
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}