"""
User query resolvers.

Handles me and list_users queries.
"""
from typing import Optional, List
from strawberry.types import Info

from ..types.user import User
from ..helpers import get_authenticated_user, require_admin
from ....database import SessionLocal
from ....models import User as UserModel


def resolve_me(info: Info) -> Optional[User]:
    """Get current user (requires auth)"""
    user = get_authenticated_user(info)
    if not user:
        return None
    return User(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        organization=user.organization,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login,
    )


def resolve_list_users(info: Info) -> List[User]:
    """List all users (requires admin role)"""
    require_admin(info)
    db = SessionLocal()
    try:
        users = db.query(UserModel).order_by(UserModel.created_at.desc()).all()
        return [
            User(
                id=str(u.id),
                email=u.email,
                full_name=u.full_name,
                organization=u.organization,
                role=u.role.value,
                is_active=u.is_active,
                created_at=u.created_at,
                last_login=u.last_login,
            )
            for u in users
        ]
    finally:
        db.close()
