"""Shared test helpers.

The game talks to the player through ``amazing_delft.ui``.  These fixtures
replace that with a script of answers and a list of everything printed, so a
test can play the game with nobody at the keyboard.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from amazing_delft import rooms, ui  # noqa: F401  (importing rooms registers them)


class FakeConsole:
    """Records output and replays a fixed list of player inputs."""

    def __init__(self, answers: list[str]) -> None:
        self.lines: list[str] = []
        self._answers = list(answers)

    def write(self, text: str) -> None:
        self.lines.append(text)

    def read(self, prompt: str) -> str:
        if not self._answers:
            return "quit"
        return self._answers.pop(0)

    @property
    def output(self) -> str:
        """Everything printed so far, as one lowercase string to search."""
        return "\n".join(self.lines).casefold()


@pytest.fixture
def console() -> Iterator[FakeConsole]:
    """Give the test a console it controls, and restore the real one after."""

    def make(*answers: str) -> FakeConsole:
        fake = FakeConsole(list(answers))
        ui.use_io(fake.write, fake.read)
        return fake

    fake = make()
    yield fake
    ui.use_io(print, input)
