"""Content sanitization for security."""

import re
import unicodedata
from pathlib import Path
from typing import Optional

import bleach
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

    # Minimal safe HTML tags
    ALLOWED_TAGS = [
        "p",
        "br",
        "strong",
        "b",
        "em",
        "i",
        "u",
        "s",
        "a",
        "ul",
        "ol",
        "li",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "blockquote",
        "code",
        "pre",
        "hr",
        "img",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
    ]

    # Safe attributes per tag
    ALLOWED_ATTRIBUTES = {
        "a": ["href", "title", "rel"],
        "img": ["src", "alt", "title", "width", "height"],
        "th": ["scope"],
        "td": ["colspan", "rowspan"],
    }

    # Safe URL schemes
    ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

    # Dangerous patterns to strip
    DANGEROUS_PATTERNS = [
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"vbscript:", re.IGNORECASE),
        re.compile(r"data:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),  # Event handlers
    ]

    # Tags whose content should be completely removed (not just the tag)
    STRIP_CONTENT_TAGS = re.compile(
        r"<(script|style|noscript|template|svg|math)[^>]*>.*?</\1>",
        re.IGNORECASE | re.DOTALL,
    )

    def __init__(self, allow_html: bool = False):
        """Initialize sanitizer.

        Args:
            allow_html: Whether to allow sanitized HTML (vs Markdown only).
        """
        self.allow_html = allow_html
        self.md = MarkdownIt("commonmark", {"html": False})  # Disable raw HTML in Markdown

    def sanitize_html(self, content: str) -> str:
        """Sanitize HTML content with strict allowlist.

        Args:
            content: HTML content to sanitize.

        Returns:
            Sanitized HTML string.
        """
        if not content:
            return ""

        # First pass: remove dangerous tags WITH their content (script, style, etc.)
        clean = self.STRIP_CONTENT_TAGS.sub("", content)

        # Second pass: bleach with strict settings
        clean = bleach.clean(
            clean,
            tags=self.ALLOWED_TAGS,
            attributes=self.ALLOWED_ATTRIBUTES,
            protocols=self.ALLOWED_PROTOCOLS,
            strip=True,
            strip_comments=True,
        )

        # Third pass: remove any remaining dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            clean = pattern.sub("", clean)

        return clean

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
            return self.render_markdown(content)
        elif format == "html":
            return self.sanitize_html(content)
        else:
            return self.sanitize_html(content)

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

        Args:
            text: Text to convert.

        Returns:
            URL-safe slug.
        """
        # Normalize unicode
        text = unicodedata.normalize("NFKD", text)

        # Convert to ASCII
        text = text.encode("ascii", "ignore").decode("ascii")

        # Lowercase
        text = text.lower()

        # Replace spaces and underscores with hyphens
        text = re.sub(r"[\s_]+", "-", text)

        # Remove non-alphanumeric except hyphens
        text = re.sub(r"[^a-z0-9-]", "", text)

        # Remove multiple consecutive hyphens
        text = re.sub(r"-+", "-", text)

        # Remove leading/trailing hyphens
        text = text.strip("-")

        return text or "untitled"
