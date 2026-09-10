"""Shared test helpers.

The game talks to the player through ``ui``. These fixtures replace that with
a script of answers and a list of everything printed, so a test can play the
game with nobody at the keyboard.

Because the game is menu-driven, a script is a list of numbers: the same keys
a player would press.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import rooms  # noqa: F401  (importing rooms registers them)
import ui


class FakeConsole:
    """Records output and replays a fixed list of player inputs."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self._answers: list[str] = []

    def script(self, *answers: str) -> None:
        """Queue what the player types next."""
        self._answers.extend(answers)

    def write(self, text: str) -> None:
        self.lines.append(text)

    def read(self, prompt: str = "") -> str:
        if not self._answers:
            # Same as a real terminal with nothing left on stdin. The game
            # treats this as the player walking away.
            raise EOFError
        return self._answers.pop(0)

    @property
    def output(self) -> str:
        """Everything printed so far, as one lowercase string to search."""
        return "\n".join(self.lines).casefold()


@pytest.fixture
def console() -> Iterator[FakeConsole]:
    """Give the test a console it controls, and restore the real one after."""
    fake = FakeConsole()
    ui.use_io(fake.write, fake.read)
    yield fake
    ui.use_io(print, input)
