# WonderCMS Analysis - PressAssistCMS Reference

> **Purpose**: Technical analysis of WonderCMS architecture for Python reimplementation.
> **Note**: No code is copied. This is a behavioral and architectural study only.

## 1. Architecture Overview

### 1.1 Single-File Core
WonderCMS consists of a single `index.php` (~3500 lines) containing:
- The entire `Wcms` class
- All routing, storage, authentication, theming, and plugin logic

**PressAssistCMS Decision**: Modular architecture with separate files for maintainability and testability.

### 1.2 Flat-File Database
- Storage: `data/database.js` (JSON with `.js` extension for security)
- Structure:
```json
{
  "config": {
    "siteTitle": "...",
    "siteLang": "en",
    "theme": "sky",
    "defaultPage": "home",
    "login": "loginURL",  // Secret login slug
    "password": "$2y$...",  // bcrypt hash
    "forceHttps": false,
    "menuItems": [...],
    "disabledPlugins": [],
    "customModules": {"themes": [], "plugins": []}
  },
  "pages": {
    "home": {
      "title": "Home",
      "content": "<h1>...</h1>",
      "keywords": "...",
      "description": "...",
      "subpages": {}
    },
    "404": {...}
  },
  "blocks": {
    "header": {"content": "..."},
    "footer": {"content": "..."},
    "subside": {"content": "..."}
  }
}
```

**PressAssistCMS Decision**: Similar JSON structure with proper `.json` extension, atomic writes with locking.

## 2. Authentication System

### 2.1 Login Mechanism
- Single admin account (no multi-user)
- Secret login URL: `/{loginSlug}` (default: `loginURL`)
- bcrypt password hashing with `password_hash()` / `password_verify()`
- Session-based authentication with `$_SESSION['loggedIn']`
- Session regeneration on login (`session_regenerate_id(true)`)
- Last 5 login IPs stored in config

### 2.2 Security Issues Found
1. **Login URL Discovery**: Default `loginURL` is predictable
2. **No Rate Limiting**: No built-in brute-force protection
3. **XSS in Alerts**: `<script>alert("Wrong password")</script>` used for wrong password
4. **No CSRF on Login**: Only POST actions protected

**PressAssistCMS Decisions**:
- Cryptographically random login slug on install
- Rate limiting with exponential backoff
- Proper error messages without XSS
- CSRF protection on all forms including login
- Multi-role support: Admin, Editor, Viewer

## 3. Content Management

### 3.1 Pages
- Hierarchical structure with subpages
- Slug-based routing: `/{page}` or `/{parent}/{child}`
- Inline editing (contenteditable divs)
- Fields: title, content, keywords, description, visibility

### 3.2 Blocks (Static Regions)
- Named blocks: header, footer, subside (sidebar)
- Shared across all pages
- Inline editable

### 3.3 Menu System
- menuItems in config
- Visibility: show/hide
- Reordering support
- Sync with pages visibility

**PressAssistCMS Decision**: Same conceptual model but:
- Markdown as default content format (safer)
- HTML sanitization mandatory (bleach)
- No inline JS editing

## 4. Theme System

### 4.1 Structure
```
themes/
  themename/
    theme.php          # Main template
    functions.php      # Optional theme functions
    404.php           # Custom 404 template
    css/
      style.css
    wcms-modules.json  # Theme metadata
```

### 4.2 Template Tags
The theme uses PHP global `$Wcms` object:
- `$Wcms->page('content')` - Page content
- `$Wcms->page('title')` - Page title
- `$Wcms->menu()` - Navigation menu
- `$Wcms->block('sidebar')` - Named block
- `$Wcms->css()` / `$Wcms->js()` - Admin assets
- `$Wcms->settings()` - Admin panel
- `$Wcms->alerts()` - Flash messages
- `$Wcms->get('config', 'siteTitle')` - Config values
- `$Wcms->asset('path')` - Theme asset URL
- `$Wcms->getSiteLanguage()` - Current language

**PressAssistCMS Decision**: Jinja2 templates with context:
```jinja2
{{ cms.page.content }}
{{ cms.page.title }}
{{ cms.menu() }}
{{ cms.block('sidebar') }}
{{ cms.site.title }}
{{ cms.asset('css/style.css') }}
```

## 5. Plugin System

### 5.1 Structure
```
plugins/
  pluginname/
    pluginname.php     # Main plugin file
    wcms-modules.json  # Plugin metadata
```

### 5.2 Loading
- Auto-loads `plugins/{name}/{name}.php`
- Can be disabled via `config.disabledPlugins`
- Exclusive groups: 'editor', 'translation' (only one active)

### 5.3 Hook System
```php
$Wcms->addListener('hookName', function($args) {
    // Modify $args
    return $args;
});

// Hooks available:
// - css, js: Inject styles/scripts
// - menu, header, footer, block: Modify output
// - page: Modify page data
// - alert: Modify alerts
// - before_save, after_save: Content hooks
// - login_success, login_failed: Auth hooks
```

**PressAssistCMS Decision**:
- Python plugin structure with `plugin.json` manifest
- Explicit permissions in manifest
- Hooks via event emitter pattern
- No auto-enable - explicit admin action required

## 6. Module/Plugin Installer

### 6.1 Current Implementation
1. Fetch ZIP from URL
2. Basic zip-slip protection (checks `../`, absolute paths)
3. Extract to themes/ or plugins/
4. Rename from `-master` or `-main` suffix

### 6.2 Security Issues Found
1. **No Hash Verification**: ZIP integrity not verified
2. **Wide File Types**: Any file extracted
3. **Symlink Risk**: Not checking for symlinks
4. **PHP Execution**: Extracted PHP runs automatically
5. **Custom URLs**: Admin can add any URL as module source

**PressAssistCMS Decisions**:
- MVP: No remote install, only filesystem copy
- Future: Registry-only with SHA256 verification
- Strict file allowlist
- No executable files (Python modules loaded explicitly)
- Symlink blocking

## 7. File Upload System

### 7.1 Current Implementation
Allowed extensions and MIME types (permissive):
- Images: gif, jpg, jpeg, png, ico, svg, webp, avif
- Documents: pdf, doc, docx, xls, xlsx, ppt, pptx, odt, ods, txt
- Media: mp3, mp4, avi, flv, mkv, mov, mpg, ogg, ogv, webm, wmv
- Code: css, html, htm
- Archives: zip, rar
- Others: psd, kdbx

### 7.2 Security Issues Found
1. **SVG Allowed**: Can contain JavaScript
2. **HTML/HTM Allowed**: XSS risk if served
3. **No Content Validation**: Only MIME check, no magic bytes
4. **Original Filename**: Preserved (predictable)
5. **No Re-encoding**: Images not sanitized

**PressAssistCMS Decisions**:
- **Strict allowlist**: png, jpg, jpeg, webp, gif only
- **SVG banned by default**
- **HTML banned**
- **UUID filenames** - unpredictable
- **Image re-encoding** - strips payloads
- **Magic bytes validation**
- **Content-Disposition: attachment** for non-images
- **nosniff header** always

## 8. Security Analysis Summary

### 8.1 Critical Risks in WonderCMS

| Risk | Severity | WonderCMS Status | PressAssistCMS Mitigation |
|------|----------|------------------|---------------------------|
| Plugin RCE | Critical | Possible via ZIP | Registry-only, no auto-enable |
| File Upload | High | SVG/HTML allowed | Strict image allowlist |
| XSS | High | Inline HTML editing | Markdown + sanitization |
| CSRF | Medium | Partial protection | Full CSRF on all POSTs |
| Brute Force | Medium | No rate limit | Exponential backoff |
| Session Fixation | Low | Regenerated | Regenerated + secure flags |

### 8.2 Attack Vectors

1. **Remote Code Execution**:
   - Upload malicious plugin ZIP
   - Upload PHP file disguised as allowed type
   - SVG with embedded JavaScript

2. **Cross-Site Scripting**:
   - Store malicious HTML in page content
   - Upload HTML file
   - Plugin injecting scripts

3. **Authentication Bypass**:
   - Brute force login
   - Session hijacking
   - CSRF to change password

## 9. PressAssistCMS Redesign Summary

### 9.1 Security-First Principles
1. Deny by default, allow explicitly
2. No inline code execution
3. All user content sanitized
4. Cryptographically random secrets
5. Audit logging for sensitive actions

### 9.2 Architectural Changes
1. Modular Python codebase
2. FastAPI with async support
3. Jinja2 templates (sandboxed)
4. JSON storage with atomic writes
5. Markdown-first content

### 9.3 Feature Parity Goals
- Single-file flat database: YES
- One-step install: YES
- Pages/Blocks/Menu: YES
- Themes: YES (Jinja2)
- Plugins: YES (Python, restricted)
- Hooks: YES (event emitter)
- Custom modules from URL: NO (security)
- WYSIWYG: NO (Markdown instead)
- File uploads: YES (restricted)

---

**Analysis Date**: 2026-01-04
**WonderCMS Version Analyzed**: 3.6.0
