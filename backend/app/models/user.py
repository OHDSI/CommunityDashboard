from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from ..database import Base

class UserRole(str, enum.Enum):
    EXPLORER = "explorer"
    LEARNER = "learner"
    RESEARCHER = "researcher"
    IMPLEMENTER = "implementer"
    CONTRIBUTOR = "contributor"
    REVIEWER = "reviewer"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    organization = Column(String(255))
    role = Column(Enum(UserRole), default=UserRole.EXPLORER)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # SSO fields
    sso_provider = Column(String(50))  # google, github, azure, orcid, etc.
    sso_id = Column(String(255))  # Provider's unique user ID
    sso_email_verified = Column(Boolean, default=False)
    
    # Relationships
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    @staticmethod
    def get_role_value(role_str: str) -> int:
        """Get numeric value for role comparison."""
        role_hierarchy = {
            "explorer": 1,
            "learner": 2,
            "researcher": 3,
            "implementer": 4,
            "contributor": 5,
            "reviewer": 6,
            "admin": 7
        }
        return role_hierarchy.get(role_str.lower(), 0)

class ApiKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    permissions = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="api_keys")

class UserPreferences(Base):
    __tablename__ = "user_preferences"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    preferences = Column(JSON, default=dict)
    saved_searches = Column(JSON, default=list)
    bookmarks = Column(JSON, default=list)
    
    # Relationships
    user = relationship("User", back_populates="preferences")