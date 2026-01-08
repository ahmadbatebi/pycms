"""Frontend authentication routes for ChelCheleh.

Handles public user login, registration, password reset, and logout.
"""

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..core.i18n import i18n, t
from ..core.models import ProfileVisibility, Role

router = APIRouter(tags=["auth"])


def _get_common_imports():
    """Lazy import to avoid circular imports."""
    from ..main import auth, storage

    return {
        "auth": auth,
        "storage": storage,
    }


def _should_use_secure_cookie(request: Request, force_https: bool) -> bool:
    """Decide whether to set Secure cookies for this request."""
    # Always allow non-secure cookies for local development hosts.
    if request.url.hostname in {"127.0.0.1", "localhost"}:
        return False
    if not force_https:
        return False
    return request.url.scheme == "https"


def _get_or_create_csrf_token(request: Request) -> tuple[str, bool]:
    """Get CSRF token from cookie or create a new one."""
    token = request.cookies.get("csrf_token")
    if token:
        return token, False
    return secrets.token_urlsafe(32), True


def _set_csrf_cookie(request: Request, response: HTMLResponse, token: str) -> None:
    """Set CSRF cookie with environment-appropriate settings."""
    imports = _get_common_imports()
    storage = imports["storage"]
    force_https = storage.get("config.force_https", True) if storage else True

    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,
        samesite="lax",
        secure=_should_use_secure_cookie(request, force_https),
        max_age=3600,
        path="/",
    )


def get_auth_page_styles() -> str:
    """Get styles for auth pages."""
    return '''
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: 'Vazirmatn', Tahoma, Arial, sans-serif;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
        }
        .auth-container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.2);
            padding: 2.5rem;
            width: 100%;
            max-width: 420px;
        }
        .auth-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .auth-header h1 {
            margin: 0 0 0.5rem;
            color: #1e293b;
            font-size: 1.75rem;
        }
        .auth-header p {
            margin: 0;
            color: #64748b;
        }
        .form-group {
            margin-bottom: 1.25rem;
        }
        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: #374151;
        }
        .form-group input {
            width: 100%;
            padding: 0.875rem 1rem;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.2s;
        }
        .form-group input:focus {
            outline: none;
            border-color: #7c3aed;
        }
        .btn {
            width: 100%;
            padding: 0.875rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        .auth-footer {
            text-align: center;
            margin-top: 1.5rem;
            color: #64748b;
        }
        .auth-footer a {
            color: #7c3aed;
            text-decoration: none;
            font-weight: 500;
        }
        .auth-footer a:hover {
            text-decoration: underline;
        }
        .error-message {
            background: #FEE2E2;
            color: #DC2626;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            font-size: 0.9rem;
        }
        .success-message {
            background: #D1FAE5;
            color: #059669;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            font-size: 0.9rem;
        }
        .site-title {
            color: #7c3aed;
            font-weight: 700;
        }
        [dir="rtl"] .form-group input {
            text-align: right;
        }
        [dir="rtl"] .form-group input[type="email"],
        [dir="rtl"] .form-group input[type="url"] {
            direction: ltr;
            text-align: left;
        }
    </style>
    '''


# ============================================================================
# Login
# ============================================================================

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str | None = None, success: str | None = None):
    """Render public login page."""
    # Note: maintenance_mode and require_login are handled by AccessMiddleware
    # /login is always allowed to enable users to log in

    imports = _get_common_imports()
    storage = imports["storage"]

    site_title = storage.get("config.site_title", "Website")
    # Use language from middleware (respects user's cookie/query param)
    site_lang = getattr(request.state, "language", storage.get("config.site_lang", "en"))
    direction = getattr(request.state, "lang_direction", "rtl" if site_lang == "fa" else "ltr")

    # Set i18n language for translations
    i18n.set_language(site_lang)

    # Generate CSRF token (reuse existing if present)
    csrf_token, needs_cookie = _get_or_create_csrf_token(request)

    error_html = f'<div class="error-message">{error}</div>' if error else ""
    success_html = f'<div class="success-message">{success}</div>' if success else ""

    html = f'''
    <!DOCTYPE html>
    <html lang="{site_lang}" dir="{direction}">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{t('auth.login')} - {site_title}</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;700&display=swap" rel="stylesheet">
        {get_auth_page_styles()}
    </head>
    <body>
        <div class="auth-container">
            <div class="auth-header">
                <h1>{t('auth.login')}</h1>
                <p>{t('auth.login_subtitle')}</p>
            </div>

            {error_html}
            {success_html}

            <form method="POST" action="/login">
                <input type="hidden" name="csrf_token" value="{csrf_token}">

                <div class="form-group">
                    <label for="username">{t('auth.username_or_email')}</label>
                    <input type="text" id="username" name="username" required autocomplete="username">
                </div>

                <div class="form-group">
                    <label for="password">{t('auth.password')}</label>
                    <input type="password" id="password" name="password" required autocomplete="current-password">
                </div>

                <button type="submit" class="btn">{t('auth.login_button')}</button>
            </form>

            <div class="auth-footer">
                <p><a href="/forgot-password">{t('auth.forgot_password')}</a></p>
                <p>{t('auth.no_account')} <a href="/register">{t('auth.register')}</a></p>
                <p style="margin-top:1rem;"><a href="/" style="color:#64748b;">&larr; {t('auth.back_to_site')}</a></p>
            </div>
        </div>
    </body>
    </html>
    '''

    response = HTMLResponse(content=html)
    if needs_cookie:
        _set_csrf_cookie(request, response, csrf_token)
    return response


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
):
    """Process login form submission."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]

    # Verify CSRF
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not secrets.compare_digest(csrf_token, csrf_cookie):
        return RedirectResponse(url="/login?error=Invalid+request", status_code=303)

    # Get client info
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")

    # Check rate limit
    if not auth.check_rate_limit(client_ip):
        return RedirectResponse(
            url="/login?error=" + t("auth.rate_limit_exceeded").replace(" ", "+"),
            status_code=303
        )

    # Find user by username or email
    username_lower = username.lower().strip()
    users = storage.get("users", {})
    user_data = None
    found_username = None

    for uname, data in users.items():
        if uname == username_lower or data.get("email") == username_lower:
            user_data = data
            found_username = uname
            break

    if not user_data:
        auth.record_login_attempt(client_ip, False, user_agent)
        return RedirectResponse(
            url="/login?error=" + t("auth.invalid_credentials").replace(" ", "+"),
            status_code=303
        )

    # Check if account is active
    if not user_data.get("is_active", True):
        auth.record_login_attempt(client_ip, False, user_agent)
        return RedirectResponse(
            url="/login?error=" + t("auth.account_disabled").replace(" ", "+"),
            status_code=303
        )

    # Verify password
    if not auth.verify_password(password, user_data.get("password_hash", "")):
        auth.record_login_attempt(client_ip, False, user_agent)
        return RedirectResponse(
            url="/login?error=" + t("auth.invalid_credentials").replace(" ", "+"),
            status_code=303
        )

    # Successful login
    auth.record_login_attempt(client_ip, True, user_agent)

    # Get role
    try:
        role = Role(user_data.get("role", "user"))
    except ValueError:
        role = Role.USER

    # Create session
    session = auth.create_session(found_username, role, client_ip, user_agent)

    # Update last login
    user_data["last_login"] = datetime.now(timezone.utc).isoformat()
    storage.set(f"users.{found_username}", user_data)

    # Determine redirect based on role
    if role in (Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR):
        redirect_url = "/admin/"
    else:
        redirect_url = f"/profile/{found_username}"

    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(
        key="session_id",
        value=session.session_id,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=int(auth.session_lifetime.total_seconds()),
    )
    return response


# ============================================================================
# Logout
# ============================================================================

@router.get("/logout")
async def logout(request: Request):
    """Logout current user."""
    imports = _get_common_imports()
    auth = imports["auth"]

    session_id = request.cookies.get("session_id")
    if session_id:
        auth.invalidate_session(session_id)

    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session_id")
    return response


# ============================================================================
# Registration
# ============================================================================

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str | None = None):
    """Render registration page."""
    imports = _get_common_imports()
    storage = imports["storage"]

    # Check if registration is enabled
    if not storage.get("config.enable_registration", True):
        raise HTTPException(status_code=403, detail=t("auth.registration_disabled"))

    site_title = storage.get("config.site_title", "Website")
    # Use language from middleware (respects user's cookie/query param)
    site_lang = getattr(request.state, "language", storage.get("config.site_lang", "en"))
    direction = getattr(request.state, "lang_direction", "rtl" if site_lang == "fa" else "ltr")

    # Set i18n language for translations
    i18n.set_language(site_lang)

    csrf_token, needs_cookie = _get_or_create_csrf_token(request)
    error_html = f'<div class="error-message">{error}</div>' if error else ""

    html = f'''
    <!DOCTYPE html>
    <html lang="{site_lang}" dir="{direction}">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{t('auth.register')} - {site_title}</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;700&display=swap" rel="stylesheet">
        {get_auth_page_styles()}
    </head>
    <body>
        <div class="auth-container">
            <div class="auth-header">
                <h1>{t('auth.register')}</h1>
                <p>{t('auth.register_subtitle')}</p>
            </div>

            {error_html}

            <form method="POST" action="/register">
                <input type="hidden" name="csrf_token" value="{csrf_token}">

                <div class="form-group">
                    <label for="username">{t('auth.username')} *</label>
                    <input type="text" id="username" name="username" required pattern="[a-zA-Z0-9_]{{3,50}}" minlength="3" maxlength="50" autocomplete="off" placeholder="john_doe" title="{t('auth.username_hint')}">
                    <small style="color:#64748b;font-size:0.8rem;">{t('auth.username_hint')}</small>
                </div>

                <div class="form-group">
                    <label for="email">{t('auth.email')} *</label>
                    <input type="email" id="email" name="email" required autocomplete="email">
                </div>

                <div class="form-group">
                    <label for="display_name">{t('auth.display_name')}</label>
                    <input type="text" id="display_name" name="display_name" maxlength="100">
                </div>

                <div class="form-group">
                    <label for="password">{t('auth.password')} *</label>
                    <input type="password" id="password" name="password" required minlength="12" autocomplete="new-password">
                    <small style="color:#64748b;font-size:0.8rem;">{t('auth.password_requirements')}</small>
                </div>

                <div class="form-group">
                    <label for="password_confirm">{t('auth.password_confirm')} *</label>
                    <input type="password" id="password_confirm" name="password_confirm" required minlength="12" autocomplete="new-password">
                </div>

                <button type="submit" class="btn">{t('auth.register_button')}</button>
            </form>

            <div class="auth-footer">
                <p>{t('auth.have_account')} <a href="/login">{t('auth.login')}</a></p>
                <p style="margin-top:1rem;"><a href="/" style="color:#64748b;">&larr; {t('auth.back_to_site')}</a></p>
            </div>
        </div>
    </body>
    </html>
    '''

    response = HTMLResponse(content=html)
    if needs_cookie:
        _set_csrf_cookie(request, response, csrf_token)
    return response


@router.post("/register")
async def register_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    display_name: str = Form(None),
    password: str = Form(...),
    password_confirm: str = Form(...),
    csrf_token: str = Form(...),
):
    """Process registration form."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]

    # Check if registration is enabled
    if not storage.get("config.enable_registration", True):
        raise HTTPException(status_code=403, detail=t("auth.registration_disabled"))

    # Verify CSRF - debug info
    csrf_cookie = request.cookies.get("csrf_token", "")
    print(f"DEBUG CSRF - Form token: {csrf_token[:20] if csrf_token else 'None'}...")
    print(f"DEBUG CSRF - Cookie token: {csrf_cookie[:20] if csrf_cookie else 'None'}...")
    print(f"DEBUG CSRF - All cookies: {list(request.cookies.keys())}")

    if not csrf_token or not csrf_cookie or not secrets.compare_digest(csrf_token, csrf_cookie):
        # Set i18n language for error message
        site_lang = getattr(request.state, "language", "en")
        i18n.set_language(site_lang)
        return RedirectResponse(url="/register?error=" + t("errors.csrf_invalid").replace(" ", "+"), status_code=303)

    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    if not auth.check_rate_limit(client_ip):
        return RedirectResponse(
            url="/register?error=" + t("auth.rate_limit_exceeded").replace(" ", "+"),
            status_code=303
        )

    # Validate passwords match
    if password != password_confirm:
        return RedirectResponse(
            url="/register?error=" + t("auth.passwords_mismatch").replace(" ", "+"),
            status_code=303
        )

    # Validate password length
    if len(password) < 12:
        return RedirectResponse(
            url="/register?error=" + t("auth.password_too_short").replace(" ", "+"),
            status_code=303
        )

    # Validate username format
    username_lower = username.lower().strip()
    if not username_lower.replace("_", "").isalnum():
        return RedirectResponse(
            url="/register?error=" + t("auth.invalid_username").replace(" ", "+"),
            status_code=303
        )

    # Check if username exists
    users = storage.get("users", {})
    if username_lower in users:
        return RedirectResponse(
            url="/register?error=" + t("auth.username_exists").replace(" ", "+"),
            status_code=303
        )

    # Check if email exists
    email_lower = email.lower().strip()
    for user_data in users.values():
        if user_data.get("email") == email_lower:
            return RedirectResponse(
                url="/register?error=" + t("auth.email_exists").replace(" ", "+"),
                status_code=303
            )

    # Create user
    user_data = {
        "username": username_lower,
        "password_hash": auth.hash_password(password),
        "role": Role.USER.value,
        "email": email_lower,
        "display_name": display_name.strip() if display_name else None,
        "phone": None,
        "bio": None,
        "avatar_uuid": None,
        "cover_image_uuid": None,
        "is_verified": False,
        "verification_requested_at": None,
        "verified_at": None,
        "verified_by": None,
        "is_active": True,
        "profile_visibility": ProfileVisibility.PUBLIC.value,
        "reset_token": None,
        "reset_token_expires": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": None,
    }

    storage.set(f"users.{username_lower}", user_data)

    # Try to send welcome email
    try:
        from ..core.email_service import EmailService
        email_service = EmailService(storage)
        if email_service.is_configured():
            site_title = storage.get("config.site_title", "Website")
            email_service.send_welcome_email(
                email_lower,
                username_lower,
                site_title,
                "/login",
            )
    except Exception:
        pass  # Email is optional

    return RedirectResponse(
        url="/login?success=" + t("auth.registration_success").replace(" ", "+"),
        status_code=303
    )


# ============================================================================
# Password Reset
# ============================================================================

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request, error: str | None = None, success: str | None = None):
    """Render forgot password page."""
    imports = _get_common_imports()
    storage = imports["storage"]

    site_title = storage.get("config.site_title", "Website")
    # Use language from middleware (respects user's cookie/query param)
    site_lang = getattr(request.state, "language", storage.get("config.site_lang", "en"))
    direction = getattr(request.state, "lang_direction", "rtl" if site_lang == "fa" else "ltr")

    # Set i18n language for translations
    i18n.set_language(site_lang)

    csrf_token, needs_cookie = _get_or_create_csrf_token(request)
    error_html = f'<div class="error-message">{error}</div>' if error else ""
    success_html = f'<div class="success-message">{success}</div>' if success else ""

    html = f'''
    <!DOCTYPE html>
    <html lang="{site_lang}" dir="{direction}">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{t('auth.forgot_password')} - {site_title}</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;700&display=swap" rel="stylesheet">
        {get_auth_page_styles()}
    </head>
    <body>
        <div class="auth-container">
            <div class="auth-header">
                <h1>{t('auth.forgot_password')}</h1>
                <p>{t('auth.forgot_password_subtitle')}</p>
            </div>

            {error_html}
            {success_html}

            <form method="POST" action="/forgot-password">
                <input type="hidden" name="csrf_token" value="{csrf_token}">

                <div class="form-group">
                    <label for="email">{t('auth.email')}</label>
                    <input type="email" id="email" name="email" required autocomplete="email">
                </div>

                <button type="submit" class="btn">{t('auth.send_reset_link')}</button>
            </form>

            <div class="auth-footer">
                <p><a href="/login">&larr; {t('auth.back_to_login')}</a></p>
            </div>
        </div>
    </body>
    </html>
    '''

    response = HTMLResponse(content=html)
    if needs_cookie:
        _set_csrf_cookie(request, response, csrf_token)
    return response


@router.post("/forgot-password")
async def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    csrf_token: str = Form(...),
):
    """Process forgot password form."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]

    # Verify CSRF
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not secrets.compare_digest(csrf_token, csrf_cookie):
        return RedirectResponse(url="/forgot-password?error=Invalid+request", status_code=303)

    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    if not auth.check_rate_limit(client_ip):
        return RedirectResponse(
            url="/forgot-password?error=" + t("auth.rate_limit_exceeded").replace(" ", "+"),
            status_code=303
        )

    # Find user by email
    email_lower = email.lower().strip()
    users = storage.get("users", {})
    found_username = None
    user_data = None

    for uname, data in users.items():
        if data.get("email") == email_lower:
            found_username = uname
            user_data = data
            break

    # Always show success (don't reveal if email exists)
    if user_data and found_username:
        # Generate reset token
        reset_token, expires_at = auth.generate_reset_token()

        # Save token to user
        user_data["reset_token"] = reset_token
        user_data["reset_token_expires"] = expires_at.isoformat()
        storage.set(f"users.{found_username}", user_data)

        # Try to send email
        try:
            from ..core.email_service import EmailService
            email_service = EmailService(storage)

            if email_service.is_configured():
                site_title = storage.get("config.site_title", "Website")
                reset_url = f"{request.url.scheme}://{request.url.netloc}/reset-password/{reset_token}"
                email_service.send_password_reset_email(
                    email_lower,
                    found_username,
                    reset_url,
                    site_title,
                )
            else:
                # SMTP not configured - for development, show token
                # In production, this should be logged only
                pass
        except Exception:
            pass

    return RedirectResponse(
        url="/forgot-password?success=" + t("auth.reset_email_sent").replace(" ", "+"),
        status_code=303
    )


@router.get("/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str, error: str | None = None):
    """Render reset password page."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]

    site_title = storage.get("config.site_title", "Website")
    # Use language from middleware (respects user's cookie/query param)
    site_lang = getattr(request.state, "language", storage.get("config.site_lang", "en"))
    direction = getattr(request.state, "lang_direction", "rtl" if site_lang == "fa" else "ltr")

    # Set i18n language for translations
    i18n.set_language(site_lang)

    # Find user with this token
    users = storage.get("users", {})
    valid_token = False

    for user_data in users.values():
        stored_token = user_data.get("reset_token")
        stored_expires = user_data.get("reset_token_expires")

        if stored_token and stored_expires:
            try:
                expires_dt = datetime.fromisoformat(stored_expires)
                if auth.verify_reset_token(stored_token, expires_dt, token):
                    valid_token = True
                    break
            except (ValueError, TypeError):
                continue

    if not valid_token:
        return RedirectResponse(
            url="/forgot-password?error=" + t("auth.invalid_reset_token").replace(" ", "+"),
            status_code=303
        )

    csrf_token, needs_cookie = _get_or_create_csrf_token(request)
    error_html = f'<div class="error-message">{error}</div>' if error else ""

    html = f'''
    <!DOCTYPE html>
    <html lang="{site_lang}" dir="{direction}">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{t('auth.reset_password')} - {site_title}</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;700&display=swap" rel="stylesheet">
        {get_auth_page_styles()}
    </head>
    <body>
        <div class="auth-container">
            <div class="auth-header">
                <h1>{t('auth.reset_password')}</h1>
                <p>{t('auth.reset_password_subtitle')}</p>
            </div>

            {error_html}

            <form method="POST" action="/reset-password/{token}">
                <input type="hidden" name="csrf_token" value="{csrf_token}">

                <div class="form-group">
                    <label for="password">{t('auth.new_password')}</label>
                    <input type="password" id="password" name="password" required minlength="12" autocomplete="new-password">
                    <small style="color:#64748b;font-size:0.8rem;">{t('auth.password_requirements')}</small>
                </div>

                <div class="form-group">
                    <label for="password_confirm">{t('auth.password_confirm')}</label>
                    <input type="password" id="password_confirm" name="password_confirm" required minlength="12" autocomplete="new-password">
                </div>

                <button type="submit" class="btn">{t('auth.reset_password_button')}</button>
            </form>
        </div>
    </body>
    </html>
    '''

    response = HTMLResponse(content=html)
    if needs_cookie:
        _set_csrf_cookie(request, response, csrf_token)
    return response


@router.post("/reset-password/{token}")
async def reset_password_submit(
    request: Request,
    token: str,
    password: str = Form(...),
    password_confirm: str = Form(...),
    csrf_token: str = Form(...),
):
    """Process reset password form."""
    imports = _get_common_imports()
    storage = imports["storage"]
    auth = imports["auth"]

    # Verify CSRF
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not secrets.compare_digest(csrf_token, csrf_cookie):
        return RedirectResponse(url=f"/reset-password/{token}?error=Invalid+request", status_code=303)

    # Validate passwords
    if password != password_confirm:
        return RedirectResponse(
            url=f"/reset-password/{token}?error=" + t("auth.passwords_mismatch").replace(" ", "+"),
            status_code=303
        )

    if len(password) < 12:
        return RedirectResponse(
            url=f"/reset-password/{token}?error=" + t("auth.password_too_short").replace(" ", "+"),
            status_code=303
        )

    # Find user with this token
    users = storage.get("users", {})
    found_username = None
    user_data = None

    for uname, data in users.items():
        stored_token = data.get("reset_token")
        stored_expires = data.get("reset_token_expires")

        if stored_token and stored_expires:
            try:
                expires_dt = datetime.fromisoformat(stored_expires)
                if auth.verify_reset_token(stored_token, expires_dt, token):
                    found_username = uname
                    user_data = data
                    break
            except (ValueError, TypeError):
                continue

    if not user_data or not found_username:
        return RedirectResponse(
            url="/forgot-password?error=" + t("auth.invalid_reset_token").replace(" ", "+"),
            status_code=303
        )

    # Update password
    user_data["password_hash"] = auth.hash_password(password)
    user_data["reset_token"] = None
    user_data["reset_token_expires"] = None
    storage.set(f"users.{found_username}", user_data)

    # Invalidate all sessions
    auth.invalidate_user_sessions(found_username)

    return RedirectResponse(
        url="/login?success=" + t("auth.password_reset_success").replace(" ", "+"),
        status_code=303
    )
