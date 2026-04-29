import locale as stdlib_locale
import logging
import os
import sys
import threading
from datetime import date, datetime
from decimal import Decimal
from importlib import resources
from pathlib import Path

import langcodes
from fluent.runtime import FluentBundle, FluentResource

# import scikms.i18n
from scikms.i18n.windows import user_default_locale

logger = logging.getLogger(__name__)


class i18nManager:
    """Thread-safe i18n manager with lazy bundle loading."""

    DEFAULT_LOCALE = "en-US"
    FALLBACK_LOCALES = ["en-US", "vi-VN"]

    def __init__(self) -> None:
        """Initialize the i18n manager with lazy loading support."""
        self._bundles: dict[str, FluentBundle] = {}
        self._lock = threading.RLock()
        package_name = __package__ or "scikms.i18n"

        # Core assets directory
        with resources.as_file(resources.files(package_name) / "assets") as assets_dir:
            self._core_assets_dir = Path(assets_dir)

        self._supported_locales = [
            entry.name for entry in self._core_assets_dir.iterdir() if entry.is_dir()
        ]

        logger.debug(
            "[i18n] Initialized with supported locales: %s",
            self._supported_locales,
        )

    def _normalize_locale(self, locale: str) -> str:
        """Convert any locale format to BCP-47 (hyphen-separated).

        Args:
            locale: Locale string (e.g., "en_US" or "en-US")

        Returns:
            Normalized locale string (e.g., "en-US")
        """
        return locale.replace("_", "-")

    def _get_default_locale(self) -> str:
        """Get system locale in BCP-47 format.

        Priority:
        1. SCIKMS_LOCALE environment variable
        2. Windows API (on Windows)
        3. POSIX locale detection
        4. Default to "en-US"

        Returns:
            BCP-47 locale string
        """
        override = os.environ.get("SCIKMS_LOCALE")
        if override:
            normalized = self._normalize_locale(override)
            logger.debug("[i18n] Using override locale from env: %s", normalized)
            return normalized

        if sys.platform == "win32":
            try:
                detected = user_default_locale()
                logger.debug("[i18n] Detected Windows locale: %s", detected)
                return detected
            except Exception as exc:
                logger.warning("[i18n] Failed to get Windows locale: %s", exc)

        # POSIX: convert en_US → en-US
        lang, _ = stdlib_locale.getlocale(stdlib_locale.LC_CTYPE)
        if lang and lang not in ("C", "POSIX", None, ""):
            normalized = self._normalize_locale(lang)
            logger.debug("[i18n] Detected POSIX locale: %s", normalized)
            return normalized

        logger.debug("[i18n] Falling back to default locale: %s", self.DEFAULT_LOCALE)
        return self.DEFAULT_LOCALE

    def _validate_locale(self, locale: str | None) -> str:
        """Validate and find best matching supported locale.

        Args:
            locale: Requested locale or None to use default

        Returns:
            Best matching supported locale from self._supported_locales
        """
        if locale is None:
            locale = self._get_default_locale()
        else:
            locale = self._normalize_locale(locale)

        # Use langcodes for smart matching
        matched = langcodes.closest_supported_match(
            desired_language=locale,
            supported_languages=self._supported_locales,
        )

        if matched is not None:
            if matched != locale:
                logger.debug(
                    "[i18n] Locale '%s' matched to supported: '%s'",
                    locale,
                    matched,
                )
            return matched

        logger.warning(
            "[i18n] Locale '%s' not supported, falling back to '%s'",
            locale,
            self.DEFAULT_LOCALE,
        )
        return self.DEFAULT_LOCALE

    def _create_bundle(self, locale: str) -> FluentBundle:
        """Create a FluentBundle by loading FTL files for a locale.

        Args:
            locale: Locale to load resources for

        Returns:
            Configured FluentBundle with loaded resources
        """
        bundle = FluentBundle([locale], use_isolating=False)
        locale_dir = self._core_assets_dir / locale

        if not locale_dir.exists():
            logger.warning("[i18n] Locale directory not found: %s", locale_dir)
            return bundle

        loaded_files = 0

        # Load all .ftl files (sorted for consistent order)
        for ftl_file in sorted(locale_dir.glob("*.ftl")):
            try:
                content = ftl_file.read_text(encoding="utf-8")
                bundle.add_resource(FluentResource(content))
                loaded_files += 1
                logger.debug("[i18n] Loaded resource: %s", ftl_file)
            except Exception as exc:
                logger.error("[i18n] Failed to load %s: %s", ftl_file, exc)

        if loaded_files == 0:
            logger.warning(
                "[i18n] No resources loaded for locale '%s' in %s",
                locale,
                locale_dir,
            )
        else:
            logger.debug(
                "[i18n] Loaded %d resources for locale '%s'",
                loaded_files,
                locale,
            )

        return bundle

    def _get_bundle(self, locale: str) -> FluentBundle:
        """Get or create bundle for a locale (lazy loading, thread-safe).

        Args:
            locale: Locale to get bundle for

        Returns:
            FluentBundle for the requested locale
        """
        with self._lock:
            if locale not in self._bundles:
                logger.debug("[i18n] Creating new bundle for locale '%s'", locale)
                self._bundles[locale] = self._create_bundle(locale)
            else:
                logger.debug("[i18n] Using cached bundle for locale '%s'", locale)

            return self._bundles[locale]

    def _build_fallback_chain(self, locale: str | None) -> list[str]:
        """Build locale search order for translation lookup.

        Args:
            locale: Requested locale or None to use default

        Returns:
            List of locales to try in order
        """
        primary_locale = self._validate_locale(locale)
        chain = [primary_locale]

        for fallback_locale in self.FALLBACK_LOCALES:
            if fallback_locale not in chain:
                chain.append(fallback_locale)

        return chain

    def translate(
        self,
        key: str,
        locale: str | None = None,
        **kwargs: str | int | float | Decimal | date | datetime | object,
    ) -> str:
        """Translate a message key using the appropriate locale bundle.

        Attempts to translate using the requested locale, then falls back
        through the FALLBACK_LOCALES chain if not found.

        Args:
            key: Message ID to translate
            locale: Optional specific locale to use
            **kwargs: Variables to interpolate into the message

        Returns:
            Translated string, or the key itself if not found

        Example:
            manager.translate("welcome-message", name="Alice")
            # Returns: "Welcome, Alice!" (or localized equivalent)
        """
        # Convert kwargs values to supported types
        for name, value in kwargs.items():
            if not isinstance(value, (str, float, int, date, datetime, Decimal)):
                kwargs[name] = str(value)

        tried_locales: list[str] = []

        # Try each locale in chain with lazy loading
        for current_locale in self._build_fallback_chain(locale):
            bundle = self._get_bundle(current_locale)
            tried_locales.append(current_locale)

            message = bundle.get_message(key)
            if message is None or message.value is None:
                continue

            value, errors = bundle.format_pattern(message.value, kwargs)

            # Log format errors
            for error in errors:
                logger.warning(
                    "[i18n] Format error for key '%s' in locale '%s': %s",
                    key,
                    current_locale,
                    error,
                )

            return str(value)

        # Key not found in ANY locale
        logger.warning(
            "[i18n] Missing translation key '%s'. Tried locales: %s. Returning key.",
            key,
            tried_locales,
        )
        return key
