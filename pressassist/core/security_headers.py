"""Security headers middleware."""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses.

    Implements recommended security headers for public web applications.
    """

    def __init__(
        self,
        app,
        force_https: bool = True,
        csp_directives: dict[str, str] | None = None,
    ):
        """Initialize middleware.

        Args:
            app: FastAPI application.
            force_https: Whether to add HSTS header.
            csp_directives: Custom CSP directives.
        """
        super().__init__(app)
        self.force_https = force_https
        self.csp_base = self._build_csp(csp_directives, include_upgrade=False)
        self.csp_https = self._build_csp(csp_directives, include_upgrade=True)

        # Embed sources for media embeds (YouTube, Vimeo, etc.)
        embed_sources = (
            "https://www.youtube.com https://www.youtube-nocookie.com "
            "https://player.vimeo.com https://www.instagram.com "
            "https://platform.twitter.com https://www.tiktok.com "
            "https://open.spotify.com https://w.soundcloud.com "
            "https://www.aparat.com"
        )

        # Blog/frontend CSP with embed support
        blog_csp = dict(csp_directives or {})
        blog_csp.setdefault(
            "frame-src",
            f"'self' {embed_sources}"
        )
        blog_csp.setdefault(
            "script-src",
            "'self' 'unsafe-inline' https://platform.twitter.com "
            "https://www.instagram.com https://www.tiktok.com"
        )
        blog_csp.setdefault("style-src", "'self' 'unsafe-inline'")
        self.blog_csp_base = self._build_csp(blog_csp, include_upgrade=False)
        self.blog_csp_https = self._build_csp(blog_csp, include_upgrade=True)

        # Admin CSP (CKEditor self-hosted - no external CDN needed)
        admin_csp = dict(csp_directives or {})
        admin_csp.setdefault("script-src", "'self' 'unsafe-inline'")
        admin_csp.setdefault("style-src", "'self' 'unsafe-inline'")
        admin_csp.setdefault("font-src", "'self'")
        admin_csp.setdefault("img-src", "'self' data: blob:")
        admin_csp.setdefault("connect-src", "'self'")
        admin_csp.setdefault(
            "frame-src",
            f"'self' {embed_sources}"
        )
        self.admin_csp_base = self._build_csp(admin_csp, include_upgrade=False)
        self.admin_csp_https = self._build_csp(admin_csp, include_upgrade=True)

    def _build_csp(self, custom: dict[str, str] | None, include_upgrade: bool) -> str:
        """Build Content-Security-Policy header value.

        Args:
            custom: Custom directives to override defaults.

        Returns:
            CSP header string.
        """
        defaults = {
            "default-src": "'self'",
            "script-src": "'self'",
            "style-src": "'self' 'unsafe-inline'",  # Inline styles for Markdown
            "img-src": "'self' data:",
            "font-src": "'self'",
            "connect-src": "'self'",
            "frame-src": "'self'",
            "frame-ancestors": "'none'",
            "base-uri": "'self'",
            "form-action": "'self'",
        }
        if include_upgrade:
            defaults["upgrade-insecure-requests"] = ""

        if custom:
            defaults.update(custom)

        parts = []
        for key, value in defaults.items():
            if value:
                parts.append(f"{key} {value}")
            else:
                parts.append(key)

        return "; ".join(parts)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to response.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response with security headers.
        """
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # XSS protection (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        path = request.url.path
        is_https = request.url.scheme == "https"

        if "/admin" in path:
            csp = self.admin_csp_https if is_https else self.admin_csp_base
        elif "/blog" in path or path.startswith("/page/"):
            # Blog and pages may contain embedded media
            csp = self.blog_csp_https if is_https else self.blog_csp_base
        else:
            csp = self.csp_https if is_https else self.csp_base

        response.headers["Content-Security-Policy"] = csp

        # HSTS for HTTPS
        if self.force_https:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Prevent caching of sensitive pages
        if "/admin" in request.url.path:
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, private"
            )
            response.headers["Pragma"] = "no-cache"

        # Permissions Policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), "
            "gyroscope=(), magnetometer=(), microphone=(), "
            "payment=(), usb=()"
        )

        return response


def get_secure_cookie_settings(force_https: bool = True) -> dict:
    """Get secure cookie settings for session cookies.

    Args:
        force_https: Whether site requires HTTPS.

    Returns:
        Dictionary of cookie settings.
    """
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": force_https,
        "max_age": 3600 * 4,  # 4 hours
    }
