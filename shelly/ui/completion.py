"""Tab completion and saved history. Uses `readline` when the system has it
(on Windows: pip install pyreadline3). Without it, everything else still works."""

import atexit
import os
from pathlib import Path

from ..core import appbook, paths, registry
from ..core.aliases import ALIASES

HISTORY_FILE = Path.home() / ".shelly" / "history"


def complete(buffer: str, text: str) -> list[str]:
    """Suggestions for the word being typed.

    `buffer` is the whole line typed so far; `text` is the word at the cursor."""
    before = buffer[: len(buffer) - len(text)].split()
    typed = text.lstrip("\"'")
    quote = text[: len(text) - len(typed)]

    if not before:
        names = set(registry.all_names()) | {p for p in ALIASES if " " not in p}
        return sorted(n for n in names if n.startswith(text.lower()))

    found: set[str] = set()
    if before[0].lower() in ("open", "close", "remove", "help") and len(before) == 1:
        try:
            found |= {a.name for a in appbook.get_book().all()}
        except appbook.AppConfigError:
            pass
    found |= _path_names(typed)
    if "/" not in typed and "\\" not in typed:
        found |= set(paths.KNOWN_FOLDERS) | {"home", "up"}

    matches = sorted(n for n in found if n.lower().startswith(typed.lower()))
    return [_quoted(m, quote) for m in matches]


def _path_names(typed: str) -> set[str]:
    folder, _, _ = typed.replace("\\", "/").rpartition("/")
    directory = Path(os.path.expanduser(folder)) if folder else Path.cwd()
    prefix = typed[: len(folder) + 1] if folder else ""
    try:
        return {prefix + entry.name + (os.sep if entry.is_dir() else "") for entry in directory.iterdir()}
    except OSError:
        return set()


def _quoted(name: str, quote: str) -> str:
    if quote or " " in name:
        return f'{quote or chr(34)}{name}{chr(34) if not quote else quote}'
    return name


def setup() -> None:
    """Turn on Tab completion and remembered history, if this system can."""
    try:
        import readline
    except ImportError:
        return

    readline.set_completer_delims(" \t\n")

    def completer(text: str, state: int) -> str | None:
        matches = complete(readline.get_line_buffer(), text)
        return matches[state] if state < len(matches) else None

    readline.set_completer(completer)
    if "libedit" in (readline.__doc__ or ""):
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if HISTORY_FILE.exists():
            readline.read_history_file(str(HISTORY_FILE))
        readline.set_history_length(1000)
        atexit.register(lambda: readline.write_history_file(str(HISTORY_FILE)))
    except OSError:
        pass
