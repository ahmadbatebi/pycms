"""Tests for CSRF protection."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from pressassist.core.csrf import CSRFProtection


class TestCSRFTokenGeneration:
    """Tests for CSRF token generation."""

    def test_generate_token_length(self):
        """Test token has correct length."""
        csrf = CSRFProtection(secret_key="test_secret")
        token = csrf.generate_token()

        # URL-safe base64 encoding, 32 bytes
        assert len(token) >= 32

    def test_generate_token_unique(self):
        """Test tokens are unique."""
        csrf = CSRFProtection(secret_key="test_secret")
        tokens = [csrf.generate_token() for _ in range(100)]

        assert len(set(tokens)) == 100

    def test_generate_token_url_safe(self):
        """Test tokens are URL-safe."""
        csrf = CSRFProtection(secret_key="test_secret")
        token = csrf.generate_token()

        # URL-safe base64 characters only
        assert all(c.isalnum() or c in "-_" for c in token)


class TestCSRFValidation:
    """Tests for CSRF token validation."""

    def test_validate_matching_tokens(self):
        """Test matching tokens validate."""
        csrf = CSRFProtection(secret_key="test_secret")
        token = csrf.generate_token()

        assert csrf.validate_token(token, token) is True

    def test_validate_different_tokens(self):
        """Test different tokens don't validate."""
        csrf = CSRFProtection(secret_key="test_secret")
        token1 = csrf.generate_token()
        token2 = csrf.generate_token()

        assert csrf.validate_token(token1, token2) is False

    def test_validate_empty_request_token(self):
        """Test empty request token fails."""
        csrf = CSRFProtection(secret_key="test_secret")
        token = csrf.generate_token()

        assert csrf.validate_token("", token) is False
        assert csrf.validate_token(None, token) is False

    def test_validate_empty_cookie_token(self):
        """Test empty cookie token fails."""
        csrf = CSRFProtection(secret_key="test_secret")
        token = csrf.generate_token()

        assert csrf.validate_token(token, "") is False
        assert csrf.validate_token(token, None) is False


class TestShouldValidate:
    """Tests for request validation checking."""

    def test_validates_post_requests(self):
        """Test POST requests need validation."""
        csrf = CSRFProtection(secret_key="test_secret")
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/admin/save"

        assert csrf.should_validate(request) is True

    def test_validates_put_requests(self):
        """Test PUT requests need validation."""
        csrf = CSRFProtection(secret_key="test_secret")
        request = MagicMock()
        request.method = "PUT"
        request.url.path = "/admin/update"

        assert csrf.should_validate(request) is True

    def test_validates_delete_requests(self):
        """Test DELETE requests need validation."""
        csrf = CSRFProtection(secret_key="test_secret")
        request = MagicMock()
        request.method = "DELETE"
        request.url.path = "/admin/remove"

        assert csrf.should_validate(request) is True

    def test_skips_get_requests(self):
        """Test GET requests don't need validation."""
        csrf = CSRFProtection(secret_key="test_secret")
        request = MagicMock()
        request.method = "GET"
        request.url.path = "/page"

        assert csrf.should_validate(request) is False

    def test_skips_exempt_paths(self):
        """Test exempt paths are skipped."""
        csrf = CSRFProtection(secret_key="test_secret")
        csrf.EXEMPT_PATHS.add("/api/webhook")

        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/webhook"

        assert csrf.should_validate(request) is False


class TestTokenExtraction:
    """Tests for token extraction from requests."""

    def test_get_token_from_header(self):
        """Test token extraction from header."""
        csrf = CSRFProtection(secret_key="test_secret")
        token = csrf.generate_token()

        request = MagicMock()
        request.headers.get = lambda k: token if k == "X-CSRF-Token" else None

        assert csrf.get_token_from_request(request) == token

    def test_get_token_from_cookie(self):
        """Test token extraction from cookie."""
        csrf = CSRFProtection(secret_key="test_secret")
        token = csrf.generate_token()

        request = MagicMock()
        request.cookies.get = lambda k: token if k == "csrf_token" else None

        assert csrf.get_token_from_cookie(request) == token

    def test_missing_token_returns_none(self):
        """Test missing token returns None."""
        csrf = CSRFProtection(secret_key="test_secret")

        request = MagicMock()
        request.headers.get = lambda k: None
        request.cookies.get = lambda k: None

        assert csrf.get_token_from_request(request) is None
        assert csrf.get_token_from_cookie(request) is None
