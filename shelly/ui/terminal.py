from .. import commands  # noqa: F401  (registers commands)
from ..core.engine import answer, run_chain
from ..core.result import Ask, Result
from . import completion


def main() -> None:
    completion.setup()
    print("Shelly here. Try 'hello', 'help' or 'bye'.")
    while True:
        try:
            line = input("shelly> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line.strip():
            continue
        if any(result.should_exit for result in run_chain(line, settle)):
            break


def settle(result: Result) -> Result:
    """Show a result, asking any questions it raises. Returns the final result."""
    while result.ask is not None:
        result = ask_person(result.ask)
    if result.message:
        print(result.message)
    return result


def show(result: Result) -> bool:
    """Like settle, but returns True when Shelly should exit."""
    return settle(result).should_exit


def ask_person(ask: Ask) -> Result:
    for _ in range(3):
        try:
            reply = input(f"{ask.prompt} ({ask.hint}) ")
        except (EOFError, KeyboardInterrupt):
            print()
            return Result.success("Okay, cancelled. Nothing was changed.")
        outcome = answer(ask, reply)
        if outcome is not None:
            return outcome
        print(f"I didn't catch that. Please say: {ask.hint}")
    return Result.success("Okay, I'll leave it there. Nothing was changed.")
