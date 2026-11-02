import shutil
from pathlib import Path
from urllib.parse import urlparse

from .. import platform as plat
from ..core import appbook, paths
from ..core.intent import Intent
from ..core.registry import command
from ..core.result import Result
from ._common import not_found, quote_hint, reject_options

ADD_USAGE = (
    'Try: add app "C:\\Program Files\\Spotify\\spotify.exe" as spotify\n'
    "  or: add website https://example.com as example"
)


@command("open")
def open_command(intent: Intent) -> Result:
    """open <app>   |   open <app> <action> <query>   |   open <file or folder>"""
    if not intent.args:
        return Result.fail('Open what? For example: open youtube   or   open youtube search "lofi"')

    unused = sorted(set(intent.options) - {"volume"})
    if unused:
        return Result.fail(f"'open' doesn't use '{unused[0]}'.")

    try:
        book = appbook.get_book()
    except appbook.AppConfigError as error:
        return Result.fail(str(error))

    app = book.find(intent.args[0])
    if app is None:
        return _open_unknown(intent, book)

    if len(intent.args) > 3:
        extra = " ".join(intent.args[2:])
        return Result.fail(
            f'That\'s a lot of words. If "{extra}" is one thing, put it in quotes: '
            f'open {intent.args[0]} {intent.args[1]} "{extra}"'
        )

    try:
        message = _run(app, intent.args[1:])
    except plat.PlatformError as error:
        return Result.fail(str(error))
    if isinstance(message, Result):
        return message

    if "volume" in intent.options:
        message += f" (I noted volume {intent.options['volume']}, but volume control isn't built yet.)"
    return Result.success(message)


def _run(app: appbook.App, rest: list[str]) -> "str | Result":
    system = plat.current()

    if app.kind == "app":
        launch = app.launch_name(system.key)
        if not rest:
            system.open_app(launch)
            return f"Opened {app.name}."
        if not app.actions:
            return Result.fail(f"{app.name} doesn't take extra words. Just: open {app.name}")
        return _run_action(app, rest, lambda url: system.open_url_in(launch, url))

    if not rest:
        system.open_url(app.home)
        return f"Opened {app.name}."
    return _run_action(app, rest, system.open_url)


def _run_action(app: appbook.App, rest: list[str], opener) -> "str | Result":
    action = app.actions.get(rest[0].lower())
    if action is None:
        if not app.actions:
            return Result.fail(f"{app.name} doesn't have any actions yet. Just: open {app.name}")
        names = ", ".join(sorted(app.actions))
        return Result.fail(
            f"{app.name} can't '{rest[0]}'. It can: {names}. "
            f'Try: open {app.name} {sorted(app.actions)[0]} "something"'
        )
    if len(rest) < 2:
        return Result.fail(f'{action.name} needs something. Try: open {app.name} {action.name} "something"')

    query = rest[1]
    opener(action.build(query))
    return action.note or f'Opened {app.name}: {action.name} "{query}".'


def _open_unknown(intent: Intent, book: appbook.AppBook) -> Result:
    name = intent.args[0]

    if len(intent.args) == 1:
        path = Path(name).expanduser()
        if path.exists():
            try:
                plat.current().open_path(path)
            except plat.PlatformError as error:
                return Result.fail(str(error))
            return Result.success(f"Opened {path}.")

    message = f"I don't know an app called '{name}'."
    guess = book.suggest(name)
    if guess:
        message += f" Did you mean '{guess}'?"
    message += f" You can add it with: add app \"path\" as {name}"
    return Result.fail(message)


@command("apps")
def list_apps(intent: Intent) -> Result:
    """Shows every app Shelly knows."""
    try:
        book = appbook.get_book()
    except appbook.AppConfigError as error:
        return Result.fail(str(error))

    lines = [f"Apps I know (your own are saved in {appbook.USER_FILE}):"]
    for app in book.all():
        label = app.name + (f" ({', '.join(app.aliases)})" if app.aliases else "")
        extra = f"  - {', '.join(sorted(app.actions))}" if app.actions else ""
        lines.append(f"  {label}{extra}")
    return Result.success("\n".join(lines))


# --- adding and removing your own apps ----------------------------------


def _valid_name(name: str) -> bool:
    return bool(name) and not any(ch in name for ch in "[]\".'\\/")


@command("add")
def add(intent: Intent) -> Result:
    """add app <path> [as <name>]   |   add website <url> [as <name>]"""
    bad = reject_options(intent, {"as"})
    if bad:
        return bad
    what = intent.args[0].lower() if intent.args else ""
    if what not in ("app", "website") or len(intent.args) < 2:
        return Result.fail(ADD_USAGE)
    if len(intent.args) > 2:
        return quote_hint(intent, intent.args[1:])

    target = intent.args[1]
    name = intent.options.get("as")
    return _add_app(target, name) if what == "app" else _add_website(target, name)


def _finish_add(name: str, fields: dict[str, str]) -> Result:
    name = name.strip().lower()
    if not _valid_name(name):
        return Result.fail(f"'{name}' isn't a name I can use. Pick a simple one, like: as spotify")

    try:
        mine = appbook.AppBook.load([appbook.USER_FILE])
        builtin = appbook.get_book().find(name)
    except appbook.AppConfigError as error:
        return Result.fail(str(error))
    if mine.find(name):
        return Result.fail(f"You already added '{name}'. To replace it: remove app {name}")

    appbook.append_user_section(name, fields)
    note = " This replaces the built-in one." if builtin else ""
    return Result.success(f"Added {name}. Try: open {name}.{note}")


def _add_app(target: str, name: str | None) -> Result:
    path = paths.resolve_existing(target)
    if path is not None and (path.is_file() or path.suffix == ".app"):
        launch = str(path.resolve())
        default = path.stem
    elif shutil.which(target):
        launch = target
        default = Path(target).stem
    else:
        return not_found(target)

    chosen = name or default.replace(" ", "-")
    return _finish_add(chosen, {"type": "app", plat.current().key: launch})


def _add_website(target: str, name: str | None) -> Result:
    url = target if "://" in target else f"https://{target}"
    host = urlparse(url).hostname
    if not host:
        return Result.fail(f"'{target}' doesn't look like a web address.")
    default = host.removeprefix("www.").split(".")[0]
    return _finish_add(name or default, {"type": "web", "home": url})


@command("remove")
def remove(intent: Intent) -> Result:
    """remove app <name>"""
    bad = reject_options(intent, set())
    if bad:
        return bad
    if len(intent.args) != 2 or intent.args[0].lower() not in ("app", "website"):
        return Result.fail("Try: remove app spotify")

    name = intent.args[1].lower()
    try:
        if appbook.remove_user_section(name):
            return Result.success(f"Removed {name}.")
        book = appbook.get_book()
    except appbook.AppConfigError as error:
        return Result.fail(str(error))

    if book.find(name):
        return Result.fail(f"'{name}' is built in, so I can only remove apps you added yourself.")
    return Result.fail(f"I don't have an app called '{name}'.")
