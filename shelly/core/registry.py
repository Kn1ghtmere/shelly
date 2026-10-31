from typing import Callable

from .intent import Intent
from .result import Result

Handler = Callable[[Intent], Result]

_commands: dict[str, Handler] = {}


def command(*names: str):
    def decorator(func: Handler) -> Handler:
        for name in names:
            _commands[name.lower()] = func
        return func
    return decorator


def find(name: str) -> Handler | None:
    return _commands.get(name.lower())


def all_names() -> list[str]:
    return sorted(_commands)
