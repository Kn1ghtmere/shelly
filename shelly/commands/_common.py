from pathlib import Path

from ..core import paths
from ..core.intent import Intent
from ..core.result import Result


def quote_hint(intent: Intent, words: list[str]) -> Result:
    """The 'put it in quotes' error, showing the user's own line fixed."""
    joined = " ".join(words)
    if joined in intent.raw:
        fixed = intent.raw.replace(joined, f'"{joined}"', 1)
    else:
        fixed = f'{intent.verb} "{joined}"'
    return Result.fail(
        f'That\'s {len(words)} words. If "{joined}" is one thing, put it in quotes: {fixed}'
    )


def not_found(text: str, *, folders_only: bool = False) -> Result:
    return Result.fail(paths.missing_message(text, folders_only=folders_only))


def reject_options(intent: Intent, allowed: set[str]) -> Result | None:
    for name in intent.options:
        if name not in allowed:
            return Result.fail(f"'{intent.verb}' doesn't use '{name}'.")
    return None


def locate_or_fail(name: str | None, chain: list[str], *, folders_only: bool = False) -> Path | Result:
    """paths.locate, but with a failed Result instead of a message string."""
    found = paths.locate(name, chain, folders_only=folders_only)
    return Result.fail(found) if isinstance(found, str) else found


def sources_of(intent: Intent) -> list[str] | Result:
    """The things the user named: one word, or several joined by 'and'.
    Without 'and', more than one word means they forgot quotes."""
    if not intent.args:
        return []
    items = intent.items()
    if len(items) > 1:
        return items
    if len(intent.args) > 1:
        return quote_hint(intent, intent.args)
    return [intent.args[0]]
