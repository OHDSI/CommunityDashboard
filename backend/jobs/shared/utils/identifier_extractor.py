"""
Shared identifier extraction utility.

Extracts PMIDs, DOIs, and URLs from content dictionaries.
Used by both the Deduplicator and ContentNormalizer.
"""

import re
from typing import Dict, Any, Set


def extract_identifiers(content: Dict[str, Any]) -> Dict[str, Set[str]]:
    """
    Extract various identifiers (PMIDs, DOIs, URLs) from content.

    Checks both direct fields (pmid, doi, url) and scans text fields
    (abstract, content, description, transcript) for embedded identifiers.

    Args:
        content: Content dictionary to extract identifiers from.

    Returns:
        Dictionary with 'pmids', 'dois', and 'urls' sets.
    """
    identifiers: Dict[str, Set[str]] = {
        'pmids': set(),
        'dois': set(),
        'urls': set(),
    }

    # Direct fields
    if content.get('pmid'):
        identifiers['pmids'].add(str(content['pmid']))
    if content.get('doi'):
        identifiers['dois'].add(content['doi'])
    if content.get('url'):
        identifiers['urls'].add(content['url'])

    # Extract from text fields
    text_fields = ['abstract', 'content', 'description', 'transcript']
    for field in text_fields:
        if content.get(field):
            text = str(content[field])

            # Find PMIDs
            pmid_matches = re.findall(r'PMID:?\s*(\d+)', text, re.IGNORECASE)
            identifiers['pmids'].update(pmid_matches)

            # Find DOIs
            doi_matches = re.findall(r'10\.\d{4,}/[-._;()/:\w]+', text)
            identifiers['dois'].update(doi_matches)

            # Find URLs
            url_matches = re.findall(
                r'https?://[^\s<>"{}|\\^`\[\]]+',
                text
            )
            identifiers['urls'].update(url_matches)

    return identifiers
