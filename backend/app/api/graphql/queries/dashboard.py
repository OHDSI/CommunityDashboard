"""
Dashboard query resolvers.

Handles dashboard_data, dashboard_stats, timeline_stats, network_stats,
get_pipeline_stats, and get_model_stats queries.
"""
import logging
from datetime import datetime, timedelta
from strawberry.scalars import JSON

from ..types.prediction import ModelStats
from ..types.dashboard import (
    CategoryStat, AuthorStat, CollaborationMetrics, FundingMetrics,
    YearRange, MonthlyTrend, DashboardStats,
    TimelinePoint, TimelineStats,
    NetworkNode, NetworkLink, NetworkStats,
    JournalStat, ArticleStat, VideoStat, ChannelStat, RepoStat,
    LanguageStat, TopicStat, DocStat, DocTypeStat,
    PubMedMetrics, YouTubeMetrics, GitHubMetrics, DiscourseMetrics,
    WikiMetrics, SourceMetrics,
    TrendingTopic, TrendingSearch, TrendingContent, TrendingData,
    EngagementMetrics, QualityDistribution, ActivityItem, ContentGrowth,
    DashboardData,
)
from ..services import dashboard_service, prediction_service
from ....config import settings
from ....database import es_client

logger = logging.getLogger(__name__)


def resolve_get_model_stats() -> ModelStats:
    """Get statistics about the prediction model"""
    stats = prediction_service.get_model_stats()
    return ModelStats(
        model_exists=stats.get('model_exists', False),
        topic_authors_count=stats.get('topic_authors_count'),
        topic_keywords_count=stats.get('topic_keywords_count'),
        known_articles_count=stats.get('known_articles_count'),
        feature_count=stats.get('feature_count'),
        last_trained=stats.get('last_trained')
    )


async def resolve_dashboard_data(date_range: str = "30d") -> DashboardData:
    """Get comprehensive dashboard data for multi-source analytics"""
    data = await dashboard_service.get_dashboard_data(date_range=date_range, use_cache=True)

    # Convert dict to GraphQL types
    return DashboardData(
        totalContent=data["totalContent"],
        contentBySource=data["contentBySource"],
        contentGrowth=[
            ContentGrowth(date=g["date"], source=g["source"], count=g["count"])
            for g in data["contentGrowth"]
        ],
        sourceMetrics=SourceMetrics(
            pubmed=PubMedMetrics(
                total=data["sourceMetrics"]["pubmed"]["total"],
                avgCitations=data["sourceMetrics"]["pubmed"]["avgCitations"],
                topJournals=[
                    JournalStat(name=j["name"], count=j["count"])
                    for j in data["sourceMetrics"]["pubmed"]["topJournals"]
                ],
                recentArticles=[
                    ArticleStat(id=a["id"], title=a["title"], journal=a["journal"], citations=a["citations"])
                    for a in data["sourceMetrics"]["pubmed"]["recentArticles"]
                ]
            ),
            youtube=YouTubeMetrics(
                total=data["sourceMetrics"]["youtube"]["total"],
                totalViews=data["sourceMetrics"]["youtube"]["totalViews"],
                avgDuration=data["sourceMetrics"]["youtube"]["avgDuration"],
                topChannels=[
                    ChannelStat(name=c["name"], videos=c["videos"], views=c["views"])
                    for c in data["sourceMetrics"]["youtube"]["topChannels"]
                ],
                recentVideos=[
                    VideoStat(id=v["id"], title=v["title"], channel=v["channel"],
                             views=v["views"], duration=v["duration"])
                    for v in data["sourceMetrics"]["youtube"]["recentVideos"]
                ]
            ),
            github=GitHubMetrics(
                total=data["sourceMetrics"]["github"]["total"],
                totalStars=data["sourceMetrics"]["github"]["totalStars"],
                topLanguages=[
                    LanguageStat(name=l["name"], count=l["count"], color=l["color"])
                    for l in data["sourceMetrics"]["github"]["topLanguages"]
                ],
                activeRepos=[
                    RepoStat(id=r["id"], name=r["name"], stars=r["stars"], language=r["language"])
                    for r in data["sourceMetrics"]["github"]["activeRepos"]
                ]
            ),
            discourse=DiscourseMetrics(
                total=data["sourceMetrics"]["discourse"]["total"],
                solvedRate=data["sourceMetrics"]["discourse"]["solvedRate"],
                avgResponseTime=data["sourceMetrics"]["discourse"]["avgResponseTime"],
                activeTopics=[
                    TopicStat(id=t["id"], title=t["title"], replies=t["replies"], solved=t["solved"])
                    for t in data["sourceMetrics"]["discourse"]["activeTopics"]
                ]
            ),
            wiki=WikiMetrics(
                total=data["sourceMetrics"]["wiki"]["total"],
                avgReadTime=data["sourceMetrics"]["wiki"]["avgReadTime"],
                docTypes=[
                    DocTypeStat(type=d["type"], count=d["count"])
                    for d in data["sourceMetrics"]["wiki"]["docTypes"]
                ],
                recentDocs=[
                    DocStat(id=d["id"], title=d["title"], type=d["type"], readTime=d["readTime"])
                    for d in data["sourceMetrics"]["wiki"]["recentDocs"]
                ]
            )
        ),
        trending=TrendingData(
            topics=[
                TrendingTopic(term=t["term"], count=t["count"], trend=t["trend"])
                for t in data["trending"]["topics"]
            ],
            searches=[
                TrendingSearch(query=s["query"], count=s["count"])
                for s in data["trending"]["searches"]
            ],
            content=[
                TrendingContent(id=c["id"], title=c["title"], source=c["source"], engagement=c["engagement"])
                for c in data["trending"]["content"]
            ]
        ),
        engagement=EngagementMetrics(
            totalViews=data["engagement"]["totalViews"],
            totalBookmarks=data["engagement"]["totalBookmarks"],
            totalShares=data["engagement"]["totalShares"],
            avgEngagementRate=data["engagement"]["avgEngagementRate"],
            engagementBySource=data["engagement"]["engagementBySource"]
        ),
        qualityDistribution=[
            QualityDistribution(range=q["range"], count=q["count"], percentage=q["percentage"])
            for q in data["qualityDistribution"]
        ],
        recentActivity=[
            ActivityItem(id=a["id"], type=a["type"], title=a["title"],
                       source=a["source"], timestamp=a["timestamp"])
            for a in data["recentActivity"]
        ],
        lastUpdated=data["lastUpdated"]
    )


async def resolve_dashboard_stats(use_cache: bool = True) -> DashboardStats:
    """Get pre-computed dashboard statistics using Elasticsearch aggregations"""
    stats = await dashboard_service.get_stats(use_cache=use_cache)

    # Convert dict to GraphQL types
    return DashboardStats(
        totalArticles=stats["totalArticles"],
        uniqueAuthors=stats["uniqueAuthors"],
        uniqueInstitutions=stats["uniqueInstitutions"],
        totalCategories=stats["totalCategories"],
        yearRange=YearRange(
            start=stats["yearRange"]["start"],
            end=stats["yearRange"]["end"]
        ),
        topCategories=[
            CategoryStat(name=cat["name"], count=cat["count"])
            for cat in stats["topCategories"]
        ],
        topAuthors=[
            AuthorStat(
                name=author["name"],
                articleCount=author["articleCount"],
                affiliations=author["affiliations"]
            )
            for author in stats["topAuthors"]
        ],
        collaborationMetrics=CollaborationMetrics(
            avgTeamSize=stats["collaborationMetrics"]["avgTeamSize"],
            largestTeam=stats["collaborationMetrics"]["largestTeam"],
            singleAuthorPapers=stats["collaborationMetrics"]["singleAuthorPapers"],
            multiInstitutional=stats["collaborationMetrics"]["multiInstitutional"],
            internationalCollaborations=stats["collaborationMetrics"]["internationalCollaborations"]
        ),
        mlScoreDistribution=stats["mlScoreDistribution"],
        contentTypes=stats["contentTypes"],
        contentSources=stats.get("contentSources", {}),
        monthlyTrend=[
            MonthlyTrend(month=trend["month"], count=trend["count"])
            for trend in stats["monthlyTrend"]
        ],
        fundingMetrics=FundingMetrics(
            fundedArticles=stats["fundingMetrics"]["fundedArticles"],
            nihFunded=stats["fundingMetrics"]["nihFunded"],
            industryFunded=stats["fundingMetrics"]["industryFunded"],
            avgGrantsPerArticle=stats["fundingMetrics"]["avgGrantsPerArticle"]
        ),
        lastUpdated=stats["lastUpdated"]
    )


async def resolve_timeline_stats(use_cache: bool = True) -> TimelineStats:
    """Get pre-computed timeline statistics for Explorer visualization"""
    stats = await dashboard_service.get_timeline_stats(use_cache=use_cache)

    return TimelineStats(
        timeline=[
            TimelinePoint(
                date=point["date"],
                year=point["year"],
                count=point["count"],
                categories=point["categories"]
            )
            for point in stats["timeline"]
        ],
        totalArticles=stats["totalArticles"],
        lastUpdated=stats["lastUpdated"]
    )


async def resolve_network_stats(use_cache: bool = True, limit: int = 100) -> NetworkStats:
    """Get pre-computed collaboration network statistics"""
    stats = await dashboard_service.get_network_stats(use_cache=use_cache, limit=limit)

    return NetworkStats(
        nodes=[
            NetworkNode(
                id=node["id"],
                name=node["name"],
                articles=node["articles"],
                centrality=node.get("centrality", 0)
            )
            for node in stats["nodes"]
        ],
        links=[
            NetworkLink(
                source=link["source"],
                target=link["target"],
                value=link["value"]
            )
            for link in stats["links"]
        ],
        totalAuthors=stats["totalAuthors"],
        lastUpdated=stats["lastUpdated"]
    )


async def resolve_get_pipeline_stats() -> dict:
    """Get pipeline statistics for dashboard"""
    # Get today's stats from Elasticsearch
    today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()

    # Count fetched today
    fetched_query = {
        "size": 0,
        "query": {
            "range": {"created_at": {"gte": today_start}}
        }
    }

    # Count approved today
    approved_query = {
        "size": 0,
        "query": {
            "bool": {
                "filter": [
                    {"term": {"approval_status": "approved"}},
                    {"range": {"created_at": {"gte": today_start}}}
                ]
            }
        }
    }

    try:
        fetched_resp = es_client.search(index=settings.content_index, body=fetched_query)
        approved_resp = es_client.search(index=settings.content_index, body=approved_query)

        fetched_today = fetched_resp['hits']['total']['value']
        approved_today = approved_resp['hits']['total']['value']
    except Exception:
        fetched_today = 0
        approved_today = 0

    # Get pending count
    pending_query = {"size": 0, "query": {"term": {"status": "pending"}}}
    try:
        pending_resp = es_client.search(index=settings.review_index, body=pending_query)
        pending_count = pending_resp['hits']['total']['value']
    except Exception:
        pending_count = 0

    # Calculate next run (2 AM UTC tomorrow)
    next_run = datetime.now().replace(hour=2, minute=0, second=0)
    if datetime.now().hour >= 2:
        next_run = next_run + timedelta(days=1)

    # Mock weekly trend for now
    weekly_trend = []
    for i in range(7):
        date = (datetime.now() - timedelta(days=6-i)).strftime('%a')
        weekly_trend.append({
            "date": date,
            "fetched": 50 + (i * 10),
            "approved": 20 + (i * 5)
        })

    return {
        "todayFetched": fetched_today,
        "todayClassified": fetched_today,
        "todayApproved": approved_today,
        "todayQueued": pending_count,
        "lastRun": (datetime.now() - timedelta(hours=3)).isoformat(),
        "nextRun": next_run.isoformat(),
        "isRunning": False,
        "successRate": 94.5,
        "weeklyTrend": weekly_trend
    }
