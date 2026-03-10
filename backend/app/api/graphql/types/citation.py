"""
Citation-related GraphQL types.

Includes all types for citation network visualization,
citation statistics, timeline, milestones, and clustering.
"""
import strawberry
from strawberry.scalars import JSON
from typing import Optional, List

from .content import Author


@strawberry.type
class CitationNode:
    id: str
    title: str
    year: Optional[int] = None  # Made optional for ghost nodes
    authors: List[Author] = strawberry.field(default_factory=list)
    journal: Optional[str] = None
    mlScore: Optional[float] = None
    citationCount: int = 0
    depth: int = 0
    nodeType: str = ""  # 'root', 'citation', 'reference', 'similar', 'ghost'
    pagerank: Optional[float] = None
    inDatabase: bool = True  # New field to indicate if paper is in our database
    externalUrl: Optional[str] = None  # New field for external link


@strawberry.type
class CitationEdge:
    source: str
    target: str
    type: str  # 'cites', 'similar'
    weight: float


@strawberry.type
class CitationMetrics:
    density: float
    avgDegree: float
    avgClustering: float
    connected: bool


@strawberry.type
class CitationNetwork:
    nodes: List[CitationNode]
    edges: List[CitationEdge]
    metrics: CitationMetrics
    rootId: str
    nodeCount: int
    edgeCount: int


@strawberry.type
class CitationStats:
    paperId: str
    title: str
    year: int
    totalCitations: int
    totalReferences: int
    totalSimilar: int
    citationVelocity: float
    hIndexContribution: int
    yearsSincePublication: int
    citationsByYear: JSON
    recentCitations: int
    selfCitations: int


@strawberry.type
class CitationTimelineEntry:
    year: int
    count: int
    papers: List[JSON]  # List of paper summaries


@strawberry.type
class CitationTimeline:
    paperId: str
    title: str
    publicationYear: int
    timeline: List[CitationTimelineEntry]
    totalCitations: int
    yearRange: JSON


@strawberry.type
class CitationMilestone:
    type: str
    year: int
    description: str
    metrics: Optional[JSON] = None


@strawberry.type
class CitationMilestones:
    paperId: str
    milestones: List[CitationMilestone]
    totalMilestones: int
    timespan: JSON


@strawberry.type
class CitationCluster:
    clusterId: int
    size: int
    papers: List[JSON]
    centralPaper: JSON


@strawberry.type
class CitationClusters:
    totalPapers: int
    clusterCount: int
    clusters: List[CitationCluster]
    unclustered: int
