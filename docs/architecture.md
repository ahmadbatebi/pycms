# PressAssistCMS Architecture

## 1. High-Level Overview

```
                    +------------------+
                    |    Internet      |
                    +--------+---------+
                             |
                    +--------v---------+
                    |  Reverse Proxy   |
                    |  (nginx/Caddy)   |
                    +--------+---------+
                             |
                    +--------v---------+
                    |    Uvicorn       |
                    |   ASGI Server    |
                    +--------+---------+
                             |
        +--------------------+--------------------+
        |                    |                    |
+-------v-------+    +-------v-------+    +-------v-------+
|   FastAPI     |    |    Jinja2     |    |    Static     |
|   Routes      |    |   Templates   |    |    Files      |
+-------+-------+    +-------+-------+    +---------------+
        |                    |
        +--------------------+
                    |
        +-----------+-----------+
        |           |           |
+-------v---+ +-----v-----+ +---v-------+
|   Core    | |  Plugins  | |  Themes   |
|  Engine   | |  System   | |  System   |
+-----------+ +-----------+ +-----------+
        |
+-------v---------+
|  JSON Storage   |
|  (data/db.json) |
+-----------------+
```

## 2. Directory Structure

```
press-assist-project/
├── README.md
├── pyproject.toml
├── .gitignore
├── pressassist/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry
│   ├── cli.py               # CLI commands
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # App configuration
│   │   ├── storage.py       # JSON database operations
│   │   ├── auth.py          # Authentication & authorization
│   │   ├── csrf.py          # CSRF protection
│   │   ├── security_headers.py
│   │   ├── hooks.py         # Event system
│   │   ├── themes.py        # Theme loader
│   │   ├── plugins.py       # Plugin loader
│   │   ├── sanitize.py      # HTML/content sanitization
│   │   ├── models.py        # Pydantic models
│   │   ├── audit_log.py     # Security logging
│   │   └── i18n.py          # Internationalization
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── routes.py        # Admin API routes
│   │   ├── templates/       # Admin panel templates
│   │   └── static/          # Admin assets
│   └── public/
│       ├── __init__.py
│       ├── routes.py        # Public page routes
│       ├── templates/       # Fallback templates
│       └── static/          # Core static files
├── themes/
│   └── default/
│       ├── templates/
│       │   ├── base.html
│       │   ├── page.html
│       │   └── 404.html
│       ├── static/
│       │   └── css/
│       │       └── style.css
│       └── theme.json
├── plugins/
│   ├── example_hello/
│   │   ├── plugin.json
│   │   └── plugin.py
│   └── ai_placeholder/
│       ├── plugin.json
│       └── plugin.py
├── data/
│   ├── db.json              # Main database
│   ├── audit.log            # Audit log
│   ├── uploads/             # Uploaded files
│   └── backups/             # Backup archives
├── tests/
│   ├── test_auth.py
│   ├── test_csrf.py
│   ├── test_sanitize.py
│   ├── test_uploads.py
│   └── test_plugin_installer.py
└── docs/
    ├── wondercms_analysis.md
    ├── parity_matrix.md
    ├── threat_model.md
    ├── SECURITY.md
    └── architecture.md
```

## 3. Module Responsibilities

### 3.1 Core Modules

#### storage.py
```python
class Storage:
    """Atomic JSON database operations."""

    def __init__(self, db_path: Path)
    def load() -> dict
    def save(data: dict) -> None  # Atomic write with lock
    def get(path: str) -> Any     # Dot notation: "config.siteTitle"
    def set(path: str, value: Any) -> None
    def delete(path: str) -> None
```

#### auth.py
```python
class AuthManager:
    """Authentication and authorization."""

    def hash_password(password: str) -> str
    def verify_password(password: str, hash: str) -> bool
    def create_session(user_id: str, role: str) -> str
    def verify_session(token: str) -> Optional[Session]
    def check_permission(role: str, action: str) -> bool
    def rate_limit_check(ip: str) -> bool
```

#### hooks.py
```python
class HookManager:
    """Event-driven plugin integration."""

    def register(event: str, callback: Callable, priority: int = 50)
    def emit(event: str, payload: Any) -> Any

    # Events:
    # - page_render, page_save, page_delete
    # - menu_render, block_render
    # - css_inject, js_inject
    # - login_success, login_failed
    # - upload_before, upload_after
```

#### sanitize.py
```python
class Sanitizer:
    """Content sanitization."""

    def sanitize_html(content: str) -> str
    def render_markdown(content: str) -> str
    def sanitize_filename(name: str) -> str
    def validate_path(path: Path, base: Path) -> bool
```

### 3.2 Admin Module

#### routes.py
```python
# Admin API endpoints
POST   /admin/login
POST   /admin/logout
GET    /admin/dashboard
GET    /admin/pages
POST   /admin/pages
PUT    /admin/pages/{slug}
DELETE /admin/pages/{slug}
GET    /admin/blocks
PUT    /admin/blocks/{name}
POST   /admin/upload
DELETE /admin/upload/{id}
GET    /admin/settings
PUT    /admin/settings
GET    /admin/plugins
POST   /admin/plugins/{name}/enable
POST   /admin/plugins/{name}/disable
GET    /admin/themes
PUT    /admin/themes/active
POST   /admin/backup
POST   /admin/restore
GET    /admin/audit-log
```

### 3.3 Public Module

#### routes.py
```python
# Public page routes
GET    /                    # Default page
GET    /{slug}              # Page by slug
GET    /{parent}/{slug}     # Nested page
GET    /{login_slug}        # Login page (secret URL)
GET    /uploads/{uuid}      # Secure file serving
```

## 4. Data Flow

### 4.1 Page Request Flow

```
Request: GET /about
    │
    ▼
┌─────────────────┐
│ security_headers │ Add security headers
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Rate Limiter  │ Check request limits
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  public/routes  │ Route to handler
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Storage      │ Load page data
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Hooks       │ emit('page_render', page)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Sanitize     │ Render markdown
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Themes       │ Load active theme
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Jinja2       │ Render template
└────────┬────────┘
         │
         ▼
Response: HTML
```

### 4.2 Admin Save Flow

```
Request: PUT /admin/pages/about
    │
    ▼
┌─────────────────┐
│   CSRF Check    │ Verify token
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Auth Check    │ Verify session + role
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Validate     │ Pydantic model
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Sanitize     │ Clean content
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Hooks       │ emit('page_save', page)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Storage      │ Atomic save
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Audit Log     │ Log change
└────────┬────────┘
         │
         ▼
Response: JSON
```

### 4.3 Upload Flow

```
Request: POST /admin/upload (multipart)
    │
    ▼
┌─────────────────┐
│   Auth + CSRF   │ Verify permissions
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Size Check     │ Max 5MB
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Extension Check │ Allowlist only
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Magic Bytes     │ Verify actual type
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Image Re-encode │ Strip payloads
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ UUID Filename   │ Generate safe name
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Save File      │ To uploads/
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Audit Log      │ Log upload
└────────┬────────┘
         │
         ▼
Response: JSON {uuid, url}
```

## 5. Database Schema

### 5.1 Main Database (data/db.json)

```json
{
  "config": {
    "siteTitle": "My Website",
    "siteLang": "en",
    "adminLang": "en",
    "theme": "default",
    "defaultPage": "home",
    "loginSlug": "abc123...",  // 32-char random
    "forceHttps": true,
    "users": {
      "admin": {
        "passwordHash": "$2b$12$...",
        "role": "admin",
        "createdAt": "2026-01-04T00:00:00Z"
      }
    },
    "disabledPlugins": [],
    "lastModified": "2026-01-04T00:00:00Z"
  },
  "pages": {
    "home": {
      "title": "Home",
      "slug": "home",
      "content": "# Welcome\n\nThis is your homepage.",
      "contentFormat": "markdown",
      "description": "Homepage description",
      "keywords": "home, welcome",
      "visibility": "show",
      "subpages": {},
      "createdAt": "2026-01-04T00:00:00Z",
      "modifiedAt": "2026-01-04T00:00:00Z",
      "modifiedBy": "admin"
    },
    "404": {
      "title": "Page Not Found",
      "content": "# 404\n\nPage not found.",
      "contentFormat": "markdown",
      "visibility": "system"
    }
  },
  "blocks": {
    "header": {
      "content": "Site Header",
      "contentFormat": "markdown"
    },
    "footer": {
      "content": "Copyright 2026",
      "contentFormat": "markdown"
    },
    "sidebar": {
      "content": "Sidebar content",
      "contentFormat": "markdown"
    }
  },
  "menuItems": [
    {
      "name": "Home",
      "slug": "home",
      "visibility": "show",
      "order": 0,
      "subpages": []
    }
  ],
  "uploads": {
    "uuid-1": {
      "originalName": "photo.jpg",
      "mimeType": "image/jpeg",
      "size": 123456,
      "uploadedAt": "2026-01-04T00:00:00Z",
      "uploadedBy": "admin"
    }
  }
}
```

## 6. Security Architecture

### 6.1 Request Pipeline

```
Request
    │
    ▼
┌───────────────────────────────────────┐
│          Middleware Stack             │
├───────────────────────────────────────┤
│ 1. Security Headers                   │
│ 2. Rate Limiting                      │
│ 3. Request Size Limit                 │
│ 4. CORS (if enabled)                  │
│ 5. Session Validation                 │
│ 6. CSRF Validation (POST/PUT/DELETE)  │
│ 7. Authorization Check                │
└───────────────────────────────────────┘
    │
    ▼
Route Handler
    │
    ▼
┌───────────────────────────────────────┐
│         Validation Layer              │
├───────────────────────────────────────┤
│ - Pydantic input validation           │
│ - Path sanitization                   │
│ - Content sanitization                │
└───────────────────────────────────────┘
    │
    ▼
Business Logic
    │
    ▼
Response
```

### 6.2 Session Storage

```python
# In-memory session store (single-server)
# For production clustering: Redis

sessions = {
    "session_id": {
        "user_id": "admin",
        "role": "admin",
        "ip": "192.168.1.1",
        "created_at": datetime,
        "expires_at": datetime,
        "csrf_token": "..."
    }
}
```

## 7. Theme Integration

### 7.1 Theme Context

Templates receive a `cms` object with:

```python
class CMSContext:
    site: SiteConfig        # Site settings
    page: PageData          # Current page
    menu: List[MenuItem]    # Navigation
    blocks: Dict[str, str]  # Static blocks
    is_admin: bool          # Admin mode
    user: Optional[User]    # Current user

    def asset(path: str) -> str  # Theme asset URL
    def url(slug: str) -> str    # Page URL
    def block(name: str) -> str  # Render block
```

### 7.2 Template Example

```jinja2
<!DOCTYPE html>
<html lang="{{ cms.site.lang }}">
<head>
    <title>{{ cms.site.title }} - {{ cms.page.title }}</title>
    <link rel="stylesheet" href="{{ cms.asset('css/style.css') }}">
</head>
<body>
    <nav>
        {% for item in cms.menu %}
            <a href="{{ cms.url(item.slug) }}">{{ item.name }}</a>
        {% endfor %}
    </nav>

    <main>
        {{ cms.page.content | safe }}
    </main>

    <footer>
        {{ cms.block('footer') | safe }}
    </footer>
</body>
</html>
```

## 8. Plugin Integration

### 8.1 Plugin Manifest (plugin.json)

```json
{
    "name": "Example Plugin",
    "version": "1.0.0",
    "description": "An example plugin",
    "author": "Developer",
    "permissions": [
        "hook:css_inject",
        "hook:page_render"
    ],
    "entrypoint": "plugin.py"
}
```

### 8.2 Plugin Structure

```python
# plugins/example/plugin.py

from pressassist.core.hooks import hook_manager

def on_load(cms):
    """Called when plugin is enabled."""
    hook_manager.register('css_inject', inject_css)
    hook_manager.register('page_render', modify_page)

def on_unload(cms):
    """Called when plugin is disabled."""
    pass

def inject_css(args):
    """Inject custom CSS."""
    args['css'] += '<link rel="stylesheet" href="/plugins/example/style.css">'
    return args

def modify_page(args):
    """Modify page before render."""
    # args['page'] contains page data
    return args
```

## 9. Deployment Options

### 9.1 Development
```bash
pressassist run --host 127.0.0.1 --port 8000 --reload
```

### 9.2 Production (Direct)
```bash
pressassist run --host 0.0.0.0 --port 8000 --workers 4
```

### 9.3 Production (Behind Nginx)
```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/pressassist/static;
        expires 30d;
    }
}
```

---

**Document Version**: 1.0
**Last Updated**: 2026-01-04
