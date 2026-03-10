"""
Shared OHDSI content relevance checking.

Provides a reusable function for determining whether text content
is related to OHDSI based on keyword matching.
"""

from typing import List, Optional

from .ohdsi_constants import OHDSI_KEYWORDS


def is_ohdsi_related(text: str, keywords: Optional[List[str]] = None,
                     threshold: int = 1) -> bool:
    """
    Check if text is OHDSI-related based on keyword matching.

    Args:
        text: The text to check (will be lowercased internally).
        keywords: Optional custom keyword list. Defaults to OHDSI_KEYWORDS.
        threshold: Minimum number of keyword matches required. Defaults to 1.

    Returns:
        True if the number of keyword matches meets or exceeds the threshold.
    """
    if not text:
        return False

    keywords = keywords or OHDSI_KEYWORDS
    text_lower = text.lower()

    match_count = 0
    for keyword in keywords:
        if keyword in text_lower:
            match_count += 1
            if match_count >= threshold:
                return True

    return False
