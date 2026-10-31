import sys

from .base import Platform, PlatformError

__all__ = ["Platform", "PlatformError", "current", "set_current"]

_current: Platform | None = None


def current() -> Platform:
    global _current
    if _current is None:
        _current = _detect()
    return _current


def set_current(platform: Platform | None) -> None:
    """Swap the platform (used by tests). None means 'detect again'."""
    global _current
    _current = platform


def _detect() -> Platform:
    if sys.platform.startswith("win"):
        from .windows import WindowsPlatform
        return WindowsPlatform()
    if sys.platform == "darwin":
        from .mac import MacPlatform
        return MacPlatform()
    from .linux import LinuxPlatform
    return LinuxPlatform()
