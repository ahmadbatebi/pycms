"""Admin API routes for PressAssistCMS."""

import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

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

# Allowed upload extensions (very restrictive for security)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

# Maximum upload size: 5MB
MAX_UPLOAD_SIZE = 5 * 1024 * 1024

# Magic bytes for image validation
MAGIC_BYTES = {
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
    "webp": b"RIFF",
    "gif": b"GIF8",
}

router = APIRouter(prefix="/admin", tags=["admin"])


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

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Dashboard - PressAssistCMS</title>
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
            <h1>PressAssistCMS</h1>
            <div>
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
    </body>
    </html>
    """
    return HTMLResponse(html)


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

def validate_image_magic_bytes(content: bytes, extension: str) -> bool:
    """Validate file content matches expected magic bytes."""
    expected = MAGIC_BYTES.get(extension.lower())
    if not expected:
        return False

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
    """Upload a file (images only)."""
    from PIL import Image
    import io

    from ..main import storage, app_config, audit_logger, sanitizer

    # Verify CSRF from header
    csrf_header = request.headers.get("X-CSRF-Token", "")
    csrf_cookie = request.cookies.get("csrf_token", "")
    if not csrf_header or not secrets.compare_digest(csrf_header, csrf_cookie):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Check extension
    filename = sanitizer.sanitize_filename(file.filename)
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

    # Validate magic bytes
    if not validate_image_magic_bytes(content, extension):
        raise HTTPException(
            status_code=400,
            detail="File content does not match extension",
        )

    # Re-encode image to strip any hidden payloads
    try:
        img = Image.open(io.BytesIO(content))

        # Strip EXIF and other metadata
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

        clean_img.save(output, format=pil_format)
        content = output.getvalue()

    except Exception as e:
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
    upload_record = {
        "uuid": file_uuid,
        "original_name": filename,
        "mime_type": f"image/{extension}",
        "size": len(content),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "uploaded_by": session.user_id,
    }

    storage.set(f"uploads.{file_uuid}", upload_record)

    audit_logger.log(
        "upload",
        session.user_id,
        request.client.host if request.client else None,
        {"uuid": file_uuid, "original_name": filename},
    )

    return {
        "uuid": file_uuid,
        "url": f"/uploads/{file_uuid}",
        "original_name": filename,
        "size": len(content),
    }


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
