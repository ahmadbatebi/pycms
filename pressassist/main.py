"""FastAPI application for ChelCheleh CMS."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .core.audit_log import AuditLogger
from .core.auth import AuthManager
from .core.config import AppConfig, Config
from .core.csrf import CSRFMiddleware, CSRFProtection, get_csrf_token
from .core.hooks import hook_manager
from .core.plugins import PluginManager
from .core.sanitize import Sanitizer
from .core.security_headers import SecurityHeadersMiddleware
from .core.session_store import RateLimitStore, SessionStore
from .core.storage import Storage
from .core.themes import CMSContext, ThemeManager
from .admin.routes import router as admin_router


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
    title="ChelCheleh CMS",
    description="A secure, Python-based flat-file CMS",
    version="0.1.0",
    lifespan=lifespan,
)

# Include admin routes
app.include_router(admin_router)

# Add security headers middleware
# This provides comprehensive security headers including HSTS, CSP, and more
app.add_middleware(SecurityHeadersMiddleware, force_https=True)


# Dependency to get current session
async def get_session(request: Request):
    """Get current user session if logged in."""
    session_id = request.cookies.get("session_id")
    if session_id and auth:
        return auth.verify_session(session_id)
    return None


# Mount static files
@app.on_event("startup")
async def mount_static():
    """Mount static file directories."""
    if app_config:
        # Theme static files
        if app_config.themes_dir.exists():
            app.mount(
                "/themes",
                StaticFiles(directory=app_config.themes_dir),
                name="themes",
            )

        # Admin static files
        admin_static = Path(__file__).parent / "admin" / "static"
        if admin_static.exists():
            app.mount(
                "/admin/static",
                StaticFiles(directory=admin_static),
                name="admin_static",
            )


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
async def page(request: Request, slug: str):
    """Render a page by slug."""
    # Check if this is the login slug
    if storage and storage.exists:
        login_slug = storage.get("config.login_slug")
        if slug == login_slug:
            return await login_page(request)

    return await render_page(request, slug)


async def render_page(request: Request, slug: str) -> HTMLResponse:
    """Render a page with the current theme."""
    if not storage or not storage.exists:
        return HTMLResponse(
            "<h1>Site Not Initialized</h1>"
            "<p>Run <code>pressassist init</code> to set up your site.</p>",
            status_code=503,
        )

    # Get page data
    page_data = storage.get(f"pages.{slug}")

    if not page_data:
        # Try 404 page
        page_data = storage.get("pages.404")
        if not page_data:
            raise HTTPException(status_code=404, detail="Page not found")

    # Check visibility
    session = await get_session(request)
    visibility = page_data.get("visibility", "show")
    if visibility == "hide" and not session:
        raise HTTPException(status_code=404, detail="Page not found")

    # Get blocks
    blocks_data = storage.get("blocks", {})
    rendered_blocks = {}
    for name, block in blocks_data.items():
        content = block.get("content", "")
        fmt = block.get("content_format", "markdown")
        rendered_blocks[name] = sanitizer.render_content(content, fmt)

    # Render page content
    page_content = page_data.get("content", "")
    content_format = page_data.get("content_format", "markdown")
    rendered_content = sanitizer.render_content(page_content, content_format)

    # Apply hooks
    hook_payload = {
        "content": rendered_content,
        "page": page_data,
        "request": request,
    }
    hook_payload = hook_manager.emit("page_render", hook_payload)
    rendered_content = hook_payload.get("content", rendered_content)

    # Get menu items
    menu_items = storage.get("menu_items", [])
    visible_menu = [
        item for item in menu_items
        if item.get("visibility") == "show" or session
    ]

    # Build context
    context = CMSContext(
        site_title=storage.get("config.site_title", "My Website"),
        site_lang=storage.get("config.site_lang", "en"),
        theme=storage.get("config.theme", "default"),
        page_title=page_data.get("title", slug),
        page_slug=slug,
        page_content=rendered_content,
        page_description=page_data.get("description", ""),
        page_keywords=page_data.get("keywords", ""),
        menu_items=visible_menu,
        blocks=rendered_blocks,
        is_admin=session and session.role.value == "admin" if session else False,
        is_editor=session and session.role.value in ("admin", "editor") if session else False,
        user=session.user_id if session else None,
        csrf_token=get_csrf_token(request),
        _asset_prefix=f"/themes/{storage.get('config.theme', 'default')}/static",
    )

    # Inject CSS/JS via hooks
    css_parts = hook_manager.emit_collect("css_inject", {"request": request})
    js_parts = hook_manager.emit_collect("js_inject", {"request": request})
    context.admin_css = "\n".join(str(p) for p in css_parts if p)
    context.admin_js = "\n".join(str(p) for p in js_parts if p)

    # Render with theme
    html = theme_manager.render_page(context)

    return HTMLResponse(html)


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
        <title>Login - ChelCheleh CMS</title>
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
            <input type="password" name="password" placeholder="Password" required autofocus>
            <button type="submit">Login</button>
        </form>
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
        audit_logger.log_login_failed("admin", client_ip, user_agent, "rate_limited")
        raise HTTPException(status_code=429, detail="Too many login attempts")

    # Verify password
    admin_user = storage.get("users.admin")
    if not admin_user:
        raise HTTPException(status_code=500, detail="Admin user not configured")

    password_hash = admin_user.get("password_hash", "")
    if auth.verify_password(password, password_hash):
        # Success!
        auth.record_login_attempt(client_ip, True, user_agent)
        audit_logger.log_login_success("admin", client_ip, user_agent)

        # Create session
        from .core.models import Role
        session = auth.create_session(
            user_id="admin",
            role=Role.ADMIN,
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
        audit_logger.log_login_failed("admin", client_ip, user_agent, "invalid_password")

        # Return to login with error
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
                <h1 class="error">Invalid Password</h1>
                <p><a href="">Try again</a></p>
            </body>
            </html>
            """,
            status_code=401,
        )
