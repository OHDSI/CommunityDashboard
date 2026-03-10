#!/usr/bin/env python3
"""
Complete database initialization for OHDSI Dashboard.
This script sets up both PostgreSQL and Elasticsearch with proper mappings.

Usage:
    docker-compose exec backend python /app/scripts/initialize_database.py
    
Options:
    --force: Drop existing indices and tables before creating
"""

import sys
import os
import argparse
import asyncio
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from elasticsearch import Elasticsearch
from app.database import engine, Base, es_client
from app.config import settings
from app.models import User

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_elasticsearch_mapping():
    """
    Get the optimized Elasticsearch mapping for content indices.
    Simplified structure with reduced redundancy.
    """
    return {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "ohdsi_analyzer": {
                        "type": "standard",
                        "stopwords": "_english_"
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                # Core identification fields
                "id": {"type": "keyword"},
                "source_id": {"type": "keyword"},  # Original ID from source (PMID, video_id, etc.)
                "fingerprint": {"type": "keyword"},  # For deduplication
                
                # Text content fields
                "title": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"},
                        "suggest": {"type": "completion"}
                    }
                },
                "abstract": {"type": "text"},
                "content": {"type": "text"},
                
                # Content classification
                "source": {"type": "keyword"},  # pubmed, youtube, github, discourse, wiki
                "content_type": {"type": "keyword"},  # article, video, repository, discussion, documentation
                
                # URLs and identifiers
                "url": {"type": "keyword"},
                "doi": {"type": "keyword"},
                
                # Authors and contributors
                "authors": {
                    "type": "nested",
                    "properties": {
                        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "email": {"type": "keyword"},
                        "affiliation": {"type": "text"},
                        "orcid": {"type": "keyword"}
                    }
                },
                
                # Dates
                "published_date": {"type": "date"},
                "year": {"type": "integer"},
                "indexed_date": {"type": "date"},
                
                # Scoring (consolidated)
                "ml_score": {"type": "float"},  # ML model score
                "ai_confidence": {"type": "float"},  # AI assessment confidence
                "final_score": {"type": "float"},  # Combined final score for routing
                
                # Categories and keywords (consolidated)
                "categories": {"type": "keyword"},  # Assigned categories
                "keywords": {"type": "keyword"},  # Searchable terms
                "mesh_terms": {"type": "keyword"},  # Medical subject headings (for articles)
                
                # AI Enhancement fields
                "ai_enhanced": {"type": "boolean"},
                "ai_is_ohdsi": {"type": "boolean"},
                "ai_summary": {"type": "text"},
                "ai_tools": {"type": "keyword"},  # OHDSI tools mentioned
                
                # Embeddings for semantic search
                "embedding": {
                    "type": "dense_vector",
                    "dims": 384,  # text-embedding-3-small dimensions
                    "index": True,
                    "similarity": "cosine"
                },
                
                # Simplified citations structure
                "citations": {
                    "type": "object",
                    "properties": {
                        "cited_by_count": {"type": "integer"},
                        "references_count": {"type": "integer"},
                        "cited_by_ids": {"type": "keyword"},  # Array of IDs
                        "reference_ids": {"type": "keyword"}  # Array of IDs
                    }
                },
                
                # Relationships to other content
                "relationships": {
                    "type": "object",
                    "properties": {
                        "related_content": {"type": "keyword"},  # Array of related content IDs
                        "relationship_types": {"type": "keyword"}  # Types of relationships
                    }
                },
                
                # Approval status
                "approval_status": {"type": "keyword"},  # approved, pending, rejected
                
                # Unified metrics object
                "metrics": {
                    "type": "object",
                    "properties": {
                        "view_count": {"type": "long"},
                        "bookmark_count": {"type": "long"},
                        "share_count": {"type": "long"},
                        "citation_count": {"type": "long"}
                    }
                },
                
                # Source-specific metadata (dynamic fields for flexibility)
                # These are optional and only populated when relevant
                
                # Article-specific
                "journal": {"type": "text"},
                "pmid": {"type": "keyword"},
                
                # Video-specific
                "channel_name": {"type": "text"},
                "duration": {"type": "integer"},  # in seconds
                "thumbnail_url": {"type": "keyword"},
                
                # Repository-specific
                "owner": {"type": "keyword"},
                "stars_count": {"type": "integer"},
                "language": {"type": "keyword"},
                "topics": {"type": "keyword"},
                
                # Discussion-specific
                "reply_count": {"type": "integer"},
                "solved": {"type": "boolean"},
                
                # Documentation-specific
                "doc_type": {"type": "keyword"},
                "last_modified": {"type": "date"}
            }
        }
    }


def get_review_queue_mapping():
    """
    Get the mapping specifically for the review queue index.
    Separated from content index for clarity.
    """
    return {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": {
                # Reference to content
                "content_id": {"type": "keyword"},
                
                # Review-specific fields
                "status": {"type": "keyword"},  # pending, approved, rejected
                "priority": {"type": "integer"},  # 0-10 priority score
                "submitted_date": {"type": "date"},
                "reviewed_date": {"type": "date"},
                "reviewer_id": {"type": "keyword"},
                "review_notes": {"type": "text"},
                "rejection_reason": {"type": "keyword"},
                
                # Cached content fields for display
                "title": {"type": "text"},
                "source": {"type": "keyword"},
                "content_type": {"type": "keyword"},
                "ml_score": {"type": "float"},
                "ai_confidence": {"type": "float"}
            }
        }
    }


def setup_postgresql(force=False):
    """Create PostgreSQL tables."""
    logger.info("Setting up PostgreSQL...")
    
    try:
        if force:
            logger.info("Dropping existing tables...")
            Base.metadata.drop_all(bind=engine)
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ PostgreSQL tables created successfully")
        
        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            logger.info(f"Created tables: {', '.join(tables)}")
            
        # Create default admin user
        create_default_users()
        
    except Exception as e:
        logger.error(f"Error setting up PostgreSQL: {e}")
        raise


def create_default_users():
    """Create default users for the application."""
    from sqlalchemy.orm import Session
    from app.utils.auth import AuthService
    
    logger.info("Creating default users...")
    
    with Session(engine) as session:
        # Check if admin already exists
        existing_admin = session.query(User).filter(User.email == "admin@ohdsi.org").first()
        if not existing_admin:
            admin = User(
                email="admin@ohdsi.org",
                password_hash=AuthService.get_password_hash(os.getenv("ADMIN_PASSWORD", "changeme")),
                full_name="OHDSI Administrator",
                role="admin",
                is_active=True,
                is_superuser=True
            )
            session.add(admin)
            logger.info("✅ Created admin user (admin@ohdsi.org)")

        # Check if reviewer already exists
        existing_reviewer = session.query(User).filter(User.email == "reviewer@ohdsi.org").first()
        if not existing_reviewer:
            reviewer = User(
                email="reviewer@ohdsi.org",
                password_hash=AuthService.get_password_hash(os.getenv("REVIEWER_PASSWORD", "changeme")),
                full_name="Content Reviewer",
                role="reviewer",
                is_active=True,
                is_superuser=False
            )
            session.add(reviewer)
            logger.info("✅ Created reviewer user (reviewer@ohdsi.org)")
        
        session.commit()


def setup_elasticsearch(force=False):
    """Create Elasticsearch indices with proper mappings."""
    logger.info("Setting up Elasticsearch...")
    
    try:
        # Define indices with their specific mappings
        indices = {
            settings.content_index: ("Main content index", get_elasticsearch_mapping()),
            settings.review_index: ("Review queue index", get_review_queue_mapping())
        }
        
        for index_name, (description, mapping) in indices.items():
            logger.info(f"Setting up {description}: {index_name}")
            
            # Check if index exists
            if es_client.indices.exists(index=index_name):
                if force:
                    logger.info(f"  Deleting existing index {index_name}...")
                    es_client.indices.delete(index=index_name)
                else:
                    logger.warning(f"  Index {index_name} already exists. Use --force to recreate.")
                    continue
            
            # Create index with its specific mapping
            es_client.indices.create(index=index_name, body=mapping)
            logger.info(f"  ✅ Created {index_name}")
        
        # Create aliases for backward compatibility
        logger.info("Setting up aliases...")
        
        # Content alias
        if not es_client.indices.exists_alias(name="ohdsi_content"):
            es_client.indices.put_alias(index=settings.content_index, name="ohdsi_content")
            logger.info("  ✅ Created alias: ohdsi_content -> " + settings.content_index)
        
        # Review alias
        if not es_client.indices.exists_alias(name="ohdsi_review"):
            es_client.indices.put_alias(index=settings.review_index, name="ohdsi_review")
            logger.info("  ✅ Created alias: ohdsi_review -> " + settings.review_index)
        
        # Verify indices
        verify_elasticsearch_setup()
        
    except Exception as e:
        logger.error(f"Error setting up Elasticsearch: {e}")
        raise


def verify_elasticsearch_setup():
    """Verify Elasticsearch indices are properly configured."""
    logger.info("\nVerifying Elasticsearch setup...")
    
    # Check indices
    indices_info = es_client.cat.indices(format='json')
    for index in indices_info:
        if 'ohdsi' in index['index']:
            logger.info(f"  Index: {index['index']}")
            logger.info(f"    Documents: {index['docs.count']}")
            logger.info(f"    Size: {index['store.size']}")
            logger.info(f"    Status: {index['health']}")
    
    # Check mappings for key fields
    for index_name in [settings.content_index, settings.review_index]:
        if es_client.indices.exists(index=index_name):
            mapping = es_client.indices.get_mapping(index=index_name)
            properties = mapping[index_name]['mappings'].get('properties', {})
            
            if index_name == settings.content_index:
                # Verify essential content fields
                essential_fields = ['id', 'title', 'source', 'content_type', 'ml_score', 
                                  'ai_confidence', 'final_score', 'categories', 'keywords']
                missing = [f for f in essential_fields if f not in properties]
                if missing:
                    logger.warning(f"  ⚠️ {index_name} missing fields: {missing}")
                else:
                    logger.info(f"  ✅ {index_name} has all essential fields")
                
                # Verify simplified citations
                if 'citations' in properties:
                    citations = properties['citations']
                    if citations.get('type') == 'object':
                        citation_props = citations.get('properties', {})
                        if 'cited_by_ids' in citation_props and 'reference_ids' in citation_props:
                            logger.info(f"  ✅ {index_name} has simplified citation structure")
                        else:
                            logger.warning(f"  ⚠️ {index_name} citations structure incomplete")
                
                # Verify metrics object
                if 'metrics' in properties:
                    metrics = properties['metrics']
                    if metrics.get('type') == 'object':
                        logger.info(f"  ✅ {index_name} has unified metrics object")
            
            elif index_name == settings.review_index:
                # Verify review-specific fields
                review_fields = ['content_id', 'status', 'priority', 'submitted_date']
                missing = [f for f in review_fields if f not in properties]
                if missing:
                    logger.warning(f"  ⚠️ {index_name} missing fields: {missing}")
                else:
                    logger.info(f"  ✅ {index_name} has all review fields")


def health_check():
    """Perform health checks on all services."""
    logger.info("\nPerforming health checks...")
    
    # PostgreSQL
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("  ✅ PostgreSQL is healthy")
    except Exception as e:
        logger.error(f"  ❌ PostgreSQL is not healthy: {e}")
        return False
    
    # Elasticsearch
    try:
        health = es_client.cluster.health()
        status = health['status']
        if status in ['green', 'yellow']:
            logger.info(f"  ✅ Elasticsearch is healthy (status: {status})")
        else:
            logger.warning(f"  ⚠️ Elasticsearch status: {status}")
    except Exception as e:
        logger.error(f"  ❌ Elasticsearch is not healthy: {e}")
        return False
    
    return True


def main():
    """Main initialization function."""
    parser = argparse.ArgumentParser(description='Initialize OHDSI Dashboard database')
    parser.add_argument('--force', action='store_true', 
                       help='Drop existing indices and tables before creating')
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("OHDSI DASHBOARD DATABASE INITIALIZATION")
    print("="*60)
    
    if args.force:
        print("\n⚠️  WARNING: Force mode enabled. This will DELETE all existing data!")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Initialization cancelled.")
            return
    
    try:
        # Setup PostgreSQL
        print("\n[1/3] Setting up PostgreSQL...")
        setup_postgresql(force=args.force)
        
        # Setup Elasticsearch
        print("\n[2/3] Setting up Elasticsearch...")
        setup_elasticsearch(force=args.force)
        
        # Health checks
        print("\n[3/3] Running health checks...")
        if health_check():
            print("\n" + "="*60)
            print("✅ DATABASE INITIALIZATION COMPLETE")
            print("="*60)
            print("\nYou can now run:")
            print("  - Ingest training data: docker-compose exec backend python /app/scripts/ingest_training_data.py")
            print("  - Ingest multimodal content: docker-compose exec backend python /app/scripts/ingest_multimodal_content.py")
        else:
            print("\n⚠️ Some health checks failed. Please review the logs above.")
            
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()