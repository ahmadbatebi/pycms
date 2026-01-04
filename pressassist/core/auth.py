"""Authentication and authorization management."""

import secrets
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt as _bcrypt

from .models import LoginAttempt, Role, Session
from .session_store import RateLimitStore, SessionStore


class AuthError(Exception):
    """Authentication error."""

    pass


class RateLimitExceeded(AuthError):
    """Rate limit exceeded error."""

    pass


class AuthManager:
    """Manages authentication, sessions, and authorization.

    Features:
    - bcrypt password hashing
    - Secure session tokens
    - Rate limiting for login attempts (file-based for multi-worker support)
    - Role-based access control
    - Persistent sessions (file-based for multi-worker support)
    """

    # Permission matrix: role -> allowed actions
    PERMISSIONS: dict[Role, set[str]] = {
        Role.ADMIN: {
            "view_public",
            "view_hidden",
            "edit_page",
            "create_page",
            "delete_page",
            "edit_block",
            "upload_file",
            "delete_file",
            "change_theme",
            "manage_plugins",
            "change_settings",
            "manage_users",
            "view_audit",
            "backup",
            "restore",
        },
        Role.EDITOR: {
            "view_public",
            "view_hidden",
            "edit_page",
            "create_page",
            "delete_page",
            "edit_block",
            "upload_file",
        },
        Role.VIEWER: {
            "view_public",
        },
    }

    def __init__(
        self,
        bcrypt_rounds: int = 12,
        session_lifetime_hours: int = 4,
        rate_limit_attempts: int = 5,
        rate_limit_window_minutes: int = 15,
        session_store: SessionStore | None = None,
        rate_limit_store: RateLimitStore | None = None,
    ):
        """Initialize auth manager.

        Args:
            bcrypt_rounds: Cost factor for bcrypt (12 recommended).
            session_lifetime_hours: Session validity in hours.
            rate_limit_attempts: Max login attempts per window.
            rate_limit_window_minutes: Rate limit window in minutes.
            session_store: Optional persistent session store.
            rate_limit_store: Optional persistent rate limit store.
        """
        self.bcrypt_rounds = bcrypt_rounds
        self.session_lifetime = timedelta(hours=session_lifetime_hours)
        self.rate_limit_attempts = rate_limit_attempts
        self.rate_limit_window = timedelta(minutes=rate_limit_window_minutes)

        # Use file-based stores if provided, otherwise fallback to in-memory
        self._session_store = session_store
        self._rate_limit_store = rate_limit_store

        # Fallback in-memory stores (for CLI and testing)
        self._sessions: dict[str, Session] = {}
        self._login_attempts: dict[str, list[LoginAttempt]] = defaultdict(list)

    @property
    def use_persistent_storage(self) -> bool:
        """Check if using persistent file-based storage."""
        return self._session_store is not None

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: Plain text password.

        Returns:
            Bcrypt hash string.
        """
        password_bytes = password.encode("utf-8")
        salt = _bcrypt.gensalt(rounds=self.bcrypt_rounds)
        hashed = _bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")

    def verify_password(self, password: str, hash_str: str) -> bool:
        """Verify a password against a hash.

        Args:
            password: Plain text password.
            hash_str: Bcrypt hash to verify against.

        Returns:
            True if password matches.
        """
        try:
            password_bytes = password.encode("utf-8")
            hash_bytes = hash_str.encode("utf-8")
            return _bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception:
            return False

    def generate_login_slug(self, length: int = 32) -> str:
        """Generate a cryptographically random login slug.

        Args:
            length: Length of the slug.

        Returns:
            Random URL-safe string.
        """
        return secrets.token_urlsafe(length)[:length]

    def generate_password(self, length: int = 16) -> str:
        """Generate a random password.

        Args:
            length: Length of password.

        Returns:
            Random password string.
        """
        # Use a mix of characters for better readability
        alphabet = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def check_rate_limit(self, ip: str) -> bool:
        """Check if IP has exceeded rate limit.

        Args:
            ip: Client IP address.

        Returns:
            True if under limit (allowed), False if exceeded (blocked).
        """
        # Use file-based store if available
        if self._rate_limit_store:
            return self._rate_limit_store.check_rate_limit(ip)

        # Fallback to in-memory
        now = datetime.now(timezone.utc)
        window_start = now - self.rate_limit_window

        # Clean old attempts
        self._login_attempts[ip] = [
            attempt
            for attempt in self._login_attempts[ip]
            if attempt.timestamp > window_start
        ]

        # Count failed attempts in window
        failed_count = sum(
            1 for attempt in self._login_attempts[ip] if not attempt.success
        )

        return failed_count < self.rate_limit_attempts

    def record_login_attempt(
        self, ip: str, success: bool, user_agent: str | None = None
    ) -> None:
        """Record a login attempt for rate limiting.

        Args:
            ip: Client IP address.
            success: Whether login succeeded.
            user_agent: Optional user agent string.
        """
        # Use file-based store if available
        if self._rate_limit_store:
            self._rate_limit_store.record_attempt(ip, success, user_agent)
            return

        # Fallback to in-memory
        self._login_attempts[ip].append(
            LoginAttempt(
                ip=ip,
                success=success,
                user_agent=user_agent,
            )
        )

    def create_session(
        self,
        user_id: str,
        role: Role,
        ip: str,
        user_agent: str,
    ) -> Session:
        """Create a new session for authenticated user.

        Args:
            user_id: Username/ID.
            role: User's role.
            ip: Client IP address.
            user_agent: Client user agent.

        Returns:
            New Session object.
        """
        session_id = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)

        session = Session(
            session_id=session_id,
            user_id=user_id,
            role=role,
            ip=ip,
            user_agent=user_agent,
            csrf_token=csrf_token,
            created_at=now,
            expires_at=now + self.session_lifetime,
        )

        # Use file-based store if available
        if self._session_store:
            self._session_store.save_session(session)
        else:
            self._sessions[session_id] = session

        return session

    def verify_session(self, session_id: str) -> Optional[Session]:
        """Verify a session token.

        Args:
            session_id: Session token to verify.

        Returns:
            Session if valid, None otherwise.
        """
        if not session_id:
            return None

        # Use file-based store if available
        if self._session_store:
            return self._session_store.get_session(session_id)

        # Fallback to in-memory
        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]

        # Check expiration
        if datetime.now(timezone.utc) > session.expires_at:
            del self._sessions[session_id]
            return None

        return session

    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate/logout a session.

        Args:
            session_id: Session to invalidate.

        Returns:
            True if session was found and removed.
        """
        # Use file-based store if available
        if self._session_store:
            return self._session_store.delete_session(session_id)

        # Fallback to in-memory
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def invalidate_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user.

        Args:
            user_id: User whose sessions to invalidate.

        Returns:
            Number of sessions invalidated.
        """
        # Use file-based store if available
        if self._session_store:
            return self._session_store.delete_user_sessions(user_id)

        # Fallback to in-memory
        to_remove = [
            sid for sid, session in self._sessions.items() if session.user_id == user_id
        ]
        for sid in to_remove:
            del self._sessions[sid]
        return len(to_remove)

    def check_permission(self, role: Role, action: str) -> bool:
        """Check if a role has permission for an action.

        Args:
            role: User's role.
            action: Action to check.

        Returns:
            True if permitted.
        """
        if role not in self.PERMISSIONS:
            return False
        return action in self.PERMISSIONS[role]

    def verify_csrf(self, session: Session, token: str) -> bool:
        """Verify CSRF token for a session.

        Args:
            session: User's session.
            token: CSRF token to verify.

        Returns:
            True if token is valid.
        """
        if not token or not session:
            return False
        # Use constant-time comparison
        return secrets.compare_digest(session.csrf_token, token)

    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions.

        Returns:
            Number of sessions removed.
        """
        # Use file-based store if available
        if self._session_store:
            return self._session_store.cleanup_expired()

        # Fallback to in-memory
        now = datetime.now(timezone.utc)
        expired = [
            sid for sid, session in self._sessions.items() if session.expires_at < now
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    def cleanup_rate_limits(self) -> int:
        """Remove old rate limit entries.

        Returns:
            Number of IPs cleaned.
        """
        if self._rate_limit_store:
            return self._rate_limit_store.cleanup_old_attempts()
        return 0

    def get_session_count(self, user_id: str | None = None) -> int:
        """Get count of active sessions.

        Args:
            user_id: Optional user to filter by.

        Returns:
            Number of active sessions.
        """
        # Use file-based store if available
        if self._session_store:
            return self._session_store.get_session_count(user_id)

        # Fallback to in-memory
        if user_id:
            return sum(1 for s in self._sessions.values() if s.user_id == user_id)
        return len(self._sessions)
