"""
Dashboard-related GraphQL types.

Includes all types used by dashboard queries: stats, metrics,
timeline, network, source-specific metrics, trending, and engagement types.
"""
import strawberry
from strawberry.scalars import JSON
from typing import Optional, List


@strawberry.type
class CategoryStat:
    name: str
    count: int


@strawberry.type
class AuthorStat:
    name: str
    articleCount: int
    affiliations: List[str]


@strawberry.type
class CollaborationMetrics:
    avgTeamSize: float
    largestTeam: int
    singleAuthorPapers: int
    multiInstitutional: int
    internationalCollaborations: int


@strawberry.type
class FundingMetrics:
    fundedArticles: int
    nihFunded: int
    industryFunded: int
    avgGrantsPerArticle: float


@strawberry.type
class YearRange:
    start: int
    end: int


@strawberry.type
class MonthlyTrend:
    month: str
    count: int


@strawberry.type
class DashboardStats:
    totalArticles: int
    uniqueAuthors: int
    uniqueInstitutions: int
    totalCategories: int
    yearRange: YearRange
    topCategories: List[CategoryStat]
    topAuthors: List[AuthorStat]
    collaborationMetrics: CollaborationMetrics
    mlScoreDistribution: JSON
    contentTypes: JSON
    contentSources: JSON
    monthlyTrend: List[MonthlyTrend]
    fundingMetrics: FundingMetrics
    lastUpdated: str


@strawberry.type
class TimelinePoint:
    date: str
    year: int
    count: int
    categories: JSON


@strawberry.type
class TimelineStats:
    timeline: List[TimelinePoint]
    totalArticles: int
    lastUpdated: str


@strawberry.type
class NetworkNode:
    id: str
    name: str
    articles: int
    centrality: float


@strawberry.type
class NetworkLink:
    source: str
    target: str
    value: int


@strawberry.type
class NetworkStats:
    nodes: List[NetworkNode]
    links: List[NetworkLink]
    totalAuthors: int
    lastUpdated: str


# Dashboard Data Types for Enhanced Dashboard
@strawberry.type
class JournalStat:
    name: str
    count: int


@strawberry.type
class ArticleStat:
    id: str
    title: str
    journal: str
    citations: int


@strawberry.type
class VideoStat:
    id: str
    title: str
    channel: str
    views: int
    duration: int


@strawberry.type
class ChannelStat:
    name: str
    videos: int
    views: int


@strawberry.type
class RepoStat:
    id: str
    name: str
    stars: int
    language: str


@strawberry.type
class LanguageStat:
    name: str
    count: int
    color: str


@strawberry.type
class TopicStat:
    id: str
    title: str
    replies: int
    solved: bool


@strawberry.type
class DocStat:
    id: str
    title: str
    type: str
    readTime: int


@strawberry.type
class DocTypeStat:
    type: str
    count: int


@strawberry.type
class PubMedMetrics:
    total: int
    avgCitations: float
    topJournals: List[JournalStat]
    recentArticles: List[ArticleStat]


@strawberry.type
class YouTubeMetrics:
    total: int
    totalViews: int
    avgDuration: float
    topChannels: List[ChannelStat]
    recentVideos: List[VideoStat]


@strawberry.type
class GitHubMetrics:
    total: int
    totalStars: int
    topLanguages: List[LanguageStat]
    activeRepos: List[RepoStat]


@strawberry.type
class DiscourseMetrics:
    total: int
    solvedRate: float
    avgResponseTime: float
    activeTopics: List[TopicStat]


@strawberry.type
class WikiMetrics:
    total: int
    avgReadTime: float
    docTypes: List[DocTypeStat]
    recentDocs: List[DocStat]


@strawberry.type
class SourceMetrics:
    pubmed: PubMedMetrics
    youtube: YouTubeMetrics
    github: GitHubMetrics
    discourse: DiscourseMetrics
    wiki: WikiMetrics


@strawberry.type
class TrendingTopic:
    term: str
    count: int
    trend: str  # 'up', 'down', 'stable'


@strawberry.type
class TrendingSearch:
    query: str
    count: int


@strawberry.type
class TrendingContent:
    id: str
    title: str
    source: str
    engagement: int


@strawberry.type
class TrendingData:
    topics: List[TrendingTopic]
    searches: List[TrendingSearch]
    content: List[TrendingContent]


@strawberry.type
class EngagementMetrics:
    totalViews: int
    totalBookmarks: int
    totalShares: int
    avgEngagementRate: float
    engagementBySource: JSON


@strawberry.type
class QualityDistribution:
    range: str
    count: int
    percentage: float


@strawberry.type
class ActivityItem:
    id: str
    type: str  # 'new', 'trending', 'updated'
    title: str
    source: str
    timestamp: str


@strawberry.type
class ContentGrowth:
    date: str
    source: str
    count: int


@strawberry.type
class DashboardData:
    totalContent: int
    contentBySource: JSON
    contentGrowth: List[ContentGrowth]
    sourceMetrics: SourceMetrics
    trending: TrendingData
    engagement: EngagementMetrics
    qualityDistribution: List[QualityDistribution]
    recentActivity: List[ActivityItem]
    lastUpdated: str
