#!/usr/bin/env python3
"""
Reindex Elasticsearch to add .keyword subfields for journal and channel_name.

This script:
1. Creates a new index with updated mapping (journal.keyword, channel_name.keyword)
2. Reindexes all data from old index to new index
3. Updates alias to point to new index
4. Optionally deletes old index

Usage:
    python scripts/reindex_with_keyword_fields.py --dry-run  # Preview changes
    python scripts/reindex_with_keyword_fields.py            # Execute reindex
"""

import argparse
import sys
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.helpers import reindex

# Configuration
OLD_INDEX = "ohdsi_content_v3"
NEW_INDEX = f"ohdsi_content_v4_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
ALIAS = "ohdsi_content"

def get_es_client():
    """Get Elasticsearch client."""
    return Elasticsearch(["http://elasticsearch:9200"], request_timeout=300)

def get_updated_mapping():
    """Get the mapping with keyword subfields added to journal and channel_name."""
    return {
        "mappings": {
            "dynamic": "false",
            "properties": {
                # Core fields
                "id": {"type": "keyword"},
                "title": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"},
                        "suggest": {
                            "type": "completion",
                            "analyzer": "simple",
                            "preserve_separators": True,
                            "preserve_position_increments": True,
                            "max_input_length": 50
                        }
                    }
                },
                "abstract": {"type": "text"},
                "content": {"type": "text"},
                "url": {"type": "keyword"},
                "doi": {"type": "keyword"},

                # Classification
                "source": {"type": "keyword"},
                "source_id": {"type": "keyword"},
                "content_type": {"type": "keyword"},
                "fingerprint": {"type": "keyword"},

                # Dates
                "published_date": {"type": "date"},
                "year": {"type": "integer"},
                "indexed_date": {"type": "date"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},

                # Scores
                "ml_score": {"type": "float"},
                "ai_confidence": {"type": "float"},
                "final_score": {"type": "float"},
                "combined_score": {"type": "float"},
                "gpt_score": {"type": "float"},
                "quality_score": {"type": "float"},
                "priority_score": {"type": "float"},
                "engagement_score": {"type": "float"},

                # Categories and keywords
                "categories": {"type": "keyword"},
                "keywords": {"type": "keyword"},
                "mesh_terms": {"type": "keyword"},
                "ohdsi_categories": {"type": "keyword"},
                "predicted_categories": {"type": "keyword"},
                "topics": {"type": "keyword"},

                # AI enhancement
                "ai_enhanced": {"type": "boolean"},
                "ai_is_ohdsi": {"type": "boolean"},
                "ai_summary": {"type": "text"},
                "ai_tools": {"type": "keyword"},
                "gpt_reasoning": {"type": "text"},

                # Approval workflow
                "approval_status": {"type": "keyword"},
                "approved_by": {"type": "keyword"},
                "approved_at": {"type": "date"},
                "review_notes": {"type": "text"},

                # Authors (nested)
                "authors": {
                    "type": "nested",
                    "properties": {
                        "name": {
                            "type": "text",
                            "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                            "fielddata": True
                        },
                        "affiliation": {
                            "type": "text",
                            "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
                        },
                        "email": {"type": "keyword"},
                        "orcid": {"type": "keyword"}
                    }
                },

                # Citations
                "citations": {
                    "properties": {
                        "cited_by_count": {"type": "long"},
                        "references_count": {"type": "long"},
                        "cited_by_ids": {"type": "keyword"},
                        "reference_ids": {"type": "keyword"}
                    }
                },

                # Metrics
                "view_count": {"type": "long"},
                "bookmark_count": {"type": "long"},
                "share_count": {"type": "long"},
                "citation_count": {"type": "long"},

                # Embeddings
                "embedding": {
                    "type": "dense_vector",
                    "dims": 384,
                    "index": True,
                    "similarity": "cosine"
                },

                # ===== FIXED FIELDS =====
                # Article-specific (FIX: added .keyword)
                "journal": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
                },
                "pmid": {"type": "keyword"},

                # Video-specific (FIX: added .keyword)
                "channel_name": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
                },
                "video_id": {"type": "keyword"},
                "duration": {"type": "integer"},
                "thumbnail_url": {"type": "keyword"},
                "transcript": {"type": "text"},

                # Repository-specific
                "repo_name": {"type": "keyword"},
                "owner": {"type": "keyword"},
                "stars_count": {"type": "integer"},
                "forks_count": {"type": "integer"},
                "language": {"type": "keyword"},
                "last_commit": {"type": "date"},

                # Discussion-specific
                "topic_id": {"type": "keyword"},
                "reply_count": {"type": "integer"},
                "solved": {"type": "boolean"},

                # Documentation-specific
                "doc_type": {"type": "keyword"},
                "last_modified": {"type": "date"},
                "section_count": {"type": "integer"},

                # Display metadata
                "display_type": {"type": "keyword"},
                "content_category": {"type": "keyword"},
                "icon_type": {"type": "keyword"},

                # Suggest
                "suggest": {
                    "type": "completion",
                    "analyzer": "simple",
                    "preserve_separators": True,
                    "preserve_position_increments": True,
                    "max_input_length": 50
                }
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 1,
            "refresh_interval": "1s"
        }
    }

def create_new_index(es, dry_run=False):
    """Create new index with updated mapping."""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Creating new index: {NEW_INDEX}")

    mapping = get_updated_mapping()

    if dry_run:
        print(f"Would create index with mapping:")
        print(f"  - journal: text + journal.keyword")
        print(f"  - channel_name: text + channel_name.keyword")
        return

    if es.indices.exists(index=NEW_INDEX):
        print(f"Index {NEW_INDEX} already exists. Deleting...")
        es.indices.delete(index=NEW_INDEX)

    es.indices.create(index=NEW_INDEX, body=mapping)
    print(f"✓ Created index: {NEW_INDEX}")

def reindex_data(es, dry_run=False):
    """Reindex data from old index to new index."""
    if dry_run:
        # Get document count
        count = es.count(index=OLD_INDEX)['count']
        print(f"\n[DRY RUN] Would reindex {count:,} documents from {OLD_INDEX} to {NEW_INDEX}")
        return

    print(f"\nReindexing data from {OLD_INDEX} to {NEW_INDEX}...")

    # Get document count
    count = es.count(index=OLD_INDEX)['count']
    print(f"Total documents to reindex: {count:,}")

    # Execute reindex
    result = es.reindex(
        body={
            "source": {"index": OLD_INDEX},
            "dest": {"index": NEW_INDEX}
        },
        wait_for_completion=True,
        request_timeout=3600
    )

    print(f"✓ Reindexed {result['total']} documents")
    print(f"  - Created: {result.get('created', 0)}")
    print(f"  - Updated: {result.get('updated', 0)}")
    print(f"  - Failures: {len(result.get('failures', []))}")

    if result.get('failures'):
        print("\n⚠️  Reindex had failures:")
        for failure in result['failures'][:5]:  # Show first 5
            print(f"  - {failure}")

def verify_reindex(es):
    """Verify the reindexed data."""
    print(f"\nVerifying reindex...")

    old_count = es.count(index=OLD_INDEX)['count']
    new_count = es.count(index=NEW_INDEX)['count']

    print(f"  Old index ({OLD_INDEX}): {old_count:,} documents")
    print(f"  New index ({NEW_INDEX}): {new_count:,} documents")

    if old_count == new_count:
        print("  ✓ Document counts match")
    else:
        print(f"  ⚠️  Count mismatch: {old_count - new_count} documents difference")
        return False

    # Test aggregations on new fields
    print("\nTesting new keyword fields...")

    # Test journal.keyword
    journal_agg = es.search(
        index=NEW_INDEX,
        body={
            "size": 0,
            "query": {"term": {"content_type": "article"}},
            "aggs": {
                "journals": {
                    "terms": {"field": "journal.keyword", "size": 5}
                }
            }
        }
    )

    journal_buckets = journal_agg['aggregations']['journals']['buckets']
    if journal_buckets:
        print(f"  ✓ journal.keyword works ({len(journal_buckets)} unique journals found)")
        for bucket in journal_buckets[:3]:
            print(f"    - {bucket['key']}: {bucket['doc_count']} articles")
    else:
        print("  ⚠️  journal.keyword returned no results")

    # Test channel_name.keyword
    channel_agg = es.search(
        index=NEW_INDEX,
        body={
            "size": 0,
            "query": {"term": {"content_type": "video"}},
            "aggs": {
                "channels": {
                    "terms": {"field": "channel_name.keyword", "size": 5}
                }
            }
        }
    )

    channel_buckets = channel_agg['aggregations']['channels']['buckets']
    if channel_buckets:
        print(f"  ✓ channel_name.keyword works ({len(channel_buckets)} unique channels found)")
        for bucket in channel_buckets[:3]:
            print(f"    - {bucket['key']}: {bucket['doc_count']} videos")
    else:
        print("  ⚠️  channel_name.keyword returned no results (may be no videos)")

    return True

def update_alias(es, dry_run=False):
    """Update alias to point to new index."""
    if dry_run:
        print(f"\n[DRY RUN] Would update alias '{ALIAS}' to point to {NEW_INDEX}")
        return

    print(f"\nUpdating alias '{ALIAS}' to point to {NEW_INDEX}...")

    # Remove old alias if exists
    if es.indices.exists_alias(name=ALIAS):
        old_indices = list(es.indices.get_alias(name=ALIAS).keys())
        print(f"  Removing alias from: {old_indices}")
        for old_index in old_indices:
            es.indices.delete_alias(index=old_index, name=ALIAS)

    # Add alias to new index
    es.indices.put_alias(index=NEW_INDEX, name=ALIAS)
    print(f"  ✓ Alias '{ALIAS}' now points to {NEW_INDEX}")

def cleanup_old_index(es, dry_run=False):
    """Optionally delete old index."""
    if dry_run:
        print(f"\n[DRY RUN] Would delete old index: {OLD_INDEX}")
        return

    response = input(f"\nDelete old index '{OLD_INDEX}'? (yes/no): ")
    if response.lower() == 'yes':
        es.indices.delete(index=OLD_INDEX)
        print(f"  ✓ Deleted old index: {OLD_INDEX}")
    else:
        print(f"  Keeping old index: {OLD_INDEX}")
        print(f"  You can delete it manually with: curl -X DELETE http://localhost:9200/{OLD_INDEX}")

def main():
    parser = argparse.ArgumentParser(description='Reindex Elasticsearch with keyword fields')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without executing')
    args = parser.parse_args()

    print("=" * 70)
    print("ELASTICSEARCH REINDEXING TOOL")
    print("Adding .keyword subfields to: journal, channel_name")
    print("=" * 70)

    try:
        es = get_es_client()

        # Check if old index exists
        if not es.indices.exists(index=OLD_INDEX):
            print(f"Error: Index '{OLD_INDEX}' does not exist")
            sys.exit(1)

        # Execute reindexing steps
        create_new_index(es, dry_run=args.dry_run)
        reindex_data(es, dry_run=args.dry_run)

        if not args.dry_run:
            if verify_reindex(es):
                update_alias(es, dry_run=args.dry_run)
                cleanup_old_index(es, dry_run=args.dry_run)

                print("\n" + "=" * 70)
                print("✓ REINDEXING COMPLETE")
                print("=" * 70)
                print(f"\nNew index: {NEW_INDEX}")
                print(f"Alias: {ALIAS} -> {NEW_INDEX}")
                print("\nYou can now run queries like:")
                print('  - "Show me articles by journal over time"')
                print('  - "Which journals publish the most OHDSI articles?"')
                print('  - "Top YouTube channels for OHDSI content"')
            else:
                print("\n⚠️  Verification failed. Please review errors above.")
                sys.exit(1)
        else:
            print("\n" + "=" * 70)
            print("[DRY RUN] No changes made. Remove --dry-run to execute.")
            print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
