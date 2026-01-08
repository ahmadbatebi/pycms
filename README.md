# ChelCheleh CMS

<div align="center">

![ChelCheleh Logo](https://img.shields.io/badge/ChelCheleh-CMS-6366f1?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiPjxwYXRoIGQ9Ik0zIDlsOS03IDkgN3YxMWEyIDIgMCAwIDEtMiAySDVhMiAyIDAgMCAxLTItMnoiLz48cG9seWxpbmUgcG9pbnRzPSI5IDIyIDkgMTIgMTUgMTIgMTUgMjIiLz48L3N2Zz4=)

**A secure, lightweight, flat-file CMS built with Python and FastAPI**

*سیستم مدیریت محتوای چلچله*

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

[Features](#features) • [Installation](#installation) • [Quick Start](#quick-start) • [Documentation](#documentation) • [Security](#security)

</div>

---

## Overview

ChelCheleh (چلچله - meaning "Swallow" in Persian) is a modern, secure content management system that requires **no database**. All data is stored in JSON files, making it perfect for small to medium websites, landing pages, and personal blogs.

### Why ChelCheleh?

| Traditional CMS Problems | ChelCheleh Solution |
|--------------------------|---------------------|
| Complex database setup | **No database** - Single JSON file storage |
| Security vulnerabilities | **Security-first** design with best practices |
| Heavy resource usage | **Lightweight** - Minimal dependencies |
| Complicated hosting | **Simple deployment** - Any Python host works |
| Outdated technology | **Modern stack** - Python 3.10+, FastAPI, async |

---

## Features

### Content Management
- **Pages** - Create unlimited pages with SEO fields (title, description, keywords)
- **Blog** - Full blogging system with categories, tags, and comments
- **Menu** - Drag-and-drop menu management with visibility control
- **Blocks** - Reusable content blocks (header, footer, sidebar)
- **Media** - Secure file uploads with image optimization
- **Multi-language** - Built-in support for English and Persian (RTL)

### Admin Panel
- Modern, responsive dashboard
- WYSIWYG editor (CKEditor 5)
- User management with roles (Super Admin, Admin, Editor, Viewer)
- Theme switching with live preview
- Backup and restore system
- System update checker

### Security
- **Secret login URL** - No predictable `/admin` or `/login` paths
- **bcrypt hashing** - 12 rounds for password security
- **Rate limiting** - Brute-force protection (5 attempts / 15 minutes)
- **CSRF protection** - On all forms and API endpoints
- **CSP headers** - Content Security Policy enforcement
- **Secure uploads** - Images only, re-encoded to strip malware
- **Audit logging** - Track all sensitive actions

---

## Installation

### Requirements

- Python 3.10 or higher
- pip (Python package manager)
- Git (optional, for cloning)

### Method 1: Clone from GitHub

```bash
# Clone the repository
git clone https://github.com/AhmadBateworCMS/chelcheleh.git
cd chelcheleh

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Method 2: Download ZIP

1. Download the ZIP file from GitHub
2. Extract to your desired location
3. Open terminal in the extracted folder
4. Follow the virtual environment steps above

---

## Quick Start

### 1. Initialize Your Site

```bash
pressassist init
```

You'll see output like this:

```
════════════════════════════════════════════════════════════════
  IMPORTANT: Save these credentials securely!
════════════════════════════════════════════════════════════════

  Login URL:  http://127.0.0.1:8000/xK9mP4qR8tY2...
  Username:   admin
  Password:   Admin12345!

  Change your password after first login!
════════════════════════════════════════════════════════════════
```

> ⚠️ **Important:** Save the Login URL - this is your secret admin access point!

### 2. Start the Server

```bash
# Development mode (with auto-reload)
pressassist run --reload

# Or specify port
pressassist run --port 7000

# Production mode
pressassist run --host 0.0.0.0 --port 8000 --workers 4
```

### 3. Access Your Site

- **Frontend:** http://127.0.0.1:8000
- **Admin Panel:** Use the secret Login URL from initialization

### Default Credentials

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `Admin12345!` |

> ⚠️ Change the default password immediately after first login!

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `pressassist init` | Initialize a new site |
| `pressassist run [options]` | Start the web server |
| `pressassist check` | Verify configuration |
| `pressassist backup` | Create a backup ZIP |
| `pressassist restore <file>` | Restore from backup |
| `pressassist new-login-slug` | Generate new secret login URL |
| `pressassist hash-password` | Generate bcrypt password hash |

### Server Options

```bash
pressassist run --host 0.0.0.0    # Bind to all interfaces
pressassist run --port 8080       # Custom port
pressassist run --workers 4       # Multiple workers (production)
pressassist run --reload          # Auto-reload on changes (development)
```

---

## Project Structure

```
chelcheleh/
├── pressassist/              # Main package
│   ├── core/                 # Core modules
│   │   ├── auth.py           # Authentication & sessions
│   │   ├── storage.py        # JSON database with file locking
│   │   ├── sanitize.py       # HTML/Markdown sanitization
│   │   ├── themes.py         # Theme management
│   │   ├── plugins.py        # Plugin system
│   │   ├── hooks.py          # Event system
│   │   ├── csrf.py           # CSRF protection
│   │   ├── i18n.py           # Internationalization
│   │   └── audit_log.py      # Security logging
│   ├── admin/                # Admin panel
│   │   ├── routes.py         # Admin pages & API
│   │   ├── blog_routes.py    # Blog management
│   │   ├── user_routes.py    # User management
│   │   └── static/           # Admin assets (CSS, JS)
│   ├── frontend/             # Public-facing routes
│   ├── locales/              # Translation files (en, fa)
│   └── main.py               # FastAPI application
├── themes/
│   └── default/              # Default theme
│       ├── templates/        # Jinja2 templates
│       └── static/           # CSS, JS, images
├── plugins/                  # Plugin directory
├── data/                     # Created on init
│   ├── db.json               # Database file
│   ├── uploads/              # Uploaded files
│   ├── backups/              # Backup files
│   └── audit.log             # Security audit log
├── tests/                    # Test suite
└── docs/                     # Documentation
```

---

## Configuration

### Admin Settings

After login, go to **Settings** to configure:

- **Site Title** - Your website name
- **Default Page** - Homepage slug
- **Site Language** - English or Persian
- **Admin Language** - Admin panel language
- **Theme** - Active theme selection
- **Login URL** - Change your secret admin path
- **Force HTTPS** - Redirect HTTP to HTTPS
- **Maintenance Mode** - Show maintenance page to visitors
- **Search Settings** - Enable/disable site search

### Environment Variables

```bash
export PRESSASSIST_HOST=0.0.0.0
export PRESSASSIST_PORT=8000
export PRESSASSIST_DEBUG=false
export PRESSASSIST_SECRET_KEY=your-secret-key
export PRESSASSIST_WORKERS=4
```

---

## Theme Development

Create a new theme in `themes/mytheme/`:

```
mytheme/
├── theme.json           # Theme metadata
├── templates/
│   ├── base.html        # Base template
│   ├── page.html        # Page template
│   └── 404.html         # Error page
└── static/
    ├── css/style.css
    └── js/script.js
```

### theme.json

```json
{
    "name": "My Theme",
    "version": "1.0.0",
    "description": "A custom theme",
    "author": "Your Name"
}
```

### Template Variables

```jinja2
{{ cms.site_title }}              {# Site title #}
{{ cms.page_title }}              {# Current page title #}
{{ cms.page_content | safe }}     {# Page content (HTML) #}
{{ cms.page_description }}        {# Meta description #}

{% for item in cms.menu_items %}  {# Navigation menu #}
    <a href="/{{ item.slug }}">{{ item.title }}</a>
{% endfor %}

{{ cms.blocks.header | safe }}    {# Header block #}
{{ cms.blocks.footer | safe }}    {# Footer block #}
```

---

## Production Deployment

### With Nginx (Recommended)

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
        alias /var/www/chelcheleh/themes;
        expires 30d;
    }
}
```

### With systemd

```ini
# /etc/systemd/system/chelcheleh.service
[Unit]
Description=ChelCheleh CMS
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/chelcheleh
Environment="PATH=/var/www/chelcheleh/.venv/bin"
ExecStart=/var/www/chelcheleh/.venv/bin/pressassist run --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable chelcheleh
sudo systemctl start chelcheleh
sudo systemctl status chelcheleh
```

---

## Security

### Upload Security

- **Allowed types:** PNG, JPG, JPEG, WebP, GIF only
- **Validation:** Magic bytes verification
- **Processing:** Images are re-encoded to strip hidden payloads
- **Storage:** UUID filenames, no directory traversal

### Authentication

- Secret login URL (no predictable paths)
- bcrypt password hashing (12 rounds)
- Rate limiting (5 failed attempts = 15 minute lockout)
- Secure session cookies (HttpOnly, Secure, SameSite)
- Automatic session expiry (4 hours)

### Content Security

- CSRF tokens on all forms
- Content Security Policy headers
- HTML sanitization with strict allowlist
- XSS protection on all outputs

---

## Testing

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# With coverage report
python -m pytest tests/ --cov=pressassist --cov-report=html

# Security scan
pip install bandit
bandit -r pressassist/

# Dependency audit
pip install pip-audit
pip-audit
```

---

## API Reference

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Homepage |
| GET | `/{slug}` | Page by slug |
| GET | `/blog` | Blog listing |
| GET | `/blog/{slug}` | Blog post |
| GET | `/uploads/{uuid}` | Uploaded file |

### Admin API

All admin endpoints require authentication and CSRF token.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/` | Dashboard |
| GET/POST | `/admin/api/pages` | List/Create pages |
| PUT/DELETE | `/admin/api/pages/{slug}` | Update/Delete page |
| GET/POST | `/admin/api/blog/posts` | List/Create posts |
| GET/PUT | `/admin/api/settings` | Get/Update settings |
| GET/POST | `/admin/api/uploads` | List/Upload files |
| GET | `/admin/api/users` | List users |
| GET/PUT | `/admin/api/menu` | Get/Update menu |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Write tests for your changes
4. Ensure all tests pass (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing`)
7. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Templates powered by [Jinja2](https://jinja.palletsprojects.com/)
- Editor: [CKEditor 5](https://ckeditor.com/ckeditor-5/)
- Inspired by flat-file CMS concepts

---

<div align="center">

**ChelCheleh CMS** - Simple, Secure, Fast

[Report Bug](https://github.com/AhmadBateworCMS/chelcheleh/issues) • [Request Feature](https://github.com/AhmadBateworCMS/chelcheleh/issues)

</div>
