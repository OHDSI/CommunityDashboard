from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from elasticsearch import Elasticsearch
import redis
import os
import logging
from .config import settings

logger = logging.getLogger(__name__)

# PostgreSQL
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Elasticsearch - synchronous client (always available)
es_kwargs = {
    "timeout": settings.elasticsearch_timeout,
}
if settings.elasticsearch_password:
    es_kwargs["basic_auth"] = ("elastic", settings.elasticsearch_password)

es_client = Elasticsearch(
    settings.elasticsearch_url,
    **es_kwargs
)

# Elasticsearch - async client (only import when not in Celery)
# Celery workers should only use the synchronous client
async_es_client = None
if not os.environ.get('CELERY_WORKER_RUNNING'):
    try:
        from elasticsearch import AsyncElasticsearch
        async_es_client = AsyncElasticsearch(
            settings.elasticsearch_url,
            **es_kwargs
        )
    except ImportError:
        pass  # AsyncElasticsearch not available in Celery context

# Redis
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

# Helper functions for Elasticsearch
def create_indices():
    """Create Elasticsearch indices with proper mappings"""
    
    # ohdsi_content index mapping
    content_mapping = {
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "source": {"type": "keyword"},
                "pmid": {"type": "keyword"},
                "pmc_id": {"type": "keyword"},
                "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "vernacular_title": {"type": "text"},
                "abstract": {"type": "text"},
                "content": {"type": "text"},
                "url": {"type": "keyword"},
                "pmc_url": {"type": "keyword"},
                "doi": {"type": "keyword"},
                "content_type": {"type": "keyword"},
                "published_date": {"type": "date"},
                "electronic_date": {"type": "date"},
                "print_date": {"type": "date"},
                "received_date": {"type": "date"},
                "accepted_date": {"type": "date"},
                "revised_date": {"type": "date"},
                "pubmed_date": {"type": "date"},
                "ml_score": {"type": "float"},
                "ai_confidence": {"type": "float"},
                "final_score": {"type": "float"},
                "quality_score": {"type": "float"},
                "gpt_score": {"type": "float"},
                "combined_score": {"type": "float"},
                "approval_status": {"type": "keyword"},
                "categories": {"type": "keyword"},
                "predicted_categories": {"type": "keyword"},
                "ohdsi_categories": {"type": "keyword"},
                "keywords": {"type": "keyword"},
                "mesh_terms": {"type": "keyword"},
                "publication_types": {"type": "keyword"},
                "journal": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "year": {"type": "integer"},
                "volume": {"type": "keyword"},
                "issue": {"type": "keyword"},
                "pages": {"type": "keyword"},
                "language": {"type": "keyword"},
                "has_funding": {"type": "boolean"},
                "has_pmc_full_text": {"type": "boolean"},
                "reference_count": {"type": "integer"},
                "author_count": {"type": "integer"},
                "medline_date": {"type": "date"},
                "medline_status": {"type": "keyword"},
                "indexing_method": {"type": "keyword"},
                "chemicals": {"type": "keyword"},
                "grants": {"type": "object", "enabled": False},
                "classification_factors": {"type": "object", "enabled": False},
                "abstract_sections": {"type": "object", "enabled": False},
                "journal_info": {"type": "object", "enabled": False},
                "ai_summary": {"type": "text"},
                "gpt_reasoning": {"type": "text"},
                "authors": {
                    "type": "nested",
                    "properties": {
                        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "email": {"type": "keyword"},
                        "affiliation": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}}
                    }
                },
                # Properly mapped citations structure
                "citations": {
                    "properties": {
                        "cited_by_count": {"type": "integer"},
                        "references_count": {"type": "integer"},
                        "cited_by_ids": {"type": "keyword"},  # Array of IDs, not dense_vector
                        "reference_ids": {"type": "keyword"}  # Array of IDs, not dense_vector
                    }
                },
                "references": {"type": "keyword"},  # Keep for backward compatibility
                "cited_by": {"type": "keyword"},  # Keep for backward compatibility
                "view_count": {"type": "integer"},
                "bookmark_count": {"type": "integer"},
                "suggest": {"type": "completion"},
                "embeddings": {"type": "dense_vector", "dims": 768, "index": True, "similarity": "cosine"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"}
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "ohdsi_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "stop", "snowball"]
                    }
                }
            }
        }
    }
    
    # review_queue index mapping
    review_mapping = {
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "source": {"type": "keyword"},
                "pmid": {"type": "keyword"},
                "pmc_id": {"type": "keyword"},
                "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "vernacular_title": {"type": "text"},
                "abstract": {"type": "text"},
                "content": {"type": "text"},
                "url": {"type": "keyword"},
                "pmc_url": {"type": "keyword"},
                "doi": {"type": "keyword"},
                "content_type": {"type": "keyword"},
                "published_date": {"type": "date"},
                "electronic_date": {"type": "date"},
                "print_date": {"type": "date"},
                "received_date": {"type": "date"},
                "accepted_date": {"type": "date"},
                "revised_date": {"type": "date"},
                "pubmed_date": {"type": "date"},
                "medline_date": {"type": "date"},
                "submitted_date": {"type": "date"},
                "ml_score": {"type": "float"},
                "gpt_score": {"type": "float"},
                "ai_confidence": {"type": "float"},
                "combined_score": {"type": "float"},
                "final_score": {"type": "float"},
                "quality_score": {"type": "float"},
                "approval_status": {"type": "keyword"},
                "predicted_categories": {"type": "keyword"},
                "ohdsi_categories": {"type": "keyword"},
                "categories": {"type": "keyword"},
                "keywords": {"type": "keyword"},
                "mesh_terms": {"type": "keyword"},
                "publication_types": {"type": "keyword"},
                "journal": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "year": {"type": "integer"},
                "volume": {"type": "keyword"},
                "issue": {"type": "keyword"},
                "pages": {"type": "keyword"},
                "language": {"type": "keyword"},
                "has_funding": {"type": "boolean"},
                "has_pmc_full_text": {"type": "boolean"},
                "reference_count": {"type": "integer"},
                "author_count": {"type": "integer"},
                "authors": {
                    "type": "nested",
                    "properties": {
                        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "email": {"type": "keyword"},
                        "affiliation": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}}
                    }
                },
                "chemicals": {"type": "keyword"},
                "grants": {"type": "object", "enabled": False},
                "abstract_sections": {"type": "object", "enabled": False},
                "journal_info": {"type": "object", "enabled": False},
                "classification_factors": {"type": "object", "enabled": False},
                "medline_status": {"type": "keyword"},
                "indexing_method": {"type": "keyword"},
                "status": {"type": "keyword"},
                "reviewer_id": {"type": "keyword"},
                "review_date": {"type": "date"},
                "review_notes": {"type": "text"},
                "priority": {"type": "integer"},
                "priority_level": {"type": "keyword"},
                "rejection_reason": {"type": "keyword"},
                "gpt_reasoning": {"type": "text"},
                "ai_summary": {"type": "text"},
                "references": {"type": "keyword"},
                "cited_by": {"type": "keyword"},
                # Properly mapped citations structure
                "citations": {
                    "properties": {
                        "cited_by_count": {"type": "integer"},
                        "references_count": {"type": "integer"},
                        "cited_by_ids": {"type": "keyword"},
                        "reference_ids": {"type": "keyword"}
                    }
                }
            }
        }
    }
    
    # user_activity index mapping
    activity_mapping = {
        "mappings": {
            "properties": {
                "user_id": {"type": "keyword"},
                "action": {"type": "keyword"},
                "content_id": {"type": "keyword"},
                "query": {"type": "text"},
                "filters": {"type": "object"},
                "timestamp": {"type": "date"},
                "session_id": {"type": "keyword"},
                "ip_address": {"type": "ip"}
            }
        }
    }
    
    # Create indices if they don't exist
    indices = [
        (settings.content_index, content_mapping),
        (settings.review_index, review_mapping),
        (settings.activity_index, activity_mapping)
    ]
    
    for index_name, mapping in indices:
        if not es_client.indices.exists(index=index_name):
            es_client.indices.create(index=index_name, body=mapping)
            logger.info(f"Created index: {index_name}")
        else:
            logger.debug(f"Index already exists: {index_name}")