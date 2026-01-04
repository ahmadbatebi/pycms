# PressAssistCMS

<div align="center">

**A secure, lightweight, flat-file CMS built with Python and FastAPI**

*Inspired by WonderCMS, completely rewritten with security-first architecture*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-86%20passed-brightgreen.svg)]()

[Features](#features) | [Quick Start](#quick-start) | [Documentation](#documentation) | [Security](#security)

</div>

---

## Why PressAssistCMS?

| Problem | Solution |
|---------|----------|
| Complex database setup | **No database required** - Single JSON file |
| Security vulnerabilities | **Security-first** - Built from ground up with best practices |
| WYSIWYG XSS attacks | **Markdown-only** - No rich editor vulnerabilities |
| Outdated PHP stacks | **Modern stack** - Python 3.10+, FastAPI, async |
| Monolithic plugins | **Safe plugins** - Permission-based, isolated |

## Features

### Core
- **Flat-file database** with atomic writes and file locking
- **Hierarchical pages** with unlimited nesting
- **SEO fields** (title, description, keywords) per page
- **Static blocks** (header, footer, sidebar)
- **Menu management** with visibility control
- **Markdown content** with sanitized HTML output
- **i18n support** built-in from day one

### Security
- **Secret login URL** (no `/admin` or `/login`)
- **bcrypt hashing** (12 rounds)
- **Rate limiting** (5 attempts / 15 minutes)
- **CSRF protection** on all forms
- **Content Security Policy** headers
- **HTML sanitization** with strict allowlist
- **Secure uploads** (images only, re-encoded)
- **Audit logging** for all sensitive actions

### Admin Panel
- Clean, responsive dashboard
- Page and block CRUD
- Secure file uploads
- Theme switching
- Plugin management
- Backup/restore system
- Audit log viewer

## Quick Start

### Requirements
- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/pressassist-cms.git
cd pressassist-cms

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install
pip install -e .

# Initialize your site
pressassist init
```

You'll see output like this - **SAVE IT!**

```
════════════════════════════════════════════════════════════
IMPORTANT: Save these credentials securely!
════════════════════════════════════════════════════════════

  Login URL:  http://127.0.0.1:8000/x7k9m2p4q8...
  Password:   Abc123XyzSecure

These credentials will NOT be shown again!
```

### Run the Server

```bash
# Development (with auto-reload)
pressassist run --reload

# Production
pressassist run --host 0.0.0.0 --port 8000 --workers 4
```

Visit `http://127.0.0.1:8000` - Your site is live!

## CLI Reference

| Command | Description |
|---------|-------------|
| `pressassist init` | Initialize a new site |
| `pressassist run [options]` | Start the web server |
| `pressassist check` | Verify configuration |
| `pressassist backup` | Create a backup ZIP |
| `pressassist restore <file>` | Restore from backup |
| `pressassist new-login-slug` | Generate new secret login URL |
| `pressassist hash-password` | Generate bcrypt password hash |

### Run Options
```bash
pressassist run --host 0.0.0.0    # Bind to all interfaces
pressassist run --port 8080       # Custom port
pressassist run --workers 4       # Multiple workers
pressassist run --reload          # Auto-reload (dev)
```

## Project Structure

```
pressassist-cms/
├── pressassist/              # Main package
│   ├── core/                 # Core modules
│   │   ├── auth.py           # Authentication & sessions
│   │   ├── storage.py        # JSON database with locking
│   │   ├── sanitize.py       # HTML/Markdown sanitization
│   │   ├── themes.py         # Theme management
│   │   ├── plugins.py        # Plugin loader
│   │   ├── hooks.py          # Event system
│   │   ├── csrf.py           # CSRF protection
│   │   ├── i18n.py           # Internationalization
│   │   └── audit_log.py      # Security logging
│   ├── admin/                # Admin panel
│   │   └── routes.py         # Admin API (22 endpoints)
│   ├── locales/              # Translation files
│   └── main.py               # FastAPI application
├── themes/
│   └── default/              # Default theme
│       ├── theme.json
│       ├── templates/
│       └── static/
├── plugins/
│   ├── example_hello/        # Example plugin
│   └── ai_placeholder/       # AI integration placeholder
├── data/                     # Created on init
│   ├── db.json               # Database
│   ├── uploads/              # Uploaded files
│   ├── backups/              # Backups
│   └── audit.log             # Audit log
├── tests/                    # 86 tests
└── docs/                     # Documentation
```

## Security Design

### Upload Security

**Allowed:** PNG, JPG, JPEG, WebP, GIF only

Every upload goes through:
1. Extension check against allowlist
2. Magic bytes verification
3. Image re-encoding (strips hidden payloads)
4. UUID filename generation
5. Secure serving endpoint

**Blocked by design:** SVG, HTML, CSS, JS, PHP, EXE, ZIP, and all other types.

### Authentication Flow

```
User visits /random-secret-slug
    ↓
Rate limit check (5 attempts/15 min)
    ↓
bcrypt password verification (12 rounds)
    ↓
Session created (HttpOnly, Secure, SameSite)
    ↓
CSRF token issued
    ↓
Audit log entry
```

### Content Security

- No raw HTML input (Markdown only)
- Output sanitized with strict tag allowlist
- `<script>`, `<style>`, `<svg>` completely stripped (with content)
- CSP headers block inline scripts
- XSS attack surface: **minimal**

## Theme Development

Create `themes/mytheme/`:

```
mytheme/
├── theme.json
├── templates/
│   ├── base.html
│   ├── page.html
│   └── 404.html
└── static/
    └── css/style.css
```

### theme.json
```json
{
    "name": "My Theme",
    "version": "1.0.0",
    "author": "Your Name"
}
```

### Template Variables
```jinja2
{{ cms.site_title }}              {# Site title #}
{{ cms.site_lang }}               {# Language code #}
{{ cms.page.title }}              {# Page title #}
{{ cms.page.content | safe }}     {# Rendered content #}
{{ cms.page.description }}        {# Meta description #}

{% for item in cms.menu_items %}  {# Navigation #}
    <a href="/{{ item.slug }}">{{ item.name }}</a>
{% endfor %}

{{ cms.block('footer') | safe }}  {# Static block #}
{{ cms.asset('css/style.css') }}  {# Theme asset URL #}
```

## Plugin Development

Create `plugins/myplugin/`:

### plugin.json
```json
{
    "name": "My Plugin",
    "version": "1.0.0",
    "description": "What it does",
    "permissions": [
        "hook:page_render",
        "hook:css_inject"
    ]
}
```

### plugin.py
```python
def on_load(api):
    """Called when plugin is enabled."""
    api.register_hook("page_render", modify_page)

def on_unload():
    """Called when plugin is disabled."""
    pass

def modify_page(payload):
    """Modify page before rendering."""
    payload["content"] += "<p>Added by plugin</p>"
    return payload
```

### Available Hooks
| Hook | Description |
|------|-------------|
| `page_render` | Before page content renders |
| `page_save_before` | Before page is saved |
| `page_save_after` | After page is saved |
| `block_render` | Before block renders |
| `menu_render` | Before menu renders |
| `css_inject` | Inject CSS into head |
| `js_inject` | Inject JavaScript |
| `upload_after` | After file upload |
| `auth_success` | After successful login |

## API Reference

### Public Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Homepage |
| GET | `/{slug}` | Page by slug |
| GET | `/uploads/{uuid}` | Serve uploaded file |

### Admin API
All admin endpoints require authentication and CSRF token.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/` | Dashboard |
| GET | `/admin/api/pages` | List all pages |
| POST | `/admin/api/pages` | Create page |
| PUT | `/admin/api/pages/{slug}` | Update page |
| DELETE | `/admin/api/pages/{slug}` | Delete page |
| GET | `/admin/api/blocks` | List blocks |
| PUT | `/admin/api/blocks/{name}` | Update block |
| GET | `/admin/api/uploads` | List uploads |
| POST | `/admin/api/uploads` | Upload file |
| DELETE | `/admin/api/uploads/{uuid}` | Delete upload |
| GET | `/admin/api/settings` | Get settings |
| PUT | `/admin/api/settings` | Update settings |
| GET | `/admin/api/plugins` | List plugins |
| POST | `/admin/api/plugins/{name}/enable` | Enable plugin |
| POST | `/admin/api/plugins/{name}/disable` | Disable plugin |
| GET | `/admin/api/themes` | List themes |
| PUT | `/admin/api/themes/active` | Set active theme |
| POST | `/admin/api/backup` | Create backup |
| GET | `/admin/api/backups` | List backups |
| GET | `/admin/api/audit-log` | View audit log |

## Production Deployment

### With Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /themes {
        alias /var/www/pressassist/themes;
        expires 30d;
    }
}
```

### With systemd

```ini
# /etc/systemd/system/pressassist.service
[Unit]
Description=PressAssistCMS
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/pressassist
Environment="PATH=/var/www/pressassist/.venv/bin"
ExecStart=/var/www/pressassist/.venv/bin/pressassist run --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable pressassist
sudo systemctl start pressassist
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=pressassist --cov-report=html

# Security scan
bandit -r pressassist/

# Dependency audit
pip-audit
```

Current status: **86 tests passing**

## Comparison: WonderCMS vs PressAssistCMS

| Feature | WonderCMS | PressAssistCMS |
|---------|-----------|----------------|
| Language | PHP | Python |
| Framework | Custom | FastAPI |
| Database | JSON | JSON |
| Content editing | HTML + WYSIWYG | Markdown only |
| Upload types | 30+ types | 5 image types |
| Security headers | Partial | Full (CSP, HSTS) |
| Rate limiting | No | Yes |
| Audit logging | No | Yes |
| CSRF protection | Partial | Full |
| Plugin security | Trust-based | Permission-based |
| Tests | None | 86 tests |

## Documentation

- [Architecture](docs/architecture.md) - System design and data flow
- [Security Policy](docs/SECURITY.md) - Security guidelines
- [Threat Model](docs/threat_model.md) - Security analysis
- [Feature Parity](docs/parity_matrix.md) - WonderCMS comparison

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Write tests for your changes
4. Ensure all tests pass (`pytest`)
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing`)
7. Open a Pull Request

## Security Vulnerabilities

Found a security issue? Please email **[your-email]** instead of opening a public issue.

## License

MIT License - see [LICENSE](LICENSE) file.

## Acknowledgments

- Inspired by [WonderCMS](https://www.wondercms.com/)
- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Templates by [Jinja2](https://jinja.palletsprojects.com/)

---

<div align="center">

**Built with security in mind.**

[Report Bug](https://github.com/YOUR_USERNAME/pressassist-cms/issues) | [Request Feature](https://github.com/YOUR_USERNAME/pressassist-cms/issues)

</div>
