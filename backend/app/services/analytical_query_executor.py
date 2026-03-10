"""
Analytical Query Executor

Handles complex multi-step analytical queries that require:
- Multiple Elasticsearch queries
- Statistical post-processing
- Temporal analysis
- Comparative analysis
- Narrative generation
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import statistics
from collections import defaultdict

logger = logging.getLogger(__name__)


class AnalyticalQueryExecutor:
    """Execute complex analytical queries with multi-step logic."""

    def __init__(self, search_service):
        """Initialize with search service dependency."""
        self.search_service = search_service

    async def execute_temporal_share_analysis(
        self,
        entity_field: str,  # e.g., "authors.affiliation.keyword"
        time_field: str,    # e.g., "year"
        time_window: Optional[Tuple[int, int]] = None,  # e.g., (2020, 2024)
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Analyze how top entities' share evolves over time.

        Example: "Which organizations contribute majority of articles in recent years,
                 and how has their share evolved?"

        Returns:
            {
                "temporal_shares": {
                    "2020": {"Columbia": 45, "Erasmus": 32, ...},
                    "2021": {...},
                },
                "top_entities": ["Columbia", "Erasmus", ...],
                "total_by_year": {"2020": 150, "2021": 180, ...},
                "share_changes": {
                    "Columbia": {"2020": 30%, "2021": 32%, "change": +2%},
                },
                "narrative": "..."
            }
        """
        logger.info(f"Executing temporal share analysis for {entity_field}")

        # Step 1: Get publications by entity and year
        agg_query = {
            "size": 0,
            "query": self._build_time_filter(time_field, time_window),
            "aggs": {
                "by_year": {
                    "terms": {
                        "field": time_field,
                        "size": 50,
                        "order": {"_key": "asc"}
                    },
                    "aggs": {
                        "by_entity": {
                            "nested": {"path": "authors"} if "authors." in entity_field else {},
                            "aggs": {
                                "entities": {
                                    "terms": {
                                        "field": entity_field,
                                        "size": top_n * 2  # Get more to ensure we have top N
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        # Handle nested fields
        if "authors." in entity_field:
            agg_query["aggs"]["by_year"]["aggs"]["by_entity"] = {
                "nested": {"path": "authors"},
                "aggs": {
                    "entities": {
                        "terms": {
                            "field": entity_field,
                            "size": top_n * 2
                        }
                    }
                }
            }

        result = await self.search_service.es.search(
            index=self.search_service.index,
            body=agg_query
        )

        # Step 2: Process results
        temporal_shares = {}
        total_by_year = {}
        all_entities = set()

        for year_bucket in result["aggregations"]["by_year"]["buckets"]:
            year = str(year_bucket["key"])
            total_by_year[year] = year_bucket["doc_count"]

            entity_buckets = year_bucket["by_entity"].get("entities", {}).get("buckets", [])
            if not entity_buckets:  # Nested case
                entity_buckets = year_bucket["by_entity"].get("entities", {}).get("buckets", [])

            temporal_shares[year] = {}
            for entity_bucket in entity_buckets:
                entity = entity_bucket["key"]
                count = entity_bucket["doc_count"]
                temporal_shares[year][entity] = count
                all_entities.add(entity)

        # Step 3: Identify top entities (by total across all years)
        entity_totals = defaultdict(int)
        for year_data in temporal_shares.values():
            for entity, count in year_data.items():
                entity_totals[entity] += count

        top_entities = sorted(entity_totals.items(), key=lambda x: x[1], reverse=True)[:top_n]
        top_entity_names = [e[0] for e in top_entities]

        # Step 4: Calculate shares and changes
        share_changes = {}
        for entity in top_entity_names:
            shares_over_time = {}
            for year in sorted(temporal_shares.keys()):
                entity_count = temporal_shares[year].get(entity, 0)
                total = total_by_year[year]
                share_pct = (entity_count / total * 100) if total > 0 else 0
                shares_over_time[year] = {
                    "count": entity_count,
                    "share": round(share_pct, 1),
                    "total": total
                }

            # Calculate year-over-year change
            years_sorted = sorted(shares_over_time.keys())
            if len(years_sorted) >= 2:
                first_year_share = shares_over_time[years_sorted[0]]["share"]
                last_year_share = shares_over_time[years_sorted[-1]]["share"]
                absolute_change = round(last_year_share - first_year_share, 1)
                relative_change = round((absolute_change / first_year_share * 100) if first_year_share > 0 else 0, 1)
            else:
                absolute_change = 0
                relative_change = 0

            share_changes[entity] = {
                "shares_over_time": shares_over_time,
                "absolute_change": absolute_change,
                "relative_change": relative_change
            }

        # Step 5: Generate narrative
        narrative = self._generate_temporal_share_narrative(
            top_entity_names,
            share_changes,
            total_by_year
        )

        return {
            "temporal_shares": temporal_shares,
            "top_entities": top_entity_names,
            "top_entities_data": [{"name": e[0], "total": e[1]} for e in top_entities],
            "total_by_year": total_by_year,
            "share_changes": share_changes,
            "narrative": narrative,
            "visualization_type": "mixed",
            "primary_chart": "stacked_area",
            "chart_data": self._format_for_stacked_area(share_changes, top_entity_names)
        }

    async def detect_publication_surges(
        self,
        time_field: str = "year",
        entity_field: Optional[str] = None,
        milestone_events: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Detect publication surges and correlate with events.

        Example: "Are there detectable publication surges corresponding to major
                 OHDSI milestones?"

        Args:
            milestone_events: Dict of year -> event description

        Returns:
            {
                "publication_timeline": {"2015": 45, "2016": 67, ...},
                "surges": [{"year": 2017, "increase_pct": 45, "event": "OHDSI Symposium"}],
                "top_contributors_during_surges": {...},
                "narrative": "..."
            }
        """
        logger.info("Detecting publication surges")

        # Default OHDSI milestone events
        if milestone_events is None:
            milestone_events = {
                "2014": "OHDSI Founded",
                "2016": "First OHDSI Global Symposium",
                "2018": "OMOP CDM v6.0 Release",
                "2020": "COVID-19 Research Surge",
                "2022": "OHDSI Europe Chapter Launch"
            }

        # Step 1: Get publication counts by year
        agg_query = {
            "size": 0,
            "query": {"match_all": {}},
            "aggs": {
                "by_year": {
                    "terms": {
                        "field": time_field,
                        "size": 50,
                        "order": {"_key": "asc"}
                    }
                }
            }
        }

        # If entity field provided, get entity breakdown for surge periods
        if entity_field:
            agg_query["aggs"]["by_year"]["aggs"] = {
                "top_entities": {
                    "nested": {"path": "authors"} if "authors." in entity_field else {},
                    "aggs": {
                        "entities": {
                            "terms": {
                                "field": entity_field,
                                "size": 10
                            }
                        }
                    }
                }
            }

            if "authors." in entity_field:
                agg_query["aggs"]["by_year"]["aggs"]["top_entities"] = {
                    "nested": {"path": "authors"},
                    "aggs": {
                        "entities": {
                            "terms": {
                                "field": entity_field,
                                "size": 10
                            }
                        }
                    }
                }

        result = await self.search_service.es.search(
            index=self.search_service.index,
            body=agg_query
        )

        # Step 2: Process timeline
        timeline = {}
        entity_by_year = {}

        for bucket in result["aggregations"]["by_year"]["buckets"]:
            year = str(bucket["key"])
            count = bucket["doc_count"]
            timeline[year] = count

            if entity_field and "top_entities" in bucket:
                entities_data = bucket["top_entities"]
                if "entities" in entities_data:
                    entity_by_year[year] = [
                        {"name": b["key"], "count": b["doc_count"]}
                        for b in entities_data["entities"]["buckets"]
                    ]

        # Step 3: Detect surges (threshold: >30% increase year-over-year)
        surges = []
        years_sorted = sorted(timeline.keys())

        for i in range(1, len(years_sorted)):
            prev_year = years_sorted[i-1]
            curr_year = years_sorted[i]
            prev_count = timeline[prev_year]
            curr_count = timeline[curr_year]

            if prev_count > 0:
                increase_pct = ((curr_count - prev_count) / prev_count) * 100

                if increase_pct > 30:  # Surge threshold
                    surge_info = {
                        "year": curr_year,
                        "count": curr_count,
                        "prev_count": prev_count,
                        "increase_pct": round(increase_pct, 1),
                        "event": milestone_events.get(curr_year, "No known event"),
                        "top_contributors": entity_by_year.get(curr_year, [])[:5]
                    }
                    surges.append(surge_info)

        # Step 4: Generate narrative
        narrative = self._generate_surge_narrative(timeline, surges, milestone_events)

        return {
            "publication_timeline": timeline,
            "surges": surges,
            "milestone_events": milestone_events,
            "top_contributors_during_surges": {s["year"]: s["top_contributors"] for s in surges},
            "narrative": narrative,
            "visualization_type": "mixed",
            "primary_chart": "line_with_events",
            "chart_data": self._format_timeline_with_events(timeline, surges, milestone_events)
        }

    async def analyze_distribution_concentration(
        self,
        entity_field: str,
        time_field: str = "year",
        time_window: Optional[Tuple[int, int]] = None
    ) -> Dict[str, Any]:
        """
        Analyze distribution of publications across entities using Gini coefficient.

        Example: "What is the distribution of article counts per organization per year?"

        Returns:
            {
                "gini_by_year": {"2020": 0.65, "2021": 0.68, ...},
                "top5_vs_rest": {"2020": {"top5": 450, "rest": 200}, ...},
                "concentration_trend": "increasing" | "decreasing" | "stable",
                "narrative": "..."
            }
        """
        logger.info(f"Analyzing distribution concentration for {entity_field}")

        # Step 1: Get entity counts by year
        agg_query = {
            "size": 0,
            "query": self._build_time_filter(time_field, time_window),
            "aggs": {
                "by_year": {
                    "terms": {
                        "field": time_field,
                        "size": 50,
                        "order": {"_key": "asc"}
                    },
                    "aggs": {
                        "entities": {
                            "nested": {"path": "authors"} if "authors." in entity_field else {},
                            "aggs": {
                                "entity_counts": {
                                    "terms": {
                                        "field": entity_field,
                                        "size": 500  # Get many to calculate distribution
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        if "authors." in entity_field:
            agg_query["aggs"]["by_year"]["aggs"]["entities"] = {
                "nested": {"path": "authors"},
                "aggs": {
                    "entity_counts": {
                        "terms": {
                            "field": entity_field,
                            "size": 500
                        }
                    }
                }
            }

        result = await self.search_service.es.search(
            index=self.search_service.index,
            body=agg_query
        )

        # Step 2: Calculate Gini coefficient and concentration metrics by year
        gini_by_year = {}
        top5_vs_rest = {}

        for year_bucket in result["aggregations"]["by_year"]["buckets"]:
            year = str(year_bucket["key"])

            entity_counts_data = year_bucket["entities"]
            if "entity_counts" in entity_counts_data:
                entity_buckets = entity_counts_data["entity_counts"]["buckets"]
            else:
                entity_buckets = []

            counts = [b["doc_count"] for b in entity_buckets]

            if len(counts) > 1:
                # Calculate Gini coefficient
                gini = self._calculate_gini(counts)
                gini_by_year[year] = round(gini, 3)

                # Top 5 vs rest
                counts_sorted = sorted(counts, reverse=True)
                top5_sum = sum(counts_sorted[:5])
                rest_sum = sum(counts_sorted[5:])
                top5_vs_rest[year] = {
                    "top5": top5_sum,
                    "rest": rest_sum,
                    "top5_percentage": round((top5_sum / (top5_sum + rest_sum)) * 100, 1) if (top5_sum + rest_sum) > 0 else 0
                }

        # Step 3: Determine concentration trend
        years_sorted = sorted(gini_by_year.keys())
        if len(years_sorted) >= 3:
            recent_gini = statistics.mean([gini_by_year[y] for y in years_sorted[-3:]])
            early_gini = statistics.mean([gini_by_year[y] for y in years_sorted[:3]])

            if recent_gini > early_gini + 0.05:
                trend = "increasing"
            elif recent_gini < early_gini - 0.05:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        # Step 4: Generate narrative
        narrative = self._generate_concentration_narrative(
            gini_by_year,
            top5_vs_rest,
            trend
        )

        return {
            "gini_by_year": gini_by_year,
            "top5_vs_rest": top5_vs_rest,
            "concentration_trend": trend,
            "narrative": narrative,
            "visualization_type": "mixed",
            "primary_chart": "line",  # Gini over time
            "secondary_chart": "stacked_bar",  # Top5 vs rest
            "chart_data": {
                "gini_trend": [{"year": y, "gini": g} for y, g in gini_by_year.items()],
                "concentration": [
                    {"year": y, "top5": d["top5"], "rest": d["rest"]}
                    for y, d in top5_vs_rest.items()
                ]
            }
        }

    def _calculate_gini(self, counts: List[int]) -> float:
        """
        Calculate Gini coefficient for distribution.

        Gini = 0 means perfect equality (all entities have same count)
        Gini = 1 means perfect inequality (one entity has everything)
        """
        if not counts or len(counts) == 0:
            return 0.0

        sorted_counts = sorted(counts)
        n = len(sorted_counts)
        cumsum = 0

        for i, count in enumerate(sorted_counts):
            cumsum += (i + 1) * count

        total = sum(sorted_counts)
        if total == 0:
            return 0.0

        gini = (2 * cumsum) / (n * total) - (n + 1) / n
        return gini

    def _build_time_filter(
        self,
        time_field: str,
        time_window: Optional[Tuple[int, int]]
    ) -> Dict[str, Any]:
        """Build Elasticsearch time range filter."""
        if time_window:
            return {
                "bool": {
                    "must": [
                        {"range": {time_field: {"gte": time_window[0], "lte": time_window[1]}}},
                        {"term": {"approval_status": "approved"}}
                    ]
                }
            }
        return {
            "bool": {
                "must": [
                    {"term": {"approval_status": "approved"}}
                ]
            }
        }

    def _generate_temporal_share_narrative(
        self,
        top_entities: List[str],
        share_changes: Dict[str, Dict],
        total_by_year: Dict[str, int]
    ) -> str:
        """Generate narrative for temporal share analysis."""
        if not top_entities:
            return "No data available for temporal share analysis."

        top_entity = top_entities[0]
        top_entity_data = share_changes[top_entity]

        years = sorted(top_entity_data["shares_over_time"].keys())
        first_year = years[0]
        last_year = years[-1]

        first_share = top_entity_data["shares_over_time"][first_year]["share"]
        last_share = top_entity_data["shares_over_time"][last_year]["share"]
        change = top_entity_data["absolute_change"]

        narrative = f"**{top_entity}** has been the leading contributor from {first_year} to {last_year}, "

        if change > 0:
            narrative += f"increasing its share from **{first_share}%** to **{last_share}%** (↑{change}% points). "
        elif change < 0:
            narrative += f"though its share decreased from **{first_share}%** to **{last_share}%** (↓{abs(change)}% points). "
        else:
            narrative += f"maintaining a stable share around **{first_share}%**. "

        # Mention runner-up if available
        if len(top_entities) > 1:
            runner_up = top_entities[1]
            runner_up_last_share = share_changes[runner_up]["shares_over_time"][last_year]["share"]
            narrative += f"**{runner_up}** follows with **{runner_up_last_share}%** of publications in {last_year}."

        return narrative

    def _generate_surge_narrative(
        self,
        timeline: Dict[str, int],
        surges: List[Dict],
        milestone_events: Dict[str, str]
    ) -> str:
        """Generate narrative for surge detection."""
        if not surges:
            return "No significant publication surges detected during the analysis period."

        narrative = f"**{len(surges)} significant publication surge(s)** detected:\n\n"

        for surge in surges[:3]:  # Top 3 surges
            year = surge["year"]
            increase = surge["increase_pct"]
            event = surge["event"]

            narrative += f"- **{year}**: {increase}% increase "
            if event != "No known event":
                narrative += f"(coinciding with *{event}*) "

            if surge["top_contributors"]:
                top_org = surge["top_contributors"][0]["name"]
                narrative += f"— led by **{top_org}**"

            narrative += "\n"

        return narrative.strip()

    def _generate_concentration_narrative(
        self,
        gini_by_year: Dict[str, float],
        top5_vs_rest: Dict[str, Dict],
        trend: str
    ) -> str:
        """Generate narrative for concentration analysis."""
        if not gini_by_year:
            return "Insufficient data for concentration analysis."

        latest_year = max(gini_by_year.keys())
        latest_gini = gini_by_year[latest_year]
        latest_top5_pct = top5_vs_rest[latest_year]["top5_percentage"]

        narrative = f"Publication concentration shows a **{trend}** trend. "
        narrative += f"In {latest_year}, the Gini coefficient is **{latest_gini}**, "
        narrative += f"with the top 5 contributors accounting for **{latest_top5_pct}%** of all publications. "

        if latest_gini > 0.7:
            narrative += "This indicates **high concentration** — a small number of organizations dominate the research output."
        elif latest_gini > 0.5:
            narrative += "This indicates **moderate concentration** — research contributions are somewhat distributed."
        else:
            narrative += "This indicates **low concentration** — contributions are relatively well-distributed across organizations."

        return narrative

    def _format_for_stacked_area(
        self,
        share_changes: Dict[str, Dict],
        top_entities: List[str]
    ) -> List[Dict]:
        """Format data for stacked area chart."""
        chart_data = []

        # Get all years
        if not top_entities or not share_changes:
            return []

        first_entity_shares = share_changes[top_entities[0]]["shares_over_time"]
        years = sorted(first_entity_shares.keys())

        for year in years:
            data_point = {"year": year}
            for entity in top_entities:
                share = share_changes[entity]["shares_over_time"].get(year, {}).get("share", 0)
                data_point[entity] = share
            chart_data.append(data_point)

        return chart_data

    def _format_timeline_with_events(
        self,
        timeline: Dict[str, int],
        surges: List[Dict],
        milestone_events: Dict[str, str]
    ) -> Dict[str, Any]:
        """Format timeline data with event markers."""
        timeline_data = [
            {"year": year, "publications": count, "is_surge": any(s["year"] == year for s in surges)}
            for year, count in sorted(timeline.items())
        ]

        event_markers = [
            {"year": year, "event": event}
            for year, event in milestone_events.items()
            if year in timeline
        ]

        return {
            "timeline": timeline_data,
            "events": event_markers,
            "surges": surges
        }
