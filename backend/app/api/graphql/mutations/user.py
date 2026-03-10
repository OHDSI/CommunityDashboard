"""
User mutation resolvers.

Handles create_user, update_user_role, and deactivate_user mutations.
"""
from strawberry.types import Info

from ..types.user import User
from ..helpers import require_admin
from ....database import SessionLocal
from ....models import User as UserModel, UserRole
from ...routes.auth import get_password_hash


def resolve_create_user(
    info: Info,
    email: str,
    password: str,
    full_name: str,
    role: str = "reviewer",
) -> User:
    """Create a new user (requires admin role)"""
    require_admin(info)
    db = SessionLocal()
    try:
        existing = db.query(UserModel).filter(UserModel.email == email).first()
        if existing:
            raise Exception("Email already registered")

        try:
            user_role = UserRole(role)
        except ValueError:
            raise Exception(f"Invalid role: {role}. Valid roles: {[r.value for r in UserRole]}")

        hashed_password = get_password_hash(password)
        new_user = UserModel(
            email=email,
            password_hash=hashed_password,
            full_name=full_name,
            role=user_role,
            is_active=True,
            is_superuser=(user_role == UserRole.ADMIN),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return User(
            id=str(new_user.id),
            email=new_user.email,
            full_name=new_user.full_name,
            organization=new_user.organization,
            role=new_user.role.value,
            is_active=new_user.is_active,
            created_at=new_user.created_at,
            last_login=new_user.last_login,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def resolve_update_user_role(
    info: Info,
    user_id: str,
    role: str,
) -> bool:
    """Update a user's role (requires admin role)"""
    require_admin(info)
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise Exception("User not found")

        try:
            new_role = UserRole(role)
        except ValueError:
            raise Exception(f"Invalid role: {role}")

        user.role = new_role
        user.is_superuser = (new_role == UserRole.ADMIN)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def resolve_deactivate_user(
    info: Info,
    user_id: str,
) -> bool:
    """Deactivate a user (requires admin role)"""
    admin = require_admin(info)
    if str(admin.id) == user_id:
        raise Exception("Cannot deactivate yourself")
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise Exception("User not found")
        user.is_active = False
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
