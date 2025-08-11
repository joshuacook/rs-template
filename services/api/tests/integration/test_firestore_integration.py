"""
Firestore Integration Tests
Tests actual database operations against real Firestore
"""
import os
import pytest
import httpx
import uuid
from datetime import datetime

# Get test configuration from environment
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8081")
TEST_TOKEN = os.getenv("TEST_TOKEN", "")
ENVIRONMENT = os.getenv("TEST_ENVIRONMENT", "local")


@pytest.fixture
def client():
    """Create HTTP client with auth headers"""
    headers = {
        "X-User-Id": "test_user_" + str(uuid.uuid4())[:8],
        "X-User-Email": "test@example.com",
    }
    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=30.0) as client:
        yield client


@pytest.fixture
def test_item():
    """Create a test item data"""
    return {
        "name": f"Test Item {uuid.uuid4().hex[:8]}",
        "description": "Integration test item",
        "metadata": {"created_at": datetime.utcnow().isoformat(), "test": True},
    }


class TestFirestoreIntegration:
    """Test Firestore CRUD operations"""

    def test_create_item(self, client, test_item):
        """Test creating an item in Firestore"""
        response = client.post("/items", json=test_item)
        assert response.status_code == 200

        data = response.json()
        assert "id" in data
        assert data["name"] == test_item["name"]
        assert data["description"] == test_item["description"]

        # Store item ID for cleanup
        pytest.test_item_id = data["id"]
        return data["id"]

    def test_read_item(self, client, test_item):
        """Test reading an item from Firestore"""
        # First create an item
        create_response = client.post("/items", json=test_item)
        assert create_response.status_code == 200
        item_id = create_response.json()["id"]

        # Now read it back
        read_response = client.get(f"/items/{item_id}")
        assert read_response.status_code == 200

        data = read_response.json()
        assert data["id"] == item_id
        assert data["name"] == test_item["name"]
        assert data["description"] == test_item["description"]

        # Cleanup
        client.delete(f"/items/{item_id}")

    def test_update_item(self, client, test_item):
        """Test updating an item in Firestore"""
        # Create an item
        create_response = client.post("/items", json=test_item)
        assert create_response.status_code == 200
        item_id = create_response.json()["id"]

        # Update it
        updated_data = {
            "name": "Updated Item Name",
            "description": "Updated description",
        }
        update_response = client.put(f"/items/{item_id}", json=updated_data)
        assert update_response.status_code == 200

        # Verify the update
        read_response = client.get(f"/items/{item_id}")
        assert read_response.status_code == 200
        data = read_response.json()
        assert data["name"] == updated_data["name"]
        assert data["description"] == updated_data["description"]

        # Cleanup
        client.delete(f"/items/{item_id}")

    def test_delete_item(self, client, test_item):
        """Test deleting an item from Firestore"""
        # Create an item
        create_response = client.post("/items", json=test_item)
        assert create_response.status_code == 200
        item_id = create_response.json()["id"]

        # Delete it
        delete_response = client.delete(f"/items/{item_id}")
        assert delete_response.status_code == 200

        # Verify it's gone
        read_response = client.get(f"/items/{item_id}")
        assert read_response.status_code == 404

    def test_list_items(self, client, test_item):
        """Test listing items from Firestore"""
        # Create multiple items
        item_ids = []
        for i in range(3):
            test_item["name"] = f"List Test Item {i}"
            response = client.post("/items", json=test_item)
            assert response.status_code == 200
            item_ids.append(response.json()["id"])

        # List items
        list_response = client.get("/items")
        assert list_response.status_code == 200

        data = list_response.json()
        assert "items" in data
        assert len(data["items"]) >= 3

        # Cleanup
        for item_id in item_ids:
            client.delete(f"/items/{item_id}")

    def test_list_items_with_pagination(self, client, test_item):
        """Test pagination when listing items"""
        # Create items for pagination test
        item_ids = []
        for i in range(5):
            test_item["name"] = f"Pagination Test Item {i}"
            response = client.post("/items", json=test_item)
            assert response.status_code == 200
            item_ids.append(response.json()["id"])

        # Get first page
        response = client.get("/items?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2

        # Cleanup
        for item_id in item_ids:
            client.delete(f"/items/{item_id}")


@pytest.mark.skipif(
    ENVIRONMENT == "production", reason="Skip cleanup tests in production"
)
class TestFirestoreCleanup:
    """Test cleanup operations"""

    def test_cleanup_test_items(self, client):
        """Clean up any leftover test items"""
        # List all items
        response = client.get("/items?limit=100")
        if response.status_code == 200:
            data = response.json()
            for item in data.get("items", []):
                # Delete items created by tests
                if (
                    item.get("name", "").startswith("Test Item")
                    or item.get("name", "").startswith("List Test Item")
                    or item.get("name", "").startswith("Pagination Test Item")
                ):
                    client.delete(f"/items/{item['id']}")
