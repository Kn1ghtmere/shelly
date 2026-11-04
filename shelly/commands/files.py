import os
from pathlib import Path

from .. import platform as plat
from ..core import paths, session
from ..core.intent import Intent
from ..core.registry import command
from ..core.result import Result
from ._common import locate_or_fail, not_found, quote_hint, reject_options

PAGE = 50
PAGE_ALL = 1000


# --- moving around ------------------------------------------------------


@command("go")
def go(intent: Intent) -> Result:
    """go <folder>   |   go <folder> in <folder> in D:   (also: up, home, downloads, ..)"""
    bad = reject_options(intent, {"in"})
    if bad:
        return bad
    if len(intent.args) > 1:
        return quote_hint(intent, intent.args)

    chain = intent.containers.get("", [])
    name = intent.args[0] if intent.args else None
    if name is None and not chain:
        name = "home"
    place = locate_or_fail(name, chain, folders_only=True)
    if isinstance(place, Result):
        return place
    if not place.is_dir():
        return Result.fail(f"'{name}' is a file, not a folder.")

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


def _list(intent: Intent, page_size: int) -> Result:
    bad = reject_options(intent, {"in"})
    if bad:
        return bad
    if len(intent.args) > 1:
        return quote_hint(intent, intent.args)

    name = intent.args[0] if intent.args else None
    place = locate_or_fail(name, intent.containers.get("", []), folders_only=True)
    if isinstance(place, Result):
        return place
    if not place.is_dir():
        return Result.fail(f"'{name}' is a file, not a folder.")

    try:
        entries = sorted(place.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError as error:
        return Result.fail(f"I couldn't look in there: {error}")

    lines = []
    for entry in entries:
        if entry.is_dir():
            lines.append(f"  {entry.name}/")
        else:
            lines.append(f"  {entry.name}  ({_size(entry)})")
    if not entries:
        lines.append("  (empty)")

    session.set_pager(lines)
    return Result.success(
        "\n".join([str(place.resolve()), *_next_page(page_size)]),
        data=[e.name for e in entries],
    )


def _next_page(size: int) -> list[str]:
    page, left = session.take_page(size)
    if left:
        page.append(f"  ...and {left} more. Say 'more' to see the next {PAGE}.")
    return page


@command("list")
def list_folder(intent: Intent) -> Result:
    """list   |   list <folder>   |   list in <folder>"""
    return _list(intent, PAGE)


@command("listall")
def list_everything(intent: Intent) -> Result:
    """list all   -- shows everything, not just the first page"""
    return _list(intent, PAGE_ALL)


@command("more")
def more(intent: Intent) -> Result:
    """The next page of the last listing."""
    page = _next_page(PAGE)
    if not page:
        return Result.fail("There's nothing more to show.")
    return Result.success("\n".join(page))


def _size(path: Path) -> str:
    try:
        return paths.human_size(path.stat().st_size)
    except OSError:
        return "?"


# --- making and changing ------------------------------------------------


def _base_folder(intent: Intent) -> Path | Result:
    """Where to make things: the end of the 'in' chain, or the current folder."""
    return locate_or_fail(None, intent.containers.get("", []), folders_only=True)


@command("mkdir")
def make_folder(intent: Intent) -> Result:
    """mkdir <name>   |   mkdir <name> in <folder> in D:"""
    bad = reject_options(intent, {"in"})
    if bad:
        return bad
    if not intent.args:
        return Result.fail("Make a folder called what? For example: make a folder called projects")
    if len(intent.args) > 1:
        return quote_hint(intent, intent.args)

    base = _base_folder(intent)
    if isinstance(base, Result):
        return base

    new = base / intent.args[0]
    if new.exists():
        return Result.fail(f"{new} already exists.")
    try:
        new.mkdir(parents=True)
    except OSError as error:
        return Result.fail(f"I couldn't make that folder: {error}")
    return Result.success(f"Made a folder: {new}")


@command("mkfile")
def make_file(intent: Intent) -> Result:
    """mkfile <name>   |   mkfile <name> with "some text"   |   mkfile <name> in <folder>"""
    bad = reject_options(intent, {"in", "with"})
    if bad:
        return bad
    if not intent.args:
        return Result.fail("Make a file called what? For example: make a file called notes.txt")
    if len(intent.args) > 1:
        return quote_hint(intent, intent.args)

    base = _base_folder(intent)
    if isinstance(base, Result):
        return base

    new = base / intent.args[0]
    if new.exists():
        return Result.fail(f"{new} already exists. I won't overwrite it.")
    if not new.parent.is_dir():
        return Result.fail(f"I can't find the folder {new.parent}.")
    try:
        new.write_text(intent.options.get("with", ""), encoding="utf-8")
    except OSError as error:
        return Result.fail(f"I couldn't make that file: {error}")
    return Result.success(f"Made a file: {new}")


@command("show")
def show(intent: Intent) -> Result:
    """show   |   show <file or folder>   -- opens your file explorer"""
    bad = reject_options(intent, {"in"})
    if bad:
        return bad
    if len(intent.args) > 1:
        return quote_hint(intent, intent.args)

    name = intent.args[0] if intent.args else None
    found = locate_or_fail(name, intent.containers.get("", []))
    if isinstance(found, Result):
        return found
    target = found.resolve()

    try:
        if target.is_dir():
            plat.current().open_path(target)
        else:
            plat.current().reveal(target)
    except plat.PlatformError as error:
        return Result.fail(str(error))
    return Result.success(f"Showing {target} in your file explorer.")


@command("rename")
def rename(intent: Intent) -> Result:
    """rename <thing> to <new name>"""
    bad = reject_options(intent, {"to", "in"})
    if bad:
        return bad
    if not intent.args or "to" not in intent.options:
        return Result.fail("Try: rename old.txt to new.txt")
    if len(intent.args) > 1:
        return quote_hint(intent, intent.args)
    if intent.containers.get("to"):
        return Result.fail("rename only changes the name. To put it somewhere else, use: move")

    source = locate_or_fail(intent.args[0], intent.containers.get("", []))
    if isinstance(source, Result):
        return source
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
