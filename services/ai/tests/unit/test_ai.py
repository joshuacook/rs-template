"""Unit tests for AI service"""
from unittest.mock import patch
from fastapi.testclient import TestClient
import sys

sys.path.append("../..")
from main import app

client = TestClient(app)


class TestAIService:
    """Test AI service operations"""

    def test_health_check(self):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "ai"

    def test_chat_completion(self):
        """Test chat completion"""
        headers = {"X-User-Id": "test-user"}

        response = client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "max_completion_tokens": 1000,
            },
            headers=headers,
        )

        # Check for either success or not configured
        if response.status_code == 200:
            assert "response" in response.json()
            assert "model" in response.json()
        else:
            assert response.status_code == 503
            assert "OpenAI client not configured" in response.json()["detail"]

    def test_chat_missing_headers(self):
        """Test chat with missing headers"""
        response = client.post(
            "/chat", json={"messages": [{"role": "user", "content": "Hello"}]}
        )
        assert response.status_code == 401  # Unauthorized - missing user header

    def test_no_openai_client(self):
        """Test behavior when OpenAI client is not configured"""
        with patch("main.openai_client", None):
            headers = {"X-User-Id": "test-user"}

            response = client.post(
                "/chat",
                json={"messages": [{"role": "user", "content": "Hello"}]},
                headers=headers,
            )

            assert response.status_code == 503
            assert "OpenAI client not configured" in response.json()["detail"]
