"""TerminalWindow: the window the game is played in, and its main loop.

Each frame the loop reads the keys (handle_events), files whatever the game has printed into
screen lines (pump_output), presses Enter for a timed question that has run out (check_clock),
moves the music on, and draws. The game runs as an asyncio task beside the loop (see
game_bridge); it only ever waits in the ``wait_*`` methods, and the loop draws meanwhile.
"""

from __future__ import annotations

import asyncio
import math
import os
import re
import sys
import time

import pygame

import browser
import ui
from music import Music
from pygame_ui import assets, game_bridge
from pygame_ui.dialogue_box import (
    OPTION,
    OPTION_PRESSED,
    OPTION_SELECTED,
    SPEAKER_LABEL,
    DialogueBox,
)
from pygame_ui.game_bridge import EOF, PAGE_BREAK, QUIT_NOW, TIMED_OUT, Cue, ShowMap, SpeakerChange
from pygame_ui.map_view import FloorMap
from pygame_ui.pause_menu import PauseMenu, blurred
from pygame_ui.room_fade import RoomFade
from pygame_ui.sounds import MenuTick, TypingBlips, load_cue_sounds
from pygame_ui.speaker import Speaker
from pygame_ui.text import TextRenderer

FPS = 60

# the background music: the intro loop on the first screen (while the name is typed), the
# exploring loop once the game has started, and the boss loop near a boss
MUSIC_FILES = {"intro": "music_intro.ogg", "explore": "music_explore.ogg", "boss": "music_boss.ogg"}

# every size on screen is measured against this screen height and scaled to the real one, so the
# window has the same proportions on every resolution. 900 is what Pygame reports on the machine
# the layout was tuned on (a 2880x1800 panel at 200% Windows display scaling)
REFERENCE_HEIGHT = 900
REFERENCE_FONT_SIZE = 15
REFERENCE_MARGIN = 10

INTRO_ROW_SPACING = 1.7  # the first screen's rows are this many text heights apart
INTRO_TEXT_FACTOR = 1.35  # the first screen's text, at most this many times the normal size
INTRO_MAX_WIDTH = 0.94  # the first screen's text may fill this much of the window width
NAME_NOTICE_SECONDS = 2.5  # how long "Please enter a valid name." stays up
PICK_DELAY_SECONDS = 0.2  # a confirmed choice shows its click this long, then answers
AUTO_ADVANCE_SECONDS = 1.0  # how long a finished line of story stays before the next one starts
POLL_SECONDS = 0.01  # how often a waiting game looks again whether it may go on
QUIT_GRACE_PERIOD = 5.0  # after quitting, wait at most this long for the game to save

DIVIDER = "-" * 64  # put after every answered question, to separate it from what comes next

_UP_DOWN = (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s)


class TerminalWindow:
    """A fullscreen window: shows the game's fake-stdout output, types into its fake-stdin."""

    def __init__(self) -> None:
        """Open the window, load everything it draws and plays, and set up the shared state."""
        if sys.platform == "win32":
            # with Windows display scaling (125%, 150%, ...) pygame would otherwise be told a
            # shrunken screen size and only fill part of it
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        pygame.init()
        if browser.IN_BROWSER:
            # the canvas, as big as the browser window in its real pixels
            self.screen = pygame.display.set_mode(browser.screen_size())
        elif os.environ.get("AMAZE_WINDOWED") == "1":
            # a normal 1280x720 window instead of fullscreen - handy next to an editor, or demos
            self.screen = pygame.display.set_mode((1280, 720))
        else:
            # (0, 0) asks for the screen's own size
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.width, self.height = self.screen.get_size()
        pygame.display.set_caption("After Hours")

        # how much bigger or smaller this screen is than the reference one
        self.scale = self.height / REFERENCE_HEIGHT
        font_size = max(8, round(REFERENCE_FONT_SIZE * self.scale))
        self.row_gap = max(1, round(2 * self.scale))  # space between two rows of the box
        self.margin = max(4, round(REFERENCE_MARGIN * self.scale))

        # the parts the window is made of - each one is a module of its own
        self.text = TextRenderer(font_size)
        self.box = DialogueBox(self.text)
        self.speaker = Speaker()
        self.floor_map = FloorMap()
        self.fade = RoomFade()
        self.pause_menu = PauseMenu(self)
        self.music = Music({name: assets.path(file) for name, file in MUSIC_FILES.items()})
        self.blips = TypingBlips()
        self.tick = MenuTick()
        self.cue_sounds = load_cue_sounds()
        self.boss_music = False  # True from getting closer to a boss until its encounter is over

        # what is on screen
        self.lines: list[tuple[str, str]] = []  # (text, colour) for every finished line
        self.current_line = ""  # the line being built right now, character by character
        self.typed = ""  # what the player has typed for their current answer
        self.room_header: str | None = None  # "== Room Name ==", pinned above the box
        self.room_image: pygame.Surface | None = None  # its background picture, if it has one
        self.hearts_line: str | None = None  # the last "Hearts: ..." line, for the countdown
        self.box_start = 0  # where the box's current page starts in self.lines
        self.page_speaker: str | None = None  # the name last put over the story on this page
        self._story_end = 0  # where the story's last typed line ends: a question starts there
        self._typed_line = False  # whether the line being built is being typed out
        self._box_rect: tuple[int, int, int, int] | None = None  # where the box was drawn

        # the question being asked
        self.waiting_for_input = False  # the game is waiting on an answer (not narrating)
        self.deadline: float | None = None  # when a timed question runs out (time.monotonic())
        self._prompt_pending = False  # a new question has just started - see pump_output
        self._prompt_start: int | None = None  # where it starts in self.lines
        self._last_blank_index: int | None = None  # every question starts after a blank line
        self.menu_selected: int | None = None  # the highlighted choice (see menu_options)
        self._pending_pick: float | None = None  # when a confirmed choice is to be answered
        self._name_notice_until = 0.0  # until when "Please enter a valid name." shows

        # talking to the game (see game_bridge)
        self.out_queue: asyncio.Queue = asyncio.Queue()  # game -> window: what it printed
        self.in_queue: asyncio.Queue = asyncio.Queue()  # window -> game: the answers
        self.skip_event = asyncio.Event()  # set by Space: ends the typing delay at once
        self.advance_event = asyncio.Event()  # set by a press: a held line carries on
        self.pause_gate = asyncio.Event()  # cleared while the game is to stand still
        self.pause_gate.set()
        self.skipping = False  # Space was pressed: no delays at all until the next question
        self.narrating = False  # story text is being told (the "SPACE to skip" tag shows)
        self.waiting_to_advance = False  # the game is held on a line it just finished
        self.waiting_for_press = False  # the story is over and waits for Space or Enter

        # pausing and leaving
        self.paused = False
        self._paused_at = 0.0
        self.game_over = False
        self.quitting = False  # Escape was pressed: the game is on its way to its save
        self.exit_silently = False  # the window closes once the game has saved, no goodbye
        self._quit_requested_at = 0.0

    # --- called by the game: holding it while the player reads --------------------------

    def wait_start(self) -> None:
        """The game has started waiting for an answer."""
        self.skipping = False  # the story stops at a question, and so does skipping it
        self.narrating = False
        self.waiting_for_input = True
        self._prompt_pending = True

    def wait_end(self) -> None:
        """The game has its answer."""
        self.waiting_for_input = False

    async def wait_for_line_advance(self) -> None:
        """Hold the game for a second right where a typed line just finished.

        So the player can read it, then it carries on by itself - or at once if Space has been
        pressed. The pause menu stops the second from running down while it is open. The line
        stays in the box: the next one is typed under it, so the story stacks up like a
        conversation until a question, a pickup or a new room starts a fresh page.
        """
        if self.quitting:
            return  # leaving: don't hold anything up on the way to the save
        if not self.skipping:
            self.advance_event.clear()
            self.waiting_to_advance = True
            deadline = time.monotonic() + AUTO_ADVANCE_SECONDS
            while not self.advance_event.is_set() and not self.quitting:
                await asyncio.sleep(POLL_SECONDS)
                if self.paused:
                    deadline = time.monotonic() + AUTO_ADVANCE_SECONDS  # held while paused
                elif time.monotonic() >= deadline:
                    break
        self.waiting_to_advance = False

    async def wait_for_story_press(self) -> None:
        """Hold the game, with the whole story still in the box, until Space or Enter.

        Not on the first screen, and not once Space has skipped the story: the player has said
        they do not want to wait for it.
        """
        if self.quitting or self.skipping or self.room_header is None:
            return
        self.advance_event.clear()
        self.waiting_for_press = True
        while not self.advance_event.is_set() and not self.quitting:
            await asyncio.sleep(POLL_SECONDS)
        self.waiting_for_press = False

    async def wait_while_paused(self) -> float:
        """Hold the game while the pause menu or a room change is on; return how long it waited."""
        if self.pause_gate.is_set():
            return 0.0
        started = time.monotonic()
        await self.pause_gate.wait()
        return time.monotonic() - started

    # --- turning what the game printed into lines on screen ------------------------------

    def pump_output(self) -> None:
        """Read what the game has printed since the last frame, and file it into self.lines.

        Which lines need a press was already settled by the game (see game_bridge.GameOutput);
        this only turns characters into (text, colour) rows.
        """
        try:
            while True:
                chunk = self.out_queue.get_nowait()
                if chunk is PAGE_BREAK:
                    self._new_page()  # the line before it is filed: a fresh page
                elif isinstance(chunk, SpeakerChange):
                    self.speaker.change(chunk)
                elif isinstance(chunk, ShowMap):
                    if self.floor_map.art is not None and not self.quitting:
                        self.open_pause_menu(view="map")  # stops the game, like pressing M
                elif isinstance(chunk, Cue):
                    self._play_cue(chunk.name)
                else:
                    for character in chunk:
                        self._add_character(character, typed=len(chunk) == 1)
        except asyncio.QueueEmpty:
            pass

        if self._prompt_pending:
            # a new question just started - remember where it began, to collapse it later
            self._prompt_start = self._last_blank_index if self._last_blank_index is not None else 0
            self._prompt_pending = False
            if self.box_start < self._story_end <= len(self.lines):
                self._new_page(self._story_end)  # the question gets the box to itself
            # an untimed menu starts on its first choice, so Enter alone answers it. A timed
            # boss question starts with nothing chosen, so a stray Enter can't answer it
            self.menu_selected = 0 if self.menu_options() and self.deadline is None else None

    def _add_character(self, character: str, typed: bool) -> None:
        """Add one printed character; ``typed`` if it came one letter at a time (narrate)."""
        if character != "\n":
            if not self.current_line:
                self._typed_line = typed
                if typed:
                    self._name_the_speaker()  # a line of the story is starting
            self.current_line += character
            if typed:
                self.blips.play(character, self.speaker.who, self.speaker.mood, self.paused)
                self.music.typing()
            return
        if _is_room_header(self.current_line):
            self._enter_room(self.current_line)
        else:
            self.lines.append((self.current_line, "white"))
            if self.current_line.startswith("Hearts:"):
                self.hearts_line = self.current_line
            if self.current_line == "":
                self._last_blank_index = len(self.lines) - 1
            if self._typed_line:
                self._story_end = len(self.lines)
        self.current_line = ""
        self.skip_event.clear()  # each new line starts fresh - needs its own press to skip

    def _enter_room(self, header: str) -> None:
        """A new room: a clean screen with its header pinned on top, faded in from black."""
        self.start_fade()
        self.speaker.clear()  # whoever was talking stays behind
        self.room_header = header
        self.room_image = assets.load_room_image(header, self.width, self.height)
        self.lines = []
        self._prompt_start = None
        self._last_blank_index = None
        self._story_end = 0
        self._new_page()

    def _new_page(self, start: int | None = None) -> None:
        """Start the box's page at line ``start`` (the end of the story so far, by default)."""
        self.box_start = len(self.lines) if start is None else start
        self.page_speaker = None

    def _name_the_speaker(self) -> None:
        """Put the name of whoever is talking above their lines, if it is someone new.

        Only in a room: the first screen, before any room, is not a conversation.
        """
        if self.room_header is None:
            return
        name = self.speaker.name()
        if name != self.page_speaker:
            self.lines.append((name, SPEAKER_LABEL))
            self.page_speaker = name

    def _play_cue(self, name: str) -> None:
        """Handle a cue: switch the boss music on or off, or play its sound and dip the music."""
        if name in ("boss_music_on", "boss_music_off"):
            self.boss_music = name == "boss_music_on"
            return
        sound = self.cue_sounds.get(name)
        if sound is not None:
            sound.play()
            self.music.duck(max(0.8, sound.get_length()))

    # --- keys -----------------------------------------------------------------------------

    def handle_events(self) -> None:
        """Turn key presses into skipping the story, going on, picking a choice or typing."""
        # file what the game has printed first: a key pressed in the very frame a question
        # starts would otherwise be taken for an answer to a question with no choices yet
        self.pump_output()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            elif event.type == pygame.KEYDOWN:
                self._key(event)

    def _key(self, event: pygame.event.Event) -> None:
        if self.paused:
            self.pause_menu.key(event)
        elif self.game_over:
            self.quit()
        elif event.key == pygame.K_ESCAPE:
            if ui.status() is not None and not self.quitting:
                self.open_pause_menu()  # a game is being played: stop it
            else:
                self.quit()  # nothing to pause yet, such as while typing the name
        elif event.key == pygame.K_m and self._can_open_map():
            self.open_pause_menu(view="map")
        elif self.waiting_for_press:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.advance_event.set()  # read it: on to what comes next
        elif self.waiting_to_advance or not self.waiting_for_input:
            # the story is being told: Space skips all of it, and no other key does anything
            if event.key == pygame.K_SPACE:
                self._skip_narration()
        elif self.menu_options():
            self._menu_key(event)
        else:
            self._typing_key(event)

    def _menu_key(self, event: pygame.event.Event) -> None:
        """A key on a numbered menu: the arrows (or W and S) pick, Enter or a number answers."""
        if self._pending_pick is not None:
            return  # a choice is already lit up, waiting to be answered
        numbers = [number for number, _row in self.menu_options()]
        if event.unicode in numbers:
            self.menu_selected = numbers.index(event.unicode)
            self.typed = ""
            self._pending_pick = time.monotonic() + PICK_DELAY_SECONDS
        elif event.key in _UP_DOWN:
            self._move_menu_selection(down=event.key in (pygame.K_DOWN, pygame.K_s))
        elif event.key == pygame.K_RETURN and self.menu_selected is not None:
            self._pending_pick = time.monotonic() + PICK_DELAY_SECONDS

    def _typing_key(self, event: pygame.event.Event) -> None:
        """A key while the player types an answer of their own."""
        if event.key == pygame.K_RETURN:
            naming = self.room_header is None and ui.status() is None and not ui.asking_secret()
            if naming and not self.typed.strip():
                # the name prompt: an empty name is not sent, it is only pointed out
                self._name_notice_until = time.monotonic() + NAME_NOTICE_SECONDS
            else:
                self._submit(self.typed)
        elif event.key == pygame.K_BACKSPACE:
            self.typed = self.typed[:-1]
        elif event.unicode and event.unicode.isprintable():
            self.typed += event.unicode

    def _skip_narration(self) -> None:
        """Skip the rest of the story text: no typing, no pauses, until the next question."""
        self.skipping = True
        self.skip_event.set()
        self.advance_event.set()  # a line that is waiting for its second carries on now

    def menu_options(self) -> list[tuple[str, int]]:
        """The numbered choices of the question being asked: (its number, its index in lines).

        Found by reading the "  1) Look around" lines the game printed, so every menu and every
        multiple-choice boss question works without the rooms or the game knowing about it.
        """
        if self._prompt_start is None:
            return []
        options = []
        for index in range(self._prompt_start, len(self.lines)):
            match = re.match(r"(\d+)\) ", self.lines[index][0].strip())
            if match:
                options.append((match.group(1), index))
        return options

    def _move_menu_selection(self, down: bool) -> None:
        """Move the highlight to the next or previous choice, wrapping round."""
        options = self.menu_options()
        if not options:
            return
        if self.menu_selected is None:
            self.menu_selected = 0 if down else len(options) - 1
        else:
            self.menu_selected = (self.menu_selected + (1 if down else -1)) % len(options)
        self.typed = ""  # the arrows take over from half a typed number
        self.tick.play()

    def check_clock(self) -> None:
        """Answer a choice picked a moment ago, or press Enter when a timed question runs out."""
        if self.paused:
            return  # the clock is stopped while the pause menu is open
        if self._pending_pick is not None:
            # answer once the choice has been lit up for a moment, even if a timed question's
            # clock ran out meanwhile - it was pressed in time
            options = self.menu_options()
            if not self.waiting_for_input or not options or self.menu_selected is None:
                self._pending_pick = None
            elif time.monotonic() >= self._pending_pick:
                self._pending_pick = None
                self.typed = options[self.menu_selected % len(options)][0]
                self._submit(self.typed)
                return
            else:
                return
        deadline = self.deadline
        if self.waiting_for_input and deadline is not None and time.monotonic() >= deadline:
            self._submit(TIMED_OUT)

    def _seconds_left(self) -> int | None:
        """What the countdown under a timed question shows, or None if it is untimed."""
        if not self.waiting_for_input or self.deadline is None:
            return None
        return max(0, math.ceil(self.deadline - time.monotonic()))

    def _shown_typed(self) -> str:
        """What the player has typed, as shown on screen: a password is shown as stars."""
        return "*" * len(self.typed) if ui.asking_secret() else self.typed

    def _submit(self, answer: object) -> None:
        """Send an answer to the game, and collapse the question on screen to what was picked.

        ``answer`` is what the player typed, or TIMED_OUT when the clock did the pressing.
        """
        answer_line = self.current_line + self._shown_typed()
        if self._prompt_start is not None:
            label = _option_label(self.typed, self.lines[self._prompt_start :])
            if label is not None:
                answer_line = f"{self.current_line}{label}"  # "Look around", not "1"
            del self.lines[self._prompt_start :]
            self._prompt_start = None
            self._last_blank_index = None
        self.lines.append((answer_line, "gray"))
        self.lines.append((DIVIDER, "gray"))
        self.current_line = ""
        self.typed = ""
        # stop listening now, not when the game gets round to it - so a second Enter (or the
        # clock) in the next frame can't answer twice
        self.waiting_for_input = False
        self.deadline = None
        self.menu_selected = None
        self.in_queue.put_nowait(answer)
        self._new_page()  # the box starts fresh for whatever comes next

    # --- pausing, the map, room changes and leaving ---------------------------------------

    def open_pause_menu(self, view: str = "menu") -> None:
        """Stop the game behind the pause menu (or the map), over a blurred freeze-frame of it."""
        self._pending_pick = None  # a number pressed a moment ago is forgotten
        self.fade.stop()  # a room change in progress is dropped: the menu holds the game
        self._draw_scene()
        self.pause_menu.open(blurred(self.screen, self.scale), view)
        self._paused_at = time.monotonic()
        self.paused = True
        self.pause_gate.clear()  # the game stops at its next word or pause

    def close_pause_menu(self) -> None:
        """Let the game carry on, with every clock set back by the time it stood still."""
        if not self.paused:
            return
        self.settle_pause_clock()
        self.paused = False
        self.pause_menu.backdrop = None
        self.pause_gate.set()

    def settle_pause_clock(self) -> None:
        """Count the time the menu has been open so far as paused, and start counting afresh.

        Done when the menu closes - and before saving, so the saved time played leaves out the
        time spent sitting in the menu.
        """
        now = time.monotonic()
        waited = now - self._paused_at
        self._paused_at = now
        if self.deadline is not None:
            self.deadline += waited  # a timed question gets back what the menu took
        ui.hold_time(waited)  # and so do the time played and the boss timers

    def _can_open_map(self) -> bool:
        """True once the floor plan has been taken, unless a typed answer is being written."""
        status = ui.status()
        if self.floor_map.art is None or self.quitting or not status or not status.get("has_map"):
            return False
        typing = self.waiting_for_input and not self.waiting_to_advance and not self.menu_options()
        return not typing  # while typing, M is just a letter

    def start_fade(self) -> None:
        """Begin fading out of the room on screen, and hold the game while it goes dark."""
        if self.paused or self.quitting or self.fade.active:
            return
        self.fade.start(self.screen.copy(), first=self.room_header is None)
        self.pause_gate.clear()  # the game stops at its next word, until the new room is lit

    def _end_fade(self) -> None:
        """Stop any room change in progress and let the game carry on."""
        self.fade.stop()
        if not self.paused:
            self.pause_gate.set()

    def quit(self, save: bool = True) -> None:
        """Leave the game and close the window, saving first unless ``save`` is False.

        Saving is the same as typing "pause"; there is nothing to save before a game has
        started (typing your name). The window just closes once the game has finished up.
        """
        if self.quitting:
            return  # don't save twice if Escape gets pressed more than once
        self.quitting = True
        self.exit_silently = True
        self._quit_requested_at = time.monotonic()
        self.close_pause_menu()  # the menu must not hold the game back from saving
        self._end_fade()  # nor must a room change
        if self.game_over:
            return
        if ui._pause_handler is not None:  # only there once a game is being played
            self.typed = ""
            self.in_queue.put_nowait("pause" if save else QUIT_NOW)
        else:
            self.in_queue.put_nowait(EOF)
        # the game may be held on a line right now - let it go, so it reaches the answer above
        # and shuts down cleanly
        self.advance_event.set()
        self.skip_event.set()

    def _update_music(self) -> None:
        """Pick the music for where the player is, and move it on a frame."""
        if self.quitting:
            self.music.want_track(None)  # leaving: let it fade out
        elif self.boss_music:
            self.music.want_track("boss", instant=True)  # a boss: it starts at once, no fades
        else:
            self.music.want_track("explore" if self.room_header is not None else "intro")
        self.music.set_paused(self.paused)
        self.music.update()

    # --- drawing ----------------------------------------------------------------------------

    def box_rows(self) -> list[tuple[str, str, bool]]:
        """What the dialogue box shows now: the rows of the current page, as (text, colour, big).

        Blank lines are left out: the game prints them to space out a scrolling terminal, and in
        a box that shows one page at a time they would only be empty rows.
        """
        options = self.menu_options()
        highlighted = (
            options[self.menu_selected % len(options)][1]
            if self.menu_selected is not None and options
            else None
        )
        option_rows = {row for _number, row in options}
        shown = []
        for index in range(self.box_start, len(self.lines)):
            text, color = self.lines[index]
            if text == "":
                continue
            if index in option_rows:
                label = re.sub(r"^\s*(\d+)\)\s*", r"\1. ", text)
                if index != highlighted:
                    kind = OPTION
                elif self._pending_pick is not None:
                    kind = OPTION_PRESSED
                else:
                    kind = OPTION_SELECTED
                shown.append((label, kind, True))
            else:
                shown.append((text, color, color != SPEAKER_LABEL))  # a name is smaller
        if self.waiting_to_advance or self.waiting_for_press:
            # the game is held, so nothing more can arrive. current_line may still hold this
            # line for a moment until pump_output files it - show it, so it doesn't flicker
            if self.current_line:
                shown.append((self.current_line, "white", True))
            return shown
        if not (self.waiting_for_input and options):  # a menu has no typing line
            shown.append((*self._live_line(), True))
        if (
            self._seconds_left() is not None
            and self.hearts_line is not None
            and not any(text.startswith("Hearts:") for text, _color, _big in shown)
        ):
            # the hearts line is on an earlier page - bring it along, for the countdown
            shown.insert(0, (self.hearts_line, "white", True))
        return shown

    def _live_line(self) -> tuple[str, str]:
        """The line being typed, with a blinking cursor (or grey once the game is over)."""
        if self.game_over:
            return self.current_line, "gray"
        cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
        return self.current_line + self._shown_typed() + cursor, "lightgreen"

    def _centered_x(self, surface: pygame.Surface) -> int:
        """Where ``surface`` goes to be centred, never further left than the margin."""
        return max(self.margin, (self.width - surface.get_width()) // 2)

    def _draw_intro(self) -> None:
        """Draw the very first screen, before any room: the banner and the name prompt.

        These are not dialogue in a room, so they are drawn full-screen and centred, top to
        bottom, as big as fits: the widest line (the banner) still has to fit the window.
        """
        widest = max(
            (
                self.text.font.size(line)[0]
                for line, _color in [*self.lines, (self.current_line, "")]
            ),
            default=0,
        )
        factor = INTRO_TEXT_FACTOR
        if widest:
            factor = min(factor, self.width * INTRO_MAX_WIDTH / widest)
        size = max(8, round(self.text.size * factor))
        big_font = self.text.menu_font
        self.text.menu_font = self.text.font_at(size)  # what "big" means, just for this screen
        try:
            self._draw_intro_rows()
        finally:
            self.text.menu_font = big_font

    def _draw_intro_rows(self) -> None:
        """Draw the rows of the first screen in the (for now) big font."""
        step = round(self.text.menu_font.get_height() * INTRO_ROW_SPACING)
        top = self.margin * 3
        visible_rows = max(1, (self.height - top - self.margin) // step - 1)
        # a numbered question here (who is playing?) works like every other menu
        options = self.menu_options() if self.waiting_for_input else []
        choices = {row for _number, row in options}
        marked = (
            options[self.menu_selected % len(options)][1]
            if options and self.menu_selected is not None
            else None
        )
        first_shown = max(0, len(self.lines) - visible_rows)
        for row, (line, color) in enumerate(self.lines[first_shown:]):
            if first_shown + row in choices:
                line = line.strip()
                if first_shown + row == marked:
                    line, color = f"> {line} <", "khaki"
            self._blit_centred(self.text.render(line, color, True), top + row * step)

        y = top + min(len(self.lines), visible_rows) * step
        if self.waiting_to_advance:
            # held on a line that may not be filed yet - show it, without a live cursor
            if self.current_line:
                self._blit_centred(self.text.render(self.current_line, "white", True), y)
            return
        if options:  # a menu has no typing line
            return
        self._blit_centred(self.text.render(*self._live_line(), True), y)
        if time.monotonic() < self._name_notice_until:
            notice = self.text.render("Please enter a valid name.", "khaki", True)
            self._blit_centred(notice, y + step)

    def _blit_centred(self, surface: pygame.Surface, y: int) -> None:
        self.screen.blit(surface, (self._centered_x(surface), y))

    def _draw_scene(self, box: bool = True) -> None:
        """Draw the game itself: the room and its text bubble (left out while a room fades in)."""
        self.screen.fill("black")
        if self.room_image is not None:
            self.screen.blit(self.room_image, (0, 0))
        if self.room_header is None:
            self._draw_intro()
            return
        self._blit_centred(self.text.render(self.room_header, "khaki"), self.margin)
        if box:
            self._box_rect = self.box.draw(
                self.screen,
                self.box_rows(),
                waiting_for_press=self.waiting_for_press,
                show_tag=self.narrating and not (self.skipping or self.game_over or self.quitting),
                seconds_left=self._seconds_left(),
                margin=self.margin,
                row_gap=self.row_gap,
            )
            self.speaker.draw(
                self.screen, self._box_rect, typing=not self.waiting_to_advance, margin=self.margin
            )

    def _draw_corner_hints(self) -> None:
        """The cog for the pause menu and the little map, drawn after the scene (never blurred)."""
        if self.game_over or self.quitting:
            return
        self.floor_map.draw_hint(self.screen, self.text, self.margin)
        if self.room_header is not None:
            self.pause_menu.draw_hint(self.screen)

    def _draw_fade(self) -> None:
        """Draw one frame of a room change: old room to black, then new room up from black."""
        phase, darkness = self.fade.phase()
        if phase == "done":
            self._end_fade()  # fully lit: now the new room's story may begin
            self._draw_scene()
            self._draw_corner_hints()
            return
        if phase == "leaving" and self.fade.snapshot is not None:
            self.screen.blit(self.fade.snapshot, (0, 0))  # the room we are leaving
        else:
            self._draw_scene(box=False)  # the room we have come to, its text not started yet
        self.fade.darken(self.screen, darkness)

    def draw(self) -> None:
        """Redraw the whole window from scratch."""
        if self.paused:
            self.pause_menu.draw(self.screen)  # the scene behind it stays frozen
        elif self.fade.active:
            self._draw_fade()
        else:
            self._draw_scene()
            self._draw_corner_hints()
        pygame.display.flip()

    # --- the main loop ----------------------------------------------------------------------

    def run(self) -> None:
        """Play the game in this window until it closes."""
        asyncio.run(self.main_loop())

    async def main_loop(self) -> None:
        """The main loop: read input, pull in new text, draw - 60 times a second.

        Between two frames it waits with ``await``, which is when the game gets to run.
        """
        game = game_bridge.start_game(self)
        next_frame = time.monotonic()
        while True:
            self.handle_events()
            self.check_clock()
            self._update_music()
            if not self.exit_silently:  # leaving: nothing more to show, just wait for the game
                self.pump_output()
                self.draw()
            if self.quitting and (
                self.game_over or time.monotonic() - self._quit_requested_at > QUIT_GRACE_PERIOD
            ):
                break
            next_frame = max(next_frame + 1 / FPS, time.monotonic())
            await asyncio.sleep(next_frame - time.monotonic())
        game.cancel()  # still saving after the grace period: give up on it
        if not self.exit_silently:
            # one more pass so the game's very last message doesn't get cut off
            self.pump_output()
            self.draw()
        self.music.stop()
        pygame.quit()


def _is_room_header(line: str) -> bool:
    """Whether ``line`` is "== Room Name ==", what game.py prints when you walk into a room."""
    return line.startswith("== ") and line.endswith(" ==") and len(line) > 6


def _option_label(typed: str, block: list[tuple[str, str]]) -> str | None:
    """The words of choice ``typed`` in ``block``: "Look around" for "1" and "1) Look around"."""
    prefix = f"{typed}) "
    for text, _color in block:
        stripped = text.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix) :]
    return None
