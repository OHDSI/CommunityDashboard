from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import logging
from sentence_transformers import SentenceTransformer

from elasticsearch import Elasticsearch
from redis import Redis

from ..config import settings
from ..schemas import SearchResult, ContentResponse

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self, es_client: Elasticsearch, redis_client: Redis):
        self.es = es_client
        self.redis = redis_client
        self.index = settings.content_index
        # Initialize sentence transformer for semantic search
        self.encoder = None
        self._init_encoder()
    
    def _init_encoder(self):
        """Initialize the sentence transformer model"""
        try:
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence transformer initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize sentence transformer: {e}")
            self.encoder = None
    
    async def semantic_search(
        self,
        query: str,
        size: int = 20,
        offset: int = 0,
        sort_by: str = "relevance",
        filters: Dict[str, Any] = None,
        min_score: float = 0.0
    ) -> SearchResult:
        """Execute semantic similarity search using embeddings"""
        
        if not self.encoder:
            logger.warning("Semantic search unavailable, falling back to keyword search")
            return await self.search(query, filters, size, offset)
        
        try:
            # Generate query embedding
            query_embedding = self.encoder.encode(query).tolist()

            # Determine scoring script based on sort mode
            if sort_by == "best-match":
                # Include recency boosting (30% boost for newest, decays over 2 years)
                script_source = """
                    double baseScore = cosineSimilarity(params.query_vector, 'embedding') + 1.0;
                    long publishedMillis = doc['published_date'].value.toInstant().toEpochMilli();
                    long nowMillis = System.currentTimeMillis();
                    long ageMillis = nowMillis - publishedMillis;
                    double twoYearsMillis = 63072000000.0;
                    double recencyFactor = Math.max(0, 1.0 - (ageMillis / twoYearsMillis));
                    return baseScore * (1.0 + recencyFactor * params.recency_weight);
                """
                script_params = {
                    "query_vector": query_embedding,
                    "recency_weight": 0.3  # 30% boost for newest documents
                }
            else:
                # Standard semantic score (no recency)
                script_source = "cosineSimilarity(params.query_vector, 'embedding') + 1.0"
                script_params = {"query_vector": query_embedding}

            # Build search body with script_score for cosine similarity
            # Use bool query to combine vector similarity with author search
            search_body = {
                "size": size,
                "from": offset,
                "track_total_hits": True,
                "query": {
                    "bool": {
                        "should": [
                            {
                                "script_score": {
                                    "query": {
                                        "bool": {
                                            "filter": [{"term": {"approval_status": "approved"}}]
                                        }
                                    },
                                    "script": {
                                        "source": script_source,
                                        "params": script_params
                                    }
                                }
                            },
                            {
                                "nested": {
                                    "path": "authors",
                                    "query": {
                                        "match": {
                                            "authors.name": {
                                                "query": query,
                                                "boost": 2.5
                                            }
                                        }
                                    }
                                }
                            }
                        ],
                        "filter": [{"term": {"approval_status": "approved"}}]
                    }
                }
            }

            # Apply min_score threshold
            # Only apply if explicitly provided - when user sorts by date/popularity,
            # they want those results regardless of similarity score
            if min_score > 0:
                search_body["min_score"] = min_score + 1.0  # Add 1.0 because cosine similarity is shifted by 1

            # Apply additional filters
            if filters:
                filter_clauses = search_body["query"]["bool"]["filter"]
                if "content_type" in filters:
                    filter_clauses.append({"terms": {"content_type": filters["content_type"]}})
                if "categories" in filters:
                    # Ensure categories is a list for terms query
                    categories_value = filters["categories"]
                    if not isinstance(categories_value, list):
                        categories_value = [categories_value]
                    filter_clauses.append({"terms": {"categories": categories_value}})
                # Author filter (nested query)
                if "author" in filters:
                    filter_clauses.append({
                        "nested": {
                            "path": "authors",
                            "query": {
                                "match": {"authors.name": filters["author"]}
                            }
                        }
                    })
                # Filter for articles with citations
                if "has_citations" in filters and filters["has_citations"]:
                    filter_clauses.append({
                        "bool": {
                            "should": [
                                {"exists": {"field": "citations.cited_by"}},
                                {"exists": {"field": "citations.references"}},
                                {"exists": {"field": "citations.similar"}}
                            ],
                            "minimum_should_match": 1
                        }
                    })
                # Support both date_from and publishedAfter for backward compatibility
                if "date_from" in filters:
                    filter_clauses.append({"range": {"published_date": {"gte": filters["date_from"]}}})
                elif "publishedAfter" in filters:
                    filter_clauses.append({"range": {"published_date": {"gte": filters["publishedAfter"]}}})
                if "date_to" in filters:
                    filter_clauses.append({"range": {"published_date": {"lte": filters["date_to"]}}})
                elif "publishedBefore" in filters:
                    filter_clauses.append({"range": {"published_date": {"lte": filters["publishedBefore"]}}})
                if "source" in filters:
                    filter_clauses.append({"term": {"source": filters["source"]}})

            # Add aggregations
            search_body["aggs"] = {
                "sources": {"terms": {"field": "source", "size": 10}},
                "content_types": {"terms": {"field": "content_type"}},
                "categories": {"terms": {"field": "categories", "size": 20}},
                "date_histogram": {
                    "date_histogram": {
                        "field": "published_date",
                        "calendar_interval": "month"
                    }
                },
                # Add total citations (using view count as proxy for now)
                "total_citations": {
                    "sum": {
                        "field": "metrics.view_count",
                        "missing": 0
                    }
                }
            }

            # Add sorting (semantic search defaults to relevance/similarity)
            # Note: For "best-match" and "relevance", no sort clause is added - uses _score
            if sort_by == "date" or sort_by == "date-desc":
                search_body["sort"] = [{"published_date": {"order": "desc"}}]
            elif sort_by == "date-asc":
                search_body["sort"] = [{"published_date": {"order": "asc"}}]
            elif sort_by == "popularity":
                search_body["sort"] = [{"metrics.view_count": {"order": "desc"}}]
            # else: "relevance" or "best-match" use the script_score

            # Execute search
            response = self.es.search(index=self.index, body=search_body)
            
            # Track search
            self._track_search(f"semantic:{query}", filters)
            
            # Parse results
            items = []
            for hit in response["hits"]["hits"]:
                item = hit["_source"]
                item["id"] = hit["_id"]
                item["similarity_score"] = hit["_score"] - 1.0  # Subtract 1.0 to get actual cosine similarity
                
                # Ensure metrics field exists with proper structure
                item = self._normalize_item_fields(item)
                
                # Add computed display fields
                self._add_display_fields(item)
                
                items.append(ContentResponse(**item))
            
            return SearchResult(
                total=response["hits"]["total"]["value"],
                items=items,
                aggregations=self._remap_aggregations(response.get("aggregations", {})),
                took_ms=response["took"]
            )

        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            # Fallback to keyword search
            return await self.search(query, filters, size, offset)
    
    async def hybrid_search(
        self,
        query: str,
        size: int = 20,
        offset: int = 0,
        sort_by: str = "relevance",
        filters: Dict[str, Any] = None,
        keyword_weight: float = 0.5,
        semantic_weight: float = 0.5
    ) -> SearchResult:
        """Execute hybrid search combining keyword and semantic search"""
        
        if not self.encoder:
            logger.warning("Semantic search unavailable, using keyword search only")
            return await self.search(query, filters, size, offset)
        
        try:
            # Generate query embedding
            query_embedding = self.encoder.encode(query).tolist()

            # Determine scoring script based on sort mode
            if sort_by == "best-match":
                # Include recency boosting (30% boost for newest, decays over 2 years)
                script_source = """
                    double baseScore = _score * params.keyword_weight + (cosineSimilarity(params.query_vector, 'embedding') + 1.0) * params.semantic_weight;
                    long publishedMillis = doc['published_date'].value.toInstant().toEpochMilli();
                    long nowMillis = System.currentTimeMillis();
                    long ageMillis = nowMillis - publishedMillis;
                    double twoYearsMillis = 63072000000.0;
                    double recencyFactor = Math.max(0, 1.0 - (ageMillis / twoYearsMillis));
                    return baseScore * (1.0 + recencyFactor * params.recency_weight);
                """
                script_params = {
                    "query_vector": query_embedding,
                    "keyword_weight": keyword_weight,
                    "semantic_weight": semantic_weight,
                    "recency_weight": 0.3  # 30% boost for newest documents
                }
            else:
                # Standard hybrid score (no recency)
                script_source = f"_score * {keyword_weight} + (cosineSimilarity(params.query_vector, 'embedding') + 1.0) * {semantic_weight}"
                script_params = {"query_vector": query_embedding}

            # Build hybrid query combining keyword match and vector similarity
            search_body = {
                "size": size,
                "from": offset,
                "track_total_hits": True,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "script_score": {
                                    "query": {
                                        "bool": {
                                            "should": [
                                                {
                                                    "multi_match": {
                                                        "query": query,
                                                        "fields": ["title^3", "abstract^2", "content"],
                                                        "type": "best_fields",
                                                        "fuzziness": "AUTO",
                                                        "boost": keyword_weight
                                                    }
                                                },
                                                {
                                                    "nested": {
                                                        "path": "authors",
                                                        "query": {
                                                            "match": {
                                                                "authors.name": {
                                                                    "query": query,
                                                                    "boost": 2.5
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            ],
                                            "filter": [{"term": {"approval_status": "approved"}}],
                                            "minimum_should_match": 1
                                        }
                                    },
                                    "script": {
                                        "source": script_source,
                                        "params": script_params
                                    }
                                }
                            }
                        ]
                    }
                }
            }
            
            # Apply filters
            if filters:
                filter_clauses = search_body["query"]["bool"]["must"][0]["script_score"]["query"]["bool"]["filter"]
                if "content_type" in filters:
                    filter_clauses.append({"terms": {"content_type": filters["content_type"]}})
                if "categories" in filters:
                    # Ensure categories is a list for terms query
                    categories_value = filters["categories"]
                    if not isinstance(categories_value, list):
                        categories_value = [categories_value]
                    filter_clauses.append({"terms": {"categories": categories_value}})
                # Author filter (nested query)
                if "author" in filters:
                    filter_clauses.append({
                        "nested": {
                            "path": "authors",
                            "query": {
                                "match": {"authors.name": filters["author"]}
                            }
                        }
                    })
                # Filter for articles with citations
                if "has_citations" in filters and filters["has_citations"]:
                    filter_clauses.append({
                        "bool": {
                            "should": [
                                {"exists": {"field": "citations.cited_by"}},
                                {"exists": {"field": "citations.references"}},
                                {"exists": {"field": "citations.similar"}}
                            ],
                            "minimum_should_match": 1
                        }
                    })
                # Support both date_from and publishedAfter for backward compatibility
                if "date_from" in filters:
                    filter_clauses.append({"range": {"published_date": {"gte": filters["date_from"]}}})
                elif "publishedAfter" in filters:
                    filter_clauses.append({"range": {"published_date": {"gte": filters["publishedAfter"]}}})
                if "date_to" in filters:
                    filter_clauses.append({"range": {"published_date": {"lte": filters["date_to"]}}})
                elif "publishedBefore" in filters:
                    filter_clauses.append({"range": {"published_date": {"lte": filters["publishedBefore"]}}})
                if "source" in filters:
                    filter_clauses.append({"term": {"source": filters["source"]}})

            # Add aggregations and highlighting
            search_body["aggs"] = {
                "sources": {"terms": {"field": "source", "size": 10}},
                "content_types": {"terms": {"field": "content_type"}},
                "categories": {"terms": {"field": "categories", "size": 20}},
                "date_histogram": {
                    "date_histogram": {
                        "field": "published_date",
                        "calendar_interval": "month"
                    }
                }
            }
            
            search_body["highlight"] = {
                "fields": {
                    "title": {},
                    "abstract": {"fragment_size": 150}
                }
            }

            # Add sorting (hybrid search defaults to combined score)
            # Note: For "best-match" and "relevance", no sort clause is added - uses _score
            if sort_by == "date" or sort_by == "date-desc":
                search_body["sort"] = [{"published_date": {"order": "desc"}}]
            elif sort_by == "date-asc":
                search_body["sort"] = [{"published_date": {"order": "asc"}}]
            elif sort_by == "popularity":
                search_body["sort"] = [{"metrics.view_count": {"order": "desc"}}]
            # else: "relevance" or "best-match" use the script_score

            # Execute search
            response = self.es.search(index=self.index, body=search_body)
            
            # Track search
            self._track_search(f"hybrid:{query}", filters)
            
            # Parse results
            items = []
            for hit in response["hits"]["hits"]:
                item = hit["_source"]
                item["id"] = hit["_id"]
                item["hybrid_score"] = hit["_score"]
                if "highlight" in hit:
                    item["highlight"] = hit["highlight"]
                
                # Ensure metrics field exists with proper structure
                item = self._normalize_item_fields(item)
                
                # Add computed display fields
                self._add_display_fields(item)
                
                items.append(ContentResponse(**item))
            
            return SearchResult(
                total=response["hits"]["total"]["value"],
                items=items,
                aggregations=self._remap_aggregations(response.get("aggregations", {})),
                took_ms=response["took"]
            )

        except Exception as e:
            logger.error(f"Hybrid search error: {e}")
            # Fallback to keyword search
            return await self.search(query, filters, size, offset)
    
    async def search(
        self,
        query: Optional[str] = None,
        filters: Dict[str, Any] = None,
        size: int = 20,
        offset: int = 0,
        sort_by: str = "relevance"
    ) -> SearchResult:
        """Execute search with filters and return results"""
        
        # Build search body
        search_body = {
            "size": size,
            "from": offset,
            "track_total_hits": True
        }
        
        # Build query
        must_clauses = []
        filter_clauses = [{"term": {"approval_status": "approved"}}]
        
        if query and query.strip() and query.strip() != "*":
            # Use should clause to search in regular fields OR in nested author field
            must_clauses.append({
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^3", "abstract^2", "content"],
                                "type": "best_fields",
                                "fuzziness": "AUTO"
                            }
                        },
                        {
                            "nested": {
                                "path": "authors",
                                "query": {
                                    "match": {
                                        "authors.name": {
                                            "query": query,
                                            "boost": 2.5
                                        }
                                    }
                                }
                            }
                        }
                    ]
                }
            })
        
        # Apply filters
        if filters:
            if "content_type" in filters:
                filter_clauses.append({"terms": {"content_type": filters["content_type"]}})
            if "categories" in filters:
                # Ensure categories is a list for terms query
                categories_value = filters["categories"]
                if not isinstance(categories_value, list):
                    categories_value = [categories_value]
                filter_clauses.append({"terms": {"categories": categories_value}})
            # Author filter (nested query)
            if "author" in filters:
                filter_clauses.append({
                    "nested": {
                        "path": "authors",
                        "query": {
                            "match": {"authors.name": filters["author"]}
                        }
                    }
                })
            # Filter for articles with citations (nested fields need special handling)
            if "has_citations" in filters and filters["has_citations"]:
                filter_clauses.append({
                    "bool": {
                        "should": [
                            {"nested": {
                                "path": "citations.cited_by",
                                "query": {"exists": {"field": "citations.cited_by.id"}}
                            }},
                            {"nested": {
                                "path": "citations.references",
                                "query": {"exists": {"field": "citations.references.id"}}
                            }},
                            {"nested": {
                                "path": "citations.similar",
                                "query": {"exists": {"field": "citations.similar.id"}}
                            }}
                        ],
                        "minimum_should_match": 1
                    }
                })
            if "source" in filters:
                filter_clauses.append({"term": {"source": filters["source"]}})
            # Support both date_from and publishedAfter for backward compatibility
            if "date_from" in filters:
                filter_clauses.append({"range": {"published_date": {"gte": filters["date_from"]}}})
            elif "publishedAfter" in filters:
                filter_clauses.append({"range": {"published_date": {"gte": filters["publishedAfter"]}}})
            if "date_to" in filters:
                filter_clauses.append({"range": {"published_date": {"lte": filters["date_to"]}}})
            elif "publishedBefore" in filters:
                filter_clauses.append({"range": {"published_date": {"lte": filters["publishedBefore"]}}})
        
        # Combine query clauses
        if must_clauses or filter_clauses:
            search_body["query"] = {
                "bool": {
                    "must": must_clauses if must_clauses else {"match_all": {}},
                    "filter": filter_clauses
                }
            }
        else:
            search_body["query"] = {"match_all": {}}
        
        # Add sorting
        if sort_by == "date" or sort_by == "date-desc":
            search_body["sort"] = [{"published_date": {"order": "desc"}}]
        elif sort_by == "date-asc":
            search_body["sort"] = [{"published_date": {"order": "asc"}}]
        elif sort_by == "popularity":
            search_body["sort"] = [{"metrics.view_count": {"order": "desc"}}]
        # else: relevance (default keyword search scoring)
        
        # Add aggregations for filters
        search_body["aggs"] = {
            "sources": {"terms": {"field": "source", "size": 10}},
            "content_types": {"terms": {"field": "content_type"}},
            "categories": {"terms": {"field": "categories", "size": 20}},
            "date_histogram": {
                "date_histogram": {
                    "field": "published_date",
                    "calendar_interval": "month"
                }
            },
            # Add total citations (using view count as proxy for now)
            "total_citations": {
                "sum": {
                    "field": "metrics.view_count",
                    "missing": 0
                }
            }
        }
        
        # Add highlighting
        if query:
            search_body["highlight"] = {
                "fields": {
                    "title": {},
                    "abstract": {"fragment_size": 150}
                }
            }
        
        # Execute search
        try:
            response = self.es.search(index=self.index, body=search_body)
            
            # Track search in analytics
            self._track_search(query, filters)
            
            # Parse results
            items = []
            for hit in response["hits"]["hits"]:
                item = hit["_source"]
                item["id"] = hit["_id"]
                if "highlight" in hit:
                    item["highlight"] = hit["highlight"]
                
                # Ensure metrics field exists with proper structure
                item = self._normalize_item_fields(item)
                
                # Add computed display fields
                self._add_display_fields(item)
                
                items.append(ContentResponse(**item))
            
            return SearchResult(
                total=response["hits"]["total"]["value"],
                items=items,
                aggregations=self._remap_aggregations(response.get("aggregations", {})),
                took_ms=response["took"]
            )
        except Exception as e:
            logger.error(f"Search error: {e}")
            raise
    
    async def get_suggestions(self, query: str, size: int = 5) -> List[str]:
        """Get search suggestions"""
        suggest_body = {
            "suggest": {
                "title_suggest": {
                    "text": query,
                    "completion": {
                        "field": "suggest",
                        "size": size,
                        "fuzzy": {
                            "fuzziness": "AUTO"
                        }
                    }
                }
            }
        }
        
        try:
            response = self.es.search(index=self.index, body=suggest_body)
            suggestions = []
            for option in response["suggest"]["title_suggest"][0]["options"]:
                suggestions.append(option["text"])
            return suggestions
        except Exception as e:
            logger.error(f"Suggestion error: {e}")
            return []
    
    async def get_filter_aggregations(self) -> Dict[str, Any]:
        """Get available filter options with counts"""
        agg_body = {
            "size": 0,
            "query": {"term": {"approval_status": "approved"}},
            "aggs": {
                "content_types": {"terms": {"field": "content_type"}},
                "categories": {"terms": {"field": "categories", "size": 30}},
                "authors": {"terms": {"field": "authors.name.keyword", "size": 20}},
                "date_range": {
                    "stats": {"field": "published_date"}
                }
            }
        }
        
        try:
            response = self.es.search(index=self.index, body=agg_body)
            return self._remap_aggregations(response["aggregations"])
        except Exception as e:
            logger.error(f"Aggregation error: {e}")
            return {}

    def _remap_aggregations(self, aggs: Dict[str, Any]) -> Dict[str, Any]:
        """Remap category buckets in any aggregation result dict."""
        if "categories" in aggs and "buckets" in aggs["categories"]:
            aggs["categories"]["buckets"] = self._remap_category_buckets(
                aggs["categories"]["buckets"]
            )
        return aggs

    @staticmethod
    def _remap_category_buckets(buckets: List[Dict]) -> List[Dict]:
        """Merge old category aggregation buckets into new 4-category names."""
        from config.ohdsi_categories import OLD_TO_NEW_CATEGORY_MAP, category_system
        new_names = set(category_system.get_all_category_names())
        merged: Dict[str, int] = {}
        for bucket in buckets:
            key = bucket.get("key", "")
            count = bucket.get("doc_count", 0)
            if key in new_names:
                new_key = key
            else:
                new_key = OLD_TO_NEW_CATEGORY_MAP.get(key)
                if not new_key:
                    # Case-insensitive fallback
                    for old_k, new_v in OLD_TO_NEW_CATEGORY_MAP.items():
                        if key.lower() == old_k.lower():
                            new_key = new_v
                            break
                if not new_key:
                    continue
            merged[new_key] = merged.get(new_key, 0) + count
        return [
            {"key": k, "doc_count": v}
            for k, v in sorted(merged.items(), key=lambda x: -x[1])
        ]

    async def get_trending(self, limit: int = 10, timeframe: str = "week") -> List[ContentResponse]:
        """Get trending content"""
        # Calculate date range
        now = datetime.now()
        if timeframe == "day":
            date_from = now - timedelta(days=1)
        elif timeframe == "week":
            date_from = now - timedelta(weeks=1)
        else:  # month
            date_from = now - timedelta(days=30)
        
        search_body = {
            "size": limit,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"approval_status": "approved"}},
                        {"range": {"published_date": {"gte": date_from.isoformat()}}}
                    ]
                }
            },
            "sort": [
                {"view_count": {"order": "desc"}},
                {"bookmark_count": {"order": "desc"}}
            ]
        }
        
        try:
            response = self.es.search(index=self.index, body=search_body)
            items = []
            for hit in response["hits"]["hits"]:
                item = hit["_source"]
                item["id"] = hit["_id"]
                items.append(ContentResponse(**item))
            return items
        except Exception as e:
            logger.error(f"Trending error: {e}")
            return []
    
    async def get_related(self, content_id: str, limit: int = 5) -> List[ContentResponse]:
        """Get related content using more_like_this query"""
        search_body = {
            "size": limit,
            "query": {
                "more_like_this": {
                    "fields": ["title", "abstract", "categories"],
                    "like": [{"_index": self.index, "_id": content_id}],
                    "min_term_freq": 1,
                    "max_query_terms": 12
                }
            }
        }
        
        try:
            response = self.es.search(index=self.index, body=search_body)
            items = []
            for hit in response["hits"]["hits"]:
                item = hit["_source"]
                item["id"] = hit["_id"]
                items.append(ContentResponse(**item))
            return items
        except Exception as e:
            logger.error(f"Related content error: {e}")
            return []
    
    async def execute_aggregation_query(
        self,
        query: Dict[str, Any],
        aggregations: List[Any]
    ) -> Dict[str, Any]:
        """
        Execute an Elasticsearch query with aggregations.

        Args:
            query: Elasticsearch query dict
            aggregations: List of AggregationSpec objects

        Returns:
            Dict with aggregation results and metadata
        """
        try:
            # Convert AggregationSpec objects to Elasticsearch aggregation syntax
            es_aggs = {}
            for agg_spec in aggregations:
                agg_name = agg_spec.name
                agg_type = agg_spec.type
                agg_field = agg_spec.field

                if agg_type == "nested":
                    # Handle nested aggregations (e.g., authors)
                    es_aggs[agg_name] = {
                        "nested": {"path": agg_spec.nested_path},
                        "aggs": {
                            f"{agg_name}_terms": {
                                "terms": {
                                    "field": agg_field,
                                    "size": agg_spec.size or 10
                                }
                            }
                        }
                    }
                elif agg_type == "terms":
                    # Standard terms aggregation
                    es_aggs[agg_name] = {
                        "terms": {
                            "field": agg_field,
                            "size": agg_spec.size or 10
                        }
                    }
                elif agg_type == "date_histogram":
                    # Date histogram aggregation
                    es_aggs[agg_name] = {
                        "date_histogram": {
                            "field": agg_field,
                            "calendar_interval": agg_spec.interval or "month"
                        }
                    }
                elif agg_type == "stats":
                    # Stats aggregation (min, max, avg, sum, count)
                    es_aggs[agg_name] = {
                        "stats": {"field": agg_field}
                    }
                elif agg_type == "cardinality":
                    # Unique count aggregation
                    es_aggs[agg_name] = {
                        "cardinality": {"field": agg_field}
                    }
                elif agg_type == "percentiles":
                    # Percentiles aggregation
                    es_aggs[agg_name] = {
                        "percentiles": {"field": agg_field}
                    }

                # Handle sub-aggregations if present
                if hasattr(agg_spec, 'sub_aggs') and agg_spec.sub_aggs:
                    # Recursively build sub-aggregations
                    sub_aggs_dict = {}
                    for sub_name, sub_spec in agg_spec.sub_aggs.items():
                        if sub_spec.type == "terms":
                            sub_aggs_dict[sub_name] = {
                                "terms": {
                                    "field": sub_spec.field,
                                    "size": sub_spec.size or 10
                                }
                            }
                        elif sub_spec.type == "nested":
                            # Handle nested sub-aggregations (e.g., organizations within years)
                            sub_aggs_dict[sub_name] = {
                                "nested": {"path": sub_spec.nested_path},
                                "aggs": {
                                    f"{sub_name}_terms": {
                                        "terms": {
                                            "field": sub_spec.field,
                                            "size": sub_spec.size or 10
                                        }
                                    }
                                }
                            }
                        elif sub_spec.type == "stats":
                            sub_aggs_dict[sub_name] = {
                                "stats": {"field": sub_spec.field}
                            }
                        elif sub_spec.type == "date_histogram":
                            # Handle date histogram sub-aggregations
                            sub_aggs_dict[sub_name] = {
                                "date_histogram": {
                                    "field": sub_spec.field,
                                    "calendar_interval": sub_spec.interval or "month"
                                }
                            }

                    # Add sub-aggs to the main aggregation
                    if agg_type == "nested":
                        es_aggs[agg_name]["aggs"][f"{agg_name}_terms"]["aggs"] = sub_aggs_dict
                    else:
                        es_aggs[agg_name]["aggs"] = sub_aggs_dict

            # Build the full search body
            search_body = {
                "size": 0,  # Don't return documents, only aggregations
                "query": query.get("query", {"match_all": {}}),
                "aggs": es_aggs
            }

            # Add approval filter
            if "bool" not in search_body["query"]:
                search_body["query"] = {
                    "bool": {
                        "must": [search_body["query"]],
                        "filter": [{"term": {"approval_status": "approved"}}]
                    }
                }

            # Execute query
            logger.info(f"Executing aggregation query with {len(es_aggs)} aggregations")
            logger.info(f"ES aggregation query body: {json.dumps(search_body, indent=2)}")
            response = self.es.search(index=self.index, body=search_body)
            logger.info(f"ES aggregation response: {json.dumps(response.get('aggregations', {}), indent=2)}")

            # Return results with metadata
            return {
                "aggregations": response.get("aggregations", {}),
                "total": response["hits"]["total"]["value"],
                "took": response.get("took", 0)
            }

        except Exception as e:
            logger.error(f"Aggregation query execution failed: {e}")
            raise Exception(f"Failed to execute aggregation query: {str(e)}")

    def _normalize_item_fields(self, item: Dict) -> Dict:
        """Normalize item fields to consistent structure."""
        # Ensure metrics field exists with proper structure
        if "metrics" not in item or not isinstance(item.get("metrics"), dict):
            item["metrics"] = {
                "view_count": item.pop("view_count", 0),
                "bookmark_count": item.pop("bookmark_count", 0),
                "share_count": item.pop("share_count", 0),
                "citation_count": item.pop("citation_count", 0)
            }
        
        # Map legacy field names to new ones for backward compatibility
        if "ai_confidence" in item and "gpt_score" not in item:
            item["gpt_score"] = item["ai_confidence"]
        if "final_score" in item and "combined_score" not in item:
            item["combined_score"] = item["final_score"]
        
        # Ensure categories field exists (map from various possible names)
        if "categories" not in item:
            item["categories"] = item.get("ohdsi_categories", []) or item.get("predicted_categories", [])

        # Map old category names to new 4-category system
        if item.get("categories"):
            from config.ohdsi_categories import map_old_categories
            item["categories"] = map_old_categories(item["categories"])
        
        # Convert year from string to int if present
        if "year" in item and item["year"]:
            try:
                item["year"] = int(item["year"])
            except (ValueError, TypeError):
                item["year"] = None
        
        # Ensure required fields have defaults
        item.setdefault("predicted_categories", [])
        item.setdefault("keywords", [])
        item.setdefault("approval_status", "approved")
        
        return item
    
    def _add_display_fields(self, item: Dict) -> None:
        """Add computed display fields based on source/content type."""
        source = item.get("source", "")
        content_type = item.get("content_type", "")
        
        # Map source-specific display fields
        if source == "youtube" or content_type == "video":
            item["display_type"] = "Video Content"
            item["icon_type"] = "play-circle"
            item["content_category"] = "media"
            # Handle legacy field name
            if "media_duration" in item and "duration" not in item:
                item["duration"] = item["media_duration"]
        elif source == "pubmed" or content_type == "article":
            item["display_type"] = "Research Article"
            item["icon_type"] = "document-text"
            item["content_category"] = "research"
        elif source == "github" or content_type == "repository":
            item["display_type"] = "Code Repository"
            item["icon_type"] = "code"
            item["content_category"] = "code"
        elif source == "discourse" or content_type == "discussion":
            item["display_type"] = "Forum Discussion"
            item["icon_type"] = "chat-bubble"
            item["content_category"] = "community"
        elif source == "wiki" or content_type == "documentation":
            item["display_type"] = "Documentation"
            item["icon_type"] = "book-open"
            item["content_category"] = "reference"
        else:
            # Default values
            item["display_type"] = "Content"
            item["icon_type"] = "document"
            item["content_category"] = "other"
    
    def _track_search(self, query: Optional[str], filters: Optional[Dict]):
        """Track search in analytics"""
        try:
            # Store in user_activity index
            activity = {
                "action": "search",
                "query": query,
                "filters": filters or {},
                "timestamp": datetime.now().isoformat()
            }
            self.es.index(index=settings.activity_index, body=activity)
            
            # Also cache popular searches in Redis
            if query:
                cache_key = f"search:popular:{query[:50]}"
                self.redis.zincrby("popular_searches", 1, query)
        except Exception as e:
            logger.error(f"Failed to track search: {e}")