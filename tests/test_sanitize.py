"""Tests for content sanitization."""

import pytest
from pathlib import Path

from pressassist.core.sanitize import Sanitizer, SanitizationError


class TestHTMLSanitization:
    """Tests for HTML sanitization."""

    def test_allows_safe_tags(self):
        """Test that safe tags are preserved."""
        sanitizer = Sanitizer()
        html = "<p>Hello <strong>world</strong></p>"
        result = sanitizer.sanitize_html(html)

        assert "<p>" in result
        assert "<strong>" in result

    def test_removes_script_tags(self):
        """Test that script tags are removed."""
        sanitizer = Sanitizer()
        html = "<p>Hello</p><script>alert('xss')</script>"
        result = sanitizer.sanitize_html(html)

        assert "<script>" not in result
        assert "alert" not in result

    def test_removes_event_handlers(self):
        """Test that on* event handlers are removed."""
        sanitizer = Sanitizer()
        html = '<p onclick="alert(1)">Click me</p>'
        result = sanitizer.sanitize_html(html)

        assert "onclick" not in result
        assert "alert" not in result

    def test_removes_javascript_urls(self):
        """Test that javascript: URLs are removed."""
        sanitizer = Sanitizer()
        html = '<a href="javascript:alert(1)">Click</a>'
        result = sanitizer.sanitize_html(html)

        assert "javascript:" not in result

    def test_allows_safe_links(self):
        """Test that safe links are preserved."""
        sanitizer = Sanitizer()
        html = '<a href="https://example.com">Link</a>'
        result = sanitizer.sanitize_html(html)

        assert 'href="https://example.com"' in result

    def test_removes_iframe(self):
        """Test that iframe is removed."""
        sanitizer = Sanitizer()
        html = '<iframe src="https://evil.com"></iframe>'
        result = sanitizer.sanitize_html(html)

        assert "<iframe" not in result

    def test_removes_object_embed(self):
        """Test that object and embed are removed."""
        sanitizer = Sanitizer()
        html = '<object data="x"></object><embed src="y">'
        result = sanitizer.sanitize_html(html)

        assert "<object" not in result
        assert "<embed" not in result

    def test_preserves_images(self):
        """Test that img tags are preserved with safe attrs."""
        sanitizer = Sanitizer()
        html = '<img src="/image.jpg" alt="Test">'
        result = sanitizer.sanitize_html(html)

        assert "<img" in result
        assert 'src="/image.jpg"' in result
        assert 'alt="Test"' in result

    def test_removes_data_urls_in_images(self):
        """Test that data: URLs in images are removed."""
        sanitizer = Sanitizer()
        html = '<img src="data:image/png;base64,xxx">'
        result = sanitizer.sanitize_html(html)

        # bleach removes dangerous protocols
        assert "data:" not in result

    def test_empty_input(self):
        """Test empty input returns empty string."""
        sanitizer = Sanitizer()

        assert sanitizer.sanitize_html("") == ""
        assert sanitizer.sanitize_html(None) == ""


class TestMarkdownRendering:
    """Tests for Markdown rendering."""

    def test_renders_headings(self):
        """Test heading rendering."""
        sanitizer = Sanitizer()
        md = "# Hello World"
        result = sanitizer.render_markdown(md)

        assert "<h1>" in result
        assert "Hello World" in result

    def test_renders_paragraphs(self):
        """Test paragraph rendering."""
        sanitizer = Sanitizer()
        md = "This is a paragraph."
        result = sanitizer.render_markdown(md)

        assert "<p>" in result

    def test_renders_links(self):
        """Test link rendering."""
        sanitizer = Sanitizer()
        md = "[Link](https://example.com)"
        result = sanitizer.render_markdown(md)

        assert "<a" in result
        assert "https://example.com" in result

    def test_renders_code_blocks(self):
        """Test code block rendering."""
        sanitizer = Sanitizer()
        md = "```\ncode here\n```"
        result = sanitizer.render_markdown(md)

        assert "<code>" in result or "<pre>" in result

    def test_sanitizes_markdown_output(self):
        """Test that rendered Markdown is sanitized."""
        sanitizer = Sanitizer()
        # Even if raw HTML somehow gets in, it's sanitized
        md = "Hello <script>alert(1)</script>"
        result = sanitizer.render_markdown(md)

        assert "<script>" not in result

    def test_empty_markdown(self):
        """Test empty Markdown returns empty string."""
        sanitizer = Sanitizer()

        assert sanitizer.render_markdown("") == ""


class TestFilenameSanitization:
    """Tests for filename sanitization."""

    def test_preserves_safe_names(self):
        """Test safe filenames are preserved."""
        sanitizer = Sanitizer()

        assert sanitizer.sanitize_filename("photo.jpg") == "photo.jpg"
        assert sanitizer.sanitize_filename("my-file.pdf") == "my-file.pdf"

    def test_removes_path_components(self):
        """Test path components are removed."""
        sanitizer = Sanitizer()

        assert sanitizer.sanitize_filename("/etc/passwd") == "passwd"
        assert sanitizer.sanitize_filename("../../../etc/passwd") == "passwd"

    def test_replaces_spaces(self):
        """Test spaces are replaced with underscores."""
        sanitizer = Sanitizer()

        assert sanitizer.sanitize_filename("my file.jpg") == "my_file.jpg"

    def test_removes_dangerous_chars(self):
        """Test dangerous characters are removed."""
        sanitizer = Sanitizer()

        result = sanitizer.sanitize_filename("file<>:\"|?*.txt")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result

    def test_removes_leading_dots(self):
        """Test leading dots (hidden files) are removed."""
        sanitizer = Sanitizer()

        assert sanitizer.sanitize_filename(".htaccess") == "htaccess"
        assert sanitizer.sanitize_filename("...file") == "file"

    def test_limits_length(self):
        """Test filename length is limited."""
        sanitizer = Sanitizer()
        long_name = "a" * 300 + ".txt"
        result = sanitizer.sanitize_filename(long_name)

        assert len(result) <= 200

    def test_empty_filename_raises(self):
        """Test empty filename raises error."""
        sanitizer = Sanitizer()

        with pytest.raises(SanitizationError):
            sanitizer.sanitize_filename("")

    def test_only_dangerous_chars_raises(self):
        """Test filename with only dangerous chars raises error."""
        sanitizer = Sanitizer()

        with pytest.raises(SanitizationError):
            sanitizer.sanitize_filename(".....")


class TestPathValidation:
    """Tests for path validation."""

    def test_valid_relative_path(self):
        """Test valid relative path within base."""
        sanitizer = Sanitizer()
        base = Path("/var/www/uploads")
        path = Path("/var/www/uploads/image.jpg")

        assert sanitizer.validate_path(path, base) is True

    def test_valid_nested_path(self):
        """Test valid nested path within base."""
        sanitizer = Sanitizer()
        base = Path("/var/www/uploads")
        path = Path("/var/www/uploads/2024/01/image.jpg")

        assert sanitizer.validate_path(path, base) is True

    def test_rejects_path_traversal(self):
        """Test path traversal is rejected."""
        sanitizer = Sanitizer()
        base = Path("/var/www/uploads")
        path = Path("/var/www/uploads/../secrets/passwd")

        assert sanitizer.validate_path(path, base) is False

    def test_rejects_outside_base(self):
        """Test paths outside base are rejected."""
        sanitizer = Sanitizer()
        base = Path("/var/www/uploads")
        path = Path("/etc/passwd")

        assert sanitizer.validate_path(path, base) is False


class TestSlugValidation:
    """Tests for URL slug validation."""

    def test_valid_slugs(self):
        """Test valid slug patterns."""
        sanitizer = Sanitizer()

        assert sanitizer.validate_slug("home") is True
        assert sanitizer.validate_slug("about-us") is True
        assert sanitizer.validate_slug("page-1") is True
        assert sanitizer.validate_slug("my-long-page-title") is True

    def test_invalid_slugs(self):
        """Test invalid slug patterns."""
        sanitizer = Sanitizer()

        assert sanitizer.validate_slug("") is False
        assert sanitizer.validate_slug("About") is False  # Uppercase
        assert sanitizer.validate_slug("about us") is False  # Space
        assert sanitizer.validate_slug("about_us") is False  # Underscore
        assert sanitizer.validate_slug("-about") is False  # Leading dash
        assert sanitizer.validate_slug("about-") is False  # Trailing dash


class TestSlugify:
    """Tests for text to slug conversion."""

    def test_basic_slugify(self):
        """Test basic slug conversion."""
        sanitizer = Sanitizer()

        assert sanitizer.slugify("Hello World") == "hello-world"
        assert sanitizer.slugify("About Us") == "about-us"

    def test_removes_special_chars(self):
        """Test special characters are removed."""
        sanitizer = Sanitizer()

        assert sanitizer.slugify("Hello! World?") == "hello-world"
        assert sanitizer.slugify("Test@123") == "test123"

    def test_handles_unicode(self):
        """Test unicode handling."""
        sanitizer = Sanitizer()
        # Converts to ASCII equivalent where possible
        result = sanitizer.slugify("cafe")
        assert result == "cafe"

    def test_empty_returns_untitled(self):
        """Test empty string returns 'untitled'."""
        sanitizer = Sanitizer()

        assert sanitizer.slugify("") == "untitled"
        assert sanitizer.slugify("   ") == "untitled"
