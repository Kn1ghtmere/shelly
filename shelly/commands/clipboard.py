from ..core import paths, session, transfer
from ..core.intent import Intent
from ..core.registry import command
from ..core.result import Result
from ._common import not_found, quote_hint, reject_options


def _one_source(intent: Intent, what: str):
    """The single thing the user named, as an absolute path, or a failed Result."""
    if not intent.args:
        return Result.fail(f"{what.capitalize()} what? For example: {what} notes.txt")
    if len(intent.args) > 1:
        return quote_hint(intent, intent.args)
    found = paths.resolve_existing(intent.args[0])
    if found is None:
        return not_found(intent.args[0])
    return transfer.absolute(found)


@command("copy")
def copy(intent: Intent) -> Result:
    """copy <thing>   (put it on the clipboard)   |   copy <thing> to <place>"""
    bad = reject_options(intent, {"to"})
    if bad:
        return bad
    source = _one_source(intent, "copy")
    if isinstance(source, Result):
        return source

    if "to" in intent.options:
        return transfer.send([source], intent.options["to"], "copy")

    session.set_clipboard([source], "copy")
    return Result.success(f"Copied {source.name}. Now say: paste   (or: paste to <folder>)")


@command("cut")
def cut(intent: Intent) -> Result:
    """cut <thing>   -- it moves when you paste"""
    bad = reject_options(intent, set())
    if bad:
        return bad
    source = _one_source(intent, "cut")
    if isinstance(source, Result):
        return source
    if paths.is_protected(source):
        return Result.fail("That's an important folder, so I won't cut it.")

    session.set_clipboard([source], "cut")
    return Result.success(f"Cut {source.name}. Now say: paste   (or: paste to <folder>)")


@command("move")
def move(intent: Intent) -> Result:
    """move <thing> to <place>"""
    bad = reject_options(intent, {"to"})
    if bad:
        return bad
    source = _one_source(intent, "move")
    if isinstance(source, Result):
        return source
    if "to" not in intent.options:
        return Result.fail("Move it where? For example: move notes.txt to documents")
    return transfer.send([source], intent.options["to"], "move")


@command("paste")
def paste(intent: Intent) -> Result:
    """paste   |   paste <folder>   |   paste to <folder>"""
    bad = reject_options(intent, {"to", "in"})
    if bad:
        return bad

    given = [*intent.args, *(intent.options[k] for k in ("to", "in") if k in intent.options)]
    if len(intent.args) > 1:
        return quote_hint(intent, intent.args)
    if len(given) > 1:
        return Result.fail("Paste it where? Give me just one place, like: paste to downloads")
    place = given[0] if given else None
    if place is not None and place.lower() == "here":
        place = None

    clip = session.get_clipboard()
    if clip is None:
        return Result.fail("There's nothing to paste yet. Use copy or cut first.")

    if clip.mode == "copy":
        return transfer.send(clip.items, place, "copy")
    return transfer.send(clip.items, place, "move", on_done=session.clipboard_done)
