"""Remembers where you've been, so 'back' works."""

from pathlib import Path

_history: list[Path] = []


def remember(place: Path) -> None:
    _history.append(place)


def previous() -> Path | None:
    return _history.pop() if _history else None


def clear() -> None:
    _history.clear()
