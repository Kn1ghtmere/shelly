from dataclasses import dataclass, field


@dataclass
class Intent:
    """One parsed line: what to do (verb), what it's about (args), extras (options)."""

    verb: str
    args: list[str] = field(default_factory=list)
    options: dict[str, str] = field(default_factory=dict)
    raw: str = ""
    line_number: int | None = None
    # 'in' chains. Key "" belongs to the args ("tools in assets in D:" ->
    # {"": ["assets", "D:"]}); other keys belong to that option ("to X in Y").
    containers: dict[str, list[str]] = field(default_factory=dict)

    @property
    def target(self) -> str | None:
        return self.args[0] if self.args else None

    @property
    def rest(self) -> list[str]:
        return self.args[1:]

    @property
    def text(self) -> str:
        return " ".join(self.args)

    def items(self) -> list[str]:
        """The args split at the word 'and':  a and my b.txt  ->  ['a', 'my b.txt']"""
        groups: list[str] = []
        current: list[str] = []
        for arg in self.args:
            if arg.lower() == "and" and current:
                groups.append(" ".join(current))
                current = []
            else:
                current.append(arg)
        if current:
            groups.append(" ".join(current))
        return groups
