"""
Landscape-related GraphQL types.

Includes all types for the knowledge accumulation landscape
visualization: terrain, territories, gaps, and paper positions.
"""
import strawberry
from strawberry.scalars import JSON
from typing import Optional, List


@strawberry.type
class Position:
    x: float
    y: float


@strawberry.type
class TerritoryLabel:
    primary: str
    stats: str
    concepts: List[str]
    tools: List[str]
    categories: List[str]


@strawberry.type
class Territory:
    id: int
    label: TerritoryLabel
    papers: List[str]  # Paper IDs
    centroid: List[float]
    size: int
    type: str  # established, emerging, developing
    representative_papers: Optional[List[JSON]] = None


@strawberry.type
class SemanticGap:
    position: List[float]
    label: str
    type: str  # sparse_region, missing_combination, missing_bridge
    sparsity: Optional[float] = None
    concepts: Optional[List[str]] = None
    suggested_research: Optional[List[str]] = None
    nearest_papers: Optional[List[str]] = None
    territories: Optional[List[int]] = None


@strawberry.type
class TerrainData:
    grid: JSON  # Contains x and y arrays
    heights: List[List[float]]
    bounds: JSON  # Contains x_min, x_max, y_min, y_max
    colors: Optional[JSON] = None  # Color map data with RGB values
    semantic_grid: Optional[List[JSON]] = None  # Grid-based semantic labels


@strawberry.type
class SemanticContext:
    x: float
    y: float
    radius: float
    label: str
    paperCount: int
    nearbyPapers: List[JSON]
    dominantCategories: List[str]
    dominantTools: List[str]
    researchSuggestions: List[str]
    density: float


@strawberry.type
class PaperPosition:
    id: str
    title: str
    year: int
    position: List[float]
    citations: int
    ml_score: float
    content_type: str
    source: str


@strawberry.type
class LandscapeStats:
    total_papers: int
    total_territories: int
    total_gaps: int
    year_range: JSON  # Contains start and end


@strawberry.type
class Landscape:
    terrain: TerrainData
    territories: List[Territory]
    gaps: List[SemanticGap]
    papers: List[PaperPosition]
    stats: LandscapeStats
    evolution: Optional[JSON] = None
    error: Optional[str] = None
