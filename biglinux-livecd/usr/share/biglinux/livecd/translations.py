"""
Translation utility module to ensure consistent translations throughout the application
"""
import gettext
import os
from logging_config import get_logger

logger = get_logger()

APP_NAME = "biglinux-livecd"
# Standard location for locale files on Linux systems
LOCALE_DIR = "/usr/share/locale"

# This module-level variable will hold the current translation object.
# It's initialized with a "null" translation, which just returns the original string.
_translation_instance = gettext.NullTranslations()


def set_language(lang_code=None):
    """
    Sets the active translation for the entire application.

    Args:
        lang_code (str, optional): The language code (e.g., 'pt', 'es').
                                   If None, gettext uses environment variables.
    """
    global _translation_instance
    try:
        # gettext.translation handles finding the best .mo file and fallbacks
        # (e.g., pt_BR -> pt -> default).
        _translation_instance = gettext.translation(
            APP_NAME,
            localedir=LOCALE_DIR,
            languages=[lang_code] if lang_code else None,
            fallback=True,  # IMPORTANT: ensures it falls back to NullTranslations
        )
    except FileNotFoundError:
        # This happens if the .mo file for the given language doesn't exist at all.
        logger.warning(
            f"Translation for '{lang_code}' not found in '{LOCALE_DIR}'. Using default (English)."
        )
        _translation_instance = gettext.NullTranslations()


def _(message):
    """
    The public translation function that all modules should use.
    It calls the gettext() method of the currently active translation instance.
    """
    return _translation_instance.gettext(message)


# Initialize with the system's default language on startup.
# This ensures that if the app starts before a language is selected, it uses
# the system's locale settings (e.g., from the LANG environment variable).
set_language()
