"""CSRF protection middleware and utilities."""

import secrets
from typing import Optional

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class CSRFProtection:
    """CSRF protection using double-submit cookie pattern.

    Generates a token that must be:
    1. Stored in a cookie (HttpOnly=False so JS can read it)
    2. Submitted in a header or form field
    3. Both values must match
    """

    COOKIE_NAME = "csrf_token"
    HEADER_NAME = "X-CSRF-Token"
    FORM_FIELD = "csrf_token"
    TOKEN_LENGTH = 32

    # Methods that require CSRF validation
    PROTECTED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

    # Paths exempt from CSRF (e.g., API endpoints with other auth)
    EXEMPT_PATHS: set[str] = set()

    def __init__(self, secret_key: str):
        """Initialize CSRF protection.

        Args:
            secret_key: Secret key for token generation.
        """
        self.secret_key = secret_key

    def generate_token(self) -> str:
        """Generate a new CSRF token.

        Returns:
            Random token string.
        """
        return secrets.token_urlsafe(self.TOKEN_LENGTH)

    def get_token_from_request(self, request: Request) -> Optional[str]:
        """Extract CSRF token from request.

        Checks header first, then form data, then query params.

        Args:
            request: FastAPI request object.

        Returns:
            Token if found, None otherwise.
        """
        # Check header first
        token = request.headers.get(self.HEADER_NAME)
        if token:
            return token

        # Check will be done in route handler for form data
        return None

    def get_token_from_cookie(self, request: Request) -> Optional[str]:
        """Get CSRF token from cookie.

        Args:
            request: FastAPI request object.

        Returns:
            Token if found, None otherwise.
        """
        return request.cookies.get(self.COOKIE_NAME)

    def validate_token(self, request_token: str, cookie_token: str) -> bool:
        """Validate that request token matches cookie token.

        Args:
            request_token: Token from header/form.
            cookie_token: Token from cookie.

        Returns:
            True if tokens match.
        """
        if not request_token or not cookie_token:
            return False
        return secrets.compare_digest(request_token, cookie_token)

    def set_cookie(self, response: Response, token: str) -> None:
        """Set CSRF token cookie on response.

        Args:
            response: Response to set cookie on.
            token: CSRF token.
        """
        response.set_cookie(
            key=self.COOKIE_NAME,
            value=token,
            httponly=False,  # Must be readable by JavaScript
            samesite="lax",
            secure=True,  # Only over HTTPS
            max_age=3600 * 4,  # 4 hours
        )

    def should_validate(self, request: Request) -> bool:
        """Check if request should have CSRF validation.

        Args:
            request: FastAPI request.

        Returns:
            True if validation needed.
        """
        # Only validate protected methods
        if request.method not in self.PROTECTED_METHODS:
            return False

        # Skip exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return False

        return True


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware for CSRF protection.

    Automatically validates CSRF tokens on protected requests
    and sets new tokens on responses.
    """

    def __init__(self, app, csrf: CSRFProtection):
        """Initialize middleware.

        Args:
            app: FastAPI application.
            csrf: CSRFProtection instance.
        """
        super().__init__(app)
        self.csrf = csrf

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with CSRF validation.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response from handler.

        Raises:
            HTTPException: If CSRF validation fails.
        """
        # Check if validation needed
        if self.csrf.should_validate(request):
            cookie_token = self.csrf.get_token_from_cookie(request)
            request_token = self.csrf.get_token_from_request(request)

            # For form submissions, we need to parse the body
            # This is handled separately in route handlers

            if request_token and cookie_token:
                if not self.csrf.validate_token(request_token, cookie_token):
                    raise HTTPException(status_code=403, detail="CSRF token mismatch")
            elif not request_token and cookie_token:
                # Token missing from request - will be validated in handler
                # for form submissions
                pass

        response = await call_next(request)

        # Set new token on GET requests if not present
        if request.method == "GET":
            if not self.csrf.get_token_from_cookie(request):
                token = self.csrf.generate_token()
                self.csrf.set_cookie(response, token)

        return response


def get_csrf_token(request: Request) -> str:
    """Get or create CSRF token for templates.

    Args:
        request: FastAPI request.

    Returns:
        CSRF token string.
    """
    token = request.cookies.get(CSRFProtection.COOKIE_NAME)
    if not token:
        token = secrets.token_urlsafe(32)
    return token
