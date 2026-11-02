from ..core.errors import ParseError
from ..core.intent import Intent
from ..core.parser import parse_line
from ..core.registry import command
from ..core.result import Result

FAREWELLS = {
    "bye": "Bye!",
    "goodbye": "Goodbye! See you soon.",
    "exit": "Closing Shelly.",
    "quit": "Closing Shelly.",
    "end": "All done. See you!",
}


@command("hello", "hi")
def hello(intent: Intent) -> Result:
    return Result.success("Hello! I'm Shelly.")


@command(*FAREWELLS)
def leave(intent: Intent) -> Result:
    return Result(True, FAREWELLS.get(intent.verb, "Bye!"), should_exit=True)


@command("say")
def say(intent: Intent) -> Result:
    return Result.success(intent.text)


@command("parse")
def parse_debug(intent: Intent) -> Result:
    """Shows how Shelly reads a line. Handy for learning the grammar."""
    parts = intent.raw.split(None, 1)
    if len(parts) < 2:
        return Result.fail("Type 'parse' then a line, e.g. parse open youtube play lofi volume 50")
    try:
        shown = parse_line(parts[1])
    except ParseError as error:
        return Result.fail(str(error))
    return Result.success(
        f"verb:    {shown.verb}\nargs:    {shown.args}\noptions: {shown.options}"
    )
