"""Test GraphQL endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User

class TestGraphQLQueries:
    """Test GraphQL query operations."""
    
    def test_graphql_endpoint_accessible(self, client: TestClient):
        """Test that GraphQL endpoint is accessible."""
        response = client.post(
            "/graphql",
            json={
                "query": "{ __schema { queryType { name } } }"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["__schema"]["queryType"]["name"] == "Query"
    
    def test_search_content_query(self, client: TestClient):
        """Test content search query."""
        query = """
            query SearchContent($query: String) {
                searchContent(query: $query) {
                    total
                    items {
                        id
                        title
                        contentType
                    }
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"query": "OHDSI"}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # Note: This will return empty results without Elasticsearch
        assert "searchContent" in data["data"]
    
    def test_review_queue_query_unauthorized(self, client: TestClient):
        """Test review queue query without authentication."""
        query = """
            query ReviewQueue {
                reviewQueue(status: "pending") {
                    id
                    title
                    mlScore
                }
            }
        """
        response = client.post(
            "/graphql",
            json={"query": query}
        )
        assert response.status_code == 200
        # Should return data but possibly empty without auth

class TestGraphQLMutations:
    """Test GraphQL mutation operations."""
    
    def test_login_mutation(self, client: TestClient, test_user: User):
        """Test login mutation."""
        mutation = """
            mutation Login($email: String!, $password: String!) {
                login(email: $email, password: $password) {
                    accessToken
                    user {
                        email
                        fullName
                        role
                    }
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "email": test_user.email,
                    "password": "testpassword"
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "login" in data["data"]
        assert "accessToken" in data["data"]["login"]
        assert data["data"]["login"]["user"]["email"] == test_user.email
    
    def test_register_mutation(self, client: TestClient):
        """Test register mutation."""
        mutation = """
            mutation Register($email: String!, $password: String!, $fullName: String!, $organization: String) {
                register(email: $email, password: $password, fullName: $fullName, organization: $organization) {
                    accessToken
                    user {
                        email
                        fullName
                        organization
                    }
                }
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "email": "graphql@example.com",
                    "password": "password123",
                    "fullName": "GraphQL User",
                    "organization": "GraphQL Org"
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "register" in data["data"]
        assert data["data"]["register"]["user"]["email"] == "graphql@example.com"
    
    def test_approve_content_mutation_unauthorized(self, client: TestClient):
        """Test approve content mutation without authentication."""
        mutation = """
            mutation ApproveContent($id: ID!, $categories: [String!]) {
                approveContent(id: $id, categories: $categories)
            }
        """
        response = client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "id": "test-id",
                    "categories": ["Observational data standards and management"]
                }
            }
        )
        assert response.status_code == 200
        # Should handle the unauthorized case gracefully