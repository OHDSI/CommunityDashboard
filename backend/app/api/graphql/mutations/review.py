"""
Review mutation resolvers.

Handles approve_content, reject_content, move_to_pending,
change_content_status, bookmark, and save_search mutations.
"""
import logging
from datetime import datetime
from typing import Optional, List
from strawberry.types import Info

from ..helpers import require_reviewer
from ..services import review_service
from ....config import settings
from ....database import es_client

logger = logging.getLogger(__name__)


async def resolve_approve_content(
    info: Info,
    id: str,
    categories: List[str]
) -> bool:
    """Approve content (requires reviewer role)"""
    reviewer = require_reviewer(info)
    success = await review_service.approve_content(
        item_id=id,
        categories=categories,
        reviewer_id=str(reviewer.id),
        notes=None
    )
    return success


async def resolve_reject_content(
    info: Info,
    id: str,
    reason: str
) -> bool:
    """Reject content (requires reviewer role)"""
    reviewer = require_reviewer(info)
    success = await review_service.reject_content(
        item_id=id,
        reason=reason,
        reviewer_id=str(reviewer.id)
    )
    return success


async def resolve_move_to_pending(
    info: Info,
    id: str,
    notes: Optional[str] = None
) -> bool:
    """Move an approved or rejected item back to pending status"""
    reviewer = require_reviewer(info)
    success = await review_service.move_to_pending(
        item_id=id,
        reviewer_id=str(reviewer.id),
        notes=notes
    )
    return success


async def resolve_change_content_status(
    info: Info,
    id: str,
    new_status: str,
    categories: Optional[List[str]] = None
) -> bool:
    """Change content status (approved -> pending for re-review)"""
    reviewer = require_reviewer(info)
    try:
        if new_status == "pending":
            # Move from main content index back to review queue
            item_response = es_client.get(index=settings.content_index, id=id)
            item = item_response["_source"]

            # Add to review queue
            review_doc = {
                "id": id,
                "title": item["title"],
                "abstract": item.get("abstract"),
                "url": item.get("url"),
                "content_type": item["content_type"],
                "authors": item.get("authors", []),
                "submitted_date": datetime.now().isoformat(),
                "ml_score": item.get("ml_score", 0),
                "ai_confidence": item.get("ai_confidence", item.get("gpt_score", 0)),
                "final_score": item.get("final_score", item.get("combined_score", item.get("ml_score", 0))),
                "categories": categories or item.get("categories", item.get("ohdsi_categories", [])),
                "status": "pending",
                "priority": 5,
                "journal": item.get("journal"),
                "year": item.get("year"),
                "doi": item.get("doi")
            }

            es_client.index(index=settings.review_index, id=id, body=review_doc)

            # Remove from content index
            es_client.delete(index=settings.content_index, id=id)

            return True
        elif new_status == "approved" and categories:
            # Re-approve with new categories
            success = await review_service.approve_content(
                item_id=id,
                categories=categories,
                reviewer_id=str(reviewer.id),
                notes="Status changed"
            )
            return success
        else:
            return False
    except Exception as e:
        logger.error(f"Failed to change content status: {e}")
        return False


def resolve_bookmark(info: Info, content_id: str) -> bool:
    """Bookmark content"""
    # Note: In production, implement proper auth check here
    return True  # Placeholder


def resolve_save_search(info: Info, query: str, name: str) -> bool:
    """Save search query"""
    # Note: In production, implement proper auth check here
    return True  # Placeholder
