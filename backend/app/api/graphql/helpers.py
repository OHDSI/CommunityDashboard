"""
Shared helper functions for GraphQL resolvers.

Contains authentication helpers and utility functions used
across multiple query and mutation modules.
"""
import logging
from strawberry.types import Info

from ...database import SessionLocal
from ...models import User as UserModel, UserRole
from ...utils.auth import AuthService

logger = logging.getLogger(__name__)


def get_authenticated_user(info: Info):
    """Extract authenticated user from Strawberry GraphQL context.

    Returns the User ORM object if valid token, None otherwise.
    """
    request = info.context["request"]
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    try:
        payload = AuthService.verify_token(token)
    except Exception:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        return user
    finally:
        db.close()


def require_reviewer(info: Info):
    """Extract authenticated user and require REVIEWER or ADMIN role.

    Raises Exception if not authenticated or insufficient role.
    Returns the User ORM object.
    """
    user = get_authenticated_user(info)
    if not user:
        raise Exception("Authentication required")
    role_value = UserModel.get_role_value(user.role.value)
    if role_value < UserModel.get_role_value("reviewer"):
        raise Exception("Insufficient permissions. Reviewer role required.")
    return user


def require_admin(info: Info):
    """Extract authenticated user and require ADMIN role.

    Raises Exception if not authenticated or insufficient role.
    Returns the User ORM object.
    """
    user = get_authenticated_user(info)
    if not user:
        raise Exception("Authentication required")
    if user.role != UserRole.ADMIN:
        raise Exception("Insufficient permissions. Admin role required.")
    return user


def compute_display_fields(source: str, content_type: str) -> dict:
    """
    Compute display_type, icon_type, and content_category based on source and content_type.
    These fields are computed rather than stored in ES schema v3.
    """
    # Default values
    display_type = content_type.title() if content_type else "Content"
    icon_type = "document-text"
    content_category = "reference"

    # Source-specific mappings
    if source == "pubmed":
        display_type = "Research Article"
        icon_type = "document-text"
        content_category = "research"
    elif source == "youtube":
        display_type = "Video Content"
        icon_type = "play-circle"
        content_category = "media"
    elif source == "github":
        display_type = "Code Repository"
        icon_type = "code"
        content_category = "code"
    elif source == "discourse":
        display_type = "Discussion"
        icon_type = "chat-bubble"
        content_category = "community"
    elif source == "wiki":
        display_type = "Documentation"
        icon_type = "book-open"
        content_category = "reference"

    return {
        "display_type": display_type,
        "icon_type": icon_type,
        "content_category": content_category
    }
