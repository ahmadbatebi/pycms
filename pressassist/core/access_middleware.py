"""Access control middleware for ChelCheleh.

Handles:
1. Maintenance mode - blocks non-admin users from accessing the site
2. Require login - redirects unauthenticated users to login page
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from .i18n import i18n
from .languages import get_direction


# Paths that should always be accessible (even in maintenance/require_login mode)
ALWAYS_ALLOWED_PATHS = {
    "/logout",
    "/admin",
    "/admin/",
    "/admin/login",
}

# Paths that are only accessible when require_login is enabled
LOGIN_REQUIRED_PATHS = {
    "/login",
    "/register",
    "/forgot-password",
}

# Path prefixes that should always be accessible
ALWAYS_ALLOWED_PREFIXES = (
    "/admin/",
    "/themes/",
    "/uploads/",
    "/reset-password/",
    "/admin/static/",
    "/profile/",
    "/me/",
)


class AccessMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce maintenance mode and login requirements."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and check access restrictions.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response or redirect to login/maintenance page.
        """
        path = request.url.path

        # Always allow certain paths
        if path in ALWAYS_ALLOWED_PATHS:
            return await call_next(request)

        # Always allow certain prefixes
        for prefix in ALWAYS_ALLOWED_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Get storage from app state
        storage = getattr(request.app.state, "storage", None)
        if not storage or not storage.exists:
            return await call_next(request)

        # Always allow the secret admin login slug
        # This is the secure URL like /jYnYG6cIrCbfCbLKmILkRpdrhV7FbAFJ
        login_slug = storage.get("config.login_slug", "")
        if login_slug and path == f"/{login_slug}":
            return await call_next(request)

        # Check if path is a login-related path (only accessible when require_login is enabled)
        require_login = storage.get("config.require_login", False)
        if path in LOGIN_REQUIRED_PATHS:
            if require_login:
                # Allow access to /login, /register, /forgot-password when require_login is ON
                return await call_next(request)
            else:
                # Block access when require_login is OFF - return 404
                return Response(status_code=404)

        # Also block /reset-password/ prefix when require_login is OFF
        if path.startswith("/reset-password/") and not require_login:
            return Response(status_code=404)

        # Get session
        session = await self._get_session(request)

        # Check maintenance mode first
        maintenance_mode = storage.get("config.maintenance_mode", False)
        if maintenance_mode and not session:
            return self._maintenance_response(request, storage)

        # Check require_login - redirect unauthenticated users to login
        if require_login and not session:
            # Redirect to login with return URL
            return_url = str(request.url.path)
            if request.url.query:
                return_url += f"?{request.url.query}"
            return RedirectResponse(
                url=f"/login?next={return_url}",
                status_code=302,
            )

        return await call_next(request)

    async def _get_session(self, request: Request):
        """Get current user session if logged in.

        Args:
            request: Incoming request.

        Returns:
            Session object or None.
        """
        auth = getattr(request.app.state, "auth", None)
        if not auth:
            return None

        session_id = request.cookies.get("session_id")
        if session_id:
            return auth.verify_session(session_id)
        return None

    def _maintenance_response(self, request: Request, storage) -> HTMLResponse:
        """Generate maintenance mode page.

        Args:
            request: Incoming request.
            storage: Storage instance.

        Returns:
            HTML response with maintenance page.
        """
        site_lang = storage.get("config.site_lang", "en")
        lang_direction = get_direction(site_lang)
        site_title = storage.get("config.site_title", "Site Under Maintenance")
        maintenance_message = storage.get(
            "config.maintenance_message",
            "Site is under maintenance. Please check back later."
        )
        maintenance_title = i18n.get("maintenance.title", site_lang) if i18n else "Under Maintenance"

        html = f"""<!DOCTYPE html>
<html lang="{site_lang}" dir="{lang_direction}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{site_title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 2rem;
        }}
        .container {{
            text-align: center;
            max-width: 600px;
        }}
        .icon {{
            font-size: 4rem;
            margin-bottom: 1.5rem;
        }}
        h1 {{
            font-size: 2rem;
            margin-bottom: 1rem;
            font-weight: 600;
        }}
        p {{
            font-size: 1.1rem;
            opacity: 0.9;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">🔧</div>
        <h1>{maintenance_title}</h1>
        <p>{maintenance_message}</p>
    </div>
</body>
</html>"""
        return HTMLResponse(html, status_code=503)
