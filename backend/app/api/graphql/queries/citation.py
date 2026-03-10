"""
Citation query resolvers.

Handles citation_network, citation_stats, citation_timeline,
citation_paths, citation_clusters, and citation_milestones queries.
"""
from typing import Optional, List

from ..types.content import Author
from ..types.citation import (
    CitationNode, CitationEdge, CitationMetrics, CitationNetwork,
    CitationStats, CitationTimelineEntry, CitationTimeline,
    CitationMilestone, CitationMilestones,
    CitationCluster, CitationClusters,
)
from ..services import citation_service


async def resolve_citation_network(
    paper_id: str,
    depth: int = 1,
    max_nodes: int = 100
) -> CitationNetwork:
    """Get citation network for a paper"""
    data = await citation_service.get_citation_network(paper_id, depth, max_nodes)

    nodes = []
    for node_data in data['nodes']:
        authors = [
            Author(name=author.get('name', ''),
                  email=author.get('email'),
                  affiliation=author.get('affiliation'))
            for author in node_data.get('authors', [])
        ]

        nodes.append(CitationNode(
            id=node_data['id'],
            title=node_data['title'],
            year=node_data.get('year'),  # Made optional for ghost nodes
            authors=authors,
            journal=node_data.get('journal'),
            mlScore=node_data.get('mlScore'),
            citationCount=node_data['citationCount'],
            depth=node_data['depth'],
            nodeType=node_data['nodeType'],
            pagerank=node_data.get('pagerank'),
            inDatabase=node_data.get('inDatabase', True),
            externalUrl=node_data.get('externalUrl')
        ))

    edges = [
        CitationEdge(
            source=edge['source'],
            target=edge['target'],
            type=edge['type'],
            weight=edge['weight']
        )
        for edge in data['edges']
    ]

    metrics = CitationMetrics(
        density=data['metrics']['density'],
        avgDegree=data['metrics']['avgDegree'],
        avgClustering=data['metrics']['avgClustering'],
        connected=data['metrics']['connected']
    )

    return CitationNetwork(
        nodes=nodes,
        edges=edges,
        metrics=metrics,
        rootId=data['rootId'],
        nodeCount=data['nodeCount'],
        edgeCount=data['edgeCount']
    )


async def resolve_citation_stats(paper_id: str) -> Optional[CitationStats]:
    """Get citation statistics for a paper"""
    data = await citation_service.get_citation_stats(paper_id)

    if not data:
        return None

    return CitationStats(
        paperId=data['paperId'],
        title=data['title'],
        year=data['year'],
        totalCitations=data['totalCitations'],
        totalReferences=data['totalReferences'],
        totalSimilar=data['totalSimilar'],
        citationVelocity=data['citationVelocity'],
        hIndexContribution=data['hIndexContribution'],
        yearsSincePublication=data['yearsSincePublication'],
        citationsByYear=data['citationsByYear'],
        recentCitations=data['recentCitations'],
        selfCitations=data['selfCitations']
    )


async def resolve_citation_timeline(paper_id: str) -> Optional[CitationTimeline]:
    """Get citation timeline for a paper"""
    data = await citation_service.get_citation_timeline(paper_id)

    if not data:
        return None

    timeline_entries = [
        CitationTimelineEntry(
            year=entry['year'],
            count=entry['count'],
            papers=entry['papers']
        )
        for entry in data['timeline']
    ]

    return CitationTimeline(
        paperId=data['paperId'],
        title=data['title'],
        publicationYear=data['publicationYear'],
        timeline=timeline_entries,
        totalCitations=data['totalCitations'],
        yearRange=data['yearRange']
    )


async def resolve_citation_paths(
    source_id: str,
    target_id: str,
    max_length: int = 4
) -> List[List[str]]:
    """Find citation paths between two papers"""
    return await citation_service.find_citation_paths(source_id, target_id, max_length)


async def resolve_citation_clusters(
    paper_ids: List[str],
    min_cluster_size: int = 3
) -> CitationClusters:
    """Identify citation clusters among papers"""
    data = await citation_service.get_citation_clusters(paper_ids, min_cluster_size)

    clusters = [
        CitationCluster(
            clusterId=cluster['clusterId'],
            size=cluster['size'],
            papers=cluster['papers'],
            centralPaper=cluster['centralPaper']
        )
        for cluster in data['clusters']
    ]

    return CitationClusters(
        totalPapers=data['totalPapers'],
        clusterCount=data['clusterCount'],
        clusters=clusters,
        unclustered=data['unclustered']
    )


async def resolve_citation_milestones(paper_id: str) -> Optional[CitationMilestones]:
    """Detect citation milestones for a paper"""
    data = await citation_service.detect_citation_milestones(paper_id)

    if not data or not data.get('milestones'):
        return None

    milestones = [
        CitationMilestone(
            type=milestone['type'],
            year=milestone['year'],
            description=milestone['description'],
            metrics=milestone.get('metrics')
        )
        for milestone in data['milestones']
    ]

    return CitationMilestones(
        paperId=data['paperId'],
        milestones=milestones,
        totalMilestones=data['totalMilestones'],
        timespan=data['timespan']
    )
