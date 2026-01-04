"""JSON flat-file storage with atomic writes and locking."""

import fcntl
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import (
    Block,
    ContentFormat,
    DatabaseSchema,
    MenuItem,
    Page,
    SiteConfig,
    User,
    Visibility,
)


class StorageError(Exception):
    """Base exception for storage errors."""

    pass


class Storage:
    """Thread-safe JSON database with atomic writes.

    Uses file locking to prevent corruption from concurrent access.
    Writes are atomic: write to temp file, then rename.
    """

    def __init__(self, db_path: Path):
        """Initialize storage with database path.

        Args:
            db_path: Path to the JSON database file.
        """
        self.db_path = db_path
        self._data: dict | None = None
        self._lock_path = db_path.with_suffix(".lock")

    @property
    def exists(self) -> bool:
        """Check if database file exists."""
        return self.db_path.exists()

    def load(self) -> dict:
        """Load database from file.

        Returns:
            Database contents as dictionary.

        Raises:
            StorageError: If file cannot be read or parsed.
        """
        if not self.db_path.exists():
            raise StorageError(f"Database file not found: {self.db_path}")

        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                # Acquire shared lock for reading
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    self._data = json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            return self._data
        except json.JSONDecodeError as e:
            raise StorageError(f"Invalid JSON in database: {e}")
        except OSError as e:
            raise StorageError(f"Cannot read database: {e}")

    def save(self, data: dict | None = None) -> None:
        """Save database to file atomically.

        Args:
            data: Data to save. If None, saves cached data.

        Raises:
            StorageError: If save fails.
        """
        if data is not None:
            self._data = data
        elif self._data is None:
            raise StorageError("No data to save")

        # Update last modified timestamp
        if "config" in self._data:
            self._data["config"]["last_modified"] = datetime.now(timezone.utc).isoformat()

        try:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to temporary file first (atomic write pattern)
            fd, temp_path = tempfile.mkstemp(
                dir=self.db_path.parent,
                suffix=".tmp",
            )
            try:
                with open(fd, "w", encoding="utf-8") as f:
                    # Acquire exclusive lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        json.dump(
                            self._data,
                            f,
                            indent=2,
                            ensure_ascii=False,
                            default=str,
                        )
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

                # Atomic rename
                shutil.move(temp_path, self.db_path)
            except Exception:
                # Clean up temp file on error
                Path(temp_path).unlink(missing_ok=True)
                raise
        except OSError as e:
            raise StorageError(f"Cannot save database: {e}")

    def get(self, path: str, default: Any = None) -> Any:
        """Get value from database using dot notation.

        Args:
            path: Dot-separated path (e.g., "config.site_title")
            default: Default value if path not found.

        Returns:
            Value at path or default.
        """
        if self._data is None:
            self.load()

        keys = path.split(".")
        value = self._data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, path: str, value: Any) -> None:
        """Set value in database using dot notation.

        Args:
            path: Dot-separated path (e.g., "config.site_title")
            value: Value to set.
        """
        if self._data is None:
            self.load()

        keys = path.split(".")
        target = self._data
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value
        self.save()

    def delete(self, path: str) -> bool:
        """Delete value from database using dot notation.

        Args:
            path: Dot-separated path to delete.

        Returns:
            True if deleted, False if not found.
        """
        if self._data is None:
            self.load()

        keys = path.split(".")
        target = self._data
        for key in keys[:-1]:
            if key not in target:
                return False
            target = target[key]

        if keys[-1] in target:
            del target[keys[-1]]
            self.save()
            return True
        return False

    def initialize(self, login_slug: str, admin_password_hash: str) -> dict:
        """Initialize a new database with default content.

        Args:
            login_slug: Secret login URL slug.
            admin_password_hash: Bcrypt hash of admin password.

        Returns:
            The initialized database.
        """
        now = datetime.now(timezone.utc).isoformat()

        self._data = {
            "config": {
                "site_title": "My Website",
                "site_lang": "en",
                "admin_lang": "en",
                "theme": "default",
                "default_page": "home",
                "login_slug": login_slug,
                "force_https": True,
                "disabled_plugins": [],
                "last_modified": now,
            },
            "users": {
                "admin": {
                    "username": "admin",
                    "password_hash": admin_password_hash,
                    "role": "admin",
                    "created_at": now,
                    "last_login": None,
                }
            },
            "pages": {
                "home": {
                    "slug": "home",
                    "title": "Home",
                    "content": "# Welcome to Your Website\n\nThis is your homepage. "
                    "Edit this content from the admin panel.\n\n"
                    "## Getting Started\n\n"
                    "1. Log in using your secret login URL\n"
                    "2. Navigate to the admin panel\n"
                    "3. Start creating content!",
                    "content_format": "markdown",
                    "description": "Welcome to my website",
                    "keywords": "home, welcome",
                    "visibility": "show",
                    "subpages": {},
                    "created_at": now,
                    "modified_at": now,
                    "modified_by": "system",
                },
                "about": {
                    "slug": "about",
                    "title": "About",
                    "content": "# About Us\n\nTell visitors about yourself or your site.",
                    "content_format": "markdown",
                    "description": "About this website",
                    "keywords": "about",
                    "visibility": "show",
                    "subpages": {},
                    "created_at": now,
                    "modified_at": now,
                    "modified_by": "system",
                },
                "404": {
                    "slug": "404",
                    "title": "Page Not Found",
                    "content": "# 404 - Page Not Found\n\n"
                    "The page you're looking for doesn't exist.\n\n"
                    "[Go back to homepage](/)",
                    "content_format": "markdown",
                    "description": "Page not found",
                    "keywords": "404, not found",
                    "visibility": "system",
                    "subpages": {},
                    "created_at": now,
                    "modified_at": now,
                    "modified_by": "system",
                },
            },
            "blocks": {
                "header": {
                    "name": "header",
                    "content": "My Website",
                    "content_format": "markdown",
                },
                "footer": {
                    "name": "footer",
                    "content": f"Copyright {datetime.now(timezone.utc).year}",
                    "content_format": "markdown",
                },
                "sidebar": {
                    "name": "sidebar",
                    "content": "## About\n\nThis is the sidebar. "
                    "It appears on every page.",
                    "content_format": "markdown",
                },
            },
            "menu_items": [
                {"name": "Home", "slug": "home", "visibility": "show", "order": 0, "subpages": []},
                {"name": "About", "slug": "about", "visibility": "show", "order": 1, "subpages": []},
            ],
            "uploads": {},
        }

        self.save()
        return self._data

    def backup(self, backup_dir: Path) -> Path:
        """Create a backup of the database.

        Args:
            backup_dir: Directory to store backup.

        Returns:
            Path to backup file.
        """
        if self._data is None:
            self.load()

        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"db_backup_{timestamp}.json"

        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False, default=str)

        return backup_path

    def restore(self, backup_path: Path) -> None:
        """Restore database from backup.

        Args:
            backup_path: Path to backup file.

        Raises:
            StorageError: If backup file is invalid.
        """
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Basic validation
            required_keys = {"config", "pages", "blocks"}
            if not required_keys.issubset(data.keys()):
                raise StorageError("Invalid backup: missing required keys")

            self._data = data
            self.save()
        except json.JSONDecodeError as e:
            raise StorageError(f"Invalid backup JSON: {e}")
        except OSError as e:
            raise StorageError(f"Cannot read backup: {e}")
