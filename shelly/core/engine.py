import difflib
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from . import registry
from .aliases import ALIASES
from .errors import ParseError
from .intent import Intent
from .parser import parse_chain, parse_line
from .result import ANSWER_WORDS, CLEAR_ANSWERS, Ask, Result, clean_answer


def run_line(line: str) -> Result | None:
    """Run ONE command. (Use run_chain for lines with 'and' / 'and then'.)"""
    if not line.strip():
        return None
    try:
        intent = parse_line(line)
    except ParseError as error:
        return Result.fail(str(error))
    return _execute(intent)


def run_chain(line: str, settle: Callable[[Result], Result]) -> list[Result]:
    """Run a line that may hold several commands.

    `settle` belongs to the front end: it shows a result, asks any question
    the result raises, and returns the final Result. Commands joined by
    'and' run at the same time; 'and then' waits for the one before it and
    stops the line if that one failed.
    """
    try:
        chain = parse_chain(line)
    except ParseError as error:
        return [settle(Result.fail(str(error)))]

    finals: list[Result] = []
    for index, stage in enumerate(chain.stages):
        failed = False
        for result in _run_stage(stage):
            final = settle(result)
            finals.append(final)
            if final.should_exit:
                return finals
            failed = failed or not final.ok
        if failed and index < len(chain.stages) - 1:
            finals.append(settle(Result.fail("I stopped there, so the commands after 'and then' didn't run.")))
            break
    return finals


def answer(ask: Ask, text: str) -> Result | None:
    """Act on someone's reply to a question. None means 'I didn't understand'."""
    return ask.reply(text)


def suggest_command(word: str) -> str | None:
    names = set(registry.all_names()) | {phrase for phrase in ALIASES if " " not in phrase}
    match = difflib.get_close_matches(word, sorted(names), n=1, cutoff=0.7)
    return match[0] if match else None


# --- internals ------------------------------------------------------------


def _run_stage(stage: list[Intent]) -> list[Result]:
    if len(stage) == 1:
        return [_execute(stage[0])]
    with ThreadPoolExecutor(max_workers=len(stage)) as pool:
        return list(pool.map(_execute, stage))


def _execute(intent: Intent) -> Result:
    handler = registry.find(intent.verb)
    if handler is None:
        return Result.fail(_unknown(intent))
    try:
        return handler(intent)
    except Exception as error:  # a bug in one command shouldn't end the shell
        return Result.fail(f"Something went wrong inside '{intent.verb}': {error}")


def _unknown(intent: Intent) -> str:
    said = clean_answer(intent.raw)
    if said and (said in ANSWER_WORDS or said.split()[0] in CLEAR_ANSWERS):
        return f"I'm not asking anything right now, so '{intent.raw}' doesn't mean anything yet."
    message = f"I don't know '{intent.verb}' yet."
    guess = suggest_command(intent.verb)
    if guess:
        message += f" Did you mean '{guess}'?"
    return message + " Type help to see what I can do."
