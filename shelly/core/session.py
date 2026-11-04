"""Things Shelly remembers while it's running: where you've been, and the clipboard."""

from dataclasses import dataclass
from pathlib import Path

_history: list[Path] = []


def remember(place: Path) -> None:
    _history.append(place)


def previous() -> Path | None:
    return _history.pop() if _history else None


# --- Shelly's own clipboard (separate from Windows' clipboard) -----------


@dataclass
class Clipboard:
    items: list[Path]
    mode: str  # "copy" or "cut"


_clipboard: Clipboard | None = None


def set_clipboard(items: list[Path], mode: str) -> None:
    global _clipboard
    _clipboard = Clipboard(list(items), mode)


def get_clipboard() -> Clipboard | None:
    return _clipboard


def clipboard_done(item: Path) -> None:
    """A cut item has been moved, so it leaves the clipboard."""
    global _clipboard
    if _clipboard is None:
        return
    _clipboard.items = [i for i in _clipboard.items if i != item]
    if not _clipboard.items:
        _clipboard = None


# --- long listings: 'more' shows the next page -----------------------------

_pager: list[str] = []


def set_pager(lines: list[str]) -> None:
    global _pager
    _pager = list(lines)


def take_page(size: int) -> tuple[list[str], int]:
    """The next `size` lines, and how many are still left after them."""
    page = _pager[:size]
    del _pager[:size]
    return page, len(_pager)


def clear() -> None:
    global _clipboard
    _history.clear()
    _clipboard = None
    _pager.clear()
