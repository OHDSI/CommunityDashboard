"""
User-related GraphQL types.

Includes User and AuthPayload types.
"""
import strawberry
from typing import Optional
from datetime import datetime


@strawberry.type
class User:
    id: str
    email: str
    full_name: Optional[str]
    organization: Optional[str]
    role: str
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime]


@strawberry.type
class AuthPayload:
    access_token: str
    token_type: str = "bearer"
    user: User
