"""Admin API routes for ChelCheleh CMS."""

import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

# CMS Info
CMS_NAME = "ChelCheleh CMS"
CMS_VERSION = "0.1.0"
ADMIN_FOOTER = f'''
<footer style="text-align:center;padding:2rem 1rem;margin-top:2rem;border-top:1px solid #e2e8f0;color:#64748b;font-size:0.875rem;">
    <p>{CMS_NAME} v{CMS_VERSION}</p>
    <p>Designed by Ahmad Batebi
        <a href="https://github.com/ahmadbatebi/pycms" target="_blank" style="margin-left:0.5rem;color:#64748b;">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle;">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
        </a>
    </p>
</footer>
'''

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from ..core.models import Role

# Allowed upload extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "pdf", "doc", "docx", "txt"}

# Image extensions that can be re-encoded
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

# Maximum upload size: 5MB
MAX_UPLOAD_SIZE = 5 * 1024 * 1024

# Magic bytes for file validation
MAGIC_BYTES = {
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
    "webp": b"RIFF",
    "gif": b"GIF8",
    "pdf": b"%PDF-",
    "doc": b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1",
    "docx": b"PK\x03\x04",
}

router = APIRouter(prefix="/admin", tags=["admin"])

def get_csrf_token(request: Request) -> tuple[str, bool]:
    """Get CSRF token and indicate whether cookie needs setting."""
    token = request.cookies.get("csrf_token")
    if token:
        return token, False
    return secrets.token_urlsafe(32), True


def set_csrf_cookie(request: Request, response: HTMLResponse, token: str) -> None:
    """Set CSRF cookie on response."""
    use_secure = request.url.scheme == "https"
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,
        samesite="lax",
        secure=use_secure,
        max_age=3600 * 4,
    )


def require_auth(roles: list[Role] | None = None):
    """Dependency to require authentication."""
    async def check_auth(request: Request):
        from ..main import auth, storage

        session_id = request.cookies.get("session_id")
        if not session_id or not auth:
            raise HTTPException(status_code=401, detail="Not authenticated")

        session = auth.verify_session(session_id)
        if not session:
            raise HTTPException(status_code=401, detail="Session expired")

        if roles and session.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return session

    return check_auth


def require_csrf(request: Request):
    """Dependency to verify CSRF token."""
    csrf_header = request.headers.get("X-CSRF-Token", "")
    csrf_cookie = request.cookies.get("csrf_token", "")

    if not csrf_header or not csrf_cookie:
        raise HTTPException(status_code=403, detail="Missing CSRF token")

    if not secrets.compare_digest(csrf_header, csrf_cookie):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


# ============================================================================
# Dashboard
# ============================================================================

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    session=Depends(require_auth()),
):
    """Render admin dashboard."""
    from ..main import storage, theme_manager

    # Get site stats
    pages = storage.get("pages", {})
    blocks = storage.get("blocks", {})
    uploads = storage.get("uploads", {})

    token, needs_cookie = get_csrf_token(request)
    token, needs_cookie = get_csrf_token(request)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Dashboard - {CMS_NAME}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                font-family: system-ui, -apple-system, sans-serif;
                margin: 0;
                background: #f5f5f5;
            }}
            .header {{
                background: #1e293b;
                color: white;
                padding: 1rem 2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .header h1 {{ margin: 0; font-size: 1.5rem; }}
            .header a {{ color: #94a3b8; text-decoration: none; }}
            .header a:hover {{ color: white; }}
            .container {{ max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                margin-bottom: 2rem;
            }}
            .stat {{
                background: white;
                padding: 1.5rem;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .stat h3 {{ margin: 0 0 0.5rem; color: #64748b; font-size: 0.875rem; }}
            .stat .value {{ font-size: 2rem; font-weight: 600; color: #1e293b; }}
            .nav {{
                background: white;
                padding: 1rem;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                margin-bottom: 1rem;
            }}
            .nav a {{
                display: inline-block;
                padding: 0.5rem 1rem;
                margin-right: 0.5rem;
                color: #1e293b;
                text-decoration: none;
                border-radius: 4px;
            }}
            .nav a:hover {{ background: #f1f5f9; }}
            .section {{
                background: white;
                padding: 1.5rem;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                margin-bottom: 1rem;
            }}
            .section h2 {{ margin: 0 0 1rem; font-size: 1.25rem; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ text-align: left; padding: 0.75rem; border-bottom: 1px solid #e2e8f0; }}
            th {{ font-weight: 600; color: #64748b; }}
            .btn {{
                display: inline-block;
                padding: 0.5rem 1rem;
                background: #3b82f6;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                border: none;
                cursor: pointer;
            }}
            .btn:hover {{ background: #2563eb; }}
            .btn-danger {{ background: #ef4444; }}
            .btn-danger:hover {{ background: #dc2626; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{CMS_NAME}</h1>
            <div>
                <a href="/" target="_blank" style="margin-right: 1rem;">View Site</a> |
                <span>Logged in as {session.user_id}</span> |
                <a href="/admin/logout">Logout</a>
            </div>
        </div>
        <div class="container">
            <div class="stats">
                <div class="stat">
                    <h3>Pages</h3>
                    <div class="value">{len(pages)}</div>
                </div>
                <div class="stat">
                    <h3>Blocks</h3>
                    <div class="value">{len(blocks)}</div>
                </div>
                <div class="stat">
                    <h3>Uploads</h3>
                    <div class="value">{len(uploads)}</div>
                </div>
            </div>

            <div class="nav">
                <a href="/admin/pages">Pages</a>
                <a href="/admin/menu">Menu</a>
                <a href="/admin/blocks">Blocks</a>
                <a href="/admin/uploads">Uploads</a>
                <a href="/admin/settings">Settings</a>
            </div>

            <div class="section">
                <h2>Quick Actions</h2>
                <a href="/admin/pages/new" class="btn">New Page</a>
                <a href="/admin/uploads" class="btn">Upload File</a>
                <a href="/" class="btn" target="_blank">View Site</a>
            </div>
        </div>
        {ADMIN_FOOTER}
    </body>
    </html>
    """
    return HTMLResponse(html)

@router.get("/pages", response_class=HTMLResponse)
async def pages_list(
    request: Request,
    session=Depends(require_auth()),
):
    """Render pages list."""
    import html as _html
    from urllib.parse import quote as _quote

    from ..main import storage

    token, needs_cookie = get_csrf_token(request)
    pages = storage.get("pages", {})
    rows = "\n".join(
        f"<tr data-slug=\"{_html.escape(p.get('slug',''))}\" data-visibility=\"{_html.escape(p.get('visibility','show'))}\">"
        f"<td>{_html.escape(p.get('title',''))}</td>"
        f"<td>{_html.escape(p.get('slug',''))}</td>"
        f"<td class=\"visibility\">{_html.escape(p.get('visibility','show'))}</td>"
        f"<td><a href=\"/admin/pages/edit/{_quote(p.get('slug',''))}\">Edit</a></td>"
        f"<td><button class=\"btn toggle-btn\" type=\"button\">Toggle</button></td>"
        f"<td><button class=\"btn danger delete-btn\" data-slug=\"{_html.escape(p.get('slug',''))}\" type=\"button\">Delete</button></td></tr>"
        for p in pages.values()
    )
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pages - {CMS_NAME}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; background: #f5f5f5; }}
            .header {{ background: #1e293b; color: white; padding: 1rem 2rem; }}
            .header a {{ color: #94a3b8; text-decoration: none; }}
            .container {{ max-width: 1000px; margin: 2rem auto; padding: 0 1rem; }}
            table {{ width: 100%; border-collapse: collapse; background: white; }}
            th, td {{ padding: 0.75rem; border-bottom: 1px solid #e2e8f0; text-align: left; }}
            .actions {{ margin: 1rem 0; }}
            .btn {{ display: inline-block; padding: 0.5rem 1rem; background: #2563eb; color: white; border-radius: 6px; text-decoration: none; }}
            .btn.danger {{ background: #dc2626; border: none; cursor: pointer; }}
            .btn.toggle-btn {{ border: none; cursor: pointer; }}
            .error {{ color: #b91c1c; margin-bottom: 0.5rem; }}
        </style>
    </head>
    <body>
        <div class="header">
            <a href="/admin/">Dashboard</a>
        </div>
        <div class="container">
            <div class="actions">
                <a class="btn" href="/admin/pages/new">New Page</a>
            </div>
            <div id="msg" class="error"></div>
            <table>
                <thead>
                    <tr><th>Title</th><th>Slug</th><th>Status</th><th></th><th></th><th></th></tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        <script>
            const csrfToken = {token!r};
            document.querySelectorAll('.delete-btn').forEach((btn) => {{
                btn.addEventListener('click', async (e) => {{
                    const slug = e.target.dataset.slug;
                    if (slug === 'home' || slug === '404') {{
                        document.getElementById('msg').textContent = 'Cannot delete system page';
                        return;
                    }}
                    if (!confirm('Delete this page?')) return;
                    const res = await fetch(`/admin/api/pages/${{encodeURIComponent(slug)}}`, {{
                        method: 'DELETE',
                        headers: {{
                            'X-CSRF-Token': csrfToken,
                        }},
                        credentials: 'same-origin',
                    }});
                    if (!res.ok) {{
                        const text = await res.text();
                        document.getElementById('msg').textContent = text || 'Failed to delete page';
                        return;
                    }}
                    e.target.closest('tr').remove();
                }});
            }});
            document.querySelectorAll('.toggle-btn').forEach((btn) => {{
                btn.addEventListener('click', async (e) => {{
                    const row = e.target.closest('tr');
                    const slug = row.dataset.slug;
                    const current = row.dataset.visibility || 'show';
                    const next = current === 'show' ? 'hide' : 'show';
                    const res = await fetch(`/admin/api/pages/${{encodeURIComponent(slug)}}`, {{
                        method: 'PUT',
                        headers: {{
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': csrfToken,
                        }},
                        credentials: 'same-origin',
                        body: JSON.stringify({{ visibility: next }}),
                    }});
                    if (!res.ok) {{
                        const text = await res.text();
                        document.getElementById('msg').textContent = text || 'Failed to update status';
                        return;
                    }}
                    row.dataset.visibility = next;
                    row.querySelector('.visibility').textContent = next;
                }});
            }});
        </script>
        {ADMIN_FOOTER}
    </body>
    </html>
    """
    response = HTMLResponse(html)
    if needs_cookie:
        set_csrf_cookie(request, response, token)
    return response

@router.get("/logout")
async def logout(request: Request):
    """Handle logout and redirect to homepage."""
    from ..main import auth, audit_logger, storage

    session_id = request.cookies.get("session_id")
    if session_id and auth:
        session = auth.verify_session(session_id)
        if session:
            auth.invalidate_session(session.session_id)
            if audit_logger:
                audit_logger.log_logout(
                    session.user_id,
                    request.client.host if request.client else None,
                )

    response = RedirectResponse(url="/", status_code=303)
    secure_cookie = storage.get("config.force_https", True) if storage else True
    response.delete_cookie("session_id", secure=secure_cookie, samesite="lax")
    return response


@router.get("/pages/new", response_class=HTMLResponse)
async def page_new(
    request: Request,
    session=Depends(require_auth([Role.ADMIN, Role.EDITOR])),
):
    """Render new page form."""
    csrf_token, needs_cookie = get_csrf_token(request)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>New Page - {CMS_NAME}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; background: #f5f5f5; }}
            .header {{ background: #1e293b; color: white; padding: 1rem 2rem; }}
            .header a {{ color: #94a3b8; text-decoration: none; }}
            .container {{ max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
            label {{ display: block; margin: 0.5rem 0 0.25rem; }}
            input, textarea, select {{ width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 6px; }}
            textarea {{ min-height: 260px; }}
            .btn {{ padding: 0.6rem 1rem; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; }}
            .error {{ color: #b91c1c; }}
        </style>
    </head>
    <body>
        <div class="header">
            <a href="/admin/pages">Pages</a>
        </div>
        <div class="container">
            <h2>New Page</h2>
            <div id="msg" class="error"></div>
            <form id="page-form" method="post" action="/admin/pages/new">
                <input type="hidden" name="csrf_token" value="{csrf_token}">
                <label>Title</label>
                <input name="title" required>
                <label>Description</label>
                <input name="description">
                <label>Keywords</label>
                <input name="keywords">
                <label>Visibility</label>
                <select name="visibility">
                    <option value="show">Show</option>
                    <option value="hide">Hide</option>
                </select>
                <label>Content</label>
                <textarea name="content"></textarea>
                <button class="btn" type="submit">Create</button>
            </form>
        </div>
        <script>
            const csrfToken = {csrf_token!r};
            document.getElementById('page-form').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const form = e.target;
                const data = Object.fromEntries(new FormData(form).entries());
                const res = await fetch('/admin/api/pages', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken,
                    }},
                    credentials: 'same-origin',
                    body: JSON.stringify(data),
                }});
                if (!res.ok) {{
                    const text = await res.text();
                    document.getElementById('msg').textContent = text || 'Failed to create page';
                    return;
                }}
                const page = await res.json();
                window.location.href = `/admin/pages/edit/${{encodeURIComponent(page.slug)}}?created=1`;
            }});
        </script>
        {ADMIN_FOOTER}
    </body>
    </html>
    """
    response = HTMLResponse(html)
    if needs_cookie:
        set_csrf_cookie(request, response, csrf_token)
    return response


@router.get("/pages/edit/{slug}", response_class=HTMLResponse)
async def page_edit(
    slug: str,
    request: Request,
    session=Depends(require_auth([Role.ADMIN, Role.EDITOR])),
):
    """Render edit page form."""
    import html as _html

    from ..main import storage

    page = storage.get(f"pages.{slug}")
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    title = _html.escape(page.get("title", ""))
    description = _html.escape(page.get("description", ""))
    keywords = _html.escape(page.get("keywords", ""))
    content = _html.escape(page.get("content", ""))

    csrf_token, needs_cookie = get_csrf_token(request)
    created_msg = "Page created and saved." if request.query_params.get("created") == "1" else ""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Edit Page - {CMS_NAME}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; background: #f5f5f5; }}
            .header {{ background: #1e293b; color: white; padding: 1rem 2rem; }}
            .header a {{ color: #94a3b8; text-decoration: none; }}
            .container {{ max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
            label {{ display: block; margin: 0.5rem 0 0.25rem; }}
            input, textarea, select {{ width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 6px; }}
            textarea {{ min-height: 260px; }}
            .btn {{ padding: 0.6rem 1rem; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; }}
            .error {{ color: #b91c1c; }}
        </style>
    </head>
    <body>
        <div class="header">
            <a href="/admin/pages">Pages</a>
        </div>
        <div class="container">
            <h2>Edit Page: {title}</h2>
            <div id="msg" class="error">{created_msg}</div>
            <form id="page-form" method="post" action="/admin/pages/edit/{slug}">
                <input type="hidden" name="csrf_token" value="{csrf_token}">
                <label>Title</label>
                <input name="title" value="{title}" required>
                <label>Description</label>
                <input name="description" value="{description}">
                <label>Keywords</label>
                <input name="keywords" value="{keywords}">
                <label>Visibility</label>
                <select name="visibility">
                    <option value="show" {"selected" if page.get("visibility") == "show" else ""}>Show</option>
                    <option value="hide" {"selected" if page.get("visibility") == "hide" else ""}>Hide</option>
                </select>
                <label>Content</label>
                <textarea name="content">{content}</textarea>
                <button class="btn" type="submit">Save</button>
            </form>
        </div>
        <script>
            const csrfToken = {csrf_token!r};
            document.getElementById('page-form').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const form = e.target;
                const data = Object.fromEntries(new FormData(form).entries());
                const res = await fetch('/admin/api/pages/{slug}', {{
                    method: 'PUT',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken,
                    }},
                    credentials: 'same-origin',
                    body: JSON.stringify(data),
                }});
                if (!res.ok) {{
                    const text = await res.text();
                    document.getElementById('msg').textContent = text || 'Failed to update page';
                    return;
                }}
                window.location.href = '/admin/pages';
            }});
        </script>
        {ADMIN_FOOTER}
    </body>
    </html>
    """
    response = HTMLResponse(html)
    if needs_cookie:
        set_csrf_cookie(request, response, csrf_token)
    return response


@router.post("/pages/new")
async def page_new_submit(
    request: Request,
    session=Depends(require_auth([Role.ADMIN, Role.EDITOR])),
):
    """Handle new page form submission."""
    from ..main import storage, sanitizer, audit_logger

    form = await request.form()
    csrf_token = form.get("csrf_token", "")
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not csrf_cookie or not secrets.compare_digest(csrf_token, csrf_cookie):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    title = str(form.get("title", "Untitled")).strip()
    slug = sanitizer.slugify(title or "untitled")
    if storage.get(f"pages.{slug}"):
        raise HTTPException(status_code=409, detail="Page already exists")

    page = {
        "title": title or "Untitled",
        "slug": slug,
        "content": str(form.get("content", "")),
        "content_format": "markdown",
        "description": str(form.get("description", "")),
        "keywords": str(form.get("keywords", "")),
        "visibility": str(form.get("visibility", "show")),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "modified_at": datetime.now(timezone.utc).isoformat(),
        "modified_by": session.user_id,
    }

    storage.set(f"pages.{slug}", page)
    audit_logger.log(
        "page_create",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        {"slug": slug},
    )

    return RedirectResponse(url=f"/admin/pages/edit/{slug}?created=1", status_code=303)


@router.post("/pages/edit/{slug}")
async def page_edit_submit(
    slug: str,
    request: Request,
    session=Depends(require_auth([Role.ADMIN, Role.EDITOR])),
):
    """Handle edit page form submission."""
    from ..main import storage, audit_logger

    page = storage.get(f"pages.{slug}")
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    form = await request.form()
    csrf_token = form.get("csrf_token", "")
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_token or not csrf_cookie or not secrets.compare_digest(csrf_token, csrf_cookie):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    page["title"] = str(form.get("title", page.get("title", "")))
    page["content"] = str(form.get("content", page.get("content", "")))
    page["description"] = str(form.get("description", page.get("description", "")))
    page["keywords"] = str(form.get("keywords", page.get("keywords", "")))
    page["visibility"] = str(form.get("visibility", page.get("visibility", "show")))
    page["modified_at"] = datetime.now(timezone.utc).isoformat()
    page["modified_by"] = session.user_id

    storage.set(f"pages.{slug}", page)
    audit_logger.log(
        "page_update",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        {"slug": slug},
    )

    return RedirectResponse(url=f"/admin/pages/edit/{slug}", status_code=303)


@router.get("/uploads", response_class=HTMLResponse)
async def uploads_page(
    request: Request,
    session=Depends(require_auth([Role.ADMIN, Role.EDITOR])),
):
    """Render upload page."""
    import html as _html

    from ..main import storage

    uploads = storage.get("uploads", {})
    rows = "\n".join(
        f"<tr data-uuid=\"{_html.escape(u.get('uuid',''))}\">"
        f"<td><input class=\"name-input\" value=\"{_html.escape(u.get('original_name',''))}\"></td>"
        f"<td>{_html.escape(u.get('uuid',''))}</td>"
        f"<td><a href=\"/uploads/{u.get('uuid','')}\" target=\"_blank\">View</a></td>"
        f"<td><button class=\"btn save-btn\" type=\"button\">Save</button> "
        f"<button class=\"btn danger delete-btn\" type=\"button\">Delete</button></td>"
        f"</tr>"
        for u in uploads.values()
    )
    csrf_token, needs_cookie = get_csrf_token(request)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Uploads - {CMS_NAME}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; background: #f5f5f5; }}
            .header {{ background: #1e293b; color: white; padding: 1rem 2rem; }}
            .header a {{ color: #94a3b8; text-decoration: none; }}
            .container {{ max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
            table {{ width: 100%; border-collapse: collapse; background: white; margin-top: 1rem; }}
            th, td {{ padding: 0.75rem; border-bottom: 1px solid #e2e8f0; text-align: left; }}
            .btn {{ padding: 0.5rem 0.8rem; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; }}
            .btn.danger {{ background: #dc2626; }}
            .name-input {{ width: 100%; padding: 0.4rem; border: 1px solid #cbd5e1; border-radius: 6px; }}
            .error {{ color: #b91c1c; }}
        </style>
    </head>
    <body>
        <div class="header">
            <a href="/admin/">Dashboard</a>
        </div>
        <div class="container">
            <h2>Upload File</h2>
            <div id="msg" class="error"></div>
            <form id="upload-form">
                <input type="file" name="file" required>
                <button class="btn" type="submit">Upload</button>
            </form>
            <table>
                <thead>
                    <tr><th>Original Name</th><th>UUID</th><th>File</th><th>Actions</th></tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        <script>
            const csrfToken = {csrf_token!r};
            document.getElementById('upload-form').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const form = e.target;
                const data = new FormData(form);
                const res = await fetch('/admin/api/uploads', {{
                    method: 'POST',
                    headers: {{
                        'X-CSRF-Token': csrfToken,
                    }},
                    credentials: 'same-origin',
                    body: data,
                }});
                if (!res.ok) {{
                    const text = await res.text();
                    document.getElementById('msg').textContent = text || 'Failed to upload';
                    return;
                }}
                window.location.reload();
            }});
            document.querySelectorAll('.save-btn').forEach((btn) => {{
                btn.addEventListener('click', async (e) => {{
                    const row = e.target.closest('tr');
                    const uuid = row.dataset.uuid;
                    const name = row.querySelector('.name-input').value;
                    const res = await fetch(`/admin/api/uploads/${{encodeURIComponent(uuid)}}`, {{
                        method: 'PUT',
                        headers: {{
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': csrfToken,
                        }},
                        credentials: 'same-origin',
                        body: JSON.stringify({{ original_name: name }}),
                    }});
                    if (!res.ok) {{
                        const text = await res.text();
                        document.getElementById('msg').textContent = text || 'Failed to update';
                        return;
                    }}
                    document.getElementById('msg').textContent = 'Updated';
                }});
            }});
            document.querySelectorAll('.delete-btn').forEach((btn) => {{
                btn.addEventListener('click', async (e) => {{
                    if (!confirm('Delete this file?')) return;
                    const row = e.target.closest('tr');
                    const uuid = row.dataset.uuid;
                    const res = await fetch(`/admin/api/uploads/${{encodeURIComponent(uuid)}}`, {{
                        method: 'DELETE',
                        headers: {{
                            'X-CSRF-Token': csrfToken,
                        }},
                        credentials: 'same-origin',
                    }});
                    if (!res.ok) {{
                        const text = await res.text();
                        document.getElementById('msg').textContent = text || 'Failed to delete';
                        return;
                    }}
                    row.remove();
                }});
            }});
        </script>
        {ADMIN_FOOTER}
    </body>
    </html>
    """
    response = HTMLResponse(html)
    if needs_cookie:
        set_csrf_cookie(request, response, csrf_token)
    return response


@router.get("/blocks", response_class=HTMLResponse)
async def blocks_page(
    request: Request,
    session=Depends(require_auth([Role.ADMIN, Role.EDITOR])),
):
    """Render blocks editor."""
    import html as _html

    from ..main import storage

    blocks = storage.get("blocks", {})
    block_options = "\n".join(
        f"<option value=\"{_html.escape(name)}\">{_html.escape(name)}</option>"
        for name in blocks.keys()
    )
    csrf_token, needs_cookie = get_csrf_token(request)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Blocks - {CMS_NAME}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; background: #f5f5f5; }}
            .header {{ background: #1e293b; color: white; padding: 1rem 2rem; }}
            .header a {{ color: #94a3b8; text-decoration: none; }}
            .container {{ max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
            label {{ display: block; margin: 0.5rem 0 0.25rem; }}
            select, textarea {{ width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 6px; }}
            textarea {{ min-height: 240px; }}
            .btn {{ padding: 0.6rem 1rem; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; }}
            .error {{ color: #b91c1c; }}
        </style>
    </head>
    <body>
        <div class="header">
            <a href="/admin/">Dashboard</a>
        </div>
        <div class="container">
            <h2>Blocks</h2>
            <div id="msg" class="error"></div>
            <form id="block-form">
                <label>Block</label>
                <select name="name" id="block-name">
                    {block_options}
                </select>
                <label>Content</label>
                <textarea name="content" id="block-content"></textarea>
                <button class="btn" type="submit">Save</button>
            </form>
        </div>
        <script>
            const csrfToken = {csrf_token!r};
            async function loadBlock(name) {{
                const res = await fetch('/admin/api/blocks', {{ credentials: 'same-origin' }});
                const data = await res.json();
                const block = (data.blocks || {{}})[name] || {{}};
                document.getElementById('block-content').value = block.content || '';
            }}
            const select = document.getElementById('block-name');
            if (select.value) {{
                loadBlock(select.value);
            }}
            select.addEventListener('change', (e) => loadBlock(e.target.value));
            document.getElementById('block-form').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const name = select.value;
                const content = document.getElementById('block-content').value;
                const res = await fetch(`/admin/api/blocks/${{encodeURIComponent(name)}}`, {{
                    method: 'PUT',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken,
                    }},
                    credentials: 'same-origin',
                    body: JSON.stringify({{ content }}),
                }});
                if (!res.ok) {{
                    const text = await res.text();
                    document.getElementById('msg').textContent = text || 'Failed to save block';
                    return;
                }}
                document.getElementById('msg').textContent = 'Saved';
            }});
        </script>
        {ADMIN_FOOTER}
    </body>
    </html>
    """
    response = HTMLResponse(html)
    if needs_cookie:
        set_csrf_cookie(request, response, csrf_token)
    return response


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    session=Depends(require_auth([Role.ADMIN])),
):
    """Render settings page."""
    import html as _html

    from ..main import storage

    config = storage.get("config", {})
    csrf_token, needs_cookie = get_csrf_token(request)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Settings - {CMS_NAME}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; background: #f5f5f5; }}
            .header {{ background: #1e293b; color: white; padding: 1rem 2rem; }}
            .header a {{ color: #94a3b8; text-decoration: none; }}
            .container {{ max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
            label {{ display: block; margin: 0.5rem 0 0.25rem; }}
            input {{ width: 100%; padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 6px; }}
            .row {{ margin-bottom: 0.75rem; }}
            .btn {{ padding: 0.6rem 1rem; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; }}
            .error {{ color: #b91c1c; }}
        </style>
    </head>
    <body>
        <div class="header">
            <a href="/admin/">Dashboard</a>
        </div>
        <div class="container">
            <h2>Settings</h2>
            <div id="msg" class="error"></div>
            <form id="settings-form">
                <div class="row">
                    <label>Site Title</label>
                    <input name="site_title" value="{_html.escape(config.get('site_title',''))}">
                </div>
                <div class="row">
                    <label>Site Language</label>
                    <input name="site_lang" value="{_html.escape(config.get('site_lang','en'))}">
                </div>
                <div class="row">
                    <label>Theme</label>
                    <input name="theme" value="{_html.escape(config.get('theme','default'))}">
                </div>
                <div class="row">
                    <label>Default Page</label>
                    <input name="default_page" value="{_html.escape(config.get('default_page','home'))}">
                </div>
                <div class="row">
                    <label>Force HTTPS (true/false)</label>
                    <input name="force_https" value="{str(config.get('force_https', True)).lower()}">
                </div>
                <button class="btn" type="submit">Save</button>
            </form>
        </div>
        <script>
            const csrfToken = {csrf_token!r};
            document.getElementById('settings-form').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const data = Object.fromEntries(new FormData(e.target).entries());
                data.force_https = (data.force_https || '').toLowerCase() === 'true';
                const res = await fetch('/admin/api/settings', {{
                    method: 'PUT',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken,
                    }},
                    credentials: 'same-origin',
                    body: JSON.stringify(data),
                }});
                if (!res.ok) {{
                    const text = await res.text();
                    document.getElementById('msg').textContent = text || 'Failed to save settings';
                    return;
                }}
                document.getElementById('msg').textContent = 'Saved';
            }});
        </script>
        {ADMIN_FOOTER}
    </body>
    </html>
    """
    response = HTMLResponse(html)
    if needs_cookie:
        set_csrf_cookie(response, csrf_token)
    return response


# ============================================================================
# Menu Management
# ============================================================================

@router.get("/menu", response_class=HTMLResponse)
async def menu_page(
    request: Request,
    session=Depends(require_auth([Role.ADMIN, Role.EDITOR])),
):
    """Render menu management page."""
    import html as _html

    from ..main import storage

    menu_items = storage.get("menu_items", [])
    pages = storage.get("pages", {})

    # Sort menu items by order
    menu_items = sorted(menu_items, key=lambda x: x.get("order", 0))

    # Build table rows
    rows = ""
    for idx, item in enumerate(menu_items):
        visibility_show = "selected" if item.get("visibility") == "show" else ""
        visibility_hide = "selected" if item.get("visibility") == "hide" else ""
        rows += f"""
        <tr data-slug="{_html.escape(item.get('slug', ''))}">
            <td class="order-cell">{idx + 1}</td>
            <td><input class="name-input" value="{_html.escape(item.get('name', ''))}" style="width:100%;padding:0.4rem;border:1px solid #cbd5e1;border-radius:4px;"></td>
            <td>{_html.escape(item.get('slug', ''))}</td>
            <td>
                <select class="visibility-select" style="padding:0.4rem;border:1px solid #cbd5e1;border-radius:4px;">
                    <option value="show" {visibility_show}>Show</option>
                    <option value="hide" {visibility_hide}>Hide</option>
                </select>
            </td>
            <td>
                <button class="btn small up-btn" type="button">Up</button>
                <button class="btn small down-btn" type="button">Down</button>
                <button class="btn danger small delete-btn" type="button">Delete</button>
            </td>
        </tr>
        """

    # Build page options for add dropdown
    page_options = ""
    for slug, page in pages.items():
        # Check if page already in menu
        in_menu = any(m.get("slug") == slug for m in menu_items)
        if not in_menu:
            page_options += f'<option value="{_html.escape(slug)}">{_html.escape(page.get("title", slug))}</option>'

    csrf_token, needs_cookie = get_csrf_token(request)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Menu - {CMS_NAME}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: system-ui, sans-serif; margin: 0; background: #f5f5f5; }}
            .header {{ background: #1e293b; color: white; padding: 1rem 2rem; }}
            .header a {{ color: #94a3b8; text-decoration: none; }}
            .container {{ max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
            table {{ width: 100%; border-collapse: collapse; background: white; margin-top: 1rem; }}
            th, td {{ padding: 0.75rem; border-bottom: 1px solid #e2e8f0; text-align: left; }}
            th {{ background: #f8fafc; font-weight: 600; color: #475569; }}
            .btn {{ padding: 0.5rem 0.8rem; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; }}
            .btn:hover {{ background: #1d4ed8; }}
            .btn.danger {{ background: #dc2626; }}
            .btn.danger:hover {{ background: #b91c1c; }}
            .btn.small {{ padding: 0.3rem 0.6rem; font-size: 0.85rem; }}
            .btn.secondary {{ background: #64748b; }}
            .add-form {{ background: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; display: flex; gap: 0.5rem; align-items: center; }}
            .add-form select {{ padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 6px; min-width: 200px; }}
            .add-form input {{ padding: 0.5rem; border: 1px solid #cbd5e1; border-radius: 6px; }}
            .msg {{ padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; }}
            .msg.error {{ background: #fef2f2; color: #b91c1c; }}
            .msg.success {{ background: #f0fdf4; color: #166534; }}
            .order-cell {{ width: 50px; text-align: center; color: #64748b; }}
            .actions {{ margin-top: 1rem; }}
        </style>
    </head>
    <body>
        <div class="header">
            <a href="/admin/">Dashboard</a>
        </div>
        <div class="container">
            <h2>Menu Management</h2>
            <div id="msg"></div>

            <div class="add-form">
                <label>Add Page to Menu:</label>
                <select id="add-page">
                    <option value="">-- Select Page --</option>
                    {page_options}
                </select>
                <input type="text" id="add-name" placeholder="Display Name (optional)">
                <button class="btn" id="add-btn" type="button">Add</button>
            </div>

            <table id="menu-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Display Name</th>
                        <th>Page (slug)</th>
                        <th>Visibility</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>

            <div class="actions">
                <button class="btn" id="save-btn" type="button">Save Menu</button>
            </div>
        </div>
        <script>
            const csrfToken = {csrf_token!r};

            function showMsg(text, isError) {{
                const msg = document.getElementById('msg');
                msg.textContent = text;
                msg.className = 'msg ' + (isError ? 'error' : 'success');
                setTimeout(() => {{ msg.textContent = ''; msg.className = ''; }}, 3000);
            }}

            function updateOrder() {{
                const rows = document.querySelectorAll('#menu-table tbody tr');
                rows.forEach((row, idx) => {{
                    row.querySelector('.order-cell').textContent = idx + 1;
                }});
            }}

            // Add new menu item
            document.getElementById('add-btn').addEventListener('click', async () => {{
                const pageSelect = document.getElementById('add-page');
                const nameInput = document.getElementById('add-name');
                const slug = pageSelect.value;
                if (!slug) {{
                    showMsg('Please select a page', true);
                    return;
                }}
                const name = nameInput.value.trim() || pageSelect.options[pageSelect.selectedIndex].text;

                const res = await fetch('/admin/api/menu', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken,
                    }},
                    credentials: 'same-origin',
                    body: JSON.stringify({{ slug, name }}),
                }});

                if (!res.ok) {{
                    const text = await res.text();
                    showMsg(text || 'Failed to add item', true);
                    return;
                }}

                window.location.reload();
            }});

            // Move up
            document.querySelectorAll('.up-btn').forEach(btn => {{
                btn.addEventListener('click', (e) => {{
                    const row = e.target.closest('tr');
                    const prev = row.previousElementSibling;
                    if (prev) {{
                        row.parentNode.insertBefore(row, prev);
                        updateOrder();
                    }}
                }});
            }});

            // Move down
            document.querySelectorAll('.down-btn').forEach(btn => {{
                btn.addEventListener('click', (e) => {{
                    const row = e.target.closest('tr');
                    const next = row.nextElementSibling;
                    if (next) {{
                        row.parentNode.insertBefore(next, row);
                        updateOrder();
                    }}
                }});
            }});

            // Delete
            document.querySelectorAll('.delete-btn').forEach(btn => {{
                btn.addEventListener('click', async (e) => {{
                    if (!confirm('Remove this item from menu?')) return;
                    const row = e.target.closest('tr');
                    const slug = row.dataset.slug;

                    const res = await fetch(`/admin/api/menu/${{encodeURIComponent(slug)}}`, {{
                        method: 'DELETE',
                        headers: {{ 'X-CSRF-Token': csrfToken }},
                        credentials: 'same-origin',
                    }});

                    if (!res.ok) {{
                        const text = await res.text();
                        showMsg(text || 'Failed to delete', true);
                        return;
                    }}

                    row.remove();
                    updateOrder();
                    showMsg('Item removed', false);
                }});
            }});

            // Save all
            document.getElementById('save-btn').addEventListener('click', async () => {{
                const rows = document.querySelectorAll('#menu-table tbody tr');
                const items = [];
                rows.forEach((row, idx) => {{
                    items.push({{
                        slug: row.dataset.slug,
                        name: row.querySelector('.name-input').value,
                        visibility: row.querySelector('.visibility-select').value,
                        order: idx,
                    }});
                }});

                const res = await fetch('/admin/api/menu', {{
                    method: 'PUT',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken,
                    }},
                    credentials: 'same-origin',
                    body: JSON.stringify({{ items }}),
                }});

                if (!res.ok) {{
                    const text = await res.text();
                    showMsg(text || 'Failed to save menu', true);
                    return;
                }}

                showMsg('Menu saved successfully', false);
            }});
        </script>
        {ADMIN_FOOTER}
    </body>
    </html>
    """
    response = HTMLResponse(html)
    if needs_cookie:
        set_csrf_cookie(request, response, csrf_token)
    return response


# ============================================================================
# Menu API
# ============================================================================

@router.get("/api/menu")
async def list_menu(
    session=Depends(require_auth()),
):
    """List all menu items."""
    from ..main import storage

    menu_items = storage.get("menu_items", [])
    return {"items": menu_items}


@router.post("/api/menu")
async def add_menu_item(
    request: Request,
    session=Depends(require_auth([Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Add a new menu item."""
    from ..main import storage, audit_logger

    data = await request.json()
    slug = data.get("slug", "").strip()
    name = data.get("name", "").strip()

    if not slug:
        raise HTTPException(status_code=400, detail="Slug is required")

    # Check page exists
    page = storage.get(f"pages.{slug}")
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Get current menu
    menu_items = storage.get("menu_items", [])

    # Check if already in menu
    if any(m.get("slug") == slug for m in menu_items):
        raise HTTPException(status_code=409, detail="Page already in menu")

    # Add new item
    new_item = {
        "name": name or page.get("title", slug),
        "slug": slug,
        "visibility": "show",
        "order": len(menu_items),
    }
    menu_items.append(new_item)
    storage.set("menu_items", menu_items)

    audit_logger.log(
        "menu_add",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        {"slug": slug},
    )

    return new_item


@router.put("/api/menu")
async def update_menu(
    request: Request,
    session=Depends(require_auth([Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Update entire menu (bulk update)."""
    from ..main import storage, audit_logger

    data = await request.json()
    items = data.get("items", [])

    # Validate and rebuild menu
    new_menu = []
    for idx, item in enumerate(items):
        slug = item.get("slug", "").strip()
        if not slug:
            continue
        new_menu.append({
            "name": item.get("name", slug),
            "slug": slug,
            "visibility": item.get("visibility", "show"),
            "order": idx,
        })

    storage.set("menu_items", new_menu)

    audit_logger.log(
        "menu_update",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        {"count": len(new_menu)},
    )

    return {"items": new_menu}


@router.delete("/api/menu/{slug}")
async def delete_menu_item(
    slug: str,
    request: Request,
    session=Depends(require_auth([Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Delete a menu item."""
    from ..main import storage, audit_logger

    menu_items = storage.get("menu_items", [])

    # Find and remove item
    new_menu = [m for m in menu_items if m.get("slug") != slug]

    if len(new_menu) == len(menu_items):
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Update order
    for idx, item in enumerate(new_menu):
        item["order"] = idx

    storage.set("menu_items", new_menu)

    audit_logger.log(
        "menu_delete",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        {"slug": slug},
    )

    return {"status": "deleted", "slug": slug}


# ============================================================================
# Pages API
# ============================================================================

@router.get("/api/pages")
async def list_pages(
    session=Depends(require_auth()),
):
    """List all pages."""
    from ..main import storage

    pages = storage.get("pages", {})
    return {"pages": list(pages.values())}


@router.get("/api/pages/{slug}")
async def get_page(
    slug: str,
    session=Depends(require_auth()),
):
    """Get a single page."""
    from ..main import storage

    page = storage.get(f"pages.{slug}")
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    return page


@router.post("/api/pages")
async def create_page(
    request: Request,
    session=Depends(require_auth([Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Create a new page."""
    from ..main import storage, sanitizer, audit_logger

    data = await request.json()

    slug = sanitizer.slugify(data.get("title", "untitled"))

    # Check if slug exists
    if storage.get(f"pages.{slug}"):
        raise HTTPException(status_code=409, detail="Page already exists")

    page = {
        "title": data.get("title", "Untitled"),
        "slug": slug,
        "content": data.get("content", ""),
        "content_format": "markdown",
        "description": data.get("description", ""),
        "keywords": data.get("keywords", ""),
        "visibility": data.get("visibility", "show"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "modified_at": datetime.now(timezone.utc).isoformat(),
        "modified_by": session.user_id,
    }

    storage.set(f"pages.{slug}", page)

    audit_logger.log(
        "page_create",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        {"slug": slug},
    )

    return page


@router.put("/api/pages/{slug}")
async def update_page(
    slug: str,
    request: Request,
    session=Depends(require_auth([Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Update a page."""
    from ..main import storage, sanitizer, audit_logger

    page = storage.get(f"pages.{slug}")
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    data = await request.json()

    # Update fields
    page["title"] = data.get("title", page["title"])
    page["content"] = data.get("content", page["content"])
    page["description"] = data.get("description", page.get("description", ""))
    page["keywords"] = data.get("keywords", page.get("keywords", ""))
    page["visibility"] = data.get("visibility", page.get("visibility", "show"))
    page["modified_at"] = datetime.now(timezone.utc).isoformat()
    page["modified_by"] = session.user_id

    storage.set(f"pages.{slug}", page)

    audit_logger.log(
        "page_update",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        {"slug": slug},
    )

    return page


@router.delete("/api/pages/{slug}")
async def delete_page(
    slug: str,
    request: Request,
    session=Depends(require_auth([Role.ADMIN])),
    _=Depends(require_csrf),
):
    """Delete a page."""
    from ..main import storage, audit_logger

    page = storage.get(f"pages.{slug}")
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Don't allow deleting system pages
    if slug in ("home", "404"):
        raise HTTPException(status_code=400, detail="Cannot delete system page")

    storage.delete(f"pages.{slug}")

    audit_logger.log(
        "page_delete",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        {"slug": slug},
    )

    return {"status": "deleted", "slug": slug}


# ============================================================================
# Blocks API
# ============================================================================

@router.get("/api/blocks")
async def list_blocks(
    session=Depends(require_auth()),
):
    """List all blocks."""
    from ..main import storage

    blocks = storage.get("blocks", {})
    return {"blocks": blocks}


@router.put("/api/blocks/{name}")
async def update_block(
    name: str,
    request: Request,
    session=Depends(require_auth([Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Update a block."""
    from ..main import storage, audit_logger

    data = await request.json()

    block = {
        "content": data.get("content", ""),
        "content_format": "markdown",
    }

    storage.set(f"blocks.{name}", block)

    audit_logger.log(
        "block_update",
        session.user_id,
        request.client.host if request.client else None,
        {"name": name},
    )

    return block


# ============================================================================
# Upload API (Secure)
# ============================================================================

def validate_file_magic_bytes(content: bytes, extension: str) -> bool:
    """Validate file content matches expected magic bytes where applicable."""
    expected = MAGIC_BYTES.get(extension.lower())
    if not expected:
        # No magic bytes defined (e.g., txt) - allow
        return True

    if extension.lower() == "webp":
        # WebP has RIFF header at start and WEBP at offset 8
        return content[:4] == b"RIFF" and content[8:12] == b"WEBP"

    return content.startswith(expected)


@router.get("/api/uploads")
async def list_uploads(
    session=Depends(require_auth()),
):
    """List all uploads."""
    from ..main import storage

    uploads = storage.get("uploads", {})
    return {"uploads": uploads}


@router.post("/api/uploads")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    session=Depends(require_auth([Role.ADMIN, Role.EDITOR])),
):
    """Upload a file."""
    import io
    import mimetypes

    from ..main import storage, app_config, audit_logger, sanitizer

    # Check Content-Length header before reading (DoS prevention)
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum: {MAX_UPLOAD_SIZE // (1024*1024)}MB"
                )
        except ValueError:
            pass  # Invalid Content-Length, continue and check actual size

    # Verify CSRF from header
    csrf_header = request.headers.get("X-CSRF-Token", "")
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_header or not secrets.compare_digest(csrf_header, csrf_cookie):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Sanitize filename FIRST before any other operations
    filename = sanitizer.sanitize_filename(file.filename)
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Check extension AFTER sanitization
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read content (with size limit)
    content = await file.read()

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum: {MAX_UPLOAD_SIZE // (1024*1024)}MB",
        )

    # Validate magic bytes when applicable
    if not validate_file_magic_bytes(content, extension):
        raise HTTPException(
            status_code=400,
            detail="File content does not match extension",
        )

    # Re-encode images to strip any hidden payloads
    if extension in IMAGE_EXTENSIONS:
        from PIL import Image

        try:
            img = Image.open(io.BytesIO(content))

            # Preserve ICC color profile if present
            icc_profile = img.info.get('icc_profile')

            # Strip EXIF and other metadata by creating a new image
            if img.mode in ('RGBA', 'LA', 'P'):
                # Handle images with alpha channel or palette
                clean_img = Image.new(img.mode, img.size)
                clean_img.putdata(list(img.getdata()))
            else:
                # For RGB/L modes
                clean_img = Image.new(img.mode, img.size)
                clean_img.putdata(list(img.getdata()))

            # Save to buffer
            output = io.BytesIO()

            # Map extension to PIL format
            pil_format = {
                "png": "PNG",
                "jpg": "JPEG",
                "jpeg": "JPEG",
                "webp": "WEBP",
                "gif": "GIF",
            }.get(extension, "PNG")

            # Prepare save options
            save_kwargs = {"format": pil_format}

            # Preserve ICC profile for color accuracy
            if icc_profile:
                save_kwargs["icc_profile"] = icc_profile

            # Use quality setting for JPEG/WEBP
            if pil_format in ("JPEG", "WEBP"):
                save_kwargs["quality"] = 90

            clean_img.save(output, **save_kwargs)
            content = output.getvalue()

        except Image.UnidentifiedImageError:
            raise HTTPException(
                status_code=400,
                detail="Cannot identify image file",
            )
        except IOError:
            raise HTTPException(
                status_code=400,
                detail="Error processing image file",
            )
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid image file",
            )

    # Generate UUID filename
    file_uuid = str(uuid.uuid4())
    safe_filename = f"{file_uuid}.{extension}"

    # Save file
    uploads_dir = app_config.uploads_dir
    uploads_dir.mkdir(parents=True, exist_ok=True)

    file_path = uploads_dir / safe_filename
    with open(file_path, "wb") as f:
        f.write(content)

    # Record in database
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    upload_record = {
        "uuid": file_uuid,
        "original_name": filename,
        "mime_type": mime_type,
        "size": len(content),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "uploaded_by": session.user_id,
    }

    storage.set(f"uploads.{file_uuid}", upload_record)

    audit_logger.log(
        "upload",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        {"uuid": file_uuid, "original_name": filename},
    )

    return {
        "uuid": file_uuid,
        "url": f"/uploads/{file_uuid}",
        "original_name": filename,
        "size": len(content),
    }


@router.put("/api/uploads/{file_uuid}")
async def update_upload(
    file_uuid: str,
    request: Request,
    session=Depends(require_auth([Role.ADMIN, Role.EDITOR])),
    _=Depends(require_csrf),
):
    """Update upload metadata."""
    from ..main import storage, audit_logger

    upload = storage.get(f"uploads.{file_uuid}")
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    data = await request.json()
    new_name = str(data.get("original_name", "")).strip()
    if new_name:
        upload["original_name"] = new_name
    storage.set(f"uploads.{file_uuid}", upload)

    audit_logger.log(
        "upload_update",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        {"uuid": file_uuid},
    )

    return upload


@router.delete("/api/uploads/{file_uuid}")
async def delete_upload(
    file_uuid: str,
    request: Request,
    session=Depends(require_auth([Role.ADMIN])),
    _=Depends(require_csrf),
):
    """Delete an uploaded file."""
    from ..main import storage, app_config, audit_logger

    upload = storage.get(f"uploads.{file_uuid}")
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Delete file
    extension = upload.get("mime_type", "").split("/")[-1]
    file_path = app_config.uploads_dir / f"{file_uuid}.{extension}"

    if file_path.exists():
        file_path.unlink()

    # Remove from database
    storage.delete(f"uploads.{file_uuid}")

    audit_logger.log(
        "upload_delete",
        session.user_id,
        request.client.host if request.client else None,
        request.headers.get("user-agent", ""),
        {"uuid": file_uuid},
    )

    return {"status": "deleted", "uuid": file_uuid}


# ============================================================================
# Settings API
# ============================================================================

@router.get("/api/settings")
async def get_settings(
    session=Depends(require_auth([Role.ADMIN])),
):
    """Get site settings."""
    from ..main import storage

    config = storage.get("config", {})

    # Don't expose sensitive data
    return {
        "site_title": config.get("site_title", ""),
        "site_lang": config.get("site_lang", "en"),
        "theme": config.get("theme", "default"),
        "default_page": config.get("default_page", "home"),
        "force_https": config.get("force_https", True),
    }


@router.put("/api/settings")
async def update_settings(
    request: Request,
    session=Depends(require_auth([Role.ADMIN])),
    _=Depends(require_csrf),
):
    """Update site settings."""
    from ..main import storage, audit_logger

    data = await request.json()

    # Update allowed settings only
    allowed_keys = {"site_title", "site_lang", "theme", "default_page", "force_https"}

    for key, value in data.items():
        if key in allowed_keys:
            storage.set(f"config.{key}", value)

    audit_logger.log(
        "settings_update",
        session.user_id,
        request.client.host if request.client else None,
        {"keys": list(data.keys())},
    )

    return await get_settings(session)


# ============================================================================
# Plugins API
# ============================================================================

@router.get("/api/plugins")
async def list_plugins(
    session=Depends(require_auth([Role.ADMIN])),
):
    """List all plugins."""
    from ..main import plugin_manager

    plugins = plugin_manager.discover_plugins()
    return {
        "plugins": [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "author": p.author,
                "enabled": p.enabled,
                "directory": p.directory,
            }
            for p in plugins
        ]
    }


@router.post("/api/plugins/{name}/enable")
async def enable_plugin(
    name: str,
    request: Request,
    session=Depends(require_auth([Role.ADMIN])),
    _=Depends(require_csrf),
):
    """Enable a plugin."""
    from ..main import plugin_manager, storage, audit_logger

    try:
        plugin_manager.enable_plugin(name)

        # Update disabled list in storage
        disabled = set(storage.get("config.disabled_plugins", []))
        disabled.discard(name)
        storage.set("config.disabled_plugins", list(disabled))

        audit_logger.log(
            "plugin_enable",
            session.user_id,
            request.client.host if request.client else None,
            {"plugin": name},
        )

        return {"status": "enabled", "plugin": name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/plugins/{name}/disable")
async def disable_plugin(
    name: str,
    request: Request,
    session=Depends(require_auth([Role.ADMIN])),
    _=Depends(require_csrf),
):
    """Disable a plugin."""
    from ..main import plugin_manager, storage, audit_logger

    plugin_manager.disable_plugin(name)

    # Update disabled list in storage
    disabled = set(storage.get("config.disabled_plugins", []))
    disabled.add(name)
    storage.set("config.disabled_plugins", list(disabled))

    audit_logger.log(
        "plugin_disable",
        session.user_id,
        request.client.host if request.client else None,
        {"plugin": name},
    )

    return {"status": "disabled", "plugin": name}


# ============================================================================
# Themes API
# ============================================================================

@router.get("/api/themes")
async def list_themes(
    session=Depends(require_auth([Role.ADMIN])),
):
    """List all themes."""
    from ..main import theme_manager, storage

    themes = theme_manager.list_themes()
    active = storage.get("config.theme", "default")

    return {
        "themes": [
            {
                "name": t.name,
                "version": t.version,
                "description": t.description,
                "author": t.author,
                "active": t.name == active,
            }
            for t in themes
        ],
        "active": active,
    }


@router.put("/api/themes/active")
async def set_active_theme(
    request: Request,
    session=Depends(require_auth([Role.ADMIN])),
    _=Depends(require_csrf),
):
    """Set active theme."""
    from ..main import theme_manager, storage, audit_logger

    data = await request.json()
    theme_name = data.get("theme")

    if not theme_name:
        raise HTTPException(status_code=400, detail="Theme name required")

    # Check theme exists
    themes = theme_manager.list_themes()
    if not any(t.name == theme_name for t in themes):
        raise HTTPException(status_code=404, detail="Theme not found")

    storage.set("config.theme", theme_name)
    theme_manager.set_active_theme(theme_name)

    audit_logger.log(
        "theme_change",
        session.user_id,
        request.client.host if request.client else None,
        {"theme": theme_name},
    )

    return {"status": "changed", "theme": theme_name}


# ============================================================================
# Backup API
# ============================================================================

@router.post("/api/backup")
async def create_backup(
    request: Request,
    session=Depends(require_auth([Role.ADMIN])),
    _=Depends(require_csrf),
):
    """Create a backup."""
    import zipfile
    from ..main import app_config, audit_logger

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_name = f"pressassist_backup_{timestamp}.zip"
    backup_path = app_config.backups_dir / backup_name

    app_config.backups_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add database
        zf.write(app_config.db_path, "db.json")

        # Add uploads
        if app_config.uploads_dir.exists():
            for file in app_config.uploads_dir.iterdir():
                if file.is_file():
                    zf.write(file, f"uploads/{file.name}")

    audit_logger.log(
        "backup_create",
        session.user_id,
        request.client.host if request.client else None,
        {"file": backup_name},
    )

    return {"status": "created", "file": backup_name}


@router.get("/api/backups")
async def list_backups(
    session=Depends(require_auth([Role.ADMIN])),
):
    """List all backups."""
    from ..main import app_config

    backups = []
    if app_config.backups_dir.exists():
        for f in sorted(app_config.backups_dir.iterdir(), reverse=True):
            if f.suffix == ".zip":
                backups.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "created": f.stat().st_mtime,
                })

    return {"backups": backups}


# ============================================================================
# Audit Log API
# ============================================================================

@router.get("/api/audit-log")
async def get_audit_log(
    session=Depends(require_auth([Role.ADMIN])),
    limit: int = 100,
):
    """Get recent audit log entries."""
    from ..main import audit_logger

    entries = audit_logger.get_recent(limit)
    return {"entries": entries}
