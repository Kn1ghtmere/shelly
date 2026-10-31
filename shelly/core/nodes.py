from dataclasses import dataclass, field

from .intent import Intent


@dataclass
class Line:
    intent: Intent


@dataclass
class Block:
    """A header line (if / repeat / for / define) plus everything up to its 'end'."""

    header: Intent
    body: list = field(default_factory=list)
    else_body: list = field(default_factory=list)
    in_else: bool = False


Node = Line | Block
