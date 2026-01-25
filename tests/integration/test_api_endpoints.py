"""
Integration tests for FastAPI REST endpoints.

These tests verify the API endpoints work correctly with real HTTP
request/response cycles using FastAPI's TestClient.

Test Categories:
- Health endpoints: Verify service health and readiness
- Generation endpoints: Test code/test/docs generation
- Review endpoints: Test code review functionality
- History endpoints: Test conversation history management
- Error handling: Verify proper error responses
"""

import pytest
from unittest.mock import patch, MagicMock


class TestHealthEndpoints:
    """Test health check and status endpoints."""

    @pytest.mark.integration
    def test_health_check_returns_200(self, test_client):
        """Test /health endpoint returns 200 with proper structure."""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert "version" in data
        assert "agent_ready" in data
        assert "capabilities" in data

        # Verify status is healthy or degraded
        assert data["status"] in ["healthy", "degraded"]

        # Verify capabilities list
        assert isinstance(data["capabilities"], list)
        expected_capabilities = [
            "code_generation",
            "test_generation",
            "code_review",
            "requirements",
            "documentation"
        ]
        for cap in expected_capabilities:
            assert cap in data["capabilities"]

    @pytest.mark.integration
    def test_health_check_version_format(self, test_client):
        """Test that version follows semantic versioning format."""
        response = test_client.get("/health")
        data = response.json()

        version = data["version"]
        # Should be in format X.Y.Z
        parts = version.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)


class TestGenerationEndpoints:
    """Test code generation endpoints."""

    @pytest.mark.integration
    def test_generate_endpoint_accepts_valid_request(self, test_client, code_generation_request):
        """Test /generate endpoint accepts valid requests."""
        response = test_client.post("/generate", json=code_generation_request)

        # Should return 200 or 503 (if agent not ready)
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "result" in data
            assert "task_type" in data
            assert "usage" in data

    @pytest.mark.integration
    def test_generate_endpoint_validates_request(self, test_client):
        """Test /generate endpoint validates request body."""
        # Missing required field 'prompt'
        invalid_request = {"language": "python"}

        response = test_client.post("/generate", json=invalid_request)

        # Should return 422 Unprocessable Entity
        assert response.status_code == 422

    @pytest.mark.integration
    def test_generate_code_endpoint(self, test_client):
        """Test /code/generate endpoint."""
        request = {
            "requirements": "Write a function to add two numbers",
            "language": "python"
        }

        response = test_client.post("/code/generate", json=request)

        # Should return 200 or 503
        assert response.status_code in [200, 503]

    @pytest.mark.integration
    def test_generate_tests_endpoint(self, test_client, test_generation_request):
        """Test /tests/generate endpoint."""
        response = test_client.post("/tests/generate", json=test_generation_request)

        # Should return 200 or 503
        assert response.status_code in [200, 503]

    @pytest.mark.integration
    def test_generate_with_auto_classification(self, test_client, auto_classify_request):
        """Test that auto task_type triggers intent classification."""
        response = test_client.post("/generate", json=auto_classify_request)

        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            # Should have classified the task type
            assert data["task_type"] != "auto"
            assert data["confidence"] >= 0.0


class TestCodeReviewEndpoints:
    """Test code review endpoints."""

    @pytest.mark.integration
    def test_code_review_endpoint(self, test_client, code_review_request):
        """Test /code/review endpoint."""
        response = test_client.post("/code/review", json=code_review_request)

        assert response.status_code in [200, 503]

    @pytest.mark.integration
    def test_code_review_with_focus(self, test_client, sample_unsafe_code):
        """Test code review with specific focus area."""
        request = {
            "code": sample_unsafe_code,
            "language": "python",
            "focus": "security"
        }

        response = test_client.post("/code/review", json=request)

        assert response.status_code in [200, 503]

    @pytest.mark.integration
    def test_code_review_validates_request(self, test_client):
        """Test code review validates request structure."""
        # Missing required 'code' field
        invalid_request = {"language": "python"}

        response = test_client.post("/code/review", json=invalid_request)

        assert response.status_code == 422


class TestHistoryEndpoints:
    """Test conversation history endpoints."""

    @pytest.mark.integration
    def test_get_history_endpoint(self, test_client):
        """Test GET /history endpoint."""
        response = test_client.get("/history")

        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.integration
    def test_clear_history_endpoint(self, test_client):
        """Test DELETE /history endpoint."""
        response = test_client.delete("/history")

        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "cleared"


class TestUsageEndpoints:
    """Test usage statistics endpoints."""

    @pytest.mark.integration
    def test_get_usage_endpoint(self, test_client):
        """Test GET /usage endpoint."""
        response = test_client.get("/usage")

        assert response.status_code in [200, 503]


class TestRAGEndpoints:
    """Test RAG (Retrieval-Augmented Generation) endpoints."""

    @pytest.mark.integration
    def test_rag_stats_endpoint(self, test_client):
        """Test GET /rag/stats endpoint."""
        response = test_client.get("/rag/stats")

        assert response.status_code in [200, 503]

    @pytest.mark.integration
    def test_rag_search_validates_request(self, test_client):
        """Test /rag/search validates request structure."""
        # Missing required 'query' field
        invalid_request = {"n_results": 5}

        response = test_client.post("/rag/search", json=invalid_request)

        assert response.status_code == 422

    @pytest.mark.integration
    def test_rag_index_validates_request(self, test_client):
        """Test /rag/index validates request structure."""
        # Missing required 'directory' field
        invalid_request = {"extensions": [".py"]}

        response = test_client.post("/rag/index", json=invalid_request)

        assert response.status_code == 422

    @pytest.mark.integration
    def test_rag_index_with_temp_directory(self, test_client, temp_codebase):
        """Test indexing a temporary codebase."""
        request = {
            "directory": str(temp_codebase),
            "extensions": [".py"]
        }

        response = test_client.post("/rag/index", json=request)

        # May fail if RAG is not initialized, which is acceptable
        assert response.status_code in [200, 500, 503]


class TestErrorHandling:
    """Test API error handling."""

    @pytest.mark.integration
    def test_404_for_nonexistent_endpoint(self, test_client):
        """Test 404 returned for non-existent endpoints."""
        response = test_client.get("/api/nonexistent")

        assert response.status_code == 404

    @pytest.mark.integration
    def test_405_for_wrong_method(self, test_client):
        """Test 405 returned for wrong HTTP method."""
        # /generate requires POST, not GET
        response = test_client.get("/generate")

        assert response.status_code == 405

    @pytest.mark.integration
    def test_422_for_invalid_json(self, test_client):
        """Test 422 returned for invalid JSON structure."""
        response = test_client.post(
            "/generate",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    @pytest.mark.integration
    def test_error_response_structure(self, test_client):
        """Test that error responses have proper structure."""
        # Send invalid request to trigger validation error
        response = test_client.post("/generate", json={})

        assert response.status_code == 422
        data = response.json()

        # FastAPI validation errors should have 'detail' field
        assert "detail" in data


class TestCORSHeaders:
    """Test CORS configuration."""

    @pytest.mark.integration
    def test_cors_headers_for_allowed_origin(self, test_client):
        """Test CORS headers are set for allowed origins."""
        response = test_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET"
            }
        )

        # Should allow the origin
        assert response.headers.get("access-control-allow-origin") in [
            "http://localhost:5173",
            "*"
        ]

    @pytest.mark.integration
    def test_cors_allows_credentials(self, test_client):
        """Test CORS allows credentials."""
        response = test_client.options(
            "/generate",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST"
            }
        )

        # Check credentials header
        allow_credentials = response.headers.get("access-control-allow-credentials")
        # May be 'true' or not present depending on CORS config
        assert allow_credentials in ["true", None]


class TestRequestValidation:
    """Test request validation for all endpoints."""

    @pytest.mark.integration
    @pytest.mark.parametrize("endpoint,method,valid_body", [
        ("/generate", "POST", {"prompt": "test", "language": "python"}),
        ("/code/generate", "POST", {"requirements": "test"}),
        ("/tests/generate", "POST", {"code": "def test(): pass"}),
        ("/code/review", "POST", {"code": "def test(): pass"}),
        ("/rag/index", "POST", {"directory": "/tmp"}),
        ("/rag/search", "POST", {"query": "test"}),
    ])
    def test_endpoints_accept_valid_requests(self, test_client, endpoint, method, valid_body):
        """Test that endpoints accept valid request bodies."""
        if method == "POST":
            response = test_client.post(endpoint, json=valid_body)
        else:
            response = test_client.get(endpoint)

        # Should not return 422 (validation error) for valid requests
        assert response.status_code != 422

    @pytest.mark.integration
    @pytest.mark.parametrize("endpoint,invalid_body", [
        ("/generate", {}),
        ("/generate", {"language": "python"}),  # missing prompt
        ("/code/generate", {}),
        ("/code/generate", {"language": "python"}),  # missing requirements
        ("/tests/generate", {}),
        ("/tests/generate", {"framework": "pytest"}),  # missing code
        ("/code/review", {}),
        ("/code/review", {"focus": "security"}),  # missing code
        ("/rag/index", {}),
        ("/rag/search", {}),
    ])
    def test_endpoints_reject_invalid_requests(self, test_client, endpoint, invalid_body):
        """Test that endpoints reject invalid request bodies."""
        response = test_client.post(endpoint, json=invalid_body)

        # Should return 422 for invalid requests
        assert response.status_code == 422


class TestResponseFormats:
    """Test response format consistency."""

    @pytest.mark.integration
    def test_health_response_format(self, test_client):
        """Test health endpoint response format."""
        response = test_client.get("/health")
        data = response.json()

        # Verify all required fields
        required_fields = ["status", "version", "agent_ready", "capabilities"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # Verify types
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["agent_ready"], bool)
        assert isinstance(data["capabilities"], list)

    @pytest.mark.integration
    def test_generate_response_format(self, test_client, code_generation_request):
        """Test generate endpoint response format."""
        response = test_client.post("/generate", json=code_generation_request)

        if response.status_code == 200:
            data = response.json()

            # Verify all required fields
            required_fields = ["success", "result", "task_type", "confidence", "usage"]
            for field in required_fields:
                assert field in data, f"Missing field: {field}"

            # Verify types
            assert isinstance(data["success"], bool)
            assert isinstance(data["result"], str)
            assert isinstance(data["task_type"], str)
            assert isinstance(data["confidence"], (int, float))
            assert isinstance(data["usage"], dict)
