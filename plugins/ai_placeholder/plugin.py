"""AI Placeholder plugin for PressAssistCMS.

IMPORTANT SECURITY PRINCIPLES:
1. This plugin NEVER modifies content automatically
2. All AI suggestions require explicit admin approval
3. No direct access to storage - only through official API
4. No content changes during save operations

This is a skeleton for future AI integration.
"""


def on_load(api):
    """Called when plugin is enabled.

    Args:
        api: PluginAPI instance.
    """
    # This plugin only provides an API endpoint for suggestions
    # It does NOT hook into save operations
    pass


def on_unload():
    """Called when plugin is disabled."""
    pass


class AISuggestionService:
    """Service for generating AI content suggestions.

    All suggestions are proposals that require admin approval.
    They are NEVER applied automatically.
    """

    def __init__(self):
        """Initialize the suggestion service."""
        self.enabled = False  # Disabled by default

    def suggest_title(self, content: str) -> str | None:
        """Suggest a title for content.

        Args:
            content: Page content.

        Returns:
            Suggested title or None.

        Note:
            This is a placeholder. In a real implementation,
            this would call an AI service.
        """
        if not self.enabled:
            return None

        # Placeholder - would call AI service here
        return None

    def suggest_description(self, content: str) -> str | None:
        """Suggest a meta description.

        Args:
            content: Page content.

        Returns:
            Suggested description or None.
        """
        if not self.enabled:
            return None

        # Placeholder - would call AI service here
        return None

    def suggest_keywords(self, content: str) -> list[str] | None:
        """Suggest keywords for SEO.

        Args:
            content: Page content.

        Returns:
            List of suggested keywords or None.
        """
        if not self.enabled:
            return None

        # Placeholder - would call AI service here
        return None


# Global service instance (disabled by default)
ai_service = AISuggestionService()
