"""Finding files and folders the way a person would name them."""

import difflib
import os
import re
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


def _drive_root(word: str) -> str:
    """On Windows a bare 'D:' means 'the last folder you used on D:'.
    People mean the drive itself, so turn it into 'D:\\'."""
    return word + os.sep if re.fullmatch(r"[A-Za-z]:", word) else word


def _known_candidates(name: str) -> list[Path]:
    # OneDrive often moves Desktop/Documents/Pictures, so check there too.
    return [home() / name, home() / "OneDrive" / name]


def resolve_existing(text: str) -> Path | None:
    """Turn what the user typed into a real path, or None.

    Tries, in order: the path as typed, the same ignoring capital letters,
    then the friendly names (up, home, downloads, ...).
    """
    word = _drive_root(text.strip())
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


# --- 'tools in assets in D:' ------------------------------------------------


def child_of(base: Path, text: str) -> Path | None:
    """`text` inside the folder `base`, ignoring capital letters if needed."""
    candidate = base / text
    try:
        if candidate.exists():
            return candidate
    except (OSError, ValueError):
        return None
    if "/" in text or "\\" in text:
        return None
    try:
        matches = [c for c in base.iterdir() if c.name.lower() == text.lower()]
    except OSError:
        return None
    return matches[0] if len(matches) == 1 else None


def missing_message(text: str, *, base: Path | None = None, folders_only: bool = False) -> str:
    if base is None:
        message = f"I can't find '{text}'."
        guess = suggest(text, folders_only=folders_only)
    else:
        message = f"I can't find '{text}' in '{base}'."
        try:
            names = [c.name for c in base.iterdir() if not folders_only or c.is_dir()]
        except OSError:
            names = []
        match = difflib.get_close_matches(text, names, n=1, cutoff=0.6)
        guess = match[0] if match else None
    return message + (f" Did you mean '{guess}'?" if guess else "")


def _step(base: Path | None, text: str, folders_only: bool) -> "Path | str":
    if base is None:
        found = resolve_existing(text)
        return found if found is not None else missing_message(text, folders_only=folders_only)
    found = child_of(base, text)
    return found if found is not None else missing_message(text, base=base, folders_only=folders_only)


def locate(name: str | None, containers=(), *, folders_only: bool = False) -> "Path | str":
    """Find `name` inside a chain of folders written inner-to-outer, like
    'tools in assets in D:'  ->  locate('tools', ['assets', 'D:']).

    Returns the Path, or a message (str) explaining what couldn't be found.
    With name None, returns the innermost folder of the chain (or the
    current folder if there's no chain).
    """
    base: Path | None = None
    for text in reversed(list(containers)):
        step = _step(base, text, True)
        if isinstance(step, str):
            return step
        if not step.is_dir():
            return f"'{text}' is a file, not a folder."
        base = step
    if name is None:
        return base if base is not None else Path.cwd()
    return _step(base, name, folders_only)
