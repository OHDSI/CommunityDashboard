"""Test authentication endpoints and utilities."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.utils.auth import auth_service

class TestAuthentication:
    """Test authentication functionality."""
    
    def test_register_user(self, client: TestClient, db_session: Session):
        """Test user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "newpassword123",
                "full_name": "New User",
                "organization": "New Org"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "newuser@example.com"
        
        # Check user was created in database
        user = db_session.query(User).filter(User.email == "newuser@example.com").first()
        assert user is not None
        assert user.full_name == "New User"
    
    def test_register_duplicate_email(self, client: TestClient, test_user: User):
        """Test registration with duplicate email."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "password123",
                "full_name": "Duplicate User",
                "organization": "Org"
            }
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    def test_login_valid_credentials(self, client: TestClient, test_user: User):
        """Test login with valid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == test_user.email
    
    def test_login_invalid_password(self, client: TestClient, test_user: User):
        """Test login with invalid password."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 401
    
    def test_get_current_user(self, client: TestClient, test_user: User, auth_headers: dict):
        """Test getting current user info."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name
    
    def test_get_current_user_unauthorized(self, client: TestClient):
        """Test getting current user without authentication."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 403  # No Authorization header
    
    def test_logout(self, client: TestClient, auth_headers: dict):
        """Test logout endpoint."""
        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()

class TestAuthService:
    """Test authentication service utilities."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "test_password_123"
        hashed = auth_service.get_password_hash(password)
        
        # Hash should be different from original
        assert hashed != password
        
        # Should verify correctly
        assert auth_service.verify_password(password, hashed)
        
        # Should not verify with wrong password
        assert not auth_service.verify_password("wrong_password", hashed)
    
    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "user123", "role": "explorer"}
        token = auth_service.create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Verify token
        payload = auth_service.verify_token(token)
        assert payload["sub"] == "user123"
        assert payload["role"] == "explorer"
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"sub": "user123"}
        token = auth_service.create_refresh_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Verify token
        payload = auth_service.verify_token(token)
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"