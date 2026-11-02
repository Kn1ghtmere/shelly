from .. import platform as plat
from ..core.intent import Intent
from ..core.registry import command
from ..core.result import Result
from ._common import reject_options

ACTIONS = {
    "play": "play", "resume": "play", "start": "play",
    "pause": "pause", "stop": "pause",
    "prev": "previous", "previous": "previous", "back": "previous",
    "next": "next", "skip": "next",
}
USAGE = "Try: music play, music pause, music next, music previous, music vol 50"


def _percent(text: str | None) -> int | None:
    if text is None:
        return None
    text = text.strip().rstrip("%")
    if not text.isdigit() or not 0 <= int(text) <= 100:
        return None
    return int(text)


@command("music")
def music(intent: Intent) -> Result:
    """music play | pause | next | previous | vol <0-100>"""
    bad = reject_options(intent, {"volume"})
    if bad:
        return bad

    word = intent.args[0].lower() if intent.args else ("vol" if "volume" in intent.options else None)
    if word is None:
        return Result.fail(USAGE)

    if word in ("vol", "volume"):
        raw = intent.args[1] if len(intent.args) > 1 else intent.options.get("volume")
        return _set_volume(raw, music_only=True, example="music vol 50")

    action = ACTIONS.get(word)
    if action is None or len(intent.args) > 1:
        return Result.fail(f"I don't know 'music {intent.text}'. {USAGE}")

    system = plat.current()
    try:
        system.media(action)
    except plat.PlatformError as error:
        return Result.fail(str(error))

    message = f"Music: {action}."
    if system.key == "windows" and action in ("play", "pause"):
        message += " (Windows has one play/pause button, so if it was already that way, it flips.)"
    return Result.success(message)


@command("volume")
def volume(intent: Intent) -> Result:
    """volume <0-100>   -- the whole computer's volume"""
    bad = reject_options(intent, set())
    if bad:
        return bad
    return _set_volume(intent.args[0] if intent.args else None, music_only=False, example="volume 50")


def _set_volume(raw: str | None, *, music_only: bool, example: str) -> Result:
    level = _percent(raw)
    if level is None:
        return Result.fail(f"Volume is a number from 0 to 100. Try: {example}")
    try:
        what = plat.current().set_volume(level, music_only)
    except plat.PlatformError as error:
        return Result.fail(str(error))
    return Result.success(f"Set the {what} to {level}.")
