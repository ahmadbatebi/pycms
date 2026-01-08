"""Blog models for ChelCheleh."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from .models import ContentFormat, ContentLanguage, utc_now


class PostStatus(str, Enum):
    """Blog post status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    SCHEDULED = "scheduled"


class CommentStatus(str, Enum):
    """Comment moderation status."""

    PENDING = "pending"
    APPROVED = "approved"
    SPAM = "spam"


class BlogPost(BaseModel):
    """Blog post model."""

    slug: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=200)
    content: str = ""
    content_format: ContentFormat = ContentFormat.HTML
    excerpt: str = Field(default="", max_length=500)
    featured_image: str | None = None  # UUID of uploaded image
    category: str | None = None  # Category slug
    tags: list[str] = Field(default_factory=list)
    author: str = "admin"
    status: PostStatus = PostStatus.DRAFT
    published_at: datetime | None = None
    display_pages: list[str] = Field(default_factory=list)  # Page slugs where post appears
    comments_enabled: bool = True
    auto_approve_comments: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    modified_at: datetime = Field(default_factory=utc_now)
    modified_by: str = "system"
    # Language settings
    language: ContentLanguage = ContentLanguage.BOTH  # Which language(s) this post shows in
    associated_post: str | None = None  # Slug of associated post in other language

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Ensure slug is URL-safe."""
        import re

        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError("Slug must be lowercase alphanumeric with hyphens")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Normalize tags to lowercase."""
        return [tag.lower().strip() for tag in v if tag.strip()]


class BlogCategory(BaseModel):
    """Blog category model."""

    slug: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    order: int = 0
    # Language settings
    language: ContentLanguage = ContentLanguage.BOTH  # Which language(s) this category shows in
    associated_category: str | None = None  # Slug of associated category in other language

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Ensure slug is URL-safe."""
        import re

        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError("Slug must be lowercase alphanumeric with hyphens")
        return v


class BlogComment(BaseModel):
    """Blog comment model."""

    id: str  # UUID
    post_slug: str
    author_name: str = Field(..., min_length=1, max_length=100)
    author_email: str = Field(..., max_length=200)
    content: str = Field(..., min_length=1, max_length=2000)
    status: CommentStatus = CommentStatus.PENDING
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("author_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email validation."""
        import re

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v.lower().strip()

    @field_validator("content")
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        """Strip HTML and sanitize content."""
        import bleach

        return bleach.clean(v, tags=[], strip=True).strip()
