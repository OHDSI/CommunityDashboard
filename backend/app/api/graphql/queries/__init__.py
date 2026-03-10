"""
GraphQL Query definitions for the OHDSI Community Intelligence Platform.

All query resolvers are defined in domain-specific modules and merged
into a single Query class here, since Strawberry requires a single
Query type for the schema.
"""
import strawberry
from strawberry.types import Info
from strawberry.scalars import JSON
from typing import Optional, List

from ..types import (
    Content, SearchResult, ReviewItem, QueueStats, User, ModelStats,
    DashboardData, DashboardStats, TimelineStats, NetworkStats,
    CitationNetwork, CitationStats, CitationTimeline, CitationMilestones,
    CitationClusters, Landscape, SemanticContext,
)

from .content import (
    resolve_search_content,
    resolve_semantic_search,
    resolve_hybrid_search,
    resolve_content,
    resolve_get_categories,
)
from .review import (
    resolve_review_queue,
    resolve_get_queue_stats,
)
from .user import (
    resolve_me,
    resolve_list_users,
)
from .dashboard import (
    resolve_get_model_stats,
    resolve_dashboard_data,
    resolve_dashboard_stats,
    resolve_timeline_stats,
    resolve_network_stats,
    resolve_get_pipeline_stats,
)
from .citation import (
    resolve_citation_network,
    resolve_citation_stats,
    resolve_citation_timeline,
    resolve_citation_paths,
    resolve_citation_clusters,
    resolve_citation_milestones,
)
from .landscape import (
    resolve_generate_landscape,
    resolve_get_semantic_context,
)


@strawberry.type
class Query:
    @strawberry.field
    async def search_content(
        self,
        query: Optional[str] = None,
        filters: Optional[JSON] = None,
        size: int = 20,
        offset: int = 0,
        sort_by: Optional[str] = None
    ) -> SearchResult:
        """Search content with filters and pagination"""
        return await resolve_search_content(query, filters, size, offset, sort_by)

    @strawberry.field
    async def semantic_search(
        self,
        query: str,
        filters: Optional[JSON] = None,
        size: int = 20,
        sort_by: Optional[str] = None,
        offset: int = 0,
        min_score: float = 0.0
    ) -> SearchResult:
        """Semantic similarity search using embeddings"""
        return await resolve_semantic_search(query, filters, size, offset, sort_by, min_score)

    @strawberry.field
    async def hybrid_search(
        self,
        query: str,
        filters: Optional[JSON] = None,
        size: int = 20,
        offset: int = 0,
        keyword_weight: float = 0.5,
        sort_by: Optional[str] = None,
        semantic_weight: float = 0.5
    ) -> SearchResult:
        """Hybrid search combining keyword and semantic search"""
        return await resolve_hybrid_search(query, filters, size, offset, sort_by, keyword_weight, semantic_weight)

    @strawberry.field
    async def content(self, id: str) -> Optional[Content]:
        """Get single content item"""
        return await resolve_content(id)

    @strawberry.field
    async def review_queue(
        self,
        info: Info,
        status: str = "pending",
        source: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None
    ) -> List[ReviewItem]:
        """Get review queue (requires auth) with optional score filtering"""
        return await resolve_review_queue(info, status, source, min_score, max_score)

    @strawberry.field
    async def get_queue_stats(self) -> QueueStats:
        """Get review queue statistics"""
        return await resolve_get_queue_stats()

    @strawberry.field
    async def me(self, info: Info) -> Optional[User]:
        """Get current user (requires auth)"""
        return resolve_me(info)

    @strawberry.field
    async def list_users(self, info: Info) -> List[User]:
        """List all users (requires admin role)"""
        return resolve_list_users(info)

    @strawberry.field
    async def get_model_stats(self) -> ModelStats:
        """Get statistics about the prediction model"""
        return resolve_get_model_stats()

    @strawberry.field
    async def dashboard_data(self, date_range: str = "30d") -> DashboardData:
        """Get comprehensive dashboard data for multi-source analytics"""
        return await resolve_dashboard_data(date_range)

    @strawberry.field
    async def dashboard_stats(self, use_cache: bool = True) -> DashboardStats:
        """Get pre-computed dashboard statistics using Elasticsearch aggregations"""
        return await resolve_dashboard_stats(use_cache)

    @strawberry.field
    async def timeline_stats(self, use_cache: bool = True) -> TimelineStats:
        """Get pre-computed timeline statistics for Explorer visualization"""
        return await resolve_timeline_stats(use_cache)

    @strawberry.field
    async def network_stats(self, use_cache: bool = True, limit: int = 100) -> NetworkStats:
        """Get pre-computed collaboration network statistics"""
        return await resolve_network_stats(use_cache, limit)

    @strawberry.field
    async def get_pipeline_stats(self) -> JSON:
        """Get pipeline statistics for dashboard"""
        return await resolve_get_pipeline_stats()

    @strawberry.field
    async def get_categories(self) -> List[str]:
        """Get all available OHDSI categories"""
        return resolve_get_categories()

    # Citation Queries
    @strawberry.field
    async def citation_network(
        self,
        paper_id: str,
        depth: int = 1,
        max_nodes: int = 100
    ) -> CitationNetwork:
        """Get citation network for a paper"""
        return await resolve_citation_network(paper_id, depth, max_nodes)

    @strawberry.field
    async def citation_stats(self, paper_id: str) -> Optional[CitationStats]:
        """Get citation statistics for a paper"""
        return await resolve_citation_stats(paper_id)

    @strawberry.field
    async def citation_timeline(self, paper_id: str) -> Optional[CitationTimeline]:
        """Get citation timeline for a paper"""
        return await resolve_citation_timeline(paper_id)

    @strawberry.field
    async def citation_paths(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 4
    ) -> List[List[str]]:
        """Find citation paths between two papers"""
        return await resolve_citation_paths(source_id, target_id, max_length)

    @strawberry.field
    async def citation_clusters(
        self,
        paper_ids: List[str],
        min_cluster_size: int = 3
    ) -> CitationClusters:
        """Identify citation clusters among papers"""
        return await resolve_citation_clusters(paper_ids, min_cluster_size)

    @strawberry.field
    async def citation_milestones(self, paper_id: str) -> Optional[CitationMilestones]:
        """Detect citation milestones for a paper"""
        return await resolve_citation_milestones(paper_id)

    @strawberry.field
    async def generate_landscape(
        self,
        query: Optional[str] = None,
        filters: Optional[JSON] = None,
        time_range: Optional[JSON] = None,
        min_papers: int = 100,
        max_papers: int = 1000
    ) -> Landscape:
        """Generate a knowledge accumulation landscape"""
        return await resolve_generate_landscape(query, filters, time_range, min_papers, max_papers)

    @strawberry.field
    async def get_semantic_context(
        self,
        x: float,
        y: float,
        radius: float = 1.0
    ) -> SemanticContext:
        """Get semantic context for a specific coordinate in the landscape"""
        return await resolve_get_semantic_context(x, y, radius)
