"""Test configuration and fixtures."""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import User, UserRole
from app.utils.auth import auth_service

# Test database URL (in-memory SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Create test engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create test session
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client with overridden database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash=auth_service.get_password_hash("testpassword"),
        full_name="Test User",
        organization="Test Org",
        role=UserRole.EXPLORER,
        is_active=True,
        is_superuser=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def admin_user(db_session: Session) -> User:
    """Create a test admin user."""
    user = User(
        email="admin@example.com",
        password_hash=auth_service.get_password_hash("adminpassword"),
        full_name="Admin User",
        organization="Admin Org",
        role=UserRole.ADMIN,
        is_active=True,
        is_superuser=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def auth_headers(test_user: User) -> dict:
    """Create authentication headers for test user."""
    token = auth_service.create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="function")
def admin_headers(admin_user: User) -> dict:
    """Create authentication headers for admin user."""
    token = auth_service.create_access_token({"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()