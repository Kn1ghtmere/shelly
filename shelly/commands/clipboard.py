from pathlib import Path

from ..core import paths, session, transfer
from ..core.intent import Intent
from ..core.registry import command
from ..core.result import Result
from ._common import locate_or_fail, reject_options, sources_of


def _sources(intent: Intent, verb: str) -> list[Path] | Result:
    """The things the user named, as absolute paths (or a failed Result)."""
    names = sources_of(intent)
    if isinstance(names, Result):
        return names
    if not names:
        return Result.fail(f"{verb.capitalize()} what? For example: {verb} notes.txt")
    found = []
    for name in names:
        path = locate_or_fail(name, intent.containers.get("", []))
        if isinstance(path, Result):
            return path
        found.append(transfer.absolute(path))
    return found


def _names(items: list[Path]) -> str:
    return items[0].name if len(items) == 1 else ", ".join(i.name for i in items)


@command("copy")
def copy(intent: Intent) -> Result:
    """copy <thing> [and <thing>]   (clipboard)   |   copy <thing> to <place>"""
    bad = reject_options(intent, {"to", "in"})
    if bad:
        return bad
    sources = _sources(intent, "copy")
    if isinstance(sources, Result):
        return sources

    if "to" in intent.options:
        return transfer.send(
            sources, intent.options["to"], "copy", dest_chain=intent.containers.get("to")
        )
    session.set_clipboard(sources, "copy")
    return Result.success(f"Copied {_names(sources)}. Now say: paste   (or: paste to <folder>)")


@command("cut")
def cut(intent: Intent) -> Result:
    """cut <thing> [and <thing>]   -- it moves when you paste"""
    bad = reject_options(intent, {"in"})
    if bad:
        return bad
    sources = _sources(intent, "cut")
    if isinstance(sources, Result):
        return sources
    for source in sources:
        if paths.is_protected(source):
            return Result.fail("That's an important folder, so I won't cut it.")

    session.set_clipboard(sources, "cut")
    return Result.success(f"Cut {_names(sources)}. Now say: paste   (or: paste to <folder>)")


@command("move")
def move(intent: Intent) -> Result:
    """move <thing> [and <thing>] to <place>"""
    bad = reject_options(intent, {"to", "in"})
    if bad:
        return bad
    sources = _sources(intent, "move")
    if isinstance(sources, Result):
        return sources
    if "to" not in intent.options:
        return Result.fail("Move it where? For example: move notes.txt to documents")
    return transfer.send(
        sources, intent.options["to"], "move", dest_chain=intent.containers.get("to")
    )


@command("paste")
def paste(intent: Intent) -> Result:
    """paste   |   paste <folder>   |   paste to <folder> in D:   |   paste in <folder>"""
    bad = reject_options(intent, {"to", "in"})
    if bad:
        return bad

    places: list[tuple[str | None, list[str]]] = []
    here = intent.containers.get("", [])
    if intent.args:
        if len(intent.args) > 1:
            return Result.fail('Paste where? If the folder has spaces, use quotes: paste "my folder"')
        places.append((intent.args[0], here))
    elif here:
        places.append((None, here))
    if "to" in intent.options:
        places.append((intent.options["to"], intent.containers.get("to", [])))
    if len(places) > 1:
        return Result.fail("Paste it where? Give me just one place, like: paste to downloads")

    place, chain = places[0] if places else (None, [])
    if place is not None and place.lower() == "here" and not chain:
        place = None

    clip = session.get_clipboard()
    if clip is None:
        return Result.fail("There's nothing to paste yet. Use copy or cut first.")

    if clip.mode == "copy":
        return transfer.send(clip.items, place, "copy", dest_chain=chain)
    return transfer.send(clip.items, place, "move", on_done=session.clipboard_done, dest_chain=chain)
