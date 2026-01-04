"""Persistent session and rate limit storage with file-based backend.

This module provides thread-safe, file-based storage for sessions and rate limiting
that works correctly with multiple workers (unlike in-memory storage).
"""

import fcntl
import json
import tempfile
import shutil
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .models import LoginAttempt, Role, Session


class SessionStoreError(Exception):
    """Session store error."""
    pass


class SessionStore:
    """File-based session storage with atomic writes and locking.

    Provides persistent session storage that works correctly with multiple
    uvicorn workers. Uses file locking to prevent corruption.
    """

    def __init__(self, session_file: Path):
        """Initialize session store.

        Args:
            session_file: Path to the JSON file for storing sessions.
        """
        self.session_file = session_file
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensure the session file exists with valid JSON."""
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.session_file.exists():
            self._atomic_write({})

    def _read(self) -> dict[str, dict]:
        """Read sessions from file with shared lock.

        Returns:
            Dictionary of session_id -> session data.
        """
        try:
            with open(self.session_file, "r", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return data
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _atomic_write(self, data: dict) -> None:
        """Write sessions to file atomically with exclusive lock.

        Args:
            data: Session data to write.
        """
        self.session_file.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first
        fd, temp_path = tempfile.mkstemp(
            dir=self.session_file.parent,
            suffix=".tmp",
        )
        try:
            with open(fd, "w", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Atomic rename
            shutil.move(temp_path, self.session_file)
        except Exception:
            Path(temp_path).unlink(missing_ok=True)
            raise

    def save_session(self, session: Session) -> None:
        """Save a session to storage.

        Args:
            session: Session object to save.
        """
        sessions = self._read()
        sessions[session.session_id] = {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "role": session.role.value,
            "ip": session.ip,
            "user_agent": session.user_agent,
            "csrf_token": session.csrf_token,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
        }
        self._atomic_write(sessions)

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Args:
            session_id: Session ID to look up.

        Returns:
            Session object if found and valid, None otherwise.
        """
        sessions = self._read()
        session_data = sessions.get(session_id)

        if not session_data:
            return None

        try:
            expires_at = datetime.fromisoformat(session_data["expires_at"])

            # Check if expired
            if datetime.now(timezone.utc) > expires_at:
                self.delete_session(session_id)
                return None

            return Session(
                session_id=session_data["session_id"],
                user_id=session_data["user_id"],
                role=Role(session_data["role"]),
                ip=session_data["ip"],
                user_agent=session_data["user_agent"],
                csrf_token=session_data["csrf_token"],
                created_at=datetime.fromisoformat(session_data["created_at"]),
                expires_at=expires_at,
            )
        except (KeyError, ValueError):
            # Invalid session data
            self.delete_session(session_id)
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session ID to delete.

        Returns:
            True if session was found and deleted.
        """
        sessions = self._read()
        if session_id in sessions:
            del sessions[session_id]
            self._atomic_write(sessions)
            return True
        return False

    def delete_user_sessions(self, user_id: str) -> int:
        """Delete all sessions for a user.

        Args:
            user_id: User ID whose sessions to delete.

        Returns:
            Number of sessions deleted.
        """
        sessions = self._read()
        to_delete = [
            sid for sid, data in sessions.items()
            if data.get("user_id") == user_id
        ]

        for sid in to_delete:
            del sessions[sid]

        if to_delete:
            self._atomic_write(sessions)

        return len(to_delete)

    def cleanup_expired(self) -> int:
        """Remove all expired sessions.

        Returns:
            Number of sessions removed.
        """
        sessions = self._read()
        now = datetime.now(timezone.utc)

        expired = []
        for session_id, data in sessions.items():
            try:
                expires_at = datetime.fromisoformat(data["expires_at"])
                if now > expires_at:
                    expired.append(session_id)
            except (KeyError, ValueError):
                expired.append(session_id)

        for sid in expired:
            del sessions[sid]

        if expired:
            self._atomic_write(sessions)

        return len(expired)

    def get_session_count(self, user_id: str | None = None) -> int:
        """Get count of active sessions.

        Args:
            user_id: Optional user to filter by.

        Returns:
            Number of active sessions.
        """
        sessions = self._read()
        if user_id:
            return sum(
                1 for data in sessions.values()
                if data.get("user_id") == user_id
            )
        return len(sessions)


class RateLimitStore:
    """File-based rate limit storage with atomic writes and locking.

    Provides persistent rate limiting that works correctly with multiple
    uvicorn workers.
    """

    def __init__(
        self,
        rate_limit_file: Path,
        max_attempts: int = 5,
        window_minutes: int = 15,
    ):
        """Initialize rate limit store.

        Args:
            rate_limit_file: Path to the JSON file for storing rate limit data.
            max_attempts: Maximum failed attempts allowed in window.
            window_minutes: Time window in minutes.
        """
        self.rate_limit_file = rate_limit_file
        self.max_attempts = max_attempts
        self.window = timedelta(minutes=window_minutes)
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensure the rate limit file exists with valid JSON."""
        self.rate_limit_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.rate_limit_file.exists():
            self._atomic_write({})

    def _read(self) -> dict[str, list[dict]]:
        """Read rate limit data from file.

        Returns:
            Dictionary of IP -> list of attempts.
        """
        try:
            with open(self.rate_limit_file, "r", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return data
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _atomic_write(self, data: dict) -> None:
        """Write rate limit data to file atomically.

        Args:
            data: Rate limit data to write.
        """
        self.rate_limit_file.parent.mkdir(parents=True, exist_ok=True)

        fd, temp_path = tempfile.mkstemp(
            dir=self.rate_limit_file.parent,
            suffix=".tmp",
        )
        try:
            with open(fd, "w", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            shutil.move(temp_path, self.rate_limit_file)
        except Exception:
            Path(temp_path).unlink(missing_ok=True)
            raise

    def record_attempt(
        self,
        ip: str,
        success: bool,
        user_agent: str | None = None
    ) -> None:
        """Record a login attempt.

        Args:
            ip: Client IP address.
            success: Whether login succeeded.
            user_agent: Optional user agent string.
        """
        data = self._read()

        if ip not in data:
            data[ip] = []

        data[ip].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": success,
            "user_agent": user_agent,
        })

        # Clean old attempts while we're here
        self._cleanup_ip(data, ip)

        self._atomic_write(data)

    def check_rate_limit(self, ip: str) -> bool:
        """Check if IP has exceeded rate limit.

        Args:
            ip: Client IP address.

        Returns:
            True if under limit (allowed), False if exceeded (blocked).
        """
        data = self._read()
        attempts = data.get(ip, [])

        now = datetime.now(timezone.utc)
        window_start = now - self.window

        # Count failed attempts in window
        failed_count = 0
        for attempt in attempts:
            try:
                timestamp = datetime.fromisoformat(attempt["timestamp"])
                if timestamp > window_start and not attempt.get("success", False):
                    failed_count += 1
            except (KeyError, ValueError):
                continue

        return failed_count < self.max_attempts

    def _cleanup_ip(self, data: dict, ip: str) -> None:
        """Remove old attempts for an IP.

        Args:
            data: Rate limit data dict.
            ip: IP to clean up.
        """
        if ip not in data:
            return

        window_start = datetime.now(timezone.utc) - self.window

        data[ip] = [
            attempt for attempt in data[ip]
            if self._is_recent(attempt, window_start)
        ]

        # Remove IP entry if empty
        if not data[ip]:
            del data[ip]

    def _is_recent(self, attempt: dict, window_start: datetime) -> bool:
        """Check if attempt is within the rate limit window.

        Args:
            attempt: Attempt dict.
            window_start: Start of rate limit window.

        Returns:
            True if attempt is recent.
        """
        try:
            timestamp = datetime.fromisoformat(attempt["timestamp"])
            return timestamp > window_start
        except (KeyError, ValueError):
            return False

    def cleanup_old_attempts(self) -> int:
        """Remove all old attempts outside the rate limit window.

        Returns:
            Number of IPs cleaned.
        """
        data = self._read()
        window_start = datetime.now(timezone.utc) - self.window

        cleaned = 0
        ips_to_remove = []

        for ip in list(data.keys()):
            original_count = len(data[ip])
            data[ip] = [
                attempt for attempt in data[ip]
                if self._is_recent(attempt, window_start)
            ]

            if len(data[ip]) < original_count:
                cleaned += 1

            if not data[ip]:
                ips_to_remove.append(ip)

        for ip in ips_to_remove:
            del data[ip]

        if cleaned or ips_to_remove:
            self._atomic_write(data)

        return cleaned

    def get_failed_count(self, ip: str) -> int:
        """Get count of failed attempts for an IP in the current window.

        Args:
            ip: Client IP address.

        Returns:
            Number of failed attempts.
        """
        data = self._read()
        attempts = data.get(ip, [])

        window_start = datetime.now(timezone.utc) - self.window

        return sum(
            1 for attempt in attempts
            if self._is_recent(attempt, window_start)
            and not attempt.get("success", False)
        )
