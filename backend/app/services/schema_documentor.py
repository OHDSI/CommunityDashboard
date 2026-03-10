"""
Schema Documentation Generator

Generates comprehensive documentation for the OHDSI content schema
to be used as context for LLM query generation.
"""

import re
from typing import Dict, List, Any, Set
import json


class SchemaDocumentor:
    """Generate LLM-friendly documentation from Elasticsearch schema."""

    # --- Intent classification for contextual prompt selection ---

    INTENT_KEYWORDS = {
        'author': [
            'author', 'contributor', 'researcher', 'who ', 'collaborat',
            'affiliation', 'orcid', 'organization', 'institution',
        ],
        'temporal': [
            'year', 'month', 'time', 'trend', 'over time', 'when',
            'quarterly', 'timeline', 'surge', 'date', 'recent',
            'historical', 'monthly', 'annual', 'per year',
        ],
        'source': [
            'source', 'pubmed', 'youtube', 'github', 'discourse', 'wiki',
            'channel', 'journal', 'repository', 'video',
        ],
        'category': [
            'category', 'categori', 'topic', 'keyword', 'mesh',
            'classification', 'about', 'subject',
        ],
        'metric': [
            'score', 'citation', 'engagement', 'average', 'statistic',
            'how many', 'unique', 'cardinality', 'stars', 'total count',
        ],
    }

    # DSL patterns to include per intent (must match ## PATTERN N headers)
    INTENT_PATTERNS = {
        'author': ['PATTERN 2', 'PATTERN 3', 'PATTERN 7'],
        'temporal': ['PATTERN 1', 'PATTERN 2', 'PATTERN 4', 'PATTERN 9'],
        'source': ['PATTERN 1', 'PATTERN 6', 'PATTERN 8'],
        'category': ['PATTERN 4', 'PATTERN 6', 'PATTERN 11'],
        'metric': ['PATTERN 5', 'PATTERN 10', 'PATTERN 11'],
        'general': ['PATTERN 1', 'PATTERN 3', 'PATTERN 6', 'PATTERN 7'],
    }

    # Example query indices to include per intent
    INTENT_EXAMPLES = {
        'author': [2, 6],
        'temporal': [1],
        'source': [0, 5],
        'category': [3],
        'metric': [2, 3, 4],
        'general': [0, 1, 6],
    }

    # Schema ### section header substrings to include per intent
    INTENT_SCHEMA_HEADERS = {
        'author': ['Authors & Contributors', 'Source-Specific'],
        'temporal': ['Temporal Fields', 'Aggregation Examples'],
        'source': ['Source-Specific', 'Content Classification'],
        'category': ['Categories & Keywords', 'AI Enhancement'],
        'metric': ['Scoring & Quality', 'Citations', 'Engagement Metrics'],
        'general': ['Authors & Contributors', 'Temporal Fields', 'Categories & Keywords'],
    }

    @staticmethod
    def get_schema_documentation() -> str:
        """
        Generate comprehensive schema documentation for LLM context.

        Returns:
            Formatted schema documentation as a string
        """
        schema_doc = """# OHDSI Content Schema (ohdsi_content_v3)

## Overview
Multi-source knowledge base containing OHDSI-related content from articles, videos, repositories, discussions, and documentation.

## Core Fields

### Identification
- **id** (keyword): Unique identifier for the content
- **source_id** (keyword): Original ID from source system (PMID, video_id, repo_name, etc.)
- **fingerprint** (keyword): Hash for deduplication
- **url** (keyword): Direct link to content
- **doi** (keyword): Digital Object Identifier (for articles)

### Content Classification
- **source** (keyword): Content source
  - Values: pubmed | youtube | github | discourse | wiki
  - Example: "pubmed"
- **content_type** (keyword): Type of content
  - Values: article | video | repository | discussion | documentation
  - Example: "article"
- **approval_status** (keyword): Review status
  - Values: approved | pending | rejected
  - Example: "approved"

### Text Content (Full-text Searchable)
- **title** (text + keyword + suggest): Content title
  - Supports full-text search, exact matching, and autocomplete
  - Example: "OMOP CDM v5.4: Extending the Common Data Model"
- **abstract** (text): Content summary or description
- **content** (text): Full text content or body

### Authors & Contributors (Nested Object Array)
- **authors** (nested array):
  - **name** (text + keyword): Author full name - "Last, First" format
    - For aggregations: use "authors.name.keyword"
  - **affiliation** (text + keyword): Institution or organization name
    - For aggregations: use "authors.affiliation.keyword"
  - **email** (keyword): Author email address
  - **orcid** (keyword): ORCID identifier
  - Example: [{"name": "Ryan, Patrick", "affiliation": "Columbia University", "orcid": "0000-0002-5361-5654"}]
  - **Nested Query Required**: Use nested query syntax for author-based aggregations
  - **IMPORTANT**: Always use .keyword subfields for text aggregations (name.keyword, affiliation.keyword)

### Temporal Fields
- **published_date** (date): Original publication date
  - Format: "2024-11-15T10:30:00Z"
- **year** (integer): Publication year for easy aggregation
  - Example: 2024
- **indexed_date** (date): When content was added to system
- **last_modified** (date): Last update timestamp (for documentation)

### Scoring & Quality
- **ml_score** (float): Machine learning model confidence score (0.0-1.0)
  - Higher = more relevant to OHDSI
  - Example: 0.85
- **ai_confidence** (float): AI assessment confidence (0.0-1.0)
  - Example: 0.92
- **final_score** (float): Combined routing score (0.0-1.0)
  - Used for auto-approval threshold
  - Example: 0.88

### Categories & Keywords
- **categories** (keyword array): Assigned OHDSI categories
  - Example: ["Methodological research", "Clinical applications"]
  - Values: Observational data standards and management, Methodological research,
    Open-source analytics development, Clinical applications
- **keywords** (keyword array): Searchable terms and tags
  - Example: ["OMOP", "CDM", "standardization", "ETL"]
- **mesh_terms** (keyword array): Medical Subject Headings (articles only)
  - Example: ["Database Management Systems", "Electronic Health Records"]

### AI Enhancement
- **ai_enhanced** (boolean): Whether content has AI enrichment
- **ai_is_ohdsi** (boolean): AI determination of OHDSI relevance
- **ai_summary** (text): AI-generated summary
- **ai_tools** (keyword array): OHDSI tools mentioned in content
  - Example: ["Atlas", "Achilles", "HADES"]

### Semantic Search
- **embedding** (dense_vector): 384-dimensional embedding vector
  - Used for semantic/similarity search
  - Cosine similarity metric

### Citations (Nested Object)
- **citations** (object):
  - **cited_by_count** (integer): Number of times cited
  - **references_count** (integer): Number of references
  - **cited_by_ids** (keyword array): IDs of citing content
  - **reference_ids** (keyword array): IDs of referenced content
  - Example: {"cited_by_count": 15, "references_count": 42, "cited_by_ids": ["id1", "id2"]}

### Relationships (Nested Object)
- **relationships** (object):
  - **related_content** (keyword array): Related content IDs
  - **relationship_types** (keyword array): Types of relationships
  - Example: {"related_content": ["id1", "id2"], "relationship_types": ["follows_up", "implements"]}

### Engagement Metrics (Nested Object)
- **metrics** (object):
  - **view_count** (long): Number of views
  - **bookmark_count** (long): Number of bookmarks
  - **share_count** (long): Number of shares
  - **citation_count** (long): Number of citations
  - Example: {"view_count": 1250, "bookmark_count": 45, "share_count": 12, "citation_count": 8}

## Source-Specific Fields

### Article (PubMed) Fields
- **journal** (text + keyword): Journal name
  - Example: "Journal of Biomedical Informatics"
  - ✓ **Supports aggregation** via `journal.keyword` subfield
- **pmid** (keyword): PubMed ID
  - Example: "12345678"

### Video (YouTube) Fields
- **channel_name** (text + keyword): YouTube channel name
  - Example: "OHDSI"
  - ✓ **Supports aggregation** via `channel_name.keyword` subfield
- **duration** (integer): Video length in seconds
  - Example: 3600 (60 minutes)
- **thumbnail_url** (keyword): Video thumbnail URL

### Repository (GitHub) Fields
- **owner** (keyword): Repository owner/organization
  - Example: "OHDSI"
- **stars_count** (integer): GitHub star count
  - Example: 342
- **language** (keyword): Primary programming language
  - Example: "R"
- **topics** (keyword array): GitHub topics/tags
  - Example: ["omop", "cdm", "ohdsi"]

### Discussion (Discourse) Fields
- **reply_count** (integer): Number of replies
  - Example: 15
- **solved** (boolean): Whether question was solved
  - Example: true

### Documentation (Wiki) Fields
- **doc_type** (keyword): Type of documentation
  - Values: tutorial | reference | guide | api_doc
  - Example: "tutorial"

## Aggregation Examples

### Count by Source
```json
{
  "aggs": {
    "sources": {
      "terms": {"field": "source"}
    }
  }
}
```

### Publications by Year
```json
{
  "aggs": {
    "by_year": {
      "terms": {"field": "year", "order": {"_key": "desc"}}
    }
  }
}
```

### Top Authors (Nested Aggregation)
```json
{
  "aggs": {
    "authors": {
      "nested": {"path": "authors"},
      "aggs": {
        "top_authors": {
          "terms": {
            "field": "authors.name.keyword",
            "size": 10
          }
        }
      }
    }
  }
}
```

### Publications by Organization (Nested Aggregation)
```json
{
  "aggs": {
    "organizations": {
      "nested": {"path": "authors"},
      "aggs": {
        "top_orgs": {
          "terms": {
            "field": "authors.affiliation.keyword",
            "size": 10
          }
        }
      }
    }
  }
}
```

### Average ML Score by Category
```json
{
  "aggs": {
    "categories": {
      "terms": {"field": "categories"},
      "aggs": {
        "avg_score": {
          "avg": {"field": "ml_score"}
        }
      }
    }
  }
}
```

### Citation Distribution (Stats Aggregation)
```json
{
  "aggs": {
    "citation_stats": {
      "stats": {"field": "citations.cited_by_count"}
    }
  }
}
```

## Common Query Patterns

### Filter by Date Range
```json
{
  "query": {
    "range": {
      "published_date": {
        "gte": "2024-01-01",
        "lte": "2024-12-31"
      }
    }
  }
}
```

### Filter by Multiple Categories
```json
{
  "query": {
    "terms": {
      "categories": ["CDM", "Vocabulary"]
    }
  }
}
```

### Search with Author Filter (Nested)
```json
{
  "query": {
    "nested": {
      "path": "authors",
      "query": {
        "match": {
          "authors.name": "Patrick Ryan"
        }
      }
    }
  }
}
```

### High-Quality Content (Score Threshold)
```json
{
  "query": {
    "range": {
      "final_score": {
        "gte": 0.7
      }
    }
  }
}
```

## Notes on Data Types

- **text**: Full-text searchable, analyzed
- **keyword**: Exact match, used for filtering and aggregations
- **integer/long**: Numeric values, support range queries and numeric aggregations
- **float**: Floating point numbers for scores
- **date**: ISO 8601 format, support range queries and date histograms
- **boolean**: true/false values
- **nested**: Complex objects requiring nested query syntax
- **object**: Simple objects with dot notation access
- **dense_vector**: Embedding vectors for semantic search

## Field Access Patterns

- Simple fields: Direct access (e.g., `"title"`, `"year"`)
- Keyword subfields: Use `.keyword` for exact match (e.g., `"title.keyword"`)
- Nested arrays: Require nested query syntax (e.g., `"authors"`)
- Object properties: Dot notation (e.g., `"metrics.view_count"`, `"citations.cited_by_count"`)
"""
        return schema_doc

    @staticmethod
    def get_example_queries() -> List[Dict[str, Any]]:
        """
        Get example natural language queries with their expected Elasticsearch translations.

        Returns:
            List of example query-translation pairs
        """
        examples = [
            {
                "natural_language": "Count articles by source",
                "intent": "aggregate_count",
                "elasticsearch_query": {
                    "query": {"match_all": {}},
                    "aggs": {"by_source": {"terms": {"field": "source", "size": 10}}},
                    "size": 0
                },
                "visualization": "bar_chart"
            },
            {
                "natural_language": "Show publication trends by month for 2024",
                "intent": "time_series",
                "elasticsearch_query": {
                    "query": {"range": {"published_date": {"gte": "2024-01-01", "lte": "2024-12-31"}}},
                    "aggs": {"by_month": {"date_histogram": {"field": "published_date", "calendar_interval": "month"}}},
                    "size": 0
                },
                "visualization": "line_chart"
            },
            {
                "natural_language": "How many unique authors are there?",
                "intent": "cardinality",
                "elasticsearch_query": {
                    "query": {"match_all": {}},
                    "aggs": {"unique_authors": {"nested": {"path": "authors"}, "aggs": {"count": {"cardinality": {"field": "authors.name.keyword"}}}}},
                    "size": 0
                },
                "visualization": "metric_card"
            },
            {
                "natural_language": "Average ML score by category",
                "intent": "stats_with_grouping",
                "elasticsearch_query": {
                    "query": {"match_all": {}},
                    "aggs": {"by_category": {"terms": {"field": "categories", "size": 15}, "aggs": {"avg_score": {"avg": {"field": "ml_score"}}}}},
                    "size": 0
                },
                "visualization": "bar_chart"
            },
            {
                "natural_language": "What is the average ML score?",
                "intent": "single_metric",
                "elasticsearch_query": {
                    "query": {"match_all": {}},
                    "aggs": {"avg_ml_score": {"avg": {"field": "ml_score"}}},
                    "size": 0
                },
                "visualization": "metric_card"
            },
            {
                "natural_language": "Distribution of content types",
                "intent": "simple_aggregation",
                "elasticsearch_query": {
                    "query": {"match_all": {}},
                    "aggs": {"by_content_type": {"terms": {"field": "content_type", "size": 10}}},
                    "size": 0
                },
                "visualization": "pie_chart"
            },
            {
                "natural_language": "Top 10 authors by publication count",
                "intent": "nested_aggregation",
                "elasticsearch_query": {
                    "query": {"match_all": {}},
                    "aggs": {"top_authors": {"nested": {"path": "authors"}, "aggs": {"author_names": {"terms": {"field": "authors.name.keyword", "size": 10}}}}},
                    "size": 0
                },
                "visualization": "bar_chart"
            }
        ]

        return examples


    @staticmethod
    def get_elasticsearch_dsl_guide() -> str:
        """Complete Elasticsearch DSL guide with patterns for query generation."""
        return """
## Elasticsearch Query DSL Reference

You will generate Elasticsearch queries directly. All queries follow this structure:

```json
{
  "query": { /* filter/search criteria */ },
  "aggs": { /* aggregations for analytics */ },
  "size": 0  // Don't return documents, only aggregations
}
```

### Query Types Reference

**match_all**: No filtering
```json
{"match_all": {}}
```

**match**: Text search (fuzzy matching, case-insensitive)
Use for: title, abstract, content, keywords (when searching for concepts)
```json
{"match": {"title": "imaging"}}
{"match": {"abstract": "machine learning"}}
{"multi_match": {"query": "imaging", "fields": ["title", "abstract", "keywords"]}}
```

**term**: Exact value match (case-sensitive, no analysis)
Use for: source, content_type, year, approval_status, categories (exact matches)
```json
{"term": {"source": "pubmed"}}
{"term": {"content_type": "article"}}
```

**terms**: Match any of multiple exact values
Use for: Multiple categories, sources, or exact IDs
```json
{"terms": {"source": ["pubmed", "youtube"]}}
{"terms": {"categories": ["Methodological research", "Clinical applications"]}}
```

**range**: Numeric or date ranges
```json
{"range": {"year": {"gte": 2020, "lte": 2024}}}
{"range": {"published_date": {"gte": "2020-01-01"}}}
```

**bool**: Combine multiple conditions
```json
{
  "bool": {
    "must": [...],     // AND conditions
    "filter": [...],   // AND conditions (no scoring)
    "should": [...],   // OR conditions
    "must_not": [...]  // NOT conditions
  }
}
```

**nested**: Access nested documents (REQUIRED for authors field)
```json
{
  "nested": {
    "path": "authors",
    "query": {"match": {"authors.name": "Smith"}}
  }
}
```

### CRITICAL: match vs term Decision Matrix

| Use Case | Query Type | Example |
|----------|------------|---------|
| Search for concepts/topics | `match` | "imaging", "machine learning" |
| Search in title/abstract | `match` or `multi_match` | "OMOP CDM tutorial" |
| Filter by exact category | `term` | source="pubmed" |
| Filter by multiple sources | `terms` | source IN ["pubmed", "youtube"] |
| Search author names | `nested` + `match` | Find "Patrick Ryan" |
| Filter by year range | `range` | year >= 2020 |

### Fields Available for Aggregation

**✅ CAN Aggregate (keyword/numeric types)**:
- `source`, `content_type`, `approval_status` - Content classification
- `categories`, `keywords`, `mesh_terms` - Topical grouping
- `year` - Temporal aggregation
- `authors.name.keyword`, `authors.affiliation.keyword` - Author data (requires nested)
- `journal.keyword` - Journal names (for article grouping)
- `channel_name.keyword` - YouTube channel names (for video grouping)
- `pmid`, `owner`, `language`, `doc_type` - Source-specific IDs

**❌ CANNOT Aggregate (text fields without .keyword)**:
- `title`, `abstract`, `content` - Use for search with `match`, not aggregations

### Aggregation Types Reference

**terms**: Bucket by field values (categories, years, etc.)
```json
{
  "agg_name": {
    "terms": {
      "field": "year",
      "size": 20,
      "order": {"_key": "asc"}  // Optional: sort by key or count
    }
  }
}
```

**date_histogram**: Bucket by time intervals
```json
{
  "agg_name": {
    "date_histogram": {
      "field": "published_date",
      "calendar_interval": "month"  // year, quarter, month, week, day
    }
  }
}
```

**nested**: Access nested fields (REQUIRED for authors.affiliation)
```json
{
  "agg_name": {
    "nested": {
      "path": "authors"
    },
    "aggs": {
      "inner_agg": {
        "terms": {"field": "authors.affiliation.keyword"}
      }
    }
  }
}
```

**stats**: Calculate min, max, avg, sum, count
```json
{
  "agg_name": {
    "stats": {"field": "citations.cited_by_count"}
  }
}
```

**cardinality**: Count unique values
```json
{
  "agg_name": {
    "cardinality": {"field": "authors.name.keyword"}
  }
}
```

### CRITICAL: Nested Field Access Rules

**WRONG**: `"field": "authors.affiliation"` ❌
**RIGHT**: `"field": "authors.affiliation.keyword"` ✅

Why: `.keyword` gives exact values. Without it, text is tokenized into words.

**WRONG**: Direct terms on nested field ❌
```json
{"terms": {"field": "authors.affiliation.keyword"}}
```

**RIGHT**: Wrap in nested aggregation ✅
```json
{
  "organizations": {
    "nested": {"path": "authors"},
    "aggs": {
      "top_orgs": {
        "terms": {"field": "authors.affiliation.keyword", "size": 10}
      }
    }
  }
}
```

### Pattern Library with Real Elasticsearch Syntax

## PATTERN 1: Simple Time Series
**Query**: "Show articles by year"

```json
{
  "query": {"match_all": {}},
  "aggs": {
    "by_year": {
      "terms": {
        "field": "year",
        "size": 20,
        "order": {"_key": "asc"}
      }
    }
  },
  "size": 0
}
```
**Visualization**: `line_chart` or `bar_chart`

## PATTERN 2: Time Series with Groups (CRITICAL FOR YOUR USE CASE)
**Query**: "Show articles by organizations over time" OR "count of articles produced by organizations over time"

```json
{
  "query": {"match_all": {}},
  "aggs": {
    "by_year": {
      "terms": {
        "field": "year",
        "size": 20,
        "order": {"_key": "asc"}
      },
      "aggs": {
        "by_organization": {
          "nested": {
            "path": "authors"
          },
          "aggs": {
            "top_orgs": {
              "terms": {
                "field": "authors.affiliation.keyword",
                "size": 10
              }
            }
          }
        }
      }
    }
  },
  "size": 0
}
```
**Visualization**: `line_chart` (multiple lines, one per organization)

## PATTERN 3: Organizations Only (No Time)
**Query**: "Top organizations by publication count"

```json
{
  "query": {"match_all": {}},
  "aggs": {
    "organizations": {
      "nested": {
        "path": "authors"
      },
      "aggs": {
        "top_orgs": {
          "terms": {
            "field": "authors.affiliation.keyword",
            "size": 10
          }
        }
      }
    }
  },
  "size": 0
}
```
**Visualization**: `bar_chart` or `pie_chart`

## PATTERN 4: Categories Over Time
**Query**: "Articles by category over time"

```json
{
  "query": {"match_all": {}},
  "aggs": {
    "by_year": {
      "terms": {
        "field": "year",
        "size": 20,
        "order": {"_key": "asc"}
      },
      "aggs": {
        "by_category": {
          "terms": {
            "field": "categories",
            "size": 10
          }
        }
      }
    }
  },
  "size": 0
}
```
**Visualization**: `line_chart` (multiple lines) or `bar_chart` (stacked)

## PATTERN 5: Multiple Metrics
**Query**: "Show publication stats by year"

```json
{
  "query": {"match_all": {}},
  "aggs": {
    "by_year": {
      "terms": {"field": "year", "size": 20},
      "aggs": {
        "citation_stats": {
          "stats": {"field": "citations.cited_by_count"}
        }
      }
    }
  },
  "size": 0
}
```
**Visualization**: `table` or `line_chart` (multiple metrics)

## PATTERN 6: Filtered Aggregation
**Query**: "Show articles from 2020-2024 by source"

```json
{
  "query": {
    "range": {"year": {"gte": 2020, "lte": 2024}}
  },
  "aggs": {
    "by_source": {
      "terms": {"field": "source", "size": 10}
    }
  },
  "size": 0
}
```
**Visualization**: `pie_chart` or `bar_chart`

## PATTERN 7: Top Authors/Contributors by Topic (CRITICAL FOR TOPIC-BASED QUERIES)
**Query**: "Who are the top contributors to imaging articles?" OR "Show me authors who contribute to machine learning"

**IMPORTANT**: For topic/concept searches, use `match` or `multi_match` (NOT `terms`!)

```json
{
  "query": {
    "multi_match": {
      "query": "imaging",
      "fields": ["title^3", "abstract^2", "keywords", "mesh_terms"],
      "operator": "or"
    }
  },
  "aggs": {
    "top_authors": {
      "nested": {
        "path": "authors"
      },
      "aggs": {
        "author_names": {
          "terms": {
            "field": "authors.name.keyword",
            "size": 10
          }
        }
      }
    }
  },
  "size": 0
}
```

**Alternative - if you want affiliation instead of names**:
```json
{
  "query": {
    "multi_match": {
      "query": "imaging",
      "fields": ["title", "abstract", "keywords", "mesh_terms"]
    }
  },
  "aggs": {
    "top_organizations": {
      "nested": {
        "path": "authors"
      },
      "aggs": {
        "org_names": {
          "terms": {
            "field": "authors.affiliation.keyword",
            "size": 10
          }
        }
      }
    }
  },
  "size": 0
}
```

**Key Points**:
- Use `multi_match` with multiple fields for concept search
- Boost more important fields (title^3 means 3x weight)
- `match` and `multi_match` are case-insensitive and fuzzy
- NEVER use `terms` query for topic search (it requires exact matches)
- Always wrap author aggregations in `nested` with `"path": "authors"`

**Visualization**: `bar_chart` or `pie_chart`

## PATTERN 8: Articles by Journal / Videos by Channel
**Query**: "Show me articles by journal over time" OR "Which journals publish the most OHDSI articles?" OR "Top YouTube channels for OHDSI content"

**Solution**: Use `.keyword` subfields for aggregation

### Top Journals (Simple Aggregation)
```json
{
  "query": {"term": {"content_type": "article"}},
  "aggs": {
    "top_journals": {
      "terms": {
        "field": "journal.keyword",
        "size": 10,
        "order": {"_count": "desc"}
      }
    }
  },
  "size": 0
}
```

### Articles by Journal Over Time (Nested Aggregation)
```json
{
  "query": {"term": {"content_type": "article"}},
  "aggs": {
    "by_year": {
      "terms": {
        "field": "year",
        "size": 20,
        "order": {"_key": "asc"}
      },
      "aggs": {
        "by_journal": {
          "terms": {
            "field": "journal.keyword",
            "size": 5
          }
        }
      }
    }
  },
  "size": 0
}
```

### Top YouTube Channels (Video Aggregation)
```json
{
  "query": {"term": {"content_type": "video"}},
  "aggs": {
    "top_channels": {
      "terms": {
        "field": "channel_name.keyword",
        "size": 10,
        "order": {"_count": "desc"}
      }
    }
  },
  "size": 0
}
```

**Key Points**:
- Always use `.keyword` subfield for journal and channel_name aggregations
- `journal.keyword` groups articles by journal name
- `channel_name.keyword` groups videos by YouTube channel
- Use nested aggregations for "X by Y over time" queries

**Visualization**: `bar_chart` (top journals/channels) or `line_chart` (over time)

### Decision Tree for Pattern Selection

**STEP 1: Determine Query Type (Filtering)**

**IF** query mentions a topic/concept (imaging, machine learning, CDM, etc.):
→ Use `match` or `multi_match` query
→ Search in: ["title^3", "abstract^2", "keywords", "mesh_terms"]
→ Example: `{"multi_match": {"query": "imaging", "fields": ["title", "abstract", "keywords"]}}`
→ NEVER use `terms` for topic search!

**IF** query filters by exact values (source, content_type, specific category):
→ Use `term` or `terms` query
→ Example: `{"term": {"source": "pubmed"}}` or `{"terms": {"categories": ["Observational data standards and management", "Open-source analytics development"]}}`

**IF** query filters by date/numeric range:
→ Use `range` query
→ Example: `{"range": {"year": {"gte": 2020, "lte": 2024}}}`

**STEP 2: Determine Aggregation Structure**

**IF** query contains "authors/contributors":
→ MUST use `nested` aggregation with `"path": "authors"`
→ Field for names: `"authors.name.keyword"`
→ Field for affiliations: `"authors.affiliation.keyword"`
→ See PATTERN 7 for complete example

**IF** query contains "organizations/institutions/affiliations":
→ MUST use `nested` aggregation with `"path": "authors"`
→ Field: `"authors.affiliation.keyword"` (NOT `authors.affiliation`)

**IF** query has "X over time":
→ Primary agg: `terms` on `"year"` field with `"order": {"_key": "asc"}`
→ Visualization: `line_chart`

**IF** query has "X by Y over time" OR "X over time by Y":
→ Primary agg: `terms` on `"year"`
→ Sub-agg inside primary's `"aggs"` key: Y field (nested if organizations/authors)
→ Creates multiple series for visualization
→ Visualization: `line_chart` (multiple lines, one per group)

**IF** query has temporal + grouping:
→ Structure: time bucket (primary) → category (sub-agg)
→ Visualization: `line_chart` (multiple lines, one per group)

**IF** query has just grouping (no time):
→ Single `terms` or `nested` aggregation
→ Visualization: `bar_chart` or `pie_chart`

**IF** query asks for statistics (avg, min, max):
→ Use `stats` or specific metric aggregations
→ Visualization: `table` or `metric`

### Sub-Aggregation Structure

Sub-aggregations go INSIDE parent at the `"aggs"` key (same level as aggregation type):

```json
{
  "parent_name": {
    "terms": {"field": "year"},
    "aggs": {  // ← Sub-aggs here, NOT at root level
      "child_name": {
        "nested": {"path": "authors"},
        "aggs": {
          "grandchild": {
            "terms": {"field": "authors.affiliation.keyword"}
          }
        }
      }
    }
  }
}
```

## PATTERN 9: Date Histogram (Monthly/Quarterly Time Series)
**Query**: "Show monthly publication trends" or "Articles per quarter in 2024"

```json
{
  "query": {"range": {"published_date": {"gte": "2024-01-01", "lte": "2024-12-31"}}},
  "aggs": {
    "by_month": {
      "date_histogram": {
        "field": "published_date",
        "calendar_interval": "month"
      }
    }
  },
  "size": 0
}
```
**Visualization**: `line_chart`
**Note**: Use `calendar_interval` (not `fixed_interval`) with values: `year`, `quarter`, `month`, `week`, `day`

## PATTERN 10: Cardinality (Unique Counts)
**Query**: "How many unique authors?" or "Count distinct categories"

```json
{
  "query": {"match_all": {}},
  "aggs": {
    "unique_authors": {
      "nested": {"path": "authors"},
      "aggs": {
        "count": {
          "cardinality": {"field": "authors.name.keyword"}
        }
      }
    }
  },
  "size": 0
}
```
**Visualization**: `metric_card`

## PATTERN 11: Stats with Grouping (Average/Sum by Category)
**Query**: "Average ML score by category" or "Total citations by source"

```json
{
  "query": {"match_all": {}},
  "aggs": {
    "by_category": {
      "terms": {"field": "categories", "size": 15},
      "aggs": {
        "avg_score": {"avg": {"field": "ml_score"}}
      }
    }
  },
  "size": 0
}
```
**Visualization**: `bar_chart` (NOT `metric_card` — grouped stats use bar charts)

### Validation Checklist

Before returning your response, verify:

- [ ] All field names exist in schema (year, categories, authors.affiliation.keyword, etc.)
- [ ] Nested fields wrapped in `nested` aggregation with correct `"path"`
- [ ] Used `.keyword` suffix for exact string matches on text fields
- [ ] Sub-aggs placed inside parent agg's `"aggs"` key
- [ ] Visualization type is one of: `bar_chart`, `line_chart`, `pie_chart`, `table`, `metric_card`
- [ ] If query mentions organizations → used `nested` with `"path": "authors"`
- [ ] If query has time dimension → included `year` or `published_date` agg
- [ ] Query structure is valid JSON

### SUPPORTED Visualization Types (use ONLY these)

| Type | When to Use | Data Shape |
|------|-------------|------------|
| `bar_chart` | Category comparisons, grouped stats | Buckets with key/value |
| `line_chart` | Time series, trends over time | Time-ordered buckets |
| `pie_chart` | Simple proportion breakdown (single dimension, ≤10 items) | Buckets with key/value |
| `table` | Complex multi-metric data, document lists, many columns | Items or multi-field buckets |
| `metric_card` | Single number or small set of stats (avg, count, min/max) | Single value or stats object |

### NEVER Use These Visualization Types
- `analytical` — NOT supported by frontend
- `scatter` — NOT supported
- `heatmap` — NOT supported
- `mixed` — NOT supported
- `narrative` — NOT supported
- `metric` — Use `metric_card` instead
- `stacked_area` — NOT supported

### Common Mistakes to Avoid

1. **DO NOT** use `visualization_type: "analytical"` — this is not a valid frontend type. Use `bar_chart`, `line_chart`, `pie_chart`, `table`, or `metric_card`.

2. **DO NOT** generate multiple top-level aggregations unless the query truly needs them. The frontend primarily visualizes the first aggregation. Prefer sub-aggregations for multi-dimensional data.

3. **DO NOT** use `metric_card` for grouped stats (e.g., "avg score by category"). Use `bar_chart` for those — `metric_card` is for single values only.

4. **DO NOT** use `terms` query for topic/concept searches. Use `match` or `multi_match` for free-text concepts like "imaging" or "machine learning".

5. **DO NOT** forget `.keyword` on text fields used in aggregations. `journal` won't work in a terms agg — use `journal.keyword`.
"""

    @staticmethod
    def get_llm_system_prompt() -> str:
        """
        Generate the system prompt for the LLM query generator.

        Returns:
            Complete system prompt with schema context
        """
        schema_doc = SchemaDocumentor.get_schema_documentation()
        examples = SchemaDocumentor.get_example_queries()

        examples_text = "\n\n".join([
            f"### Example {i+1}\n"
            f"**User**: {ex['natural_language']}\n"
            f"**Intent**: {ex['intent']}\n"
            f"**ES Query**:\n```json\n{json.dumps(ex['elasticsearch_query'], indent=2)}\n```\n"
            f"**Visualization**: {ex['visualization']}"
            for i, ex in enumerate(examples)
        ])

        # Build prompt in parts
        prompt_parts = [
            "You are an expert at converting natural language questions into Elasticsearch queries for the OHDSI content database.",
            "",
            "You will generate Elasticsearch Query DSL directly - not an intermediate representation.",
            "",
            schema_doc,
            "",
            SchemaDocumentor.get_elasticsearch_dsl_guide(),
            "",
            """## Your Task

When given a natural language query, you must:

1. **Understand the Intent**: Identify what the user wants (filter, aggregate, compare, trend analysis, etc.)

2. **Generate Elasticsearch Query**: Create a complete Elasticsearch query in this format:
```json
{
  "elasticsearch_query": {
    "query": { /* filter criteria or match_all */ },
    "aggs": { /* aggregations */ },
    "size": 0
  },
  "visualization_type": "line_chart|bar_chart|pie_chart|table|metric",
  "explanation": "Brief explanation of what the query does"
}
```

3. **Use Pattern Library**: Match the user's query to the patterns in the DSL guide above

4. **Handle Organizations**: If query mentions organizations/institutions/affiliations:
   - MUST use nested aggregation with `"path": "authors"`
   - MUST use `"authors.affiliation.keyword"` field

5. **Handle Time Series with Groups**: If query asks for "X by Y over time":
   - Primary aggregation: terms on "year" with order by _key ascending
   - Sub-aggregation: nested (for orgs) or terms (for categories)
   - Visualization: line_chart

6. **Validate**: Ensure all field names match the schema exactly

## Output Format

Your response MUST be valid JSON with exactly this structure:

```json
{
  "elasticsearch_query": {
    "query": { ... },
    "aggs": { ... },
    "size": 0
  },
  "visualization_type": "line_chart|bar_chart|pie_chart|table|metric",
  "explanation": "Brief explanation of what this query does"
}
```

### Complete Example: Organizations Over Time

Input: "count of articles produced by organizations over time"

Output:
```json
{
  "elasticsearch_query": {
    "query": {"match_all": {}},
    "aggs": {
      "by_year": {
        "terms": {
          "field": "year",
          "size": 20,
          "order": {"_key": "asc"}
        },
        "aggs": {
          "by_organization": {
            "nested": {
              "path": "authors"
            },
            "aggs": {
              "top_orgs": {
                "terms": {
                  "field": "authors.affiliation.keyword",
                  "size": 10
                }
              }
            }
          }
        }
      }
    },
    "size": 0
  },
  "visualization_type": "line_chart",
  "explanation": "Shows publication counts by year with breakdowns by top 10 organizations, creating multiple time series lines"
}
```

## Complete Example Document

Here is a complete example of how articles are stored in the ohdsi_content_v3 index:

```json
{
  "id": "34583416",
  "source": "pubmed",
  "source_id": "34583416",
  "title": "Development of Prediction Models for Unplanned Hospital Readmission within 30 Days Based on Common Data Model: A Feasibility Study.",
  "abstract": "BACKGROUND: Unplanned hospital readmission after discharge reflects low satisfaction...",
  "content": "Full article text...",
  "url": "https://pubmed.ncbi.nlm.nih.gov/34583416/",
  "authors": [
    {
      "position": 1,
      "last_name": "Ryu",
      "first_name": "Borim",
      "name": "Ryu, Borim",
      "affiliation": "Office of eHealth Research and Business, Seoul National University Bundang Hospital, Seongnam, South Korea.",
      "orcid": null
    }
  ],
  "published_date": "2021-12-01T00:00:00",
  "year": "2021",
  "journal": "Methods of information in medicine",
  "doi": "10.1055/s-0041-1735166",
  "pmid": "34583416",
  "keywords": [],
  "mesh_terms": ["Area Under Curve", "Feasibility Studies", "Humans", "Patient Readmission"],
  "citations": {
    "cited_by_count": 0,
    "references_count": 0,
    "cited_by_ids": [],
    "reference_ids": []
  },
  "ml_score": 0.974,
  "ai_confidence": 0.85,
  "final_score": 0.938,
  "categories": ["Methodological research", "Observational data standards and management"],
  "approval_status": "approved",
  "content_type": "article",
  "metrics": {
    "view_count": 0,
    "bookmark_count": 0,
    "citation_count": 0
  },
  "ai_enrichment": {
    "is_ohdsi_related": true,
    "confidence_score": 0.85,
    "summary": "This feasibility study aimed to develop and validate prediction models...",
    "key_concepts": ["unplanned hospital readmission", "prediction models", "common data model"],
    "ohdsi_tools_mentioned": ["Common Data Model (CDM)", "Observational Medical Outcomes Partnership"]
  }
}
```

**Key Points from This Example**:
- `authors` is a nested array - requires nested aggregations
- `authors.name.keyword` contains full names like "Ryu, Borim"
- `authors.affiliation.keyword` contains full organization names
- `categories` is a keyword array - can aggregate directly
- `published_date` is a date field - use date_histogram for time-based aggregations
- `year` is an integer - can use terms aggregation
- All text fields have .keyword subfields for exact-match aggregations

## Critical Field Selection Guidelines

When choosing fields for aggregations:
1. **Check the schema carefully** - Use exact field names as documented above
2. **Text vs Keyword** - For aggregations, ALWAYS use .keyword subfields for text fields
3. **Author names** - Use "authors.name.keyword" to get full names, not "authors.name" (which tokenizes)
4. **Verify field types**:
   - keyword fields: Use directly for aggregations (categories, source, content_type)
   - text fields: Must use .keyword subfield for aggregations (title.keyword, authors.name.keyword)
   - nested fields: Require nested aggregation with nested_path specified
5. **When in doubt** - Check the "Notes on Data Types" and "Field Access Patterns" sections above
6. **Refer to the complete example above** - See how real documents are structured

**Remember**: Always use the AggregationSpec format above, NEVER return raw Elasticsearch aggregation syntax.

Be precise with field names and understand the difference between text and keyword fields.

## Complex Analytical Queries

For sophisticated questions involving share evolution, distribution concentration, or multi-step analysis,
express them as standard Elasticsearch aggregations with appropriate visualization types.

### Examples of Complex Queries Expressed as Standard ES

**"Which organizations produce the most articles and how has it changed over time?"**
→ Use PATTERN 2 (time series with groups) with `visualization_type: "line_chart"`

**"What is the distribution of citations across articles?"**
→ Use stats aggregation with `visualization_type: "metric_card"`

**"Compare publication counts by source for 2023 vs 2024"**
→ Use filtered aggregation with year range + terms on source with `visualization_type: "bar_chart"`

**IMPORTANT**: Always use one of the 5 supported visualization types: `bar_chart`, `line_chart`, `pie_chart`, `table`, `metric_card`. Never use `analytical` or any other unsupported type."""
        ]

        return "\n".join(prompt_parts)

    # --- Intent-based contextual prompt methods ---

    @staticmethod
    def classify_query_intent(query: str) -> Set[str]:
        """Classify query into intent categories using keyword matching.

        Returns set of intents like {'author', 'temporal'}.
        Falls back to {'general'} if no specific intent detected.
        """
        query_lower = query.lower()
        intents = set()
        for intent, keywords in SchemaDocumentor.INTENT_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                intents.add(intent)
        if not intents:
            intents.add('general')
        return intents

    @staticmethod
    def _extract_pattern_blocks(dsl_text: str) -> Dict[str, str]:
        """Extract individual PATTERN blocks from the DSL guide text.

        Returns dict mapping pattern name (e.g., 'PATTERN 1') to its full text block.
        """
        patterns = {}
        parts = re.split(r'\n(?=## PATTERN \d+)', dsl_text)
        for part in parts:
            match = re.match(r'## (PATTERN \d+)', part)
            if match:
                patterns[match.group(1)] = part.strip()
        return patterns

    @staticmethod
    def _extract_core_dsl_sections(dsl_text: str) -> Dict[str, str]:
        """Extract non-pattern infrastructure sections from DSL guide.

        Returns dict with keys: 'intro_and_query_types', 'decision_tree', 'validation_and_viz'.
        """
        sections = {}

        # Everything from start to first pattern or "Pattern Library" header
        intro_match = re.search(
            r'(## Elasticsearch Query DSL Reference.*?)(?=\n### Pattern Library|\n## PATTERN)',
            dsl_text, re.DOTALL
        )
        if intro_match:
            sections['intro_and_query_types'] = intro_match.group(1).strip()

        # Decision tree and sub-aggregation structure (between pattern 8 and pattern 9)
        decision_match = re.search(
            r'(### Decision Tree for Pattern Selection.*?### Sub-Aggregation Structure.*?)(?=\n## PATTERN)',
            dsl_text, re.DOTALL
        )
        if decision_match:
            sections['decision_tree'] = decision_match.group(1).strip()

        # Validation + viz types + common mistakes (everything after last pattern)
        tail_match = re.search(
            r'(### Validation Checklist.*)',
            dsl_text, re.DOTALL
        )
        if tail_match:
            sections['validation_and_viz'] = tail_match.group(1).strip()

        return sections

    @staticmethod
    def _extract_schema_field_sections(schema_text: str) -> Dict[str, str]:
        """Extract field sections from schema documentation by ### headers.

        Returns dict mapping header text to section content.
        Also extracts ## level sections (Source-Specific, Aggregation Examples, etc.).
        """
        sections = {}

        # Extract intro (everything before first ### header)
        intro_match = re.search(r'(# OHDSI.*?)(?=\n### )', schema_text, re.DOTALL)
        if intro_match:
            sections['_intro'] = intro_match.group(1).strip()

        # Extract each ### section
        parts = re.split(r'\n(?=### )', schema_text)
        for part in parts:
            header_match = re.match(r'### (.+?)(?:\n|$)', part)
            if header_match:
                sections[header_match.group(1).strip()] = part.strip()

        # Extract ## level sections
        for section_header in [
            'Source-Specific Fields', 'Aggregation Examples',
            'Common Query Patterns', 'Notes on Data Types', 'Field Access Patterns',
        ]:
            pattern = rf'(## {re.escape(section_header)}.*?)(?=\n## |\Z)'
            match = re.search(pattern, schema_text, re.DOTALL)
            if match:
                sections[section_header] = match.group(1).strip()

        return sections

    @classmethod
    def get_contextual_system_prompt(cls, intents: Set[str]) -> str:
        """Assemble a targeted system prompt based on detected query intents.

        Selects only relevant schema sections, DSL patterns, and examples.
        Always includes: role preamble, core fields, query types, aggregation types,
        validation, viz types, common mistakes, output format, example document.

        Args:
            intents: Set of intent strings from classify_query_intent()

        Returns:
            Assembled system prompt string (typically 40-60% smaller than full prompt)
        """
        full_schema = cls.get_schema_documentation()
        full_dsl = cls.get_elasticsearch_dsl_guide()
        all_examples = cls.get_example_queries()

        # Parse into sections
        schema_sections = cls._extract_schema_field_sections(full_schema)
        pattern_blocks = cls._extract_pattern_blocks(full_dsl)
        core_dsl = cls._extract_core_dsl_sections(full_dsl)

        # Collect relevant sections across all detected intents
        relevant_schema_headers: Set[str] = set()
        relevant_patterns: Set[str] = set()
        relevant_example_indices: Set[int] = set()

        for intent in intents:
            for header_substr in cls.INTENT_SCHEMA_HEADERS.get(intent, []):
                relevant_schema_headers.add(header_substr)
            for pattern_name in cls.INTENT_PATTERNS.get(intent, []):
                relevant_patterns.add(pattern_name)
            for idx in cls.INTENT_EXAMPLES.get(intent, []):
                relevant_example_indices.add(idx)

        # Fallback to general if nothing matched
        if not relevant_patterns:
            for p in cls.INTENT_PATTERNS.get('general', []):
                relevant_patterns.add(p)
            for idx in cls.INTENT_EXAMPLES.get('general', []):
                relevant_example_indices.add(idx)

        # --- Build schema section ---
        schema_parts = []
        # Always include intro and core field sections
        if '_intro' in schema_sections:
            schema_parts.append(schema_sections['_intro'])
        core_headers = [
            'Identification',
            'Content Classification',
            'Text Content (Full-text Searchable)',
        ]
        for header in core_headers:
            if header in schema_sections:
                schema_parts.append(schema_sections[header])

        # Include intent-specific field sections
        for header, content in schema_sections.items():
            if header.startswith('_') or header in core_headers:
                continue
            if any(substr in header for substr in relevant_schema_headers):
                schema_parts.append(content)

        # Always include data types and field access
        for key in ['Notes on Data Types', 'Field Access Patterns']:
            if key in schema_sections:
                schema_parts.append(schema_sections[key])

        schema_text = '\n\n'.join(schema_parts)

        # --- Build DSL section ---
        dsl_parts = []
        # Always include intro/query types/agg types/nested rules
        if 'intro_and_query_types' in core_dsl:
            dsl_parts.append(core_dsl['intro_and_query_types'])

        # Include relevant patterns only
        for pattern_name in sorted(relevant_patterns, key=lambda p: int(re.search(r'\d+', p).group())):
            if pattern_name in pattern_blocks:
                dsl_parts.append(pattern_blocks[pattern_name])

        # Include decision tree for complex/temporal queries
        if 'temporal' in intents or 'general' in intents or len(intents) > 1:
            if 'decision_tree' in core_dsl:
                dsl_parts.append(core_dsl['decision_tree'])

        # Always include validation, viz types, common mistakes
        if 'validation_and_viz' in core_dsl:
            dsl_parts.append(core_dsl['validation_and_viz'])

        dsl_text = '\n\n'.join(dsl_parts)

        # --- Build examples ---
        selected_examples = [
            all_examples[i] for i in sorted(relevant_example_indices)
            if i < len(all_examples)
        ]
        if not selected_examples:
            selected_examples = all_examples[:2]

        examples_text = "\n\n".join([
            f"### Example {i+1}\n"
            f"**User**: {ex['natural_language']}\n"
            f"**Intent**: {ex['intent']}\n"
            f"**ES Query**:\n```json\n{json.dumps(ex['elasticsearch_query'], indent=2)}\n```\n"
            f"**Visualization**: {ex['visualization']}"
            for i, ex in enumerate(selected_examples)
        ])

        # --- Assemble prompt ---
        prompt_parts = [
            "You are an expert at converting natural language questions into Elasticsearch queries for the OHDSI content database.",
            "",
            "You will generate Elasticsearch Query DSL directly - not an intermediate representation.",
            "",
            schema_text,
            "",
            dsl_text,
            "",
            _CONTEXTUAL_TASK_INSTRUCTIONS,
            "",
            "## Example Queries",
            "",
            examples_text,
            "",
            _CONTEXTUAL_EXAMPLE_DOCUMENT,
        ]

        return "\n".join(prompt_parts)


# Task instructions shared by contextual prompt (extracted to avoid deep nesting)
_CONTEXTUAL_TASK_INSTRUCTIONS = """## Your Task

When given a natural language query, you must:

1. **Understand the Intent**: Identify what the user wants (filter, aggregate, compare, trend analysis, etc.)

2. **Generate Elasticsearch Query**: Create a complete Elasticsearch query in this format:
```json
{
  "elasticsearch_query": {
    "query": { /* filter criteria or match_all */ },
    "aggs": { /* aggregations */ },
    "size": 0
  },
  "visualization_type": "line_chart|bar_chart|pie_chart|table|metric_card",
  "explanation": "Brief explanation of what the query does"
}
```

3. **Use Pattern Library**: Match the user's query to the patterns provided above

4. **Handle Organizations**: If query mentions organizations/institutions/affiliations:
   - MUST use nested aggregation with `"path": "authors"`
   - MUST use `"authors.affiliation.keyword"` field

5. **Handle Time Series with Groups**: If query asks for "X by Y over time":
   - Primary aggregation: terms on "year" with order by _key ascending
   - Sub-aggregation: nested (for orgs) or terms (for categories)
   - Visualization: line_chart

6. **Validate**: Ensure all field names match the schema exactly

## Output Format

Your response MUST be valid JSON with exactly this structure:

```json
{
  "elasticsearch_query": {
    "query": { ... },
    "aggs": { ... },
    "size": 0
  },
  "visualization_type": "line_chart|bar_chart|pie_chart|table|metric_card",
  "explanation": "Brief explanation of what this query does"
}
```"""

_CONTEXTUAL_EXAMPLE_DOCUMENT = """## Complete Example Document

Here is a complete example of how articles are stored in the ohdsi_content_v3 index:

```json
{
  "id": "34583416",
  "source": "pubmed",
  "source_id": "34583416",
  "title": "Development of Prediction Models for Unplanned Hospital Readmission within 30 Days Based on Common Data Model: A Feasibility Study.",
  "abstract": "BACKGROUND: Unplanned hospital readmission after discharge reflects low satisfaction...",
  "authors": [
    {
      "position": 1,
      "name": "Ryu, Borim",
      "affiliation": "Office of eHealth Research and Business, Seoul National University Bundang Hospital, Seongnam, South Korea.",
      "orcid": null
    }
  ],
  "published_date": "2021-12-01T00:00:00",
  "year": "2021",
  "journal": "Methods of information in medicine",
  "categories": ["Methodological research", "Observational data standards and management"],
  "approval_status": "approved",
  "content_type": "article",
  "ml_score": 0.974,
  "ai_confidence": 0.85,
  "final_score": 0.938,
  "citations": {"cited_by_count": 0, "references_count": 0},
  "metrics": {"view_count": 0, "bookmark_count": 0, "citation_count": 0}
}
```

**Key Points**: `authors` is nested (requires nested aggs), use `.keyword` for text field aggregations, `categories` is a keyword array."""
