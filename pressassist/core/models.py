"""Pydantic models for PressAssistCMS."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    """Get current UTC time with timezone info."""
    return datetime.now(timezone.utc)


class Role(str, Enum):
    """User roles with different permission levels."""

    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class Visibility(str, Enum):
    """Page/menu item visibility settings."""

    SHOW = "show"
    HIDE = "hide"
    SYSTEM = "system"  # For internal pages like 404


class ContentFormat(str, Enum):
    """Supported content formats."""

    MARKDOWN = "markdown"
    HTML = "html"  # Sanitized HTML only


class User(BaseModel):
    """User account model."""

    username: str = Field(..., min_length=3, max_length=50)
    password_hash: str
    role: Role = Role.VIEWER
    created_at: datetime = Field(default_factory=utc_now)
    last_login: datetime | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Ensure username is alphanumeric with underscores."""
        if not v.replace("_", "").isalnum():
            raise ValueError("Username must be alphanumeric with underscores only")
        return v.lower()


class Page(BaseModel):
    """Page content model."""

    slug: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=200)
    content: str = ""
    content_format: ContentFormat = ContentFormat.MARKDOWN
    description: str = ""
    keywords: str = ""
    visibility: Visibility = Visibility.SHOW
    subpages: dict[str, "Page"] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    modified_at: datetime = Field(default_factory=utc_now)
    modified_by: str = "system"

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Ensure slug is URL-safe."""
        import re

        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError("Slug must be lowercase alphanumeric with hyphens")
        return v


class Block(BaseModel):
    """Static block content model."""

    name: str = Field(..., min_length=1, max_length=50)
    content: str = ""
    content_format: ContentFormat = ContentFormat.MARKDOWN


class MenuItem(BaseModel):
    """Navigation menu item model."""

    name: str = Field(..., min_length=1, max_length=100)
    slug: str
    visibility: Visibility = Visibility.SHOW
    order: int = 0
    subpages: list["MenuItem"] = Field(default_factory=list)


class UploadedFile(BaseModel):
    """Uploaded file metadata model."""

    uuid: str
    original_name: str
    mime_type: str
    size: int
    uploaded_at: datetime = Field(default_factory=utc_now)
    uploaded_by: str


class SiteConfig(BaseModel):
    """Site configuration model."""

    site_title: str = "My Website"
    site_lang: str = "en"
    admin_lang: str = "en"
    theme: str = "default"
    default_page: str = "home"
    login_slug: str  # Random, secret
    force_https: bool = True
    disabled_plugins: list[str] = Field(default_factory=list)
    last_modified: datetime = Field(default_factory=utc_now)


class Session(BaseModel):
    """User session model."""

    session_id: str
    user_id: str
    role: Role
    ip: str
    user_agent: str
    csrf_token: str
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime


class LoginAttempt(BaseModel):
    """Login attempt for rate limiting."""

    ip: str
    timestamp: datetime = Field(default_factory=utc_now)
    success: bool
    user_agent: str | None = None


class AuditEvent(BaseModel):
    """Audit log event model."""

    timestamp: datetime = Field(default_factory=utc_now)
    event: str
    actor: str
    ip: str | None = None
    user_agent: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class DatabaseSchema(BaseModel):
    """Full database schema model."""

    config: SiteConfig
    users: dict[str, User] = Field(default_factory=dict)
    pages: dict[str, Page] = Field(default_factory=dict)
    blocks: dict[str, Block] = Field(default_factory=dict)
    menu_items: list[MenuItem] = Field(default_factory=list)
    uploads: dict[str, UploadedFile] = Field(default_factory=dict)
