from .. import commands  # noqa: F401  (registers commands)
from ..core.engine import run_line


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
        if result.message:
            print(result.message)
        if result.should_exit:
            break
