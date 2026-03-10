#!/usr/bin/env python3
"""Initialize default users for the OHDSI Community Intelligence Platform."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import engine, Base
from app.models import User, UserRole, UserPreferences
from app.utils.auth import auth_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default users configuration
# IMPORTANT: Change these passwords before deploying to production!
# Set ADMIN_PASSWORD, REVIEWER_PASSWORD etc. as environment variables.
DEFAULT_USERS = [
    {
        "email": os.getenv("ADMIN_EMAIL", "admin@ohdsi.org"),
        "password": os.getenv("ADMIN_PASSWORD", "changeme"),
        "full_name": "System Administrator",
        "organization": "OHDSI Community",
        "role": UserRole.ADMIN,
        "is_superuser": True
    },
    {
        "email": "reviewer@ohdsi.org",
        "password": os.getenv("REVIEWER_PASSWORD", "changeme"),
        "full_name": "Content Reviewer",
        "organization": "OHDSI Community",
        "role": UserRole.REVIEWER,
        "is_superuser": False
    },
    {
        "email": "researcher@ohdsi.org",
        "password": os.getenv("RESEARCHER_PASSWORD", "changeme"),
        "full_name": "Research User",
        "organization": "OHDSI Research",
        "role": UserRole.RESEARCHER,
        "is_superuser": False
    },
    {
        "email": "user@ohdsi.org",
        "password": os.getenv("USER_PASSWORD", "changeme"),
        "full_name": "Regular User",
        "organization": "OHDSI Community",
        "role": UserRole.EXPLORER,
        "is_superuser": False
    }
]

def init_users():
    """Initialize default users in the database."""
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    with Session(engine) as db:
        for user_data in DEFAULT_USERS:
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == user_data["email"]).first()
            if existing_user:
                logger.info(f"User {user_data['email']} already exists, skipping...")
                continue
            
            # Create new user
            user = User(
                email=user_data["email"],
                password_hash=auth_service.get_password_hash(user_data["password"]),
                full_name=user_data["full_name"],
                organization=user_data["organization"],
                role=user_data["role"],
                is_superuser=user_data["is_superuser"],
                is_active=True
            )
            db.add(user)
            db.flush()  # Get the user ID
            
            # Create user preferences
            preferences = UserPreferences(
                user_id=user.id,
                preferences={},
                saved_searches=[],
                bookmarks=[]
            )
            db.add(preferences)
            
            logger.info(f"Created user: {user_data['email']} with role: {user_data['role'].value}")
        
        db.commit()
        logger.info("Default users initialized successfully!")

if __name__ == "__main__":
    init_users()