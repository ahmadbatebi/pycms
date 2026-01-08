"""FastAPI dependency injection system for ChelCheleh.

This module provides a clean dependency injection pattern that replaces
global state with proper FastAPI dependencies. This makes testing easier
and avoids circular imports.
"""

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request

from .models import Role, Session


@dataclass
class AppState:
    """Application state container.

    This is stored in app.state and provides access to all
    initialized services.
    """
    config: "AppConfig"
    storage: "Storage"
    auth: "AuthManager"
    sanitizer: "Sanitizer"
    theme_manager: "ThemeManager"
    plugin_manager: "PluginManager"
    audit_logger: "AuditLogger"


def get_app_state(request: Request) -> AppState:
    """Get application state from request.

    Args:
        request: FastAPI request object.

    Returns:
        AppState containing all initialized services.

    Raises:
        HTTPException: If app state not initialized.
    """
    if not hasattr(request.app.state, "cms"):
        raise HTTPException(
            status_code=503,
            detail="Application not initialized"
        )
    return request.app.state.cms


def get_storage(request: Request):
    """Get storage instance.

    Args:
        request: FastAPI request object.

    Returns:
        Storage instance.
    """
    # Import here to avoid circular imports during module load
    from ..main import storage
    if not storage or not storage.exists:
        raise HTTPException(
            status_code=503,
            detail="Storage not initialized"
        )
    return storage


def get_auth(request: Request):
    """Get auth manager instance.

    Args:
        request: FastAPI request object.

    Returns:
        AuthManager instance.
    """
    from ..main import auth
    if not auth:
        raise HTTPException(
            status_code=503,
            detail="Auth not initialized"
        )
    return auth


def get_sanitizer(request: Request):
    """Get sanitizer instance.

    Args:
        request: FastAPI request object.

    Returns:
        Sanitizer instance.
    """
    from ..main import sanitizer
    if not sanitizer:
        raise HTTPException(
            status_code=503,
            detail="Sanitizer not initialized"
        )
    return sanitizer


def get_audit_logger(request: Request):
    """Get audit logger instance.

    Args:
        request: FastAPI request object.

    Returns:
        AuditLogger instance.
    """
    from ..main import audit_logger
    if not audit_logger:
        raise HTTPException(
            status_code=503,
            detail="Audit logger not initialized"
        )
    return audit_logger


def get_app_config(request: Request):
    """Get application configuration.

    Args:
        request: FastAPI request object.

    Returns:
        AppConfig instance.
    """
    from ..main import app_config
    if not app_config:
        raise HTTPException(
            status_code=503,
            detail="App config not initialized"
        )
    return app_config


async def get_current_session(request: Request) -> Optional[Session]:
    """Get current user session if logged in.

    Args:
        request: FastAPI request object.

    Returns:
        Session if user is logged in, None otherwise.
    """
    from ..main import auth

    session_id = request.cookies.get("session_id")
    if session_id and auth:
        return auth.verify_session(session_id)
    return None


async def require_session(
    session: Optional[Session] = Depends(get_current_session)
) -> Session:
    """Require an authenticated session.

    Args:
        session: Current session from dependency.

    Returns:
        Session object.

    Raises:
        HTTPException: If not authenticated.
    """
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    return session


def require_role(allowed_roles: list[Role]):
    """Create a dependency that requires specific roles.

    Args:
        allowed_roles: List of roles that are allowed.

    Returns:
        Dependency function.
    """
    async def check_role(
        session: Session = Depends(require_session)
    ) -> Session:
        if session.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions"
            )
        return session

    return check_role


def require_admin():
    """Require admin or super_admin role."""
    return require_role([Role.SUPER_ADMIN, Role.ADMIN])


def require_editor():
    """Require editor, admin, or super_admin role."""
    return require_role([Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR])


async def get_client_info(request: Request) -> dict:
    """Extract client information from request.

    Args:
        request: FastAPI request object.

    Returns:
        Dict with ip and user_agent.
    """
    return {
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", ""),
    }
