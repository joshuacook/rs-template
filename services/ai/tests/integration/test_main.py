"""
Tests for AI Service
"""
import pytest
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
    assert "openai" in data
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
    messages = [
        {"role": "user", "content": "Hello"}
    ]
    response = client.post(
        "/chat", 
        json={"messages": messages},
        headers=headers
    )
    # Will fail if OpenAI not configured
    assert response.status_code in [200, 503]
    
    if response.status_code == 503:
        assert "OpenAI client not configured" in response.json()["detail"]

def test_analyze_no_auth():
    """Test analyze endpoint without auth"""
    response = client.post("/analyze", json={"text": "Test"})
    assert response.status_code == 401

def test_analyze_no_text():
    """Test analyze endpoint without text"""
    headers = {"X-User-Id": "test_user_123"}
    response = client.post("/analyze", json={}, headers=headers)
    assert response.status_code == 400
    assert "Text is required" in response.json()["detail"]

def test_analyze_with_text():
    """Test analyze endpoint with text"""
    headers = {"X-User-Id": "test_user_123"}
    response = client.post(
        "/analyze",
        json={
            "text": "This is a test text for analysis.",
            "analysis_type": "summary"
        },
        headers=headers
    )
    # Will fail if OpenAI not configured
    assert response.status_code in [200, 503]
    
    if response.status_code == 503:
        assert "OpenAI client not configured" in response.json()["detail"]

def test_embeddings_no_auth():
    """Test embeddings endpoint without auth"""
    response = client.post("/embeddings", json={"texts": ["test"]})
    assert response.status_code == 401

def test_embeddings_no_texts():
    """Test embeddings endpoint without texts"""
    headers = {"X-User-Id": "test_user_123"}
    response = client.post("/embeddings", json={}, headers=headers)
    assert response.status_code == 400
    assert "Texts are required" in response.json()["detail"]

def test_embeddings_with_texts():
    """Test embeddings endpoint with texts"""
    headers = {"X-User-Id": "test_user_123"}
    response = client.post(
        "/embeddings",
        json={"texts": ["test text 1", "test text 2"]},
        headers=headers
    )
    # Will fail if OpenAI not configured
    assert response.status_code in [200, 503]
    
    if response.status_code == 503:
        assert "OpenAI client not configured" in response.json()["detail"]