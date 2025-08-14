"""
Cloud Storage Integration Tests
Tests actual file operations against real GCS
"""
import os
import pytest
import httpx
import uuid
import base64

# Get test configuration from environment
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8080")  # Gateway URL
TEST_TOKEN = os.getenv("TEST_BYPASS_TOKEN", "")
ENVIRONMENT = os.getenv("TEST_ENVIRONMENT", "local")


@pytest.fixture
def client():
    """Create HTTP client with auth headers"""
    headers = {
        "Authorization": f"Bearer {TEST_TOKEN}",
        # Don't set Content-Type - let httpx handle it for multipart/form-data
    }
    # For API tests, we need to go through the gateway with /api prefix
    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=30.0) as client:
        yield client


@pytest.fixture
def test_file_content():
    """Create test file content"""
    return b"This is a test file for integration testing"


@pytest.fixture
def test_image_content():
    """Create a small test image (1x1 pixel PNG)"""
    # Base64 encoded 1x1 transparent PNG
    png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    return base64.b64decode(png_base64)


class TestStorageIntegration:
    """Test Cloud Storage operations"""

    def test_upload_file(self, client, test_file_content):
        """Test uploading a file to Cloud Storage"""
        file_name = f"test_file_{uuid.uuid4().hex[:8]}.txt"

        files = {"file": (file_name, test_file_content, "text/plain")}

        response = client.post("/api/files/upload", files=files)
        if response.status_code != 200:
            print(f"Upload failed: {response.status_code} - {response.text}")
        assert response.status_code == 200

        data = response.json()
        assert "file_id" in data
        assert "file_name" in data
        assert "url" in data
        assert data["file_name"] == file_name

        # Store for cleanup
        pytest.test_file_id = data["file_id"]
        return data["file_id"]

    def test_download_file(self, client, test_file_content):
        """Test downloading a file from Cloud Storage"""
        # First upload a file
        file_name = f"test_download_{uuid.uuid4().hex[:8]}.txt"
        files = {"file": (file_name, test_file_content, "text/plain")}

        upload_response = client.post("/api/files/upload", files=files)
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]

        # Get download URL
        download_response = client.get(f"/api/files/{file_id}/download")
        assert download_response.status_code == 200
        download_data = download_response.json()
        assert "download_url" in download_data
        assert "file_name" in download_data
        assert "expires_in" in download_data
        assert download_data["expires_in"] == 3600

        # Cleanup
        client.delete(f"/api/files/{file_id}")

    def test_list_files(self, client, test_file_content):
        """Test listing files from Cloud Storage"""
        # Upload multiple files
        file_ids = []
        for i in range(3):
            file_name = f"test_list_{i}_{uuid.uuid4().hex[:8]}.txt"
            files = {"file": (file_name, test_file_content, "text/plain")}
            response = client.post("/api/files/upload", files=files)
            assert response.status_code == 200
            file_ids.append(response.json()["file_id"])

        # List files
        list_response = client.get("/api/files")
        assert list_response.status_code == 200

        data = list_response.json()
        assert "files" in data
        assert len(data["files"]) >= 3

        # Cleanup
        for file_id in file_ids:
            client.delete(f"/api/files/{file_id}")

    def test_delete_file(self, client, test_file_content):
        """Test deleting a file from Cloud Storage"""
        # Upload a file
        file_name = f"test_delete_{uuid.uuid4().hex[:8]}.txt"
        files = {"file": (file_name, test_file_content, "text/plain")}

        upload_response = client.post("/api/files/upload", files=files)
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]

        # Delete it
        delete_response = client.delete(f"/api/files/{file_id}")
        assert delete_response.status_code == 200

        # Verify it's gone
        download_response = client.get(f"/api/files/{file_id}/download")
        assert download_response.status_code == 404

    def test_upload_image(self, client, test_image_content):
        """Test uploading an image to Cloud Storage"""
        file_name = f"test_image_{uuid.uuid4().hex[:8]}.png"

        files = {"file": (file_name, test_image_content, "image/png")}

        response = client.post("/api/files/upload", files=files)
        assert response.status_code == 200

        data = response.json()
        assert "file_id" in data
        assert data["file_name"] == file_name

        # Cleanup
        client.delete(f"/api/files/{data['file_id']}")

    @pytest.mark.skipif(
        os.getenv("TEST_ENVIRONMENT") in ["staging", "production"],
        reason="Signed URL generation requires additional GCS permissions not available in staging/production"
    )
    def test_generate_signed_url(self, client, test_file_content):
        """Test generating a signed URL for a file"""
        # Upload a file
        file_name = f"test_signed_{uuid.uuid4().hex[:8]}.txt"
        files = {"file": (file_name, test_file_content, "text/plain")}

        upload_response = client.post("/api/files/upload", files=files)
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]

        # Get signed URL
        signed_url_response = client.get(f"/api/files/{file_id}/signed-url")
        assert signed_url_response.status_code == 200

        data = signed_url_response.json()
        assert "signed_url" in data
        assert "expires_in" in data

        # Test that the signed URL works
        with httpx.Client() as external_client:
            download_response = external_client.get(data["signed_url"])
            assert download_response.status_code == 200
            assert download_response.content == test_file_content

        # Cleanup
        client.delete(f"/api/files/{file_id}")


@pytest.mark.skipif(
    ENVIRONMENT == "production", reason="Skip cleanup tests in production"
)
class TestStorageCleanup:
    """Test cleanup operations"""

    def test_cleanup_test_files(self, client):
        """Clean up any leftover test files"""
        # List all files
        response = client.get("/api/files?limit=100")
        if response.status_code == 200:
            data = response.json()
            for file_info in data.get("files", []):
                # Delete files created by tests
                if file_info.get("file_name", "").startswith("test_"):
                    client.delete(f"/api/files/{file_info['file_id']}")
