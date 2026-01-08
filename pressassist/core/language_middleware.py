"""Language detection middleware for ChelCheleh.

Detects user's preferred language from:
1. Query parameter (?lang=fa)
2. Cookie (cms_lang)
3. Default language
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .languages import DEFAULT_LANGUAGE, is_valid_language, get_direction
from .i18n import i18n

# Cookie name for language preference
LANGUAGE_COOKIE = "cms_lang"
ADMIN_LANGUAGE_COOKIE = "cms_admin_lang"

# Cookie max age: 1 year
COOKIE_MAX_AGE = 365 * 24 * 60 * 60


class LanguageMiddleware(BaseHTTPMiddleware):
    """Middleware to detect and set user's preferred language."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and detect language.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response with language cookie if changed.
        """
        # Detect language
        lang = self._detect_language(request)

        # Store in request state for handlers
        request.state.language = lang
        request.state.lang_direction = get_direction(lang)

        # Detect admin language separately
        admin_lang = self._detect_admin_language(request)
        request.state.admin_language = admin_lang
        request.state.admin_lang_direction = get_direction(admin_lang)

        # Set i18n language based on path
        if request.url.path.startswith("/admin"):
            i18n.set_language(admin_lang)
        else:
            i18n.set_language(lang)

        # Process request
        response = await call_next(request)

        # Set cookie if language was explicitly changed via query param
        lang_param = request.query_params.get("lang")
        if lang_param and is_valid_language(lang_param):
            if request.url.path.startswith("/admin"):
                response.set_cookie(
                    key=ADMIN_LANGUAGE_COOKIE,
                    value=lang_param,
                    max_age=COOKIE_MAX_AGE,
                    httponly=True,
                    samesite="lax",
                )
            else:
                response.set_cookie(
                    key=LANGUAGE_COOKIE,
                    value=lang_param,
                    max_age=COOKIE_MAX_AGE,
                    httponly=True,
                    samesite="lax",
                )

        return response

    def _detect_language(self, request: Request) -> str:
        """Detect frontend language from request.

        Priority:
        1. Query parameter (?lang=fa)
        2. Cookie
        3. Default language

        Args:
            request: Incoming request.

        Returns:
            Detected language code.
        """
        # 1. Query parameter
        lang = request.query_params.get("lang")
        if lang and is_valid_language(lang):
            return lang

        # 2. Cookie
        lang = request.cookies.get(LANGUAGE_COOKIE)
        if lang and is_valid_language(lang):
            return lang

        # 3. Site default from config (if available)
        config = getattr(request.app.state, "config", None)
        if config is not None:
            config_lang = config.get("site_lang", DEFAULT_LANGUAGE)
            if is_valid_language(config_lang):
                return config_lang

        # 4. Default
        return DEFAULT_LANGUAGE

    def _detect_admin_language(self, request: Request) -> str:
        """Detect admin panel language from request.

        Priority:
        1. Query parameter (?lang=fa)
        2. Admin cookie
        3. Default language

        Args:
            request: Incoming request.

        Returns:
            Detected language code.
        """
        # 1. Query parameter
        lang = request.query_params.get("lang")
        if lang and is_valid_language(lang):
            return lang

        # 2. Admin cookie
        lang = request.cookies.get(ADMIN_LANGUAGE_COOKIE)
        if lang and is_valid_language(lang):
            return lang

        # 3. Admin default from config (if available)
        config = getattr(request.app.state, "config", None)
        if config is not None:
            config_lang = config.get("admin_lang", DEFAULT_LANGUAGE)
            if is_valid_language(config_lang):
                return config_lang

        # 4. Default
        return DEFAULT_LANGUAGE


def get_language_from_request(request: Request) -> str:
    """Get language from request state.

    Args:
        request: Request object.

    Returns:
        Language code.
    """
    return getattr(request.state, "language", DEFAULT_LANGUAGE)


def get_admin_language_from_request(request: Request) -> str:
    """Get admin language from request state.

    Args:
        request: Request object.

    Returns:
        Admin language code.
    """
    return getattr(request.state, "admin_language", DEFAULT_LANGUAGE)


def get_direction_from_request(request: Request) -> str:
    """Get text direction from request state.

    Args:
        request: Request object.

    Returns:
        'rtl' or 'ltr'.
    """
    return getattr(request.state, "lang_direction", "ltr")


def get_admin_direction_from_request(request: Request) -> str:
    """Get admin text direction from request state.

    Args:
        request: Request object.

    Returns:
        'rtl' or 'ltr'.
    """
    return getattr(request.state, "admin_lang_direction", "ltr")
