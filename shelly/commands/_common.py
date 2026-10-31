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
    message = f"I can't find '{text}'."
    guess = paths.suggest(text, folders_only=folders_only)
    if guess:
        message += f" Did you mean '{guess}'?"
    return Result.fail(message)


def reject_options(intent: Intent, allowed: set[str]) -> Result | None:
    for name in intent.options:
        if name not in allowed:
            return Result.fail(f"'{intent.verb}' doesn't use '{name}'.")
    return None
