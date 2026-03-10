#!/usr/bin/env python3
"""Backfill embeddings for existing documents in Elasticsearch."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backfill_embeddings(batch_size=50):
    """Generate and add embeddings to all existing documents."""

    # Initialize - use environment variable or default to elasticsearch service
    es_host = os.getenv("ELASTICSEARCH_HOST", "elasticsearch")
    es_port = os.getenv("ELASTICSEARCH_PORT", "9200")
    es_url = f"http://{es_host}:{es_port}"

    es = Elasticsearch([es_url])
    encoder = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info(f"Initialized Elasticsearch ({es_url}) and SentenceTransformer")
    
    # Get total count
    count_response = es.count(index="ohdsi_content_v3")
    total = count_response["count"]
    logger.info(f"Found {total} documents to process")
    
    # Process in batches
    processed = 0
    updated = 0
    errors = 0
    
    # Scroll through all documents
    response = es.search(
        index="ohdsi_content_v3",
        scroll="5m",
        size=batch_size,
        body={
            "query": {"match_all": {}},
            "_source": ["title", "abstract"]
        }
    )
    
    scroll_id = response["_scroll_id"]
    hits = response["hits"]["hits"]
    
    with tqdm(total=total, desc="Processing documents") as pbar:
        while hits:
            batch_updates = []
            
            for hit in hits:
                try:
                    doc_id = hit["_id"]
                    source = hit["_source"]
                    
                    # Generate embedding
                    text = source.get("title", "")
                    if source.get("abstract"):
                        text += " " + source["abstract"][:500]
                    
                    if text.strip():
                        embedding = encoder.encode(text).tolist()
                        
                        # Update document
                        es.update(
                            index="ohdsi_content_v3",
                            id=doc_id,
                            body={"doc": {"embedding": embedding}},
                            refresh=False  # Don't refresh immediately for performance
                        )
                        updated += 1
                    
                    processed += 1
                    pbar.update(1)
                    
                except Exception as e:
                    logger.error(f"Error processing document {hit.get('_id')}: {e}")
                    errors += 1
            
            # Get next batch
            response = es.scroll(scroll_id=scroll_id, scroll="5m")
            scroll_id = response["_scroll_id"]
            hits = response["hits"]["hits"]
    
    # Clear scroll
    es.clear_scroll(scroll_id=scroll_id)
    
    # Refresh index
    logger.info("Refreshing index...")
    es.indices.refresh(index="ohdsi_content_v3")
    
    logger.info(f"Backfill complete: {processed} processed, {updated} updated, {errors} errors")
    return {"processed": processed, "updated": updated, "errors": errors}

if __name__ == "__main__":
    result = backfill_embeddings()
    print(f"\nResults: {result}")
