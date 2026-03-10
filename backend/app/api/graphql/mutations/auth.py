"""
Authentication mutation resolvers.

Handles register and login mutations.
"""
from datetime import datetime
from typing import Optional

from ..types.user import User, AuthPayload
from ....database import SessionLocal
from ....models import User as UserModel
from ...routes.auth import create_access_token, get_password_hash, verify_password


async def resolve_register(
    email: str,
    password: str,
    full_name: str,
    organization: Optional[str] = None
) -> AuthPayload:
    """Register new user"""
    from ....models import UserPreferences

    db = SessionLocal()
    try:
        # Check if user exists
        existing = db.query(UserModel).filter(UserModel.email == email).first()
        if existing:
            raise Exception("Email already registered")

        # Create user
        hashed_password = get_password_hash(password)
        user = UserModel(
            email=email,
            password_hash=hashed_password,
            full_name=full_name,
            organization=organization
        )
        db.add(user)

        # Create preferences
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)

        db.commit()
        db.refresh(user)

        # Create token
        access_token = create_access_token({"sub": str(user.id)})

        return AuthPayload(
            access_token=access_token,
            user=User(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                organization=user.organization,
                role=user.role.value,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login=user.last_login
            )
        )
    finally:
        db.close()


async def resolve_login(email: str, password: str) -> AuthPayload:
    """Login user"""
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.email == email).first()
        if not user or not verify_password(password, user.password_hash):
            raise Exception("Invalid credentials")

        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()

        # Create token
        access_token = create_access_token({"sub": str(user.id)})

        return AuthPayload(
            access_token=access_token,
            user=User(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                organization=user.organization,
                role=user.role.value,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login=user.last_login
            )
        )
    finally:
        db.close()
