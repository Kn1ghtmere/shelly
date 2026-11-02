from pathlib import Path

from .. import platform as plat
from ..core import paths, transfer
from ..core.intent import Intent
from ..core.registry import command
from ..core.result import Ask, Result
from ._common import locate_or_fail, reject_options, sources_of


@command("delete")
def delete(intent: Intent) -> Result:
    """delete <thing> [and <thing>]   -- moves it to the trash, after asking"""
    bad = reject_options(intent, {"in"})
    if bad:
        return bad
    names = sources_of(intent)
    if isinstance(names, Result):
        return names
    if not names:
        return Result.fail("Delete what? For example: delete old.txt")

    items: list[Path] = []
    for name in names:
        found = locate_or_fail(name, intent.containers.get("", []))
        if isinstance(found, Result):
            return found
        item = transfer.absolute(found)
        if paths.is_protected(item):
            return Result.fail(f"'{item.name}' is an important folder, so I won't delete it.")
        items.append(item)

    if len(items) == 1:
        what = f"the folder '{items[0].name}' and everything in it" if items[0].is_dir() else f"'{items[0].name}'"
    else:
        what = f"these {len(items)} things ({', '.join(i.name for i in items)})"
    return Result.asking(Ask.yes_no(f"Move {what} to the trash?", lambda: _trash(items)))


def _trash(items: list[Path]) -> Result:
    done = []
    for item in items:
        try:
            plat.current().trash(item)
        except plat.PlatformError as error:
            lines = [f"Moved {i.name} to the trash." for i in done]
            return Result.fail("\n".join([*lines, str(error)]))
        done.append(item)
    names = items[0].name if len(items) == 1 else f"{len(items)} things"
    return Result.success(f"Moved {names} to the trash. You can restore it from there.")
