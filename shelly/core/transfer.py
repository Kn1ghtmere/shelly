"""Copying and moving things, including the questions that come up on the way:
a missing folder (create it?) or a name clash (replace / keep both / cancel)."""

import os
import shutil
from collections.abc import Callable
from pathlib import Path

from . import paths
from .result import NO_WORDS, Ask, Choice, Result

REPLACE_WORDS = frozenset({"replace", "r", "overwrite", "replace it", "overwrite it"})
KEEP_WORDS = frozenset({"keep both", "both", "keep", "b", "duplicate", "keep them", "number"})
CANCEL_WORDS = NO_WORDS | frozenset({"c"})


class TransferError(Exception):
    """A problem found while working out where things should go."""


OnDone = Callable[[Path], None]


def absolute(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))


def looks_like_file_name(text: str, source: Path) -> bool:
    """'copy a.txt to b.txt' names a new file. 'copy a.txt to backup' names a folder."""
    return source.is_file() and Path(text).suffix != ""


def split_missing(path: Path) -> tuple[Path, str]:
    """For a folder that doesn't exist: (the part that does, the part that doesn't)."""
    path = absolute(path)
    missing: list[str] = []
    current = path
    while not current.exists() and current != current.parent:
        missing.append(current.name)
        current = current.parent
    return current, str(Path(*reversed(missing))) if missing else ""


def unique_name(target: Path) -> Path:
    """notes.txt -> notes (2).txt, src -> src (2)"""
    if target.is_dir():
        stem, suffix = target.name, ""
    else:
        stem, suffix = target.stem, target.suffix
    number = 2
    while True:
        candidate = target.with_name(f"{stem} ({number}){suffix}")
        if not candidate.exists():
            return candidate
        number += 1


def send(
    sources: list[Path],
    dest_text: str | None,
    mode: str,
    on_done: OnDone | None = None,
) -> Result:
    """Copy or move `sources`. mode is 'copy' or 'move'.
    dest_text None means the current folder."""
    sources = [absolute(s) for s in sources]
    try:
        folder, pairs = _targets(sources, dest_text)
        for source, target in pairs:
            _check(source, target, mode)
    except TransferError as error:
        return Result.fail(str(error))

    if folder.exists() and not folder.is_dir():
        return Result.fail(f"'{folder.name}' is a file, not a folder.")
    if not folder.exists():
        return _ask_create(folder, lambda: _process(pairs, 0, [], mode, on_done))
    return _process(pairs, 0, [], mode, on_done)


# --- working out where things go ------------------------------------------


def _targets(sources: list[Path], dest_text: str | None) -> tuple[Path, list[tuple[Path, Path]]]:
    if dest_text is None:
        folder = Path.cwd()
        return folder, [(s, folder / s.name) for s in sources]

    dest = paths.resolve_existing(dest_text)
    if dest is not None:
        dest = absolute(dest)
        if dest.is_dir():
            return dest, [(s, dest / s.name) for s in sources]
        if len(sources) != 1:
            raise TransferError("I can't put several things into one file.")
        return dest.parent, [(sources[0], dest)]

    path = absolute(Path(dest_text))
    if len(sources) == 1 and looks_like_file_name(dest_text, sources[0]):
        return path.parent, [(sources[0], path)]
    return path, [(s, path / s.name) for s in sources]


def _same(a: Path, b: Path) -> bool:
    try:
        return a.exists() and b.exists() and a.samefile(b)
    except OSError:
        return False


def _inside(target: Path, folder: Path) -> bool:
    target, folder = target.resolve(), folder.resolve()
    return target == folder or folder in target.parents


def _check(source: Path, target: Path, mode: str) -> None:
    if not source.exists():
        raise TransferError(f"'{source.name}' isn't there anymore.")
    if mode == "move" and paths.is_protected(source):
        raise TransferError("That's an important folder, so I won't move it.")
    if source.is_dir() and not _same(source, target) and _inside(target, source):
        raise TransferError("I can't put a folder inside itself.")


# --- the questions -----------------------------------------------------------


def _ask_create(folder: Path, proceed: Callable[[], Result]) -> Result:
    location, name = split_missing(folder)
    prompt = (
        f"There is no folder named '{name}' in '{location}'. "
        f"Would you like me to create one and continue?"
    )

    def create() -> Result:
        try:
            folder.mkdir(parents=True)
        except OSError as error:
            return Result.fail(f"I couldn't make that folder: {error}")
        return proceed()

    return Result.asking(Ask.yes_no(prompt, create))


def _conflict(pairs, index, lines, mode, on_done, allow_replace: bool) -> Result:
    source, target = pairs[index]
    if allow_replace:
        prompt = f"'{target.name}' already exists in '{target.parent}'. What should I do?"
    else:
        prompt = f"'{target.name}' is already in '{target.parent}'. What should I do?"

    def go(final: Path, replace: bool) -> Callable[[], Result]:
        return lambda: _apply(pairs, index, lines, mode, on_done, final, replace)

    def cancel() -> Result:
        done = "\n".join(lines) + "\n" if lines else ""
        return Result.success(done + "Okay, cancelled. Nothing else was changed.")

    choices = []
    if allow_replace:
        choices.append(Choice("replace", REPLACE_WORDS, go(target, True)))
    choices.append(Choice("keep both", KEEP_WORDS, go(unique_name(target), False)))
    choices.append(Choice("cancel", CANCEL_WORDS, cancel))
    return Result.asking(Ask(prompt, choices))


# --- doing it ------------------------------------------------------------------


def _process(pairs, index, lines, mode, on_done) -> Result:
    while index < len(pairs):
        source, target = pairs[index]
        if target.exists():
            if _same(source, target):
                if mode == "move":
                    lines.append(f"'{source.name}' is already in {target.parent}.")
                    index += 1
                    continue
                return _conflict(pairs, index, lines, mode, on_done, allow_replace=False)
            return _conflict(pairs, index, lines, mode, on_done, allow_replace=True)
        return _apply(pairs, index, lines, mode, on_done, target, replace=False)
    return Result.success("\n".join(lines))


def _apply(pairs, index, lines, mode, on_done, target: Path, replace: bool) -> Result:
    source = pairs[index][0]
    try:
        _do(source, target, mode, replace)
    except (OSError, shutil.Error) as error:
        done = "\n".join(lines) + "\n" if lines else ""
        return Result.fail(f"{done}I couldn't {mode} {source.name}: {error}")

    verb = "Copied" if mode == "copy" else "Moved"
    note = " (replaced the old one)" if replace else ""
    lines.append(f"{verb} {source.name} to {target}{note}")
    if mode == "move" and on_done:
        on_done(source)
    return _process(pairs, index + 1, lines, mode, on_done)


def _do(source: Path, target: Path, mode: str, replace: bool) -> None:
    if replace and target.exists():
        # Put the new one next to the old one first, so a failure can't lose both.
        staging = target.with_name(target.name + ".shelly-new")
        if staging.exists():
            raise OSError(f"{staging.name} is in the way")
        _transfer(source, staging, mode)
        _remove(target)
        staging.rename(target)
    else:
        _transfer(source, target, mode)


def _transfer(source: Path, target: Path, mode: str) -> None:
    if mode == "copy":
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    else:
        shutil.move(str(source), str(target))


def _remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()
