"""Unit tests for API CRUD operations"""
from fastapi.testclient import TestClient
import sys

sys.path.append("../..")
from main import app

client = TestClient(app)


class TestCRUD:
    """Test CRUD operations"""

    def test_health_check(self):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "api"

    def test_create_item(self):
        """Test item creation"""
        headers = {"X-User-Id": "test-user", "X-User-Email": "test@example.com"}

        response = client.post(
            "/items",
            json={"name": "Test Item", "description": "Test Description"},
            headers=headers,
        )

        # Will be 503 if Firestore not configured, 200 if it is
        if response.status_code == 200:
            data = response.json()
            assert data["name"] == "Test Item"
            assert data["user_id"] == "test-user"
        else:
            assert response.status_code == 503
            assert "Database not available" in response.json()["detail"]

    def test_missing_user_headers(self):
        """Test missing user headers"""
        response = client.post("/items", json={"name": "Test Item"})
        # Should get 401 for missing headers or 503 if Firestore not configured
        assert response.status_code in [401, 503]
        if response.status_code == 401:
            assert "User ID header required" in response.json()["detail"]
        else:
            assert "Database not available" in response.json()["detail"]

    def test_get_items(self):
        """Test getting items"""
        headers = {"X-User-Id": "test-user"}
        response = client.get("/items", headers=headers)

        # Will be 503 if Firestore not configured, 200 if it is
        if response.status_code == 200:
            assert isinstance(response.json(), list)
        else:
            assert response.status_code == 503
            assert "Database not available" in response.json()["detail"]

    def test_upload_no_file(self):
        """Test upload with no file"""
        headers = {"X-User-Id": "test-user"}
        response = client.post("/upload", headers=headers)

        # Should get 422 for missing file or 503 if Storage not configured
        assert response.status_code in [422, 503]
        if response.status_code == 503:
            assert "Storage not available" in response.json()["detail"]

    def test_get_item_by_id(self):
        """Test getting item by ID"""
        headers = {"X-User-Id": "test-user"}
        response = client.get("/items/test-item-id", headers=headers)

        # Will be 404 or 503 depending on Firestore status
        assert response.status_code in [404, 503]
        if response.status_code == 503:
            assert "Database not available" in response.json()["detail"]

    def test_delete_item(self):
        """Test deleting an item"""
        headers = {"X-User-Id": "test-user"}
        response = client.delete("/items/test-item-id", headers=headers)

        # Will be 200 or 503 depending on Firestore status
        assert response.status_code in [200, 503]
        if response.status_code == 503:
            assert "Database not available" in response.json()["detail"]
