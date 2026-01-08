"""Language configuration for ChelCheleh.

This module defines supported languages and their properties.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Language:
    """Language configuration."""

    code: str
    name: str
    native_name: str
    direction: Literal["ltr", "rtl"]
    flag: str = ""


# Supported languages configuration
SUPPORTED_LANGUAGES: dict[str, Language] = {
    "en": Language(
        code="en",
        name="English",
        native_name="English",
        direction="ltr",
        flag="🇬🇧"
    ),
    "fa": Language(
        code="fa",
        name="Persian",
        native_name="فارسی",
        direction="rtl",
        flag="🇮🇷"
    ),
}

# Default language code
DEFAULT_LANGUAGE = "en"

# RTL languages
RTL_LANGUAGES = {"fa", "ar", "he", "ur"}


def get_language(code: str) -> Language | None:
    """Get language configuration by code.

    Args:
        code: Language code (e.g., 'en', 'fa')

    Returns:
        Language configuration or None if not found.
    """
    return SUPPORTED_LANGUAGES.get(code)


def get_default_language() -> Language:
    """Get default language configuration.

    Returns:
        Default language configuration.
    """
    return SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE]


def is_rtl(code: str) -> bool:
    """Check if a language is RTL.

    Args:
        code: Language code.

    Returns:
        True if the language is RTL.
    """
    lang = SUPPORTED_LANGUAGES.get(code)
    if lang:
        return lang.direction == "rtl"
    return code in RTL_LANGUAGES


def get_direction(code: str) -> str:
    """Get text direction for a language.

    Args:
        code: Language code.

    Returns:
        'rtl' or 'ltr'.
    """
    return "rtl" if is_rtl(code) else "ltr"


def get_available_languages() -> list[dict]:
    """Get list of available languages for UI.

    Returns:
        List of language dictionaries with code, name, native_name, direction.
    """
    return [
        {
            "code": lang.code,
            "name": lang.name,
            "native_name": lang.native_name,
            "direction": lang.direction,
            "flag": lang.flag,
        }
        for lang in SUPPORTED_LANGUAGES.values()
    ]


def is_valid_language(code: str) -> bool:
    """Check if a language code is valid/supported.

    Args:
        code: Language code to check.

    Returns:
        True if language is supported.
    """
    return code in SUPPORTED_LANGUAGES
