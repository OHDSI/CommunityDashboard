from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy.orm import Session
import logging

from ...database import es_client, get_db
from ...models import User, UserRole
from ...schemas import ReviewItem, ReviewAction, ReviewStats
from ...api.routes.auth import get_current_user
from ...services.review_service import ReviewService
from ...config import settings

router = APIRouter()
logger = logging.getLogger(__name__)
review_service = ReviewService(es_client)

def require_reviewer(current_user: User = Depends(get_current_user)) -> User:
    """Ensure user has reviewer role"""
    if current_user.role not in [UserRole.REVIEWER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewer access required"
        )
    return current_user

@router.get("/queue", response_model=List[ReviewItem])
async def get_review_queue(
    status: str = Query("pending", regex="^(pending|approved|rejected)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    reviewer: User = Depends(require_reviewer)
):
    """
    Get items in the review queue
    """
    try:
        items = review_service.get_queue(status, limit, offset)
        return items
    except Exception as e:
        logger.error(f"Failed to get review queue: {e}")
        raise HTTPException(status_code=500, detail="Failed to get review queue")

@router.get("/stats", response_model=ReviewStats)
async def get_review_stats(reviewer: User = Depends(require_reviewer)):
    """
    Get review queue statistics
    """
    try:
        stats = review_service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get review stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get review statistics")

@router.post("/{item_id}/approve")
async def approve_content(
    item_id: str,
    categories: List[str] = Query(...),
    notes: Optional[str] = None,
    reviewer: User = Depends(require_reviewer)
):
    """
    Approve content and move to main index
    """
    try:
        success = await review_service.approve_content(
            item_id=item_id,
            categories=categories,
            reviewer_id=str(reviewer.id),
            notes=notes
        )
        if not success:
            raise HTTPException(status_code=404, detail="Review item not found")
        return {"message": "Content approved successfully", "id": item_id}
    except Exception as e:
        logger.error(f"Failed to approve content: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve content")

@router.post("/{item_id}/reject")
async def reject_content(
    item_id: str,
    reason: str = Query(..., min_length=10),
    reviewer: User = Depends(require_reviewer)
):
    """
    Reject content with reason
    """
    try:
        success = await review_service.reject_content(
            item_id=item_id,
            reason=reason,
            reviewer_id=str(reviewer.id)
        )
        if not success:
            raise HTTPException(status_code=404, detail="Review item not found")
        return {"message": "Content rejected", "id": item_id}
    except Exception as e:
        logger.error(f"Failed to reject content: {e}")
        raise HTTPException(status_code=500, detail="Failed to reject content")

@router.post("/bulk-action")
async def bulk_review_action(
    item_ids: List[str],
    action: ReviewAction,
    reviewer: User = Depends(require_reviewer)
):
    """
    Perform bulk approve/reject actions
    """
    try:
        results = await review_service.bulk_action(
            item_ids=item_ids,
            action=action.action,
            categories=action.categories,
            reviewer_id=str(reviewer.id),
            notes=action.notes
        )
        return {
            "message": f"Bulk {action.action} completed",
            "processed": len(results["success"]),
            "failed": len(results["failed"]),
            "results": results
        }
    except Exception as e:
        logger.error(f"Failed to perform bulk action: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform bulk action")