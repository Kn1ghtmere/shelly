import shutil
from pathlib import Path
from urllib.parse import urlparse

from .. import platform as plat
from ..core import appbook, paths
from ..core.intent import Intent
from ..core.registry import command
from ..core.result import NO_WORDS, Ask, Choice, Result, clean_answer
from ._common import not_found, quote_hint, reject_options, sources_of
from .trash import delete

ADD_USAGE = (
    'Try: add app "C:\\Program Files\\Spotify\\spotify.exe" as spotify\n'
    "  or: add website https://example.com as example"
)
SEARCH_ENGINES = [
    ("google", "https://www.google.com/search?q={query}"),
    ("duckduckgo", "https://duckduckgo.com/?q={query}"),
    ("bing", "https://www.bing.com/search?q={query}"),
    ("brave search", "https://search.brave.com/search?q={query}"),
]


# --- open ------------------------------------------------------------------


@command("open")
def open_command(intent: Intent) -> Result:
    """open <app>   |   open <app> <action> <query>   |   open <site> in <browser>   |   open <file>"""
    if not intent.args:
        return Result.fail('Open what? For example: open youtube   or   open youtube search "lofi"')
    bad = reject_options(intent, {"volume", "in", "using"})
    if bad:
        return bad

    try:
        book = appbook.get_book()
    except appbook.AppConfigError as error:
        return Result.fail(str(error))

    browser, chain, problem = _pick_browser(intent, book)
    if problem:
        return problem

    app = book.find(intent.args[0])
    if app is None:
        return _open_unknown(intent, book, browser, chain)
    if chain:
        return Result.fail(
            f"'{app.name}' is an app, so 'in {chain[0]}' doesn't apply. "
            f"To open a site in a browser: open {app.name} using <browser>"
        )

    if len(intent.args) > 3:
        extra = " ".join(intent.args[2:])
        return Result.fail(
            f'That\'s a lot of words. If "{extra}" is one thing, put it in quotes: '
            f'open {intent.args[0]} {intent.args[1]} "{extra}"'
        )

    try:
        message = _run(app, intent.args[1:], browser)
    except plat.PlatformError as error:
        return Result.fail(str(error))
    if isinstance(message, Result):
        return message

    if browser is not None:
        message += f" (in {browser.name})"
    if "volume" in intent.options:
        message += f" (I noted volume {intent.options['volume']}, but volume control isn't built yet.)"
    return Result.success(message)


def _pick_browser(intent: Intent, book: appbook.AppBook):
    """Which browser (if any) the user asked for: 'using x', or 'in x' when x is a browser."""
    chain = list(intent.containers.get("", []))
    using = intent.options.get("using")
    if using:
        browser = book.find(using)
        if browser is None:
            guess = book.suggest(using)
            hint = f" Did you mean '{guess}'?" if guess else ""
            return None, chain, Result.fail(f"I don't know a browser called '{using}'.{hint}")
        if browser.role != "browser":
            return None, chain, Result.fail(
                f"'{browser.name}' isn't a browser. (When you add an app, choose 'browser' as its type.)"
            )
        return browser, chain, None
    if len(chain) == 1:
        candidate = book.find(chain[0])
        if candidate is not None and candidate.role == "browser":
            return candidate, [], None
    return None, chain, None


def _run(app: appbook.App, rest: list[str], browser: appbook.App | None) -> "str | Result":
    system = plat.current()

    if app.kind == "app":
        if browser is not None:
            return Result.fail(
                f"{app.name} is a program, not a website, so it can't open inside {browser.name}."
            )
        launch = app.launch_name(system.key)
        if not rest:
            system.open_app(launch)
            return f"Opened {app.name}."
        if not app.actions:
            return Result.fail(f"{app.name} doesn't take extra words. Just: open {app.name}")
        return _run_action(app, rest, lambda url: system.open_url_in(launch, url))

    if browser is None:
        opener = system.open_url
    else:
        browser_name = browser.launch_name(system.key)
        opener = lambda url: system.open_url_in(browser_name, url)  # noqa: E731

    if not rest:
        opener(app.home)
        return f"Opened {app.name}."
    return _run_action(app, rest, opener)


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


def _open_unknown(intent: Intent, book: appbook.AppBook, browser, chain: list[str]) -> Result:
    name = intent.args[0]
    system = plat.current()

    if len(intent.args) == 1:
        try:
            if name.lower().startswith(("http://", "https://")):
                if browser is None:
                    system.open_url(name)
                else:
                    system.open_url_in(browser.launch_name(system.key), name)
                return Result.success(f"Opened {name}.")

            found = paths.locate(name, chain)
            if not isinstance(found, str):
                system.open_path(found.resolve())
                return Result.success(f"Opened {found.resolve()}.")
            if chain:
                return Result.fail(found)
        except plat.PlatformError as error:
            return Result.fail(str(error))

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


# --- close -------------------------------------------------------------------


@command("close")
def close(intent: Intent) -> Result:
    """close <app> [and <app>]"""
    bad = reject_options(intent, set())
    if bad:
        return bad
    names = sources_of(intent)
    if isinstance(names, Result):
        return names
    if not names:
        return Result.fail("Close what? For example: close notepad")

    try:
        book = appbook.get_book()
    except appbook.AppConfigError as error:
        return Result.fail(str(error))

    system = plat.current()
    lines, failed = [], False
    for name in names:
        app = book.find(name)
        if app is None:
            guess = book.suggest(name)
            lines.append(f"I don't know an app called '{name}'." + (f" Did you mean '{guess}'?" if guess else ""))
            failed = True
        elif app.kind == "web":
            lines.append(f"{app.name} is a website, so it's a tab, not a program. I can't close tabs yet.")
            failed = True
        else:
            process = app.process if system.key == "windows" else None
            try:
                system.close_app(app.launch_name(system.key), process or None)
                lines.append(f"Asked {app.name} to close. (If it has unsaved work, it will ask you first.)")
            except plat.PlatformError as error:
                lines.append(str(error))
                failed = True
    return Result(not failed, "\n".join(lines))


# --- adding and removing your own apps ----------------------------------------


def _valid_name(name: str) -> bool:
    return bool(name) and not any(ch in name for ch in "[]\".'\\/ ")


@command("add")
def add(intent: Intent) -> Result:
    """add app <path or link> [as <name>]   |   add website <url> [as <name>]"""
    bad = reject_options(intent, {"as"})
    if bad:
        return bad
    what = intent.args[0].lower() if intent.args else ""
    if what not in ("app", "website", "link") or len(intent.args) < 2:
        return Result.fail(ADD_USAGE)
    if len(intent.args) > 2:
        return quote_hint(intent, intent.args[1:])

    target, name = intent.args[1], intent.options.get("as")
    if what in ("website", "link") or "://" in target:
        return _add_website(target, name)
    return _add_app(target, name)


def _prepare(name: str) -> "tuple[str, str] | Result":
    name = name.strip().lower()
    if not _valid_name(name):
        return Result.fail(f"'{name}' isn't a name I can use. Pick one simple word, like: as spotify")
    try:
        mine = appbook.AppBook.load([appbook.USER_FILE])
        builtin = appbook.get_book().find(name)
    except appbook.AppConfigError as error:
        return Result.fail(str(error))
    if mine.find(name):
        return Result.fail(f"You already added '{name}'. To replace it: remove app {name}")
    return name, (" This replaces the built-in one." if builtin else "")


def _save(name: str, fields: dict[str, str], actions: dict[str, str] | None, note: str) -> Result:
    try:
        appbook.append_user_section(name, fields, actions)
    except OSError as error:
        return Result.fail(f"I couldn't save that: {error}")
    hint = f"Try: open {name}"
    if actions and "search" in actions:
        hint += f'   or: open {name} search "something"'
    if fields.get("role") == "browser":
        hint += f"   or: open youtube in {name}"
    return Result.success(f"Added {name}. {hint}.{note}")


def _add_app(target: str, name: str | None) -> Result:
    path = paths.resolve_existing(target)
    if path is not None and (path.is_file() or path.suffix == ".app"):
        launch, default = str(path.resolve()), path.stem
    elif shutil.which(target):
        launch, default = target, Path(target).stem
    else:
        return not_found(target)

    prepared = _prepare(name or default.replace(" ", "-"))
    if isinstance(prepared, Result):
        return prepared
    chosen, note = prepared
    key = plat.current().key

    def as_browser() -> Result:
        return _ask_search_engine(chosen, {"type": "app", key: launch, "role": "browser"}, note)

    def as_other() -> Result:
        return _save(chosen, {"type": "app", key: launch}, None, note)

    return Result.asking(Ask(
        f"Please choose an app type for {chosen}:\n  1. browser\n  2. other app",
        [
            Choice("1", frozenset({"1", "one", "browser", "a browser"}), as_browser),
            Choice("2", frozenset({"2", "two", "other", "other app", "app", "none", "normal"}), as_other),
        ],
        hint_text="1 / 2",
    ))


def _ask_search_engine(name: str, fields: dict[str, str], note: str) -> Result:
    lines = [f"  {i}. {label}" for i, (label, _) in enumerate(SEARCH_ENGINES, start=1)]
    lines.append(f"  {len(SEARCH_ENGINES) + 1}. none")
    choices = []
    for number, (label, url) in enumerate(SEARCH_ENGINES, start=1):
        words = frozenset({str(number), label, label.split()[0]})
        choices.append(Choice(str(number), words, lambda url=url: _save(name, fields, {"search": url}, note)))
    none = frozenset({str(len(SEARCH_ENGINES) + 1), "none", "no", "skip", "nope"})
    choices.append(Choice(str(len(SEARCH_ENGINES) + 1), none, lambda: _save(name, fields, None, note)))
    hint = " / ".join(c.label for c in choices)
    return Result.asking(Ask(
        f"Which search should 'open {name} search ...' use?\n" + "\n".join(lines), choices, hint_text=hint
    ))


def _add_website(target: str, name: str | None) -> Result:
    url = target if "://" in target else f"https://{target}"
    host = urlparse(url).hostname
    if not host:
        return Result.fail(f"'{target}' doesn't look like a web address.")

    prepared = _prepare(name or host.removeprefix("www.").split(".")[0])
    if isinstance(prepared, Result):
        return prepared
    chosen, note = prepared
    fields = {"type": "web", "home": url}

    prompt = (
        f"Does {chosen} have a search page? Paste its search address, using {{query}} "
        f"where the search words go (like https://example.com/search?q={{query}}), or say no."
    )

    def read(text: str) -> Result:
        if clean_answer(text) in NO_WORDS:
            return _save(chosen, fields, None, note)
        address = text.strip()
        if "{query}" in address and "://" in address:
            return _save(chosen, fields, {"search": address}, note)
        return Result.asking(Ask.text(
            "That address needs {query} in it, where the search words go. Try again, or say no.", read
        ))

    return Result.asking(Ask.text(prompt, read))


@command("remove")
def remove(intent: Intent) -> Result:
    """remove app <name>   |   remove <file>  (same as delete)"""
    if not (intent.args and intent.args[0].lower() in ("app", "website", "link")):
        return delete(intent)

    bad = reject_options(intent, set())
    if bad:
        return bad
    if len(intent.args) != 2:
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
