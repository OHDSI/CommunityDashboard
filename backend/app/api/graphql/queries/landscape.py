"""
Landscape query resolvers.

Handles generate_landscape and get_semantic_context queries.
"""
from typing import Optional
from strawberry.scalars import JSON

from ..types.landscape import (
    TerritoryLabel, Territory, SemanticGap, TerrainData,
    SemanticContext, PaperPosition, LandscapeStats, Landscape,
)
from ..services import landscape_service


async def resolve_generate_landscape(
    query: Optional[str] = None,
    filters: Optional[JSON] = None,
    time_range: Optional[JSON] = None,
    min_papers: int = 100,
    max_papers: int = 1000
) -> Landscape:
    """Generate a knowledge accumulation landscape"""
    data = await landscape_service.generate_landscape(
        query=query,
        filters=filters,
        time_range=time_range,
        min_papers=min_papers,
        max_papers=max_papers
    )

    # Handle error case
    if 'error' in data:
        return Landscape(
            terrain=TerrainData(grid={}, heights=[], bounds={}),
            territories=[],
            gaps=[],
            papers=[],
            stats=LandscapeStats(
                total_papers=data.get('papers_found', 0),
                total_territories=0,
                total_gaps=0,
                year_range={}
            ),
            error=data['error']
        )

    # Convert data to GraphQL types
    terrain = TerrainData(
        grid=data['terrain']['grid'],
        heights=data['terrain']['heights'],
        bounds=data['terrain']['bounds'],
        colors=data['terrain'].get('colors'),
        semantic_grid=data['terrain'].get('semantic_grid')
    )

    territories = []
    for t in data.get('territories', []):
        label = TerritoryLabel(
            primary=t['label']['primary'],
            stats=t['label']['stats'],
            concepts=t['label'].get('concepts', []),
            tools=t['label'].get('tools', []),
            categories=t['label'].get('categories', [])
        )
        territories.append(Territory(
            id=t['id'],
            label=label,
            papers=t['papers'],
            centroid=t['centroid'],
            size=t['size'],
            type=t['type'],
            representative_papers=t.get('representative_papers')
        ))

    gaps = []
    for g in data.get('gaps', []):
        gaps.append(SemanticGap(
            position=g['position'],
            label=g['label'],
            type=g['type'],
            sparsity=g.get('sparsity'),
            concepts=g.get('concepts'),
            suggested_research=g.get('suggested_research'),
            nearest_papers=g.get('nearest_papers'),
            territories=g.get('territories')
        ))

    papers = []
    for p in data.get('papers', []):
        papers.append(PaperPosition(
            id=p['id'],
            title=p['title'],
            year=p['year'],
            position=p['position'],
            citations=p['citations'],
            ml_score=p['ml_score'],
            content_type=p['content_type'],
            source=p['source']
        ))

    stats = LandscapeStats(
        total_papers=data['stats']['total_papers'],
        total_territories=data['stats']['total_territories'],
        total_gaps=data['stats']['total_gaps'],
        year_range=data['stats']['year_range']
    )

    return Landscape(
        terrain=terrain,
        territories=territories,
        gaps=gaps,
        papers=papers,
        stats=stats,
        evolution=data.get('evolution')
    )


async def resolve_get_semantic_context(
    x: float,
    y: float,
    radius: float = 1.0
) -> SemanticContext:
    """Get semantic context for a specific coordinate in the landscape"""
    context_data = await landscape_service.get_semantic_context(
        x=x, y=y, radius=radius
    )

    return SemanticContext(
        x=context_data['x'],
        y=context_data['y'],
        radius=context_data['radius'],
        label=context_data.get('label', 'Unknown'),
        paperCount=context_data.get('paper_count', 0),
        nearbyPapers=context_data.get('nearby_papers', []),
        dominantCategories=context_data.get('dominant_categories', []),
        dominantTools=context_data.get('dominant_tools', []),
        researchSuggestions=context_data.get('research_suggestions', []),
        density=context_data.get('density', 0.0)
    )
