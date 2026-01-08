"""FastAPI application for ChelCheleh."""

import asyncio
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .core.access_middleware import AccessMiddleware
from .core.audit_log import AuditLogger
from .core.auth import AuthManager
from .core.config import AppConfig, Config
from .core.csrf import CSRFMiddleware, CSRFProtection, get_csrf_token
from .core.hooks import hook_manager
from .core.i18n import i18n
from .core.language_middleware import (
    LanguageMiddleware,
    get_language_from_request,
    get_direction_from_request,
)
from .core.languages import get_available_languages
from .core.plugins import PluginManager
from .core.sanitize import Sanitizer
from .core.security_headers import SecurityHeadersMiddleware
from .core.session_store import RateLimitStore, SessionStore
from .core.storage import Storage
from .core.themes import CMSContext, ThemeManager
from .admin.routes import router as admin_router
from .admin.blog_routes import blog_router
from .admin.user_routes import router as user_router
from .frontend.blog_routes import blog_frontend_router
from .frontend.auth_routes import router as auth_router
from .frontend.profile_routes import router as profile_router
from .frontend.search_routes import router as search_router


# Global instances (initialized at startup)
app_config: AppConfig | None = None
storage: Storage | None = None
config: Config | None = None
auth: AuthManager | None = None
sanitizer: Sanitizer | None = None
theme_manager: ThemeManager | None = None
plugin_manager: PluginManager | None = None
audit_logger: AuditLogger | None = None
_cleanup_task: asyncio.Task | None = None


async def periodic_cleanup():
    """Background task for periodic cleanup of sessions, rate limits, and audit logs."""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour

            if auth:
                # Clean up expired sessions
                cleaned_sessions = auth.cleanup_expired_sessions()
                if cleaned_sessions > 0:
                    from .core.logging import logger
                    logger.info(f"Cleaned up {cleaned_sessions} expired sessions")

                # Clean up old rate limit entries
                cleaned_rate_limits = auth.cleanup_rate_limits()
                if cleaned_rate_limits > 0:
                    from .core.logging import logger
                    logger.info(f"Cleaned up rate limits for {cleaned_rate_limits} IPs")

            if audit_logger:
                # Clean up old audit log entries
                cleaned_entries = audit_logger.cleanup_old_entries()
                if cleaned_entries > 0:
                    from .core.logging import logger
                    logger.info(f"Cleaned up {cleaned_entries} old audit log entries")

        except asyncio.CancelledError:
            break
        except Exception as e:
            from .core.logging import logger
            logger.error(f"Error in periodic cleanup: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize on startup."""
    global app_config, storage, config, auth, sanitizer
    global theme_manager, plugin_manager, audit_logger

    # Load configuration
    app_config = AppConfig.from_env()

    # Initialize storage
    storage = Storage(app_config.db_path)
    if storage.exists:
        storage.load()
    else:
        # Not initialized - will redirect to setup
        pass

    # Initialize config
    config = Config(app_config, storage)
    app.state.config = config
    app.state.storage = storage

    # Initialize persistent stores for sessions and rate limiting
    # This enables multi-worker support
    session_store = SessionStore(app_config.sessions_file)
    rate_limit_store = RateLimitStore(
        app_config.rate_limit_file,
        max_attempts=app_config.rate_limit_attempts,
        window_minutes=app_config.rate_limit_window_minutes,
    )

    # Initialize auth with persistent stores
    auth = AuthManager(
        bcrypt_rounds=app_config.bcrypt_rounds,
        session_lifetime_hours=app_config.session_lifetime_hours,
        rate_limit_attempts=app_config.rate_limit_attempts,
        rate_limit_window_minutes=app_config.rate_limit_window_minutes,
        session_store=session_store,
        rate_limit_store=rate_limit_store,
    )
    app.state.auth = auth

    # Initialize sanitizer
    sanitizer = Sanitizer(allow_html=app_config.allow_html_content)

    # Initialize theme manager
    theme_manager = ThemeManager(
        themes_dir=app_config.themes_dir,
        fallback_dir=Path(__file__).parent / "public" / "templates",
        active_theme=config.theme if storage.exists else "default",
    )

    # Initialize plugin manager
    plugin_manager = PluginManager(
        plugins_dir=app_config.plugins_dir,
        disabled_plugins=config.disabled_plugins if storage.exists else [],
    )

    # Load enabled plugins
    if storage.exists:
        plugin_manager.load_enabled_plugins()

    # Initialize audit logger
    audit_logger = AuditLogger(app_config.audit_log_path)

    # Start periodic cleanup task
    global _cleanup_task
    _cleanup_task = asyncio.create_task(periodic_cleanup())

    yield

    # Cancel cleanup task
    if _cleanup_task:
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            pass

    # Final cleanup on shutdown
    auth.cleanup_expired_sessions()
    auth.cleanup_rate_limits()


# Create FastAPI app
app = FastAPI(
    title="ChelCheleh",
    description="A secure, Python-based flat-file CMS",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files BEFORE including routes
# This ensures static files are served before the catch-all route
themes_dir = Path("themes")
if themes_dir.exists():
    app.mount(
        "/themes",
        StaticFiles(directory=themes_dir, follow_symlink=True),
        name="themes",
    )

admin_static = Path(__file__).parent / "admin" / "static"
if admin_static.exists():
    app.mount(
        "/admin/static",
        StaticFiles(directory=admin_static),
        name="admin_static",
    )

# Include admin routes
app.include_router(admin_router)
app.include_router(blog_router)
app.include_router(user_router, prefix="/admin")

# Include frontend routes (must be before catch-all page routes)
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(search_router)
app.include_router(blog_frontend_router)

# Add security headers middleware
# This provides comprehensive security headers including HSTS, CSP, and more
app.add_middleware(SecurityHeadersMiddleware, force_https=True)

# Add language detection middleware
# This detects user's preferred language from query param, cookie, or default
app.add_middleware(LanguageMiddleware)

# Add access control middleware
# This handles maintenance mode and require_login settings
app.add_middleware(AccessMiddleware)


# Dependency to get current session
async def get_session(request: Request):
    """Get current user session if logged in."""
    session_id = request.cookies.get("session_id")
    if session_id and auth:
        return auth.verify_session(session_id)
    return None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render homepage."""
    return await render_page(request, config.default_page if config else "home")


@app.get("/uploads/{file_uuid}")
async def serve_upload(file_uuid: str):
    """Serve uploaded files securely."""
    from fastapi.responses import FileResponse

    if not storage or not storage.exists:
        raise HTTPException(status_code=503, detail="Site not initialized")

    # Get upload record
    upload = storage.get(f"uploads.{file_uuid}")
    if not upload:
        raise HTTPException(status_code=404, detail="File not found")

    # Get file path
    extension = upload.get("mime_type", "").split("/")[-1]
    file_path = app_config.uploads_dir / f"{file_uuid}.{extension}"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Validate path is within uploads directory
    try:
        file_path.resolve().relative_to(app_config.uploads_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        file_path,
        media_type=upload.get("mime_type", "application/octet-stream"),
        headers={
            "Cache-Control": "public, max-age=31536000",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/{slug:path}", response_class=HTMLResponse)
async def page(request: Request, slug: str, blog_page: int = 1):
    """Render a page by slug."""
    # Check if this is the login slug - always allow access to admin login
    if storage and storage.exists:
        login_slug = storage.get("config.login_slug")
        if slug == login_slug:
            return await login_page(request)

    return await render_page(request, slug, blog_page=blog_page)


async def render_page(request: Request, slug: str, blog_page: int = 1) -> HTMLResponse:
    """Render a page with the current theme."""
    if not storage or not storage.exists:
        return HTMLResponse(
            "<h1>Site Not Initialized</h1>"
            "<p>Run <code>pressassist init</code> to set up your site.</p>",
            status_code=503,
        )

    # Note: maintenance_mode and require_login are handled by AccessMiddleware

    # Get session and language info
    session = await get_session(request)
    current_lang = get_language_from_request(request)
    lang_direction = get_direction_from_request(request)

    # Get page data
    page_data = storage.get(f"pages.{slug}")

    if not page_data:
        # Try 404 page
        page_data = storage.get("pages.404")
        if not page_data:
            raise HTTPException(status_code=404, detail="Page not found")

    # Check visibility (session already loaded above for maintenance check)
    visibility = page_data.get("visibility", "show")
    if visibility == "hide" and not session:
        # Try to render 404 page instead of raising exception
        page_data = storage.get("pages.404")
        if not page_data:
            raise HTTPException(status_code=404, detail="Page not found")
        slug = "404"

    # Check language visibility (only if not admin/editor)
    page_language = page_data.get("language", "both")
    if page_language != "both" and page_language != current_lang and not session:
        # Page is not available in this language, try 404
        page_data = storage.get("pages.404")
        if not page_data:
            raise HTTPException(status_code=404, detail="Page not found")
        slug = "404"

    # Get blocks (with language support)
    blocks_data = storage.get("blocks", {})
    rendered_blocks = {}
    for name, block in blocks_data.items():
        # Skip disabled blocks
        if block.get("enabled") is False:
            rendered_blocks[name] = ""
            continue

        # Support both old format (single content) and new format (per-language content)
        if current_lang in block and isinstance(block.get(current_lang), dict):
            # New format: language-specific content
            lang_block = block[current_lang]
            content = lang_block.get("content", "")
            fmt = lang_block.get("content_format", "html")
        elif "content" in block:
            # Old format: single content for all languages
            content = block.get("content", "")
            fmt = block.get("content_format", "markdown")
        else:
            # Fallback: try first available language
            content = ""
            fmt = "html"
            for lang_code in ["fa", "en"]:
                if lang_code in block and isinstance(block.get(lang_code), dict):
                    lang_block = block[lang_code]
                    content = lang_block.get("content", "")
                    fmt = lang_block.get("content_format", "html")
                    break
        rendered_blocks[name] = sanitizer.render_content(content, fmt)

    # Render page content
    page_content = page_data.get("content", "")
    content_format = page_data.get("content_format", "markdown")
    rendered_content = sanitizer.render_content(page_content, content_format)

    # Get blog posts for this page with pagination
    from .frontend.blog_routes import get_blog_posts_for_page
    posts_per_page = page_data.get("posts_per_page", 10)
    blog_page = max(1, blog_page)  # Ensure page is at least 1
    offset = (blog_page - 1) * posts_per_page
    blog_posts_for_page, total_posts = get_blog_posts_for_page(
        storage, slug, limit=posts_per_page, offset=offset, current_lang=current_lang
    )
    total_pages = max(1, (total_posts + posts_per_page - 1) // posts_per_page)

    # Apply hooks
    hook_payload = {
        "content": rendered_content,
        "page": page_data,
        "request": request,
    }
    hook_payload = hook_manager.emit("page_render", hook_payload)
    rendered_content = hook_payload.get("content", rendered_content)

    # Get menu items (filtered by visibility and language)
    menu_items = storage.get("menu_items", [])
    visible_menu = []
    for item in menu_items:
        # Check visibility
        if item.get("visibility") != "show" and not session:
            continue
        # Check menu item's own language setting
        item_lang = item.get("language", "both")
        if item_lang != "both" and item_lang != current_lang and not session:
            continue
        # Also check language of the linked page
        page_slug = item.get("slug")
        if page_slug:
            linked_page = storage.get(f"pages.{page_slug}")
            if linked_page:
                page_lang = linked_page.get("language", "both")
                if page_lang != "both" and page_lang != current_lang and not session:
                    continue
        visible_menu.append(item)

    # Get localized page content if available
    page_title = page_data.get("title", slug)
    page_description = page_data.get("description", "")
    page_keywords = page_data.get("keywords", "")

    # Check for translations
    translations = page_data.get("translations", {})
    if current_lang in translations:
        trans = translations[current_lang]
        if trans.get("title"):
            page_title = trans["title"]
        if trans.get("content"):
            page_content = trans["content"]
            rendered_content = sanitizer.render_content(page_content, content_format)
        if trans.get("description"):
            page_description = trans["description"]
        if trans.get("keywords"):
            page_keywords = trans["keywords"]

    # Resolve active theme to match directory name for assets/templates
    theme_name = theme_manager.active_theme if theme_manager else storage.get("config.theme", "default")

    # Get site title - prefer header block content (plain text) if available
    header_block_content = rendered_blocks.get("header", "")
    if header_block_content:
        # Strip HTML tags to get plain text for title tag
        site_title_text = re.sub(r'<[^>]+>', '', header_block_content).strip()
        if not site_title_text:
            site_title_text = storage.get("config.site_title", "My Website")
    else:
        site_title_text = storage.get("config.site_title", "My Website")

    # Build context
    context = CMSContext(
        site_title=site_title_text,
        site_lang=storage.get("config.site_lang", "en"),
        theme=theme_name,
        # Language settings
        lang_direction=lang_direction,
        current_language=current_lang,
        available_languages=get_available_languages(),
        # Page content (possibly localized)
        page_title=page_title,
        page_slug=slug,
        page_content=rendered_content,
        page_description=page_description,
        page_keywords=page_keywords,
        page_template=page_data.get("template", "default"),
        hide_title=page_data.get("hide_title", False),
        hide_description=page_data.get("hide_description", False),
        blog_columns=page_data.get("blog_columns", 2),
        posts_per_page=posts_per_page,
        blog_current_page=blog_page,
        blog_total_pages=total_pages,
        blog_total_posts=total_posts,
        menu_items=visible_menu,
        blocks=rendered_blocks,
        is_admin=session and session.role.value == "admin" if session else False,
        is_editor=session and session.role.value in ("admin", "editor") if session else False,
        user=session.user_id if session else None,
        user_display_name=storage.get(f"users.{session.user_id}.display_name") if session else None,
        csrf_token=get_csrf_token(request),
        _asset_prefix=f"/themes/{theme_name}/static",
        # Blog posts assigned to this page
        blog_posts=blog_posts_for_page,
        # Copyright text
        copyright_text=storage.get("config.copyright_text", "Copyright 2026 ChelCheleh v0.1.0 — Designed by Ahmad Batebi"),
        # Search settings
        search_enabled=storage.get("config.enable_search", True),
        search_placeholder=i18n.get("search.placeholder", current_lang),
        search_hint=i18n.get("search.hint", current_lang),
        search_no_results=i18n.get("search.no_results", current_lang),
        search_navigate=i18n.get("search.navigate", current_lang),
        search_select=i18n.get("search.select", current_lang),
        search_close=i18n.get("search.close", current_lang),
        search_type_page=i18n.get("search.type_page", current_lang),
        search_type_blog=i18n.get("search.type_blog", current_lang),
        # Jump to Top button
        jump_to_top_enabled=storage.get("config.enable_jump_to_top", True),
    )

    # Inject CSS/JS via hooks
    css_parts = hook_manager.emit_collect("css_inject", {"request": request})
    js_parts = hook_manager.emit_collect("js_inject", {"request": request})
    context.admin_css = "\n".join(str(p) for p in css_parts if p)
    context.admin_js = "\n".join(str(p) for p in js_parts if p)

    # Render with theme
    html = theme_manager.render_page(context)

    return HTMLResponse(html)


def _login_failed_response() -> HTMLResponse:
    """Return a login failed error page."""
    return HTMLResponse(
        """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login Failed</title>
            <meta charset="utf-8">
            <style>
                body { font-family: system-ui; text-align: center; padding-top: 100px; }
                .error { color: red; }
            </style>
        </head>
        <body>
            <h1 class="error">Invalid Credentials</h1>
            <p><a href="">Try again</a></p>
        </body>
        </html>
        """,
        status_code=401,
    )


async def login_page(request: Request) -> HTMLResponse:
    """Render login page."""
    import secrets as _secrets

    # Get or create CSRF token
    csrf_token = request.cookies.get("csrf_token")
    needs_cookie = False
    if not csrf_token:
        csrf_token = _secrets.token_urlsafe(32)
        needs_cookie = True

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login - ChelCheleh</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: system-ui, sans-serif; max-width: 400px; margin: 100px auto; padding: 20px; }}
            h1 {{ text-align: center; }}
            form {{ display: flex; flex-direction: column; gap: 15px; }}
            input {{ padding: 10px; font-size: 16px; border: 1px solid #ccc; border-radius: 4px; }}
            button {{ padding: 12px; font-size: 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }}
            button:hover {{ background: #0056b3; }}
            .error {{ color: red; text-align: center; }}
        </style>
    </head>
    <body>
        <h1>Login</h1>
        <form method="POST">
            <input type="hidden" name="csrf_token" value="{csrf_token}">
            <input type="text" name="username" placeholder="Username" required autofocus>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <footer style="text-align:center;padding:2rem 1rem;margin-top:3rem;border-top:1px solid #e2e8f0;color:#64748b;font-size:0.875rem;">
            <p>ChelCheleh v0.1.0</p>
            <p>Designed by Ahmad Batebi
                <a href="https://github.com/ahmadbatebi/pycms" target="_blank" style="margin-left:0.5rem;color:#64748b;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle;">
                        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                    </svg>
                </a>
            </p>
        </footer>
    </body>
    </html>
    """
    response = HTMLResponse(html)

    # Set CSRF cookie if needed
    if needs_cookie:
        # Use force_https setting from config to determine secure flag
        use_secure = request.url.scheme == "https"
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            httponly=False,  # Must be readable by JavaScript for double-submit pattern
            samesite="lax",
            secure=use_secure,
            max_age=3600 * 4,
        )

    return response


@app.post("/{slug:path}")
async def handle_login(request: Request, slug: str):
    """Handle login form submission."""
    if not storage or not storage.exists:
        raise HTTPException(status_code=503, detail="Site not initialized")

    login_slug = storage.get("config.login_slug")
    if slug != login_slug:
        raise HTTPException(status_code=404, detail="Not found")

    # Get form data
    form = await request.form()
    username = form.get("username", "")
    password = form.get("password", "")
    csrf_token = form.get("csrf_token", "")

    # Verify CSRF using constant-time comparison to prevent timing attacks
    import secrets as _secrets
    cookie_token = request.cookies.get("csrf_token", "")
    if not csrf_token or not cookie_token or not _secrets.compare_digest(csrf_token, cookie_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    # Get client info
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")

    # Check rate limit
    if not auth.check_rate_limit(client_ip):
        audit_logger.log_login_failed(username, client_ip, user_agent, "rate_limited")
        raise HTTPException(status_code=429, detail="Too many login attempts")

    # Verify user exists and password is correct
    user_data = storage.get(f"users.{username}")
    if not user_data:
        # User not found - log and fail
        auth.record_login_attempt(client_ip, False, user_agent)
        audit_logger.log_login_failed(username, client_ip, user_agent, "user_not_found")
        return _login_failed_response()

    password_hash = user_data.get("password_hash", "")
    if auth.verify_password(password, password_hash):
        # Success!
        auth.record_login_attempt(client_ip, True, user_agent)
        audit_logger.log_login_success(username, client_ip, user_agent)

        # Get user role
        from .core.models import Role
        user_role_str = user_data.get("role", "viewer")
        try:
            user_role = Role(user_role_str)
        except ValueError:
            user_role = Role.VIEWER

        # Create session
        session = auth.create_session(
            user_id=username,
            role=user_role,
            ip=client_ip,
            user_agent=user_agent,
        )

        # Redirect to admin
        response = RedirectResponse(url="/admin/", status_code=303)
        response.set_cookie(
            key="session_id",
            value=session.session_id,
            httponly=True,
            samesite="lax",
            secure=request.url.scheme == "https",
            max_age=3600 * 4,
        )
        return response
    else:
        # Failed
        auth.record_login_attempt(client_ip, False, user_agent)
        audit_logger.log_login_failed(username, client_ip, user_agent, "invalid_password")
        return _login_failed_response()
