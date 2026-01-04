"""Tests for authentication module."""

import pytest
from datetime import datetime, timedelta

from pressassist.core.auth import AuthManager
from pressassist.core.models import Role


class TestPasswordHashing:
    """Tests for password hashing."""

    def test_hash_password(self):
        """Test password hashing produces bcrypt hash."""
        auth = AuthManager()
        password = "test_password_123"
        hash_str = auth.hash_password(password)

        assert hash_str.startswith("$2b$")
        assert len(hash_str) == 60

    def test_verify_password_correct(self):
        """Test correct password verification."""
        auth = AuthManager()
        password = "correct_password"
        hash_str = auth.hash_password(password)

        assert auth.verify_password(password, hash_str) is True

    def test_verify_password_wrong(self):
        """Test wrong password verification."""
        auth = AuthManager()
        password = "correct_password"
        hash_str = auth.hash_password(password)

        assert auth.verify_password("wrong_password", hash_str) is False

    def test_verify_password_invalid_hash(self):
        """Test verification with invalid hash."""
        auth = AuthManager()

        assert auth.verify_password("password", "invalid_hash") is False
        assert auth.verify_password("password", "") is False


class TestSessionManagement:
    """Tests for session management."""

    def test_create_session(self):
        """Test session creation."""
        auth = AuthManager()
        session = auth.create_session(
            user_id="admin",
            role=Role.ADMIN,
            ip="127.0.0.1",
            user_agent="TestAgent",
        )

        assert session.user_id == "admin"
        assert session.role == Role.ADMIN
        assert session.ip == "127.0.0.1"
        assert len(session.session_id) > 0
        assert len(session.csrf_token) > 0

    def test_verify_session_valid(self):
        """Test verifying a valid session."""
        auth = AuthManager()
        session = auth.create_session(
            user_id="admin",
            role=Role.ADMIN,
            ip="127.0.0.1",
            user_agent="TestAgent",
        )

        verified = auth.verify_session(session.session_id)
        assert verified is not None
        assert verified.user_id == "admin"

    def test_verify_session_invalid(self):
        """Test verifying an invalid session."""
        auth = AuthManager()

        assert auth.verify_session("nonexistent") is None
        assert auth.verify_session("") is None
        assert auth.verify_session(None) is None

    def test_invalidate_session(self):
        """Test session invalidation."""
        auth = AuthManager()
        session = auth.create_session(
            user_id="admin",
            role=Role.ADMIN,
            ip="127.0.0.1",
            user_agent="TestAgent",
        )

        assert auth.invalidate_session(session.session_id) is True
        assert auth.verify_session(session.session_id) is None

    def test_invalidate_user_sessions(self):
        """Test invalidating all sessions for a user."""
        auth = AuthManager()

        # Create multiple sessions
        for _ in range(3):
            auth.create_session(
                user_id="admin",
                role=Role.ADMIN,
                ip="127.0.0.1",
                user_agent="TestAgent",
            )

        removed = auth.invalidate_user_sessions("admin")
        assert removed == 3
        assert auth.get_session_count("admin") == 0


class TestRateLimiting:
    """Tests for login rate limiting."""

    def test_rate_limit_under(self):
        """Test rate limit not exceeded."""
        auth = AuthManager(rate_limit_attempts=5)

        # Record 4 failed attempts
        for _ in range(4):
            auth.record_login_attempt("192.168.1.1", False)

        assert auth.check_rate_limit("192.168.1.1") is True

    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded."""
        auth = AuthManager(rate_limit_attempts=5)

        # Record 5 failed attempts
        for _ in range(5):
            auth.record_login_attempt("192.168.1.1", False)

        assert auth.check_rate_limit("192.168.1.1") is False

    def test_rate_limit_per_ip(self):
        """Test rate limiting is per-IP."""
        auth = AuthManager(rate_limit_attempts=3)

        # Exhaust rate limit for one IP
        for _ in range(3):
            auth.record_login_attempt("192.168.1.1", False)

        assert auth.check_rate_limit("192.168.1.1") is False
        assert auth.check_rate_limit("192.168.1.2") is True

    def test_successful_login_not_counted(self):
        """Test successful logins don't count toward rate limit."""
        auth = AuthManager(rate_limit_attempts=3)

        # Record successful attempts
        for _ in range(5):
            auth.record_login_attempt("192.168.1.1", True)

        assert auth.check_rate_limit("192.168.1.1") is True


class TestPermissions:
    """Tests for role-based permissions."""

    def test_admin_has_all_permissions(self):
        """Test admin role has all permissions."""
        auth = AuthManager()

        assert auth.check_permission(Role.ADMIN, "manage_users") is True
        assert auth.check_permission(Role.ADMIN, "edit_page") is True
        assert auth.check_permission(Role.ADMIN, "delete_file") is True

    def test_editor_permissions(self):
        """Test editor role has correct permissions."""
        auth = AuthManager()

        assert auth.check_permission(Role.EDITOR, "edit_page") is True
        assert auth.check_permission(Role.EDITOR, "upload_file") is True
        assert auth.check_permission(Role.EDITOR, "manage_users") is False
        assert auth.check_permission(Role.EDITOR, "delete_file") is False

    def test_viewer_permissions(self):
        """Test viewer role has limited permissions."""
        auth = AuthManager()

        assert auth.check_permission(Role.VIEWER, "view_public") is True
        assert auth.check_permission(Role.VIEWER, "edit_page") is False
        assert auth.check_permission(Role.VIEWER, "upload_file") is False


class TestCSRFValidation:
    """Tests for CSRF token validation."""

    def test_verify_csrf_valid(self):
        """Test valid CSRF token verification."""
        auth = AuthManager()
        session = auth.create_session(
            user_id="admin",
            role=Role.ADMIN,
            ip="127.0.0.1",
            user_agent="TestAgent",
        )

        assert auth.verify_csrf(session, session.csrf_token) is True

    def test_verify_csrf_invalid(self):
        """Test invalid CSRF token verification."""
        auth = AuthManager()
        session = auth.create_session(
            user_id="admin",
            role=Role.ADMIN,
            ip="127.0.0.1",
            user_agent="TestAgent",
        )

        assert auth.verify_csrf(session, "wrong_token") is False
        assert auth.verify_csrf(session, "") is False
        assert auth.verify_csrf(None, session.csrf_token) is False


class TestLoginSlugGeneration:
    """Tests for login slug generation."""

    def test_generate_login_slug_length(self):
        """Test login slug has correct length."""
        auth = AuthManager()
        slug = auth.generate_login_slug(32)

        assert len(slug) == 32

    def test_generate_login_slug_unique(self):
        """Test login slugs are unique."""
        auth = AuthManager()
        slugs = [auth.generate_login_slug() for _ in range(100)]

        assert len(set(slugs)) == 100  # All unique

    def test_generate_login_slug_url_safe(self):
        """Test login slug is URL-safe."""
        auth = AuthManager()
        slug = auth.generate_login_slug()

        # Should only contain alphanumeric, dash, underscore
        assert all(c.isalnum() or c in "-_" for c in slug)
