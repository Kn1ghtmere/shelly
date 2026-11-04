"""The list of apps Shelly knows, loaded from apps.toml files."""

import difflib
import json
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote_plus

DEFAULT_FILE = Path(__file__).resolve().parent.parent / "data" / "apps.toml"
USER_FILE = Path.home() / ".shelly" / "apps.toml"


class AppConfigError(Exception):
    """apps.toml has a mistake. The message says where."""


@dataclass
class Action:
    name: str
    url: str
    note: str = ""

    def build(self, query: str) -> str:
        return self.url.replace("{query}", quote_plus(query))


@dataclass
class App:
    name: str
    kind: str  # "web" or "app"
    aliases: list[str] = field(default_factory=list)
    home: str = ""
    actions: dict[str, Action] = field(default_factory=dict)
    launch: dict[str, str] = field(default_factory=dict)
    role: str = ""  # "browser" for browsers: sites can be opened in them
    process: str = ""  # program name to close, when it differs from the launch name

    def launch_name(self, platform_key: str) -> str:
        return self.launch.get(platform_key) or self.launch.get("name") or self.name


class AppBook:
    def __init__(self, apps: dict[str, App]):
        self._apps = apps
        self._lookup: dict[str, App] = {}
        for app in apps.values():
            self._lookup[app.name] = app
            for alias in app.aliases:
                self._lookup[alias] = app

    @classmethod
    def load(cls, files: list[Path]) -> "AppBook":
        apps: dict[str, App] = {}
        for file in files:
            file = Path(file)
            if not file.exists():
                continue
            try:
                with file.open("rb") as handle:
                    raw = tomllib.load(handle)
            except tomllib.TOMLDecodeError as error:
                raise AppConfigError(f"I couldn't read {file}: {error}") from error
            for name, spec in raw.items():
                try:
                    apps[name.lower()] = _parse_app(name, spec)
                except AppConfigError as error:
                    raise AppConfigError(f"{file}: {error}") from error
        return cls(apps)

    def find(self, word: str) -> App | None:
        return self._lookup.get(word.lower())

    def suggest(self, word: str) -> str | None:
        match = difflib.get_close_matches(word.lower(), list(self._lookup), n=1, cutoff=0.6)
        return self._lookup[match[0]].name if match else None

    def all(self) -> list[App]:
        return [self._apps[name] for name in sorted(self._apps)]


def _parse_app(name: str, spec: object) -> App:
    if not isinstance(spec, dict):
        raise AppConfigError(f"'{name}' should be a [section], like [{name}].")

    kind = spec.get("type", "app")
    if kind not in ("web", "app"):
        raise AppConfigError(f"'{name}': type must be \"web\" or \"app\".")
    if kind == "web" and not spec.get("home"):
        raise AppConfigError(f"'{name}': web apps need a home = \"https://...\" line.")

    actions: dict[str, Action] = {}
    for action_name, action_spec in spec.get("actions", {}).items():
        if isinstance(action_spec, str):
            action_spec = {"url": action_spec}
        if not isinstance(action_spec, dict) or "url" not in action_spec:
            raise AppConfigError(f"'{name}' action '{action_name}' needs a url.")
        actions[action_name.lower()] = Action(
            action_name.lower(), action_spec["url"], action_spec.get("note", "")
        )

    launch = {key: spec[key] for key in ("name", "windows", "mac", "linux") if key in spec}

    return App(
        name=name.lower(),
        kind=kind,
        aliases=[alias.lower() for alias in spec.get("aliases", [])],
        home=spec.get("home", ""),
        actions=actions,
        launch=launch,
        role=str(spec.get("role", "")).lower(),
        process=str(spec.get("process", "")),
    )


_book: AppBook | None = None


def get_book() -> AppBook:
    global _book
    if _book is None:
        _book = AppBook.load([DEFAULT_FILE, USER_FILE])
    return _book


def set_book(book: AppBook | None) -> None:
    """Swap the app list (used by tests). None means 'reload from disk'."""
    global _book
    _book = book


# --- editing the user's own apps.toml -----------------------------------


def _toml_string(value: str) -> str:
    # Single quotes mean "no escaping", which keeps Windows paths readable.
    if "'" not in value and "\n" not in value:
        return f"'{value}'"
    return json.dumps(value, ensure_ascii=False)


def _toml_key(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z0-9_-]+", name) else json.dumps(name)


def append_user_section(
    name: str,
    fields: dict[str, str],
    actions: dict[str, str] | None = None,
    file: Path | None = None,
) -> None:
    """Add a [name] section (and an optional [name.actions] one) to the user's apps.toml."""
    file = file or USER_FILE
    file.parent.mkdir(parents=True, exist_ok=True)
    existing = file.read_text(encoding="utf-8") if file.exists() else ""
    key = _toml_key(name)
    block = f"[{key}]\n" + "".join(f"{k} = {_toml_string(v)}\n" for k, v in fields.items())
    if actions:
        block += f"\n[{key}.actions]\n" + "".join(
            f"{k} = {_toml_string(v)}\n" for k, v in actions.items()
        )
    if existing and not existing.endswith("\n"):
        existing += "\n"
    if existing and not existing.endswith("\n\n"):
        existing += "\n"
    file.write_text(existing + block, encoding="utf-8")
    set_book(None)


_HEADER = re.compile(r"^\s*\[\s*([^\[\]]+?)\s*\]\s*(#.*)?$")


def _table_name(line: str) -> str | None:
    match = _HEADER.match(line)
    return match.group(1).strip("\"'").lower() if match else None


def remove_user_section(name: str, file: Path | None = None) -> bool:
    """Remove [name] (and its sub-tables) from the user's apps.toml. False if absent."""
    file = file or USER_FILE
    if not file.exists():
        return False
    wanted = name.lower()
    lines = file.read_text(encoding="utf-8").splitlines(keepends=True)

    start = next((i for i, line in enumerate(lines) if _table_name(line) == wanted), None)
    if start is None:
        return False
    end = len(lines)
    for j in range(start + 1, len(lines)):
        other = _table_name(lines[j])
        if other is not None and not other.startswith(wanted + "."):
            end = j
            break

    del lines[start:end]
    text = "".join(lines).rstrip()
    file.write_text(text + "\n" if text else "", encoding="utf-8")
    set_book(None)
    return True
