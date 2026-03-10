from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json

from ...database import get_db, redis_client
from ...models import User, UserPreferences
from ...schemas import UserResponse, UserPreferencesUpdate
from ...api.routes.auth import get_current_user

router = APIRouter()

@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return UserResponse.model_validate(current_user)

@router.put("/profile")
async def update_profile(
    full_name: str = None,
    organization: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    if full_name:
        current_user.full_name = full_name
    if organization:
        current_user.organization = organization
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse.model_validate(current_user)

@router.get("/preferences")
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user preferences"""
    prefs = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    if not prefs:
        # Create default preferences
        prefs = UserPreferences(user_id=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    
    return {
        "preferences": prefs.preferences or {},
        "saved_searches": prefs.saved_searches or [],
        "bookmarks": prefs.bookmarks or []
    }

@router.put("/preferences")
async def update_preferences(
    updates: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user preferences"""
    prefs = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    if not prefs:
        prefs = UserPreferences(user_id=current_user.id)
        db.add(prefs)
    
    if updates.preferences is not None:
        prefs.preferences = updates.preferences
    if updates.saved_searches is not None:
        prefs.saved_searches = updates.saved_searches
    if updates.bookmarks is not None:
        prefs.bookmarks = updates.bookmarks
    
    db.commit()
    db.refresh(prefs)
    
    return {
        "message": "Preferences updated successfully",
        "preferences": prefs.preferences,
        "saved_searches": prefs.saved_searches,
        "bookmarks": prefs.bookmarks
    }

@router.post("/bookmark/{content_id}")
async def add_bookmark(
    content_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a bookmark"""
    prefs = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    if not prefs:
        prefs = UserPreferences(user_id=current_user.id, bookmarks=[])
        db.add(prefs)
    
    bookmarks = prefs.bookmarks or []
    if content_id not in bookmarks:
        bookmarks.append(content_id)
        prefs.bookmarks = bookmarks
        db.commit()
    
    # Also update bookmark count in Elasticsearch
    # This would be done via a service in production
    
    return {"message": "Bookmark added", "content_id": content_id}

@router.delete("/bookmark/{content_id}")
async def remove_bookmark(
    content_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a bookmark"""
    prefs = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    if prefs and prefs.bookmarks:
        bookmarks = prefs.bookmarks
        if content_id in bookmarks:
            bookmarks.remove(content_id)
            prefs.bookmarks = bookmarks
            db.commit()
    
    return {"message": "Bookmark removed", "content_id": content_id}

@router.post("/save-search")
async def save_search(
    name: str,
    query: str,
    filters: dict = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save a search query"""
    prefs = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    if not prefs:
        prefs = UserPreferences(user_id=current_user.id, saved_searches=[])
        db.add(prefs)
    
    saved_searches = prefs.saved_searches or []
    saved_searches.append({
        "name": name,
        "query": query,
        "filters": filters or {}
    })
    prefs.saved_searches = saved_searches
    db.commit()
    
    return {"message": "Search saved", "name": name}