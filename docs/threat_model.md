# PressAssistCMS Threat Model

## 1. System Overview

PressAssistCMS is a flat-file CMS designed for public internet deployment with:
- Multi-role authentication (Admin, Editor, Viewer)
- Markdown content editing
- Plugin/theme extensibility
- File upload capabilities
- i18n support

## 2. Assets to Protect

### 2.1 Critical Assets
| Asset | Description | CIA Priority |
|-------|-------------|--------------|
| Admin Credentials | Password hash, session tokens | C > I > A |
| Database File | All site content and config | I > A > C |
| Login Slug | Secret admin URL | C > I > A |
| Server Filesystem | Prevent unauthorized access | C > I > A |

### 2.2 High-Value Assets
| Asset | Description | CIA Priority |
|-------|-------------|--------------|
| Page Content | User-visible content | I > A > C |
| Uploaded Files | Media and documents | I > A > C |
| Plugins | Extensibility code | I > C > A |
| Audit Logs | Security events | I > A > C |

### 2.3 Medium-Value Assets
| Asset | Description | CIA Priority |
|-------|-------------|--------------|
| Theme Templates | Visual presentation | I > A > C |
| Backups | Recovery data | C > I > A |
| Session Data | User state | C > I > A |

## 3. Threat Actors

### 3.1 External Attackers
| Actor | Motivation | Capability | Likelihood |
|-------|------------|------------|------------|
| Script Kiddie | Defacement, Botnets | Low (automated tools) | High |
| Opportunistic Hacker | Data theft, Cryptomining | Medium | Medium |
| Targeted Attacker | Specific site compromise | High | Low |
| Competitor | Business disruption | Medium | Low |

### 3.2 Internal Threats
| Actor | Motivation | Capability | Likelihood |
|-------|------------|------------|------------|
| Curious Editor | Privilege escalation | Medium (authenticated) | Medium |
| Compromised Admin | Account takeover | High (full access) | Low |
| Malicious Plugin | Supply chain attack | High (code execution) | Medium |

## 4. Attack Vectors and Mitigations

### 4.1 Authentication Attacks

#### A1: Brute Force Login
- **Vector**: Automated password guessing on login endpoint
- **Impact**: Account compromise (Critical)
- **Likelihood**: High
- **Mitigations**:
  1. Rate limiting: 5 attempts per 15 minutes per IP
  2. Exponential backoff after failures
  3. Account lockout notification
  4. Random login slug (not discoverable)
  5. Strong password requirements (min 12 chars)

#### A2: Session Hijacking
- **Vector**: Steal session cookie via XSS or network sniffing
- **Impact**: Account impersonation (Critical)
- **Likelihood**: Medium
- **Mitigations**:
  1. HttpOnly cookies
  2. Secure flag (HTTPS only)
  3. SameSite=Lax or Strict
  4. Session regeneration on login
  5. Short session timeout (4 hours)
  6. CSRF tokens on all state-changing requests

#### A3: Credential Stuffing
- **Vector**: Use leaked credentials from other breaches
- **Impact**: Account compromise (Critical)
- **Likelihood**: Medium
- **Mitigations**:
  1. Unique password requirement messaging
  2. Audit log of login attempts
  3. Optional: HIBP integration for compromised password check

### 4.2 Injection Attacks

#### B1: Cross-Site Scripting (XSS)
- **Vector**: Malicious content in pages, blocks, or uploads
- **Impact**: Session theft, defacement, malware distribution (High)
- **Likelihood**: High
- **Mitigations**:
  1. Markdown-only content (no raw HTML by default)
  2. bleach sanitization with strict allowlist
  3. Content-Security-Policy header
  4. X-XSS-Protection header
  5. Output encoding in templates

#### B2: SQL Injection
- **Vector**: N/A - No SQL database
- **Impact**: N/A
- **Mitigations**: Flat-file JSON storage eliminates this vector

#### B3: Template Injection
- **Vector**: User content rendered as Jinja2 code
- **Impact**: Server code execution (Critical)
- **Likelihood**: Low (if properly implemented)
- **Mitigations**:
  1. Jinja2 sandboxed environment
  2. User content never rendered as template code
  3. Autoescape enabled globally
  4. No custom filters from user input

#### B4: Path Traversal
- **Vector**: Manipulate file paths (uploads, backups, themes)
- **Impact**: Arbitrary file read/write (Critical)
- **Likelihood**: Medium
- **Mitigations**:
  1. Validate all paths are within allowed directories
  2. Reject `..`, absolute paths, symlinks
  3. Use pathlib with resolve() and is_relative_to()
  4. UUID filenames for uploads

### 4.3 Upload Attacks

#### C1: Malicious File Upload
- **Vector**: Upload executable or script file
- **Impact**: Remote code execution (Critical)
- **Likelihood**: High (if misconfigured)
- **Mitigations**:
  1. Strict allowlist: png, jpg, jpeg, webp, gif only
  2. Magic bytes validation (not just extension)
  3. MIME type verification
  4. Image re-encoding (strips payloads)
  5. UUID filenames
  6. Separate upload directory (non-executable)
  7. Content-Disposition: attachment

#### C2: SVG XSS
- **Vector**: SVG file with embedded JavaScript
- **Impact**: XSS when viewed (High)
- **Likelihood**: High (if SVG allowed)
- **Mitigations**:
  1. SVG uploads banned by default
  2. If enabled: sanitize with svg-sanitizer
  3. Serve with Content-Type: image/svg+xml
  4. CSP blocking inline scripts

#### C3: ImageTragick-style Exploits
- **Vector**: Malicious image exploiting parser vulnerabilities
- **Impact**: RCE via image library (Critical)
- **Likelihood**: Low (modern libraries patched)
- **Mitigations**:
  1. Keep Pillow updated
  2. Re-encode all images
  3. Limit image dimensions
  4. Memory limits on processing

### 4.4 Plugin/Theme Attacks

#### D1: Malicious Plugin Installation
- **Vector**: Admin installs trojanized plugin
- **Impact**: Full server compromise (Critical)
- **Likelihood**: Medium
- **Mitigations**:
  1. No remote installation in MVP
  2. Future: Registry-only with signatures
  3. SHA256 hash verification
  4. Plugin sandboxing (limited API access)
  5. Audit log of plugin changes

#### D2: Zip Slip
- **Vector**: Malicious ZIP with path traversal filenames
- **Impact**: Arbitrary file write (Critical)
- **Likelihood**: Medium
- **Mitigations**:
  1. Validate all ZIP entries stay within target dir
  2. Reject absolute paths, `..`, symlinks
  3. Check before extraction

#### D3: Plugin Privilege Escalation
- **Vector**: Plugin exceeds declared permissions
- **Impact**: Unauthorized actions (High)
- **Likelihood**: Medium
- **Mitigations**:
  1. Permission manifest in plugin.json
  2. API access control based on permissions
  3. No direct filesystem access
  4. No direct database access

### 4.5 Infrastructure Attacks

#### E1: Denial of Service
- **Vector**: Resource exhaustion via requests
- **Impact**: Service unavailability (Medium)
- **Likelihood**: Medium
- **Mitigations**:
  1. Request rate limiting
  2. Request body size limits
  3. Upload size limits
  4. Connection timeouts
  5. Behind reverse proxy (nginx)

#### E2: Information Disclosure
- **Vector**: Error messages, debug info, directory listing
- **Impact**: Attack surface reconnaissance (Medium)
- **Likelihood**: High (if misconfigured)
- **Mitigations**:
  1. Generic error messages in production
  2. No stack traces to users
  3. No directory listing
  4. Security headers (nosniff, etc.)

### 4.6 CSRF Attacks

#### F1: State-Changing CSRF
- **Vector**: Trick admin into clicking malicious link
- **Impact**: Unauthorized actions as admin (High)
- **Likelihood**: Medium
- **Mitigations**:
  1. CSRF tokens on all POST/PUT/DELETE
  2. Double-submit cookie pattern
  3. SameSite cookie attribute
  4. Referer validation

## 5. Security Controls Summary

### 5.1 Authentication & Authorization
- [x] bcrypt password hashing (cost 12)
- [x] Cryptographically random login slug
- [x] Session regeneration on auth events
- [x] Secure cookie attributes
- [x] CSRF protection
- [x] Role-based access control
- [x] Rate limiting

### 5.2 Input Validation
- [x] Markdown sanitization
- [x] HTML allowlist (minimal)
- [x] Path traversal prevention
- [x] Upload validation
- [x] JSON schema validation

### 5.3 Output Encoding
- [x] Jinja2 autoescape
- [x] Content-Type headers
- [x] Content-Security-Policy

### 5.4 Security Headers
- [x] X-Content-Type-Options: nosniff
- [x] X-Frame-Options: SAMEORIGIN
- [x] X-XSS-Protection: 1; mode=block
- [x] Referrer-Policy: strict-origin-when-cross-origin
- [x] Content-Security-Policy
- [x] Strict-Transport-Security (HTTPS)

### 5.5 Logging & Monitoring
- [x] Authentication events
- [x] Authorization failures
- [x] Content modifications
- [x] Plugin/theme changes
- [x] Upload events

## 6. Risk Matrix

| Risk ID | Description | Likelihood | Impact | Risk Level | Priority |
|---------|-------------|------------|--------|------------|----------|
| C1 | Malicious Upload | High | Critical | CRITICAL | P0 |
| D1 | Malicious Plugin | Medium | Critical | HIGH | P0 |
| B1 | XSS | High | High | HIGH | P1 |
| A1 | Brute Force | High | Critical | HIGH | P1 |
| B4 | Path Traversal | Medium | Critical | HIGH | P1 |
| D2 | Zip Slip | Medium | Critical | HIGH | P1 |
| A2 | Session Hijack | Medium | Critical | HIGH | P1 |
| B3 | Template Injection | Low | Critical | MEDIUM | P2 |
| F1 | CSRF | Medium | High | MEDIUM | P2 |
| E1 | DoS | Medium | Medium | MEDIUM | P2 |
| E2 | Info Disclosure | High | Medium | MEDIUM | P2 |

## 7. Acceptance Criteria

Before v1.0 release:
1. All P0 and P1 risks must have implemented mitigations
2. Security test suite passes
3. No known vulnerabilities in dependencies (pip-audit)
4. Static analysis clean (bandit)
5. Manual security review completed

---

**Document Version**: 1.0
**Last Updated**: 2026-01-04
**Review Schedule**: Before each release
