"""Finding files and folders the way a person would name them."""

import difflib
from pathlib import Path

# Friendly names that point at the usual folders in your home folder.
KNOWN_FOLDERS = {
    "desktop": "Desktop",
    "downloads": "Downloads",
    "documents": "Documents",
    "pictures": "Pictures",
    "music": "Music",
    "videos": "Videos",
}


def home() -> Path:
    return Path.home()


def _known_candidates(name: str) -> list[Path]:
    # OneDrive often moves Desktop/Documents/Pictures, so check there too.
    return [home() / name, home() / "OneDrive" / name]


def resolve_existing(text: str) -> Path | None:
    """Turn what the user typed into a real path, or None.

    Tries, in order: the path as typed, the same ignoring capital letters,
    then the friendly names (up, home, downloads, ...).
    """
    word = text.strip()
    if not word:
        return None

    path = Path(word).expanduser()
    try:
        if path.exists():
            return path
    except (OSError, ValueError):
        return None

    found = _ignoring_case(path)
    if found is not None:
        return found

    lowered = word.lower()
    if lowered == "up":
        return Path.cwd().parent
    if lowered == "home":
        return home()
    if lowered in KNOWN_FOLDERS:
        for candidate in _known_candidates(KNOWN_FOLDERS[lowered]):
            if candidate.is_dir():
                return candidate
    return None


def _ignoring_case(path: Path) -> Path | None:
    parent = path.parent
    try:
        if not parent.is_dir():
            return None
        matches = [c for c in parent.iterdir() if c.name.lower() == path.name.lower()]
    except OSError:
        return None
    return matches[0] if len(matches) == 1 else None


def suggest(text: str, *, folders_only: bool = False) -> str | None:
    """A close match for a mistyped name, for 'did you mean ...?'"""
    path = Path(text).expanduser()
    parent = path.parent
    try:
        names = [c.name for c in parent.iterdir() if not folders_only or c.is_dir()]
    except OSError:
        names = []
    plain = parent == Path(".")
    if plain:
        names += ["home", "up", *KNOWN_FOLDERS]
    match = difflib.get_close_matches(path.name, names, n=1, cutoff=0.6)
    if not match:
        return None
    return match[0] if plain else str(parent / match[0])


def is_protected(path: Path) -> bool:
    """Folders that shouldn't be moved or renamed by accident."""
    try:
        target = path.resolve()
        protected = {Path.cwd().resolve(), home().resolve(), Path(target.anchor)}
        for name in KNOWN_FOLDERS.values():
            for candidate in _known_candidates(name):
                protected.add(candidate.resolve())
    except OSError:
        return True
    return target in protected


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{int(value)} B" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"
