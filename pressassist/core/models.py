"""Pydantic models for ChelCheleh."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    """Get current UTC time with timezone info."""
    return datetime.now(timezone.utc)


class ProfileVisibility(str, Enum):
    """User profile visibility settings."""

    PUBLIC = "public"
    PRIVATE = "private"


class Role(str, Enum):
    """User roles with different permission levels.

    Hierarchy (highest to lowest):
    - SUPER_ADMIN: Full access, can manage admins, cannot be deleted
    - ADMIN: Full CMS access, can manage users/editors
    - EDITOR: Can edit/create content
    - USER: Basic user, can view, comment, manage own profile
    """

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    EDITOR = "editor"
    USER = "user"


class Visibility(str, Enum):
    """Page/menu item visibility settings."""

    SHOW = "show"
    HIDE = "hide"
    SYSTEM = "system"  # For internal pages like 404


class ContentFormat(str, Enum):
    """Supported content formats."""

    MARKDOWN = "markdown"
    HTML = "html"  # Sanitized HTML only


class ContentLanguage(str, Enum):
    """Content language visibility settings."""

    EN = "en"  # English only
    FA = "fa"  # Persian only
    BOTH = "both"  # Both languages


class User(BaseModel):
    """User account model with profile and verification support."""

    # Core fields
    username: str = Field(..., min_length=3, max_length=50)
    password_hash: str
    role: Role = Role.USER
    created_at: datetime = Field(default_factory=utc_now)
    last_login: datetime | None = None

    # Profile fields
    email: str | None = None
    display_name: str | None = None
    phone: str | None = None
    bio: str | None = None  # About me text
    avatar_uuid: str | None = None  # Reference to uploaded file
    cover_image_uuid: str | None = None  # Profile cover image

    # Verification system
    is_verified: bool = False
    verification_requested_at: datetime | None = None
    verified_at: datetime | None = None
    verified_by: str | None = None

    # Account status
    is_active: bool = True
    profile_visibility: ProfileVisibility = ProfileVisibility.PUBLIC

    # Password reset
    reset_token: str | None = None
    reset_token_expires: datetime | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Ensure username is alphanumeric with underscores."""
        if not v.replace("_", "").isalnum():
            raise ValueError("Username must be alphanumeric with underscores only")
        return v.lower()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Basic email validation."""
        if v is None:
            return None
        import re

        v = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """Basic phone validation (allows +, digits, spaces, dashes)."""
        if v is None:
            return None
        import re

        v = v.strip()
        if v and not re.match(r"^[\d\s\-+()]+$", v):
            raise ValueError("Invalid phone format")
        return v


class LocalizedContent(BaseModel):
    """Localized content for a page in a specific language."""

    title: str = ""
    content: str = ""
    description: str = ""
    keywords: str = ""


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
    template: str = "default"
    translations: dict[str, LocalizedContent] = Field(default_factory=dict)
    # Display options
    hide_title: bool = False
    hide_description: bool = False
    blog_columns: int = 2  # Number of columns for blog posts display (1, 2, or 3)
    posts_per_page: int = 10  # Number of blog posts per page
    # Language settings
    language: ContentLanguage = ContentLanguage.BOTH  # Which language(s) this page shows in
    associated_page: str | None = None  # Slug of associated page in other language

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Ensure slug is URL-safe."""
        import re

        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError("Slug must be lowercase alphanumeric with hyphens")
        return v

    def get_localized(self, lang: str) -> "LocalizedContent":
        """Get localized content for a language.

        Falls back to default content if translation not available.

        Args:
            lang: Language code.

        Returns:
            LocalizedContent with title, content, description, keywords.
        """
        if lang in self.translations and self.translations[lang].title:
            return self.translations[lang]
        return LocalizedContent(
            title=self.title,
            content=self.content,
            description=self.description,
            keywords=self.keywords,
        )


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
    language: ContentLanguage = ContentLanguage.BOTH  # Which language(s) this menu item shows in


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
    copyright_text: str = "Copyright 2026 ChelCheleh v0.1.0 — Designed by Ahmad Batebi"
    last_modified: datetime = Field(default_factory=utc_now)

    # User registration settings
    enable_registration: bool = True
    require_email_verification: bool = False

    # SMTP settings for email (password reset, notifications)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password_encrypted: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True

    # Search settings
    enable_search: bool = True
    search_in_pages: bool = True
    search_in_blog: bool = True
    search_min_chars: int = 2
    search_max_results: int = 20

    # Jump to Top button
    enable_jump_to_top: bool = True

    # Maintenance mode
    maintenance_mode: bool = False
    maintenance_message: str = "Site is under maintenance. Please check back later."

    # Login required to view site
    require_login: bool = False
    allow_registration: bool = True


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
    # Blog system
    blog_posts: dict[str, "BlogPost"] = Field(default_factory=dict)
    blog_categories: dict[str, "BlogCategory"] = Field(default_factory=dict)
    blog_comments: dict[str, "BlogComment"] = Field(default_factory=dict)


# Import blog models at the end to avoid circular imports
from .blog_models import BlogCategory, BlogComment, BlogPost  # noqa: E402, F401
