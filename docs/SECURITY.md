# PressAssistCMS Security Policy

## 1. Secure Defaults

PressAssistCMS is designed with **security by default**. The following are the default security settings:

### 1.1 Authentication
- **Password Requirements**: Minimum 12 characters
- **Login Slug**: Cryptographically random 32-character URL
- **Session Duration**: 4 hours
- **Rate Limiting**: 5 login attempts per 15 minutes per IP
- **Password Storage**: bcrypt with cost factor 12

### 1.2 Content
- **Default Format**: Markdown (no raw HTML)
- **HTML Mode**: Disabled by default
- **If HTML enabled**: Strict sanitization via bleach
- **Blocked Elements**: script, iframe, object, embed, form, input
- **Blocked Attributes**: on*, style (inline), srcset
- **Allowed HTML Tags**: p, br, strong, em, a, ul, ol, li, h1-h6, blockquote, code, pre, img (src only)

### 1.3 File Uploads
- **Allowed Types**: PNG, JPG, JPEG, WebP, GIF only
- **Maximum Size**: 5MB per file
- **SVG**: Blocked (XSS risk)
- **HTML/HTM**: Blocked
- **Filename**: UUID (original name discarded)
- **Processing**: Images re-encoded to strip metadata/payloads

### 1.4 Plugins
- **Remote Installation**: Disabled
- **Auto-Enable**: Disabled (requires manual activation)
- **Execution**: Only explicitly loaded via manifest

### 1.5 Network
- **HTTPS**: Required in production
- **Cookies**: HttpOnly, Secure, SameSite=Lax
- **CSRF**: Enabled on all state-changing requests
- **CORS**: Same-origin only

## 2. Security Headers

All responses include:

```
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'
```

With HTTPS:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

## 3. Roles and Permissions

| Permission | Admin | Editor | Viewer |
|------------|-------|--------|--------|
| View public pages | Yes | Yes | Yes |
| View hidden pages | Yes | Yes | No |
| Edit page content | Yes | Yes | No |
| Create/delete pages | Yes | Yes | No |
| Edit blocks | Yes | Yes | No |
| Upload files | Yes | Yes | No |
| Delete files | Yes | No | No |
| Change theme | Yes | No | No |
| Manage plugins | Yes | No | No |
| Change settings | Yes | No | No |
| Manage users | Yes | No | No |
| View audit log | Yes | No | No |
| Backup/restore | Yes | No | No |

## 4. Audit Logging

The following events are logged:

### Authentication Events
- Login success (IP, user agent, timestamp)
- Login failure (IP, user agent, timestamp)
- Logout
- Password change
- Session invalidation

### Content Events
- Page created
- Page modified
- Page deleted
- Block modified
- File uploaded
- File deleted

### System Events
- Plugin enabled/disabled
- Theme changed
- Settings changed
- Backup created
- Backup restored

### Log Format
```json
{
  "timestamp": "2026-01-04T12:00:00Z",
  "event": "login_success",
  "actor": "admin",
  "ip": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "details": {}
}
```

### Log Retention
- Default: 90 days
- Location: `data/audit.log`
- Format: JSON Lines

## 5. Dependency Policy

### Approved Dependencies
- **FastAPI**: Web framework
- **Uvicorn**: ASGI server
- **Jinja2**: Templating
- **passlib[bcrypt]**: Password hashing
- **bleach**: HTML sanitization
- **markdown-it-py**: Markdown parsing
- **Pillow**: Image processing (optional)
- **python-multipart**: File uploads
- **itsdangerous**: Token signing

### Security Scanning
- Run `pip-audit` before each release
- Run `bandit` for static analysis
- Update dependencies monthly
- Security patches applied within 48 hours

## 6. Secure Development Guidelines

### For Plugin Developers
1. Never access files outside plugin directory
2. Never execute shell commands
3. Use provided API for storage access
4. Declare all permissions in plugin.json
5. Sanitize all user input
6. Never store credentials

### For Theme Developers
1. Use Jinja2 autoescape (default)
2. Never render user content as template code
3. Link assets via `cms.asset()` helper
4. Validate all URLs in templates
5. Use nonce for inline scripts (if needed)

## 7. Incident Response

### If You Discover a Vulnerability
1. **Do Not** disclose publicly
2. Email security details to [MAINTAINER EMAIL]
3. Include: description, steps to reproduce, potential impact
4. We will respond within 48 hours
5. We will coordinate disclosure after fix

### Our Response
1. Acknowledge receipt within 48 hours
2. Provide initial assessment within 7 days
3. Release patch within 30 days (critical: 7 days)
4. Credit reporter in advisory (if desired)

## 8. Security Checklist for Deployment

### Before Going Live
- [ ] Change default login slug
- [ ] Set strong admin password (12+ chars, unique)
- [ ] Enable HTTPS (required for public sites)
- [ ] Review allowed upload types
- [ ] Configure backup schedule
- [ ] Set appropriate file permissions (600 for data/)
- [ ] Review and enable only needed plugins
- [ ] Test all forms for CSRF protection
- [ ] Verify security headers with securityheaders.com

### Server Configuration
- [ ] Run as non-root user
- [ ] Restrict file permissions
- [ ] Configure firewall
- [ ] Enable fail2ban (recommended)
- [ ] Set up log rotation
- [ ] Configure reverse proxy (nginx/Caddy)
- [ ] Enable automatic security updates

## 9. Known Limitations

1. **Single-Server**: No built-in clustering support
2. **No Encryption at Rest**: Database file not encrypted
3. **No 2FA**: Two-factor authentication not implemented (future)
4. **No IP Allowlisting**: Admin access not IP-restricted (future)

## 10. Security Updates

Subscribe to security announcements:
- GitHub Security Advisories
- Mailing list: [TO BE CREATED]

---

**Policy Version**: 1.0
**Effective Date**: 2026-01-04
**Review Schedule**: Quarterly
