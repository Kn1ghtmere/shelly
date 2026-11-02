from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

YES_WORDS = frozenset({
    "y", "yes", "yeah", "yep", "yup", "ya", "yea", "sure", "ok", "okay", "k",
    "please", "alright", "fine", "go ahead", "do it", "go on", "create it",
    "create", "continue", "proceed", "confirm", "absolutely", "definitely",
    "of course", "sounds good", "yes please",
})
NO_WORDS = frozenset({
    "n", "no", "nope", "nah", "cancel", "stop", "dont", "abort", "never mind",
    "nevermind", "no thanks", "negative", "skip",
})


def _clean(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", "", text.lower()).split())


@dataclass
class Choice:
    """One possible answer to a question, and what happens if it's picked."""

    label: str
    words: frozenset[str]
    run: Callable[[], "Result"]


@dataclass
class Ask:
    """A question for the person. Front ends show it, read an answer, and
    call `match` to find out which choice they meant."""

    prompt: str
    choices: list[Choice]

    @property
    def hint(self) -> str:
        return " / ".join(choice.label for choice in self.choices)

    def match(self, text: str) -> Choice | None:
        answer = _clean(text)
        if not answer:
            return None
        for choice in self.choices:
            if answer in choice.words:
                return choice
        first = answer.split()[0]
        for choice in self.choices:
            if first in choice.words:
                return choice
        return None

    @classmethod
    def yes_no(
        cls,
        prompt: str,
        on_yes: Callable[[], "Result"],
        on_no: Callable[[], "Result"] | None = None,
    ) -> "Ask":
        on_no = on_no or (lambda: Result.success("Okay, I didn't do anything."))
        return cls(prompt, [Choice("yes", YES_WORDS, on_yes), Choice("no", NO_WORDS, on_no)])


@dataclass
class Result:
    ok: bool
    message: str = ""
    data: Any = None
    should_exit: bool = False
    ask: Ask | None = None

    @classmethod
    def success(cls, message: str = "", data: Any = None) -> "Result":
        return cls(True, message, data)

    @classmethod
    def fail(cls, message: str, data: Any = None) -> "Result":
        return cls(False, message, data)

    @classmethod
    def asking(cls, ask: Ask) -> "Result":
        return cls(True, "", ask=ask)
