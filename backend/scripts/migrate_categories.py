#!/usr/bin/env python3
"""
Migrate category values in Elasticsearch from old 42-category system
to new 4-category system.

This script is idempotent — safe to run multiple times.

Usage:
    python scripts/migrate_categories.py [--dry-run]
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from elasticsearch import Elasticsearch, helpers
from config.ohdsi_categories import OLD_TO_NEW_CATEGORY_MAP, map_old_categories, category_system

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

ES_HOST = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
INDICES = ["ohdsi_content_v3", "ohdsi_review_queue_v3"]
CATEGORY_FIELDS = ["categories", "predicted_categories", "ohdsi_categories"]
BATCH_SIZE = 500


def migrate_index(es: Elasticsearch, index: str, dry_run: bool = False):
    """Migrate all documents in the given index."""
    if not es.indices.exists(index=index):
        logger.warning(f"Index {index} does not exist, skipping")
        return

    total = es.count(index=index)["count"]
    logger.info(f"Processing {total} documents in {index}")

    updated = 0
    skipped = 0
    actions = []
    new_names = set(category_system.get_all_category_names())

    for doc in helpers.scan(es, index=index, query={"query": {"match_all": {}}}, size=BATCH_SIZE):
        doc_id = doc["_id"]
        source = doc["_source"]
        changes = {}

        for field in CATEGORY_FIELDS:
            old_values = source.get(field, [])
            if not old_values or not isinstance(old_values, list):
                continue

            # Check if any values need mapping
            needs_mapping = any(v not in new_names for v in old_values)
            if not needs_mapping:
                continue

            new_values = map_old_categories(old_values)
            if new_values != sorted(old_values):
                changes[field] = new_values

        if changes:
            if dry_run:
                old_cats = source.get("categories", [])
                logger.info(f"  [DRY RUN] {doc_id}: {old_cats} -> {changes.get('categories', old_cats)}")
            else:
                actions.append({
                    "_op_type": "update",
                    "_index": index,
                    "_id": doc_id,
                    "doc": changes,
                })
            updated += 1
        else:
            skipped += 1

        # Flush batch
        if not dry_run and len(actions) >= BATCH_SIZE:
            helpers.bulk(es, actions, raise_on_error=False)
            logger.info(f"  Flushed {len(actions)} updates ({updated} updated, {skipped} skipped so far)")
            actions = []

    # Final flush
    if not dry_run and actions:
        helpers.bulk(es, actions, raise_on_error=False)

    logger.info(f"Completed {index}: {updated} updated, {skipped} already current (total {total})")


def main():
    parser = argparse.ArgumentParser(description="Migrate ES categories to 4-category system")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying them")
    args = parser.parse_args()

    es = Elasticsearch(ES_HOST)

    if not es.ping():
        logger.error(f"Cannot connect to Elasticsearch at {ES_HOST}")
        sys.exit(1)

    logger.info(f"Connected to Elasticsearch at {ES_HOST}")
    if args.dry_run:
        logger.info("DRY RUN mode — no changes will be made")

    for index in INDICES:
        migrate_index(es, index, dry_run=args.dry_run)

    logger.info("Migration complete")


if __name__ == "__main__":
    main()
