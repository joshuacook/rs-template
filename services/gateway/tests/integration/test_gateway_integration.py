"""
Gateway Service Integration Tests
These tests run against actual deployed services (local, staging, or production)
"""
import os
import pytest
import httpx

# Get test configuration from environment
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8080")
TEST_TOKEN = os.getenv("TEST_TOKEN", "")
ENVIRONMENT = os.getenv("TEST_ENVIRONMENT", "local")

@pytest.fixture
def client():
    """Create HTTP client with test token"""
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json"
    }
    with httpx.Client(base_url=BASE_URL, headers=headers) as client:
        yield client

def test_gateway_health(client):
    """Test gateway health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "gateway"

def test_gateway_root(client):
    """Test gateway root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "gateway"
    assert "project" in data
    assert "environment" in data

def test_api_proxy_with_test_token(client):
    """Test that API proxy works with test bypass token"""
    response = client.get("/api/users/me")
    assert response.status_code == 200
    data = response.json()
    
    # Should get test admin user
    assert data["user_id"] == "test_admin_123"
    assert data["email"] == "admin@test.example.com"

def test_ai_proxy_with_test_token(client):
    """Test that AI proxy works with test bypass token"""
    # Just test that the route exists and accepts our token
    # The AI service might return 400 if no messages provided
    response = client.post("/ai/chat", json={})
    assert response.status_code in [200, 400, 503]  # 503 if OpenAI not configured
    
    if response.status_code == 400:
        # This is expected if no messages provided
        assert "Messages are required" in response.json()["detail"]

def test_unauthorized_without_token():
    """Test that requests without token are rejected in production"""
    if ENVIRONMENT == "local":
        pytest.skip("Auth not enforced in local development")
    
    with httpx.Client(base_url=BASE_URL) as client:
        response = client.get("/api/users/me")
        assert response.status_code == 401