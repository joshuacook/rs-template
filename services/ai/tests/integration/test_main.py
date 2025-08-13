"""
Tests for AI Service
"""
from fastapi.testclient import TestClient
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)


def test_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ai"
    assert "status" in data
    assert "model" in data


def test_health():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ai"
    assert data["provider"] == "openai"
    assert "langfuse" in data


def test_chat_no_auth():
    """Test chat endpoint without auth"""
    response = client.post("/chat", json={"messages": []})
    assert response.status_code == 401


def test_chat_with_auth_no_messages():
    """Test chat endpoint with auth but no messages"""
    headers = {"X-User-Id": "test_user_123"}
    response = client.post("/chat", json={}, headers=headers)
    assert response.status_code == 400
    assert "Messages are required" in response.json()["detail"]


def test_chat_with_auth_and_messages():
    """Test chat endpoint with auth and messages"""
    headers = {"X-User-Id": "test_user_123"}
    messages = [{"role": "user", "content": "Hello"}]
    response = client.post("/chat", json={"messages": messages}, headers=headers)
    # Will fail if OpenAI not configured
    assert response.status_code in [200, 503]

    if response.status_code == 503:
        assert "OpenAI client not configured" in response.json()["detail"]


