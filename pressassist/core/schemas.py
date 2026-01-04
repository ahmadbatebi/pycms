"""Pydantic schemas for request/response validation.

This module provides comprehensive input validation using Pydantic models
for all API endpoints, replacing manual dict.get() calls with proper validation.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from .models import ContentFormat, Visibility


# ============================================================================
# Page Schemas
# ============================================================================

class PageCreateRequest(BaseModel):
    """Request schema for creating a new page."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Page title"
    )
    content: str = Field(
        default="",
        max_length=500000,  # 500KB limit
        description="Page content in markdown or HTML"
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Meta description for SEO"
    )
    keywords: str = Field(
        default="",
        max_length=200,
        description="Meta keywords for SEO"
    )
    content_format: ContentFormat = Field(
        default=ContentFormat.MARKDOWN,
        description="Content format (markdown or html)"
    )
    visibility: Visibility = Field(
        default=Visibility.SHOW,
        description="Page visibility setting"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not just whitespace."""
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()


class PageUpdateRequest(BaseModel):
    """Request schema for updating an existing page."""

    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Page title"
    )
    content: Optional[str] = Field(
        None,
        max_length=500000,
        description="Page content"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Meta description"
    )
    keywords: Optional[str] = Field(
        None,
        max_length=200,
        description="Meta keywords"
    )
    content_format: Optional[ContentFormat] = None
    visibility: Optional[Visibility] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        """Ensure title is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip() if v else v


class PageResponse(BaseModel):
    """Response schema for page data."""

    slug: str
    title: str
    content: str
    content_format: str
    description: str
    keywords: str
    visibility: str
    created_at: datetime
    modified_at: datetime
    modified_by: str


# ============================================================================
# Block Schemas
# ============================================================================

class BlockUpdateRequest(BaseModel):
    """Request schema for updating a content block."""

    content: str = Field(
        ...,
        max_length=100000,  # 100KB limit
        description="Block content"
    )
    content_format: ContentFormat = Field(
        default=ContentFormat.MARKDOWN,
        description="Content format"
    )


class BlockResponse(BaseModel):
    """Response schema for block data."""

    name: str
    content: str
    content_format: str


# ============================================================================
# Settings Schemas
# ============================================================================

class SiteSettingsRequest(BaseModel):
    """Request schema for updating site settings."""

    site_title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Site title"
    )
    site_lang: Optional[str] = Field(
        None,
        min_length=2,
        max_length=10,
        description="Site language code (e.g., 'en', 'fa')"
    )
    admin_lang: Optional[str] = Field(
        None,
        min_length=2,
        max_length=10,
        description="Admin panel language"
    )
    theme: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="Active theme name"
    )
    default_page: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Default page slug for homepage"
    )
    force_https: Optional[bool] = Field(
        None,
        description="Force HTTPS for all connections"
    )

    @field_validator("site_lang", "admin_lang")
    @classmethod
    def validate_lang(cls, v: Optional[str]) -> Optional[str]:
        """Validate language code format."""
        if v is not None:
            v = v.lower().strip()
            if not v.replace("-", "").replace("_", "").isalpha():
                raise ValueError("Language code must contain only letters and hyphens")
        return v


class SiteSettingsResponse(BaseModel):
    """Response schema for site settings."""

    site_title: str
    site_lang: str
    admin_lang: str
    theme: str
    default_page: str
    force_https: bool


# ============================================================================
# Upload Schemas
# ============================================================================

class UploadResponse(BaseModel):
    """Response schema for file upload."""

    uuid: str
    original_name: str
    mime_type: str
    size: int
    url: str
    uploaded_at: datetime


class UploadListResponse(BaseModel):
    """Response schema for listing uploads."""

    uploads: list[UploadResponse]
    total: int


# ============================================================================
# Menu Schemas
# ============================================================================

class MenuItemRequest(BaseModel):
    """Request schema for a menu item."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Menu item display name"
    )
    slug: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Page slug to link to"
    )
    visibility: Visibility = Field(
        default=Visibility.SHOW,
        description="Menu item visibility"
    )
    order: int = Field(
        default=0,
        ge=0,
        le=10000,
        description="Sort order (lower = earlier)"
    )


class MenuUpdateRequest(BaseModel):
    """Request schema for updating the entire menu."""

    items: list[MenuItemRequest] = Field(
        ...,
        max_length=100,  # Maximum 100 menu items
        description="List of menu items"
    )


# ============================================================================
# Authentication Schemas
# ============================================================================

class LoginRequest(BaseModel):
    """Request schema for login."""

    password: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="User password"
    )
    csrf_token: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="CSRF token"
    )


class PasswordChangeRequest(BaseModel):
    """Request schema for changing password."""

    current_password: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Current password"
    )
    new_password: str = Field(
        ...,
        min_length=12,
        max_length=200,
        description="New password (minimum 12 characters)"
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_letter and has_digit):
            raise ValueError("Password must contain at least one letter and one number")
        return v


# ============================================================================
# Plugin Schemas
# ============================================================================

class PluginActionRequest(BaseModel):
    """Request schema for plugin enable/disable."""

    action: str = Field(
        ...,
        pattern="^(enable|disable)$",
        description="Action to perform (enable or disable)"
    )


class PluginResponse(BaseModel):
    """Response schema for plugin info."""

    name: str
    version: str
    description: str
    author: str
    enabled: bool
    permissions: list[str]


# ============================================================================
# Backup Schemas
# ============================================================================

class BackupResponse(BaseModel):
    """Response schema for backup info."""

    filename: str
    created_at: datetime
    size: int


class BackupListResponse(BaseModel):
    """Response schema for listing backups."""

    backups: list[BackupResponse]
    total: int


# ============================================================================
# Generic Response Schemas
# ============================================================================

class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = True
    message: str = "Operation completed successfully"


class ErrorResponse(BaseModel):
    """Generic error response."""

    success: bool = False
    error: str
    detail: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Generic paginated response."""

    items: list[Any]
    total: int
    page: int
    per_page: int
    pages: int
