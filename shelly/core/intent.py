from dataclasses import dataclass, field


@dataclass
class Intent:
    """One parsed line: what to do (verb), what it's about (args), extras (options)."""

    verb: str
    args: list[str] = field(default_factory=list)
    options: dict[str, str] = field(default_factory=dict)
    raw: str = ""
    line_number: int | None = None

    @property
    def target(self) -> str | None:
        return self.args[0] if self.args else None

    @property
    def rest(self) -> list[str]:
        return self.args[1:]

    @property
    def text(self) -> str:
        return " ".join(self.args)
