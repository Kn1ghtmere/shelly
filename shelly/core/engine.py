from . import registry
from .errors import ParseError
from .parser import parse_line
from .result import Ask, Result


def run_line(line: str) -> Result | None:
    if not line.strip():
        return None

    try:
        intent = parse_line(line)
    except ParseError as error:
        return Result.fail(str(error))

    handler = registry.find(intent.verb)
    if handler is None:
        return Result.fail(f"I don't know '{intent.verb}' yet.")

    return handler(intent)


def answer(ask: Ask, text: str) -> Result | None:
    """Act on someone's reply to a question. None means 'I didn't understand'."""
    choice = ask.match(text)
    return choice.run() if choice else None
