from dataclasses import dataclass
from typing import Any


@dataclass
class Result:
    ok: bool
    message: str = ""
    data: Any = None
    should_exit: bool = False

    @classmethod
    def success(cls, message: str = "", data: Any = None) -> "Result":
        return cls(True, message, data)

    @classmethod
    def fail(cls, message: str, data: Any = None) -> "Result":
        return cls(False, message, data)
