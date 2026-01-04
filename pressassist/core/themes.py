"""Theme loading and management."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound

from .sanitize import Sanitizer


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

    # Current page
    page_title: str = ""
    page_slug: str = ""
    page_content: str = ""  # Rendered HTML
    page_description: str = ""
    page_keywords: str = ""

    # Navigation
    menu_items: list[dict] = field(default_factory=list)

    # Blocks (rendered HTML)
    blocks: dict[str, str] = field(default_factory=dict)

    # Authentication
    is_admin: bool = False
    is_editor: bool = False
    user: str | None = None

    # Admin panel HTML (only for logged in users)
    admin_panel: str = ""
    admin_css: str = ""
    admin_js: str = ""
    csrf_token: str = ""

    # Flash messages
    alerts: list[dict] = field(default_factory=list)

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
        self.active_theme = active_theme
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

        return self._env

    def set_active_theme(self, theme: str) -> None:
        """Change active theme.

        Args:
            theme: Theme directory name.
        """
        self.active_theme = theme
        self._env = None
        self._theme_info = None

    def render(
        self,
        template_name: str,
        context: CMSContext,
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

        First tries {slug}.html, then page.html, then base.html.

        Args:
            context: CMSContext with page data.

        Returns:
            Rendered HTML.
        """
        env = self.get_env()

        # Try page-specific template
        templates_to_try = [
            f"{context.page_slug}.html",
            "page.html",
            "base.html",
        ]

        for template_name in templates_to_try:
            try:
                return self.render(template_name, context)
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
            return self.render("404.html", context)
        except TemplateNotFound:
            return self.render("page.html", context)

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
