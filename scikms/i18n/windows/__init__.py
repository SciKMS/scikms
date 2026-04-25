"""Windows platform locale detection adapter.

This module provides a thin shim over the Windows API for detecting
the user's default locale. It is only functional on Windows; on other
platforms, the public API explicitly raises NotImplementedError.
"""

import ctypes
import os
from typing import Any

# Windows-specific constant per MS-LSCD docs
LOCALE_NAME_MAX_LENGTH = 85

# Windows API binding - only initialized on Windows
_kernel32: Any | None = None

if os.name == "nt":
    from ctypes import wintypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.GetUserDefaultLocaleName.argtypes = [wintypes.LPWSTR, ctypes.c_int]
    _kernel32.GetUserDefaultLocaleName.restype = ctypes.c_int


def user_default_locale() -> str:
    """Get user default locale encoded in BCP-47 format.

    This function queries the Windows GetUserDefaultLocaleName API
    and returns the locale string (e.g., "en-US", "vi-VN").

    Returns:
        BCP-47 locale string from Windows.

    Raises:
        NotImplementedError: If called on a non-Windows platform.
        OSError: If the Windows API call fails.

    Example:
        >>> user_default_locale()
        'en-US'
    """
    if _kernel32 is None:
        raise NotImplementedError("user_default_locale() is only available on Windows.")

    buffer = ctypes.create_unicode_buffer(LOCALE_NAME_MAX_LENGTH)
    result = _kernel32.GetUserDefaultLocaleName(buffer, LOCALE_NAME_MAX_LENGTH)

    if result == 0:
        error_code = getattr(ctypes, "get_last_error")()
        raise getattr(ctypes, "WinError")(error_code)

    return buffer.value
