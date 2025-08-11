"""Unit tests for gateway authentication"""
import pytest
import os
from unittest.mock import patch
from fastapi.testclient import TestClient
import sys

sys.path.append("../..")
from main import app, verify_token

client = TestClient(app)


class TestAuthentication:
    """Test authentication functions"""

    def test_health_check_no_auth(self):
        """Health check should work without authentication"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @patch.dict(os.environ, {"TEST_BYPASS_TOKEN": "test-token-123"})
    def test_bypass_token_auth(self):
        """Test bypass token authentication"""
        with patch("main.TEST_BYPASS_TOKEN", "test-token-123"):
            result = verify_token("Bearer test-token-123")
            assert result["user_id"] == "test_admin_123"
            assert result["email"] == "admin@test.example.com"
            assert result["role"] == "admin"

    def test_missing_auth_header(self):
        """Test missing authorization header"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_token(None)
        assert exc_info.value.status_code == 401

    def test_invalid_auth_format(self):
        """Test invalid authorization format"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            verify_token("InvalidFormat")
        assert exc_info.value.status_code == 401

    @patch("main.jwks_client")
    @patch("main.ENVIRONMENT", "production")
    def test_jwt_decode_error(self, mock_jwks):
        """Test JWT decode error handling"""
        from fastapi import HTTPException

        # Mock jwks_client to exist but fail on token verification
        mock_jwks.get_signing_key_from_jwt.side_effect = Exception("Invalid token")

        with pytest.raises(HTTPException) as exc_info:
            verify_token("Bearer invalid.jwt.token")
        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value.detail)
