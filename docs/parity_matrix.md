# PressAssistCMS Feature Parity Matrix

This document maps WonderCMS features to their PressAssistCMS equivalents.

## Legend
- **YES**: Fully implemented
- **PARTIAL**: Implemented with modifications
- **NO**: Intentionally not implemented (security/design)
- **FUTURE**: Planned for later release
- **N/A**: Not applicable

## 1. Core Features

| WonderCMS Feature | PressAssistCMS | Notes |
|-------------------|----------------|-------|
| Single-file core | NO | Modular architecture for maintainability |
| Flat-file database | YES | `data/db.json` |
| One-step install | YES | `pressassist init` creates everything |
| No external dependencies for basic use | PARTIAL | Requires Python packages |

**PressAssistCMS Files**: `pressassist/core/storage.py`, `pressassist/cli.py`

## 2. Authentication

| WonderCMS Feature | PressAssistCMS | Notes |
|-------------------|----------------|-------|
| Single admin user | YES | Also supports Editor, Viewer roles |
| Secret login URL | YES | `/admin/login/{random_slug}` |
| bcrypt password hashing | YES | `pressassist/core/auth.py` |
| Session-based auth | YES | With secure cookie settings |
| Last 5 login IPs stored | YES | Plus user agent and timestamp |
| Password change | YES | Admin panel |
| Force logout all sessions | YES | Settings option |

**Additional in PressAssistCMS**:
- Multi-role support (Admin, Editor, Viewer)
- Rate limiting (5 attempts/15 min)
- CSRF on login form
- Audit logging

**PressAssistCMS Files**: `pressassist/core/auth.py`, `pressassist/core/csrf.py`

## 3. Content Management

| WonderCMS Feature | PressAssistCMS | Notes |
|-------------------|----------------|-------|
| Pages with slug routing | YES | `/{slug}` and `/{parent}/{slug}` |
| Hierarchical pages (subpages) | YES | Unlimited nesting |
| 404 page | YES | Customizable |
| Static blocks (header/footer/sidebar) | YES | Named blocks |
| Menu system | YES | With visibility control |
| Menu reordering | YES | Drag-and-drop in admin |
| Page visibility (show/hide) | YES | Per page |
| SEO fields (title/desc/keywords) | YES | Per page |
| Inline content editing | NO | Dedicated editor (security) |
| WYSIWYG editor | NO | Markdown only (security) |
| HTML content | PARTIAL | Sanitized HTML allowed |

**PressAssistCMS Files**: `pressassist/public/routes.py`, `pressassist/admin/routes.py`

## 4. Theme System

| WonderCMS Feature | PressAssistCMS | Notes |
|-------------------|----------------|-------|
| Theme directory structure | YES | `themes/{name}/` |
| Theme switching | YES | Admin settings |
| Theme metadata (wcms-modules.json) | YES | `theme.json` |
| PHP template tags | N/A | Jinja2 instead |
| `$Wcms->page('content')` | YES | `{{ cms.page.content }}` |
| `$Wcms->page('title')` | YES | `{{ cms.page.title }}` |
| `$Wcms->menu()` | YES | `{{ cms.menu() }}` |
| `$Wcms->block('name')` | YES | `{{ cms.block('name') }}` |
| `$Wcms->get('config', 'key')` | YES | `{{ cms.site.key }}` |
| `$Wcms->asset('path')` | YES | `{{ cms.asset('path') }}` |
| `$Wcms->css()` / `$Wcms->js()` | YES | `{{ cms.admin_css }}` / `{{ cms.admin_js }}` |
| `$Wcms->settings()` | YES | `{{ cms.admin_panel }}` |
| `$Wcms->alerts()` | YES | `{{ cms.alerts }}` |
| Theme functions.php | PARTIAL | `functions.py` for Python hooks |
| Custom page templates | YES | `{slug}.html` in theme |

**PressAssistCMS Files**: `pressassist/core/themes.py`

### Theme Tag Mapping

| WonderCMS (PHP) | PressAssistCMS (Jinja2) |
|-----------------|-------------------------|
| `<?= $Wcms->page('content') ?>` | `{{ cms.page.content \| safe }}` |
| `<?= $Wcms->page('title') ?>` | `{{ cms.page.title }}` |
| `<?= $Wcms->menu() ?>` | `{% for item in cms.menu %}...{% endfor %}` |
| `<?= $Wcms->block('sidebar') ?>` | `{{ cms.block('sidebar') \| safe }}` |
| `<?= $Wcms->get('config', 'siteTitle') ?>` | `{{ cms.site.title }}` |
| `<?= $Wcms->asset('css/style.css') ?>` | `{{ cms.asset('css/style.css') }}` |
| `<?= $Wcms->footer() ?>` | `{{ cms.block('footer') \| safe }}` |
| `<?= $Wcms->getSiteLanguage() ?>` | `{{ cms.site.lang }}` |

## 5. Plugin System

| WonderCMS Feature | PressAssistCMS | Notes |
|-------------------|----------------|-------|
| Plugin directory structure | YES | `plugins/{name}/` |
| Auto-load plugins | NO | Explicit enable required |
| Plugin metadata (wcms-modules.json) | YES | `plugin.json` |
| Disable/enable plugins | YES | Admin panel |
| Exclusive plugin groups | YES | Only one editor/translation |
| Hook system | YES | Event-based |
| `addListener()` | YES | `hook_manager.register()` |
| Hook: css | YES | `css_inject` |
| Hook: js | YES | `js_inject` |
| Hook: menu | YES | `menu_render` |
| Hook: page | YES | `page_render` |
| Hook: block | YES | `block_render` |
| Hook: header/footer | YES | Via `block_render` |
| Hook: alert | YES | `alert_render` |
| Hook: before_save | YES | `page_save_before` |
| Hook: after_save | YES | `page_save_after` |
| Hook: login_success | YES | `auth_success` |
| Hook: login_failed | YES | `auth_failed` |
| Plugin functions.php | N/A | `plugin.py` |

**Additional in PressAssistCMS**:
- Permission manifest in plugin.json
- API access control based on permissions
- No direct filesystem access from plugins

**PressAssistCMS Files**: `pressassist/core/plugins.py`, `pressassist/core/hooks.py`

## 6. Module/Plugin Installer

| WonderCMS Feature | PressAssistCMS | Notes |
|-------------------|----------------|-------|
| Install from official repo | FUTURE | Registry-only when implemented |
| Install from custom URL | NO | Security risk |
| Custom module URLs in config | NO | Security risk |
| ZIP download and extract | FUTURE | With verification |
| ZIP slip protection | YES | When implemented |
| Update existing module | FUTURE | Via registry |
| Delete module | YES | Admin panel |
| Module version checking | FUTURE | |
| Cache modules list | FUTURE | |

**PressAssistCMS Files**: `pressassist/core/plugins.py`

## 7. File Upload

| WonderCMS Feature | PressAssistCMS | Notes |
|-------------------|----------------|-------|
| File upload form | YES | Admin panel |
| Allowed extensions list | YES | MUCH stricter |
| MIME type checking | YES | Plus magic bytes |
| Upload size limit | YES | 5MB default |
| List uploaded files | YES | Admin panel |
| Delete uploaded file | YES | Admin only |
| Direct file serving | NO | Via secure endpoint |

### Allowed File Types Comparison

| WonderCMS | PressAssistCMS |
|-----------|----------------|
| avi, avif, css, doc, docx, flv, gif, htm, html, ico, jpeg, jpg, kdbx, m4a, mkv, mov, mp3, mp4, mpg, ods, odt, ogg, ogv, pdf, png, ppt, pptx, psd, rar, svg, txt, xls, xlsx, webm, webp, wmv, zip | **png, jpg, jpeg, webp, gif** |

**Security Note**: PressAssistCMS is intentionally restrictive.

**PressAssistCMS Files**: `pressassist/admin/routes.py` (upload endpoints)

## 8. Settings & Configuration

| WonderCMS Feature | PressAssistCMS | Notes |
|-------------------|----------------|-------|
| Site title | YES | |
| Site language | YES | With i18n |
| Admin language | YES | Separate setting |
| Default page | YES | |
| Theme selection | YES | |
| Login URL change | YES | |
| Force HTTPS toggle | YES | |
| Save changes popup | FUTURE | |
| Modal persistence | N/A | Different admin UI |

**PressAssistCMS Files**: `pressassist/core/config.py`, `pressassist/admin/routes.py`

## 9. Backup & Restore

| WonderCMS Feature | PressAssistCMS | Notes |
|-------------------|----------------|-------|
| Create backup (ZIP) | YES | `pressassist backup` |
| Backup includes database | YES | |
| Backup includes files | YES | |
| Backup includes themes | YES | Active theme |
| Backup includes plugins | YES | Active plugins |
| Restore from backup | YES | `pressassist restore` |
| Backup file list in admin | YES | |
| Delete old backups | YES | |

**PressAssistCMS Files**: `pressassist/cli.py`

## 10. Security Features

| WonderCMS Feature | PressAssistCMS | Notes |
|-------------------|----------------|-------|
| CSRF protection | PARTIAL→YES | All forms |
| Session regeneration | YES | |
| Basic rate limiting | NO→YES | Built-in |
| Security headers | PARTIAL→YES | Full set |
| Content sanitization | NO→YES | bleach |
| Path traversal prevention | PARTIAL→YES | Strict |
| Audit logging | NO→YES | Comprehensive |

**PressAssistCMS Files**: `pressassist/core/csrf.py`, `pressassist/core/security_headers.py`, `pressassist/core/sanitize.py`, `pressassist/core/audit_log.py`

## 11. CLI

| WonderCMS Feature | PressAssistCMS | Notes |
|-------------------|----------------|-------|
| N/A (web-only) | YES | Full CLI |

**PressAssistCMS CLI Commands**:
```bash
pressassist init           # Initialize new site
pressassist run            # Start server
pressassist backup         # Create backup
pressassist restore <zip>  # Restore from backup
pressassist hash-password  # Generate password hash
pressassist new-login-slug # Generate new login URL
```

**PressAssistCMS Files**: `pressassist/cli.py`

## 12. NOT Implemented (Security Decisions)

| WonderCMS Feature | Reason |
|-------------------|--------|
| Inline contenteditable editing | XSS risk, requires JS |
| Install modules from URL | RCE risk |
| Custom module URLs | Supply chain risk |
| SVG upload | XSS risk |
| HTML/HTM upload | XSS risk |
| CSS upload | Potential injection |
| ZIP/RAR upload | Malicious archives |
| Auto-enable plugins | Must be explicit |

---

**Document Version**: 1.0
**Last Updated**: 2026-01-04
