"""
End-to-End Integration Tests
Tests full user flows through Gateway → API → GCP Services
"""
import os
import pytest
import httpx
import uuid
import json
from datetime import datetime

# Get test configuration from environment
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8080")
TEST_TOKEN = os.getenv("TEST_BYPASS_TOKEN", "")
ENVIRONMENT = os.getenv("TEST_ENVIRONMENT", "local")


@pytest.fixture
def client():
    """Create HTTP client with test bypass token"""
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        "Content-Type": "application/json",
    }
    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=30.0) as client:
        yield client


@pytest.fixture
def test_user_data():
    """Create test user data"""
    return {
        "name": f"Test User {uuid.uuid4().hex[:8]}",
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "preferences": {"theme": "dark", "notifications": True},
    }


class TestEndToEndFlows:
    """Test complete user flows through all services"""

    def test_health_check_all_services(self, client):
        """Test that all services are healthy"""
        # Gateway health
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

        # API health (through gateway)
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "api"
        assert "firestore" in data
        assert "storage" in data

    def test_user_profile_flow(self, client, test_user_data):
        """Test creating and managing user profile"""
        # Get current user (test bypass token provides test admin user)
        response = client.get("/api/users/me")
        assert response.status_code == 200
        user = response.json()
        assert user["user_id"] == "test_admin_123"
        assert user["email"] == "admin@test.example.com"

        # Create a profile item for the user
        profile_data = {
            "name": f"Profile for {user['user_id']}",
            "description": json.dumps(test_user_data),
            "metadata": {
                "type": "user_profile",
                "user_id": user["user_id"],
                "created_at": datetime.utcnow().isoformat(),
            },
        }

        create_response = client.post("/api/items", json=profile_data)
        assert create_response.status_code == 200
        profile = create_response.json()
        assert "id" in profile

        # Read the profile back
        read_response = client.get(f"/api/items/{profile['id']}")
        assert read_response.status_code == 200
        retrieved_profile = read_response.json()
        assert retrieved_profile["id"] == profile["id"]

        # Update the profile
        updated_data = {
            "name": f"Updated Profile for {user['user_id']}",
            "description": json.dumps({**test_user_data, "updated": True}),
        }
        update_response = client.put(f"/api/items/{profile['id']}", json=updated_data)
        assert update_response.status_code == 200

        # Cleanup
        client.delete(f"/api/items/{profile['id']}")

    def test_file_upload_flow(self, client):
        """Test file upload through gateway to API"""
        # Create a test file
        file_content = b"Test file content for E2E testing"
        file_name = f"e2e_test_{uuid.uuid4().hex[:8]}.txt"

        # Upload file through gateway
        files = {"file": (file_name, file_content, "text/plain")}

        # Note: Adjust headers for multipart upload
        upload_client = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
            timeout=30.0,
        )

        with upload_client:
            upload_response = upload_client.post("/api/files/upload", files=files)
            assert upload_response.status_code == 200

            file_data = upload_response.json()
            assert "file_id" in file_data
            file_id = file_data["file_id"]

            # Get download URL
            download_response = upload_client.get(f"/api/files/{file_id}/download")
            assert download_response.status_code == 200
            download_data = download_response.json()
            assert "download_url" in download_data
            
            # Download the file using the pre-signed URL
            actual_download = httpx.get(download_data["download_url"])
            assert actual_download.status_code == 200
            assert actual_download.content == file_content

            # Cleanup
            upload_client.delete(f"/api/files/{file_id}")

    def test_ai_chat_flow(self, client):
        """Test AI chat through gateway"""
        chat_request = {
            "messages": [
                {
                    "role": "user",
                    "content": "Hello, this is an integration test. Please respond with 'Test successful'",
                }
            ],
            "temperature": 0.1,
            "max_tokens": 50,
        }

        response = client.post("/ai/chat", json=chat_request)

        # AI service might return 503 if OpenAI is not configured
        # or 200 if it's working
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "response" in data or "message" in data
        elif response.status_code == 503:
            # This is expected if OpenAI is not configured
            assert "OpenAI service unavailable" in response.json()["detail"]

    def test_combined_workflow(self, client):
        """Test a combined workflow using multiple services"""
        # Step 1: Get user info
        user_response = client.get("/api/users/me")
        assert user_response.status_code == 200
        user = user_response.json()

        # Step 2: Create an item for the user
        item_data = {
            "name": f"Workflow item for {user['user_id']}",
            "description": "Created in combined workflow test",
            "metadata": {
                "workflow": "e2e_test",
                "user_id": user["user_id"],
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

        create_response = client.post("/api/items", json=item_data)
        assert create_response.status_code == 200
        item = create_response.json()

        # Step 3: List items to verify it exists
        list_response = client.get("/api/items")
        assert list_response.status_code == 200
        items = list_response.json()["items"]
        assert any(i["id"] == item["id"] for i in items)

        # Step 4: Make an AI request about the item (if AI is available)
        ai_request = {
            "messages": [
                {
                    "role": "user",
                    "content": f"I have an item named '{item_data['name']}'. Please acknowledge.",
                }
            ],
            "temperature": 0.1,
            "max_tokens": 50,
        }

        ai_response = client.post("/ai/chat", json=ai_request)
        # Don't fail if AI is not configured, just check it responds
        assert ai_response.status_code in [200, 503]

        # Cleanup
        client.delete(f"/api/items/{item['id']}")

    def test_error_handling_flow(self, client):
        """Test error handling across services"""
        # Test 404 for non-existent item
        response = client.get("/api/items/non_existent_id")
        assert response.status_code == 404

        # Test unauthorized access without token
        unauth_client = httpx.Client(base_url=BASE_URL)
        with unauth_client:
            response = unauth_client.get("/api/users/me")
            assert response.status_code == 401


@pytest.mark.skipif(
    ENVIRONMENT == "production", reason="Skip cleanup tests in production"
)
class TestE2ECleanup:
    """Cleanup test data"""

    def test_cleanup_e2e_test_data(self, client):
        """Clean up any test data created during E2E tests"""
        # Clean up test items
        response = client.get("/api/items?limit=100")
        if response.status_code == 200:
            items = response.json().get("items", [])
            for item in items:
                # Delete items created by E2E tests
                if (
                    "workflow" in item.get("metadata", {})
                    and item["metadata"]["workflow"] == "e2e_test"
                ):
                    client.delete(f"/api/items/{item['id']}")
                elif item.get("name", "").startswith("Workflow item for") or item.get(
                    "name", ""
                ).startswith("Profile for"):
                    client.delete(f"/api/items/{item['id']}")
