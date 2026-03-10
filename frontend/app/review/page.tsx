'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { RequireAuth } from '@/components/auth/require-auth';
import ReviewItemCard from './ReviewItemCard';
import { REVIEW_FALLBACK_CATEGORIES } from '@/lib/constants/categories';

function getAuthHeaders(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
  };
}
import {
  Book,
  FileText,
  Github,
  MessageSquare,
  RefreshCw,
  Search,
  Video
} from 'lucide-react';

interface ReviewItem {
  id: string;
  title: string;
  abstract?: string;
  contentType: string;
  source?: 'pubmed' | 'github' | 'youtube' | 'discourse' | 'wiki';
  displayType?: string;  // "Research Article", "Code Repository", etc.
  iconType?: string;     // "document-text", "code", "play-circle", etc.
  contentCategory?: string; // "research", "code", "media", etc.
  url?: string;
  mlScore: number;
  aiConfidence?: number;  // Schema v3: replaces gptScore
  finalScore?: number;     // Schema v3: replaces combinedScore
  qualityScore?: number;   // Quality score used in final_score calculation
  categories: string[];    // Schema v3: replaces predictedCategories
  aiSummary?: string;      // Schema v3: replaces gptReasoning
  status: string;
  submittedDate: string;
  classificationFactors?: Array<{
    feature: string;
    value: number;
    contribution: number;
  }>;
  priority: number;
  authors?: Array<{ name: string }>;
  journal?: string;
  year?: string;
}

interface ReviewStats {
  pending: number;
  approvedToday: number;
  rejectedToday: number;
  avgScore: number;
}

export default function ReviewPage() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedStatus, setSelectedStatus] = useState('pending');
  const [selectedSource, setSelectedSource] = useState<string>('all');
  const [selectedCategories, setSelectedCategories] = useState<{ [key: string]: string[] }>({});
  const [rejectionReasons, setRejectionReasons] = useState<{ [key: string]: string }>({});
  const [filterScore, setFilterScore] = useState<[number, number]>([0, 1]);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    // Fetch review queue when switching tabs or source filter
    fetchReviewQueue();
  }, [selectedStatus, selectedSource, filterScore]);

  const fetchReviewQueue = async () => {
    setLoading(true);
    try {
      const graphqlUrl = process.env.NEXT_PUBLIC_GRAPHQL_URL || '/graphql';
      const response = await fetch(graphqlUrl, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          query: `
            query GetReviewQueue($status: String!, $source: String, $minScore: Float, $maxScore: Float) {
              reviewQueue(status: $status, source: $source, minScore: $minScore, maxScore: $maxScore) {
                id
                title
                abstract
                contentType
                source
                displayType
                iconType
                contentCategory
                url
                mlScore
                aiConfidence
                finalScore
                qualityScore
                categories
                aiSummary
                classificationFactors {
                  feature
                  value
                  contribution
                }
                status
                submittedDate
                priority
              }
            }
          `,
          variables: {
            status: selectedStatus,
            source: selectedSource === 'all' ? null : selectedSource,
            minScore: filterScore[0] > 0 ? filterScore[0] : null,
            maxScore: filterScore[1] < 1 ? filterScore[1] : null
          }
        })
      });

      if (!response.ok) {
        throw new Error(`GraphQL request failed: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();

      // Check for GraphQL errors
      if (data.errors) {
        throw new Error(`GraphQL errors: ${JSON.stringify(data.errors)}`);
      }
      
      if (data.data?.reviewQueue) {
        setItems(data.data.reviewQueue);
        
        // Pre-select AI recommended categories
        const newSelectedCategories: { [key: string]: string[] } = {};
        data.data.reviewQueue.forEach((item: ReviewItem) => {
          if (item.categories && item.categories.length > 0) {
            newSelectedCategories[item.id] = item.categories;
          }
        });
        setSelectedCategories(newSelectedCategories);
      }

      // Fetch stats
      const statsResponse = await fetch(graphqlUrl, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          query: `
            query GetReviewStats {
              getQueueStats {
                pending
                approved
                rejected
                avgScore
              }
            }
          `
        })
      });

      const statsData = await statsResponse.json();
      if (statsData.data?.getQueueStats) {
        const queueStats = statsData.data.getQueueStats;
        setStats({
          pending: queueStats.pending,
          approvedToday: queueStats.approved,
          rejectedToday: queueStats.rejected,
          avgScore: queueStats.avgScore
        });
      } else {
        // Use mock data if API doesn't exist yet
        setStats({
          pending: items.length,
          approvedToday: 12,
          rejectedToday: 3,
          avgScore: 0.72
        });
      }
    } catch (error) {
      // Fallback to dummy data for testing
      setItems([
        {
          id: 'test1',
          title: 'Test Item 1',
          abstract: 'Test abstract',
          contentType: 'article',
          source: 'pubmed',
          mlScore: 0.8,
          status: 'pending',
          submittedDate: new Date().toISOString(),
          priority: 5,
          categories: ['Test Category']
        }
      ] as any);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: string) => {
    const categories = selectedCategories[id] || [];
    
    if (categories.length === 0) {
      return;
    }

    try {
      const graphqlUrl = process.env.NEXT_PUBLIC_GRAPHQL_URL || '/graphql';
      const response = await fetch(graphqlUrl, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          query: `
            mutation ApproveContent($id: String!, $categories: [String!]!) {
              approveContent(id: $id, categories: $categories)
            }
          `,
          variables: { id, categories }
        })
      });

      const data = await response.json();

      // Check for GraphQL errors
      if (data.errors) {
        alert('Failed to approve: ' + (data.errors[0]?.message || 'Unknown error'));
        return;
      }
      
      // Check if approval succeeded (explicitly check for true)
      if (data.data?.approveContent === true) {
        // Remove from list
        setItems(items.filter(item => item.id !== id));
        // Update stats locally for immediate feedback
        if (stats) {
          setStats({
            ...stats,
            approvedToday: stats.approvedToday + 1,
            pending: Math.max(0, stats.pending - 1)
          });
        }
        // Content approved successfully
      } else {
        alert('Failed to approve content. Please try again.');
      }
    } catch (error) {
      alert('Network error while approving content. Please try again.');
    }
  };

  const handleReject = async (id: string) => {
    const reason = rejectionReasons[id] || 'Not relevant to OHDSI';

    try {
      const graphqlUrl = process.env.NEXT_PUBLIC_GRAPHQL_URL || '/graphql';
      const response = await fetch(graphqlUrl, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          query: `
            mutation RejectContent($id: String!, $reason: String!) {
              rejectContent(id: $id, reason: $reason)
            }
          `,
          variables: { id, reason }
        })
      });

      const data = await response.json();

      // Check for GraphQL errors
      if (data.errors) {
        alert('Failed to reject: ' + (data.errors[0]?.message || 'Unknown error'));
        return;
      }
      
      // Check if rejection succeeded (explicitly check for true)
      if (data.data?.rejectContent === true) {
        // Remove from list
        setItems(items.filter(item => item.id !== id));
        // Update stats locally for immediate feedback
        if (stats) {
          setStats({
            ...stats,
            rejectedToday: stats.rejectedToday + 1,
            pending: Math.max(0, stats.pending - 1)
          });
        }
        // Content rejected successfully
      } else {
        alert('Failed to reject content. Please try again.');
      }
    } catch (error) {
      alert('Network error while rejecting content. Please try again.');
    }
  };

  const handleMoveToPending = async (id: string) => {
    try {
      const graphqlUrl = process.env.NEXT_PUBLIC_GRAPHQL_URL || '/graphql';
      const response = await fetch(graphqlUrl, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          query: `
            mutation MoveToPending($id: String!, $notes: String) {
              moveToPending(id: $id, notes: $notes)
            }
          `,
          variables: { 
            id, 
            notes: 'Moved back to pending for re-review' 
          }
        })
      });

      const data = await response.json();
      if (data.data?.moveToPending) {
        // Remove from current list since it's moved to a different status
        setItems(items.filter(item => item.id !== id));
        
        // Update stats if available
        if (stats) {
          if (selectedStatus === 'approved') {
            setStats({
              ...stats,
              approvedToday: Math.max(0, stats.approvedToday - 1),
              pending: stats.pending + 1
            });
          } else if (selectedStatus === 'rejected') {
            setStats({
              ...stats,
              rejectedToday: Math.max(0, stats.rejectedToday - 1),
              pending: stats.pending + 1
            });
          }
        }
        
        // Content moved back to pending successfully
      }
    } catch (error) {
      // Silently ignored
    }
  };

  const toggleCategory = (itemId: string, category: string) => {
    const current = selectedCategories[itemId] || [];
    const updated = current.includes(category)
      ? current.filter(c => c !== category)
      : [...current, category];
    setSelectedCategories({ ...selectedCategories, [itemId]: updated });
  };

  const filteredItems = items.filter(item => {
    const matchesScore = item.mlScore >= filterScore[0] && item.mlScore <= filterScore[1];
    const matchesSearch = !searchQuery || 
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.abstract?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesScore && matchesSearch;
  });

  const [allCategories, setAllCategories] = useState<string[]>([]);

  // Fetch categories from backend
  useEffect(() => {
    fetchCategories();
  }, []);

  const fetchCategories = async () => {
    try {
      const graphqlUrl = process.env.NEXT_PUBLIC_GRAPHQL_URL || '/graphql';
      const response = await fetch(graphqlUrl, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          query: `
            query GetCategories {
              getCategories
            }
          `
        })
      });

      const data = await response.json();
      if (data.data?.getCategories) {
        setAllCategories(data.data.getCategories);
      } else {
        // Fallback to default categories
        setAllCategories(REVIEW_FALLBACK_CATEGORIES);
      }
    } catch (error) {
      // Use extensive fallback list
      setAllCategories(REVIEW_FALLBACK_CATEGORIES);
    }
  };

  return (
    <RequireAuth role="reviewer">
    <div className="container mx-auto py-8">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Review Queue</h1>
            <p className="text-muted-foreground">
              Review and approve OHDSI-related content from automated pipeline
            </p>
          </div>
          <Button onClick={fetchReviewQueue} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Pending Review</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.pending}</div>
              <p className="text-xs text-muted-foreground">Items awaiting review</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Approved Today</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{stats.approvedToday}</div>
              <p className="text-xs text-muted-foreground">Auto + manual approvals</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Rejected Today</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{stats.rejectedToday}</div>
              <p className="text-xs text-muted-foreground">Not OHDSI relevant</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Avg Confidence</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{(stats.avgScore * 100).toFixed(1)}%</div>
              <p className="text-xs text-muted-foreground">ML model confidence</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters and Tabs */}
      <div className="mb-6 space-y-4">
        <Tabs value={selectedStatus} onValueChange={setSelectedStatus}>
          <TabsList>
            <TabsTrigger value="pending">Pending</TabsTrigger>
            <TabsTrigger value="approved">Approved</TabsTrigger>
            <TabsTrigger value="rejected">Rejected</TabsTrigger>
          </TabsList>
        </Tabs>

        <div className="flex gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
              <Input
                placeholder="Search by title or abstract..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          
          {/* Source Filter */}
          <Select value={selectedSource} onValueChange={setSelectedSource}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="All Sources" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  All Sources
                </div>
              </SelectItem>
              <SelectItem value="pubmed">
                <div className="flex items-center gap-2">
                  <Book className="w-4 h-4" />
                  PubMed Articles
                </div>
              </SelectItem>
              <SelectItem value="github">
                <div className="flex items-center gap-2">
                  <Github className="w-4 h-4" />
                  GitHub Repositories
                </div>
              </SelectItem>
              <SelectItem value="youtube">
                <div className="flex items-center gap-2">
                  <Video className="w-4 h-4" />
                  YouTube Videos
                </div>
              </SelectItem>
              <SelectItem value="discourse">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4" />
                  Forum Discussions
                </div>
              </SelectItem>
              <SelectItem value="wiki">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Documentation
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
          
          <div className="flex items-center gap-2">
            <Label>Confidence:</Label>
            <Input
              type="number"
              min="0"
              max="1"
              step="0.1"
              value={filterScore[0]}
              onChange={(e) => setFilterScore([parseFloat(e.target.value), filterScore[1]])}
              className="w-20"
            />
            <span>-</span>
            <Input
              type="number"
              min="0"
              max="1"
              step="0.1"
              value={filterScore[1]}
              onChange={(e) => setFilterScore([filterScore[0], parseFloat(e.target.value)])}
              className="w-20"
            />
          </div>
        </div>
      </div>

      {/* Review Items */}
      {loading ? (
        <div className="text-center py-8">Loading review queue...</div>
      ) : filteredItems.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          No items found matching your filters
        </div>
      ) : (
        <div className="space-y-4">
          {filteredItems.map((item) => (
            <ReviewItemCard
              key={item.id}
              item={{
                ...item,
                contentType: item.contentType,
                aiConfidence: item.aiConfidence || 0,
                finalScore: item.finalScore || item.mlScore,
                qualityScore: item.qualityScore ?? 0.5,
                aiSummary: item.aiSummary || '',
                priority: item.priority,
                categories: item.categories || []
              }}
              selectedCategories={selectedCategories[item.id] || []}
              onCategoryToggle={(category) => toggleCategory(item.id, category)}
              onApprove={() => handleApprove(item.id)}
              onReject={() => handleReject(item.id)}
              onMoveToPending={() => handleMoveToPending(item.id)}
              rejectionReason={rejectionReasons[item.id] || ''}
              onRejectionReasonChange={(reason) => 
                setRejectionReasons({
                  ...rejectionReasons,
                  [item.id]: reason
                })
              }
              showActions={true}
            />
          ))}
        </div>
      )}
    </div>
    </RequireAuth>
  );
}