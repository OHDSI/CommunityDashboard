#!/usr/bin/env python3
"""Search for articles by PMID number (not ID)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import es_client
from app.config import settings

print("=" * 80)
print("SEARCHING FOR ARTICLES BY PMID NUMBER")
print("=" * 80)

pmids = ['33411620', '33554609', '33775125']

for pmid in pmids:
    print(f"\n{'=' * 80}")
    print(f"SEARCHING FOR PMID: {pmid}")
    print('=' * 80)

    # Search review queue
    print("\n1. Searching Review Queue:")
    query = {
        "query": {
            "term": {"pmid": pmid}
        },
        "size": 5,
        "_source": ["title", "abstract", "content", "pmid", "status", "source"]
    }

    try:
        response = es_client.search(index=settings.review_index, body=query)
        hits = response['hits']['hits']

        if hits:
            for hit in hits:
                doc_id = hit['_id']
                doc = hit['_source']

                print(f"  ✓ Found in review queue")
                print(f"    Document ID: {doc_id}")
                print(f"    Status: {doc.get('status')}")
                print(f"    Source: {doc.get('source', 'MISSING')}")
                print(f"    Title: {doc.get('title', 'N/A')[:70]}...")

                abstract = doc.get('abstract', '')
                content = doc.get('content', '')

                print(f"\n    Abstract field:")
                if abstract:
                    print(f"      Present: {len(abstract)} characters")
                    if abstract == "[Figure: see text]":
                        print(f"      ⚠️ Contains only '[Figure: see text]' - no real abstract")
                    else:
                        print(f"      Preview: {abstract[:150]}...")
                else:
                    print(f"      ❌ MISSING or EMPTY")

                print(f"\n    Content field:")
                if content:
                    print(f"      Present: {len(content)} characters")
                    if content == "[Figure: see text]":
                        print(f"      ⚠️ Contains only '[Figure: see text]' - no real content")
                    else:
                        print(f"      Preview: {content[:150]}...")
                else:
                    print(f"      ❌ MISSING or EMPTY")
        else:
            print(f"  ✗ Not found in review queue")

    except Exception as e:
        print(f"  Error searching review queue: {e}")

    # Search content index
    print("\n2. Searching Content Index:")
    try:
        response = es_client.search(index=settings.content_index, body=query)
        hits = response['hits']['hits']

        if hits:
            for hit in hits:
                doc_id = hit['_id']
                doc = hit['_source']

                print(f"  ✓ Found in content index")
                print(f"    Document ID: {doc_id}")
                print(f"    Status: {doc.get('approval_status')}")
                print(f"    Source: {doc.get('source', 'MISSING')}")

                abstract = doc.get('abstract', '')
                content = doc.get('content', '')

                print(f"\n    Abstract field:")
                if abstract:
                    print(f"      Present: {len(abstract)} characters")
                    if abstract == "[Figure: see text]":
                        print(f"      ⚠️ Contains only '[Figure: see text]' - no real abstract")
                    else:
                        print(f"      Preview: {abstract[:150]}...")
                else:
                    print(f"      ❌ MISSING or EMPTY")

                print(f"\n    Content field:")
                if content:
                    print(f"      Present: {len(content)} characters")
                    if content == "[Figure: see text]":
                        print(f"      ⚠️ Contains only '[Figure: see text]' - no real content")
                    else:
                        print(f"      Preview: {content[:150]}...")
                else:
                    print(f"      ❌ MISSING or EMPTY")
        else:
            print(f"  ✗ Not found in content index")

    except Exception as e:
        print(f"  Error searching content index: {e}")

print("\n" + "=" * 80)
print("\nSUMMARY: The issue is likely that PubMed provides '[Figure: see text]'")
print("instead of actual abstracts for some articles (especially those with")
print("graphical abstracts or infographics). This is PubMed's data, not a bug.")
print("=" * 80)
