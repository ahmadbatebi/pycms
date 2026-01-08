"""Application configuration management."""

import os
import secrets
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """Application-wide configuration.

    These settings come from environment variables or defaults.
    Database settings are stored separately in the JSON file.
    """

    # Paths
    base_dir: Path = Field(default_factory=lambda: Path.cwd())
    data_dir: Path = Field(default=None)
    themes_dir: Path = Field(default=None)
    plugins_dir: Path = Field(default=None)

    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    workers: int = 1

    # Security
    secret_key: str = Field(default_factory=lambda: secrets.token_hex(32))
    session_lifetime_hours: int = 4
    rate_limit_attempts: int = 5
    rate_limit_window_minutes: int = 15
    password_min_length: int = 12
    bcrypt_rounds: int = 12

    # Uploads
    max_upload_size_mb: int = 5
    allowed_upload_extensions: set[str] = Field(
        default_factory=lambda: {"png", "jpg", "jpeg", "webp", "gif"}
    )

    # Content
    allow_html_content: bool = True  # WYSIWYG editor produces HTML

    def __init__(self, **data):
        super().__init__(**data)
        # Set derived paths if not provided
        if self.data_dir is None:
            self.data_dir = self.base_dir / "data"
        if self.themes_dir is None:
            self.themes_dir = self.base_dir / "themes"
        if self.plugins_dir is None:
            self.plugins_dir = self.base_dir / "plugins"

    @property
    def db_path(self) -> Path:
        """Path to the JSON database file."""
        return self.data_dir / "db.json"

    @property
    def uploads_dir(self) -> Path:
        """Path to uploads directory."""
        return self.data_dir / "uploads"

    @property
    def backups_dir(self) -> Path:
        """Path to backups directory."""
        return self.data_dir / "backups"

    @property
    def audit_log_path(self) -> Path:
        """Path to audit log file."""
        return self.data_dir / "audit.log"

    @property
    def sessions_file(self) -> Path:
        """Path to sessions storage file."""
        return self.data_dir / "sessions.json"

    @property
    def rate_limit_file(self) -> Path:
        """Path to rate limit storage file."""
        return self.data_dir / "rate_limits.json"

    @property
    def max_upload_size_bytes(self) -> int:
        """Maximum upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        self.themes_dir.mkdir(parents=True, exist_ok=True)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls, base_dir: Path | None = None) -> "AppConfig":
        """Create configuration from environment variables.

        Args:
            base_dir: Base directory for the application.

        Returns:
            AppConfig instance.

        Raises:
            ValueError: If environment variable values are invalid.
        """
        if base_dir is None:
            base_dir = Path(os.getenv("PRESSASSIST_BASE_DIR", Path.cwd()))

        # Parse and validate environment variables
        def get_int_env(name: str, default: int, min_val: int, max_val: int) -> int:
            """Parse and validate integer environment variable."""
            value_str = os.getenv(name, str(default))
            try:
                value = int(value_str)
            except ValueError:
                raise ValueError(f"{name} must be an integer, got: {value_str}")
            if value < min_val or value > max_val:
                raise ValueError(f"{name} must be between {min_val} and {max_val}, got: {value}")
            return value

        port = get_int_env("PRESSASSIST_PORT", 8000, 1, 65535)
        workers = get_int_env("PRESSASSIST_WORKERS", 1, 1, 32)
        session_lifetime_hours = get_int_env("PRESSASSIST_SESSION_HOURS", 4, 1, 168)
        rate_limit_attempts = get_int_env("PRESSASSIST_RATE_LIMIT_ATTEMPTS", 5, 1, 100)
        rate_limit_window_minutes = get_int_env("PRESSASSIST_RATE_LIMIT_WINDOW", 15, 1, 1440)
        password_min_length = get_int_env("PRESSASSIST_PASSWORD_MIN_LENGTH", 12, 8, 128)
        max_upload_size_mb = get_int_env("PRESSASSIST_MAX_UPLOAD_MB", 5, 1, 100)

        return cls(
            base_dir=base_dir,
            host=os.getenv("PRESSASSIST_HOST", "127.0.0.1"),
            port=port,
            debug=os.getenv("PRESSASSIST_DEBUG", "false").lower() == "true",
            workers=workers,
            secret_key=os.getenv("PRESSASSIST_SECRET_KEY", secrets.token_hex(32)),
            session_lifetime_hours=session_lifetime_hours,
            rate_limit_attempts=rate_limit_attempts,
            rate_limit_window_minutes=rate_limit_window_minutes,
            password_min_length=password_min_length,
            max_upload_size_mb=max_upload_size_mb,
            allow_html_content=os.getenv("PRESSASSIST_ALLOW_HTML", "false").lower() == "true",
        )


class Config:
    """Configuration manager that combines app config with database settings."""

    def __init__(self, app_config: AppConfig, storage: Any = None):
        """Initialize config manager.

        Args:
            app_config: Application configuration.
            storage: Storage instance for database settings.
        """
        self.app = app_config
        self._storage = storage

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        First checks database settings, then app config.

        Args:
            key: Configuration key (supports dot notation for db values).
            default: Default value if not found.

        Returns:
            Configuration value.
        """
        # Try database first
        if self._storage is not None:
            db_value = self._storage.get(f"config.{key}")
            if db_value is not None:
                return db_value

        # Fall back to app config
        if hasattr(self.app, key):
            return getattr(self.app, key)

        return default

    def set(self, key: str, value: Any) -> None:
        """Set configuration value in database.

        Args:
            key: Configuration key.
            value: Value to set.
        """
        if self._storage is not None:
            self._storage.set(f"config.{key}", value)

    @property
    def site_title(self) -> str:
        """Get site title."""
        return self.get("site_title", "My Website")

    @property
    def theme(self) -> str:
        """Get active theme name."""
        return self.get("theme", "default")

    @property
    def login_slug(self) -> str:
        """Get secret login URL slug."""
        return self.get("login_slug", "")

    @property
    def force_https(self) -> bool:
        """Check if HTTPS is forced."""
        return self.get("force_https", True)

    @property
    def default_page(self) -> str:
        """Get default page slug."""
        return self.get("default_page", "home")

    @property
    def disabled_plugins(self) -> list[str]:
        """Get list of disabled plugin names."""
        return self.get("disabled_plugins", [])
