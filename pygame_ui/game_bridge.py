"""The bridge between the console game and the window: a fake stdout, a fake stdin, a thread.

The game runs main.py unchanged on a background thread (the GAME THREAD). Whatever it prints
lands in the window's ``out_queue``; whatever the player answers goes back through ``in_queue``.
Next to the text, a few markers go through ``out_queue`` too, so they land in text order:
PAGE_BREAK, SpeakerChange, ShowMap and Cue.
"""

from __future__ import annotations

import os
import queue
import sys
import threading
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


# set AMAZE_PYGAME_DEBUG=1 to print every fake-stdout write to the real terminal
_DEBUG = os.environ.get("AMAZE_PYGAME_DEBUG") == "1"
_debug_start = time.monotonic()


def _debug_log(message: str) -> None:
    if _DEBUG:
        print(f"[{time.monotonic() - _debug_start:7.3f}s] {message}", file=sys.stderr, flush=True)


class StreamToQueue:
    """Fake sys.stdout - catches what the game prints and queues it for the window.

    It is also the one place that knows whether text is being typed out letter by letter
    (narrate) or handed over as a whole line (say, a menu, a prompt). The moment a typed line's
    newline arrives, write() holds the GAME THREAD itself until the line has been read. Holding
    only the drawing would not do: the game would carry on typing the next lines in the
    background, and they would already be there in full instead of being typed in.

    Every typed line is one pause point. Where a sentence "really" ends is the room's business:
    a room that writes its story as short parts (see rooms/corridor_blue.py) stops in the right
    places, because each part is a line.
    """

    def __init__(self, out_queue: queue.Queue, window: TerminalWindow) -> None:
        """Pass the game's text on to ``out_queue``, for ``window``."""
        self._queue = out_queue
        self._window = window
        self._typing_current_line = False
        self._story_told = False  # a typed line has finished since the player last went on
        # a character (not the narrator) has talked in that story, or the game asked to keep it
        # up (ui.keep_up): it waits for a press once it is told
        self.someone_spoke = False

    def write(self, text: str) -> None:
        """Pass ``text`` on to the window, holding the game where a typed line ends."""
        if not text:
            return
        self._window.wait_while_paused()  # the pause menu is open: the game stands still
        _debug_log(f"stdout.write() len={len(text)} text={text!r}")
        if text == "\n":
            was_typed = self._typing_current_line
            self._typing_current_line = False
            self._queue.put(text)
            if was_typed:
                self._window.wait_for_line_advance()
                self._story_told = True
            return
        if len(text) > 1 and text.strip():
            self.story_over()  # a menu, a question or the next room is about to be shown
        # narrate() writes one character at a time; say() hands over a whole line at once
        self._typing_current_line = len(text) == 1
        if self._typing_current_line:
            self._window.narrating = True  # the "SPACE to skip" tag shows while this goes on
        self._queue.put(text)

    def story_over(self) -> None:
        """Keep the story that was just told up until the player presses to go on.

        Called on the GAME THREAD just before something else takes the box: other text, or a
        fresh page (ui.new_page). Only when a character - a boss, the backpack - had something
        to say in it: plain narration moves on by itself, so the player is not pressing a key
        after every room.
        """
        if self._story_told and self.someone_spoke:
            self._window.wait_for_story_press()
        self._story_told = False
        self.someone_spoke = False

    def flush(self) -> None:
        """Nothing to flush: queue.put() delivers at once."""

    def isatty(self) -> bool:
        """Say yes, or narrate() prints its text all at once instead of typing it out."""
        return True


class QueueToStream:
    """Fake sys.stdin - the game blocks here until the player answers."""

    def __init__(self, in_queue: queue.Queue, on_wait_start, on_wait_end) -> None:
        """Read answers from ``in_queue``, calling the two hooks round every wait."""
        self._queue = in_queue
        self._on_wait_start = on_wait_start
        self._on_wait_end = on_wait_end

    def read_answer(self, prompt: str) -> str:
        """Show ``prompt`` and wait for the player's answer.

        Never the built-in input(): ui.py's own timed questions watch the real keyboard, and
        the player is typing in the window, not there.
        """
        sys.stdout.write(prompt)
        self._on_wait_start()
        try:
            line = self._queue.get()
        finally:
            self._on_wait_end()
        if line is EOF:
            raise EOFError
        if line is TIMED_OUT:
            raise ui.TimedOut  # the same thing ui.py does in a real terminal
        if line is QUIT_NOW:
            raise ui.QuitRequested  # what a confirmed "quit" does - game.py ends the run
        return line

    def readline(self) -> str:
        """Read an answer for a stray input(); nothing in the game calls this."""
        try:
            return f"{self.read_answer('')}\n"
        except (EOFError, ui.TimedOut, ui.QuitRequested):
            return ""  # empty string = EOF, same as a real terminal

    def isatty(self) -> bool:
        """Say yes - ui.py checks stdin as well as stdout before typing text out."""
        return True

    def fileno(self) -> int:
        """There is no real file behind this, so fail like a fake stream would."""
        raise OSError("this is not a real terminal - no file descriptor")


def make_dialogue_sleep(window: TerminalWindow):
    """Return a time.sleep() for the game that the window can cut short: it types the story out.

    It waits in short slices, so Space (``window.skipping``) can end every delay until the next
    question, and the pause menu can stop the clock for as long as it is open.
    """

    def _sleep(seconds: float) -> None:
        if window.quitting or window.skipping:
            return  # leaving, or Space was pressed: no waiting
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if window.skip_event.is_set() or window.skipping:
                return
            end += window.wait_while_paused()  # the pause menu is open: stop this clock too
            time.sleep(0.005)  # check often so a keypress feels instant

    return _sleep


def start_game(window: TerminalWindow) -> None:
    """Wire the fake stdout and stdin in, then start the real game on its own thread."""
    screen = StreamToQueue(window.out_queue, window)
    sys.stdout = screen
    keyboard = QueueToStream(window.in_queue, window.wait_start, window.wait_end)
    sys.stdin = keyboard

    ui.use_io(write=print, read=keyboard.read_answer, sleep=make_dialogue_sleep(window))
    ui.set_pause_menu(True)  # Escape opens the pause menu, so the game menu drops "Options"
    ui.set_cue_handler(lambda name: window.out_queue.put(Cue(name)))
    ui.set_page_handler(lambda: (screen.story_over(), window.out_queue.put(PAGE_BREAK)))
    ui.set_keep_up_handler(lambda: setattr(screen, "someone_spoke", True))
    ui.set_map_handler(lambda: (screen.story_over(), window.out_queue.put(ShowMap())))
    ui.set_speaker_handler(lambda who, mood: _speaker_changed(window, screen, who, mood))
    ui.set_flowing(True)  # the window holds each line itself: no second wait before the next
    # the box wraps every line to its own width in pixels. Cutting lines at ui.py's 80
    # characters first would break each one twice, stranding a word or two on a row of its own
    ui.WIDTH = 10_000
    # ui.py's typing has its own skip check that peeks at the real console's keyboard, not the
    # window's. Stray input there would write the rest of a line in one go, and StreamToQueue
    # would then take it for an instant line that needs no pause
    ui._pressed_a_key = lambda: False

    def read_line_with_clock(prompt: str, timeout: float | None) -> str:
        # every answer passes through ui._read_line (ui.choose() does not go through ask()):
        # Space-skipping stops here, and a timed question starts its clock
        window.skip_event.clear()
        window.deadline = None if timeout is None else time.monotonic() + timeout
        try:
            return keyboard.read_answer(prompt)
        finally:
            window.deadline = None

    ui._read_line = read_line_with_clock

    threading.Thread(target=_run_game, args=(window,), daemon=True).start()


def _speaker_changed(window: TerminalWindow, screen: StreamToQueue, who: str | None, mood: str):
    if who is not None:
        screen.someone_spoke = True  # what they say will wait for a press once it is told
    window.out_queue.put(SpeakerChange(who, mood))


def _run_game(window: TerminalWindow) -> None:
    try:
        run_console_game()
    except (EOFError, ui.PauseRequested, ui.QuitRequested):
        # "pause" (or Escape) or a confirmed quit during the very first room's arrival, before
        # game.py's own loop is there to catch it - a clean end
        pass
    except Exception:
        traceback.print_exc()  # real terminal, not the window - bugs stay visible
    finally:
        window.out_queue.put("\n[Game ended - press any key to close the window]\n")
        window.game_over = True
