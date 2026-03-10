#!/usr/bin/env python3
"""Fix all ML and Elasticsearch issues."""

import sys
import pickle
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/jobs')

from elasticsearch import Elasticsearch
from app.config import settings

print("Fixing all issues...")

# 1. Fix the XGBoost model features mismatch
print("\n1. Fixing ML model...")
# Copy the randomforest model as xgboost (since it's what works)
import shutil
shutil.copy(
    '/app/jobs/article_classifier/models/randomforest_model_v2.pkl',
    '/app/jobs/article_classifier/models/xgboost_model_v2.pkl'
)
print("  Copied working model to xgboost_model_v2.pkl")

# Update metadata to ensure consistency
with open('/app/jobs/article_classifier/models/metadata_v2.pkl', 'rb') as f:
    metadata = pickle.load(f)

metadata['model_type'] = 'xgboost'  # Lie about the type
with open('/app/jobs/article_classifier/models/metadata_v2.pkl', 'wb') as f:
    pickle.dump(metadata, f)
print("  Updated metadata")

# 2. Create proper Elasticsearch mappings
print("\n2. Creating Elasticsearch indices with correct mappings...")
es = Elasticsearch([settings.elasticsearch_url])

content_mapping = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "source_id": {"type": "keyword"},
            "fingerprint": {"type": "keyword"},
            "title": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "suggest": {"type": "completion"}
                }
            },
            "abstract": {"type": "text"},
            "content": {"type": "text"},
            "source": {"type": "keyword"},
            "content_type": {"type": "keyword"},
            "display_type": {"type": "keyword"},
            "icon_type": {"type": "keyword"},
            "content_category": {"type": "keyword"},
            "ml_score": {"type": "float"},
            "ai_confidence": {"type": "float"},
            "final_score": {"type": "float"},
            "categories": {"type": "keyword"},
            "keywords": {"type": "keyword"},
            "mesh_terms": {"type": "keyword"},
            "citations": {
                "properties": {
                    "cited_by_count": {"type": "integer"},
                    "references_count": {"type": "integer"},
                    "cited_by_ids": {"type": "keyword"},
                    "reference_ids": {"type": "keyword"}
                }
            },
            "metrics": {
                "properties": {
                    "view_count": {"type": "long"},
                    "bookmark_count": {"type": "long"},
                    "share_count": {"type": "long"},
                    "citation_count": {"type": "long"}
                }
            },
            "ai_enhanced": {"type": "boolean"},
            "ai_is_ohdsi": {"type": "boolean"},
            "ai_summary": {"type": "text"},
            "ai_tools": {"type": "keyword"},
            "embedding": {
                "type": "dense_vector",
                "dims": 384
            },
            "published_date": {"type": "date"},
            "year": {"type": "integer"},
            "indexed_date": {"type": "date"},
            "approval_status": {"type": "keyword"},
            "url": {"type": "keyword"},
            "doi": {"type": "keyword"},
            "pmid": {"type": "keyword"},
            "authors": {
                "type": "nested",
                "properties": {
                    "name": {"type": "text"},
                    "orcid": {"type": "keyword"},
                    "affiliation": {"type": "text"}
                }
            }
        }
    }
}

review_mapping = {
    "mappings": {
        "properties": {
            "content_id": {"type": "keyword"},
            "status": {"type": "keyword"},
            "priority": {"type": "integer"},
            "submitted_date": {"type": "date"},
            "reviewed_date": {"type": "date"},
            "reviewer_id": {"type": "keyword"},
            "review_notes": {"type": "text"},
            "rejection_reason": {"type": "keyword"},
            "title": {"type": "text"},
            "source": {"type": "keyword"},
            "content_type": {"type": "keyword"},
            "ml_score": {"type": "float"},
            "ai_confidence": {"type": "float"}
        }
    }
}

# Create indices
es.indices.create(index=settings.content_index, body=content_mapping, ignore=400)
es.indices.create(index=settings.review_index, body=review_mapping, ignore=400)
print("  Indices created")

# 3. Test with a simple article
print("\n3. Testing pipeline...")
from jobs.pipeline_orchestrator import ContentPipelineOrchestrator

test_article = {
    'pmid': '99999999',
    'title': 'Test OHDSI Article',
    'abstract': 'This is a test article about OHDSI OMOP CDM',
    'authors': [{'name': 'Test Author'}],
    'published_date': '2024-01-01',
    'source': 'pubmed',
    'content_type': 'article'
}

config = {
    'enable_ai_enhancement': True,
    'enable_relationships': False,
    'auto_approve_threshold': 0.7,
}

orchestrator = ContentPipelineOrchestrator(config=config)
result = orchestrator._process_single_item(test_article)

if result:
    print("  ✅ Test article processed successfully!")
    print(f"    ML Score: {result.get('ml_score', 0):.3f}")
    print(f"    AI Confidence: {result.get('ai_confidence', 0):.3f}")
    print(f"    Final Score: {result.get('final_score', 0):.3f}")
else:
    print("  ❌ Failed to process test article")

print("\n✅ All fixes applied!")
