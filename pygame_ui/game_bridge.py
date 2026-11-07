"""The bridge between the game and the window: what the game prints, and what the player answers.

The game (main.py's async ``main()``) runs as an asyncio task next to the window's own loop, on
the same thread: whenever it waits for the player or for a line to be read, the window draws. What
it prints lands in the window's ``out_queue``; whatever the player answers comes back through
``in_queue``. Next to the text, a few markers go through ``out_queue`` too, so they land in text
order: PAGE_BREAK, SpeakerChange, ShowMap and Cue.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import traceback
from typing import TYPE_CHECKING

import ui
from main import main as run_console_game

if TYPE_CHECKING:
    from pygame_ui.window import TerminalWindow

# put in in_queue by the window, never typed: "stop waiting" (read as the end of the input),
# "the clock ran out", and "the player has confirmed a quit in the pause menu"
EOF = object()
TIMED_OUT = object()
QUIT_NOW = object()

# put in out_queue once a line of story text has had its time on screen: the box starts a fresh
# page. It goes through the queue so it lands after that line, in order
PAGE_BREAK = object()


class SpeakerChange:
    """Put in out_queue when someone starts speaking (who) or stops (who is None)."""

    def __init__(self, who: str | None, mood: str) -> None:
        """Remember who is speaking (None: nobody) and in what mood."""
        self.who = who
        self.mood = mood


class ShowMap:
    """Put in out_queue where the game asks for the drawn floor map (see ui.show_map)."""


class Cue:
    """Put in out_queue where a sound cue is to be played (see ui.cue)."""

    def __init__(self, name: str) -> None:
        """Remember which cue to play."""
        self.name = name


# set AMAZE_PYGAME_DEBUG=1 to print everything the game writes to the real terminal
_DEBUG = os.environ.get("AMAZE_PYGAME_DEBUG") == "1"
_debug_start = time.monotonic()


def _debug_log(message: str) -> None:
    if _DEBUG:
        print(f"[{time.monotonic() - _debug_start:7.3f}s] {message}", file=sys.stderr, flush=True)


class GameOutput:
    """Catches what the game prints and queues it for the window.

    It is also the one place that knows whether text is being typed out letter by letter
    (narrate, through ui.set_typist) or handed over as a whole line (say, a menu, a prompt). The
    moment a typed line's newline arrives, write() holds the game until the line has been read.
    Holding only the drawing would not do: the game would carry on typing the next lines, and
    they would already be there in full instead of being typed in.

    Every typed line is one pause point. Where a sentence "really" ends is the room's business:
    a room that writes its story as short parts (see rooms/corridor_blue.py) stops in the right
    places, because each part is a line.
    """

    def __init__(self, window: TerminalWindow) -> None:
        """Pass the game's text on to ``window``'s out_queue."""
        self._queue = window.out_queue
        self._window = window
        self._typing_current_line = False
        self._story_told = False  # a typed line has finished since the player last went on
        # a character (not the narrator) has talked in that story, or the game asked to keep it
        # up (ui.keep_up): it waits for a press once it is told
        self.someone_spoke = False

    async def write(self, text: str) -> None:
        """Pass ``text`` on to the window, holding the game where a typed line ends."""
        if not text:
            return
        await self._window.wait_while_paused()  # the pause menu is open: the game stands still
        _debug_log(f"write() len={len(text)} text={text!r}")
        if text == "\n":
            was_typed = self._typing_current_line
            self._typing_current_line = False
            self._queue.put_nowait(text)
            if was_typed:
                await self._window.wait_for_line_advance()
                self._story_told = True
            return
        if len(text) > 1 and text.strip():
            await self.story_over()  # a menu, a question or the next room is about to be shown
        # narrate() types one character at a time; say() hands over a whole line at once
        self._typing_current_line = len(text) == 1
        if self._typing_current_line:
            self._window.narrating = True  # the "SPACE to skip" tag shows while this goes on
        self._queue.put_nowait(text)

    async def write_line(self, line: str) -> None:
        """Write a whole line, as ``print`` would."""
        await self.write(line)
        await self.write("\n")

    async def story_over(self) -> None:
        """Keep the story that was just told up until the player presses to go on.

        Called just before something else takes the box: other text, or a fresh page
        (ui.new_page). Only when a character - a boss, the backpack - had something to say in
        it: plain narration moves on by itself, so the player is not pressing a key after
        every room.
        """
        if self._story_told and self.someone_spoke:
            await self._window.wait_for_story_press()
        self._story_told = False
        self.someone_spoke = False


class GameInput:
    """Hands the game the player's answers; the game waits here until there is one."""

    def __init__(self, window: TerminalWindow, screen: GameOutput) -> None:
        """Read answers from ``window``'s in_queue, showing each prompt on ``screen``."""
        self._window = window
        self._screen = screen

    async def read_answer(self, prompt: str) -> str:
        """Show ``prompt`` and wait for the player's answer."""
        await self._screen.write(prompt)
        self._window.wait_start()
        try:
            line = await self._window.in_queue.get()
        finally:
            self._window.wait_end()
        if line is EOF:
            raise EOFError
        if line is TIMED_OUT:
            raise ui.TimedOut  # the same thing ui.py does in a real terminal
        if line is QUIT_NOW:
            raise ui.QuitRequested  # what a confirmed "quit" does - game.py ends the run
        return line


def make_dialogue_sleep(window: TerminalWindow):
    """Return the game's sleep, which the window can cut short: it types the story out.

    It waits in short slices, so Space (``window.skipping``) can end every delay until the next
    question, and the pause menu can stop the clock for as long as it is open.
    """

    async def _sleep(seconds: float) -> None:
        if window.quitting or window.skipping:
            return  # leaving, or Space was pressed: no waiting
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if window.skip_event.is_set() or window.skipping:
                return
            end += await window.wait_while_paused()  # the pause menu is open: stop this clock
            await asyncio.sleep(0.005)  # check often so a keypress feels instant

    return _sleep


def start_game(window: TerminalWindow) -> asyncio.Task:
    """Wire the game's input and output to ``window``, and start the game as a task."""
    screen = GameOutput(window)
    keyboard = GameInput(window, screen)

    ui.use_io(write=screen.write_line, read=keyboard.read_answer, sleep=make_dialogue_sleep(window))
    ui.set_typist(screen.write)
    ui.set_pause_menu(True)  # Escape opens the pause menu, so the game menu drops "Options"
    ui.set_cue_handler(lambda name: window.out_queue.put_nowait(Cue(name)))
    ui.set_page_handler(lambda: _then_put(screen, window, PAGE_BREAK))
    ui.set_keep_up_handler(lambda: setattr(screen, "someone_spoke", True))
    ui.set_map_handler(lambda: _then_put(screen, window, ShowMap()))
    ui.set_speaker_handler(lambda who, mood: _speaker_changed(window, screen, who, mood))
    ui.set_flowing(True)  # the window holds each line itself: no second wait before the next
    # the box wraps every line to its own width in pixels. Cutting lines at ui.py's 80
    # characters first would break each one twice, stranding a word or two on a row of its own
    ui.WIDTH = 10_000

    async def read_line_with_clock(prompt: str, timeout: float | None) -> str:
        # every answer passes through ui._read_line (ui.choose() does not go through ask()):
        # Space-skipping stops here, and a timed question starts its clock
        window.skip_event.clear()
        window.deadline = None if timeout is None else time.monotonic() + timeout
        try:
            return await keyboard.read_answer(prompt)
        finally:
            window.deadline = None

    ui._read_line = read_line_with_clock

    return asyncio.create_task(_run_game(window))


async def _then_put(screen: GameOutput, window: TerminalWindow, marker: object) -> None:
    """Let the story just told be read, then put ``marker`` in the queue after it."""
    await screen.story_over()
    window.out_queue.put_nowait(marker)


def _speaker_changed(window: TerminalWindow, screen: GameOutput, who: str | None, mood: str):
    if who is not None:
        screen.someone_spoke = True  # what they say will wait for a press once it is told
    window.out_queue.put_nowait(SpeakerChange(who, mood))


async def _run_game(window: TerminalWindow) -> None:
    try:
        await run_console_game()
    except (EOFError, ui.PauseRequested, ui.QuitRequested):
        # "pause" (or Escape) or a confirmed quit during the very first room's arrival, before
        # game.py's own loop is there to catch it - a clean end
        pass
    except Exception:
        traceback.print_exc()  # the real terminal, not the window - bugs stay visible
    finally:
        window.out_queue.put_nowait("\n[Game ended - press any key to close the window]\n")
        window.game_over = True
