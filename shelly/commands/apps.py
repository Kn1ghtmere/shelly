from pathlib import Path

from .. import platform as plat
from ..core import appbook
from ..core.intent import Intent
from ..core.registry import command
from ..core.result import Result


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

    name = intent.args[0]
    app = book.find(name)
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
        if rest:
            return Result.fail(f"{app.name} doesn't take extra words. Just: open {app.name}")
        system.open_app(app.launch_name(system.key))
        return f"Opened {app.name}."

    if not rest:
        system.open_url(app.home)
        return f"Opened {app.name}."

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
    system.open_url(action.build(query))
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
    message += f" You can add it to {appbook.USER_FILE}."
    return Result.fail(message)


@command("apps")
def list_apps(intent: Intent) -> Result:
    """Shows every app Shelly knows."""
    try:
        book = appbook.get_book()
    except appbook.AppConfigError as error:
        return Result.fail(str(error))

    lines = [f"Apps I know (add your own in {appbook.USER_FILE}):"]
    for app in book.all():
        label = app.name + (f" ({', '.join(app.aliases)})" if app.aliases else "")
        extra = f"  - {', '.join(sorted(app.actions))}" if app.actions else ""
        lines.append(f"  {label}{extra}")
    return Result.success("\n".join(lines))
