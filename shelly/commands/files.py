import os
import shutil
from pathlib import Path

from ..core import paths, session
from ..core.intent import Intent
from ..core.registry import command
from ..core.result import Result
from ._common import not_found, quote_hint, reject_options

MAX_LISTED = 200


# --- moving around ------------------------------------------------------


@command("go")
def go(intent: Intent) -> Result:
    """go <folder>   (also: up, home, downloads, ..)"""
    bad = reject_options(intent, set())
    if bad:
        return bad
    if len(intent.args) > 1:
        return quote_hint(intent, intent.args)

    target = intent.args[0] if intent.args else "home"
    place = paths.resolve_existing(target)
    if place is None:
        return not_found(target, folders_only=True)
    if not place.is_dir():
        return Result.fail(f"'{target}' is a file, not a folder.")

    before = Path.cwd()
    try:
        os.chdir(place)
    except OSError as error:
        return Result.fail(f"I couldn't go there: {error}")
    if Path.cwd() != before:
        session.remember(before)
    return Result.success(f"Now in {Path.cwd()}")


@command("back")
def back(intent: Intent) -> Result:
    previous = session.previous()
    if previous is None:
        return Result.fail("There's nowhere to go back to yet.")
    try:
        os.chdir(previous)
    except OSError:
        return Result.fail(f"{previous} isn't there anymore.")
    return Result.success(f"Back in {Path.cwd()}")


@command("where")
def where(intent: Intent) -> Result:
    return Result.success(str(Path.cwd()))


# --- looking ------------------------------------------------------------


@command("list")
def list_folder(intent: Intent) -> Result:
    """list   |   list <folder>   |   list in <folder>"""
    bad = reject_options(intent, {"in"})
    if bad:
        return bad
    if len(intent.args) > 1:
        return quote_hint(intent, intent.args)
    if intent.args and "in" in intent.options:
        return Result.fail("Use either 'list downloads' or 'list in downloads', not both.")

    text = intent.args[0] if intent.args else intent.options.get("in")
    if text is None:
        place = Path.cwd()
    else:
        place = paths.resolve_existing(text)
        if place is None:
            return not_found(text, folders_only=True)
        if not place.is_dir():
            return Result.fail(f"'{text}' is a file, not a folder.")

    try:
        entries = sorted(place.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError as error:
        return Result.fail(f"I couldn't look in there: {error}")

    lines = [str(place.resolve())]
    for entry in entries[:MAX_LISTED]:
        if entry.is_dir():
            lines.append(f"  {entry.name}/")
        else:
            lines.append(f"  {entry.name}  ({_size(entry)})")
    if not entries:
        lines.append("  (empty)")
    if len(entries) > MAX_LISTED:
        lines.append(f"  ...and {len(entries) - MAX_LISTED} more")
    return Result.success("\n".join(lines), data=[e.name for e in entries])


def _size(path: Path) -> str:
    try:
        return paths.human_size(path.stat().st_size)
    except OSError:
        return "?"


# --- making and changing ------------------------------------------------


@command("mkdir")
def make_folder(intent: Intent) -> Result:
    """mkdir <name>   |   mkdir <name> in <folder>"""
    bad = reject_options(intent, {"in"})
    if bad:
        return bad
    if not intent.args:
        return Result.fail("Make a folder called what? For example: make a folder called projects")
    if len(intent.args) > 1:
        return quote_hint(intent, intent.args)

    base = Path.cwd()
    if "in" in intent.options:
        found = paths.resolve_existing(intent.options["in"])
        if found is None:
            return not_found(intent.options["in"], folders_only=True)
        if not found.is_dir():
            return Result.fail(f"'{intent.options['in']}' is a file, not a folder.")
        base = found

    new = base / intent.args[0]
    if new.exists():
        return Result.fail(f"{new} already exists.")
    try:
        new.mkdir(parents=True)
    except OSError as error:
        return Result.fail(f"I couldn't make that folder: {error}")
    return Result.success(f"Made a folder: {new}")


def _plan(intent: Intent, verb: str) -> tuple[Path, Path] | Result:
    """Shared by copy and move: work out (source, target) or explain the problem."""
    bad = reject_options(intent, {"to"})
    if bad:
        return bad
    if not intent.args or "to" not in intent.options:
        return Result.fail(f"Try: {verb} notes.txt to backup")
    if len(intent.args) > 1:
        return quote_hint(intent, intent.args)

    source_text = intent.args[0]
    source = paths.resolve_existing(source_text)
    if source is None:
        return not_found(source_text)

    dest_text = intent.options["to"]
    dest = paths.resolve_existing(dest_text)
    if dest is not None:
        target = dest / source.name if dest.is_dir() else dest
    else:
        target = Path(dest_text).expanduser()

    if target.exists():
        return Result.fail(f"{target} already exists. I won't overwrite it.")
    if not target.parent.is_dir():
        return Result.fail(f"I can't find the folder {target.parent}.")
    if source.is_dir() and _inside(target, source):
        return Result.fail("I can't put a folder inside itself.")
    return source, target


def _new_name_note(intent: Intent) -> str:
    """If the destination wasn't an existing folder, it became the new name. Say so."""
    dest_text = intent.options["to"]
    if paths.resolve_existing(dest_text) is not None:
        return ""
    return (
        f" ('{dest_text}' wasn't an existing folder, so it's the new name. "
        f"To put it inside a folder, make the folder first.)"
    )


def _inside(target: Path, folder: Path) -> bool:
    target, folder = target.resolve(), folder.resolve()
    return target == folder or folder in target.parents


@command("copy")
def copy(intent: Intent) -> Result:
    """copy <thing> to <place>"""
    plan = _plan(intent, "copy")
    if isinstance(plan, Result):
        return plan
    source, target = plan
    note = _new_name_note(intent)
    try:
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    except (OSError, shutil.Error) as error:
        return Result.fail(f"I couldn't copy that: {error}")
    return Result.success(f"Copied {source.name} to {target}{note}")


@command("move")
def move(intent: Intent) -> Result:
    """move <thing> to <place>"""
    plan = _plan(intent, "move")
    if isinstance(plan, Result):
        return plan
    source, target = plan
    if paths.is_protected(source):
        return Result.fail("That's an important folder, so I won't move it.")
    note = _new_name_note(intent)
    try:
        shutil.move(str(source), str(target))
    except (OSError, shutil.Error) as error:
        return Result.fail(f"I couldn't move that: {error}")
    return Result.success(f"Moved {source.name} to {target}{note}")


@command("rename")
def rename(intent: Intent) -> Result:
    """rename <thing> to <new name>"""
    bad = reject_options(intent, {"to"})
    if bad:
        return bad
    if not intent.args or "to" not in intent.options:
        return Result.fail("Try: rename old.txt to new.txt")
    if len(intent.args) > 1:
        return quote_hint(intent, intent.args)

    source = paths.resolve_existing(intent.args[0])
    if source is None:
        return not_found(intent.args[0])
    if paths.is_protected(source):
        return Result.fail("That's an important folder, so I won't rename it.")

    new_name = intent.options["to"]
    if "/" in new_name or "\\" in new_name:
        return Result.fail("rename only changes the name. To put it somewhere else, use: move")

    target = source.with_name(new_name)
    if target.exists() and source.name.lower() != new_name.lower():
        return Result.fail(f"{target.name} already exists here. I won't overwrite it.")
    try:
        source.rename(target)
    except OSError as error:
        return Result.fail(f"I couldn't rename that: {error}")
    return Result.success(f"Renamed {source.name} to {new_name}")
