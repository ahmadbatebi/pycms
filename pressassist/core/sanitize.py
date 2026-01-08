"""Content sanitization for security."""

import re
import unicodedata
from pathlib import Path
from typing import Optional

import bleach
try:
    from bleach.css_sanitizer import CSSSanitizer
except Exception:  # pragma: no cover - optional dependency across bleach versions
    CSSSanitizer = None
from markdown_it import MarkdownIt


class SanitizationError(Exception):
    """Error during content sanitization."""

    pass


class Sanitizer:
    """Content sanitization utilities.

    Provides secure handling of:
    - HTML content (strict allowlist)
    - Markdown rendering
    - Filenames
    - Path validation
    """

    # Safe HTML tags (extended for WYSIWYG editor support)
    ALLOWED_TAGS = [
        # Basic text formatting
        "p",
        "br",
        "strong",
        "b",
        "em",
        "i",
        "u",
        "s",
        "a",
        "span",
        "mark",
        # Lists
        "ul",
        "ol",
        "li",
        # Headings
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        # Blocks
        "blockquote",
        "code",
        "pre",
        "hr",
        "div",
        # Images and figures
        "img",
        "figure",
        "figcaption",
        # Tables
        "table",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "th",
        "td",
        "caption",
        "colgroup",
        "col",
        # Text formatting (WYSIWYG)
        "sup",
        "sub",
        # Media (embedded)
        "video",
        "audio",
        "source",
        # NOTE: iframe is intentionally NOT allowed due to security risks (XSS, clickjacking)
        # See: OWASP guidelines on iframe security
    ]

    # Safe attributes per tag (extended for WYSIWYG)
    ALLOWED_ATTRIBUTES = {
        "a": ["href", "title", "rel", "target"],
        "img": ["src", "alt", "title", "width", "height", "class", "loading", "style"],
        "th": ["scope", "colspan", "rowspan", "style"],
        "td": ["colspan", "rowspan", "style"],
        "table": ["class", "style"],
        "col": ["style", "width"],
        "colgroup": ["span"],
        # WYSIWYG specific
        "span": ["style", "class"],
        "mark": ["style", "class"],
        "div": ["style", "class", "dir"],
        "p": ["style", "class", "dir"],
        "h1": ["style", "class", "dir"],
        "h2": ["style", "class", "dir"],
        "h3": ["style", "class", "dir"],
        "h4": ["style", "class", "dir"],
        "h5": ["style", "class", "dir"],
        "h6": ["style", "class", "dir"],
        "figure": ["class", "style"],
        "figcaption": ["class", "style"],
        "blockquote": ["class"],
        "pre": ["class"],
        "code": ["class"],
        # Media embeds (iframe removed for security)
        "video": ["src", "controls", "width", "height", "poster", "style"],
        "audio": ["src", "controls"],
        "source": ["src", "type"],
        # Lists
        "ul": ["class", "style"],
        "ol": ["class", "style", "start", "type"],
        "li": ["class", "style", "dir"],
    }

    # Allowed CSS properties for inline styles (to prevent XSS via CSS)
    ALLOWED_STYLE_PROPERTIES = [
        "color",
        "background-color",
        "font-size",
        "font-weight",
        "font-style",
        "font-family",
        "text-align",
        "text-decoration",
        "vertical-align",
        "width",
        "height",
        "max-width",
        "min-width",
        "margin",
        "margin-top",
        "margin-right",
        "margin-bottom",
        "margin-left",
        "padding",
        "padding-top",
        "padding-right",
        "padding-bottom",
        "padding-left",
        "border",
        "border-width",
        "border-style",
        "border-color",
        "border-collapse",
        "direction",
        "float",
        "display",
        "list-style-type",
        "position",
        "top",
        "left",
        "right",
        "bottom",
        "overflow",
        "max-height",
        "min-height",
    ]

    # Safe URL schemes
    ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

    # Dangerous patterns to strip
    DANGEROUS_PATTERNS = [
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"vbscript:", re.IGNORECASE),
        re.compile(r"data:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),  # Event handlers
    ]

    # CKEditor widget labels that shouldn't be saved (accessibility text)
    CKEDITOR_WIDGET_PATTERNS = [
        # Media widget labels (Persian)
        re.compile(
            r"ویجت رسانه\.\s*Press Enter to type after or press Shift \+ Enter to type "
            r"before the widget",
            re.IGNORECASE,
        ),
        # Image widget labels with any alt text (Persian) - matches "تصویر ALT_TEXT ابزاره تصویر. Press..."
        re.compile(
            r"تصویر\s+[^\n]*?\s*ابزاره تصویر\.\s*Press Enter to type after or press Shift \+ "
            r"Enter to type before the widget",
            re.IGNORECASE,
        ),
        # Simple image widget label (Persian)
        re.compile(
            r"ابزاره تصویر\.\s*Press Enter to type after or press Shift \+ Enter to type "
            r"before the widget",
            re.IGNORECASE,
        ),
        # English versions
        re.compile(
            r"Media widget\.\s*Press Enter to type after or press Shift \+ Enter to type "
            r"before the widget",
            re.IGNORECASE,
        ),
        re.compile(
            r"Image widget\.\s*Press Enter to type after or press Shift \+ Enter to type "
            r"before the widget",
            re.IGNORECASE,
        ),
        re.compile(
            r"Widget toolbar\.\s*Press Enter to type after or press Shift \+ Enter to type "
            r"before the widget",
            re.IGNORECASE,
        ),
        # Image with alt text (English)
        re.compile(
            r"[^\n<>]*?\s*Image widget\.\s*Press Enter to type after or press Shift \+ "
            r"Enter to type before the widget",
            re.IGNORECASE,
        ),
        # Catch any remaining widget instructions
        re.compile(
            r"Press Enter to type after or press Shift \+ Enter to type before the widget",
            re.IGNORECASE,
        ),
        # Standalone Persian labels that might remain (outside of HTML tags)
        re.compile(r"(?<![\"'>])ابزاره تصویر\.(?![\"'<])", re.IGNORECASE),
        re.compile(r"(?<![\"'>])ویجت رسانه\.(?![\"'<])", re.IGNORECASE),
    ]

    # Patterns to clean AFTER bleach sanitization (when HTML is safe)
    POST_BLEACH_PATTERNS = [
        # Standalone lines with alt text artifacts (after </figure> or </p>)
        re.compile(r"(?<=>)\s*\n\s*تصویر\s+\S+\s*\n\s*\n", re.IGNORECASE),
    ]

    # Tags whose content should be completely removed (not just the tag)
    STRIP_CONTENT_TAGS = re.compile(
        r"<(script|style|noscript|template|svg|math)[^>]*>.*?</\1>",
        re.IGNORECASE | re.DOTALL,
    )
    HTML_LIKE_RE = re.compile(r"</?[a-z][\w:-]*(\s[^>]*?)?>", re.IGNORECASE)
    ALIGN_STYLE_RE = re.compile(r"text-align\s*:\s*(left|right|center|justify)", re.IGNORECASE)
    TAG_WITH_STYLE_RE = re.compile(
        r"<([a-z][\w:-]*)([^>]*?)\sstyle=\"([^\"]*?)\"([^>]*?)>",
        re.IGNORECASE,
    )

    def __init__(self, allow_html: bool = False):
        """Initialize sanitizer.

        Args:
            allow_html: Whether to allow sanitized HTML (vs Markdown only).
        """
        self.allow_html = allow_html
        self.md = MarkdownIt("commonmark", {"html": False})  # Disable raw HTML in Markdown
        self._css_sanitizer = None
        if CSSSanitizer is not None:
            self._css_sanitizer = CSSSanitizer(
                allowed_css_properties=self.ALLOWED_STYLE_PROPERTIES
            )

    def sanitize_style(self, style: str) -> str:
        """Sanitize inline CSS style attribute.

        Args:
            style: CSS style string to sanitize.

        Returns:
            Sanitized CSS style string.
        """
        if not style:
            return ""

        sanitized = []
        for declaration in style.split(";"):
            if ":" not in declaration:
                continue
            prop, value = declaration.split(":", 1)
            prop = prop.strip().lower()
            value = value.strip()

            # Check property is allowed
            if prop not in self.ALLOWED_STYLE_PROPERTIES:
                continue

            # Check for dangerous patterns in value
            value_lower = value.lower()
            if any(p in value_lower for p in ["javascript:", "expression(", "url(", "behavior:"]):
                continue

            sanitized.append(f"{prop}: {value}")

        return "; ".join(sanitized)

    def _style_filter(self, tag: str, name: str, value: str) -> bool | str:
        """Custom attribute filter for bleach that sanitizes style attributes.

        Args:
            tag: HTML tag name.
            name: Attribute name.
            value: Attribute value.

        Returns:
            True if attribute is allowed, sanitized value for style, False otherwise.
        """
        # Check if this tag-attribute combination is allowed
        allowed_attrs = self.ALLOWED_ATTRIBUTES.get(tag, [])
        if name not in allowed_attrs:
            return False

        # Special handling for style attribute
        if name == "style":
            if self._css_sanitizer is not None:
                return True
            sanitized = self.sanitize_style(value)
            return sanitized if sanitized else False

        return True

    def sanitize_html(self, content: str) -> str:
        """Sanitize HTML content with strict allowlist.

        Args:
            content: HTML content to sanitize.

        Returns:
            Sanitized HTML string.
        """
        if not content:
            return ""

        # First pass: remove CKEditor widget accessibility text BEFORE bleach
        # This must be done first because these are plain text that bleach won't touch
        clean = content
        for pattern in self.CKEDITOR_WIDGET_PATTERNS:
            clean = pattern.sub("", clean)

        # Second pass: normalize alignment styles into classes and remove dangerous tags.
        clean = self._normalize_alignment_classes(clean)
        clean = self.STRIP_CONTENT_TAGS.sub("", clean)

        # Third pass: bleach with strict settings and style sanitization
        clean_kwargs = {
            "tags": self.ALLOWED_TAGS,
            "attributes": self._style_filter,
            "protocols": self.ALLOWED_PROTOCOLS,
            "strip": True,
            "strip_comments": True,
        }
        if self._css_sanitizer is not None:
            clean_kwargs["css_sanitizer"] = self._css_sanitizer

        clean = bleach.clean(clean, **clean_kwargs)

        # Fourth pass: remove any remaining dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            clean = pattern.sub("", clean)

        # Fifth pass: remove post-bleach patterns (safe text artifacts)
        for pattern in self.POST_BLEACH_PATTERNS:
            clean = pattern.sub("\n", clean)

        # Clean up empty paragraphs left behind
        clean = re.sub(r"<p>\s*</p>", "", clean)
        clean = re.sub(r"<p>&nbsp;</p>", "", clean)

        # Clean up multiple newlines
        clean = re.sub(r"\n\s*\n\s*\n", "\n\n", clean)

        return clean.strip()

    def render_markdown(self, content: str) -> str:
        """Render Markdown to sanitized HTML.

        Args:
            content: Markdown content.

        Returns:
            Sanitized HTML string.
        """
        if not content:
            return ""

        # Render Markdown (raw HTML disabled)
        html = self.md.render(content)

        # Sanitize output just in case
        return self.sanitize_html(html)

    def sanitize_content(self, content: str, format: str = "markdown") -> str:
        """Sanitize content based on format.

        Args:
            content: Content to sanitize.
            format: Content format ("markdown" or "html").

        Returns:
            Sanitized content.

        Raises:
            SanitizationError: If HTML not allowed but requested.
        """
        if format == "markdown":
            return content  # Markdown is rendered at display time
        elif format == "html":
            if not self.allow_html:
                raise SanitizationError("HTML content is not allowed")
            return self.sanitize_html(content)
        else:
            raise SanitizationError(f"Unknown content format: {format}")

    def render_content(self, content: str, format: str = "markdown") -> str:
        """Render content to display HTML.

        Args:
            content: Raw content.
            format: Content format.

        Returns:
            HTML ready for display.
        """
        if format == "markdown":
            if self._looks_like_html(content):
                return self.sanitize_html(content)
            return self.render_markdown(content)
        elif format == "html":
            return self.sanitize_html(content)
        else:
            return self.sanitize_html(content)

    def _looks_like_html(self, content: str) -> bool:
        if not content or "<" not in content:
            return False
        return bool(self.HTML_LIKE_RE.search(content))

    def _normalize_alignment_classes(self, content: str) -> str:
        def _replace(match: re.Match) -> str:
            tag, before, style, after = match.groups()
            align_match = self.ALIGN_STYLE_RE.search(style)
            if not align_match:
                return match.group(0)

            align_class = f"text-align-{align_match.group(1).lower()}"
            attrs = f"{before} {after}".strip()

            class_match = re.search(r"\bclass=\"([^\"]*)\"", attrs, re.IGNORECASE)
            if class_match:
                classes = class_match.group(1).split()
                if align_class not in classes:
                    classes.append(align_class)
                new_class = " ".join(classes)
                attrs = (
                    attrs[:class_match.start()]
                    + f'class="{new_class}"'
                    + attrs[class_match.end():]
                )
            else:
                attrs = f'{attrs} class="{align_class}"' if attrs else f'class="{align_class}"'

            return f"<{tag}{(' ' + attrs) if attrs else ''}>"

        return self.TAG_WITH_STYLE_RE.sub(_replace, content)

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename for safe storage.

        Args:
            filename: Original filename.

        Returns:
            Safe filename.

        Raises:
            SanitizationError: If filename is invalid.
        """
        if not filename:
            raise SanitizationError("Empty filename")

        # Normalize unicode
        filename = unicodedata.normalize("NFKC", filename)

        # Get just the filename part (no path)
        filename = Path(filename).name

        # Remove or replace dangerous characters
        # Keep only alphanumeric, dash, underscore, dot
        safe_chars = []
        for char in filename:
            if char.isalnum() or char in "-_.":
                safe_chars.append(char)
            elif char == " ":
                safe_chars.append("_")
        filename = "".join(safe_chars)

        # Remove leading dots (hidden files)
        filename = filename.lstrip(".")

        # Limit length
        if len(filename) > 200:
            name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
            filename = name[: 200 - len(ext) - 1] + "." + ext if ext else name[:200]

        if not filename:
            raise SanitizationError("Filename contains no valid characters")

        return filename

    def validate_path(self, path: Path, base: Path) -> bool:
        """Validate that a path is within allowed base directory.

        Prevents path traversal attacks.

        Args:
            path: Path to validate.
            base: Base directory path must be within.

        Returns:
            True if path is safe.
        """
        try:
            # Resolve to absolute path
            resolved = path.resolve()
            base_resolved = base.resolve()

            # Check if path is within base
            return resolved.is_relative_to(base_resolved)
        except (ValueError, RuntimeError):
            return False

    def validate_slug(self, slug: str) -> bool:
        """Validate a URL slug.

        Args:
            slug: Slug to validate.

        Returns:
            True if valid.
        """
        if not slug:
            return False

        # Must be lowercase alphanumeric with hyphens
        return bool(re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", slug))

    def slugify(self, text: str) -> str:
        """Convert text to URL-safe slug.

        Supports Persian/Arabic and other Unicode characters.

        Args:
            text: Text to convert.

        Returns:
            URL-safe slug.
        """
        # Normalize unicode (NFC keeps composed characters for non-Latin scripts)
        text = unicodedata.normalize("NFC", text)

        # Lowercase (works for Latin characters)
        text = text.lower()

        # Replace spaces and underscores with hyphens
        text = re.sub(r"[\s_]+", "-", text)

        # Keep alphanumeric, hyphens, and Persian/Arabic Unicode ranges
        # \u0600-\u06FF: Arabic/Persian
        # \u0750-\u077F: Arabic Supplement
        # \uFB50-\uFDFF: Arabic Presentation Forms-A
        # \uFE70-\uFEFF: Arabic Presentation Forms-B
        text = re.sub(r"[^a-z0-9\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF-]", "", text)

        # Remove multiple consecutive hyphens
        text = re.sub(r"-+", "-", text)

        # Remove leading/trailing hyphens
        text = text.strip("-")

        return text or "untitled"
