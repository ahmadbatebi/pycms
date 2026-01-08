"""Theme loading and management."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import jdatetime
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound

from .sanitize import Sanitizer


def to_persian_numerals(text: str) -> str:
    """Convert English numerals to Persian numerals.

    Args:
        text: String containing English numerals.

    Returns:
        String with Persian numerals.
    """
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    result = ""
    for char in str(text):
        if char.isdigit():
            result += persian_digits[int(char)]
        else:
            result += char
    return result


def jalali_date(value: str, lang: str = "en") -> str:
    """Convert a date string to Jalali (Persian) calendar format.

    Args:
        value: Date string in ISO format (e.g., "2026-01-05" or "2026-01-05T12:00:00")
        lang: Language code ("fa" for Persian/Jalali, otherwise Gregorian)

    Returns:
        Formatted date string.
    """
    if not value:
        return ""

    try:
        # Parse the date string
        if "T" in value:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00").split("+")[0])
        else:
            dt = datetime.fromisoformat(value)

        if lang == "fa":
            # Convert to Jalali
            jd = jdatetime.date.fromgregorian(date=dt.date())
            # Persian month names
            months = [
                "", "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
            ]
            # Convert numbers to Persian numerals
            day = to_persian_numerals(jd.day)
            year = to_persian_numerals(jd.year)
            return f"{day} {months[jd.month]} {year}"
        else:
            # Return Gregorian format
            return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError, AttributeError):
        # If parsing fails, return original value
        return value[:10] if len(value) >= 10 else value


@dataclass
class ThemeInfo:
    """Theme metadata from theme.json."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    homepage: str = ""
    screenshot: str = ""


@dataclass
class CMSContext:
    """Context passed to theme templates.

    Provides access to site data, page content, and helpers.
    """

    # Site configuration
    site_title: str = ""
    site_lang: str = "en"
    theme: str = "default"

    # Language settings
    lang_direction: str = "ltr"  # 'ltr' or 'rtl'
    current_language: str = "en"  # Current display language
    available_languages: list[dict] = field(default_factory=list)  # [{code, name, native_name, direction}]

    # Current page
    page_title: str = ""
    page_slug: str = ""
    page_content: str = ""  # Rendered HTML
    page_description: str = ""
    page_keywords: str = ""
    page_template: str = "default"  # Template name (light, dark, mixed, default)
    hide_title: bool = False  # Hide title in frontend
    hide_description: bool = False  # Hide description in frontend
    blog_columns: int = 2  # Number of columns for blog posts (1, 2, or 3)
    posts_per_page: int = 10  # Number of blog posts per page

    # Pagination for blog posts
    blog_current_page: int = 1
    blog_total_pages: int = 1
    blog_total_posts: int = 0

    # Navigation
    menu_items: list[dict] = field(default_factory=list)

    # Blocks (rendered HTML)
    blocks: dict[str, str] = field(default_factory=dict)

    # Authentication
    is_admin: bool = False
    is_editor: bool = False
    user: str | None = None
    user_display_name: str | None = None

    # Admin panel HTML (only for logged in users)
    admin_panel: str = ""
    admin_css: str = ""
    admin_js: str = ""
    csrf_token: str = ""

    # Flash messages
    alerts: list[dict] = field(default_factory=list)

    # Blog posts for this page
    blog_posts: list[dict] = field(default_factory=list)

    # Copyright text
    copyright_text: str = ""

    # Search settings
    search_enabled: bool = True
    search_placeholder: str = "Search..."
    search_hint: str = "Type to search..."
    search_no_results: str = "No results found"
    search_navigate: str = "Navigate"
    search_select: str = "Select"
    search_close: str = "Close"
    search_type_page: str = "Page"
    search_type_blog: str = "Post"

    # Jump to Top button
    jump_to_top_enabled: bool = True

    # Theme asset helper (set by ThemeManager)
    _asset_prefix: str = ""

    def asset(self, path: str) -> str:
        """Get URL for theme asset.

        Args:
            path: Relative path within theme's static directory.

        Returns:
            Full URL to asset.
        """
        return f"{self._asset_prefix}/{path}"

    def lang_url(self, lang_code: str) -> str:
        """Get URL for switching to a different language.

        Args:
            lang_code: Target language code.

        Returns:
            URL with lang parameter.
        """
        return f"?lang={lang_code}"


class ThemeManager:
    """Manages theme loading and rendering."""

    def __init__(
        self,
        themes_dir: Path,
        fallback_dir: Path | None = None,
        active_theme: str = "default",
    ):
        """Initialize theme manager.

        Args:
            themes_dir: Path to themes directory.
            fallback_dir: Path to fallback templates (optional).
            active_theme: Name of active theme.
        """
        self.themes_dir = themes_dir
        self.fallback_dir = fallback_dir
        self.active_theme = self._resolve_theme_dir(active_theme)
        self._env: Environment | None = None
        self._theme_info: ThemeInfo | None = None
        self.sanitizer = Sanitizer()

    @property
    def theme_path(self) -> Path:
        """Get path to active theme directory."""
        return self.themes_dir / self.active_theme

    @property
    def templates_path(self) -> Path:
        """Get path to active theme's templates."""
        return self.theme_path / "templates"

    @property
    def static_path(self) -> Path:
        """Get path to active theme's static files."""
        return self.theme_path / "static"

    def _resolve_theme_dir(self, theme: str) -> str:
        """Resolve a theme name to its directory.

        Allows matching by directory name or theme.json display name.
        Falls back to "default" when available.
        """
        theme = (theme or "").strip()
        if not theme:
            theme = "default"

        direct_path = self.themes_dir / theme
        if direct_path.exists():
            return theme

        if self.themes_dir.exists():
            for entry in self.themes_dir.iterdir():
                if entry.is_dir() and entry.name.lower() == theme.lower():
                    return entry.name

            for entry in self.themes_dir.iterdir():
                if not entry.is_dir():
                    continue
                json_path = entry / "theme.json"
                if not json_path.exists():
                    continue
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if str(data.get("name", "")).lower() == theme.lower():
                        return entry.name
                except (json.JSONDecodeError, OSError):
                    continue

        if (self.themes_dir / "default").exists():
            return "default"

        return theme

    def get_theme_info(self) -> ThemeInfo:
        """Load and return theme metadata.

        Returns:
            ThemeInfo with theme metadata.
        """
        if self._theme_info is not None:
            return self._theme_info

        json_path = self.theme_path / "theme.json"
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._theme_info = ThemeInfo(
                    name=data.get("name", self.active_theme),
                    version=data.get("version", "1.0.0"),
                    description=data.get("description", ""),
                    author=data.get("author", ""),
                    homepage=data.get("homepage", ""),
                    screenshot=data.get("screenshot", ""),
                )
            except (json.JSONDecodeError, OSError):
                self._theme_info = ThemeInfo(name=self.active_theme)
        else:
            self._theme_info = ThemeInfo(name=self.active_theme)

        return self._theme_info

    def get_env(self) -> Environment:
        """Get or create Jinja2 environment.

        Returns:
            Configured Jinja2 Environment.
        """
        if self._env is not None:
            return self._env

        # Build loader paths
        loader_paths = []

        # Theme templates first
        if self.templates_path.exists():
            loader_paths.append(str(self.templates_path))

        # Fallback templates
        if self.fallback_dir and self.fallback_dir.exists():
            loader_paths.append(str(self.fallback_dir))

        if not loader_paths:
            raise RuntimeError(f"No template directories found for theme: {self.active_theme}")

        self._env = Environment(
            loader=FileSystemLoader(loader_paths),
            autoescape=select_autoescape(["html", "htm", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self._env.filters["render_markdown"] = self.sanitizer.render_markdown
        self._env.filters["jalali_date"] = jalali_date

        return self._env

    def set_active_theme(self, theme: str) -> None:
        """Change active theme.

        Args:
            theme: Theme directory name.
        """
        self.active_theme = self._resolve_theme_dir(theme)
        self._env = None
        self._theme_info = None

    def render(
        self,
        template_name: str,
        context: CMSContext,
        allow_fallback: bool = True,
        **extra: Any,
    ) -> str:
        """Render a template with context.

        Args:
            template_name: Template filename (e.g., "page.html").
            context: CMSContext with page data.
            **extra: Additional template variables.

        Returns:
            Rendered HTML string.
        """
        env = self.get_env()

        try:
            template = env.get_template(template_name)
        except TemplateNotFound:
            if not allow_fallback:
                raise
            # Try base template as fallback
            template = env.get_template("base.html")

        # Build template context
        ctx = {
            "cms": context,
            "site": {
                "title": context.site_title,
                "lang": context.site_lang,
                "theme": context.theme,
            },
            "page": {
                "title": context.page_title,
                "slug": context.page_slug,
                "content": context.page_content,
                "description": context.page_description,
                "keywords": context.page_keywords,
            },
            "lang": {
                "code": context.current_language,
                "direction": context.lang_direction,
                "is_rtl": context.lang_direction == "rtl",
                "available": context.available_languages,
            },
            "menu": context.menu_items,
            "blocks": context.blocks,
            "is_admin": context.is_admin,
            "is_editor": context.is_editor,
            "user": context.user,
            "csrf_token": context.csrf_token,
            "alerts": context.alerts,
            **extra,
        }

        return template.render(**ctx)

    def render_page(self, context: CMSContext) -> str:
        """Render a page using the page template.

        Template resolution order:
        1. {slug}.html (page-specific template)
        2. page-{template}.html (selected template: light, dark, mixed)
        3. page.html (default page template)
        4. base.html (fallback)

        Args:
            context: CMSContext with page data.

        Returns:
            Rendered HTML.
        """
        env = self.get_env()

        # Normalize template name
        template = (context.page_template or "default").strip().lower()
        if template not in {"default", "light", "dark", "mixed"}:
            template = "default"
        context.page_template = template

        # Build list of templates to try
        templates_to_try = [
            f"{context.page_slug}.html",
        ]

        # Add selected template if not default
        if context.page_template != "default":
            templates_to_try.append(f"page-{context.page_template}.html")

        # Always try page.html and base.html as fallbacks
        templates_to_try.extend(["page.html", "base.html"])

        for template_name in templates_to_try:
            try:
                return self.render(template_name, context, allow_fallback=False)
            except TemplateNotFound:
                continue

        raise RuntimeError("No valid template found")

    def render_404(self, context: CMSContext) -> str:
        """Render 404 error page.

        Args:
            context: CMSContext with 404 page data.

        Returns:
            Rendered HTML.
        """
        try:
            return self.render("404.html", context, allow_fallback=False)
        except TemplateNotFound:
            return self.render("page.html", context, allow_fallback=True)

    def list_themes(self) -> list[ThemeInfo]:
        """List all available themes.

        Returns:
            List of ThemeInfo for each theme.
        """
        themes = []

        if not self.themes_dir.exists():
            return themes

        for theme_dir in self.themes_dir.iterdir():
            if not theme_dir.is_dir():
                continue

            # Check for required files
            templates = theme_dir / "templates"
            if not templates.exists():
                continue

            # Load theme info
            json_path = theme_dir / "theme.json"
            if json_path.exists():
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    themes.append(
                        ThemeInfo(
                            name=data.get("name", theme_dir.name),
                            version=data.get("version", "1.0.0"),
                            description=data.get("description", ""),
                            author=data.get("author", ""),
                        )
                    )
                except (json.JSONDecodeError, OSError):
                    themes.append(ThemeInfo(name=theme_dir.name))
            else:
                themes.append(ThemeInfo(name=theme_dir.name))

        return themes
