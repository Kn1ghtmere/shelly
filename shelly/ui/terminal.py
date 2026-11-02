from .. import commands  # noqa: F401  (registers commands)
from ..core.engine import answer, run_line
from ..core.result import Ask, Result


def main() -> None:
    print("Shelly here. Try 'hello' or 'bye'.")
    while True:
        try:
            line = input("shelly> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        result = run_line(line)
        if result is None:
            continue
        if show(result):
            break


def show(result: Result) -> bool:
    """Print a result, asking any questions it raises. True means 'exit Shelly'."""
    while result.ask is not None:
        result = ask_person(result.ask)
    if result.message:
        print(result.message)
    return result.should_exit


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
