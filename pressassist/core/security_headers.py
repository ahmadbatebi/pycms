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
        self.csp = self._build_csp(csp_directives)
        admin_csp = dict(csp_directives or {})
        admin_csp.setdefault("script-src", "'self' 'unsafe-inline'")
        self.admin_csp = self._build_csp(admin_csp)

    def _build_csp(self, custom: dict[str, str] | None) -> str:
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
            "frame-ancestors": "'none'",
            "base-uri": "'self'",
            "form-action": "'self'",
            "upgrade-insecure-requests": "",
        }

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
        if "/admin" in request.url.path:
            response.headers["Content-Security-Policy"] = self.admin_csp
        else:
            response.headers["Content-Security-Policy"] = self.csp

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
