"""Internationalization (i18n) support for ChelCheleh."""

import json
from pathlib import Path
from typing import Any

from .languages import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    Language,
    get_direction,
    get_language,
    is_rtl,
    get_available_languages as get_langs,
)


class I18n:
    """Simple internationalization support.

    Loads translations from JSON files in the locales directory.
    Falls back to default language (en) if translation not found.
    """

    def __init__(
        self,
        locales_dir: Path | None = None,
        default_lang: str = "en",
    ):
        """Initialize i18n.

        Args:
            locales_dir: Path to locales directory with JSON files.
            default_lang: Default/fallback language code.
        """
        self.locales_dir = locales_dir or (
            Path(__file__).parent.parent / "locales"
        )
        self.default_lang = default_lang
        self._translations: dict[str, dict[str, str]] = {}
        self._current_lang = default_lang

    def load_language(self, lang: str) -> bool:
        """Load translations for a language.

        Args:
            lang: Language code (e.g., 'en', 'fa', 'de').

        Returns:
            True if loaded successfully.
        """
        if lang in self._translations:
            return True

        lang_file = self.locales_dir / f"{lang}.json"
        if not lang_file.exists():
            return False

        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                self._translations[lang] = json.load(f)
            return True
        except (json.JSONDecodeError, OSError):
            return False

    def set_language(self, lang: str) -> bool:
        """Set current language.

        Args:
            lang: Language code.

        Returns:
            True if language is available.
        """
        if self.load_language(lang):
            self._current_lang = lang
            return True
        return False

    def t(self, key: str, **kwargs: Any) -> str:
        """Translate a key.

        Args:
            key: Translation key (e.g., 'login.title').
            **kwargs: Variables for string formatting.

        Returns:
            Translated string or key if not found.
        """
        # Try current language
        text = self._get_translation(self._current_lang, key)

        # Fallback to default language
        if text is None and self._current_lang != self.default_lang:
            text = self._get_translation(self.default_lang, key)

        # Use key as fallback
        if text is None:
            return key

        # Format with variables
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text

        return text

    def get(self, key: str, lang: str | None = None, **kwargs: Any) -> str:
        """Get translation for a key in a specific language.

        Args:
            key: Translation key (e.g., 'search.placeholder').
            lang: Language code. If None, uses current language.
            **kwargs: Variables for string formatting.

        Returns:
            Translated string or key if not found.
        """
        target_lang = lang or self._current_lang

        # Try target language
        text = self._get_translation(target_lang, key)

        # Fallback to default language
        if text is None and target_lang != self.default_lang:
            text = self._get_translation(self.default_lang, key)

        # Use key as fallback
        if text is None:
            return key

        # Format with variables
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text

        return text

    def _get_translation(self, lang: str, key: str) -> str | None:
        """Get translation for a key in a specific language.

        Args:
            lang: Language code.
            key: Translation key.

        Returns:
            Translation or None.
        """
        # Load language if not loaded
        if lang not in self._translations:
            if not self.load_language(lang):
                return None

        translations = self._translations.get(lang, {})

        # Support dot notation (e.g., 'admin.pages.title')
        parts = key.split(".")
        value: Any = translations
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        return value if isinstance(value, str) else None

    @property
    def current_language(self) -> str:
        """Get current language code."""
        return self._current_lang

    @property
    def current_direction(self) -> str:
        """Get text direction for current language.

        Returns:
            'rtl' or 'ltr'.
        """
        return get_direction(self._current_lang)

    @property
    def is_rtl(self) -> bool:
        """Check if current language is RTL.

        Returns:
            True if current language is RTL.
        """
        return is_rtl(self._current_lang)

    def get_language_info(self, lang: str | None = None) -> Language | None:
        """Get language metadata.

        Args:
            lang: Language code, or None for current language.

        Returns:
            Language object or None if not found.
        """
        code = lang or self._current_lang
        return get_language(code)

    def get_available_languages(self) -> list[str]:
        """Get list of available language codes.

        Returns:
            List of language codes with translation files.
        """
        if not self.locales_dir.exists():
            return [self.default_lang]

        languages = []
        for f in self.locales_dir.iterdir():
            if f.suffix == ".json" and f.stem:
                languages.append(f.stem)

        return languages if languages else [self.default_lang]

    def get_languages_for_ui(self) -> list[dict]:
        """Get languages with full metadata for UI display.

        Returns:
            List of language dicts with code, name, native_name, direction.
        """
        available = self.get_available_languages()
        return [
            lang for lang in get_langs()
            if lang["code"] in available
        ]


# Global instance
i18n = I18n()


def t(key: str, **kwargs: Any) -> str:
    """Translate a key using global i18n instance.

    Args:
        key: Translation key.
        **kwargs: Variables for formatting.

    Returns:
        Translated string.
    """
    return i18n.t(key, **kwargs)
