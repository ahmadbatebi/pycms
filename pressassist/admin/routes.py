"""Admin API routes for ChelCheleh."""

import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from ..core.i18n import i18n, t
from ..core.language_middleware import (
    get_admin_language_from_request,
    get_admin_direction_from_request,
    ADMIN_LANGUAGE_COOKIE,
)
from ..core.languages import get_available_languages, is_rtl

# CMS Info
CMS_VERSION = "0.1.0"


def get_admin_common_css() -> str:
    """Return link to admin common CSS file."""
    return '<link rel="stylesheet" href="/admin/static/css/admin-common.css">'


def get_admin_footer() -> str:
    """Generate admin footer with translated CMS name and designer credit."""
    cms_name = t('cms.name')
    designed_by = t('cms.designed_by')
    return f'''
<footer style="text-align:center;padding:2rem 1rem;margin-top:2rem;border-top:1px solid #e2e8f0;color:#64748b;font-size:0.875rem;">
    <p>{cms_name} v{CMS_VERSION}</p>
    <p>{designed_by}
        <a href="https://github.com/ahmadbatebi/pycms" target="_blank" style="margin-left:0.5rem;color:#64748b;">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle;">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
        </a>
    </p>
</footer>
'''


def get_page_options_for_association(storage, current_slug: str, selected_slug: str | None) -> str:
    """Generate HTML options for page association dropdown.

    Args:
        storage: Storage instance to get pages from.
        current_slug: Current page slug to exclude from options.
        selected_slug: Currently selected associated page slug.

    Returns:
        HTML string with option elements.
    """
    import html as _html

    pages = storage.get("pages", {})
    options = []
    for slug, page in pages.items():
        if slug == current_slug:
            continue
        title = _html.escape(page.get("title", slug))
        lang = page.get("language", "both")
        lang_label = {"en": "EN", "fa": "FA", "both": "Both"}.get(lang, "")
        selected = "selected" if slug == selected_slug else ""
        options.append(f'<option value="{slug}" {selected}>{title} [{lang_label}]</option>')
    return "\n".join(options)


def get_post_options_for_association(storage, current_slug: str, selected_slug: str | None) -> str:
    """Generate HTML options for blog post association dropdown.

    Args:
        storage: Storage instance to get posts from.
        current_slug: Current post slug to exclude from options.
        selected_slug: Currently selected associated post slug.

    Returns:
        HTML string with option elements.
    """
    import html as _html

    posts = storage.get("blog_posts", {})
    options = []
    for slug, post in posts.items():
        if slug == current_slug:
            continue
        title = _html.escape(post.get("title", slug))
        lang = post.get("language", "both")
        lang_label = {"en": "EN", "fa": "FA", "both": "Both"}.get(lang, "")
        selected = "selected" if slug == selected_slug else ""
        options.append(f'<option value="{slug}" {selected}>{title} [{lang_label}]</option>')
    return "\n".join(options)


def get_category_options_for_association(storage, current_slug: str, selected_slug: str | None) -> str:
    """Generate HTML options for category association dropdown.

    Args:
        storage: Storage instance to get categories from.
        current_slug: Current category slug to exclude from options.
        selected_slug: Currently selected associated category slug.

    Returns:
        HTML string with option elements.
    """
    import html as _html

    categories = storage.get("blog_categories", {})
    options = []
    for slug, cat in categories.items():
        if slug == current_slug:
            continue
        name = _html.escape(cat.get("name", slug))
        lang = cat.get("language", "both")
        lang_label = {"en": "EN", "fa": "FA", "both": "Both"}.get(lang, "")
        selected = "selected" if slug == selected_slug else ""
        options.append(f'<option value="{slug}" {selected}>{name} [{lang_label}]</option>')
    return "\n".join(options)


def get_admin_nav() -> str:
    """Generate admin navigation menu."""
    return f'''
    <nav class="admin-nav" style="background:#f8fafc;border-bottom:1px solid #e2e8f0;padding:0.75rem 2rem;">
        <div style="max-width:1400px;margin:0 auto;display:flex;flex-wrap:wrap;gap:0.5rem 1.5rem;justify-content:center;">
            <a href="/admin/" style="color:#475569;text-decoration:none;padding:0.25rem 0;font-size:0.9rem;">{t('admin.dashboard')}</a>
            <a href="/admin/pages" style="color:#475569;text-decoration:none;padding:0.25rem 0;font-size:0.9rem;">{t('admin.pages.title')}</a>
            <a href="/admin/blog" style="color:#475569;text-decoration:none;padding:0.25rem 0;font-size:0.9rem;">{t('admin.blog.title')}</a>
            <a href="/admin/users" style="color:#475569;text-decoration:none;padding:0.25rem 0;font-size:0.9rem;">{t('admin.users.title')}</a>
            <a href="/admin/menu" style="color:#475569;text-decoration:none;padding:0.25rem 0;font-size:0.9rem;">{t('admin.menu.title')}</a>
            <a href="/admin/templates" style="color:#475569;text-decoration:none;padding:0.25rem 0;font-size:0.9rem;">{t('admin.themes.title')}</a>
            <a href="/admin/blocks" style="color:#475569;text-decoration:none;padding:0.25rem 0;font-size:0.9rem;">{t('admin.blocks.title')}</a>
            <a href="/admin/uploads" style="color:#475569;text-decoration:none;padding:0.25rem 0;font-size:0.9rem;">{t('admin.uploads.title')}</a>
            <a href="/admin/settings" style="color:#475569;text-decoration:none;padding:0.25rem 0;font-size:0.9rem;">{t('admin.settings.title')}</a>
        </div>
    </nav>
    '''


def get_admin_header_right(lang_switcher: str, user_id: str) -> str:
    """Generate admin header right section with user info and actions."""
    return f'''
        {lang_switcher}
        <a href="/" target="_blank" style="color:#94a3b8;text-decoration:none;">{t('admin.view_site')}</a>
        <span style="color:#94a3b8;">|</span>
        <span style="color:#94a3b8;">{user_id}</span>
        <span style="color:#94a3b8;">|</span>
        <a href="/admin/logout" style="color:#94a3b8;text-decoration:none;">{t('admin.logout')}</a>
    '''


from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from ..core.models import Role

# Allowed upload extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "pdf", "doc", "docx", "txt"}

# Image extensions that can be re-encoded
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

# Maximum upload size: 5MB
MAX_UPLOAD_SIZE = 5 * 1024 * 1024

# Magic bytes for file validation
MAGIC_BYTES = {
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
    "webp": b"RIFF",
    "gif": b"GIF8",
    "pdf": b"%PDF-",
    "doc": b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1",
    "docx": b"PK\x03\x04",
}

router = APIRouter(prefix="/admin", tags=["admin"])


def get_wysiwyg_head() -> str:
    """Generate CSS assets for WYSIWYG editor (goes in <head>)."""
    return '''
    <!-- Editor custom styles -->
    <link rel="stylesheet" href="/admin/static/css/wysiwyg/editor-theme.css">
    <link rel="stylesheet" href="/admin/static/css/wysiwyg/editor-rtl.css">
    <link rel="stylesheet" href="/admin/static/css/wysiwyg/editor-decoupled.css">
    <style>
        /* Decoupled Editor Container Styles */
        .ck-editor-container {
            width: 100%;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            overflow: hidden;
        }
        .ck-toolbar-container {
            background: linear-gradient(to bottom, #faf5ff, #f3e8ff);
            border-bottom: 1px solid #e2e8f0;
        }
        .ck-toolbar-container .ck.ck-toolbar {
            border: none !important;
            background: transparent !important;
            padding: 8px 12px !important;
            flex-wrap: wrap !important;
            direction: rtl !important;
        }
        .ck-editable-container {
            min-height: 350px;
            max-height: 600px;
            overflow-y: auto;
            padding: 20px 24px;
            font-family: 'Vazirmatn', Tahoma, Arial, sans-serif;
            font-size: 16px;
            line-height: 1.8;
            direction: rtl;
            text-align: right;
            background: #fff;
        }
        .ck-editable-container:focus {
            outline: none;
        }
        .ck-editable-container .ck-content {
            min-height: 300px;
        }
        .ck-editable-container .ck-content:focus {
            outline: none;
            box-shadow: none;
        }
        /* Alignment styles for RTL */
        .ck-content[style*="text-align:right"], .ck-content [style*="text-align:right"] { text-align: right; }
        .ck-content[style*="text-align:left"], .ck-content [style*="text-align:left"] { text-align: left; }
        .ck-content[style*="text-align:center"], .ck-content [style*="text-align:center"] { text-align: center; }
        .ck-content[style*="text-align:justify"], .ck-content [style*="text-align:justify"] { text-align: justify; }
    </style>
    '''


def get_wysiwyg_scripts(csrf_token: str) -> str:
    """Generate JS assets for WYSIWYG editor (goes at end of <body>)."""
    return f'''
    <!-- CKEditor 5 Decoupled Document Build (self-hosted v41.4.2) -->
    <script src="/admin/static/vendor/ckeditor5/ckeditor.js"></script>
    <script src="/admin/static/vendor/ckeditor5/translations-fa.js"></script>

    <!-- CSRF token for uploads -->
    <script>window.CHELCHELEH_CSRF_TOKEN = {csrf_token!r};</script>
    <script src="/admin/static/js/wysiwyg/decoupled-init.js"></script>
    '''


def get_csrf_token(request: Request) -> tuple[str, bool]:
    """Get CSRF token and indicate whether cookie needs setting."""
    token = request.cookies.get("csrf_token")
    if token:
        return token, False
    return secrets.token_urlsafe(32), True


def get_admin_lang_context(request: Request) -> dict:
    """Get language context for admin panel.

    Returns:
        Dictionary with lang, direction, is_rtl, available_languages.
    """
    lang = get_admin_language_from_request(request)
    direction = get_admin_direction_from_request(request)
    i18n.set_language(lang)

    return {
        "lang": lang,
        "direction": direction,
        "is_rtl": direction == "rtl",
        "available_languages": get_available_languages(),
        "t": t,
    }


def get_admin_html_attrs(request: Request) -> str:
    """Get HTML tag attributes for admin panel RTL support.

    Returns:
        String like 'lang="fa" dir="rtl"'.
    """
    ctx = get_admin_lang_context(request)
    return f'lang="{ctx["lang"]}" dir="{ctx["direction"]}"'


def get_admin_language_switcher_html(request: Request) -> str:
    """Generate language switcher HTML for admin header.

    Returns:
        HTML string for language switcher with flag icons.
    """
    ctx = get_admin_lang_context(request)
    current_lang = ctx["lang"]
    langs = ctx["available_languages"]

    if len(langs) <= 1:
        return ""

    # Flag icons - Lion and Sun for Persian (using external file), UK flag for English
    flag_icons = {
        "fa": '''<img src="/themes/default/static/img/lion-sun.svg" alt="فارسی" width="22" height="16" style="vertical-align:middle;">''',
        "en": '''<svg viewBox="0 0 60 30" width="22" height="16" style="vertical-align:middle;"><clipPath id="admin-uk-s"><path d="M0,0 v30 h60 v-30 z"/></clipPath><clipPath id="admin-uk-t"><path d="M30,15 h30 v15 z v15 h-30 z h-30 v-15 z v-15 h30 z"/></clipPath><g clip-path="url(#admin-uk-s)"><path d="M0,0 v30 h60 v-30 z" fill="#012169"/><path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/><path d="M0,0 L60,30 M60,0 L0,30" clip-path="url(#admin-uk-t)" stroke="#C8102E" stroke-width="4"/><path d="M30,0 v30 M0,15 h60" stroke="#fff" stroke-width="10"/><path d="M30,0 v30 M0,15 h60" stroke="#C8102E" stroke-width="6"/></g></svg>''',
    }

    links = []
    for lang in langs:
        active = "active" if lang["code"] == current_lang else ""
        flag = flag_icons.get(lang["code"], "")
        links.append(
            f'<a href="?lang={lang["code"]}" class="lang-switch-link {active}" '
            f'title="{lang["name"]}">{flag}</a>'
        )

    return f'''
    <div class="lang-switcher" style="display:flex;gap:0.25rem;background:#334155;padding:0.25rem;border-radius:4px;">
        {"".join(links)}
    </div>
    <style>
        .lang-switch-link {{
            padding: 0.35rem 0.5rem;
            color: #94a3b8;
            text-decoration: none;
            font-size: 0.8rem;
            border-radius: 3px;
            transition: all 0.2s;
            display: flex;
            align-items: center;
        }}
        .lang-switch-link:hover {{ color: white; background: #475569; }}
        .lang-switch-link.active {{ color: white; background: #7c3aed; }}
        .lang-switch-link svg, .lang-switch-link img {{ opacity: 0.8; }}
        .lang-switch-link:hover svg, .lang-switch-link.active svg,
        .lang-switch-link:hover img, .lang-switch-link.active img {{ opacity: 1; }}
    </style>
    '''


def get_admin_rtl_styles() -> str:
    """Get RTL-specific styles for admin panel.

    Returns:
        CSS string for RTL support.
    """
    return '''
    <style>
        /* Vazirmatn font for Persian - Local font files */
        @font-face {
            font-family: 'Vazirmatn';
            src: url('/admin/static/fonts/vazirmatn/Vazirmatn-Regular.ttf') format('truetype');
            font-weight: 400;
            font-style: normal;
            font-display: swap;
        }
        @font-face {
            font-family: 'Vazirmatn';
            src: url('/admin/static/fonts/vazirmatn/Vazirmatn-Medium.ttf') format('truetype');
            font-weight: 500;
            font-style: normal;
            font-display: swap;
        }
        @font-face {
            font-family: 'Vazirmatn';
            src: url('/admin/static/fonts/vazirmatn/Vazirmatn-Bold.ttf') format('truetype');
            font-weight: 700;
            font-style: normal;
            font-display: swap;
        }

        /* RTL Support for Admin Panel */
        html[dir="rtl"] body {
            font-family: 'Vazirmatn', Tahoma, Arial, sans-serif;
            text-align: right;
            direction: rtl;
        }
        html[dir="rtl"] .header {
            flex-direction: row;
            justify-content: space-between;
            gap: 1rem;
            direction: rtl;
        }
        html[dir="rtl"] .header h1 {
            text-align: right;
            order: 1;
        }
        html[dir="rtl"] .header-right {
            flex-direction: row-reverse !important;
            direction: rtl;
            text-align: right;
            order: 2;
            margin-right: auto;
        }
        html[dir="rtl"] .nav {
            flex-direction: row-reverse;
        }
        html[dir="rtl"] .nav a {
            margin-right: 0;
            margin-left: 0.5rem;
        }
        html[dir="rtl"] th, html[dir="rtl"] td {
            text-align: right;
        }
        html[dir="rtl"] .form-group label {
            text-align: right;
            display: block;
        }
        html[dir="rtl"] input, html[dir="rtl"] textarea, html[dir="rtl"] select {
            text-align: right;
            direction: rtl;
        }
        html[dir="rtl"] input[type="email"],
        html[dir="rtl"] input[type="url"] {
            direction: ltr;
            text-align: left;
        }
        html[dir="rtl"] .container {
            text-align: right;
            margin-inline-start: auto;
            margin-inline-end: auto;
        }
        html[dir="rtl"] .stats {
            flex-direction: row-reverse;
        }
        html[dir="rtl"] table {
            direction: rtl;
        }
        html[dir="rtl"] .actions {
            text-align: left;
        }
        /* RTL two-col layout - sidebar should be on left in RTL */
        html[dir="rtl"] .two-col {
            direction: rtl;
        }
    </style>
    '''


def set_csrf_cookie(request: Request, response: HTMLResponse, token: str) -> None:
    """Set CSRF cookie on response."""
    use_secure = request.url.scheme == "https"
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,
        samesite="lax",
        secure=use_secure,
        max_age=3600 * 4,
    )


def require_auth(roles: list[Role] | None = None):
    """Dependency to require authentication."""
    async def check_auth(request: Request):
        from ..main import auth, storage

        session_id = request.cookies.get("session_id")
        if not session_id or not auth:
            raise HTTPException(status_code=401, detail="Not authenticated")

        session = auth.verify_session(session_id)
        if not session:
            raise HTTPException(status_code=401, detail="Session expired")

        if roles and session.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return session

    return check_auth


def require_csrf(request: Request):
    """Dependency to verify CSRF token."""
    csrf_header = request.headers.get("X-CSRF-Token", "")
    csrf_cookie = request.cookies.get("csrf_token", "")

    if not csrf_header or not csrf_cookie:
        raise HTTPException(status_code=403, detail="Missing CSRF token")

    if not secrets.compare_digest(csrf_header, csrf_cookie):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


# ============================================================================
# Dashboard
# ============================================================================

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    session=Depends(require_auth()),
):
    """Render admin dashboard."""
    from ..main import storage, theme_manager

    # Get language context
    lang_ctx = get_admin_lang_context(request)
    html_attrs = get_admin_html_attrs(request)
    lang_switcher = get_admin_language_switcher_html(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""
    is_rtl = lang_ctx["is_rtl"]

    # Get site stats
    pages = storage.get("pages", {})
    blocks = storage.get("blocks", {})
    uploads = storage.get("uploads", {})
    users = storage.get("users", {})
    blog_posts = storage.get("blog_posts", {})
    blog_categories = storage.get("blog_categories", {})
    comments = storage.get("blog_comments", {})
    settings = storage.get("settings", {})
    menu_items = storage.get("menu", [])

    # Count JSON data files
    data_dir = Path(storage.data_dir) if hasattr(storage, 'data_dir') else Path("data")
    json_files_count = len(list(data_dir.glob("*.json"))) if data_dir.exists() else 0

    # Get settings info
    site_lang = settings.get("site_lang", "en")
    admin_lang_setting = settings.get("admin_lang", "fa")
    force_https = settings.get("force_https", False)
    site_title = settings.get("site_title", "ChelCheleh")
    default_page = settings.get("default_page", "")
    login_slug = settings.get("login_slug", "admin")

    # Count visible/hidden pages
    visible_pages = sum(1 for p in pages.values() if p.get("visibility") == "show")
    hidden_pages = len(pages) - visible_pages

    # Count published/draft posts
    published_posts = sum(1 for p in blog_posts.values() if p.get("status") == "published")
    draft_posts = len(blog_posts) - published_posts

    # Count active/inactive users
    active_users = sum(1 for u in users.values() if u.get("is_active", True))
    inactive_users = len(users) - active_users

    # Count approved/pending comments
    approved_comments = sum(1 for c in comments.values() if c.get("status") == "approved")
    pending_comments = sum(1 for c in comments.values() if c.get("status") == "pending")

    # RTL-aware positioning
    icon_position = "left" if is_rtl else "right"
    text_align = "right" if is_rtl else "left"

    token, needs_cookie = get_csrf_token(request)
    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.dashboard')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="/admin/static/css/admin-common.css">
        <style>
            /* Dashboard specific styles */
            .dashboard-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }}

            .stat-card {{
                position: relative;
                overflow: hidden;
            }}
            .stat-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                border-radius: 16px 16px 0 0;
            }}
            .stat-card.pages::before {{ background: linear-gradient(90deg, #3b82f6, #60a5fa); }}
            .stat-card.blocks::before {{ background: linear-gradient(90deg, #8b5cf6, #a78bfa); }}
            .stat-card.uploads::before {{ background: linear-gradient(90deg, #10b981, #34d399); }}
            .stat-card.users::before {{ background: linear-gradient(90deg, #f59e0b, #fbbf24); }}
            .stat-card.posts::before {{ background: linear-gradient(90deg, #ec4899, #f472b6); }}
            .stat-card.categories::before {{ background: linear-gradient(90deg, #06b6d4, #22d3ee); }}
            .stat-card.json::before {{ background: linear-gradient(90deg, #84cc16, #a3e635); }}
            .stat-card.comments::before {{ background: linear-gradient(90deg, #f97316, #fb923c); }}
            .stat-card.settings::before {{ background: linear-gradient(90deg, #6366f1, #818cf8); }}

            .stat-icon.pages {{ background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); }}
            .stat-icon.blocks {{ background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%); }}
            .stat-icon.uploads {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); }}
            .stat-icon.users {{ background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }}
            .stat-icon.posts {{ background: linear-gradient(135deg, #ec4899 0%, #be185d 100%); }}
            .stat-icon.categories {{ background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%); }}
            .stat-icon.json {{ background: linear-gradient(135deg, #84cc16 0%, #65a30d 100%); }}
            .stat-icon.comments {{ background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); }}
            .stat-icon.settings {{ background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); }}

            .stat-icon svg {{ width: 24px; height: 24px; }}

            .detail-bar {{
                margin-top: 1rem;
                height: 8px;
                background: #f1f5f9;
                border-radius: 4px;
                overflow: hidden;
                display: flex;
            }}
            .detail-bar .segment {{
                height: 100%;
                transition: width 0.5s ease-out;
            }}
            .segment.pages {{ background: #3b82f6; }}
            .segment.blocks {{ background: #8b5cf6; }}
            .segment.uploads {{ background: #10b981; }}
            .segment.users {{ background: #f59e0b; }}
            .segment.posts {{ background: #ec4899; }}
            .segment.categories {{ background: #06b6d4; }}
            .segment.json {{ background: #84cc16; }}
            .segment.comments {{ background: #f97316; }}
            .segment.secondary {{ background: #cbd5e1; }}
            .segment.warning {{ background: #fbbf24; }}

            .detail-legend {{
                display: flex;
                gap: 1rem;
                margin-top: 0.75rem;
                font-size: 0.8rem;
                flex-wrap: wrap;
            }}
            .detail-legend span {{
                display: flex;
                align-items: center;
                gap: 0.35rem;
                color: #64748b;
            }}
            .detail-legend .dot {{
                width: 10px;
                height: 10px;
                border-radius: 50%;
            }}
            .dot.pages {{ background: #3b82f6; }}
            .dot.blocks {{ background: #8b5cf6; }}
            .dot.uploads {{ background: #10b981; }}
            .dot.users {{ background: #f59e0b; }}
            .dot.posts {{ background: #ec4899; }}
            .dot.categories {{ background: #06b6d4; }}
            .dot.json {{ background: #84cc16; }}
            .dot.comments {{ background: #f97316; }}
            .dot.secondary {{ background: #cbd5e1; }}
            .dot.warning {{ background: #fbbf24; }}

            .settings-card {{
                min-height: auto;
            }}
            .settings-list {{
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
                margin-top: 0.5rem;
            }}
            .settings-list .setting-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.5rem 0;
                border-bottom: 1px solid #f1f5f9;
            }}
            .settings-list .setting-row:last-child {{ border-bottom: none; }}
            .settings-list .label {{ color: #64748b; font-size: 0.85rem; }}
            .settings-list .val {{ font-weight: 600; color: #1e293b; font-size: 0.9rem; }}
            .settings-list .val.success {{ color: #16a34a; }}
            .settings-list .val.warning {{ color: #d97706; }}

            /* Quick Actions */
            .quick-actions-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 1rem;
            }}
            .quick-action-card {{
                display: flex;
                align-items: center;
                gap: 1rem;
                padding: 1.25rem;
                background: #f8fafc;
                border-radius: 12px;
                text-decoration: none;
                color: inherit;
                transition: all 0.2s;
                border: 2px solid transparent;
            }}
            .quick-action-card:hover {{
                background: white;
                border-color: #6366f1;
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(99, 102, 241, 0.15);
            }}
            .quick-action-icon {{
                width: 44px;
                height: 44px;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
                color: white;
            }}
            .quick-action-icon svg {{ width: 22px; height: 22px; }}
            .quick-action-label {{
                font-weight: 600;
                color: #1e293b;
                font-size: 0.95rem;
            }}

            /* About Section */
            .about-section h3 {{
                margin: 1.5rem 0 0.5rem;
                font-size: 1rem;
                color: #475569;
            }}
            .about-section p {{
                line-height: 1.7;
                color: #64748b;
                margin: 0 0 1rem;
            }}
            .about-section .version-info {{
                margin-top: 1.5rem;
                padding-top: 1rem;
                border-top: 1px solid #e2e8f0;
            }}
            .about-section .version-info p {{ margin: 0.25rem 0; }}
            .about-section .hint {{ font-size: 0.875rem; color: #94a3b8; }}

            .about-toggle-input {{ display: none; }}
            .about-details {{
                max-height: 0;
                overflow: hidden;
                transition: max-height 0.4s ease-out, opacity 0.3s ease-out;
                opacity: 0;
            }}
            .about-toggle-input:checked ~ .about-details {{
                max-height: 2000px;
                opacity: 1;
                transition: max-height 0.6s ease-in, opacity 0.3s ease-in;
            }}
            .about-toggle-btn {{
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.625rem 1.25rem;
                background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
                color: #475569;
                border-radius: 8px;
                cursor: pointer;
                font-size: 0.875rem;
                font-weight: 500;
                margin-top: 1rem;
                transition: all 0.2s;
                border: 1px solid #e2e8f0;
            }}
            .about-toggle-btn:hover {{
                background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
                color: #1e293b;
            }}
            .about-toggle-btn svg {{ vertical-align: middle; }}
            .about-toggle-btn .show-less {{ display: none; }}
            .about-toggle-input:checked ~ .about-toggle-btn .show-more {{ display: none; }}
            .about-toggle-input:checked ~ .about-toggle-btn .show-less {{ display: inline-flex; align-items: center; gap: 0.25rem; }}
        </style>
        {rtl_styles}
    </head>
    <body>
        <div class="header">
            <a href="/admin/" style="font-size:1.25rem;font-weight:700;color:white;text-decoration:none;">{t('cms.name_short')}</a>
            <div class="header-right">
                {lang_switcher}
                <a href="/" target="_blank" style="color:#94a3b8;text-decoration:none;">{t('admin.view_site')}</a>
                <span style="color:#64748b;">|</span>
                <span style="color:#e2e8f0;">{session.user_id}</span>
                <a href="/admin/logout" style="color:#f87171;text-decoration:none;">{t('admin.logout')}</a>
            </div>
        </div>
        {get_admin_nav()}
        <div class="container">
            <!-- Page Title -->
            <h1 class="page-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                {t('admin.dashboard')}
            </h1>

            <!-- Quick Actions -->
            <div class="card card-static" style="margin-bottom: 2rem;">
                <div class="card-header info">
                    <div class="card-icon info">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                    </div>
                    <h3 class="card-title">{t('admin.quick_actions')}</h3>
                </div>
                <div class="card-body">
                    <div class="quick-actions-grid">
                        <a href="/admin/pages/new" class="quick-action-card">
                            <div class="quick-action-icon" style="background: linear-gradient(135deg, #3b82f6, #1d4ed8);">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                                </svg>
                            </div>
                            <span class="quick-action-label">{t('admin.pages.new')}</span>
                        </a>
                        <a href="/admin/blog/posts/new" class="quick-action-card">
                            <div class="quick-action-icon" style="background: linear-gradient(135deg, #ec4899, #be185d);">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                            </div>
                            <span class="quick-action-label">{t('admin.blog.new_post')}</span>
                        </a>
                        <a href="/admin/uploads" class="quick-action-card">
                            <div class="quick-action-icon" style="background: linear-gradient(135deg, #10b981, #059669);">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                                </svg>
                            </div>
                            <span class="quick-action-label">{t('admin.uploads.title')}</span>
                        </a>
                        <a href="/admin/settings" class="quick-action-card">
                            <div class="quick-action-icon" style="background: linear-gradient(135deg, #6366f1, #4f46e5);">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                </svg>
                            </div>
                            <span class="quick-action-label">{t('admin.settings.title')}</span>
                        </a>
                    </div>
                </div>
            </div>

            <!-- Statistics Grid Row 1 -->
            <div class="dashboard-grid">
                <div class="stat-card pages">
                    <div class="stat-icon pages">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value">{len(pages)}</div>
                        <div class="stat-label">{t('admin.pages.title')}</div>
                        <div class="detail-bar">
                            <div class="segment pages" style="width:{(visible_pages / max(1, len(pages))) * 100 if len(pages) > 0 else 0}%"></div>
                            <div class="segment secondary" style="width:{(hidden_pages / max(1, len(pages))) * 100 if len(pages) > 0 else 0}%"></div>
                        </div>
                        <div class="detail-legend">
                            <span><span class="dot pages"></span> {t('admin.pages.show')}: {visible_pages}</span>
                            <span><span class="dot secondary"></span> {t('admin.pages.hide')}: {hidden_pages}</span>
                        </div>
                    </div>
                </div>
                <div class="stat-card blocks">
                    <div class="stat-icon blocks">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
                        </svg>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value">{len(blocks)}</div>
                        <div class="stat-label">{t('admin.blocks.title')}</div>
                        <div class="detail-bar">
                            <div class="segment blocks" style="width:100%"></div>
                        </div>
                        <div class="detail-legend">
                            <span><span class="dot blocks"></span> {t('admin.blocks.header')}, {t('admin.blocks.footer')}, {t('admin.blocks.sidebar')}</span>
                        </div>
                    </div>
                </div>
                <div class="stat-card uploads">
                    <div class="stat-icon uploads">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value">{len(uploads)}</div>
                        <div class="stat-label">{t('admin.uploads.title')}</div>
                        <div class="detail-bar">
                            <div class="segment uploads" style="width:100%"></div>
                        </div>
                        <div class="detail-legend">
                            <span><span class="dot uploads"></span> {t('admin.uploads.file_name')}</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Statistics Grid Row 2 -->
            <div class="dashboard-grid">
                <div class="stat-card users">
                    <div class="stat-icon users">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                        </svg>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value">{len(users)}</div>
                        <div class="stat-label">{t('admin.users.title')}</div>
                        <div class="detail-bar">
                            <div class="segment users" style="width:{(active_users / max(1, len(users))) * 100 if len(users) > 0 else 0}%"></div>
                            <div class="segment secondary" style="width:{(inactive_users / max(1, len(users))) * 100 if len(users) > 0 else 0}%"></div>
                        </div>
                        <div class="detail-legend">
                            <span><span class="dot users"></span> {t('admin.stats.enabled')}: {active_users}</span>
                            <span><span class="dot secondary"></span> {t('admin.stats.disabled')}: {inactive_users}</span>
                        </div>
                    </div>
                </div>
                <div class="stat-card posts">
                    <div class="stat-icon posts">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                        </svg>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value">{len(blog_posts)}</div>
                        <div class="stat-label">{t('admin.blog.posts')}</div>
                        <div class="detail-bar">
                            <div class="segment posts" style="width:{(published_posts / max(1, len(blog_posts))) * 100 if len(blog_posts) > 0 else 0}%"></div>
                            <div class="segment secondary" style="width:{(draft_posts / max(1, len(blog_posts))) * 100 if len(blog_posts) > 0 else 0}%"></div>
                        </div>
                        <div class="detail-legend">
                            <span><span class="dot posts"></span> {t('admin.blog.published')}: {published_posts}</span>
                            <span><span class="dot secondary"></span> {t('admin.blog.draft')}: {draft_posts}</span>
                        </div>
                    </div>
                </div>
                <div class="stat-card categories">
                    <div class="stat-icon categories">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                        </svg>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value">{len(blog_categories)}</div>
                        <div class="stat-label">{t('admin.blog.categories')}</div>
                        <div class="detail-bar">
                            <div class="segment categories" style="width:100%"></div>
                        </div>
                        <div class="detail-legend">
                            <span><span class="dot categories"></span> {t('admin.menu.items')}: {len(menu_items)}</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Statistics Grid Row 3 -->
            <div class="dashboard-grid">
                <div class="stat-card json">
                    <div class="stat-icon json">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                        </svg>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value">{json_files_count}</div>
                        <div class="stat-label">{t('admin.stats.json_files')}</div>
                        <div class="detail-bar">
                            <div class="segment json" style="width:100%"></div>
                        </div>
                        <div class="detail-legend">
                            <span><span class="dot json"></span> Flat-File Storage</span>
                        </div>
                    </div>
                </div>
                <div class="stat-card comments">
                    <div class="stat-icon comments">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                    </div>
                    <div class="stat-content">
                        <div class="stat-value">{len(comments)}</div>
                        <div class="stat-label">{t('admin.stats.total_comments')}</div>
                        <div class="detail-bar">
                            <div class="segment comments" style="width:{(approved_comments / max(1, len(comments))) * 100 if len(comments) > 0 else 0}%"></div>
                            <div class="segment warning" style="width:{(pending_comments / max(1, len(comments))) * 100 if len(comments) > 0 else 0}%"></div>
                        </div>
                        <div class="detail-legend">
                            <span><span class="dot comments"></span> {t('admin.blog.approved')}: {approved_comments}</span>
                            <span><span class="dot warning"></span> {t('admin.blog.pending')}: {pending_comments}</span>
                        </div>
                    </div>
                </div>
                <div class="stat-card settings settings-card">
                    <div class="stat-icon settings">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                    </div>
                    <div class="stat-content" style="width: 100%;">
                        <div class="stat-label" style="margin-bottom: 0.5rem;">{t('admin.stats.settings_overview')}</div>
                        <div class="settings-list">
                            <div class="setting-row"><span class="label">{t('admin.settings.site_title')}:</span> <span class="val">{site_title[:20]}{'...' if len(site_title) > 20 else ''}</span></div>
                            <div class="setting-row"><span class="label">{t('admin.stats.site_language')}:</span> <span class="val">{site_lang.upper()}</span></div>
                            <div class="setting-row"><span class="label">{t('admin.stats.admin_language')}:</span> <span class="val">{admin_lang_setting.upper()}</span></div>
                            <div class="setting-row"><span class="label">{t('admin.stats.https_status')}:</span> <span class="val {'success' if force_https else 'warning'}">{t('admin.stats.enabled') if force_https else t('admin.stats.disabled')}</span></div>
                            <div class="setting-row"><span class="label">{t('admin.settings.default_page')}:</span> <span class="val">{default_page if default_page else '-'}</span></div>
                            <div class="setting-row"><span class="label">{t('admin.settings.login_slug')}:</span> <span class="val">/{login_slug}</span></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- About Section -->
            <div class="card card-static" style="margin-top: 2rem;">
                <div class="card-header purple">
                    <div class="card-icon purple">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                    <h3 class="card-title">{t('cms.about_title')}</h3>
                </div>
                <div class="card-body about-section">
                    <p>{t('cms.about_intro')}</p>

                    <input type="checkbox" id="about-toggle" class="about-toggle-input">
                    <div class="about-details">
                        <h3>{t('cms.about_flatfile_title')}</h3>
                        <p>{t('cms.about_flatfile')}</p>

                        <h3>{t('cms.about_storage_title')}</h3>
                        <p>{t('cms.about_storage')}</p>

                        <h3>{t('cms.about_tech_title')}</h3>
                        <p>{t('cms.about_tech')}</p>

                        <h3>{t('cms.about_features_title')}</h3>
                        <p>{t('cms.about_features')}</p>

                        <h3>{t('cms.about_security_title')}</h3>
                        <p>{t('cms.about_security')}</p>

                        <div class="version-info">
                            <p><strong>{t('cms.about_version').replace('{version}', CMS_VERSION)}</strong></p>
                            <p class="hint">{t('cms.about_update_hint')}</p>
                        </div>
                    </div>
                    <label for="about-toggle" class="about-toggle-btn">
                        <span class="show-more">{t('cms.about_read_more')} <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></span>
                        <span class="show-less">{t('cms.about_read_less')} <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 15l-6-6-6 6"/></svg></span>
                    </label>
                </div>
            </div>
        </div>
        {get_admin_footer()}
    </body>
    </html>
    """
    return HTMLResponse(html)

@router.get("/pages", response_class=HTMLResponse)
async def pages_list(
    request: Request,
    session=Depends(require_auth()),
):
    """Render pages list."""
    import html as _html
    from urllib.parse import quote as _quote

    from ..main import storage

    # Get language context
    lang_ctx = get_admin_lang_context(request)
    html_attrs = get_admin_html_attrs(request)
    lang_switcher = get_admin_language_switcher_html(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""

    token, needs_cookie = get_csrf_token(request)
    pages = storage.get("pages", {})

    # Build table rows with improved design
    rows_list = []
    for p in sorted(pages.values(), key=lambda x: x.get('title', '')):
        slug = _html.escape(p.get('slug', ''))
        title = _html.escape(p.get('title', ''))
        visibility = p.get('visibility', 'show')
        is_visible = visibility == 'show'
        badge_class = 'badge-success' if is_visible else 'badge-gray'
        badge_text = t('admin.pages.show') if is_visible else t('admin.pages.hide')
        toggle_icon = 'M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21' if is_visible else 'M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z'
        rows_list.append(f'''
            <tr data-slug="{slug}" data-visibility="{visibility}">
                <td>
                    <div style="display:flex;align-items:center;gap:0.75rem;">
                        <div style="width:40px;height:40px;border-radius:10px;background:linear-gradient(135deg,#3b82f6,#1d4ed8);display:flex;align-items:center;justify-content:center;color:white;flex-shrink:0;">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </div>
                        <div>
                            <div style="font-weight:600;color:#1e293b;">{title}</div>
                            <div style="font-size:0.85rem;color:#64748b;">/{slug}</div>
                        </div>
                    </div>
                </td>
                <td><span class="badge {badge_class}">{badge_text}</span></td>
                <td class="actions-cell">
                    <div class="actions">
                        <a href="/admin/pages/edit/{_quote(p.get('slug',''))}" class="btn btn-sm btn-secondary" title="{t('common.edit')}">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                            {t('common.edit')}
                        </a>
                        <button class="btn btn-sm btn-outline toggle-btn" type="button" title="{t('admin.pages.visibility')}">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="{toggle_icon}" />
                            </svg>
                        </button>
                        <button class="btn btn-sm btn-danger delete-btn" data-slug="{slug}" type="button" title="{t('common.delete')}">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        ''')
    rows = "\n".join(rows_list)

    empty_state = ""
    if not pages:
        empty_state = f'''
            <div class="empty-state">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <h3>{t('admin.pages.no_pages')}</h3>
                <p>{t('admin.pages.create_first')}</p>
            </div>
        '''

    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.pages.title')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="/admin/static/css/admin-common.css">
        <style>
            .actions-cell {{
                width: 200px;
            }}
            .actions-cell .actions {{
                justify-content: flex-end;
            }}
            [dir="rtl"] .actions-cell .actions {{
                justify-content: flex-start;
            }}
        </style>
        {rtl_styles}
    </head>
    <body>
        <div class="header">
            <a href="/admin/" style="font-size:1.25rem;font-weight:700;color:white;text-decoration:none;">{t('cms.name_short')}</a>
            <div class="header-right">
                {lang_switcher}
                <a href="/" target="_blank" style="color:#94a3b8;text-decoration:none;">{t('admin.view_site')}</a>
                <span style="color:#64748b;">|</span>
                <span style="color:#e2e8f0;">{session.user_id}</span>
                <a href="/admin/logout" style="color:#f87171;text-decoration:none;">{t('admin.logout')}</a>
            </div>
        </div>
        {get_admin_nav()}
        <div class="container">
            <!-- Page Header -->
            <div class="page-header">
                <h1 class="page-title">
                    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    {t('admin.pages.title')}
                </h1>
                <a class="btn btn-primary" href="/admin/pages/new">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                    </svg>
                    {t('admin.pages.new')}
                </a>
            </div>

            <!-- Error Message -->
            <div id="msg" class="alert alert-error" style="display:none;"></div>

            <!-- Pages Table -->
            <div class="card card-static">
                <div class="card-header primary">
                    <div class="card-icon primary">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                        </svg>
                    </div>
                    <h3 class="card-title">{t('admin.pages.all_pages')} ({len(pages)})</h3>
                </div>
                {"<div class='card-body'>" + empty_state + "</div>" if not pages else f'''
                <div class="table-container">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>{t('admin.pages.page_info')}</th>
                                <th>{t('common.status')}</th>
                                <th style="text-align:right;">{t('common.actions')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows}
                        </tbody>
                    </table>
                </div>
                '''}
            </div>
        </div>
        <script>
            const csrfToken = {token!r};
            const showMsg = (text, type = 'error') => {{
                const msg = document.getElementById('msg');
                msg.textContent = text;
                msg.className = 'alert alert-' + type;
                msg.style.display = 'flex';
                setTimeout(() => {{ msg.style.display = 'none'; }}, 5000);
            }};

            document.querySelectorAll('.delete-btn').forEach((btn) => {{
                btn.addEventListener('click', async (e) => {{
                    const slug = e.target.closest('.delete-btn').dataset.slug;
                    if (slug === 'home' || slug === '404') {{
                        showMsg('{t("admin.pages.cannot_delete_system")}');
                        return;
                    }}
                    if (!confirm('{t("admin.pages.confirm_delete")}')) return;
                    const res = await fetch(`/admin/api/pages/${{encodeURIComponent(slug)}}`, {{
                        method: 'DELETE',
                        headers: {{ 'X-CSRF-Token': csrfToken }},
                        credentials: 'same-origin',
                    }});
                    if (!res.ok) {{
                        const text = await res.text();
                        showMsg(text || '{t("admin.pages.delete_failed")}');
                        return;
                    }}
                    e.target.closest('tr').remove();
                    showMsg('{t("admin.pages.deleted_success")}', 'success');
                }});
            }});

            document.querySelectorAll('.toggle-btn').forEach((btn) => {{
                btn.addEventListener('click', async (e) => {{
                    const row = e.target.closest('tr');
                    const slug = row.dataset.slug;
                    const current = row.dataset.visibility || 'show';
                    const next = current === 'show' ? 'hide' : 'show';
                    const res = await fetch(`/admin/api/pages/${{encodeURIComponent(slug)}}`, {{
                        method: 'PUT',
                        headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken }},
                        credentials: 'same-origin',
                        body: JSON.stringify({{ visibility: next }}),
                    }});
                    if (!res.ok) {{
                        const text = await res.text();
                        showMsg(text || '{t("admin.pages.update_failed")}');
                        return;
                    }}
                    row.dataset.visibility = next;
                    // Update badge
                    const badge = row.querySelector('.badge');
                    if (next === 'show') {{
                        badge.className = 'badge badge-success';
                        badge.textContent = '{t("admin.pages.show")}';
                    }} else {{
                        badge.className = 'badge badge-gray';
                        badge.textContent = '{t("admin.pages.hide")}';
                    }}
                    showMsg('{t("admin.pages.visibility_updated")}', 'success');
                }});
            }});
        </script>
        {get_admin_footer()}
    </body>
    </html>
    """
    response = HTMLResponse(html)
    if needs_cookie:
        set_csrf_cookie(request, response, token)
    return response

@router.get("/logout")
async def logout(request: Request):
    """Handle logout and redirect to login page."""
    from ..main import auth, audit_logger, storage

    session_id = request.cookies.get("session_id")
    if session_id and auth:
        session = auth.verify_session(session_id)
        if session:
            auth.invalidate_session(session.session_id)
            if audit_logger:
                audit_logger.log_logout(
                    session.user_id,
                    request.client.host if request.client else None,
                )

    # Redirect to the current login_slug
    login_slug = storage.get("config.login_slug", "") if storage else ""
    redirect_url = f"/{login_slug}" if login_slug else "/"

    response = RedirectResponse(url=redirect_url, status_code=303)
    secure_cookie = storage.get("config.force_https", True) if storage else True
    response.delete_cookie("session_id", secure=secure_cookie, samesite="lax")
    return response


@router.get("/pages/new", response_class=HTMLResponse)
async def page_new(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
):
    """Render new page form."""
    html_attrs = get_admin_html_attrs(request)
    lang_ctx = get_admin_lang_context(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""
    lang_switcher = get_admin_language_switcher_html(request)
    csrf_token, needs_cookie = get_csrf_token(request)
    wysiwyg_head = get_wysiwyg_head()
    wysiwyg_scripts = get_wysiwyg_scripts(csrf_token)
    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.pages.new')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        {get_admin_common_css()}
        {rtl_styles}
        {wysiwyg_head}
    </head>
    <body>
        <div class="header">
            <a href="/admin/" class="header-logo">{t('cms.name_short')}</a>
            <div class="header-right">
                {lang_switcher}
                <a href="/" target="_blank">{t('admin.view_site')}</a>
                <span class="header-separator">|</span>
                <span class="header-user">{session.user_id}</span>
                <a href="/admin/logout" class="header-logout">{t('admin.logout')}</a>
            </div>
        </div>
        {get_admin_nav()}
        <div class="container">
            <div class="page-header">
                <h1 class="page-title">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                        <line x1="12" y1="18" x2="12" y2="12"/>
                        <line x1="9" y1="15" x2="15" y2="15"/>
                    </svg>
                    {t('admin.pages.new')}
                </h1>
                <div class="page-header-actions">
                    <a href="/admin/pages" class="btn btn-secondary">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="19" y1="12" x2="5" y2="12"/>
                            <polyline points="12 19 5 12 12 5"/>
                        </svg>
                        <span class="btn-text">{t('admin.pages.back_to_list')}</span>
                    </a>
                </div>
            </div>

            <div id="msg" class="alert" style="display:none;"></div>

            <form id="page-form" method="post" action="/admin/pages/new">
                <input type="hidden" name="csrf_token" value="{csrf_token}">

                <div class="two-col">
                    <div>
                        <div class="card card-static">
                            <div class="card-header primary">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                                    <polyline points="14 2 14 8 20 8"/>
                                    <line x1="16" y1="13" x2="8" y2="13"/>
                                    <line x1="16" y1="17" x2="8" y2="17"/>
                                </svg>
                                {t('admin.pages.page_info')}
                            </div>
                            <div class="card-body">
                                <div class="form-group">
                                    <label class="form-label">{t('common.title')}</label>
                                    <input name="title" required class="form-input" placeholder="{t('admin.pages.title_placeholder')}">
                                </div>
                                <div class="form-group">
                                    <label class="form-label">{t('common.description')}</label>
                                    <input name="description" class="form-input" placeholder="{t('admin.pages.description_placeholder')}">
                                </div>
                                <div class="form-group">
                                    <label class="form-label">{t('admin.pages.keywords')}</label>
                                    <input name="keywords" class="form-input" placeholder="{t('admin.pages.keywords_hint')}">
                                </div>
                            </div>
                        </div>

                        <div class="card card-static" style="margin-top:1rem;">
                            <div class="card-header purple">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M12 20h9"/>
                                    <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
                                </svg>
                                {t('common.content')}
                            </div>
                            <div class="card-body">
                                <textarea name="content"></textarea>
                            </div>
                        </div>
                    </div>

                    <div class="sidebar-card">
                        <div class="card card-static">
                            <div class="card-header success">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="3"/>
                                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                                </svg>
                                {t('admin.pages.settings')}
                            </div>
                            <div class="card-body">
                                <div class="form-group">
                                    <label class="form-label">{t('admin.pages.visibility')}</label>
                                    <select name="visibility" class="form-select">
                                        <option value="show">{t('admin.pages.show')}</option>
                                        <option value="hide">{t('admin.pages.hide')}</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label class="form-label">{t('admin.pages.template')}</label>
                                    <select name="template" class="form-select">
                                        <option value="default">{t('admin.pages.template_default')}</option>
                                        <option value="light">{t('admin.pages.template_light')}</option>
                                        <option value="dark">{t('admin.pages.template_dark')}</option>
                                        <option value="mixed">{t('admin.pages.template_mixed')}</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label class="form-label">{t('admin.pages.language')}</label>
                                    <select name="language" class="form-select">
                                        <option value="both">{t('admin.pages.lang_both')}</option>
                                        <option value="en">{t('admin.pages.lang_en')}</option>
                                        <option value="fa">{t('admin.pages.lang_fa')}</option>
                                    </select>
                                </div>
                                <div class="checkbox-row">
                                    <label class="checkbox-item">
                                        <input type="checkbox" name="hide_title">
                                        {t('admin.pages.hide_title')}
                                    </label>
                                    <label class="checkbox-item">
                                        <input type="checkbox" name="hide_description">
                                        {t('admin.pages.hide_description')}
                                    </label>
                                </div>
                            </div>
                            <div class="card-footer">
                                <button class="btn btn-primary" type="submit" style="width:100%;">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                                        <polyline points="17 21 17 13 7 13 7 21"/>
                                        <polyline points="7 3 7 8 15 8"/>
                                    </svg>
                                    {t('admin.pages.create_page')}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </form>
        </div>
        {get_admin_footer()}
        {wysiwyg_scripts}
        <script>
            const csrfToken = {csrf_token!r};
            document.getElementById('page-form').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const form = e.target;
                const textarea = form.querySelector('textarea[name="content"]');
                if (textarea.editorInstance) {{
                    textarea.value = textarea.editorInstance.getData();
                }}
                const data = Object.fromEntries(new FormData(form).entries());
                data.hide_title = form.querySelector('input[name="hide_title"]').checked;
                data.hide_description = form.querySelector('input[name="hide_description"]').checked;

                const res = await fetch('/admin/api/pages', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken,
                    }},
                    credentials: 'same-origin',
                    body: JSON.stringify(data),
                }});

                const msg = document.getElementById('msg');
                if (!res.ok) {{
                    const text = await res.text();
                    msg.className = 'alert alert-error';
                    msg.textContent = text || '{t("admin.pages.create_error")}';
                    msg.style.display = 'flex';
                    window.scrollTo({{ top: 0, behavior: 'smooth' }});
                    return;
                }}
                const page = await res.json();
                window.location.href = `/admin/pages/edit/${{encodeURIComponent(page.slug)}}?created=1`;
            }});
        </script>
    </body>
    </html>
    """
    response = HTMLResponse(html)
    if needs_cookie:
        set_csrf_cookie(request, response, csrf_token)
    return response


@router.get("/pages/edit/{slug}", response_class=HTMLResponse)
async def page_edit(
    slug: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
):
    """Render edit page form."""
    import html as _html

    from ..main import storage

    page = storage.get(f"pages.{slug}")
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    title = _html.escape(page.get("title", ""))
    description = _html.escape(page.get("description", ""))
    keywords = _html.escape(page.get("keywords", ""))
    content = _html.escape(page.get("content", ""))

    html_attrs = get_admin_html_attrs(request)
    lang_ctx = get_admin_lang_context(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""
    lang_switcher = get_admin_language_switcher_html(request)
    csrf_token, needs_cookie = get_csrf_token(request)
    wysiwyg_head = get_wysiwyg_head()
    wysiwyg_scripts = get_wysiwyg_scripts(csrf_token)
    created_msg = t('admin.pages.created_success') if request.query_params.get("created") == "1" else ""
    update_error_msg = t('admin.pages.update_error')
    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.pages.edit')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        {get_admin_common_css()}
        <style>
            .slug-display {{
                display: flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.5rem 0.75rem;
                background: #f1f5f9;
                border-radius: 6px;
                font-family: monospace;
                font-size: 0.875rem;
                color: #64748b;
                word-break: break-all;
            }}
            .slug-display svg {{
                flex-shrink: 0;
            }}
        </style>
        {rtl_styles}
        {wysiwyg_head}
    </head>
    <body>
        <div class="header">
            <a href="/admin/" class="header-logo">{t('cms.name_short')}</a>
            <div class="header-right">
                {lang_switcher}
                <a href="/" target="_blank">{t('admin.view_site')}</a>
                <span class="header-separator">|</span>
                <span class="header-user">{session.user_id}</span>
                <a href="/admin/logout" class="header-logout">{t('admin.logout')}</a>
            </div>
        </div>
        {get_admin_nav()}
        <div class="container">
            <div class="page-header">
                <h1 class="page-title">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                    {t('admin.pages.edit')}
                </h1>
                <div class="page-header-actions">
                    <a href="/{slug}" target="_blank" class="btn btn-secondary">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                            <polyline points="15 3 21 3 21 9"/>
                            <line x1="10" y1="14" x2="21" y2="3"/>
                        </svg>
                        <span class="btn-text">{t('admin.pages.preview')}</span>
                    </a>
                    <a href="/admin/pages" class="btn btn-secondary">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="19" y1="12" x2="5" y2="12"/>
                            <polyline points="12 19 5 12 12 5"/>
                        </svg>
                        <span class="btn-text">{t('admin.pages.back_to_list')}</span>
                    </a>
                </div>
            </div>

            <div id="msg" class="alert {'alert-success' if created_msg else ''}" style="{'display:block;' if created_msg else 'display:none;'}">{created_msg}</div>

            <form id="page-form" method="post" action="/admin/pages/edit/{slug}">
                <input type="hidden" name="csrf_token" value="{csrf_token}">

                <div class="two-col">
                    <div>
                        <div class="card card-static">
                            <div class="card-header primary">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                                    <polyline points="14 2 14 8 20 8"/>
                                    <line x1="16" y1="13" x2="8" y2="13"/>
                                    <line x1="16" y1="17" x2="8" y2="17"/>
                                </svg>
                                {t('admin.pages.page_info')}
                            </div>
                            <div class="card-body">
                                <div class="form-group">
                                    <label>{t('common.title')}</label>
                                    <input name="title" value="{title}" required class="form-input">
                                </div>
                                <div class="form-group">
                                    <label>Slug</label>
                                    <div class="slug-display">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                                            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
                                        </svg>
                                        /{slug}
                                    </div>
                                </div>
                                <div class="form-group">
                                    <label>{t('common.description')}</label>
                                    <input name="description" value="{description}" class="form-input">
                                </div>
                                <div class="form-group">
                                    <label>{t('admin.pages.keywords')}</label>
                                    <input name="keywords" value="{keywords}" class="form-input" placeholder="{t('admin.pages.keywords_hint')}">
                                </div>
                            </div>
                        </div>

                        <div class="card card-static" style="margin-top:1rem;">
                            <div class="card-header purple">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M12 20h9"/>
                                    <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
                                </svg>
                                {t('common.content')}
                            </div>
                            <div class="card-body">
                                <textarea name="content">{content}</textarea>
                            </div>
                        </div>
                    </div>

                    <div class="sidebar-card">
                        <div class="card card-static">
                            <div class="card-header success">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="3"/>
                                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                                </svg>
                                {t('admin.pages.settings')}
                            </div>
                            <div class="card-body">
                                <div class="form-group">
                                    <label>{t('admin.pages.visibility')}</label>
                                    <select name="visibility" class="form-input">
                                        <option value="show" {"selected" if page.get("visibility") == "show" else ""}>{t('admin.pages.show')}</option>
                                        <option value="hide" {"selected" if page.get("visibility") == "hide" else ""}>{t('admin.pages.hide')}</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label>{t('admin.pages.template')}</label>
                                    <select name="template" class="form-input">
                                        <option value="default" {"selected" if page.get("template", "default") == "default" else ""}>{t('admin.pages.template_default')}</option>
                                        <option value="light" {"selected" if page.get("template") == "light" else ""}>{t('admin.pages.template_light')}</option>
                                        <option value="dark" {"selected" if page.get("template") == "dark" else ""}>{t('admin.pages.template_dark')}</option>
                                        <option value="mixed" {"selected" if page.get("template") == "mixed" else ""}>{t('admin.pages.template_mixed')}</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label>{t('admin.pages.language')}</label>
                                    <select name="language" class="form-input">
                                        <option value="both" {"selected" if page.get("language", "both") == "both" else ""}>{t('admin.pages.lang_both')}</option>
                                        <option value="en" {"selected" if page.get("language") == "en" else ""}>{t('admin.pages.lang_en')}</option>
                                        <option value="fa" {"selected" if page.get("language") == "fa" else ""}>{t('admin.pages.lang_fa')}</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label>{t('admin.pages.associated_page')}</label>
                                    <select name="associated_page" class="form-input">
                                        <option value="">{t('admin.pages.no_association')}</option>
                                        {get_page_options_for_association(storage, slug, page.get("associated_page"))}
                                    </select>
                                </div>
                                <div class="checkbox-row">
                                    <label class="checkbox-item">
                                        <input type="checkbox" name="hide_title" {"checked" if page.get("hide_title") else ""}>
                                        {t('admin.pages.hide_title')}
                                    </label>
                                    <label class="checkbox-item">
                                        <input type="checkbox" name="hide_description" {"checked" if page.get("hide_description") else ""}>
                                        {t('admin.pages.hide_description')}
                                    </label>
                                </div>
                            </div>
                        </div>

                        <div class="card card-static" style="margin-top:1rem;">
                            <div class="card-header info">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                                    <line x1="3" y1="9" x2="21" y2="9"/>
                                    <line x1="9" y1="21" x2="9" y2="9"/>
                                </svg>
                                {t('admin.pages.blog_settings')}
                            </div>
                            <div class="card-body">
                                <div class="form-group">
                                    <label>{t('admin.pages.blog_columns')}</label>
                                    <select name="blog_columns" class="form-input">
                                        <option value="1" {"selected" if page.get("blog_columns", 2) == 1 else ""}>{t('admin.pages.blog_columns_1')}</option>
                                        <option value="2" {"selected" if page.get("blog_columns", 2) == 2 else ""}>{t('admin.pages.blog_columns_2')}</option>
                                        <option value="3" {"selected" if page.get("blog_columns", 2) == 3 else ""}>{t('admin.pages.blog_columns_3')}</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label>{t('admin.pages.posts_per_page')}</label>
                                    <input type="number" name="posts_per_page" value="{page.get("posts_per_page", 10)}" min="1" max="50" class="form-input">
                                </div>
                            </div>
                            <div class="card-footer">
                                <button class="btn btn-primary" type="submit" style="width:100%;">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-inline-end:0.5rem;">
                                        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                                        <polyline points="17 21 17 13 7 13 7 21"/>
                                        <polyline points="7 3 7 8 15 8"/>
                                    </svg>
                                    {t('admin.pages.save_changes')}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </form>
        </div>
        <script>
            const csrfToken = {csrf_token!r};
            const updateErrorMsg = {update_error_msg!r};

            function showMsg(type, text) {{
                const msg = document.getElementById('msg');
                msg.className = 'alert alert-' + type;
                msg.textContent = text;
                msg.style.display = 'block';
                setTimeout(() => {{ msg.style.display = 'none'; }}, 5000);
            }}

            document.getElementById('page-form').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const form = e.target;
                // Sync editor content if available
                const textarea = form.querySelector('textarea[name="content"]');
                if (textarea.editorInstance) {{
                    textarea.value = textarea.editorInstance.getData();
                }}
                const data = Object.fromEntries(new FormData(form).entries());
                const res = await fetch('/admin/api/pages/{slug}', {{
                    method: 'PUT',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken,
                    }},
                    credentials: 'same-origin',
                    body: JSON.stringify(data),
                }});
                if (!res.ok) {{
                    const text = await res.text();
                    showMsg('error', text || updateErrorMsg);
                    return;
                }}
                showMsg('success', '{t("messages.saved")}');
            }});
        </script>
        {wysiwyg_scripts}
        {get_admin_footer()}
    </body>
    </html>
    """
    response = HTMLResponse(html)
    if needs_cookie:
        set_csrf_cookie(request, response, csrf_token)
    return response


@router.post("/pages/new")
async def page_new_submit(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
):
    """Handle new page form submission."""
    from ..main import storage, sanitizer, audit_logger

    form = await request.form()
    csrf_token = form.get("csrf_token", "")
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not csrf_cookie or not secrets.compare_digest(csrf_token, csrf_cookie):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    title = str(form.get("title", "Untitled")).strip()
    slug = sanitizer.slugify(title or "untitled")
    if storage.get(f"pages.{slug}"):
        raise HTTPException(status_code=409, detail="Page already exists")

    template = normalize_template(form.get("template"))
    page = {
        "title": title or "Untitled",
        "slug": slug,
        "content": str(form.get("content", "")),
        "content_format": "html",  # WYSIWYG editor produces HTML
        "description": str(form.get("description", "")),
        "keywords": str(form.get("keywords", "")),
        "visibility": str(form.get("visibility", "show")),
        "template": template,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "modified_at": datetime.now(timezone.utc).isoformat(),
        "modified_by": session.user_id,
    }

    storage.set(f"pages.{slug}", page)
    audit_logger.log(
        "page_create",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        details={"slug": slug},
    )

    return RedirectResponse(url=f"/admin/pages/edit/{slug}?created=1", status_code=303)


@router.post("/pages/edit/{slug}")
async def page_edit_submit(
    slug: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
):
    """Handle edit page form submission."""
    from ..main import storage, audit_logger

    page = storage.get(f"pages.{slug}")
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    form = await request.form()
    csrf_token = form.get("csrf_token", "")
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not csrf_cookie or not secrets.compare_digest(csrf_token, csrf_cookie):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    page["title"] = str(form.get("title", page.get("title", "")))
    page["content"] = str(form.get("content", page.get("content", "")))
    page["content_format"] = "html"
    page["description"] = str(form.get("description", page.get("description", "")))
    page["keywords"] = str(form.get("keywords", page.get("keywords", "")))
    page["visibility"] = str(form.get("visibility", page.get("visibility", "show")))
    page["template"] = normalize_template(form.get("template", page.get("template", "default")))
    page["modified_at"] = datetime.now(timezone.utc).isoformat()
    page["modified_by"] = session.user_id

    storage.set(f"pages.{slug}", page)
    audit_logger.log(
        "page_update",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        details={"slug": slug},
    )

    return RedirectResponse(url=f"/admin/pages/edit/{slug}", status_code=303)


@router.get("/uploads", response_class=HTMLResponse)
async def uploads_page(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
):
    """Render upload page."""
    import html as _html

    from ..main import storage

    uploads = storage.get("uploads", {})

    # Build file rows with improved design
    def get_file_icon(filename: str) -> str:
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']:
            return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>'
        elif ext in ['pdf']:
            return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>'
        elif ext in ['mp4', 'avi', 'mov', 'mkv']:
            return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>'
        elif ext in ['mp3', 'wav', 'ogg']:
            return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" /></svg>'
        else:
            return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>'

    rows_list = []
    for u in sorted(uploads.values(), key=lambda x: x.get('original_name', '')):
        uuid = _html.escape(u.get('uuid', ''))
        name = _html.escape(u.get('original_name', ''))
        file_icon = get_file_icon(name)
        ext = name.lower().split('.')[-1] if '.' in name else 'file'
        is_image = ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']
        preview = f'<img src="/uploads/{uuid}" alt="{name}" style="max-width:100%;max-height:100%;object-fit:contain;border-radius:6px;">' if is_image else file_icon
        rows_list.append(f'''
            <tr data-uuid="{uuid}">
                <td>
                    <div style="display:flex;align-items:center;gap:1rem;">
                        <div style="width:60px;height:60px;border-radius:10px;background:#f1f5f9;display:flex;align-items:center;justify-content:center;flex-shrink:0;overflow:hidden;color:#64748b;">
                            {preview}
                        </div>
                        <div style="flex:1;min-width:0;">
                            <input class="form-input name-input" value="{name}" style="font-weight:500;">
                            <div style="font-size:0.8rem;color:#64748b;margin-top:0.25rem;">{uuid[:8]}...{uuid[-4:]}</div>
                        </div>
                    </div>
                </td>
                <td class="actions-cell">
                    <div class="actions">
                        <a href="/uploads/{uuid}" target="_blank" class="btn btn-sm btn-secondary" title="{t('common.view')}">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                        </a>
                        <button class="btn btn-sm btn-success save-btn" type="button" title="{t('common.save')}">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                            </svg>
                        </button>
                        <button class="btn btn-sm btn-danger delete-btn" type="button" title="{t('common.delete')}">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        ''')
    rows = "\n".join(rows_list)

    empty_state = ""
    if not uploads:
        empty_state = f'''
            <div class="empty-state">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <h3>{t('admin.uploads.no_files')}</h3>
                <p>{t('admin.uploads.upload_first')}</p>
            </div>
        '''

    html_attrs = get_admin_html_attrs(request)
    lang_ctx = get_admin_lang_context(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""
    lang_switcher = get_admin_language_switcher_html(request)
    csrf_token, needs_cookie = get_csrf_token(request)
    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.uploads.title')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="/admin/static/css/admin-common.css">
        <style>
            .upload-zone {{
                position: relative;
                display: block;
                border: 2px dashed #cbd5e1;
                border-radius: 16px;
                padding: 2rem;
                text-align: center;
                background: #f8fafc;
                transition: all 0.2s;
                cursor: pointer;
            }}
            .upload-zone:hover, .upload-zone.dragover {{
                border-color: #6366f1;
                background: rgba(99, 102, 241, 0.05);
            }}
            .upload-zone input[type="file"] {{
                position: absolute;
                width: 1px;
                height: 1px;
                padding: 0;
                margin: -1px;
                overflow: hidden;
                clip: rect(0, 0, 0, 0);
                white-space: nowrap;
                border: 0;
            }}
            .upload-icon {{
                width: 64px;
                height: 64px;
                margin: 0 auto 1rem;
                background: linear-gradient(135deg, #10b981, #059669);
                border-radius: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
            }}
            .upload-text {{
                color: #64748b;
                margin-bottom: 0.5rem;
            }}
            .upload-hint {{
                font-size: 0.85rem;
                color: #94a3b8;
            }}
            .actions-cell {{
                width: 150px;
            }}
            .actions-cell .actions {{
                justify-content: flex-end;
            }}
            [dir="rtl"] .actions-cell .actions {{
                justify-content: flex-start;
            }}
            .name-input {{
                padding: 0.5rem 0.75rem;
                font-size: 0.95rem;
            }}
        </style>
        {rtl_styles}
    </head>
    <body>
        <div class="header">
            <a href="/admin/" style="font-size:1.25rem;font-weight:700;color:white;text-decoration:none;">{t('cms.name_short')}</a>
            <div class="header-right">
                {lang_switcher}
                <a href="/" target="_blank" style="color:#94a3b8;text-decoration:none;">{t('admin.view_site')}</a>
                <span style="color:#64748b;">|</span>
                <span style="color:#e2e8f0;">{session.user_id}</span>
                <a href="/admin/logout" style="color:#f87171;text-decoration:none;">{t('admin.logout')}</a>
            </div>
        </div>
        {get_admin_nav()}
        <div class="container">
            <!-- Page Header -->
            <h1 class="page-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                {t('admin.uploads.title')}
            </h1>

            <!-- Message -->
            <div id="msg" class="alert" style="display:none;"></div>

            <!-- Upload Zone -->
            <div class="card card-static" style="margin-bottom: 2rem;">
                <div class="card-header success">
                    <div class="card-icon success">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                        </svg>
                    </div>
                    <h3 class="card-title">{t('admin.uploads.upload')}</h3>
                </div>
                <div class="card-body">
                    <form id="upload-form">
                        <label class="upload-zone" id="dropzone">
                            <input type="file" name="file" required id="file-input">
                            <div class="upload-icon">
                                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                                </svg>
                            </div>
                            <div class="upload-text">{t('admin.uploads.drag_drop')}</div>
                            <div class="upload-hint">{t('admin.uploads.or_click')}</div>
                        </label>
                    </form>
                </div>
            </div>

            <!-- Files Table -->
            <div class="card card-static">
                <div class="card-header primary">
                    <div class="card-icon primary">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                        </svg>
                    </div>
                    <h3 class="card-title">{t('admin.uploads.all_files')} ({len(uploads)})</h3>
                </div>
                {"<div class='card-body'>" + empty_state + "</div>" if not uploads else f'''
                <div class="table-container">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>{t('admin.uploads.file_info')}</th>
                                <th style="text-align:right;">{t('common.actions')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows}
                        </tbody>
                    </table>
                </div>
                '''}
            </div>
        </div>
        <script>
            const csrfToken = {csrf_token!r};
            const showMsg = (text, type = 'error') => {{
                const msg = document.getElementById('msg');
                msg.textContent = text;
                msg.className = 'alert alert-' + type;
                msg.style.display = 'flex';
                setTimeout(() => {{ msg.style.display = 'none'; }}, 5000);
            }};

            // Drag & Drop
            const dropzone = document.getElementById('dropzone');
            const fileInput = document.getElementById('file-input');

            ['dragenter', 'dragover'].forEach(evt => {{
                dropzone.addEventListener(evt, (e) => {{
                    e.preventDefault();
                    dropzone.classList.add('dragover');
                }});
            }});
            ['dragleave', 'drop'].forEach(evt => {{
                dropzone.addEventListener(evt, (e) => {{
                    e.preventDefault();
                    dropzone.classList.remove('dragover');
                }});
            }});
            dropzone.addEventListener('drop', (e) => {{
                const files = e.dataTransfer.files;
                if (files.length) {{
                    fileInput.files = files;
                    uploadFile(files[0]);
                }}
            }});

            fileInput.addEventListener('change', (e) => {{
                if (e.target.files.length) {{
                    uploadFile(e.target.files[0]);
                }}
            }});

            async function uploadFile(file) {{
                const data = new FormData();
                data.append('file', file);
                const res = await fetch('/admin/api/uploads', {{
                    method: 'POST',
                    headers: {{ 'X-CSRF-Token': csrfToken }},
                    credentials: 'same-origin',
                    body: data,
                }});
                if (!res.ok) {{
                    const text = await res.text();
                    showMsg(text || '{t("admin.uploads.upload_failed")}');
                    return;
                }}
                showMsg('{t("admin.uploads.upload_success")}', 'success');
                setTimeout(() => window.location.reload(), 1000);
            }}

            document.querySelectorAll('.save-btn').forEach((btn) => {{
                btn.addEventListener('click', async (e) => {{
                    const row = e.target.closest('tr');
                    const uuid = row.dataset.uuid;
                    const name = row.querySelector('.name-input').value;
                    const res = await fetch(`/admin/api/uploads/${{encodeURIComponent(uuid)}}`, {{
                        method: 'PUT',
                        headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken }},
                        credentials: 'same-origin',
                        body: JSON.stringify({{ original_name: name }}),
                    }});
                    if (!res.ok) {{
                        const text = await res.text();
                        showMsg(text || '{t("admin.uploads.update_failed")}');
                        return;
                    }}
                    showMsg('{t("admin.uploads.update_success")}', 'success');
                }});
            }});

            document.querySelectorAll('.delete-btn').forEach((btn) => {{
                btn.addEventListener('click', async (e) => {{
                    if (!confirm('{t("admin.uploads.confirm_delete")}')) return;
                    const row = e.target.closest('tr');
                    const uuid = row.dataset.uuid;
                    const res = await fetch(`/admin/api/uploads/${{encodeURIComponent(uuid)}}`, {{
                        method: 'DELETE',
                        headers: {{ 'X-CSRF-Token': csrfToken }},
                        credentials: 'same-origin',
                    }});
                    if (!res.ok) {{
                        const text = await res.text();
                        showMsg(text || '{t("admin.uploads.delete_failed")}');
                        return;
                    }}
                    row.remove();
                    showMsg('{t("admin.uploads.delete_success")}', 'success');
                }});
            }});
        </script>
        {get_admin_footer()}
    </body>
    </html>
    """
    response = HTMLResponse(html)
    if needs_cookie:
        set_csrf_cookie(request, response, csrf_token)
    return response


@router.get("/blocks", response_class=HTMLResponse)
async def blocks_page(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
):
    """Render blocks editor with dual-language support."""
    import html as _html

    from ..main import storage

    blocks = storage.get("blocks", {})

    # Ensure all block types exist
    block_types = ['header', 'footer', 'sidebar']
    for block_type in block_types:
        if block_type not in blocks:
            blocks[block_type] = {}

    # Build block cards
    block_cards = ""
    block_icons = {
        'header': '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5z" />',
        'footer': '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 17a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1v-2z" />',
        'sidebar': '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v14a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm12 0v14" />'
    }
    for name in block_types:
        icon = block_icons.get(name, '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />')
        block_cards += f'''
            <button type="button" class="block-card" data-block="{_html.escape(name)}">
                <div class="block-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor">{icon}</svg>
                </div>
                <span class="block-name">{t(f'admin.blocks.{name}')}</span>
            </button>
        '''

    html_attrs = get_admin_html_attrs(request)
    lang_ctx = get_admin_lang_context(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""
    lang_switcher = get_admin_language_switcher_html(request)
    csrf_token, needs_cookie = get_csrf_token(request)
    wysiwyg_head = get_wysiwyg_head()
    wysiwyg_scripts = get_wysiwyg_scripts(csrf_token)
    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.blocks.title')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="/admin/static/css/admin-common.css">
        <style>
            .block-selector {{
                display: flex;
                gap: 1rem;
                flex-wrap: wrap;
                margin-bottom: 1.5rem;
            }}
            .block-card {{
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 0.75rem;
                padding: 1.25rem 1.5rem;
                background: #f8fafc;
                border: 2px solid #e2e8f0;
                border-radius: 12px;
                cursor: pointer;
                transition: all 0.2s;
                min-width: 120px;
            }}
            .block-card:hover {{
                border-color: #a855f7;
                background: rgba(168, 85, 247, 0.05);
            }}
            .block-card.active {{
                border-color: #a855f7;
                background: rgba(168, 85, 247, 0.1);
                box-shadow: 0 4px 15px rgba(168, 85, 247, 0.2);
            }}
            .block-icon {{
                width: 48px;
                height: 48px;
                background: linear-gradient(135deg, #a855f7, #9333ea);
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
            }}
            .block-name {{
                font-weight: 600;
                color: #475569;
                font-size: 0.9rem;
            }}
            .block-card.active .block-name {{
                color: #7c3aed;
            }}
            .block-card.disabled {{
                opacity: 0.5;
            }}
            .block-card.disabled .block-icon {{
                background: linear-gradient(135deg, #94a3b8, #64748b);
            }}
            /* Block enabled toggle */
            .block-toggle {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
                padding: 1rem;
                background: #f8fafc;
                border-radius: 8px;
                margin-bottom: 1.5rem;
            }}
            .block-toggle-label {{
                font-weight: 600;
                color: #475569;
            }}
            .block-toggle-hint {{
                font-size: 0.85rem;
                color: #64748b;
                margin-top: 0.25rem;
            }}
            .toggle-switch {{
                position: relative;
                width: 50px;
                height: 26px;
                flex-shrink: 0;
            }}
            .toggle-switch input {{
                opacity: 0;
                width: 0;
                height: 0;
            }}
            .toggle-slider {{
                position: absolute;
                cursor: pointer;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: #cbd5e1;
                transition: 0.3s;
                border-radius: 26px;
            }}
            .toggle-slider:before {{
                position: absolute;
                content: "";
                height: 20px;
                width: 20px;
                left: 3px;
                bottom: 3px;
                background-color: white;
                transition: 0.3s;
                border-radius: 50%;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }}
            .toggle-switch input:checked + .toggle-slider {{
                background: linear-gradient(135deg, #a855f7, #7c3aed);
            }}
            .toggle-switch input:checked + .toggle-slider:before {{
                transform: translateX(24px);
            }}
            .editor-container {{
                min-height: 300px;
            }}
            .ck-editor__editable {{
                min-height: 250px;
            }}
            /* Language tabs */
            .lang-tabs {{
                display: flex;
                gap: 0;
                margin-bottom: 1.5rem;
                border-bottom: 2px solid #e2e8f0;
            }}
            .lang-tab {{
                padding: 0.75rem 1.5rem;
                border: none;
                background: transparent;
                cursor: pointer;
                font-weight: 600;
                color: #64748b;
                border-bottom: 2px solid transparent;
                margin-bottom: -2px;
                transition: all 0.2s;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            .lang-tab:hover {{
                color: #475569;
                background: #f8fafc;
            }}
            .lang-tab.active {{
                color: #2563eb;
                border-bottom-color: #2563eb;
            }}
            .lang-tab .flag {{
                width: 20px;
                height: 14px;
            }}
            .lang-panel {{
                display: none;
            }}
            .lang-panel.active {{
                display: block;
            }}
            /* Two column layout for editors */
            .editors-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 2rem;
            }}
            .editor-column {{
                min-width: 0;
            }}
            .editor-column h4 {{
                display: flex;
                align-items: center;
                gap: 0.5rem;
                margin-bottom: 1rem;
                padding-bottom: 0.5rem;
                border-bottom: 2px solid #e2e8f0;
                font-size: 1rem;
                color: #475569;
            }}
            .editor-column h4 img {{
                width: 24px;
                height: 18px;
            }}
            .editor-column.fa h4 {{
                direction: rtl;
            }}
            @media (max-width: 1200px) {{
                .editors-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
        {rtl_styles}
        {wysiwyg_head}
    </head>
    <body>
        <div class="header">
            <a href="/admin/" style="font-size:1.25rem;font-weight:700;color:white;text-decoration:none;">{t('cms.name_short')}</a>
            <div class="header-right">
                {lang_switcher}
                <a href="/" target="_blank" style="color:#94a3b8;text-decoration:none;">{t('admin.view_site')}</a>
                <span style="color:#64748b;">|</span>
                <span style="color:#e2e8f0;">{session.user_id}</span>
                <a href="/admin/logout" style="color:#f87171;text-decoration:none;">{t('admin.logout')}</a>
            </div>
        </div>
        {get_admin_nav()}
        <div class="container">
            <!-- Page Header -->
            <h1 class="page-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
                </svg>
                {t('admin.blocks.title')}
            </h1>

            <!-- Message -->
            <div id="msg" class="alert" style="display:none;"></div>

            <!-- Block Selector Card -->
            <div class="card card-static" style="margin-bottom: 2rem;">
                <div class="card-header purple">
                    <div class="card-icon purple">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                        </svg>
                    </div>
                    <h3 class="card-title">{t('admin.blocks.select')}</h3>
                </div>
                <div class="card-body">
                    <div class="block-selector">
                        {block_cards}
                    </div>
                </div>
            </div>

            <!-- Block Editor Card with Language Tabs -->
            <div class="card card-static">
                <div class="card-header primary">
                    <div class="card-icon primary">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                    </div>
                    <h3 class="card-title">{t('admin.blocks.edit_content')}</h3>
                </div>
                <div class="card-body">
                    <form id="block-form">
                        <input type="hidden" name="name" id="block-name" value="">

                        <!-- Block Enable/Disable Toggle -->
                        <div class="block-toggle">
                            <label class="toggle-switch">
                                <input type="checkbox" id="block-enabled" checked>
                                <span class="toggle-slider"></span>
                            </label>
                            <div>
                                <div class="block-toggle-label">{t('admin.blocks.enable_block')}</div>
                                <div class="block-toggle-hint">{t('admin.blocks.enable_hint')}</div>
                            </div>
                        </div>

                        <!-- Two column editors for both languages -->
                        <div class="editors-grid">
                            <div class="editor-column fa">
                                <h4>
                                    <svg viewBox="0 0 22 15" width="24" height="18" style="border:1px solid #e2e8f0;border-radius:2px;">
                                        <rect width="22" height="5" fill="#239f40"/>
                                        <rect y="5" width="22" height="5" fill="#fff"/>
                                        <rect y="10" width="22" height="5" fill="#da0000"/>
                                    </svg>
                                    {t('admin.blocks.persian_content')}
                                </h4>
                                <div class="editor-container" dir="rtl">
                                    <textarea name="content_fa" id="block-content-fa"></textarea>
                                </div>
                            </div>
                            <div class="editor-column en">
                                <h4>
                                    <svg viewBox="0 0 60 30" width="24" height="18" style="border:1px solid #e2e8f0;border-radius:2px;"><clipPath id="uk-s2"><path d="M0,0 v30 h60 v-30 z"/></clipPath><clipPath id="uk-t2"><path d="M30,15 h30 v15 z v15 h-30 z h-30 v-15 z v-15 h30 z"/></clipPath><g clip-path="url(#uk-s2)"><path d="M0,0 v30 h60 v-30 z" fill="#012169"/><path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/><path d="M0,0 L60,30 M60,0 L0,30" clip-path="url(#uk-t2)" stroke="#C8102E" stroke-width="4"/><path d="M30,0 v30 M0,15 h60" stroke="#fff" stroke-width="10"/><path d="M30,0 v30 M0,15 h60" stroke="#C8102E" stroke-width="6"/></g></svg>
                                    {t('admin.blocks.english_content')}
                                </h4>
                                <div class="editor-container" dir="ltr">
                                    <textarea name="content_en" id="block-content-en"></textarea>
                                </div>
                            </div>
                        </div>

                        <div style="margin-top: 1.5rem;">
                            <button class="btn btn-primary" type="submit">
                                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                                </svg>
                                {t('common.save')}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        <script>
            const csrfToken = {csrf_token!r};
            let editorFa = null;
            let editorEn = null;

            const showMsg = (text, type = 'error') => {{
                const msg = document.getElementById('msg');
                msg.textContent = text;
                msg.className = 'alert alert-' + type;
                msg.style.display = 'flex';
                setTimeout(() => {{ msg.style.display = 'none'; }}, 5000);
            }};

            function updateBlockCardState(name, enabled) {{
                const card = document.querySelector(`.block-card[data-block="${{name}}"]`);
                if (card) {{
                    if (enabled) {{
                        card.classList.remove('disabled');
                    }} else {{
                        card.classList.add('disabled');
                    }}
                }}
            }}

            // Update all block cards on page load
            async function updateAllBlockCards() {{
                const res = await fetch('/admin/api/blocks', {{ credentials: 'same-origin' }});
                const data = await res.json();
                const blocks = data.blocks || {{}};
                for (const [name, block] of Object.entries(blocks)) {{
                    updateBlockCardState(name, block.enabled !== false);
                }}
            }}

            async function loadBlock(name) {{
                const res = await fetch('/admin/api/blocks', {{ credentials: 'same-origin' }});
                const data = await res.json();
                const block = (data.blocks || {{}})[name] || {{}};

                // Support both old and new format
                let contentFa = '';
                let contentEn = '';
                let enabled = block.enabled !== false; // Default to true

                if (block.fa && typeof block.fa === 'object') {{
                    contentFa = block.fa.content || '';
                }} else if (block.content) {{
                    // Old format - put in both
                    contentFa = block.content || '';
                    contentEn = block.content || '';
                }}

                // Update enabled toggle
                document.getElementById('block-enabled').checked = enabled;
                updateBlockCardState(name, enabled);

                if (block.en && typeof block.en === 'object') {{
                    contentEn = block.en.content || '';
                }}

                document.getElementById('block-name').value = name;

                // Update FA editor
                const textareaFa = document.getElementById('block-content-fa');
                if (textareaFa.editorInstance) {{
                    textareaFa.editorInstance.setData(contentFa);
                }} else {{
                    textareaFa.value = contentFa;
                }}

                // Update EN editor
                const textareaEn = document.getElementById('block-content-en');
                if (textareaEn.editorInstance) {{
                    textareaEn.editorInstance.setData(contentEn);
                }} else {{
                    textareaEn.value = contentEn;
                }}
            }}

            // Block card selection
            document.querySelectorAll('.block-card').forEach(card => {{
                card.addEventListener('click', () => {{
                    document.querySelectorAll('.block-card').forEach(c => c.classList.remove('active'));
                    card.classList.add('active');
                    loadBlock(card.dataset.block);
                }});
            }});

            // Select first block by default
            const firstCard = document.querySelector('.block-card');
            if (firstCard) {{
                firstCard.classList.add('active');
                setTimeout(() => loadBlock(firstCard.dataset.block), 500);
            }}

            document.getElementById('block-form').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const name = document.getElementById('block-name').value;
                if (!name) {{
                    showMsg('{t("admin.blocks.select_first")}');
                    return;
                }}

                const textareaFa = document.getElementById('block-content-fa');
                const textareaEn = document.getElementById('block-content-en');
                const enabled = document.getElementById('block-enabled').checked;

                // Get content from editors if available
                let contentFa = textareaFa.editorInstance ? textareaFa.editorInstance.getData() : textareaFa.value;
                let contentEn = textareaEn.editorInstance ? textareaEn.editorInstance.getData() : textareaEn.value;

                const res = await fetch(`/admin/api/blocks/${{encodeURIComponent(name)}}`, {{
                    method: 'PUT',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken,
                    }},
                    credentials: 'same-origin',
                    body: JSON.stringify({{
                        fa: {{ content: contentFa, content_format: 'html' }},
                        en: {{ content: contentEn, content_format: 'html' }},
                        enabled: enabled
                    }}),
                }});
                if (!res.ok) {{
                    const text = await res.text();
                    showMsg(text || '{t("admin.blocks.save_failed")}');
                    return;
                }}
                // Update card state
                updateBlockCardState(name, enabled);
                showMsg('{t("admin.blocks.saved")}', 'success');
            }});

            // Update all cards on load
            updateAllBlockCards();
        </script>
        {wysiwyg_scripts}
        {get_admin_footer()}
    </body>
    </html>
    """
    response = HTMLResponse(html)
    if needs_cookie:
        set_csrf_cookie(request, response, csrf_token)
    return response


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
):
    """Render settings page."""
    import html as _html

    from ..main import storage, theme_manager

    # Get language context
    lang_ctx = get_admin_lang_context(request)
    html_attrs = get_admin_html_attrs(request)
    lang_switcher = get_admin_language_switcher_html(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""

    config = storage.get("config", {})
    themes = theme_manager.list_themes() if theme_manager else []
    theme_options = "\n".join(
        f"<option value=\"{_html.escape(t.name)}\" "
        f"{'selected' if t.name == config.get('theme','default') else ''}>"
        f"{_html.escape(t.name)}</option>"
        for t in themes
    )

    # Build language options
    available_langs = get_available_languages()
    current_site_lang = config.get('site_lang', 'en')
    current_admin_lang = config.get('admin_lang', 'en')
    site_lang_options = "\n".join(
        f"<option value=\"{lang['code']}\" "
        f"{'selected' if lang['code'] == current_site_lang else ''}>"
        f"{lang['native_name']} ({lang['name']})</option>"
        for lang in available_langs
    )
    admin_lang_options = "\n".join(
        f"<option value=\"{lang['code']}\" "
        f"{'selected' if lang['code'] == current_admin_lang else ''}>"
        f"{lang['native_name']} ({lang['name']})</option>"
        for lang in available_langs
    )

    csrf_token, needs_cookie = get_csrf_token(request)
    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.settings.title')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                font-family: system-ui, -apple-system, sans-serif;
                margin: 0;
                background: linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 100%);
                min-height: 100vh;
            }}
            .header {{
                background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
                color: white;
                padding: 1rem 2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header a {{ color: #94a3b8; text-decoration: none; }}
            .header-right {{ display: flex; align-items: center; gap: 1rem; }}

            .container {{
                max-width: 1000px;
                margin: 0 auto;
                padding: 2rem 1.5rem;
            }}

            .page-title {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
                margin: 0 0 2rem 0;
                font-size: 1.75rem;
                font-weight: 700;
                color: #1e293b;
            }}
            .page-title svg {{
                color: #6366f1;
            }}

            /* Message styles */
            #msg {{
                padding: 1rem 1.25rem;
                border-radius: 12px;
                margin-bottom: 1.5rem;
                display: none;
                font-weight: 500;
            }}
            #msg.error {{
                display: block;
                background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
                color: #b91c1c;
                border: 1px solid #fca5a5;
            }}
            #msg.success {{
                display: block;
                background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
                color: #16a34a;
                border: 1px solid #86efac;
            }}

            /* Settings Cards */
            .settings-grid {{
                display: grid;
                gap: 1.5rem;
            }}

            .settings-card {{
                background: white;
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.06);
                overflow: hidden;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .settings-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 30px rgba(0,0,0,0.1);
            }}

            .card-header {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
                padding: 1.25rem 1.5rem;
                border-bottom: 1px solid #f1f5f9;
            }}
            .card-header.primary {{ background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-bottom-color: #bfdbfe; }}
            .card-header.search {{ background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border-bottom-color: #bbf7d0; }}
            .card-header.access {{ background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%); border-bottom-color: #e9d5ff; }}
            .card-header.warning {{ background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%); border-bottom-color: #fde68a; }}
            .card-header.update {{ background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%); border-bottom-color: #c7d2fe; }}

            .card-icon {{
                width: 40px;
                height: 40px;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
            }}
            .card-icon.primary {{ background: #3b82f6; color: white; }}
            .card-icon.search {{ background: #22c55e; color: white; }}
            .card-icon.access {{ background: #a855f7; color: white; }}
            .card-icon.warning {{ background: #f59e0b; color: white; }}
            .card-icon.update {{ background: #6366f1; color: white; }}

            .card-title {{
                font-size: 1.1rem;
                font-weight: 600;
                color: #1e293b;
                margin: 0;
            }}

            .card-body {{
                padding: 1.5rem;
            }}

            /* Form Elements */
            .form-row {{
                margin-bottom: 1.25rem;
            }}
            .form-row:last-child {{
                margin-bottom: 0;
            }}

            .form-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1.25rem;
            }}

            .form-label {{
                display: block;
                font-size: 0.875rem;
                font-weight: 600;
                color: #374151;
                margin-bottom: 0.5rem;
            }}

            .form-input,
            .form-select {{
                width: 100%;
                padding: 0.75rem 1rem;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                font-size: 0.95rem;
                transition: all 0.2s;
                background: #f8fafc;
            }}
            .form-input:focus,
            .form-select:focus {{
                outline: none;
                border-color: #6366f1;
                background: white;
                box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
            }}

            .form-input-small {{
                width: 100px;
                text-align: center;
            }}

            /* Checkbox styles */
            .checkbox-row {{
                display: flex;
                align-items: flex-start;
                gap: 0.75rem;
                padding: 0.75rem 1rem;
                background: #f8fafc;
                border-radius: 10px;
                margin-bottom: 0.75rem;
                cursor: pointer;
                transition: background 0.2s;
            }}
            .checkbox-row:hover {{
                background: #f1f5f9;
            }}
            .checkbox-row:last-child {{
                margin-bottom: 0;
            }}

            .checkbox-input {{
                width: 20px;
                height: 20px;
                margin: 0;
                cursor: pointer;
                accent-color: #6366f1;
                flex-shrink: 0;
            }}

            .checkbox-content {{
                flex: 1;
            }}
            .checkbox-label {{
                font-weight: 500;
                color: #1e293b;
                margin: 0;
            }}
            .checkbox-hint {{
                font-size: 0.8rem;
                color: #64748b;
                margin: 0.25rem 0 0 0;
            }}

            /* Link card */
            .link-card {{
                display: flex;
                align-items: center;
                gap: 1rem;
                padding: 1rem 1.25rem;
                background: #f8fafc;
                border-radius: 10px;
                text-decoration: none;
                color: inherit;
                transition: all 0.2s;
                border: 2px solid transparent;
            }}
            .link-card:hover {{
                background: #eff6ff;
                border-color: #bfdbfe;
            }}
            .link-card-icon {{
                width: 44px;
                height: 44px;
                background: #3b82f6;
                color: white;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
            }}
            .link-card-content {{
                flex: 1;
            }}
            .link-card-title {{
                font-weight: 600;
                color: #1e293b;
                margin: 0;
            }}
            .link-card-desc {{
                font-size: 0.85rem;
                color: #64748b;
                margin: 0.25rem 0 0 0;
            }}
            .link-card-arrow {{
                color: #94a3b8;
                transition: transform 0.2s;
            }}
            .link-card:hover .link-card-arrow {{
                transform: translateX(4px);
                color: #3b82f6;
            }}

            /* Inline number inputs */
            .inline-form {{
                display: flex;
                align-items: center;
                gap: 1rem;
                flex-wrap: wrap;
            }}
            .inline-form-group {{
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}
            .inline-form-group label {{
                font-size: 0.875rem;
                color: #64748b;
                white-space: nowrap;
            }}
            .inline-form-group input {{
                width: 80px;
                padding: 0.5rem 0.75rem;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                text-align: center;
                font-size: 0.95rem;
            }}
            .inline-form-group input:focus {{
                outline: none;
                border-color: #6366f1;
            }}

            /* Buttons */
            .btn {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
                padding: 0.75rem 1.5rem;
                font-size: 0.95rem;
                font-weight: 600;
                border: none;
                border-radius: 10px;
                cursor: pointer;
                transition: all 0.2s;
            }}
            .btn-primary {{
                background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
                color: white;
                box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
            }}
            .btn-primary:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
            }}
            .btn-success {{
                background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
                color: white;
                box-shadow: 0 4px 15px rgba(34, 197, 94, 0.3);
            }}
            .btn-success:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(34, 197, 94, 0.4);
            }}
            .btn-check {{
                background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
                color: white;
                box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
            }}
            .btn-check:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4);
            }}
            .btn:disabled {{
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }}

            .btn-save {{
                width: 100%;
                padding: 1rem;
                font-size: 1rem;
                margin-top: 1.5rem;
            }}

            /* Update status */
            #update-status {{
                padding: 1rem;
                border-radius: 10px;
                margin-bottom: 1rem;
                display: none;
            }}
            #update-info {{
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 10px;
                padding: 1rem;
                margin-bottom: 1rem;
                display: none;
            }}
            #update-info p {{
                margin: 0 0 0.5rem 0;
                color: #1e40af;
            }}

            /* Version badge */
            .version-badge {{
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.5rem 1rem;
                background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
                border: 1px solid #86efac;
                border-radius: 20px;
                font-size: 0.9rem;
                font-weight: 600;
                color: #16a34a;
            }}

            /* Hidden row animation */
            .hidden-row {{
                display: none;
            }}

            /* RTL Adjustments */
            [dir="rtl"] .link-card-arrow {{
                transform: rotate(180deg);
            }}
            [dir="rtl"] .link-card:hover .link-card-arrow {{
                transform: rotate(180deg) translateX(4px);
            }}

            /* Responsive */
            @media (max-width: 768px) {{
                .container {{
                    padding: 1rem;
                }}
                .page-title {{
                    font-size: 1.4rem;
                }}
                .form-grid {{
                    grid-template-columns: 1fr;
                }}
                .inline-form {{
                    flex-direction: column;
                    align-items: flex-start;
                }}
                .header {{
                    padding: 1rem;
                }}
            }}
        </style>
        {rtl_styles}
    </head>
    <body>
        <div class="header">
            <a href="/admin/" style="font-weight:600;">{t('cms.name_short')}</a>
            <div class="header-right">{get_admin_header_right(lang_switcher, session.user_id)}</div>
        </div>
        {get_admin_nav()}

        <div class="container">
            <h1 class="page-title">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
                </svg>
                {t('admin.settings.title')}
            </h1>

            <div id="msg"></div>

            <form id="settings-form">
                <div class="settings-grid">

                    <!-- General Settings Card -->
                    <div class="settings-card">
                        <div class="card-header primary">
                            <div class="card-icon primary">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
                                </svg>
                            </div>
                            <h3 class="card-title">{t('admin.settings.general')}</h3>
                        </div>
                        <div class="card-body">
                            <div class="form-grid">
                                <div class="form-row">
                                    <label class="form-label">{t('admin.settings.site_title')}</label>
                                    <input class="form-input" name="site_title" value="{_html.escape(config.get('site_title',''))}">
                                </div>
                                <div class="form-row">
                                    <label class="form-label">{t('admin.settings.default_page')}</label>
                                    <input class="form-input" name="default_page" value="{_html.escape(config.get('default_page','home'))}">
                                </div>
                            </div>
                            <div class="form-grid" style="margin-top: 1.25rem;">
                                <div class="form-row">
                                    <label class="form-label">{t('admin.settings.site_lang')}</label>
                                    <select class="form-select" name="site_lang">{site_lang_options}</select>
                                </div>
                                <div class="form-row">
                                    <label class="form-label">{t('admin.settings.admin_lang')}</label>
                                    <select class="form-select" name="admin_lang">{admin_lang_options}</select>
                                </div>
                            </div>
                            <div class="form-grid" style="margin-top: 1.25rem;">
                                <div class="form-row">
                                    <label class="form-label">{t('admin.settings.theme')}</label>
                                    <select class="form-select" name="theme">{theme_options}</select>
                                </div>
                                <div class="form-row">
                                    <label class="form-label">{t('admin.settings.force_https')}</label>
                                    <select class="form-select" name="force_https">
                                        <option value="true" {'selected' if config.get('force_https', True) else ''}>True</option>
                                        <option value="false" {'selected' if not config.get('force_https', True) else ''}>False</option>
                                    </select>
                                </div>
                            </div>

                            <!-- Admin Login URL -->
                            <div class="form-row" style="margin-top: 1.25rem;">
                                <label class="form-label">{t('admin.settings.login_slug')}</label>
                                <div style="display: flex; align-items: center; gap: 0.5rem;">
                                    <span style="color: #64748b; font-size: 0.9rem;">/</span>
                                    <input class="form-input" name="login_slug" value="{_html.escape(config.get('login_slug',''))}" placeholder="secret-admin-path" style="flex: 1;">
                                </div>
                                <p style="font-size: 0.8rem; color: #64748b; margin: 0.5rem 0 0 0;">{t('admin.settings.login_slug_hint')}</p>
                            </div>

                            <!-- Copyright Link -->
                            <a href="/admin/copyright" class="link-card" style="margin-top: 1.5rem;">
                                <div class="link-card-icon">
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <circle cx="12" cy="12" r="10"/><path d="M14.83 14.83a4 4 0 1 1 0-5.66"/>
                                    </svg>
                                </div>
                                <div class="link-card-content">
                                    <p class="link-card-title">{t('admin.settings.copyright')}</p>
                                    <p class="link-card-desc">{t('admin.settings.copyright_hint')}</p>
                                </div>
                                <svg class="link-card-arrow" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="9 18 15 12 9 6"/>
                                </svg>
                            </a>
                        </div>
                    </div>

                    <!-- Search Settings Card -->
                    <div class="settings-card">
                        <div class="card-header search">
                            <div class="card-icon search">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
                                </svg>
                            </div>
                            <h3 class="card-title">{t('search.settings_title')}</h3>
                        </div>
                        <div class="card-body">
                            <label class="checkbox-row">
                                <input type="checkbox" class="checkbox-input" name="enable_search" {'checked' if config.get('enable_search', True) else ''}>
                                <div class="checkbox-content">
                                    <p class="checkbox-label">{t('search.enabled')}</p>
                                </div>
                            </label>
                            <label class="checkbox-row">
                                <input type="checkbox" class="checkbox-input" name="search_in_pages" {'checked' if config.get('search_in_pages', True) else ''}>
                                <div class="checkbox-content">
                                    <p class="checkbox-label">{t('search.search_in_pages')}</p>
                                </div>
                            </label>
                            <label class="checkbox-row">
                                <input type="checkbox" class="checkbox-input" name="search_in_blog" {'checked' if config.get('search_in_blog', True) else ''}>
                                <div class="checkbox-content">
                                    <p class="checkbox-label">{t('search.search_in_blog')}</p>
                                </div>
                            </label>
                            <div class="inline-form" style="margin-top: 1rem;">
                                <div class="inline-form-group">
                                    <label>{t('search.min_query_length')}:</label>
                                    <input type="number" name="search_min_chars" min="1" max="10" value="{config.get('search_min_chars', 2)}">
                                </div>
                                <div class="inline-form-group">
                                    <label>{t('search.max_results')}:</label>
                                    <input type="number" name="search_max_results" min="5" max="100" value="{config.get('search_max_results', 20)}">
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Access Control Card -->
                    <div class="settings-card">
                        <div class="card-header access">
                            <div class="card-icon access">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                                </svg>
                            </div>
                            <h3 class="card-title">{t('admin.settings.require_login')}</h3>
                        </div>
                        <div class="card-body">
                            <label class="checkbox-row">
                                <input type="checkbox" class="checkbox-input" name="require_login" id="require_login" {'checked' if config.get('require_login', False) else ''}>
                                <div class="checkbox-content">
                                    <p class="checkbox-label">{t('admin.settings.require_login')}</p>
                                    <p class="checkbox-hint">{t('admin.settings.require_login_hint')}</p>
                                </div>
                            </label>
                            <div id="allow_registration_row" class="{'hidden-row' if not config.get('require_login', False) else ''}">
                                <label class="checkbox-row">
                                    <input type="checkbox" class="checkbox-input" name="allow_registration" {'checked' if config.get('allow_registration', True) else ''}>
                                    <div class="checkbox-content">
                                        <p class="checkbox-label">{t('admin.settings.allow_registration')}</p>
                                        <p class="checkbox-hint">{t('admin.settings.allow_registration_hint')}</p>
                                    </div>
                                </label>
                            </div>

                            <!-- Jump to Top -->
                            <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #e2e8f0;">
                                <label class="checkbox-row">
                                    <input type="checkbox" class="checkbox-input" name="enable_jump_to_top" {'checked' if config.get('enable_jump_to_top', True) else ''}>
                                    <div class="checkbox-content">
                                        <p class="checkbox-label">{t('jump_to_top.enabled')}</p>
                                    </div>
                                </label>
                            </div>
                        </div>
                    </div>

                    <!-- Maintenance Mode Card -->
                    <div class="settings-card">
                        <div class="card-header warning">
                            <div class="card-icon warning">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                                    <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                                </svg>
                            </div>
                            <h3 class="card-title">{t('admin.settings.maintenance_mode')}</h3>
                        </div>
                        <div class="card-body">
                            <label class="checkbox-row">
                                <input type="checkbox" class="checkbox-input" name="maintenance_mode" id="maintenance_mode" {'checked' if config.get('maintenance_mode', False) else ''}>
                                <div class="checkbox-content">
                                    <p class="checkbox-label">{t('admin.settings.maintenance_mode')}</p>
                                    <p class="checkbox-hint">{t('admin.settings.maintenance_mode_hint')}</p>
                                </div>
                            </label>
                            <div id="maintenance_message_row" class="{'hidden-row' if not config.get('maintenance_mode', False) else ''}" style="margin-top: 1rem;">
                                <label class="form-label">{t('admin.settings.maintenance_message')}</label>
                                <textarea name="maintenance_message" rows="3" class="form-input" style="resize: vertical;">{_html.escape(config.get('maintenance_message', t('admin.settings.maintenance_message_default')))}</textarea>
                                <p style="font-size: 0.8rem; color: #92400e; margin: 0.5rem 0 0 0;">{t('admin.settings.maintenance_message_hint')}</p>
                            </div>
                        </div>
                    </div>

                    <!-- System Update Card -->
                    <div class="settings-card">
                        <div class="card-header update">
                            <div class="card-icon update">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16"/>
                                </svg>
                            </div>
                            <h3 class="card-title">{t('admin.settings.updates.title')}</h3>
                        </div>
                        <div class="card-body">
                            <div class="version-badge">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="20 6 9 17 4 12"/>
                                </svg>
                                {t('admin.settings.updates.current_version')}: {CMS_VERSION}
                            </div>

                            <div id="update-status"></div>
                            <div id="update-info">
                                <p style="font-weight: 600;">{t('admin.settings.updates.available')}</p>
                                <p id="update-details" style="font-size: 0.9rem;"></p>
                                <button type="button" id="apply-update-btn" class="btn btn-success" style="margin-top: 1rem;">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                                    </svg>
                                    {t('admin.settings.updates.apply')}
                                </button>
                                <p style="margin: 0.75rem 0 0 0; color: #dc2626; font-size: 0.8rem;">
                                    {t('admin.settings.updates.restart_warning')}
                                </p>
                            </div>

                            <button type="button" id="check-update-btn" class="btn btn-check" style="margin-top: 1rem;">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
                                </svg>
                                {t('admin.settings.updates.check')}
                            </button>
                        </div>
                    </div>

                </div>

                <button class="btn btn-primary btn-save" type="submit">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
                    </svg>
                    {t('common.save')}
                </button>
            </form>
        </div>
        <script>
            const csrfToken = {csrf_token!r};
            document.getElementById('settings-form').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const form = e.target;
                const data = Object.fromEntries(new FormData(form).entries());
                data.force_https = data.force_https === 'true';
                // Handle search checkboxes
                data.enable_search = form.querySelector('[name="enable_search"]').checked;
                data.search_in_pages = form.querySelector('[name="search_in_pages"]').checked;
                data.search_in_blog = form.querySelector('[name="search_in_blog"]').checked;
                data.search_min_chars = parseInt(data.search_min_chars) || 2;
                data.search_max_results = parseInt(data.search_max_results) || 20;
                // Handle Jump to Top checkbox
                data.enable_jump_to_top = form.querySelector('[name="enable_jump_to_top"]').checked;
                // Handle Maintenance Mode
                data.maintenance_mode = form.querySelector('[name="maintenance_mode"]').checked;
                data.maintenance_message = form.querySelector('[name="maintenance_message"]').value;
                // Handle Login Required
                data.require_login = form.querySelector('[name="require_login"]').checked;
                data.allow_registration = form.querySelector('[name="allow_registration"]').checked;
                const res = await fetch('/admin/api/settings', {{
                    method: 'PUT',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken,
                    }},
                    credentials: 'same-origin',
                    body: JSON.stringify(data),
                }});
                const msgEl = document.getElementById('msg');
                if (!res.ok) {{
                    const text = await res.text();
                    msgEl.className = 'error';
                    msgEl.textContent = text || 'Failed to save settings';
                    return;
                }}
                // Update the login_slug field with the new value from response
                const result = await res.json();
                if (result.login_slug) {{
                    form.querySelector('[name="login_slug"]').value = result.login_slug;
                }}
                msgEl.className = 'success';
                msgEl.textContent = '{t("admin.settings.save_success")}';
            }});

            // Update checking functionality
            const checkBtn = document.getElementById('check-update-btn');
            const applyBtn = document.getElementById('apply-update-btn');
            const statusEl = document.getElementById('update-status');
            const infoEl = document.getElementById('update-info');
            const detailsEl = document.getElementById('update-details');
            let latestCommit = null;

            function showStatus(message, isError = false) {{
                statusEl.style.display = 'block';
                statusEl.style.background = isError ? '#fee2e2' : '#dcfce7';
                statusEl.style.color = isError ? '#b91c1c' : '#16a34a';
                statusEl.textContent = message;
            }}

            checkBtn.addEventListener('click', async () => {{
                checkBtn.disabled = true;
                checkBtn.textContent = '{t("admin.settings.updates.checking")}';
                statusEl.style.display = 'none';
                infoEl.style.display = 'none';

                try {{
                    const res = await fetch('/admin/api/updates/check', {{
                        credentials: 'same-origin',
                    }});
                    const data = await res.json();

                    if (data.error) {{
                        showStatus(data.error, true);
                    }} else if (data.update_available) {{
                        latestCommit = data.latest_commit;
                        const date = data.commit_date ? new Date(data.commit_date).toLocaleString() : '';
                        detailsEl.innerHTML = `
                            <strong>{t('admin.settings.updates.commit_date')}:</strong> ${{date}}<br>
                            <strong>{t('admin.settings.updates.commit_message')}:</strong> ${{data.commit_message || ''}}
                        `;
                        infoEl.style.display = 'block';
                    }} else {{
                        showStatus('{t("admin.settings.updates.up_to_date")}', false);
                    }}
                }} catch (err) {{
                    showStatus('{t("admin.settings.updates.check_error")}', true);
                }} finally {{
                    checkBtn.disabled = false;
                    checkBtn.textContent = '{t("admin.settings.updates.check")}';
                }}
            }});

            applyBtn.addEventListener('click', async () => {{
                if (!confirm('{t("admin.settings.updates.confirm")}')) return;

                applyBtn.disabled = true;
                applyBtn.textContent = '{t("admin.settings.updates.applying")}';

                try {{
                    const res = await fetch('/admin/api/updates/apply', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': csrfToken,
                        }},
                        credentials: 'same-origin',
                    }});
                    const data = await res.json();

                    if (data.success) {{
                        infoEl.style.display = 'none';
                        showStatus('{t("admin.settings.updates.success")}', false);
                    }} else {{
                        showStatus(data.error || '{t("admin.settings.updates.apply_error")}', true);
                    }}
                }} catch (err) {{
                    showStatus('{t("admin.settings.updates.apply_error")}', true);
                }} finally {{
                    applyBtn.disabled = false;
                    applyBtn.textContent = '{t("admin.settings.updates.apply")}';
                }}
            }});

            // Toggle maintenance message field visibility
            document.getElementById('maintenance_mode').addEventListener('change', function() {{
                document.getElementById('maintenance_message_row').style.display = this.checked ? '' : 'none';
            }});

            // Toggle allow registration field visibility
            document.getElementById('require_login').addEventListener('change', function() {{
                document.getElementById('allow_registration_row').style.display = this.checked ? '' : 'none';
            }});
        </script>
        {get_admin_footer()}
    </body>
    </html>
    """
    response = HTMLResponse(html)
    if needs_cookie:
        set_csrf_cookie(request, response, csrf_token)
    return response


# ============================================================================
# Copyright Settings
# ============================================================================

@router.get("/copyright", response_class=HTMLResponse)
async def copyright_page(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
):
    """Render copyright settings page."""
    import html as _html

    from ..main import storage

    # Get language context
    lang_ctx = get_admin_lang_context(request)
    html_attrs = get_admin_html_attrs(request)
    lang_switcher = get_admin_language_switcher_html(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""

    config = storage.get("config", {})
    copyright_text = config.get("copyright_text", "Copyright 2026 ChelCheleh v0.1.0 — Designed by Ahmad Batebi")

    csrf_token, needs_cookie = get_csrf_token(request)
    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.settings.copyright')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="/admin/static/css/admin-common.css">
        {rtl_styles}
    </head>
    <body>
        <div class="header">
            <a href="/admin/" style="font-size:1.25rem;font-weight:700;color:white;text-decoration:none;">{t('cms.name_short')}</a>
            <div class="header-right">
                {lang_switcher}
                <a href="/" target="_blank" style="color:#94a3b8;text-decoration:none;">{t('admin.view_site')}</a>
                <span style="color:#64748b;">|</span>
                <span style="color:#e2e8f0;">{session.user_id}</span>
                <a href="/admin/logout" style="color:#f87171;text-decoration:none;">{t('admin.logout')}</a>
            </div>
        </div>
        {get_admin_nav()}
        <div class="container">
            <!-- Breadcrumb -->
            <a href="/admin/settings" class="back-link">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                </svg>
                {t('common.back')} {t('admin.settings.title')}
            </a>

            <!-- Page Header -->
            <h1 class="page-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <circle cx="12" cy="12" r="10"/><path d="M14.83 14.83a4 4 0 1 1 0-5.66"/>
                </svg>
                {t('admin.settings.copyright')}
            </h1>

            <!-- Message -->
            <div id="msg" class="alert" style="display:none;"></div>

            <!-- Copyright Form Card -->
            <div class="card card-static">
                <div class="card-header info">
                    <div class="card-icon info">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                    </div>
                    <h3 class="card-title">{t('admin.settings.copyright_text')}</h3>
                </div>
                <div class="card-body">
                    <p class="text-muted" style="margin-bottom:1rem;">{t('admin.settings.copyright_hint')}</p>
                    <form id="copyright-form">
                        <div class="form-group">
                            <label class="form-label">{t('admin.settings.copyright_text')}</label>
                            <textarea name="copyright_text" id="copyright_text" class="form-input" rows="4" placeholder="{t('admin.settings.copyright_placeholder')}">{_html.escape(copyright_text)}</textarea>
                        </div>
                    </form>
                </div>
                <div class="card-footer" style="display:flex;justify-content:flex-end;">
                    <button class="btn btn-primary" type="button" id="save-btn">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                        {t('common.save')}
                    </button>
                </div>
            </div>
        </div>
        <script>
            const csrfToken = {csrf_token!r};

            const showMsg = (text, type = 'error') => {{
                const msg = document.getElementById('msg');
                msg.textContent = text;
                msg.className = 'alert alert-' + type;
                msg.style.display = 'flex';
                setTimeout(() => {{ msg.style.display = 'none'; }}, 5000);
            }};

            document.getElementById('save-btn').addEventListener('click', async () => {{
                const data = {{
                    copyright_text: document.getElementById('copyright_text').value
                }};
                const res = await fetch('/admin/api/copyright', {{
                    method: 'PUT',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken,
                    }},
                    credentials: 'same-origin',
                    body: JSON.stringify(data),
                }});
                if (!res.ok) {{
                    const text = await res.text();
                    showMsg(text || '{t("errors.save_failed")}');
                    return;
                }}
                showMsg('{t("admin.settings.copyright_saved")}', 'success');
            }});
        </script>
        {get_admin_footer()}
    </body>
    </html>
    """
    response = HTMLResponse(html)
    if needs_cookie:
        set_csrf_cookie(request, response, csrf_token)
    return response


# ============================================================================
# Menu Management
# ============================================================================

@router.get("/menu", response_class=HTMLResponse)
async def menu_page(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
):
    """Render menu management page."""
    import html as _html

    from ..main import storage

    menu_items = storage.get("menu_items", [])
    pages = storage.get("pages", {})

    # Sort menu items by order
    menu_items = sorted(menu_items, key=lambda x: x.get("order", 0))

    # Build table rows with improved design
    rows = ""
    for idx, item in enumerate(menu_items):
        visibility_show = "selected" if item.get("visibility") == "show" else ""
        visibility_hide = "selected" if item.get("visibility") == "hide" else ""
        is_visible = item.get("visibility") == "show"
        badge_class = 'badge-success' if is_visible else 'badge-gray'
        item_lang = item.get("language", "both")
        lang_both = "selected" if item_lang == "both" else ""
        lang_en = "selected" if item_lang == "en" else ""
        lang_fa = "selected" if item_lang == "fa" else ""
        rows += f"""
        <tr data-slug="{_html.escape(item.get('slug', ''))}">
            <td class="order-cell">
                <div class="order-badge">{idx + 1}</div>
            </td>
            <td>
                <div style="display:flex;align-items:center;gap:0.75rem;">
                    <div style="width:36px;height:36px;border-radius:8px;background:linear-gradient(135deg,#06b6d4,#0891b2);display:flex;align-items:center;justify-content:center;color:white;flex-shrink:0;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                        </svg>
                    </div>
                    <input class="form-input name-input" value="{_html.escape(item.get('name', ''))}" style="max-width:200px;">
                </div>
            </td>
            <td><code style="background:#f1f5f9;padding:0.25rem 0.5rem;border-radius:4px;font-size:0.85rem;">/{_html.escape(item.get('slug', ''))}</code></td>
            <td>
                <select class="form-select visibility-select" style="max-width:120px;">
                    <option value="show" {visibility_show}>{t('admin.pages.show')}</option>
                    <option value="hide" {visibility_hide}>{t('admin.pages.hide')}</option>
                </select>
            </td>
            <td>
                <select class="form-select language-select" style="max-width:140px;">
                    <option value="both" {lang_both}>{t('admin.menu.lang_both')}</option>
                    <option value="en" {lang_en}>{t('admin.menu.lang_en')}</option>
                    <option value="fa" {lang_fa}>{t('admin.menu.lang_fa')}</option>
                </select>
            </td>
            <td class="actions-cell">
                <div class="actions">
                    <button class="btn btn-sm btn-outline up-btn" type="button" title="{t('common.up')}">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                        </svg>
                    </button>
                    <button class="btn btn-sm btn-outline down-btn" type="button" title="{t('common.down')}">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                        </svg>
                    </button>
                    <button class="btn btn-sm btn-danger delete-btn" type="button" title="{t('common.delete')}">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                    </button>
                </div>
            </td>
        </tr>
        """

    # Build page options for add dropdown
    page_options = ""
    for slug, page in pages.items():
        # Check if page already in menu
        in_menu = any(m.get("slug") == slug for m in menu_items)
        if not in_menu:
            page_options += f'<option value="{_html.escape(slug)}">{_html.escape(page.get("title", slug))}</option>'

    empty_state = ""
    if not menu_items:
        empty_state = f'''
            <div class="empty-state">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
                </svg>
                <h3>{t('admin.menu.no_items')}</h3>
                <p>{t('admin.menu.add_first')}</p>
            </div>
        '''

    html_attrs = get_admin_html_attrs(request)
    lang_ctx = get_admin_lang_context(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""
    lang_switcher = get_admin_language_switcher_html(request)
    csrf_token, needs_cookie = get_csrf_token(request)
    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.menu.title')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="/admin/static/css/admin-common.css">
        <style>
            .order-cell {{
                width: 60px;
            }}
            .order-badge {{
                width: 32px;
                height: 32px;
                background: linear-gradient(135deg, #6366f1, #4f46e5);
                color: white;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 600;
                font-size: 0.9rem;
            }}
            .actions-cell {{
                width: 150px;
            }}
            .actions-cell .actions {{
                justify-content: flex-end;
            }}
            [dir="rtl"] .actions-cell .actions {{
                justify-content: flex-start;
            }}
            .add-form-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr auto;
                gap: 1rem;
                align-items: end;
            }}
            @media (max-width: 768px) {{
                .add-form-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
        {rtl_styles}
    </head>
    <body>
        <div class="header">
            <a href="/admin/" style="font-size:1.25rem;font-weight:700;color:white;text-decoration:none;">{t('cms.name_short')}</a>
            <div class="header-right">
                {lang_switcher}
                <a href="/" target="_blank" style="color:#94a3b8;text-decoration:none;">{t('admin.view_site')}</a>
                <span style="color:#64748b;">|</span>
                <span style="color:#e2e8f0;">{session.user_id}</span>
                <a href="/admin/logout" style="color:#f87171;text-decoration:none;">{t('admin.logout')}</a>
            </div>
        </div>
        {get_admin_nav()}
        <div class="container">
            <!-- Page Header -->
            <h1 class="page-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
                </svg>
                {t('admin.menu.title')}
            </h1>

            <!-- Message -->
            <div id="msg" class="alert" style="display:none;"></div>

            <!-- Add Menu Item Card -->
            <div class="card card-static" style="margin-bottom: 2rem;">
                <div class="card-header success">
                    <div class="card-icon success">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                        </svg>
                    </div>
                    <h3 class="card-title">{t('admin.menu.add_item')}</h3>
                </div>
                <div class="card-body">
                    <div class="add-form-grid">
                        <div class="form-group" style="margin-bottom:0;">
                            <label class="form-label">{t('admin.menu.page_link')}</label>
                            <select id="add-page" class="form-select">
                                <option value="">-- {t('admin.menu.select_page')} --</option>
                                {page_options}
                            </select>
                        </div>
                        <div class="form-group" style="margin-bottom:0;">
                            <label class="form-label">{t('admin.menu.display_name')}</label>
                            <input type="text" id="add-name" class="form-input" placeholder="{t('admin.menu.optional_name')}">
                        </div>
                        <button class="btn btn-success" id="add-btn" type="button">
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                            </svg>
                            {t('common.add')}
                        </button>
                    </div>
                </div>
            </div>

            <!-- Menu Items Card -->
            <div class="card card-static">
                <div class="card-header info">
                    <div class="card-icon info">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                        </svg>
                    </div>
                    <h3 class="card-title">{t('admin.menu.items')} ({len(menu_items)})</h3>
                </div>
                {"<div class='card-body'>" + empty_state + "</div>" if not menu_items else f'''
                <div class="table-container">
                    <table class="table" id="menu-table">
                        <thead>
                            <tr>
                                <th>{t('admin.menu.order')}</th>
                                <th>{t('common.name')}</th>
                                <th>{t('admin.pages.slug')}</th>
                                <th>{t('admin.menu.visibility')}</th>
                                <th>{t('admin.menu.language')}</th>
                                <th style="text-align:right;">{t('common.actions')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows}
                        </tbody>
                    </table>
                </div>
                <div class="card-footer" style="display:flex;justify-content:flex-end;">
                    <button class="btn btn-primary" id="save-btn" type="button">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                        {t('common.save')}
                    </button>
                </div>
                '''}
            </div>
        </div>
        <script>
            const csrfToken = {csrf_token!r};

            const showMsg = (text, type = 'error') => {{
                const msg = document.getElementById('msg');
                msg.textContent = text;
                msg.className = 'alert alert-' + type;
                msg.style.display = 'flex';
                setTimeout(() => {{ msg.style.display = 'none'; }}, 5000);
            }};

            function updateOrder() {{
                const rows = document.querySelectorAll('#menu-table tbody tr');
                rows.forEach((row, idx) => {{
                    row.querySelector('.order-badge').textContent = idx + 1;
                }});
            }}

            // Add new menu item
            document.getElementById('add-btn').addEventListener('click', async () => {{
                const pageSelect = document.getElementById('add-page');
                const nameInput = document.getElementById('add-name');
                const slug = pageSelect.value;
                if (!slug) {{
                    showMsg('{t("admin.menu.select_page_first")}');
                    return;
                }}
                const name = nameInput.value.trim() || pageSelect.options[pageSelect.selectedIndex].text;

                const res = await fetch('/admin/api/menu', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken,
                    }},
                    credentials: 'same-origin',
                    body: JSON.stringify({{ slug, name }}),
                }});

                if (!res.ok) {{
                    const text = await res.text();
                    showMsg(text || '{t("admin.menu.add_failed")}');
                    return;
                }}

                showMsg('{t("admin.menu.added_success")}', 'success');
                setTimeout(() => window.location.reload(), 1000);
            }});

            // Move up
            document.querySelectorAll('.up-btn').forEach(btn => {{
                btn.addEventListener('click', (e) => {{
                    const row = e.target.closest('tr');
                    const prev = row.previousElementSibling;
                    if (prev) {{
                        row.parentNode.insertBefore(row, prev);
                        updateOrder();
                    }}
                }});
            }});

            // Move down
            document.querySelectorAll('.down-btn').forEach(btn => {{
                btn.addEventListener('click', (e) => {{
                    const row = e.target.closest('tr');
                    const next = row.nextElementSibling;
                    if (next) {{
                        row.parentNode.insertBefore(next, row);
                        updateOrder();
                    }}
                }});
            }});

            // Delete
            document.querySelectorAll('.delete-btn').forEach(btn => {{
                btn.addEventListener('click', async (e) => {{
                    if (!confirm('{t("admin.menu.confirm_remove")}')) return;
                    const row = e.target.closest('tr');
                    const slug = row.dataset.slug;

                    const res = await fetch(`/admin/api/menu/${{encodeURIComponent(slug)}}`, {{
                        method: 'DELETE',
                        headers: {{ 'X-CSRF-Token': csrfToken }},
                        credentials: 'same-origin',
                    }});

                    if (!res.ok) {{
                        const text = await res.text();
                        showMsg(text || '{t("admin.menu.delete_failed")}');
                        return;
                    }}

                    row.remove();
                    updateOrder();
                    showMsg('{t("admin.menu.removed_success")}', 'success');
                }});
            }});

            // Save all
            const saveBtn = document.getElementById('save-btn');
            if (saveBtn) {{
                saveBtn.addEventListener('click', async () => {{
                    const rows = document.querySelectorAll('#menu-table tbody tr');
                    const items = [];
                    rows.forEach((row, idx) => {{
                        items.push({{
                            slug: row.dataset.slug,
                            name: row.querySelector('.name-input').value,
                            visibility: row.querySelector('.visibility-select').value,
                            language: row.querySelector('.language-select').value,
                            order: idx,
                        }});
                    }});

                    const res = await fetch('/admin/api/menu', {{
                        method: 'PUT',
                        headers: {{
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': csrfToken,
                        }},
                        credentials: 'same-origin',
                        body: JSON.stringify({{ items }}),
                    }});

                    if (!res.ok) {{
                        const text = await res.text();
                        showMsg(text || '{t("admin.menu.save_failed")}');
                        return;
                    }}

                    showMsg('{t("admin.menu.saved_success")}', 'success');
                }});
            }}
        </script>
        {get_admin_footer()}
    </body>
    </html>
    """
    response = HTMLResponse(html)
    if needs_cookie:
        set_csrf_cookie(request, response, csrf_token)
    return response


# ============================================================================
# Menu API
# ============================================================================

@router.get("/api/menu")
async def list_menu(
    session=Depends(require_auth()),
):
    """List all menu items."""
    from ..main import storage

    menu_items = storage.get("menu_items", [])
    return {"items": menu_items}


@router.post("/api/menu")
async def add_menu_item(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Add a new menu item."""
    from ..main import storage, audit_logger

    data = await request.json()
    slug = data.get("slug", "").strip()
    name = data.get("name", "").strip()
    language = data.get("language", "both")

    if not slug:
        raise HTTPException(status_code=400, detail="Slug is required")

    # Validate language
    if language not in ("en", "fa", "both"):
        language = "both"

    # Check page exists
    page = storage.get(f"pages.{slug}")
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Get current menu
    menu_items = storage.get("menu_items", [])

    # Check if already in menu
    if any(m.get("slug") == slug for m in menu_items):
        raise HTTPException(status_code=409, detail="Page already in menu")

    # Add new item
    new_item = {
        "name": name or page.get("title", slug),
        "slug": slug,
        "visibility": "show",
        "language": language,
        "order": len(menu_items),
    }
    menu_items.append(new_item)
    storage.set("menu_items", menu_items)

    audit_logger.log(
        "menu_add",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        details={"slug": slug},
    )

    return new_item


@router.put("/api/menu")
async def update_menu(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Update entire menu (bulk update)."""
    from ..main import storage, audit_logger

    data = await request.json()
    items = data.get("items", [])

    # Validate and rebuild menu
    new_menu = []
    for idx, item in enumerate(items):
        slug = item.get("slug", "").strip()
        if not slug:
            continue
        language = item.get("language", "both")
        if language not in ("en", "fa", "both"):
            language = "both"
        new_menu.append({
            "name": item.get("name", slug),
            "slug": slug,
            "visibility": item.get("visibility", "show"),
            "language": language,
            "order": idx,
        })

    storage.set("menu_items", new_menu)

    audit_logger.log(
        "menu_update",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        details={"count": len(new_menu)},
    )

    return {"items": new_menu}


@router.delete("/api/menu/{slug}")
async def delete_menu_item(
    slug: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Delete a menu item."""
    from ..main import storage, audit_logger

    menu_items = storage.get("menu_items", [])

    # Find and remove item
    new_menu = [m for m in menu_items if m.get("slug") != slug]

    if len(new_menu) == len(menu_items):
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Update order
    for idx, item in enumerate(new_menu):
        item["order"] = idx

    storage.set("menu_items", new_menu)

    audit_logger.log(
        "menu_delete",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        details={"slug": slug},
    )

    return {"status": "deleted", "slug": slug}


# ============================================================================
# Page Templates
# ============================================================================

TEMPLATE_INFO = {
    "default": {
        "name": "Default",
        "description": "Standard template using base.html",
        "preview_bg": "#f5f5f5",
        "preview_header": "#1e293b",
        "preview_footer": "#f3f4f6",
    },
    "light": {
        "name": "Light",
        "description": "Clean, bright design with blue accents",
        "preview_bg": "#ffffff",
        "preview_header": "#ffffff",
        "preview_footer": "#f3f4f6",
    },
    "dark": {
        "name": "Dark",
        "description": "Modern, sleek design with cyan accents and glow effects",
        "preview_bg": "#0f172a",
        "preview_header": "#1e293b",
        "preview_footer": "#020617",
    },
    "mixed": {
        "name": "Mixed",
        "description": "Gradient header, light body, and dark footer",
        "preview_bg": "#ffffff",
        "preview_header": "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
        "preview_footer": "#1e293b",
    },
}

def normalize_template(value: str | None) -> str:
    """Normalize template name to a supported template."""
    if not value:
        return "default"
    value = str(value)
    return value if value in TEMPLATE_INFO else "default"


@router.get("/templates", response_class=HTMLResponse)
async def templates_page(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
):
    """Render page templates management page."""
    import html as _html

    from ..main import storage

    pages = storage.get("pages", {})

    # Count pages by template
    template_counts = {"default": 0, "light": 0, "dark": 0, "mixed": 0}
    for page in pages.values():
        tpl = page.get("template", "default")
        if tpl in template_counts:
            template_counts[tpl] += 1
        else:
            template_counts["default"] += 1

    # Template colors for icons
    template_colors = {
        "default": "#64748b",
        "light": "#3b82f6",
        "dark": "#06b6d4",
        "mixed": "#7c3aed",
    }

    # Build template cards
    template_cards = ""
    for tpl_id, tpl_info in TEMPLATE_INFO.items():
        count = template_counts.get(tpl_id, 0)
        header_style = tpl_info["preview_header"]
        if header_style.startswith("linear"):
            header_css = f"background: {header_style};"
        else:
            header_css = f"background-color: {header_style};"

        # Get translated name and description
        tpl_name = t(f'admin.themes.{tpl_id}.name')
        tpl_desc = t(f'admin.themes.{tpl_id}.description')
        page_label = t('admin.themes.page') if count == 1 else t('admin.themes.pages')
        icon_color = template_colors.get(tpl_id, "#64748b")

        template_cards += f"""
        <div class="template-card">
            <div class="preview">
                <div class="preview-header" style="{header_css}"></div>
                <div class="preview-body" style="background-color: {tpl_info['preview_bg']};"></div>
                <div class="preview-footer" style="background-color: {tpl_info['preview_footer']};"></div>
            </div>
            <div class="template-info">
                <div class="template-name">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{icon_color}" stroke-width="2">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                        <line x1="3" y1="9" x2="21" y2="9"/>
                        <line x1="9" y1="21" x2="9" y2="9"/>
                    </svg>
                    <h3>{_html.escape(tpl_name)}</h3>
                </div>
                <p>{_html.escape(tpl_desc)}</p>
                <span class="count-badge">{count} {page_label}</span>
            </div>
        </div>
        """

    # Build pages table
    pages_rows = ""
    for slug, page in pages.items():
        tpl = normalize_template(page.get("template"))
        tpl_name = t(f'admin.themes.{tpl}.name')
        options = "\n".join(
            f"<option value=\"{tpl_id}\" {'selected' if tpl_id == tpl else ''}>"
            f"{_html.escape(t(f'admin.themes.{tpl_id}.name'))}</option>"
            for tpl_id in TEMPLATE_INFO.keys()
        )
        pages_rows += f"""
        <tr>
            <td>
                <div style="display:flex;align-items:center;gap:0.75rem;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                    </svg>
                    <span style="font-weight:500;">{_html.escape(page.get('title', slug))}</span>
                </div>
            </td>
            <td style="color:#64748b;font-family:monospace;font-size:0.875rem;">/{_html.escape(slug)}</td>
            <td><span class="template-badge template-{_html.escape(tpl)}">{_html.escape(tpl_name)}</span></td>
            <td>
                <select class="template-select" data-slug="{_html.escape(slug)}">
                    {options}
                </select>
            </td>
        </tr>
        """

    empty_state = f'''
    <tr>
        <td colspan="4">
            <div class="empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.5">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                </svg>
                <p style="margin:0.5rem 0;color:#64748b;">{t('admin.pages.no_pages')}</p>
            </div>
        </td>
    </tr>
    '''

    html_attrs = get_admin_html_attrs(request)
    lang_ctx = get_admin_lang_context(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""
    lang_switcher = get_admin_language_switcher_html(request)
    csrf_token, needs_cookie = get_csrf_token(request)
    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.themes.title')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        {get_admin_common_css()}
        <style>
            .templates-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }}

            .template-card {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                overflow: hidden;
                transition: all 0.3s;
                border: 2px solid transparent;
            }}
            .template-card:hover {{
                transform: translateY(-4px);
                box-shadow: 0 8px 24px rgba(0,0,0,0.12);
                border-color: #7c3aed;
            }}

            .preview {{
                height: 100px;
                display: flex;
                flex-direction: column;
                border-bottom: 1px solid #e2e8f0;
            }}
            .preview-header {{
                height: 20px;
                flex-shrink: 0;
            }}
            .preview-body {{
                flex: 1;
            }}
            .preview-footer {{
                height: 16px;
                flex-shrink: 0;
            }}

            .template-info {{
                padding: 1rem 1.25rem;
            }}
            .template-name {{
                display: flex;
                align-items: center;
                gap: 0.5rem;
                margin-bottom: 0.5rem;
            }}
            .template-name h3 {{
                margin: 0;
                font-size: 1rem;
                color: #1e293b;
            }}
            .template-info p {{
                color: #64748b;
                font-size: 0.875rem;
                margin: 0 0 0.75rem;
                line-height: 1.4;
            }}

            .count-badge {{
                display: inline-flex;
                align-items: center;
                gap: 0.25rem;
                padding: 0.25rem 0.75rem;
                background: #ede9fe;
                color: #7c3aed;
                border-radius: 9999px;
                font-size: 0.75rem;
                font-weight: 500;
            }}

            .template-badge {{
                display: inline-block;
                padding: 0.25rem 0.75rem;
                border-radius: 9999px;
                font-size: 0.75rem;
                font-weight: 500;
            }}
            .template-default {{ background: #f1f5f9; color: #475569; }}
            .template-light {{ background: #dbeafe; color: #1d4ed8; }}
            .template-dark {{ background: #1e293b; color: #06b6d4; }}
            .template-mixed {{ background: linear-gradient(135deg, #4f46e5, #7c3aed); color: white; }}

            .template-select {{
                padding: 0.375rem 0.75rem;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 0.875rem;
                background: white;
                cursor: pointer;
                min-width: 120px;
            }}
            .template-select:focus {{
                outline: none;
                border-color: #7c3aed;
                box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
            }}
            .empty-state {{
                text-align: center;
                padding: 3rem 1rem;
            }}
        </style>
        {rtl_styles}
    </head>
    <body>
        <div class="header">
            <a href="/admin/" style="font-size:1.25rem;font-weight:700;color:white;text-decoration:none;">{t('cms.name_short')}</a>
            <div class="header-right">
                {lang_switcher}
                <a href="/" target="_blank">{t('admin.view_site')}</a>
                <span style="color:#64748b;">|</span>
                <span style="color:#e2e8f0;">{session.user_id}</span>
                <a href="/admin/logout" style="color:#f87171;">{t('admin.logout')}</a>
            </div>
        </div>
        {get_admin_nav()}
        <div class="container">
            <h1 class="page-title">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                    <line x1="3" y1="9" x2="21" y2="9"/>
                    <line x1="9" y1="21" x2="9" y2="9"/>
                </svg>
                {t('admin.themes.title')}
            </h1>
            <p style="color:#64748b;margin-bottom:1.5rem;">{t('admin.themes.description')}</p>

            <div id="msg" class="alert" style="display:none;"></div>

            <div class="templates-grid">
                {template_cards}
            </div>

            <div class="card card-static">
                <div class="card-header purple">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                    </svg>
                    {t('admin.themes.pages_by_template')}
                </div>
                <div class="card-body" style="padding:0;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>{t('common.title')}</th>
                                <th>{t('admin.pages.slug')}</th>
                                <th>{t('admin.pages.template')}</th>
                                <th style="width:150px;">{t('admin.themes.change')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {pages_rows if pages_rows else empty_state}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <script>
            const csrfToken = {csrf_token!r};
            function showMsg(type, text) {{
                const msg = document.getElementById('msg');
                msg.className = 'alert alert-' + type;
                msg.textContent = text;
                msg.style.display = 'block';
                setTimeout(() => {{ msg.style.display = 'none'; }}, 5000);
            }}
            document.querySelectorAll('.template-select').forEach((select) => {{
                select.addEventListener('change', async (e) => {{
                    const slug = e.target.dataset.slug;
                    const template = e.target.value;
                    const res = await fetch(`/admin/api/pages/${{encodeURIComponent(slug)}}`, {{
                        method: 'PUT',
                        headers: {{
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': csrfToken,
                        }},
                        credentials: 'same-origin',
                        body: JSON.stringify({{ template }}),
                    }});
                    if (!res.ok) {{
                        const text = await res.text();
                        showMsg('error', text || 'Failed to update template');
                        return;
                    }}
                    showMsg('success', '{t("messages.updated")}');
                    const row = e.target.closest('tr');
                    const badge = row.querySelector('.template-badge');
                    badge.className = `template-badge template-${{template}}`;
                    const templateNames = {{
                        'default': '{t("admin.themes.default.name")}',
                        'light': '{t("admin.themes.light.name")}',
                        'dark': '{t("admin.themes.dark.name")}',
                        'mixed': '{t("admin.themes.mixed.name")}'
                    }};
                    badge.textContent = templateNames[template] || template;
                }});
            }});
        </script>
        {get_admin_footer()}
    </body>
    </html>
    """
    response = HTMLResponse(html)
    if needs_cookie:
        set_csrf_cookie(request, response, csrf_token)
    return response


# ============================================================================
# Pages API
# ============================================================================

@router.get("/api/pages")
async def list_pages(
    session=Depends(require_auth()),
):
    """List all pages."""
    from ..main import storage

    pages = storage.get("pages", {})
    return {"pages": list(pages.values())}


@router.get("/api/pages/{slug}")
async def get_page(
    slug: str,
    session=Depends(require_auth()),
):
    """Get a single page."""
    from ..main import storage

    page = storage.get(f"pages.{slug}")
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    return page


@router.post("/api/pages")
async def create_page(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Create a new page."""
    from ..main import storage, sanitizer, audit_logger

    data = await request.json()

    slug = sanitizer.slugify(data.get("title", "untitled"))

    # Check if slug exists
    if storage.get(f"pages.{slug}"):
        raise HTTPException(status_code=409, detail="Page already exists")

    page = {
        "title": data.get("title", "Untitled"),
        "slug": slug,
        "content": data.get("content", ""),
        "content_format": "html",  # WYSIWYG editor produces HTML
        "description": data.get("description", ""),
        "keywords": data.get("keywords", ""),
        "visibility": data.get("visibility", "show"),
        "template": normalize_template(data.get("template")),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "modified_at": datetime.now(timezone.utc).isoformat(),
        "modified_by": session.user_id,
    }

    storage.set(f"pages.{slug}", page)

    audit_logger.log(
        "page_create",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        details={"slug": slug},
    )

    return page


@router.put("/api/pages/{slug}")
async def update_page(
    slug: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Update a page."""
    from ..main import storage, sanitizer, audit_logger

    page = storage.get(f"pages.{slug}")
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    data = await request.json()

    # Update fields
    page["title"] = data.get("title", page["title"])
    page["content"] = data.get("content", page["content"])
    page["content_format"] = "html"
    page["description"] = data.get("description", page.get("description", ""))
    page["keywords"] = data.get("keywords", page.get("keywords", ""))
    page["visibility"] = data.get("visibility", page.get("visibility", "show"))
    page["template"] = normalize_template(data.get("template", page.get("template", "default")))
    # Display options - handle both boolean and checkbox string values
    hide_title = data.get("hide_title", page.get("hide_title", False))
    page["hide_title"] = hide_title if isinstance(hide_title, bool) else hide_title == "on"
    hide_description = data.get("hide_description", page.get("hide_description", False))
    page["hide_description"] = hide_description if isinstance(hide_description, bool) else hide_description == "on"
    # Blog columns - convert to int, default to 2
    blog_columns = data.get("blog_columns", page.get("blog_columns", 2))
    try:
        page["blog_columns"] = max(1, min(3, int(blog_columns)))  # Clamp between 1 and 3
    except (ValueError, TypeError):
        page["blog_columns"] = 2
    # Posts per page - convert to int, default to 10
    posts_per_page = data.get("posts_per_page", page.get("posts_per_page", 10))
    try:
        page["posts_per_page"] = max(1, min(50, int(posts_per_page)))  # Clamp between 1 and 50
    except (ValueError, TypeError):
        page["posts_per_page"] = 10
    # Language settings
    language = data.get("language", page.get("language", "both"))
    if language in ("en", "fa", "both"):
        page["language"] = language
    else:
        page["language"] = "both"
    # Associated page - handle empty string as None
    associated_page = data.get("associated_page", page.get("associated_page"))
    page["associated_page"] = associated_page if associated_page else None
    page["modified_at"] = datetime.now(timezone.utc).isoformat()
    page["modified_by"] = session.user_id

    storage.set(f"pages.{slug}", page)

    audit_logger.log(
        "page_update",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        details={"slug": slug},
    )

    return page


@router.delete("/api/pages/{slug}")
async def delete_page(
    slug: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
    _=Depends(require_csrf),
):
    """Delete a page."""
    from ..main import storage, audit_logger

    page = storage.get(f"pages.{slug}")
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Don't allow deleting system pages
    if slug in ("home", "404"):
        raise HTTPException(status_code=400, detail="Cannot delete system page")

    storage.delete(f"pages.{slug}")

    audit_logger.log(
        "page_delete",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        details={"slug": slug},
    )

    return {"status": "deleted", "slug": slug}


# ============================================================================
# Blocks API
# ============================================================================

@router.get("/api/blocks")
async def list_blocks(
    session=Depends(require_auth()),
):
    """List all blocks."""
    from ..main import storage

    blocks = storage.get("blocks", {})
    return {"blocks": blocks}


@router.put("/api/blocks/{name}")
async def update_block(
    name: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Update a block with language-specific content."""
    from ..main import storage, audit_logger

    data = await request.json()

    # Get existing block to preserve enabled state if not provided
    existing_block = storage.get(f"blocks.{name}", {})

    # Support both old format (single content) and new format (per-language content)
    if "fa" in data or "en" in data:
        # New format with language-specific content
        block = {}
        if "fa" in data:
            block["fa"] = {
                "content": data["fa"].get("content", "") if isinstance(data["fa"], dict) else "",
                "content_format": "html",
            }
        if "en" in data:
            block["en"] = {
                "content": data["en"].get("content", "") if isinstance(data["en"], dict) else "",
                "content_format": "html",
            }
        # Handle enabled state - default to True if not specified
        if "enabled" in data:
            block["enabled"] = bool(data["enabled"])
        else:
            block["enabled"] = existing_block.get("enabled", True)
    else:
        # Old format - single content for all languages
        block = {
            "content": data.get("content", ""),
            "content_format": "html",
            "enabled": data.get("enabled", existing_block.get("enabled", True)),
        }

    storage.set(f"blocks.{name}", block)

    audit_logger.log(
        "block_update",
        session.user_id,
        request.client.host if request.client else None,
        details={"name": name},
    )

    return block


# ============================================================================
# Upload API (Secure)
# ============================================================================

def validate_file_magic_bytes(content: bytes, extension: str) -> bool:
    """Validate file content matches expected magic bytes where applicable."""
    expected = MAGIC_BYTES.get(extension.lower())
    if not expected:
        # No magic bytes defined (e.g., txt) - allow
        return True

    if extension.lower() == "webp":
        # WebP has RIFF header at start and WEBP at offset 8
        return content[:4] == b"RIFF" and content[8:12] == b"WEBP"

    return content.startswith(expected)


@router.get("/api/uploads")
async def list_uploads(
    session=Depends(require_auth()),
):
    """List all uploads."""
    from ..main import storage

    uploads = storage.get("uploads", {})
    return {"uploads": uploads}


@router.post("/api/uploads")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
):
    """Upload a file."""
    import io
    import mimetypes

    from ..main import storage, app_config, audit_logger, sanitizer

    # Check Content-Length header before reading (DoS prevention)
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum: {MAX_UPLOAD_SIZE // (1024*1024)}MB"
                )
        except ValueError:
            pass  # Invalid Content-Length, continue and check actual size

    # Verify CSRF from header
    csrf_header = request.headers.get("X-CSRF-Token", "")
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_header or not secrets.compare_digest(csrf_header, csrf_cookie):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Sanitize filename FIRST before any other operations
    filename = sanitizer.sanitize_filename(file.filename)
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Check extension AFTER sanitization
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read content (with size limit)
    content = await file.read()

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum: {MAX_UPLOAD_SIZE // (1024*1024)}MB",
        )

    # Validate magic bytes when applicable
    if not validate_file_magic_bytes(content, extension):
        raise HTTPException(
            status_code=400,
            detail="File content does not match extension",
        )

    # Re-encode images to strip any hidden payloads
    if extension in IMAGE_EXTENSIONS:
        from PIL import Image

        try:
            img = Image.open(io.BytesIO(content))

            # Preserve ICC color profile if present
            icc_profile = img.info.get('icc_profile')

            # Strip EXIF and other metadata by creating a new image
            if img.mode in ('RGBA', 'LA', 'P'):
                # Handle images with alpha channel or palette
                clean_img = Image.new(img.mode, img.size)
                clean_img.putdata(list(img.getdata()))
            else:
                # For RGB/L modes
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
            }.get(extension, "PNG")

            # Prepare save options
            save_kwargs = {"format": pil_format}

            # Preserve ICC profile for color accuracy
            if icc_profile:
                save_kwargs["icc_profile"] = icc_profile

            # Use quality setting for JPEG/WEBP
            if pil_format in ("JPEG", "WEBP"):
                save_kwargs["quality"] = 90

            clean_img.save(output, **save_kwargs)
            content = output.getvalue()

        except Image.UnidentifiedImageError:
            raise HTTPException(
                status_code=400,
                detail="Cannot identify image file",
            )
        except IOError:
            raise HTTPException(
                status_code=400,
                detail="Error processing image file",
            )
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid image file",
            )

    # Generate UUID filename
    file_uuid = str(uuid.uuid4())
    safe_filename = f"{file_uuid}.{extension}"

    # Save file
    uploads_dir = app_config.uploads_dir
    uploads_dir.mkdir(parents=True, exist_ok=True)

    file_path = uploads_dir / safe_filename
    with open(file_path, "wb") as f:
        f.write(content)

    # Record in database
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    upload_record = {
        "uuid": file_uuid,
        "original_name": filename,
        "mime_type": mime_type,
        "size": len(content),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "uploaded_by": session.user_id,
    }

    storage.set(f"uploads.{file_uuid}", upload_record)

    audit_logger.log(
        "upload",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        details={"uuid": file_uuid, "original_name": filename},
    )

    return {
        "uuid": file_uuid,
        "url": f"/uploads/{file_uuid}",
        "original_name": filename,
        "size": len(content),
    }


@router.put("/api/uploads/{file_uuid}")
async def update_upload(
    file_uuid: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Update upload metadata."""
    from ..main import storage, audit_logger

    upload = storage.get(f"uploads.{file_uuid}")
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    data = await request.json()
    new_name = str(data.get("original_name", "")).strip()
    if new_name:
        upload["original_name"] = new_name
    storage.set(f"uploads.{file_uuid}", upload)

    audit_logger.log(
        "upload_update",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        details={"uuid": file_uuid},
    )

    return upload


@router.delete("/api/uploads/{file_uuid}")
async def delete_upload(
    file_uuid: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
    _=Depends(require_csrf),
):
    """Delete an uploaded file."""
    from ..main import storage, app_config, audit_logger

    upload = storage.get(f"uploads.{file_uuid}")
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Delete file
    extension = upload.get("mime_type", "").split("/")[-1]
    file_path = app_config.uploads_dir / f"{file_uuid}.{extension}"

    if file_path.exists():
        file_path.unlink()

    # Remove from database
    storage.delete(f"uploads.{file_uuid}")

    audit_logger.log(
        "upload_delete",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        details={"uuid": file_uuid},
    )

    return {"status": "deleted", "uuid": file_uuid}


# ============================================================================
# Settings API
# ============================================================================

@router.get("/api/settings")
async def get_settings(
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
):
    """Get site settings."""
    from ..main import storage

    config = storage.get("config", {})

    # Don't expose sensitive data
    return {
        "site_title": config.get("site_title", ""),
        "site_lang": config.get("site_lang", "en"),
        "theme": config.get("theme", "default"),
        "default_page": config.get("default_page", "home"),
        "force_https": config.get("force_https", True),
        "login_slug": config.get("login_slug", ""),
        "enable_search": config.get("enable_search", True),
        "search_in_pages": config.get("search_in_pages", True),
        "search_in_blog": config.get("search_in_blog", True),
        "search_min_chars": config.get("search_min_chars", 2),
        "search_max_results": config.get("search_max_results", 20),
        "maintenance_mode": config.get("maintenance_mode", False),
        "maintenance_message": config.get("maintenance_message", ""),
        "require_login": config.get("require_login", False),
        "allow_registration": config.get("allow_registration", True),
    }


@router.put("/api/settings")
async def update_settings(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
    _=Depends(require_csrf),
):
    """Update site settings."""
    from ..main import storage, audit_logger, theme_manager

    data = await request.json()

    # Update allowed settings only
    allowed_keys = {
        "site_title", "site_lang", "admin_lang", "theme", "default_page", "force_https",
        "login_slug",
        "enable_search", "search_in_pages", "search_in_blog", "search_min_chars", "search_max_results",
        "enable_jump_to_top",
        "maintenance_mode", "maintenance_message", "require_login", "allow_registration"
    }

    if "theme" in data and theme_manager:
        themes = theme_manager.list_themes()
        if not any(t.name == data["theme"] for t in themes):
            raise HTTPException(status_code=400, detail="Theme not found")

    # If login_slug is empty, generate a random one for security
    if "login_slug" in data and not data["login_slug"].strip():
        import secrets as _secrets
        data["login_slug"] = _secrets.token_urlsafe(24)

    for key, value in data.items():
        if key in allowed_keys:
            storage.set(f"config.{key}", value)

    if "theme" in data and theme_manager:
        theme_manager.set_active_theme(data["theme"])

    audit_logger.log(
        "settings_update",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        details={"keys": list(data.keys())},
    )

    return await get_settings(session)


# ============================================================================
# Copyright API
# ============================================================================

@router.get("/api/copyright")
async def get_copyright(
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
):
    """Get copyright text."""
    from ..main import storage

    config = storage.get("config", {})
    return {
        "copyright_text": config.get("copyright_text", "Copyright 2026 ChelCheleh v0.1.0 — Designed by Ahmad Batebi"),
    }


@router.put("/api/copyright")
async def update_copyright(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
    _=Depends(require_csrf),
):
    """Update copyright text."""
    from ..main import storage, audit_logger

    data = await request.json()

    copyright_text = data.get("copyright_text", "").strip()
    if not copyright_text:
        raise HTTPException(status_code=400, detail="Copyright text cannot be empty")

    storage.set("config.copyright_text", copyright_text)

    audit_logger.log(
        "copyright_update",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        details={"copyright_text": copyright_text[:100]},
    )

    return {"copyright_text": copyright_text}


# ============================================================================
# Plugins API
# ============================================================================

@router.get("/api/plugins")
async def list_plugins(
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
):
    """List all plugins."""
    from ..main import plugin_manager

    plugins = plugin_manager.discover_plugins()
    return {
        "plugins": [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "author": p.author,
                "enabled": p.enabled,
                "directory": p.directory,
            }
            for p in plugins
        ]
    }


@router.post("/api/plugins/{name}/enable")
async def enable_plugin(
    name: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
    _=Depends(require_csrf),
):
    """Enable a plugin."""
    from ..main import plugin_manager, storage, audit_logger

    try:
        plugin_manager.enable_plugin(name)

        # Update disabled list in storage
        disabled = set(storage.get("config.disabled_plugins", []))
        disabled.discard(name)
        storage.set("config.disabled_plugins", list(disabled))

        audit_logger.log(
            "plugin_enable",
            session.user_id,
            request.client.host if request.client else None,
            details={"plugin": name},
        )

        return {"status": "enabled", "plugin": name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/plugins/{name}/disable")
async def disable_plugin(
    name: str,
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
    _=Depends(require_csrf),
):
    """Disable a plugin."""
    from ..main import plugin_manager, storage, audit_logger

    plugin_manager.disable_plugin(name)

    # Update disabled list in storage
    disabled = set(storage.get("config.disabled_plugins", []))
    disabled.add(name)
    storage.set("config.disabled_plugins", list(disabled))

    audit_logger.log(
        "plugin_disable",
        session.user_id,
        request.client.host if request.client else None,
        details={"plugin": name},
    )

    return {"status": "disabled", "plugin": name}


# ============================================================================
# Themes API
# ============================================================================

@router.get("/api/themes")
async def list_themes(
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
):
    """List all themes."""
    from ..main import theme_manager, storage

    themes = theme_manager.list_themes()
    active = storage.get("config.theme", "default")

    return {
        "themes": [
            {
                "name": t.name,
                "version": t.version,
                "description": t.description,
                "author": t.author,
                "active": t.name == active,
            }
            for t in themes
        ],
        "active": active,
    }


@router.put("/api/themes/active")
async def set_active_theme(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
    _=Depends(require_csrf),
):
    """Set active theme."""
    from ..main import theme_manager, storage, audit_logger

    data = await request.json()
    theme_name = data.get("theme")

    if not theme_name:
        raise HTTPException(status_code=400, detail="Theme name required")

    # Check theme exists
    themes = theme_manager.list_themes()
    if not any(t.name == theme_name for t in themes):
        raise HTTPException(status_code=404, detail="Theme not found")

    storage.set("config.theme", theme_name)
    theme_manager.set_active_theme(theme_name)

    audit_logger.log(
        "theme_change",
        session.user_id,
        request.client.host if request.client else None,
        details={"theme": theme_name},
    )

    return {"status": "changed", "theme": theme_name}


# ============================================================================
# Backup API
# ============================================================================

@router.post("/api/backup")
async def create_backup(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
    _=Depends(require_csrf),
):
    """Create a backup."""
    import zipfile
    from ..main import app_config, audit_logger

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_name = f"pressassist_backup_{timestamp}.zip"
    backup_path = app_config.backups_dir / backup_name

    app_config.backups_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add database
        zf.write(app_config.db_path, "db.json")

        # Add uploads
        if app_config.uploads_dir.exists():
            for file in app_config.uploads_dir.iterdir():
                if file.is_file():
                    zf.write(file, f"uploads/{file.name}")

    audit_logger.log(
        "backup_create",
        session.user_id,
        request.client.host if request.client else None,
        details={"file": backup_name},
    )

    return {"status": "created", "file": backup_name}


@router.get("/api/backups")
async def list_backups(
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
):
    """List all backups."""
    from ..main import app_config

    backups = []
    if app_config.backups_dir.exists():
        for f in sorted(app_config.backups_dir.iterdir(), reverse=True):
            if f.suffix == ".zip":
                backups.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "created": f.stat().st_mtime,
                })

    return {"backups": backups}


# ============================================================================
# Audit Log API
# ============================================================================

@router.get("/api/audit-log")
async def get_audit_log(
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
    limit: int = 100,
):
    """Get recent audit log entries."""
    from ..main import audit_logger

    entries = audit_logger.get_recent(limit)
    return {"entries": entries}


# ============================================================================
# Updates API
# ============================================================================

@router.get("/api/updates/check")
async def check_updates(
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
):
    """Check for available updates from GitHub."""
    from ..main import storage
    from ..core.updater import check_for_updates

    current_commit = storage.get("config.update_commit")
    result = await check_for_updates(current_commit)
    return result


@router.post("/api/updates/apply")
async def apply_update(
    request: Request,
    session=Depends(require_auth([Role.SUPER_ADMIN, Role.ADMIN])),
    _=Depends(require_csrf),
):
    """Download and apply the latest update from GitHub."""
    import zipfile
    from ..main import app_config, storage, audit_logger
    from ..core.updater import download_and_apply_update

    def create_backup() -> str:
        """Create a backup before updating."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"pre_update_backup_{timestamp}.zip"
        backup_path = app_config.backups_dir / backup_name

        app_config.backups_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add database
            if app_config.db_path.exists():
                zf.write(app_config.db_path, "db.json")

            # Add uploads
            if app_config.uploads_dir.exists():
                for file in app_config.uploads_dir.iterdir():
                    if file.is_file():
                        zf.write(file, f"uploads/{file.name}")

        return str(backup_path)

    # Get base path (project root)
    base_path = Path(__file__).parent.parent.parent

    result = await download_and_apply_update(base_path, create_backup)

    if result["success"]:
        # Save new commit hash
        storage.set("config.update_commit", result["new_commit"])

        # Log the update
        audit_logger.log(
            "system_update",
            session.user_id,
            request.client.host if request.client else None,
            request.headers.get("user-agent", ""),
            details={
                "new_commit": result["new_commit"],
                "backup_path": result["backup_path"],
            },
        )

    return result
