"""Shared test helpers.

The game talks to the player through ``ui``. These fixtures replace that with
a script of answers and a list of everything printed, so a test can play the
game with nobody at the keyboard.

Because the game is menu-driven, a script is a list of numbers: the same keys
a player would press.
"""

from __future__ import annotations

import time
from collections.abc import Iterator

import pytest

import narrator
import persistence
import rooms  # noqa: F401  (importing rooms registers them)
import ui


@pytest.fixture(autouse=True)
def own_database(tmp_path, monkeypatch) -> None:
    """Give every test an empty database of its own, never the real game.db.

    Finishing the game shows the scoreboard, which reads the saves - so any
    test that walks out of the building would otherwise read, and could
    write, the saves of whoever last played on this machine.
    """
    monkeypatch.setattr(persistence, "DATABASE_NAME", str(tmp_path / "test.db"))
    persistence.create_tables()


@pytest.fixture(autouse=True)
def quiet_backpack() -> Iterator[None]:
    """Keep the Evil Backpack quiet for every test but its own.

    It is a character, and characters get rewritten. No test should fail
    because somebody improved one of its lines - the ones that are about the
    backpack turn it back on themselves (#103).
    """
    narrator.silence()
    yield
    narrator.speak_up()


class FakeConsole:
    """Records output and replays a fixed list of player inputs."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self._answers: list[str] = []
        #: Every pause the game asked for, in seconds, instead of really waiting.
        self.pauses: list[float] = []
        #: The clock the game reads, in seconds. A test times a question by
        #: moving this forward itself - see ``take_seconds``.
        self.time = 0.0
        #: How long the player "takes" over each answer, in order. Anything
        #: not listed is answered instantly.
        self._delays: list[float] = []

    def take_seconds(self, *delays: float) -> None:
        """Make the player take this long over the next answers, in order."""
        self._delays.extend(delays)

    def clock(self) -> float:
        """The time, as the game sees it."""
        return self.time

    def script(self, *answers: str) -> None:
        """Queue what the player types next."""
        self._answers.extend(answers)

    def write(self, text: str) -> None:
        self.lines.append(text)

    def read(self, prompt: str = "") -> str:
        if self._delays:
            # Answering takes the player however long the test says it does.
            self.time += self._delays.pop(0)
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
    ui.use_io(fake.write, fake.read, sleep=fake.pauses.append, clock=fake.clock)
    yield fake
    ui.use_io(print, input, time.sleep, time.monotonic)
