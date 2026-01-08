"""Admin user management routes for ChelCheleh."""

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from ..core.auth import AuthManager
from ..core.i18n import i18n, t
from ..core.models import ProfileVisibility, Role, User

router = APIRouter(prefix="/users", tags=["admin-users"])


def get_verification_badge_svg(role: Role, is_verified: bool, verification_requested: bool, lang: str = "en") -> str:
    """Get SVG badge based on role and verification status.

    Args:
        role: User's role.
        is_verified: Whether user is verified.
        verification_requested: Whether verification is pending.
        lang: Language for tooltip text.

    Returns:
        SVG string for the badge wrapped in a span with tooltip.
    """
    # Get tooltip texts based on language
    super_admin_tooltip = i18n.get("profile.super_admin_badge", lang)
    admin_tooltip = i18n.get("profile.admin_badge", lang)
    verified_tooltip = i18n.get("profile.verified_identity", lang)
    pending_tooltip = i18n.get("profile.verification_pending", lang)
    not_verified_tooltip = i18n.get("profile.not_verified", lang)

    # Super Admin - Gold badge
    if role == Role.SUPER_ADMIN:
        svg = '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" fill="#FFD700"/>
            <path d="M9 12l2 2 4-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>'''
        return f'<span title="{super_admin_tooltip}" style="display:inline-flex;cursor:help;">{svg}</span>'

    # Admin - Silver badge
    if role == Role.ADMIN:
        svg = '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" fill="#C0C0C0"/>
            <path d="M9 12l2 2 4-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>'''
        return f'<span title="{admin_tooltip}" style="display:inline-flex;cursor:help;">{svg}</span>'

    # Verified user - Blue badge (like Twitter)
    if is_verified:
        svg = '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" fill="#1DA1F2"/>
            <path d="M9 12l2 2 4-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>'''
        return f'<span title="{verified_tooltip}" style="display:inline-flex;cursor:help;">{svg}</span>'

    # Verification pending - Red/Orange badge
    if verification_requested:
        svg = '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" fill="#EF4444"/>
            <path d="M12 8v4M12 16h.01" stroke="white" stroke-width="2" stroke-linecap="round"/>
        </svg>'''
        return f'<span title="{pending_tooltip}" style="display:inline-flex;cursor:help;">{svg}</span>'

    # Unverified - Gray badge (clickable)
    svg = '''<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="cursor:pointer;opacity:0.5;">
        <circle cx="12" cy="12" r="10" fill="#9CA3AF"/>
        <path d="M9 12l2 2 4-4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''
    return f'<span title="{not_verified_tooltip}" style="display:inline-flex;cursor:pointer;opacity:0.5;">{svg}</span>'


def get_role_display_name(role: Role, lang: str = "en") -> str:
    """Get human-readable role name."""
    names = {
        Role.SUPER_ADMIN: {"en": "Super Admin", "fa": "مدیر ارشد"},
        Role.ADMIN: {"en": "Admin", "fa": "مدیر"},
        Role.EDITOR: {"en": "Editor", "fa": "ویرایشگر"},
        Role.USER: {"en": "User", "fa": "کاربر"},
    }
    return names.get(role, {}).get(lang, str(role.value))


def get_role_badge_color(role: Role) -> str:
    """Get CSS color for role badge."""
    colors = {
        Role.SUPER_ADMIN: "#FFD700",  # Gold
        Role.ADMIN: "#C0C0C0",  # Silver
        Role.EDITOR: "#10B981",  # Green
        Role.USER: "#6B7280",  # Gray
    }
    return colors.get(role, "#6B7280")


# Import shared functions from routes.py
def _get_common_imports():
    """Lazy import to avoid circular imports."""
    from .routes import (
        get_admin_footer,
        get_admin_header_right,
        get_admin_html_attrs,
        get_admin_lang_context,
        get_admin_language_switcher_html,
        get_admin_nav,
        get_admin_rtl_styles,
        get_admin_common_css,
        get_csrf_token,
        require_auth,
        require_csrf,
        set_csrf_cookie,
    )
    from ..main import auth, storage

    return {
        "get_admin_footer": get_admin_footer,
        "get_admin_header_right": get_admin_header_right,
        "get_admin_html_attrs": get_admin_html_attrs,
        "get_admin_lang_context": get_admin_lang_context,
        "get_admin_language_switcher_html": get_admin_language_switcher_html,
        "get_admin_nav": get_admin_nav,
        "get_admin_rtl_styles": get_admin_rtl_styles,
        "get_admin_common_css": get_admin_common_css,
        "get_csrf_token": get_csrf_token,
        "require_auth": require_auth,
        "require_csrf": require_csrf,
        "set_csrf_cookie": set_csrf_cookie,
        "auth": auth,
        "storage": storage,
    }


def require_user_management():
    """Dependency to require user management permission."""
    async def check_permission(request: Request):
        imports = _get_common_imports()
        auth = imports["auth"]
        require_auth = imports["require_auth"]

        session = await require_auth()(request)

        if not auth.check_permission(session.role, "manage_users"):
            raise HTTPException(status_code=403, detail="No permission to manage users")

        return session

    return check_permission


# ============================================================================
# User List
# ============================================================================

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def list_users(
    request: Request,
    role_filter: str | None = None,
    search: str | None = None,
    page: int = 1,
):
    """List all users with filtering and pagination."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]
    get_admin_lang_context = imports["get_admin_lang_context"]
    get_admin_html_attrs = imports["get_admin_html_attrs"]
    get_admin_language_switcher_html = imports["get_admin_language_switcher_html"]
    get_admin_rtl_styles = imports["get_admin_rtl_styles"]
    get_admin_common_css = imports["get_admin_common_css"]
    get_admin_nav = imports["get_admin_nav"]
    get_admin_header_right = imports["get_admin_header_right"]
    get_admin_footer = imports["get_admin_footer"]
    get_csrf_token = imports["get_csrf_token"]
    set_csrf_cookie = imports["set_csrf_cookie"]
    require_auth = imports["require_auth"]

    # Check authentication
    session = await require_auth()(request)
    if not auth.check_permission(session.role, "manage_users"):
        raise HTTPException(status_code=403, detail="No permission to manage users")

    # Get language context
    lang_ctx = get_admin_lang_context(request)
    html_attrs = get_admin_html_attrs(request)
    lang_switcher = get_admin_language_switcher_html(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""
    lang = lang_ctx["lang"]

    # Get all users
    users_data = storage.get("users", {})
    users_list = []

    for username, user_data in users_data.items():
        # Handle old format without new fields
        user = {
            "username": username,
            "email": user_data.get("email", ""),
            "display_name": user_data.get("display_name", username),
            "role": user_data.get("role", "user"),
            "is_verified": user_data.get("is_verified", False),
            "verification_requested_at": user_data.get("verification_requested_at"),
            "is_active": user_data.get("is_active", True),
            "avatar_uuid": user_data.get("avatar_uuid"),
            "created_at": user_data.get("created_at", ""),
            "last_login": user_data.get("last_login"),
        }
        users_list.append(user)

    # Filter by role
    if role_filter and role_filter != "all":
        users_list = [u for u in users_list if u["role"] == role_filter]

    # Search
    if search:
        search_lower = search.lower()
        users_list = [
            u for u in users_list
            if search_lower in u["username"].lower()
            or search_lower in (u.get("email") or "").lower()
            or search_lower in (u.get("display_name") or "").lower()
        ]

    # Sort by created_at descending
    users_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # Pagination
    per_page = 20
    total_users = len(users_list)
    total_pages = max(1, (total_users + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    users_list = users_list[start_idx:start_idx + per_page]

    # Count pending verifications
    pending_count = sum(
        1 for u in storage.get("users", {}).values()
        if u.get("verification_requested_at") and not u.get("is_verified")
    )

    token, needs_cookie = get_csrf_token(request)

    # Build user rows
    user_rows = ""
    for user in users_list:
        role_enum = Role(user["role"]) if user["role"] in [r.value for r in Role] else Role.USER
        verification_requested = user.get("verification_requested_at") is not None
        badge_svg = get_verification_badge_svg(role_enum, user["is_verified"], verification_requested, lang)
        role_color = get_role_badge_color(role_enum)
        role_name = get_role_display_name(role_enum, lang)

        # Avatar
        avatar_html = f'<img src="/uploads/{user["avatar_uuid"]}" alt="" class="user-avatar">' if user.get("avatar_uuid") else f'<div class="user-avatar-placeholder">{user["username"][0].upper()}</div>'

        # Status indicator
        status_class = "active" if user["is_active"] else "inactive"
        status_text = t("admin.users.active") if user["is_active"] else t("admin.users.inactive")

        # Actions based on permissions
        can_edit = AuthManager.can_manage_role(session.role, role_enum) or user["username"] == session.user_id
        can_delete = AuthManager.can_manage_role(session.role, role_enum) and role_enum != Role.SUPER_ADMIN and user["username"] != session.user_id

        actions = '<div class="action-btns">'
        if can_edit:
            actions += f'''<a href="/admin/users/edit/{user["username"]}" class="btn-icon edit" title="{t('common.edit')}">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
            </a>'''
        if can_delete:
            actions += f'''<a href="/admin/users/delete/{user["username"]}" onclick="return confirm('{t("admin.users.delete_confirm")}')" class="btn-icon delete" title="{t('common.delete')}">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
            </a>'''

        # Verification action
        if verification_requested and not user["is_verified"] and AuthManager.is_admin_or_above(session.role):
            actions += f'''<form method="POST" action="/admin/users/verify/{user["username"]}" style="display:inline;">
                <input type="hidden" name="csrf_token" value="{token}">
                <button type="submit" class="btn-icon verify" title="{t('admin.users.approve')}">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                        <polyline points="22 4 12 14.01 9 11.01"/>
                    </svg>
                </button>
            </form>'''
        actions += '</div>'

        user_rows += f'''
        <tr>
            <td>{avatar_html}</td>
            <td>
                <div class="user-info">
                    <div style="display:flex;align-items:center;gap:0.5rem;">
                        <span style="font-weight:500;">{user["display_name"] or user["username"]}</span>
                        {badge_svg}
                    </div>
                    <div class="username">@{user["username"]}</div>
                </div>
            </td>
            <td style="color:#64748b;">{user.get("email") or "-"}</td>
            <td>
                <span class="role-badge" style="--role-color:{role_color};">{role_name}</span>
            </td>
            <td>
                <span class="status-dot {status_class}" title="{status_text}"></span>
            </td>
            <td>{actions}</td>
        </tr>
        '''

    # Pagination HTML
    pagination_html = ""
    if total_pages > 1:
        pagination_html = '<div class="pagination">'
        for p in range(1, total_pages + 1):
            active_class = "active" if p == page else ""
            pagination_html += f'<a href="?page={p}&role_filter={role_filter or ""}&search={search or ""}" class="page-link {active_class}">{p}</a>'
        pagination_html += '</div>'

    empty_state = f'''
    <tr>
        <td colspan="6">
            <div class="empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="1.5">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                    <circle cx="9" cy="7" r="4"/>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
                <p style="margin:0.5rem 0;color:#64748b;">{t('admin.users.no_users')}</p>
                <a href="/admin/users/new" class="btn btn-primary" style="margin-top:0.5rem;">{t('admin.users.add')}</a>
            </div>
        </td>
    </tr>
    '''

    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.users.title')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        {get_admin_common_css()}
        <style>
            .page-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1.5rem;
                flex-wrap: wrap;
                gap: 1rem;
            }}
            .pending-badge {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                background: #ef4444;
                color: white;
                min-width: 20px;
                height: 20px;
                padding: 0 6px;
                border-radius: 10px;
                font-size: 0.75rem;
                font-weight: 600;
                margin-inline-start: 0.5rem;
            }}
            .filter-bar {{
                display: flex;
                gap: 0.75rem;
                margin-bottom: 1rem;
                flex-wrap: wrap;
                align-items: center;
            }}
            .filter-bar select, .filter-bar input {{
                padding: 0.5rem 0.75rem;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                font-size: 0.875rem;
                background: white;
            }}
            .filter-bar select:focus, .filter-bar input:focus {{
                outline: none;
                border-color: #7c3aed;
                box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
            }}
            .filter-bar input {{
                min-width: 220px;
            }}
            .user-avatar {{
                width: 44px;
                height: 44px;
                border-radius: 50%;
                object-fit: cover;
            }}
            .user-avatar-placeholder {{
                width: 44px;
                height: 44px;
                border-radius: 50%;
                background: linear-gradient(135deg, #7c3aed, #a855f7);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: 600;
                font-size: 1rem;
            }}
            .user-info {{
                display: flex;
                flex-direction: column;
                gap: 0.125rem;
            }}
            .username {{
                font-size: 0.8rem;
                color: #64748b;
            }}
            .role-badge {{
                display: inline-block;
                background: color-mix(in srgb, var(--role-color) 15%, white);
                color: var(--role-color);
                padding: 0.25rem 0.75rem;
                border-radius: 9999px;
                font-size: 0.75rem;
                font-weight: 500;
            }}
            .status-dot {{
                width: 10px;
                height: 10px;
                border-radius: 50%;
                display: inline-block;
            }}
            .status-dot.active {{
                background: #10B981;
                box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
            }}
            .status-dot.inactive {{
                background: #EF4444;
                box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.2);
            }}
            .action-btns {{
                display: flex;
                gap: 0.5rem;
            }}
            .btn-icon {{
                width: 32px;
                height: 32px;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: none;
                cursor: pointer;
                transition: all 0.2s;
                text-decoration: none;
            }}
            .btn-icon.edit {{
                background: #ede9fe;
                color: #7c3aed;
            }}
            .btn-icon.edit:hover {{
                background: #7c3aed;
                color: white;
            }}
            .btn-icon.delete {{
                background: #fee2e2;
                color: #dc2626;
            }}
            .btn-icon.delete:hover {{
                background: #dc2626;
                color: white;
            }}
            .btn-icon.verify {{
                background: #d1fae5;
                color: #059669;
            }}
            .btn-icon.verify:hover {{
                background: #059669;
                color: white;
            }}
            .pagination {{
                display: flex;
                gap: 0.5rem;
                justify-content: center;
                margin-top: 1.5rem;
            }}
            .page-link {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-width: 36px;
                height: 36px;
                padding: 0 0.75rem;
                border-radius: 6px;
                text-decoration: none;
                color: #475569;
                font-weight: 500;
                background: white;
                border: 1px solid #e2e8f0;
                transition: all 0.2s;
            }}
            .page-link:hover {{
                border-color: #7c3aed;
                color: #7c3aed;
            }}
            .page-link.active {{
                background: #7c3aed;
                color: white;
                border-color: #7c3aed;
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
            <div class="page-header">
                <h1 class="page-title" style="margin:0;">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                        <circle cx="9" cy="7" r="4"/>
                        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                    </svg>
                    {t('admin.users.title')}
                    {f'<span class="pending-badge">{pending_count}</span>' if pending_count > 0 else ''}
                </h1>
                <a href="/admin/users/new" class="btn btn-primary">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-inline-end:0.5rem;">
                        <line x1="12" y1="5" x2="12" y2="19"/>
                        <line x1="5" y1="12" x2="19" y2="12"/>
                    </svg>
                    {t('admin.users.add')}
                </a>
            </div>

            <div class="card card-static">
                <div class="card-header info">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="11" cy="11" r="8"/>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    </svg>
                    {t('admin.search')}
                </div>
                <div class="card-body">
                    <form class="filter-bar" method="GET">
                        <select name="role_filter" onchange="this.form.submit()">
                            <option value="all">{t('admin.users.all_roles')}</option>
                            <option value="super_admin" {"selected" if role_filter == "super_admin" else ""}>{get_role_display_name(Role.SUPER_ADMIN, lang)}</option>
                            <option value="admin" {"selected" if role_filter == "admin" else ""}>{get_role_display_name(Role.ADMIN, lang)}</option>
                            <option value="editor" {"selected" if role_filter == "editor" else ""}>{get_role_display_name(Role.EDITOR, lang)}</option>
                            <option value="user" {"selected" if role_filter == "user" else ""}>{get_role_display_name(Role.USER, lang)}</option>
                        </select>
                        <input type="text" name="search" placeholder="{t('admin.users.search_placeholder')}" value="{search or ""}">
                        <button type="submit" class="btn btn-primary">{t('admin.search')}</button>
                    </form>
                </div>
            </div>

            <div class="card card-static" style="margin-top:1rem;">
                <div class="card-header primary">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="8" y1="6" x2="21" y2="6"/>
                        <line x1="8" y1="12" x2="21" y2="12"/>
                        <line x1="8" y1="18" x2="21" y2="18"/>
                        <line x1="3" y1="6" x2="3.01" y2="6"/>
                        <line x1="3" y1="12" x2="3.01" y2="12"/>
                        <line x1="3" y1="18" x2="3.01" y2="18"/>
                    </svg>
                    {t('admin.users.list')}
                </div>
                <div class="card-body" style="padding:0;">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th style="width:60px;"></th>
                                <th>{t('admin.users.name')}</th>
                                <th>{t('admin.users.email')}</th>
                                <th>{t('admin.users.role')}</th>
                                <th style="width:80px;text-align:center;">{t('admin.users.status')}</th>
                                <th style="width:130px;">{t('common.actions')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            {user_rows if user_rows else empty_state}
                        </tbody>
                    </table>
                </div>
                {f'<div class="card-footer">{pagination_html}</div>' if pagination_html else ''}
            </div>
        </div>
        {get_admin_footer()}
    </body>
    </html>
    """

    response = HTMLResponse(content=html)
    if needs_cookie:
        set_csrf_cookie(request, response, token)
    return response


# ============================================================================
# Create User
# ============================================================================

@router.get("/new", response_class=HTMLResponse)
async def new_user_form(request: Request):
    """Render new user form."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]
    get_admin_lang_context = imports["get_admin_lang_context"]
    get_admin_html_attrs = imports["get_admin_html_attrs"]
    get_admin_language_switcher_html = imports["get_admin_language_switcher_html"]
    get_admin_rtl_styles = imports["get_admin_rtl_styles"]
    get_admin_nav = imports["get_admin_nav"]
    get_admin_header_right = imports["get_admin_header_right"]
    get_admin_footer = imports["get_admin_footer"]
    get_csrf_token = imports["get_csrf_token"]
    set_csrf_cookie = imports["set_csrf_cookie"]
    require_auth = imports["require_auth"]

    session = await require_auth()(request)
    if not auth.check_permission(session.role, "manage_users"):
        raise HTTPException(status_code=403, detail="No permission to manage users")

    lang_ctx = get_admin_lang_context(request)
    html_attrs = get_admin_html_attrs(request)
    lang_switcher = get_admin_language_switcher_html(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""
    lang = lang_ctx["lang"]

    token, needs_cookie = get_csrf_token(request)

    # Role options based on current user's role
    role_options = ""
    available_roles = [Role.USER, Role.EDITOR]
    if session.role == Role.ADMIN:
        pass  # Can only create users and editors
    elif session.role == Role.SUPER_ADMIN:
        available_roles.append(Role.ADMIN)

    for role in available_roles:
        role_options += f'<option value="{role.value}">{get_role_display_name(role, lang)}</option>'

    get_admin_common_css = imports["get_admin_common_css"]

    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.users.add')} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        {get_admin_common_css()}
        <style>
            .form-row {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1rem;
            }}
            @media (max-width: 640px) {{
                .form-row {{
                    grid-template-columns: 1fr;
                }}
            }}
            .required-star {{
                color: #ef4444;
                margin-inline-start: 0.25rem;
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
        <div class="container container-narrow">
            <div class="page-header">
                <h1 class="page-title">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                        <circle cx="8.5" cy="7" r="4"/>
                        <line x1="20" y1="8" x2="20" y2="14"/>
                        <line x1="23" y1="11" x2="17" y2="11"/>
                    </svg>
                    {t('admin.users.add')}
                </h1>
                <a href="/admin/users" class="btn btn-secondary">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="19" y1="12" x2="5" y2="12"/>
                        <polyline points="12 19 5 12 12 5"/>
                    </svg>
                    {t('admin.back')}
                </a>
            </div>

            <div class="card card-static">
                <div class="card-header success">
                    <div class="card-icon success">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                            <circle cx="8.5" cy="7" r="4"/>
                            <line x1="20" y1="8" x2="20" y2="14"/>
                            <line x1="23" y1="11" x2="17" y2="11"/>
                        </svg>
                    </div>
                    <h2 class="card-title">{t('admin.users.new_user')}</h2>
                </div>
                <div class="card-body">
                    <form method="POST" action="/admin/users/new">
                        <input type="hidden" name="csrf_token" value="{token}">

                        <div class="form-row">
                            <div class="form-group">
                                <label class="form-label" for="username">{t('admin.users.username')}<span class="required-star">*</span></label>
                                <input type="text" id="username" name="username" class="form-input" required pattern="[a-zA-Z0-9_]+" minlength="3" maxlength="50" placeholder="john_doe">
                                <small style="color:#64748b;font-size:0.8rem;margin-top:0.25rem;display:block;">{t('admin.users.username_hint')}</small>
                            </div>
                            <div class="form-group">
                                <label class="form-label" for="email">{t('admin.users.email')}</label>
                                <input type="email" id="email" name="email" class="form-input" placeholder="user@example.com">
                            </div>
                        </div>

                        <div class="form-row">
                            <div class="form-group">
                                <label class="form-label" for="password">{t('admin.users.password')}<span class="required-star">*</span></label>
                                <input type="password" id="password" name="password" class="form-input" required minlength="12">
                                <small style="color:#64748b;font-size:0.8rem;margin-top:0.25rem;display:block;">{t('admin.users.password_hint')}</small>
                            </div>
                            <div class="form-group">
                                <label class="form-label" for="password_confirm">{t('admin.users.password_confirm')}<span class="required-star">*</span></label>
                                <input type="password" id="password_confirm" name="password_confirm" class="form-input" required minlength="12">
                            </div>
                        </div>

                        <div class="form-row">
                            <div class="form-group">
                                <label class="form-label" for="display_name">{t('admin.users.display_name')}</label>
                                <input type="text" id="display_name" name="display_name" class="form-input" maxlength="100" placeholder="John Doe">
                            </div>
                            <div class="form-group">
                                <label class="form-label" for="phone">{t('admin.users.phone')}</label>
                                <input type="tel" id="phone" name="phone" class="form-input" placeholder="+1 234 567 8900">
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="role">{t('admin.users.role')}<span class="required-star">*</span></label>
                            <select id="role" name="role" class="form-select" required>
                                {role_options}
                            </select>
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="bio">{t('admin.users.bio')}</label>
                            <textarea id="bio" name="bio" class="form-textarea" maxlength="500" placeholder="{t('admin.users.bio')}..."></textarea>
                        </div>

                        <div class="form-group">
                            <label class="checkbox-row" style="cursor:pointer;">
                                <input type="checkbox" class="checkbox-input" id="is_active" name="is_active" checked>
                                <div class="checkbox-content">
                                    <p class="checkbox-label">{t('admin.users.is_active')}</p>
                                    <p class="checkbox-hint">{t('admin.users.is_active_hint')}</p>
                                </div>
                            </label>
                        </div>

                        <div style="display:flex;gap:1rem;margin-top:1.5rem;">
                            <button type="submit" class="btn btn-success">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                                    <circle cx="8.5" cy="7" r="4"/>
                                    <line x1="20" y1="8" x2="20" y2="14"/>
                                    <line x1="23" y1="11" x2="17" y2="11"/>
                                </svg>
                                {t('admin.users.add')}
                            </button>
                            <a href="/admin/users" class="btn btn-secondary">{t('admin.cancel')}</a>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        {get_admin_footer()}
    </body>
    </html>
    """

    response = HTMLResponse(content=html)
    if needs_cookie:
        set_csrf_cookie(request, response, token)
    return response


@router.post("/new")
async def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    email: str = Form(None),
    display_name: str = Form(None),
    phone: str = Form(None),
    role: str = Form(...),
    bio: str = Form(None),
    is_active: bool = Form(False),
    csrf_token: str = Form(...),
):
    """Create a new user."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]
    require_auth = imports["require_auth"]
    require_csrf = imports["require_csrf"]

    # Verify CSRF
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not secrets.compare_digest(csrf_token, csrf_cookie):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    session = await require_auth()(request)
    if not auth.check_permission(session.role, "manage_users"):
        raise HTTPException(status_code=403, detail="No permission to manage users")

    # Validate passwords match
    if password != password_confirm:
        raise HTTPException(status_code=400, detail=t("admin.users.passwords_mismatch"))

    # Validate password length
    if len(password) < 12:
        raise HTTPException(status_code=400, detail=t("admin.users.password_too_short"))

    # Check if username exists
    username_lower = username.lower()
    existing_users = storage.get("users", {})
    if username_lower in existing_users:
        raise HTTPException(status_code=400, detail=t("admin.users.username_exists"))

    # Validate role permissions
    try:
        role_enum = Role(role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

    if not AuthManager.can_manage_role(session.role, role_enum):
        raise HTTPException(status_code=403, detail="Cannot create user with this role")

    # Create user
    user_data = {
        "username": username_lower,
        "password_hash": auth.hash_password(password),
        "role": role,
        "email": email.strip().lower() if email else None,
        "display_name": display_name.strip() if display_name else None,
        "phone": phone.strip() if phone else None,
        "bio": bio.strip() if bio else None,
        "avatar_uuid": None,
        "cover_image_uuid": None,
        "is_verified": False,
        "verification_requested_at": None,
        "verified_at": None,
        "verified_by": None,
        "is_active": is_active,
        "profile_visibility": "public",
        "reset_token": None,
        "reset_token_expires": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": None,
    }

    storage.set(f"users.{username_lower}", user_data)

    return RedirectResponse(url="/admin/users", status_code=303)


# ============================================================================
# Edit User
# ============================================================================

@router.get("/edit/{username}", response_class=HTMLResponse)
async def edit_user_form(request: Request, username: str):
    """Render edit user form."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]
    get_admin_lang_context = imports["get_admin_lang_context"]
    get_admin_html_attrs = imports["get_admin_html_attrs"]
    get_admin_language_switcher_html = imports["get_admin_language_switcher_html"]
    get_admin_rtl_styles = imports["get_admin_rtl_styles"]
    get_admin_nav = imports["get_admin_nav"]
    get_admin_header_right = imports["get_admin_header_right"]
    get_admin_footer = imports["get_admin_footer"]
    get_csrf_token = imports["get_csrf_token"]
    set_csrf_cookie = imports["set_csrf_cookie"]
    require_auth = imports["require_auth"]

    get_admin_common_css = imports["get_admin_common_css"]

    session = await require_auth()(request)

    # Get user data
    user_data = storage.get(f"users.{username}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    user_role = Role(user_data.get("role", "user"))

    # Check permissions
    can_edit = AuthManager.can_manage_role(session.role, user_role) or username == session.user_id
    if not can_edit:
        raise HTTPException(status_code=403, detail="No permission to edit this user")

    lang_ctx = get_admin_lang_context(request)
    html_attrs = get_admin_html_attrs(request)
    lang_switcher = get_admin_language_switcher_html(request)
    rtl_styles = get_admin_rtl_styles() if lang_ctx["is_rtl"] else ""
    lang = lang_ctx["lang"]

    token, needs_cookie = get_csrf_token(request)

    # Role options
    role_options = ""
    can_change_role = AuthManager.can_manage_role(session.role, user_role) and username != session.user_id

    if can_change_role:
        available_roles = [Role.USER, Role.EDITOR]
        if session.role == Role.SUPER_ADMIN:
            available_roles.append(Role.ADMIN)
            if user_role == Role.SUPER_ADMIN:
                available_roles.append(Role.SUPER_ADMIN)

        for role in available_roles:
            selected = "selected" if role.value == user_data.get("role") else ""
            role_options += f'<option value="{role.value}" {selected}>{get_role_display_name(role, lang)}</option>'
    else:
        role_options = f'<option value="{user_data.get("role")}" selected>{get_role_display_name(user_role, lang)}</option>'

    # Avatar preview
    avatar_html = ""
    if user_data.get("avatar_uuid"):
        avatar_html = f'<img src="/uploads/{user_data["avatar_uuid"]}" style="width:100px;height:100px;border-radius:50%;object-fit:cover;margin-bottom:1rem;">'

    # Verification status
    verification_section = ""
    if AuthManager.is_admin_or_above(session.role) and username != session.user_id:
        is_verified = user_data.get("is_verified", False)
        verification_requested = user_data.get("verification_requested_at") is not None

        if is_verified:
            verification_section = f'''
            <div class="form-group">
                <label>{t('admin.users.verification')}</label>
                <div style="display:flex;align-items:center;gap:0.5rem;">
                    {get_verification_badge_svg(user_role, True, False, lang)}
                    <span style="color:#10B981;">{t('admin.users.verified')}</span>
                    <form method="POST" action="/admin/users/unverify/{username}" style="display:inline;margin-left:1rem;">
                        <input type="hidden" name="csrf_token" value="{token}">
                        <button type="submit" style="background:#EF4444;color:white;border:none;padding:0.25rem 0.5rem;border-radius:4px;cursor:pointer;">{t('admin.users.revoke_verification')}</button>
                    </form>
                </div>
            </div>
            '''
        elif verification_requested:
            verification_section = f'''
            <div class="form-group">
                <label>{t('admin.users.verification')}</label>
                <div style="display:flex;align-items:center;gap:0.5rem;">
                    {get_verification_badge_svg(user_role, False, True, lang)}
                    <span style="color:#EF4444;">{t('admin.users.pending_verification')}</span>
                    <form method="POST" action="/admin/users/verify/{username}" style="display:inline;margin-left:1rem;">
                        <input type="hidden" name="csrf_token" value="{token}">
                        <button type="submit" style="background:#10B981;color:white;border:none;padding:0.25rem 0.5rem;border-radius:4px;cursor:pointer;">{t('admin.users.approve')}</button>
                    </form>
                </div>
            </div>
            '''

    # Avatar HTML for card
    avatar_card_html = ""
    if user_data.get("avatar_uuid"):
        avatar_card_html = f'''
        <div style="display:flex;align-items:center;gap:1rem;margin-bottom:1.5rem;padding:1rem;background:#f8fafc;border-radius:12px;">
            <img src="/uploads/{user_data["avatar_uuid"]}" class="avatar avatar-lg" style="width:80px;height:80px;">
            <div>
                <div style="font-weight:600;font-size:1.1rem;color:#1e293b;">{user_data.get("display_name") or username}</div>
                <div style="color:#64748b;font-size:0.9rem;">@{username}</div>
            </div>
        </div>
        '''
    else:
        avatar_card_html = f'''
        <div style="display:flex;align-items:center;gap:1rem;margin-bottom:1.5rem;padding:1rem;background:#f8fafc;border-radius:12px;">
            <div class="avatar avatar-lg avatar-placeholder" style="width:80px;height:80px;font-size:1.5rem;">{username[0].upper()}</div>
            <div>
                <div style="font-weight:600;font-size:1.1rem;color:#1e293b;">{user_data.get("display_name") or username}</div>
                <div style="color:#64748b;font-size:0.9rem;">@{username}</div>
            </div>
        </div>
        '''

    html = f"""
    <!DOCTYPE html>
    <html {html_attrs}>
    <head>
        <title>{t('admin.users.edit')} - {username} - {t('cms.name')}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        {get_admin_common_css()}
        <style>
            .form-row {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1rem;
            }}
            @media (max-width: 640px) {{
                .form-row {{
                    grid-template-columns: 1fr;
                }}
            }}
            .verification-badge {{
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.5rem 1rem;
                border-radius: 8px;
                font-size: 0.9rem;
                font-weight: 500;
            }}
            .verification-badge.verified {{
                background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
                color: #16a34a;
            }}
            .verification-badge.pending {{
                background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
                color: #dc2626;
            }}
            .verification-action {{
                margin-inline-start: 0.75rem;
            }}
            .verification-action button {{
                padding: 0.375rem 0.75rem;
                border-radius: 6px;
                font-size: 0.8rem;
                font-weight: 500;
                border: none;
                cursor: pointer;
                transition: all 0.2s;
            }}
            .verification-action .approve-btn {{
                background: #22c55e;
                color: white;
            }}
            .verification-action .approve-btn:hover {{
                background: #16a34a;
            }}
            .verification-action .revoke-btn {{
                background: #ef4444;
                color: white;
            }}
            .verification-action .revoke-btn:hover {{
                background: #dc2626;
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
        <div class="container container-narrow">
            <div class="page-header">
                <h1 class="page-title">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                    {t('admin.users.edit')}
                </h1>
                <a href="/admin/users" class="btn btn-secondary">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="19" y1="12" x2="5" y2="12"/>
                        <polyline points="12 19 5 12 12 5"/>
                    </svg>
                    {t('admin.back')}
                </a>
            </div>

            <div class="card card-static" style="margin-bottom:1.5rem;">
                <div class="card-header purple">
                    <div class="card-icon purple">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                            <circle cx="12" cy="7" r="4"/>
                        </svg>
                    </div>
                    <h2 class="card-title">{t('admin.users.edit_user')}</h2>
                </div>
                <div class="card-body">
                    {avatar_card_html}
                    <form method="POST" action="/admin/users/edit/{username}">
                        <input type="hidden" name="csrf_token" value="{token}">

                        <div class="form-row">
                            <div class="form-group">
                                <label class="form-label" for="username">{t('admin.users.username')}</label>
                                <input type="text" id="username" class="form-input" value="{username}" disabled style="background:#e2e8f0;color:#64748b;">
                                <small style="color:#64748b;font-size:0.8rem;margin-top:0.25rem;display:block;">{t('admin.users.username_cannot_change')}</small>
                            </div>
                            <div class="form-group">
                                <label class="form-label" for="email">{t('admin.users.email')}</label>
                                <input type="email" id="email" name="email" class="form-input" value="{user_data.get('email') or ''}">
                            </div>
                        </div>

                        <div class="form-row">
                            <div class="form-group">
                                <label class="form-label" for="display_name">{t('admin.users.display_name')}</label>
                                <input type="text" id="display_name" name="display_name" class="form-input" value="{user_data.get('display_name') or ''}" maxlength="100">
                            </div>
                            <div class="form-group">
                                <label class="form-label" for="phone">{t('admin.users.phone')}</label>
                                <input type="tel" id="phone" name="phone" class="form-input" value="{user_data.get('phone') or ''}">
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="role">{t('admin.users.role')}</label>
                            <select id="role" name="role" class="form-select" {"disabled" if not can_change_role else ""}>
                                {role_options}
                            </select>
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="bio">{t('admin.users.bio')}</label>
                            <textarea id="bio" name="bio" class="form-textarea" maxlength="500">{user_data.get('bio') or ''}</textarea>
                        </div>

                        {verification_section}

                        <div class="form-group">
                            <label class="checkbox-row" style="cursor:pointer;">
                                <input type="checkbox" class="checkbox-input" id="is_active" name="is_active" {"checked" if user_data.get("is_active", True) else ""}>
                                <div class="checkbox-content">
                                    <p class="checkbox-label">{t('admin.users.is_active')}</p>
                                    <p class="checkbox-hint">{t('admin.users.is_active_hint')}</p>
                                </div>
                            </label>
                        </div>

                        <div style="display:flex;gap:1rem;margin-top:1.5rem;">
                            <button type="submit" class="btn btn-primary">{t('admin.save')}</button>
                            <a href="/admin/users" class="btn btn-secondary">{t('admin.cancel')}</a>
                        </div>
                    </form>
                </div>
            </div>

            <div class="card card-static">
                <div class="card-header warning">
                    <div class="card-icon warning">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                        </svg>
                    </div>
                    <h2 class="card-title">{t('admin.users.change_password')}</h2>
                </div>
                <div class="card-body">
                    <form method="POST" action="/admin/users/edit/{username}/password">
                        <input type="hidden" name="csrf_token" value="{token}">
                        <div class="form-row">
                            <div class="form-group">
                                <label class="form-label" for="new_password">{t('admin.users.new_password')}</label>
                                <input type="password" id="new_password" name="new_password" class="form-input" minlength="12">
                            </div>
                            <div class="form-group">
                                <label class="form-label" for="new_password_confirm">{t('admin.users.password_confirm')}</label>
                                <input type="password" id="new_password_confirm" name="new_password_confirm" class="form-input" minlength="12">
                            </div>
                        </div>
                        <small style="color:#64748b;font-size:0.8rem;">{t('admin.users.password_hint')}</small>
                        <div style="margin-top:1.25rem;">
                            <button type="submit" class="btn btn-warning">{t('admin.users.update_password')}</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        {get_admin_footer()}
    </body>
    </html>
    """

    response = HTMLResponse(content=html)
    if needs_cookie:
        set_csrf_cookie(request, response, token)
    return response


@router.post("/edit/{username}")
async def update_user(
    request: Request,
    username: str,
    email: str = Form(None),
    display_name: str = Form(None),
    phone: str = Form(None),
    role: str = Form(None),
    bio: str = Form(None),
    is_active: bool = Form(False),
    csrf_token: str = Form(...),
):
    """Update user details."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]
    require_auth = imports["require_auth"]

    # Verify CSRF
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not secrets.compare_digest(csrf_token, csrf_cookie):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    session = await require_auth()(request)

    # Get existing user
    user_data = storage.get(f"users.{username}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    user_role = Role(user_data.get("role", "user"))

    # Check permissions
    can_edit = AuthManager.can_manage_role(session.role, user_role) or username == session.user_id
    if not can_edit:
        raise HTTPException(status_code=403, detail="No permission to edit this user")

    # Update fields
    if email is not None:
        user_data["email"] = email.strip().lower() if email else None
    if display_name is not None:
        user_data["display_name"] = display_name.strip() if display_name else None
    if phone is not None:
        user_data["phone"] = phone.strip() if phone else None
    if bio is not None:
        user_data["bio"] = bio.strip() if bio else None

    # Only update role if allowed
    if role and AuthManager.can_manage_role(session.role, user_role) and username != session.user_id:
        try:
            new_role = Role(role)
            if AuthManager.can_manage_role(session.role, new_role):
                user_data["role"] = role
        except ValueError:
            pass

    # Only update is_active if allowed
    if AuthManager.can_manage_role(session.role, user_role):
        user_data["is_active"] = is_active

    storage.set(f"users.{username}", user_data)

    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/edit/{username}/password")
async def update_user_password(
    request: Request,
    username: str,
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    csrf_token: str = Form(...),
):
    """Update user password."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]
    require_auth = imports["require_auth"]

    # Verify CSRF
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not secrets.compare_digest(csrf_token, csrf_cookie):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    session = await require_auth()(request)

    # Get existing user
    user_data = storage.get(f"users.{username}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    user_role = Role(user_data.get("role", "user"))

    # Check permissions
    can_edit = AuthManager.can_manage_role(session.role, user_role) or username == session.user_id
    if not can_edit:
        raise HTTPException(status_code=403, detail="No permission to edit this user")

    # Validate passwords
    if new_password != new_password_confirm:
        raise HTTPException(status_code=400, detail=t("admin.users.passwords_mismatch"))

    if len(new_password) < 12:
        raise HTTPException(status_code=400, detail=t("admin.users.password_too_short"))

    # Update password
    user_data["password_hash"] = auth.hash_password(new_password)
    storage.set(f"users.{username}", user_data)

    # Invalidate all sessions for this user (except current if self)
    if username != session.user_id:
        auth.invalidate_user_sessions(username)

    return RedirectResponse(url=f"/admin/users/edit/{username}", status_code=303)


# ============================================================================
# Delete User
# ============================================================================

@router.get("/delete/{username}")
async def delete_user(request: Request, username: str):
    """Delete a user."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]
    require_auth = imports["require_auth"]
    get_csrf_token = imports["get_csrf_token"]

    token, _ = get_csrf_token(request)

    # Verify CSRF from query param
    csrf_param = request.query_params.get("csrf_token", "")
    csrf_cookie = request.cookies.get("csrf_token", "")

    session = await require_auth()(request)

    # Get existing user
    user_data = storage.get(f"users.{username}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    user_role = Role(user_data.get("role", "user"))

    # Cannot delete super admin
    if user_role == Role.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Cannot delete super administrator")

    # Cannot delete self
    if username == session.user_id:
        raise HTTPException(status_code=403, detail="Cannot delete your own account")

    # Check permissions
    if not AuthManager.can_manage_role(session.role, user_role):
        raise HTTPException(status_code=403, detail="No permission to delete this user")

    # Delete user
    users = storage.get("users", {})
    if username in users:
        del users[username]
        storage.set("users", users)

    # Invalidate all sessions
    auth.invalidate_user_sessions(username)

    return RedirectResponse(url="/admin/users", status_code=303)


# ============================================================================
# Verification
# ============================================================================

@router.post("/verify/{username}")
async def verify_user(
    request: Request,
    username: str,
    csrf_token: str = Form(...),
):
    """Approve user verification."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]
    require_auth = imports["require_auth"]

    # Verify CSRF
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not secrets.compare_digest(csrf_token, csrf_cookie):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    session = await require_auth()(request)

    if not AuthManager.is_admin_or_above(session.role):
        raise HTTPException(status_code=403, detail="Only admins can verify users")

    user_data = storage.get(f"users.{username}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    user_data["is_verified"] = True
    user_data["verified_at"] = datetime.now(timezone.utc).isoformat()
    user_data["verified_by"] = session.user_id
    user_data["verification_requested_at"] = None

    storage.set(f"users.{username}", user_data)

    # Try to send notification email
    try:
        from ..core.email_service import EmailService
        email_service = EmailService(storage)
        if email_service.is_configured() and user_data.get("email"):
            site_title = storage.get("config.site_title", "Website")
            email_service.send_verification_approved_email(
                user_data["email"],
                username,
                site_title,
                f"/profile/{username}",
            )
    except Exception:
        pass  # Email is optional

    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/unverify/{username}")
async def unverify_user(
    request: Request,
    username: str,
    csrf_token: str = Form(...),
):
    """Revoke user verification."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]
    require_auth = imports["require_auth"]

    # Verify CSRF
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not secrets.compare_digest(csrf_token, csrf_cookie):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    session = await require_auth()(request)

    if not AuthManager.is_admin_or_above(session.role):
        raise HTTPException(status_code=403, detail="Only admins can revoke verification")

    user_data = storage.get(f"users.{username}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    user_data["is_verified"] = False
    user_data["verified_at"] = None
    user_data["verified_by"] = None

    storage.set(f"users.{username}", user_data)

    return RedirectResponse(url=f"/admin/users/edit/{username}", status_code=303)


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/api/list", response_class=JSONResponse)
async def api_list_users(request: Request):
    """Get users list as JSON."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]
    require_auth = imports["require_auth"]

    session = await require_auth()(request)

    if not auth.check_permission(session.role, "manage_users"):
        raise HTTPException(status_code=403, detail="No permission")

    users_data = storage.get("users", {})
    users_list = []

    for username, user_data in users_data.items():
        users_list.append({
            "username": username,
            "email": user_data.get("email"),
            "display_name": user_data.get("display_name"),
            "role": user_data.get("role"),
            "is_verified": user_data.get("is_verified", False),
            "is_active": user_data.get("is_active", True),
            "created_at": user_data.get("created_at"),
        })

    return JSONResponse({"users": users_list})
