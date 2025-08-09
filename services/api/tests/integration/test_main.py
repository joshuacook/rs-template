"""
Tests for API Service
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
    assert data["service"] == "api"
    assert "status" in data

def test_health():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "api"
    assert "firestore" in data
    assert "storage" in data

def test_get_current_user_no_auth():
    """Test getting current user without auth headers"""
    response = client.get("/users/me")
    assert response.status_code == 401

def test_get_current_user_with_auth():
    """Test getting current user with auth headers"""
    headers = {
        "X-User-Id": "test_user_123",
        "X-User-Email": "test@example.com"
    }
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test_user_123"
    assert data["email"] == "test@example.com"

def test_create_item_no_auth():
    """Test creating item without auth"""
    response = client.post("/items", json={"name": "Test Item"})
    assert response.status_code == 401

def test_create_item_with_auth():
    """Test creating item with auth (will fail without Firestore)"""
    headers = {
        "X-User-Id": "test_user_123",
        "X-User-Email": "test@example.com"
    }
    response = client.post(
        "/items", 
        json={"name": "Test Item", "description": "Test Description"},
        headers=headers
    )
    # Will fail because Firestore isn't configured in test
    assert response.status_code in [200, 503]
    
    if response.status_code == 503:
        data = response.json()
        assert "Database not available" in data["detail"]

def test_list_items_requires_auth():
    """Test that listing items requires authentication"""
    response = client.get("/items")
    assert response.status_code == 401

def test_get_item_requires_auth():
    """Test that getting an item requires authentication"""
    response = client.get("/items/test_id")
    assert response.status_code == 401

def test_update_item_requires_auth():
    """Test that updating an item requires authentication"""
    response = client.put("/items/test_id", json={"name": "Updated"})
    assert response.status_code == 401

def test_delete_item_requires_auth():
    """Test that deleting an item requires authentication"""
    response = client.delete("/items/test_id")
    assert response.status_code == 401