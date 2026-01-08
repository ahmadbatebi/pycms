"""Frontend profile routes for ChelCheleh.

Handles public profile viewing and user profile editing.
"""

import html
import io
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from ..core.auth import AuthManager
from ..core.i18n import i18n, t
from ..core.models import ProfileVisibility, Role

router = APIRouter(tags=["profile"])

# Image upload security constants
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
MAGIC_BYTES = {
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
    "webp": b"RIFF",
    "gif": b"GIF8",
}
MAX_PROFILE_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


def _validate_image_magic_bytes(content: bytes, extension: str) -> bool:
    """Validate file content matches expected magic bytes.

    Args:
        content: File content bytes.
        extension: File extension.

    Returns:
        True if magic bytes match, False otherwise.
    """
    expected = MAGIC_BYTES.get(extension.lower())
    if not expected:
        return False

    if extension.lower() == "webp":
        # WebP has RIFF header at start and WEBP at offset 8
        return content[:4] == b"RIFF" and len(content) > 12 and content[8:12] == b"WEBP"

    return content.startswith(expected)


def _reencode_image(content: bytes, extension: str) -> bytes | None:
    """Re-encode image to strip metadata and hidden payloads.

    Args:
        content: Original image bytes.
        extension: File extension.

    Returns:
        Clean image bytes or None if processing failed.
    """
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(content))

        # Preserve ICC color profile if present
        icc_profile = img.info.get("icc_profile")

        # Strip EXIF and other metadata by creating a new image
        if img.mode in ("RGBA", "LA", "P"):
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(list(img.getdata()))
        else:
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(list(img.getdata()))

        # Save to buffer
        output = io.BytesIO()

        # Map extension to PIL format
        pil_format = {
            "png": "PNG",
            "jpg": "JPEG",
            "jpeg": "JPEG",
            "webp": "WEBP",
            "gif": "GIF",
        }.get(extension.lower(), "PNG")

        # Prepare save options
        save_kwargs = {"format": pil_format}

        # Preserve ICC profile for color accuracy
        if icc_profile:
            save_kwargs["icc_profile"] = icc_profile

        # Use quality setting for JPEG/WEBP
        if pil_format in ("JPEG", "WEBP"):
            save_kwargs["quality"] = 90

        clean_img.save(output, **save_kwargs)
        return output.getvalue()

    except Exception:
        return None


def _get_common_imports():
    """Lazy import to avoid circular imports."""
    from ..main import auth, storage

    return {
        "auth": auth,
        "storage": storage,
    }


def get_verification_badge_svg(role: Role, is_verified: bool, size: int = 24) -> str:
    """Get SVG badge based on role and verification status.

    Args:
        role: User's role.
        is_verified: Whether user is verified.
        size: Badge size in pixels.

    Returns:
        SVG string for the badge wrapped in a span with tooltip.
    """
    # Get tooltip texts
    super_admin_tooltip = t("profile.super_admin_badge")
    admin_tooltip = t("profile.admin_badge")
    verified_tooltip = t("profile.verified_identity")

    # Super Admin - Gold badge
    if role == Role.SUPER_ADMIN:
        svg = f'''<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" fill="#FFD700"/>
            <path d="M9 12l2 2 4-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>'''
        return f'<span title="{super_admin_tooltip}" style="display:inline-flex;cursor:help;">{svg}</span>'

    # Admin - Silver badge
    if role == Role.ADMIN:
        svg = f'''<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" fill="#C0C0C0"/>
            <path d="M9 12l2 2 4-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>'''
        return f'<span title="{admin_tooltip}" style="display:inline-flex;cursor:help;">{svg}</span>'

    # Verified user - Blue badge (like Twitter)
    if is_verified:
        svg = f'''<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" fill="#1DA1F2"/>
            <path d="M9 12l2 2 4-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>'''
        return f'<span title="{verified_tooltip}" style="display:inline-flex;cursor:help;">{svg}</span>'

    return ""


def get_profile_page_styles() -> str:
    """Get styles for profile pages."""
    return '''
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: 'Vazirmatn', Tahoma, Arial, sans-serif;
            margin: 0;
            background: #f5f5f5;
            color: #1e293b;
            min-height: 100vh;
        }

        /* LTR Default */
        body {
            direction: ltr;
            text-align: left;
        }

        /* RTL Mode */
        [dir="rtl"] body {
            direction: rtl;
            text-align: right;
        }

        /* Navigation Bar */
        .nav-bar {
            background: white;
            padding: 1rem 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .nav-content {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }
        .site-logo {
            font-size: 1.25rem;
            font-weight: 700;
            color: #1e293b;
            text-decoration: none;
        }
        .site-logo:hover {
            color: #7c3aed;
        }
        .nav-links {
            display: flex;
            gap: 1.5rem;
            align-items: center;
        }
        .nav-links a {
            color: #64748b;
            text-decoration: none;
            font-weight: 500;
            transition: color 0.2s;
        }
        .nav-links a:hover {
            color: #7c3aed;
        }

        /* Profile Header (Cover) */
        .profile-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            position: relative;
            width: 100%;
        }
        .cover-image {
            width: 100%;
            height: 280px;
            object-fit: cover;
            display: block;
        }
        .cover-placeholder {
            width: 100%;
            height: 280px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }

        /* Profile Info Container */
        .profile-info {
            max-width: 900px;
            margin: 0 auto;
            padding: 0 1.5rem 2rem;
            position: relative;
        }

        /* Avatar */
        .avatar-container {
            position: absolute;
            top: -80px;
            z-index: 10;
        }
        [dir="ltr"] .avatar-container,
        :not([dir="rtl"]) .avatar-container {
            left: 1.5rem;
            right: auto;
        }
        [dir="rtl"] .avatar-container {
            right: 1.5rem;
            left: auto;
        }
        .avatar {
            width: 160px;
            height: 160px;
            border-radius: 50%;
            border: 5px solid white;
            object-fit: cover;
            background: white;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .avatar-placeholder {
            width: 160px;
            height: 160px;
            border-radius: 50%;
            border: 5px solid white;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3.5rem;
            color: white;
            font-weight: 700;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        /* Profile Details */
        .profile-details {
            padding-top: 100px;
        }
        .profile-name {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin: 0 0 0.25rem;
            font-size: 1.875rem;
            font-weight: 700;
            flex-wrap: wrap;
        }
        [dir="rtl"] .profile-name {
            justify-content: flex-start;
        }
        .profile-username {
            color: #64748b;
            font-size: 1.1rem;
            margin: 0 0 1.25rem;
        }

        /* Profile Meta (Email, Phone) */
        .profile-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 1.5rem;
            margin-bottom: 1.5rem;
            color: #64748b;
        }
        .profile-meta-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .profile-meta-item svg {
            flex-shrink: 0;
        }

        /* Profile Actions */
        .profile-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.95rem;
            border: none;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
        }
        .btn-secondary {
            background: #6b7280;
        }

        /* Bio Section */
        .profile-bio {
            background: white;
            padding: 1.5rem;
            border-radius: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 1.5rem;
        }
        .profile-bio h3 {
            margin: 0 0 1rem;
            font-size: 1.15rem;
            font-weight: 600;
            color: #374151;
        }
        .profile-bio p {
            margin: 0;
            line-height: 1.9;
            white-space: pre-wrap;
            word-wrap: break-word;
            color: #4b5563;
        }

        /* Private Profile Notice */
        .private-notice {
            text-align: center;
            padding: 3rem 1rem;
            color: #64748b;
        }
        .private-notice svg {
            opacity: 0.5;
            margin-bottom: 1rem;
        }
        .private-notice p {
            margin: 0;
            font-size: 1.1rem;
        }

        /* Back Link */
        .back-link {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            color: #7c3aed;
            text-decoration: none;
            margin: 1rem 0;
            font-weight: 500;
        }
        .back-link:hover {
            text-decoration: underline;
        }

        /* ========== Responsive Design ========== */

        /* Tablet */
        @media (max-width: 768px) {
            .cover-image, .cover-placeholder {
                height: 200px;
            }
            .profile-info {
                padding: 0 1rem 2rem;
            }
            .avatar-container {
                top: -60px;
            }
            [dir="ltr"] .avatar-container,
            :not([dir="rtl"]) .avatar-container {
                left: 1rem;
            }
            [dir="rtl"] .avatar-container {
                right: 1rem;
            }
            .avatar, .avatar-placeholder {
                width: 120px;
                height: 120px;
                font-size: 2.5rem;
                border-width: 4px;
            }
            .profile-details {
                padding-top: 75px;
            }
            .profile-name {
                font-size: 1.5rem;
            }
            .profile-username {
                font-size: 1rem;
            }
            .profile-meta {
                gap: 1rem;
            }
            .profile-bio {
                padding: 1.25rem;
            }
            .btn {
                padding: 0.625rem 1.25rem;
                font-size: 0.9rem;
            }
        }

        /* Mobile */
        @media (max-width: 480px) {
            .nav-bar {
                padding: 0.75rem 1rem;
            }
            .nav-content {
                justify-content: center;
                text-align: center;
            }
            .nav-links {
                width: 100%;
                justify-content: center;
                gap: 1rem;
            }
            .cover-image, .cover-placeholder {
                height: 160px;
            }
            .profile-info {
                padding: 0 0.75rem 1.5rem;
            }
            .avatar-container {
                top: -50px;
            }
            [dir="ltr"] .avatar-container,
            :not([dir="rtl"]) .avatar-container {
                left: 0.75rem;
            }
            [dir="rtl"] .avatar-container {
                right: 0.75rem;
            }
            .avatar, .avatar-placeholder {
                width: 100px;
                height: 100px;
                font-size: 2rem;
                border-width: 3px;
            }
            .profile-details {
                padding-top: 60px;
            }
            .profile-name {
                font-size: 1.35rem;
            }
            .profile-username {
                font-size: 0.95rem;
                margin-bottom: 1rem;
            }
            .profile-meta {
                flex-direction: column;
                gap: 0.75rem;
            }
            .profile-actions {
                flex-direction: column;
            }
            .profile-actions .btn {
                width: 100%;
            }
            .profile-bio {
                padding: 1rem;
                border-radius: 12px;
            }
            .profile-bio h3 {
                font-size: 1.05rem;
            }
            .profile-bio p {
                font-size: 0.95rem;
                line-height: 1.8;
            }
        }

        /* Very small screens */
        @media (max-width: 360px) {
            .avatar, .avatar-placeholder {
                width: 80px;
                height: 80px;
                font-size: 1.75rem;
            }
            .avatar-container {
                top: -40px;
            }
            .profile-details {
                padding-top: 50px;
            }
            .profile-name {
                font-size: 1.2rem;
            }
        }
    </style>
    '''


def get_edit_profile_styles() -> str:
    """Get styles for edit profile page - matching admin panel design."""
    return '''
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: system-ui, -apple-system, sans-serif;
            margin: 0;
            background: #f5f5f5;
            color: #1e293b;
            min-height: 100vh;
        }

        /* Header */
        .header {
            background: #1e293b;
            color: white;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header a {
            color: #94a3b8;
            text-decoration: none;
        }
        .header-right {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        /* Page wrapper and container */
        .page-wrapper {
            display: flex;
            justify-content: center;
            width: 100%;
            padding: 2rem 1rem;
        }
        .container {
            width: 100%;
            max-width: 1000px;
        }

        /* Form grid layout */
        .form-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 1.5rem;
        }
        @media (min-width: 768px) {
            .form-grid {
                grid-template-columns: 1.5fr 1fr;
            }
        }

        /* Section cards */
        .section {
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            padding: 1.5rem;
        }
        .section h2 {
            margin: 0 0 1.5rem;
            font-size: 1.1rem;
            color: #475569;
            text-transform: uppercase;
            font-weight: 600;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid #e2e8f0;
        }

        /* Sidebar cards */
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        .sidebar-card {
            background: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .sidebar-card h4 {
            margin: 0 0 1rem;
            color: #475569;
            font-size: 0.875rem;
            text-transform: uppercase;
        }

        /* Form elements */
        .form-group {
            margin-bottom: 1.25rem;
        }
        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: #334155;
        }
        .form-group input, .form-group select, .form-group textarea {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            font-size: 1rem;
            box-sizing: border-box;
        }
        .form-group input:focus, .form-group textarea:focus, .form-group select:focus {
            outline: none;
            border-color: #7c3aed;
        }
        .form-group textarea {
            min-height: 120px;
            resize: vertical;
        }
        .form-group small {
            color: #6b7280;
            font-size: 0.875rem;
            display: block;
            margin-top: 0.25rem;
        }
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }
        @media (max-width: 600px) {
            .form-row {
                grid-template-columns: 1fr;
            }
        }

        /* Image upload */
        .image-upload {
            display: flex;
            align-items: center;
            gap: 1.5rem;
            padding: 1rem;
            border: 2px dashed #e2e8f0;
            border-radius: 8px;
            background: #f8fafc;
        }
        .current-image {
            width: 100px;
            height: 100px;
            border-radius: 8px;
            object-fit: cover;
            flex-shrink: 0;
        }
        .avatar-preview {
            border-radius: 50%;
        }
        .image-upload-info {
            flex: 1;
        }

        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            background: #7c3aed;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            border: none;
            cursor: pointer;
            font-size: 1rem;
            transition: background 0.2s;
        }
        .btn:hover {
            background: #6d28d9;
        }
        .btn-secondary {
            background: #6b7280;
        }
        .btn-secondary:hover {
            background: #4b5563;
        }
        .btn-outline {
            background: transparent;
            border: 2px solid #7c3aed;
            color: #7c3aed;
        }
        .btn-outline:hover {
            background: #7c3aed;
            color: white;
        }
        .btn-verify {
            padding: 0.5rem 1rem;
            font-size: 0.875rem;
        }

        /* Verification box */
        .verification-box {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem;
            background: #f8fafc;
            border-radius: 8px;
            gap: 1rem;
        }
        .verification-status {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        /* Messages */
        .success-message {
            background: #D1FAE5;
            color: #059669;
            padding: 0.75rem 1rem;
            border-radius: 6px;
            margin-bottom: 1rem;
        }
        .error-message {
            background: #FEE2E2;
            color: #DC2626;
            padding: 0.75rem 1rem;
            border-radius: 6px;
            margin-bottom: 1rem;
        }

        /* Page title */
        h1.page-title {
            text-align: center;
            color: #1e293b;
            margin: 0 0 1.5rem;
            font-size: 1.5rem;
        }

        /* RTL support */
        [dir="rtl"] input, [dir="rtl"] textarea, [dir="rtl"] select {
            text-align: right;
        }
        [dir="rtl"] input[type="email"], [dir="rtl"] input[type="url"], [dir="rtl"] input[type="tel"] {
            direction: ltr;
            text-align: left;
        }
        [dir="rtl"] .image-upload {
            flex-direction: row-reverse;
        }
        [dir="rtl"] .verification-box {
            flex-direction: row-reverse;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
            .header {
                padding: 0.75rem 1rem;
                flex-wrap: wrap;
                gap: 0.5rem;
            }
            .page-wrapper {
                padding: 1rem 0.5rem;
            }
            .section {
                padding: 1rem;
            }
            .form-grid {
                grid-template-columns: 1fr;
            }
            .form-row {
                grid-template-columns: 1fr;
            }
            .image-upload {
                flex-direction: column;
                text-align: center;
            }
            [dir="rtl"] .image-upload {
                flex-direction: column;
            }
            .verification-box {
                flex-direction: column;
                text-align: center;
            }
            [dir="rtl"] .verification-box {
                flex-direction: column;
            }
            .btn {
                width: 100%;
            }
        }

        @media (max-width: 480px) {
            .section h2, .sidebar-card h4 {
                font-size: 0.95rem;
            }
            .form-group input, .form-group select, .form-group textarea {
                font-size: 0.95rem;
            }
        }
    </style>
    '''


# ============================================================================
# Public Profile View
# ============================================================================

@router.get("/profile/{username}", response_class=HTMLResponse)
async def view_profile(request: Request, username: str):
    """View a user's public profile."""
    from ..main import storage, theme_manager, sanitizer, get_session
    from ..core.themes import CMSContext
    from ..core.csrf import get_csrf_token
    from ..core.language_middleware import (
        get_language_from_request,
        get_direction_from_request,
    )
    from ..core.languages import get_available_languages

    imports = _get_common_imports()
    auth = imports["auth"]

    # Get user data
    user_data = storage.get(f"users.{username}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # Check visibility
    visibility = user_data.get("profile_visibility", "public")
    is_private = visibility == "private"

    # Get current session
    session = await get_session(request)
    is_owner = session and session.user_id == username
    is_admin = session and AuthManager.is_admin_or_above(session.role)

    # Check access
    can_view = not is_private or is_owner or is_admin

    site_title = storage.get("config.site_title", "Website")
    site_lang = storage.get("config.site_lang", "en")
    current_lang = get_language_from_request(request)
    lang_direction = get_direction_from_request(request)

    # Get page template from site config
    page_template = storage.get("config.default_template", "default")

    try:
        role = Role(user_data.get("role", "user"))
    except ValueError:
        role = Role.USER

    badge_svg = get_verification_badge_svg(role, user_data.get("is_verified", False), 28)

    # Avatar
    if user_data.get("avatar_uuid"):
        avatar_html = f'<img src="/uploads/{user_data["avatar_uuid"]}" alt="" class="avatar">'
    else:
        initial = (user_data.get("display_name") or username)[0].upper()
        avatar_html = f'<div class="avatar-placeholder">{initial}</div>'

    # Cover image
    if user_data.get("cover_image_uuid"):
        cover_html = f'<img src="/uploads/{user_data["cover_image_uuid"]}" alt="" class="cover-image">'
    else:
        cover_html = '<div class="cover-placeholder"></div>'

    display_name = user_data.get("display_name") or username
    bio = ""
    meta_items = ""

    if can_view:
        bio = html.escape(user_data.get("bio") or "")
        phone = user_data.get("phone") or ""
        email = user_data.get("email") or ""

        # Build meta items
        if email and (is_owner or is_admin):
            meta_items += f'''
            <div class="profile-meta-item">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
                <span>{email}</span>
            </div>
            '''
        if phone:
            meta_items += f'''
            <div class="profile-meta-item">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                <span>{phone}</span>
            </div>
            '''

    # Get menu items
    menu_items = storage.get("menu_items", [])
    visible_menu = [item for item in menu_items if item.get("visibility") == "show" or session]

    # Get blocks
    blocks_data = storage.get("blocks", {})
    rendered_blocks = {}
    for name, block in blocks_data.items():
        if block.get("enabled") is False:
            rendered_blocks[name] = ""
            continue
        content = block.get("content", "")
        fmt = block.get("content_format", "markdown")
        rendered_blocks[name] = sanitizer.render_content(content, fmt)

    # Profile data for template
    profile_data = {
        "username": username,
        "display_name": display_name,
        "bio": bio,
        "badge_svg": badge_svg,
        "avatar_html": avatar_html,
        "cover_html": cover_html,
        "meta_items": meta_items,
        "can_view": can_view,
        "is_owner": is_owner,
        "about_label": i18n.get("profile.about", current_lang),
        "edit_label": i18n.get("profile.edit_profile", current_lang),
        "private_message": i18n.get("profile.private_profile", current_lang),
    }

    context = CMSContext(
        site_title=site_title,
        site_lang=site_lang,
        theme=storage.get("config.theme", "default"),
        lang_direction=lang_direction,
        current_language=current_lang,
        available_languages=get_available_languages(),
        page_title=display_name,
        page_slug=f"profile/{username}",
        page_content="",
        page_description=f"Profile of {display_name}",
        page_keywords="",
        page_template=page_template,
        menu_items=visible_menu,
        blocks=rendered_blocks,
        is_admin=session and session.role.value == "admin" if session else False,
        is_editor=session and session.role.value in ("admin", "editor") if session else False,
        user=session.user_id if session else None,
        user_display_name=storage.get(f"users.{session.user_id}.display_name") if session else None,
        csrf_token=get_csrf_token(request),
        _asset_prefix=f"/themes/{storage.get('config.theme', 'default').lower()}/static",
    )

    rendered_html = theme_manager.render("profile.html", context, profile=profile_data)
    return HTMLResponse(content=rendered_html)


# ============================================================================
# Edit Own Profile
# ============================================================================

@router.get("/me/profile", response_class=HTMLResponse)
async def edit_profile_page(request: Request, success: str | None = None, error: str | None = None):
    """Render edit profile page for current user."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]

    # Check authentication
    session_id = request.cookies.get("session_id")
    session = auth.verify_session(session_id) if session_id else None

    if not session:
        return RedirectResponse(url="/login", status_code=303)

    username = session.user_id
    user_data = storage.get(f"users.{username}")

    if not user_data:
        return RedirectResponse(url="/login", status_code=303)

    from ..core.language_middleware import (
        get_language_from_request,
        get_direction_from_request,
    )

    site_title = storage.get("config.site_title", "Website")
    site_lang = storage.get("config.site_lang", "en")
    current_lang = get_language_from_request(request)
    direction = get_direction_from_request(request)

    csrf_token = secrets.token_urlsafe(32)

    try:
        role = Role(user_data.get("role", "user"))
    except ValueError:
        role = Role.USER

    # Messages
    success_html = f'<div class="success-message">{success}</div>' if success else ""
    error_html = f'<div class="error-message">{error}</div>' if error else ""

    # Current images
    avatar_preview = ""
    if user_data.get("avatar_uuid"):
        avatar_preview = f'<img src="/uploads/{user_data["avatar_uuid"]}" class="current-image avatar-preview" alt="">'
    else:
        initial = (user_data.get("display_name") or username)[0].upper()
        avatar_preview = f'<div class="current-image avatar-preview" style="display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);color:white;font-size:2rem;font-weight:700;border-radius:50%;">{initial}</div>'

    cover_preview = ""
    if user_data.get("cover_image_uuid"):
        cover_preview = f'<img src="/uploads/{user_data["cover_image_uuid"]}" class="current-image" alt="" style="width:200px;height:80px;">'
    else:
        cover_preview = '<div class="current-image" style="width:200px;height:80px;background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);"></div>'

    # Verification section
    is_verified = user_data.get("is_verified", False)
    verification_requested = user_data.get("verification_requested_at") is not None
    badge_svg = get_verification_badge_svg(role, is_verified, 24)

    if role in (Role.SUPER_ADMIN, Role.ADMIN):
        verification_html = f'''
        <div class="verification-box">
            <div class="verification-status">
                {badge_svg}
                <span>{t('profile.admin_verified')}</span>
            </div>
        </div>
        '''
    elif is_verified:
        verification_html = f'''
        <div class="verification-box">
            <div class="verification-status">
                {badge_svg}
                <span style="color:#1DA1F2;">{t('profile.verified')}</span>
            </div>
        </div>
        '''
    elif verification_requested:
        verification_html = f'''
        <div class="verification-box">
            <div class="verification-status">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#EF4444"/><path d="M12 8v4M12 16h.01" stroke="white" stroke-width="2" stroke-linecap="round"/></svg>
                <span style="color:#EF4444;">{t('profile.verification_pending')}</span>
            </div>
        </div>
        '''
    else:
        verification_html = f'''
        <div class="verification-box">
            <div class="verification-status">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" style="opacity:0.5;"><circle cx="12" cy="12" r="10" fill="#9CA3AF"/><path d="M9 12l2 2 4-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                <span style="color:#6B7280;">{t('profile.not_verified')}</span>
            </div>
            <form method="POST" action="/me/request-verification">
                <input type="hidden" name="csrf_token" value="{csrf_token}">
                <button type="submit" class="btn btn-verify">{t('profile.request_verification')}</button>
            </form>
        </div>
        '''

    # Visibility options
    current_visibility = user_data.get("profile_visibility", "public")
    visibility_public = "selected" if current_visibility == "public" else ""
    visibility_private = "selected" if current_visibility == "private" else ""

    # Get display name for header
    display_name = user_data.get("display_name") or username

    html = f'''
    <!DOCTYPE html>
    <html lang="{current_lang}" dir="{direction}">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{t('profile.edit_profile')} - {site_title}</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;700&display=swap" rel="stylesheet">
        {get_edit_profile_styles()}
    </head>
    <body>
        <div class="header">
            <a href="/" style="font-weight:600;color:white;">{site_title}</a>
            <div class="header-right">
                <a href="/profile/{username}" style="color:#94a3b8;">{t('profile.view_profile')}</a>
                <span style="color:#475569;">|</span>
                <span style="color:#94a3b8;">{display_name}</span>
                <span style="color:#475569;">|</span>
                <a href="/logout" style="color:#94a3b8;">{t('auth.logout')}</a>
            </div>
        </div>

        <div class="page-wrapper">
            <div class="container">
                <h1 class="page-title">{t('profile.edit_profile')}</h1>

                {success_html}
                {error_html}

                <div class="form-grid">
                    <!-- Main content column -->
                    <div class="main-content">
                        <div class="section">
                            <h2>{t('profile.basic_info')}</h2>
                            <form method="POST" action="/me/profile">
                                <input type="hidden" name="csrf_token" value="{csrf_token}">

                                <div class="form-row">
                                    <div class="form-group">
                                        <label>{t('profile.username')}</label>
                                        <input type="text" value="{username}" disabled style="background:#f3f4f6;">
                                    </div>
                                    <div class="form-group">
                                        <label for="email">{t('profile.email')}</label>
                                        <input type="email" id="email" name="email" value="{user_data.get('email') or ''}">
                                    </div>
                                </div>

                                <div class="form-row">
                                    <div class="form-group">
                                        <label for="display_name">{t('profile.display_name')}</label>
                                        <input type="text" id="display_name" name="display_name" value="{user_data.get('display_name') or ''}" maxlength="100">
                                    </div>
                                    <div class="form-group">
                                        <label for="phone">{t('profile.phone')}</label>
                                        <input type="tel" id="phone" name="phone" value="{user_data.get('phone') or ''}">
                                    </div>
                                </div>

                                <div class="form-group">
                                    <label for="bio">{t('profile.bio')}</label>
                                    <textarea id="bio" name="bio" maxlength="500">{user_data.get('bio') or ''}</textarea>
                                </div>

                                <div class="form-group">
                                    <label for="visibility">{t('profile.visibility')}</label>
                                    <select id="visibility" name="visibility">
                                        <option value="public" {visibility_public}>{t('profile.visibility_public')}</option>
                                        <option value="private" {visibility_private}>{t('profile.visibility_private')}</option>
                                    </select>
                                    <small>{t('profile.visibility_hint')}</small>
                                </div>

                                <button type="submit" class="btn" style="width:100%;">{t('profile.save_changes')}</button>
                            </form>
                        </div>

                        <div class="section" style="margin-top:1.5rem;">
                            <h2>{t('profile.change_password')}</h2>
                            <form method="POST" action="/me/password">
                                <input type="hidden" name="csrf_token" value="{csrf_token}">

                                <div class="form-group">
                                    <label for="current_password">{t('profile.current_password')}</label>
                                    <input type="password" id="current_password" name="current_password" required>
                                </div>

                                <div class="form-row">
                                    <div class="form-group">
                                        <label for="new_password">{t('profile.new_password')}</label>
                                        <input type="password" id="new_password" name="new_password" required minlength="12">
                                    </div>
                                    <div class="form-group">
                                        <label for="confirm_password">{t('profile.confirm_password')}</label>
                                        <input type="password" id="confirm_password" name="confirm_password" required minlength="12">
                                    </div>
                                </div>
                                <small style="color:#6b7280;">{t('profile.password_requirements')}</small>

                                <div style="margin-top:1rem;">
                                    <button type="submit" class="btn" style="width:100%;">{t('profile.update_password')}</button>
                                </div>
                            </form>
                        </div>
                    </div>

                    <!-- Sidebar column -->
                    <div class="sidebar">
                        <div class="sidebar-card">
                            <h4>{t('profile.avatar')}</h4>
                            <form method="POST" action="/me/avatar" enctype="multipart/form-data">
                                <input type="hidden" name="csrf_token" value="{csrf_token}">
                                <div class="image-upload">
                                    {avatar_preview}
                                    <div class="image-upload-info">
                                        <input type="file" name="avatar" accept="image/png,image/jpeg,image/webp,image/gif">
                                        <small>{t('profile.image_requirements')}</small>
                                    </div>
                                </div>
                                <button type="submit" class="btn btn-outline" style="width:100%;margin-top:0.75rem;">{t('profile.upload')}</button>
                            </form>
                        </div>

                        <div class="sidebar-card">
                            <h4>{t('profile.cover_image')}</h4>
                            <form method="POST" action="/me/cover" enctype="multipart/form-data">
                                <input type="hidden" name="csrf_token" value="{csrf_token}">
                                <div class="image-upload">
                                    {cover_preview}
                                    <div class="image-upload-info">
                                        <input type="file" name="cover" accept="image/png,image/jpeg,image/webp,image/gif">
                                        <small>{t('profile.cover_requirements')}</small>
                                    </div>
                                </div>
                                <button type="submit" class="btn btn-outline" style="width:100%;margin-top:0.75rem;">{t('profile.upload')}</button>
                            </form>
                        </div>

                        <div class="sidebar-card">
                            <h4>{t('profile.verification')}</h4>
                            {verification_html}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <footer style="text-align:center;padding:2rem 1rem;margin-top:2rem;border-top:1px solid #e2e8f0;color:#64748b;font-size:0.875rem;">
            <p>&copy; {site_title}</p>
        </footer>
    </body>
    </html>
    '''

    response = HTMLResponse(content=html)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=3600,
    )
    return response


@router.post("/me/profile")
async def update_profile(
    request: Request,
    email: str = Form(None),
    display_name: str = Form(None),
    phone: str = Form(None),
    bio: str = Form(None),
    visibility: str = Form("public"),
    csrf_token: str = Form(...),
):
    """Update current user's profile."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]

    # Verify CSRF
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not secrets.compare_digest(csrf_token, csrf_cookie):
        return RedirectResponse(url="/me/profile?error=Invalid+request", status_code=303)

    # Check authentication
    session_id = request.cookies.get("session_id")
    session = auth.verify_session(session_id) if session_id else None

    if not session:
        return RedirectResponse(url="/login", status_code=303)

    username = session.user_id
    user_data = storage.get(f"users.{username}")

    if not user_data:
        return RedirectResponse(url="/login", status_code=303)

    # Update fields
    user_data["email"] = email.strip().lower() if email else None
    user_data["display_name"] = display_name.strip() if display_name else None
    user_data["phone"] = phone.strip() if phone else None
    user_data["bio"] = bio.strip() if bio else None
    user_data["profile_visibility"] = visibility if visibility in ("public", "private") else "public"

    storage.set(f"users.{username}", user_data)

    return RedirectResponse(
        url="/me/profile?success=" + t("profile.profile_updated").replace(" ", "+"),
        status_code=303
    )


@router.post("/me/password")
async def update_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...),
):
    """Update current user's password."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]

    # Verify CSRF
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not secrets.compare_digest(csrf_token, csrf_cookie):
        return RedirectResponse(url="/me/profile?error=Invalid+request", status_code=303)

    # Check authentication
    session_id = request.cookies.get("session_id")
    session = auth.verify_session(session_id) if session_id else None

    if not session:
        return RedirectResponse(url="/login", status_code=303)

    username = session.user_id
    user_data = storage.get(f"users.{username}")

    if not user_data:
        return RedirectResponse(url="/login", status_code=303)

    # Verify current password
    if not auth.verify_password(current_password, user_data.get("password_hash", "")):
        return RedirectResponse(
            url="/me/profile?error=" + t("profile.wrong_password").replace(" ", "+"),
            status_code=303
        )

    # Validate new passwords
    if new_password != confirm_password:
        return RedirectResponse(
            url="/me/profile?error=" + t("auth.passwords_mismatch").replace(" ", "+"),
            status_code=303
        )

    if len(new_password) < 12:
        return RedirectResponse(
            url="/me/profile?error=" + t("auth.password_too_short").replace(" ", "+"),
            status_code=303
        )

    # Update password
    user_data["password_hash"] = auth.hash_password(new_password)
    storage.set(f"users.{username}", user_data)

    return RedirectResponse(
        url="/me/profile?success=" + t("profile.password_updated").replace(" ", "+"),
        status_code=303
    )


@router.post("/me/avatar")
async def upload_avatar(
    request: Request,
    avatar: UploadFile = File(...),
    csrf_token: str = Form(...),
):
    """Upload avatar image."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]

    # Verify CSRF
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not secrets.compare_digest(csrf_token, csrf_cookie):
        return RedirectResponse(url="/me/profile?error=Invalid+request", status_code=303)

    # Check authentication
    session_id = request.cookies.get("session_id")
    session = auth.verify_session(session_id) if session_id else None

    if not session:
        return RedirectResponse(url="/login", status_code=303)

    username = session.user_id
    user_data = storage.get(f"users.{username}")

    if not user_data:
        return RedirectResponse(url="/login", status_code=303)

    # Validate file
    if not avatar.filename:
        return RedirectResponse(url="/me/profile?error=No+file+selected", status_code=303)

    # Check extension
    ext = avatar.filename.rsplit(".", 1)[-1].lower() if "." in avatar.filename else ""
    if ext not in IMAGE_EXTENSIONS:
        return RedirectResponse(url="/me/profile?error=Invalid+file+type", status_code=303)

    # Read file content
    content = await avatar.read()

    # Check size
    if len(content) > MAX_PROFILE_IMAGE_SIZE:
        return RedirectResponse(url="/me/profile?error=File+too+large", status_code=303)

    # Validate magic bytes (security: prevent extension spoofing)
    if not _validate_image_magic_bytes(content, ext):
        return RedirectResponse(url="/me/profile?error=Invalid+image+file", status_code=303)

    # Re-encode image to strip EXIF metadata and hidden payloads
    clean_content = _reencode_image(content, ext)
    if clean_content is None:
        return RedirectResponse(url="/me/profile?error=Could+not+process+image", status_code=303)

    # Generate UUID and save
    file_uuid = str(uuid.uuid4())
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"{file_uuid}.{ext}"
    file_path.write_bytes(clean_content)

    # Sanitize filename for metadata
    safe_filename = "".join(c for c in avatar.filename if c.isalnum() or c in "._- ")[:100]

    # Save metadata
    upload_meta = {
        "uuid": file_uuid,
        "original_name": safe_filename,
        "mime_type": f"image/{ext}" if ext != "jpg" else "image/jpeg",
        "size": len(clean_content),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "uploaded_by": username,
    }
    storage.set(f"uploads.{file_uuid}", upload_meta)

    # Update user avatar
    user_data["avatar_uuid"] = file_uuid
    storage.set(f"users.{username}", user_data)

    return RedirectResponse(
        url="/me/profile?success=" + t("profile.avatar_updated").replace(" ", "+"),
        status_code=303
    )


@router.post("/me/cover")
async def upload_cover(
    request: Request,
    cover: UploadFile = File(...),
    csrf_token: str = Form(...),
):
    """Upload cover image."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]

    # Verify CSRF
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not secrets.compare_digest(csrf_token, csrf_cookie):
        return RedirectResponse(url="/me/profile?error=Invalid+request", status_code=303)

    # Check authentication
    session_id = request.cookies.get("session_id")
    session = auth.verify_session(session_id) if session_id else None

    if not session:
        return RedirectResponse(url="/login", status_code=303)

    username = session.user_id
    user_data = storage.get(f"users.{username}")

    if not user_data:
        return RedirectResponse(url="/login", status_code=303)

    # Validate file
    if not cover.filename:
        return RedirectResponse(url="/me/profile?error=No+file+selected", status_code=303)

    # Check extension
    ext = cover.filename.rsplit(".", 1)[-1].lower() if "." in cover.filename else ""
    if ext not in IMAGE_EXTENSIONS:
        return RedirectResponse(url="/me/profile?error=Invalid+file+type", status_code=303)

    # Read file content
    content = await cover.read()

    # Check size
    if len(content) > MAX_PROFILE_IMAGE_SIZE:
        return RedirectResponse(url="/me/profile?error=File+too+large", status_code=303)

    # Validate magic bytes (security: prevent extension spoofing)
    if not _validate_image_magic_bytes(content, ext):
        return RedirectResponse(url="/me/profile?error=Invalid+image+file", status_code=303)

    # Re-encode image to strip EXIF metadata and hidden payloads
    clean_content = _reencode_image(content, ext)
    if clean_content is None:
        return RedirectResponse(url="/me/profile?error=Could+not+process+image", status_code=303)

    # Generate UUID and save
    file_uuid = str(uuid.uuid4())
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"{file_uuid}.{ext}"
    file_path.write_bytes(clean_content)

    # Sanitize filename for metadata
    safe_filename = "".join(c for c in cover.filename if c.isalnum() or c in "._- ")[:100]

    # Save metadata
    upload_meta = {
        "uuid": file_uuid,
        "original_name": safe_filename,
        "mime_type": f"image/{ext}" if ext != "jpg" else "image/jpeg",
        "size": len(clean_content),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "uploaded_by": username,
    }
    storage.set(f"uploads.{file_uuid}", upload_meta)

    # Update user cover
    user_data["cover_image_uuid"] = file_uuid
    storage.set(f"users.{username}", user_data)

    return RedirectResponse(
        url="/me/profile?success=" + t("profile.cover_updated").replace(" ", "+"),
        status_code=303
    )


@router.post("/me/request-verification")
async def request_verification(
    request: Request,
    csrf_token: str = Form(...),
):
    """Request profile verification."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]

    # Verify CSRF
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not secrets.compare_digest(csrf_token, csrf_cookie):
        return RedirectResponse(url="/me/profile?error=Invalid+request", status_code=303)

    # Check authentication
    session_id = request.cookies.get("session_id")
    session = auth.verify_session(session_id) if session_id else None

    if not session:
        return RedirectResponse(url="/login", status_code=303)

    username = session.user_id
    user_data = storage.get(f"users.{username}")

    if not user_data:
        return RedirectResponse(url="/login", status_code=303)

    # Check if already verified or pending
    if user_data.get("is_verified"):
        return RedirectResponse(url="/me/profile", status_code=303)

    if user_data.get("verification_requested_at"):
        return RedirectResponse(
            url="/me/profile?error=" + t("profile.verification_already_requested").replace(" ", "+"),
            status_code=303
        )

    # Set verification requested
    user_data["verification_requested_at"] = datetime.now(timezone.utc).isoformat()
    storage.set(f"users.{username}", user_data)

    return RedirectResponse(
        url="/me/profile?success=" + t("profile.verification_requested").replace(" ", "+"),
        status_code=303
    )
