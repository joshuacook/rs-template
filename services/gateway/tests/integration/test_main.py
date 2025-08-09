"""
Tests for Gateway Service
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
    assert data["service"] == "gateway"
    assert "status" in data

def test_health():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "gateway"

def test_api_proxy_no_auth():
    """Test API proxy without authentication"""
    # In development mode, this should work
    os.environ["ENVIRONMENT"] = "development"
    response = client.get("/api/test")
    # Will fail because API service isn't running in test
    # This is just to test the route exists
    assert response.status_code in [200, 500, 503]

def test_ai_proxy_no_auth():
    """Test AI proxy without authentication"""
    # In development mode, this should work
    os.environ["ENVIRONMENT"] = "development"
    response = client.post("/ai/chat", json={"messages": []})
    # Will fail because AI service isn't running in test
    # This is just to test the route exists
    assert response.status_code in [200, 400, 500, 503]

def test_auth_required_in_production():
    """Test that auth is required in production"""
    os.environ["ENVIRONMENT"] = "production"
    # Recreate client to pick up env change
    from main import app as prod_app
    prod_client = TestClient(prod_app)
    
    response = prod_client.get("/api/test")
    assert response.status_code == 401
    
    response = prod_client.post("/ai/chat", json={})
    assert response.status_code == 401