"""Audit logging for security events."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import AuditEvent


class AuditLogger:
    """Append-only audit log for security events.

    Logs are stored in JSON Lines format for easy parsing.
    Each line is a complete JSON object.
    """

    def __init__(self, log_path: Path, max_age_days: int = 90):
        """Initialize audit logger.

        Args:
            log_path: Path to audit log file.
            max_age_days: Maximum age of log entries before cleanup.
        """
        self.log_path = log_path
        self.max_age_days = max_age_days

    def log(
        self,
        event: str,
        actor: str,
        ip: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log an audit event.

        Args:
            event: Event type (e.g., "login_success", "page_edit").
            actor: Username or identifier of who performed action.
            ip: Client IP address.
            user_agent: Client user agent.
            details: Additional event-specific details.
        """
        entry = AuditEvent(
            timestamp=datetime.now(timezone.utc),
            event=event,
            actor=actor,
            ip=ip,
            user_agent=user_agent,
            details=details or {},
        )

        # Ensure directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Append to log file (JSON Lines format)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.model_dump(), default=str) + "\n")

    def log_login_success(
        self,
        username: str,
        ip: str,
        user_agent: str | None = None,
    ) -> None:
        """Log successful login.

        Args:
            username: User who logged in.
            ip: Client IP.
            user_agent: Client user agent.
        """
        self.log(
            event="login_success",
            actor=username,
            ip=ip,
            user_agent=user_agent,
        )

    def log_login_failed(
        self,
        username: str,
        ip: str,
        user_agent: str | None = None,
        reason: str = "invalid_password",
    ) -> None:
        """Log failed login attempt.

        Args:
            username: Attempted username.
            ip: Client IP.
            user_agent: Client user agent.
            reason: Failure reason.
        """
        self.log(
            event="login_failed",
            actor=username,
            ip=ip,
            user_agent=user_agent,
            details={"reason": reason},
        )

    def log_logout(
        self,
        username: str,
        ip: str | None = None,
    ) -> None:
        """Log logout.

        Args:
            username: User who logged out.
            ip: Client IP.
        """
        self.log(
            event="logout",
            actor=username,
            ip=ip,
        )

    def log_page_change(
        self,
        action: str,
        page_slug: str,
        actor: str,
        ip: str | None = None,
    ) -> None:
        """Log page content change.

        Args:
            action: Action type (create, edit, delete).
            page_slug: Page slug.
            actor: User who made change.
            ip: Client IP.
        """
        self.log(
            event=f"page_{action}",
            actor=actor,
            ip=ip,
            details={"page": page_slug},
        )

    def log_file_upload(
        self,
        filename: str,
        uuid: str,
        actor: str,
        ip: str | None = None,
    ) -> None:
        """Log file upload.

        Args:
            filename: Original filename.
            uuid: Assigned UUID.
            actor: User who uploaded.
            ip: Client IP.
        """
        self.log(
            event="file_upload",
            actor=actor,
            ip=ip,
            details={"filename": filename, "uuid": uuid},
        )

    def log_file_delete(
        self,
        uuid: str,
        actor: str,
        ip: str | None = None,
    ) -> None:
        """Log file deletion.

        Args:
            uuid: File UUID.
            actor: User who deleted.
            ip: Client IP.
        """
        self.log(
            event="file_delete",
            actor=actor,
            ip=ip,
            details={"uuid": uuid},
        )

    def log_settings_change(
        self,
        setting: str,
        actor: str,
        ip: str | None = None,
    ) -> None:
        """Log settings change.

        Args:
            setting: Setting that was changed.
            actor: User who made change.
            ip: Client IP.
        """
        self.log(
            event="settings_change",
            actor=actor,
            ip=ip,
            details={"setting": setting},
        )

    def log_plugin_change(
        self,
        action: str,
        plugin: str,
        actor: str,
        ip: str | None = None,
    ) -> None:
        """Log plugin enable/disable.

        Args:
            action: Action (enable, disable).
            plugin: Plugin name.
            actor: User who made change.
            ip: Client IP.
        """
        self.log(
            event=f"plugin_{action}",
            actor=actor,
            ip=ip,
            details={"plugin": plugin},
        )

    def log_backup(
        self,
        action: str,
        actor: str,
        filename: str | None = None,
        ip: str | None = None,
    ) -> None:
        """Log backup/restore action.

        Args:
            action: Action (create, restore).
            actor: User who performed action.
            filename: Backup filename.
            ip: Client IP.
        """
        self.log(
            event=f"backup_{action}",
            actor=actor,
            ip=ip,
            details={"filename": filename} if filename else {},
        )

    def read_recent(self, limit: int = 100) -> list[dict]:
        """Read recent audit log entries using optimized tail-like approach.

        Args:
            limit: Maximum entries to return.

        Returns:
            List of recent log entries (newest first).
        """
        if not self.log_path.exists():
            return []

        try:
            # Use optimized tail-like reading for large files
            file_size = self.log_path.stat().st_size

            # For small files, read entire file
            if file_size < 1024 * 1024:  # Less than 1MB
                return self._read_recent_full(limit)

            # For larger files, read from end
            return self._read_recent_tail(limit, file_size)
        except OSError:
            return []

    def _read_recent_full(self, limit: int) -> list[dict]:
        """Read recent entries by reading entire file (for small files).

        Args:
            limit: Maximum entries to return.

        Returns:
            List of recent log entries (newest first).
        """
        entries = []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except OSError:
            return []

        # Return most recent first
        return list(reversed(entries[-limit:]))

    def _read_recent_tail(self, limit: int, file_size: int) -> list[dict]:
        """Read recent entries from file tail (for large files).

        Args:
            limit: Maximum entries to return.
            file_size: Size of the file in bytes.

        Returns:
            List of recent log entries (newest first).
        """
        # Estimate bytes needed (assume avg 500 bytes per entry)
        chunk_size = min(file_size, max(8192, limit * 500))

        try:
            with open(self.log_path, "rb") as f:
                # Seek to near end
                f.seek(max(0, file_size - chunk_size))

                # Skip partial first line if not at start
                if f.tell() > 0:
                    f.readline()

                # Read remaining content
                content = f.read().decode("utf-8", errors="replace")

            lines = content.strip().split("\n")
            entries = []

            for line in reversed(lines[-limit:]):
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

                if len(entries) >= limit:
                    break

            return entries
        except OSError:
            return []

    def cleanup_old_entries(self) -> int:
        """Remove entries older than max_age_days.

        Returns:
            Number of entries removed.
        """
        if not self.log_path.exists():
            return 0

        cutoff = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        from datetime import timedelta

        cutoff -= timedelta(days=self.max_age_days)

        kept = []
        removed = 0

        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        timestamp = datetime.fromisoformat(
                            entry.get("timestamp", "").replace("Z", "+00:00")
                        )
                        if timestamp >= cutoff:
                            kept.append(line)
                        else:
                            removed += 1
                    except (json.JSONDecodeError, ValueError):
                        kept.append(line)

            # Rewrite file with kept entries
            with open(self.log_path, "w", encoding="utf-8") as f:
                for line in kept:
                    f.write(line + "\n")

        except OSError:
            pass

        return removed
