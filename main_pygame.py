"""Runs the real console game inside a Pygame window that acts like a terminal.

We used to reimplement say()/narrate()/ask()/choose() for Pygame, but that
broke every time ui.py changed. This version runs your actual main.py
unchanged in a background thread, and only fakes stdout/stdin so the game
never knows it's not a real terminal.

Run it with:

    python main_pygame.py

Type + Enter like a normal console. The story text moves on by itself a
second after each line. When a character has spoken in it, it stays up once it is
told until Space (or Enter) is pressed. Space skips all of it. Escape
opens the pause menu: the whole game stops behind it, timers included, and
Escape again resumes. Closing the window saves and quits, the same as typing
"pause". A timed question shows its seconds counting down, and presses Enter
for you when they run out.

Quick map of the file:
    _StreamToQueue                   -> the fake stdout - also where typed
                                         vs instant lines get told apart and
                                         the game thread gets blocked (see
                                         its docstring)
    _QueueToStream                   -> the fake stdin
    _make_dialogue_sleep             -> lets a keypress fast-forward mid-typing
    TerminalWindow.__init__          -> all the state the window tracks
    TerminalWindow.wait_for_line_advance -> blocks the game thread until a press
    TerminalWindow.start_game_thread -> wires the fakes in, starts the game
    TerminalWindow._pump_output      -> turns printed text into screen lines
    TerminalWindow._handle_events    -> turns keypresses into "advance the box" or typed answers
    TerminalWindow._check_clock      -> presses Enter when a timed question runs out
    TerminalWindow._draw             -> draws everything each frame
    TerminalWindow._draw_intro       -> the old full-screen layout, before the first room
    TerminalWindow._draw_dialogue_box -> draws the Undertale-style box, lower-center
    TerminalWindow._draw_map_view    -> draws the drawn floor map, opened with the M key
    TerminalWindow._load_room_image  -> loads/scales a room's background image, if it has one
    TerminalWindow._load_static_image -> the shared loader behind that, and
                                          the intro screen's background
    TerminalWindow.run               -> the main loop tying it all together
"""

from __future__ import annotations

import array
import ctypes
import io
import json
import math
import os
import queue
import re
import sys
import threading
import time
import traceback
import wave

import pygame

import progress
import ui  # the real console ui.py - nothing here reimplements any of it
import world
from leaderboard import scoreboard
from main import main as run_console_game
from music import Music

# an exe built with `pyinstaller --windowed` has no console at all, so
# Windows hands it fake stdout/stderr that crash on the first write instead
# of just being empty - avoid that whole trap by building WITH a console
# (leave off --windowed) and hiding that console the instant we start, so
# it never flashes on screen but stdout/stderr stay real, working streams
if sys.platform == "win32" and getattr(sys, "frozen", False):
    console_window = ctypes.windll.kernel32.GetConsoleWindow()
    if console_window:
        ctypes.windll.user32.ShowWindow(console_window, 0)  # 0 = SW_HIDE

# belt-and-suspenders: if stdout/stderr are still missing or broken for any
# other reason (a different packager, a future PyInstaller change, etc.),
# give them somewhere harmless to write instead of crashing the game
try:
    sys.stdout.write("")
except Exception:
    sys.stdout = open(os.devnull, "w")  # noqa: SIM115 - stays open all program
try:
    sys.stderr.write("")
except Exception:
    sys.stderr = open(os.devnull, "w")  # noqa: SIM115 - stays open all program

# tells the game "stop waiting" - the game reads it as the end of the input
_EOF = object()

# tells the game "the clock ran out" - sent by the window, never typed
_TIMED_OUT = object()

# what the window puts in the answer queue once the player has confirmed a quit
# in the pause menu: the game stops at once instead of asking again
_QUIT_NOW = object()

# what the game thread puts in the output queue after a line of story text has had its second
# on screen: the text box starts a fresh page (it has to go through the queue, so it lands
# after that line has been filed on screen, in order)
_PAGE_BREAK = object()


class _SpeakerChange:
    """Put in the print queue when someone starts speaking (who) or stops (who is None)."""

    def __init__(self, who: str | None, mood: str) -> None:
        self.who = who
        self.mood = mood


class _ShowMap:
    """Put in the output queue where the game asks for the drawn floor map (see ui.show_map)."""


class _Cue:
    """Put in the output queue where a sound cue is to be played (see ui.cue)."""

    def __init__(self, name: str) -> None:
        self.name = name


FPS = 60

# fonts with glyphs for the unusual Unicode some puzzle text uses - the main
# font alone can't draw these, so they live next to this file as small files
# the background music: the intro loop on the first screen (while the name is typed), the
# exploring loop once the game has started (see TerminalWindow._update_music)
_MUSIC_FILES = {
    "intro": "music_intro.wav",
    "explore": "music_explore.wav",
    "boss": "music_boss.wav",
}
# one-off sounds for moments in the game, played where ui.cue(name) is called: the file, and how
# loud it is (0 to 1). "combat" is heard as a boss's questions begin
_CUE_SOUNDS = {"combat": ("combat_start.wav", 0.32), "victory": ("boss_defeated.wav", 0.32)}
# the small tick heard when the highlight moves from one choice to the next, in any menu
_MOVE_SOUND_FILE = "ui_move.wav"
# its volumes (a name and a share of full volume): the player picks one in the pause menu, and it
# starts on Low
_MOVE_SOUND_LEVELS = (("Off", 0.0), ("Low", 0.2), ("Normal", 0.3))
_MOVE_SOUND_START = 1
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# the game's main font, bundled as an actual file rather than asked for by
# name - see TerminalWindow._load_main_font for why. Free, redistributable,
# monospaced, and designed for exactly this (small, screen-rendered text) -
# see assets/JetBrainsMono-OFL.txt for its license.
_MAIN_FONT_FILE = "AmazeHand-Regular.ttf"
# our own handwriting is a copy of JetBrains Mono with the 52 letters redrawn, so if
# it is ever missing the game falls back to the plain JetBrains Mono beside it
_BACKUP_FONT_FILE = "JetBrainsMono-Regular.ttf"

_FALLBACK_FONT_FILES = ["unifont-subset.otf", "unifont-upper-subset.otf"]

# every size on screen - text, margins, spacing - is measured against this
# screen height and scaled to match the real one, so the window looks the
# same on every resolution: the same proportions, not the same pixel counts.
# 900 is what Pygame reports on the machine this layout was tuned on (a
# 2880x1800 panel with Windows display scaling at 200%).
_REFERENCE_HEIGHT = 900
_REFERENCE_FONT_SIZE = 15
_REFERENCE_MARGIN = 10

# the heart in "Hearts: ♥♥♥" (health.py) - the main font has no glyph for it
# either, so it gets a tiny font of its own: one glyph, built to the main
# font's size and spacing so it sits on the same line as the text around it
_HEART = "♥"
_HEART_FONT_FILE = "heart.otf"

# the "no heart" icon: a skull, in the same font under a private-use code point
# nothing else uses. Only the "Hearts: ..." lines get it, in place of the dot
# the game prints for an empty heart (see _render_text)
_SKULL = "\ue000"
# both icons are drawn in this red, whatever colour the text around them is
_ICON_COLOR = (235, 45, 45)

# the dialogue box is your hand-drawn chat box (assets/chat_box.png). It is cut into pieces so
# it can be stretched to any size without thinning its lines: the columns are the left leg, the
# gap (stretched to fit the words below), the foot, a stretchy middle and the right end; the rows
# are the top edge, a stretchy middle, and the bottom edge with its legs. The numbers are pixel
# positions in the drawing, which is 450 x 248
_CHAT_BOX_FILE = "chat_box.png"
# the picture is drawn at this many times the size the numbers below are written for, so it
# stays smooth when it is scaled up: every rectangle taken from it is multiplied by this
_CHAT_BOX_UPSCALE = 4
_CHAT_BOX_X_CUTS = (0, 75, 146, 200, 330, 450)
_CHAT_BOX_Y_CUTS = (0, 45, 150, 248)
_CHAT_BOX_FOOT_HEIGHT = 79  # how tall the leg and foot are: the words are sized to fit between them
_CHAT_BOX_LINE_Y = 190  # where the bottom edge runs
_CHAT_BOX_WORDS_Y = 208  # the middle of the leg and foot, where the words sit
# When there is nothing to skip, the gap and the little brackets of the leg and foot are
# erased from a copy of the drawing and its bottom edge is drawn right across, using a short,
# straight piece of that same edge (x, y, width, height in the drawing) stretched out - so the
# closed box looks like the rest of your drawing, not like a patch.
_CHAT_BOX_EDGE_PIECE = (196, 181, 15, 17)
_CHAT_BOX_EDGE_START_X = 22  # where the new edge begins: inside the left side of the drawing
_CHAT_BOX_EDGE_END_X = 211  # ...and where it joins the drawing's own bottom edge again
# what to erase (x, y, width, height in the drawing): the leg's hook below the line, then the
# foot and everything between the leg and the foot
_CHAT_BOX_ERASE = ((0, 198, 76, 50), (76, 150, 124, 98))
# shown in the gap at the bottom left of the box while the story is being told
_SKIP_HINT_TEXT = "SPACE to skip"
# ...and in its place once the story has been told, until the player presses to go on
_CONTINUE_HINT_TEXT = "SPACE to go on"

# what the Controls screen of the pause menu lists: (the keys, what they do)
_CONTROLS = [
    ("Up / Down  or  W / S", "choose from a menu or a question"),
    ("1, 2, 3 ...", "pick that choice by its number"),
    ("Enter", "confirm your choice, or send what you typed"),
    ("Space", "skip the story text, or go on once it has been told"),
    ("M", "open the floor map, once you have taken the plan from the wall"),
    ("Esc", "open the pause menu, and close it again"),
    ("Type + Enter", "answer a question in your own words"),
    ("Backspace", "take back a letter"),
]

# the choices of a menu are drawn as plain text in a column of their own (no "1)" numbers),
# the chosen one in khaki with a ">" beside it. _box_lines marks their rows with these
# two names instead of a real colour, and _draw_dialogue_box turns them into the colours
_OPTION = "option"
_OPTION_SELECTED = "option_selected"
# the choice just confirmed (Enter, or its number): it "clicks" - orange, pressed in a little
_OPTION_PRESSED = "option_pressed"
_OPTION_COLORS = {_OPTION: "white", _OPTION_SELECTED: "khaki", _OPTION_PRESSED: "orange"}

# the pause menu sits over a blurred, dimmed freeze-frame of the game, so it is
# obvious the game is stopped, yet you can still see where you were
_PAUSE_BLUR_RADIUS = 14  # at the reference screen height - scaled to the real one
_PAUSE_DIM_ALPHA = 130  # how much the frozen scene is darkened: 0 = not at all, 255 = black
_PAUSE_ACCENT = (240, 200, 80)

# background image per room, keyed by the exact "== Room Name ==" header
# text the game prints when you walk in (see TerminalWindow._is_room_header)
# - a room with no entry here just shows a plain black background, same as
# every room did before this existed. Photos are reused across rooms that
# are the same kind of real-world space (every classroom, both plain
# hallways, both labs, both teachers' rooms and the front desk office, every
# project room). The storage room is left without a photo on purpose.
_ROOM_IMAGES = {
    "== classroom.2015 ==": "classroom_2035.jpg",
    "== Classroom 2021 ==": "classroom_2035.jpg",
    "== Classroom 2.015 ==": "classroom_2035.jpg",
    "== Classroom 2.021 ==": "classroom_2035.jpg",
    "== Classroom 2.035 ==": "classroom_2035.jpg",
    "== Classroom 2.031 ==": "classroom_2031.jpg",
    "== The Blue corridor ==": "blue_corridor_hall.jpg",
    "== The Red corridor ==": "red_corridor.jpg",
    "== LAB2.003 ==": "lab.jpg",
    "== LAB 2.003 ==": "lab.jpg",  # the name the room has now
    "== Forest room ==": "forest_lab.jpg",  # lab_2001
    "== LAB 2.001 ==": "forest_lab.jpg",  # the name the forest room has now
    "== Teachers room ==": "teacher_room.jpg",
    "== Teachers room 4 ==": "teacher_room.jpg",
    "== Front Desk Office ==": "front_desk_office.jpg",
    "== Storage Room ==": "storage.jpg",
    "== Lobby ==": "lobby.jpg",
    "== Main Teachers Room ==": "teacher_room.jpg",
    "== Teachers Room 4 ==": "teacher_room_4.jpg",
    "== Project Room 1 ==": "project_room.jpg",  # shared with Project Room 2
    "== Project room 1 ==": "project_room.jpg",
    "== Project Room 2 ==": "project_room.jpg",
    "== Student society ==": "student_society.jpg",
    "== Equinox Student Society ==": "student_society.jpg",  # the name the room has now
    "== Project Room 3 ==": "project_room_3.jpg",
}

# the background behind the very first screen - the name prompt and intro
# blurb, before any room header exists (see TerminalWindow._draw_intro) -
# same "just don't draw anything if it's missing" fallback as _ROOM_IMAGES
_INTRO_IMAGE = "intro.jpg"

# the exact characters rooms/classroom_2031.py's last puzzle question uses
# (Canadian syllabics, box-drawing, math symbols, ...) that the main font
# (_MAIN_FONT_FILE) has no glyph for - everything else (ascii, accented
# letters elsewhere in the game) keeps using it as normal. The heart is the
# one other exception: it has its own font, see _HEART_FONT_FILE.
# This has to be an
# exact list rather than asking pygame "can you draw this character" at
# runtime: that check (Font.metrics()) turned out to report a character as
# drawable even when the installed font can't actually draw it, so it
# can't be trusted to decide this. Add a room with similarly unusual
# Unicode later? Add its non-ascii characters here too.
_NEEDS_FALLBACK_FONT = set("ᒲᒷᓭᔑ↸∷⊣⋮⍊⍑⎓╎⚍リꖎ𝙹")

# every line of the main text gets a soft shadow behind it (see
# TerminalWindow._render_text) so it stays readable over a room's
# background image instead of just floating on top of it bare
_TEXT_SHADOW_COLOR = (40, 40, 40)
_TEXT_SHADOW_OFFSET = 1  # pixels, down and to the right
_TEXT_SHADOW_ALPHA = 190  # 0 = invisible, 255 = fully solid

# the drawn map of the floor (assets/floor_map.png): shown over the blurred game, opened with M
# once the floor plan has been taken, and sized to fill this much of the window
_MAP_FILE = "floor_map.png"
_MAP_SCREEN_FRACTION = 0.92
# the white scribble drawn over the room you are in, one picture per room, and where each one
# goes on the map (assets/floor_map_rooms/index.json: room key -> x, y in the map's pixels)
_MAP_ROOMS_DIR = "floor_map_rooms"
# the padlocks (and shut doors) drawn on the map over every room that is still locked, one
# picture per room, with where each goes in assets/floor_map_locks/index.json
_MAP_LOCKS_DIR = "floor_map_locks"
# the small map in the bottom right corner that says "press M": this tall, as part of the window
# the cloud a speaker's face pops up in beside the dialogue box, and the faces that go in it
# (assets/<who>_<mood>.png). Its height is this share of the window's, and it grows in and
# shrinks out in these many seconds
_SPEAKER_CLOUD_FILE = "speaker_cloud.png"
_SPEAKER_MOODS = ("speaking", "smiling", "upset")
_SPEAKER_HEIGHT = 0.15
_SPEAKER_IN_SECONDS = 0.3
_SPEAKER_OUT_SECONDS = 0.16
_SPEAKER_SHAKE = {"speaking": 0.6, "smiling": 0.6, "upset": 1.0}  # how hard each mood shakes
# the story stacks up in the box like a conversation, and whoever says the next lines is named
# above them in this colour: a boss by its own name, the backpack as below, anything nobody in
# particular says as the narrator. _box_lines marks those rows with this name instead of a colour
_SPEAKER_LABEL = "speaker_label"
_SPEAKER_LABEL_COLOR = "khaki"
_NARRATOR_NAME = "Narrator"
_SPEAKER_NAMES = {"backpack": "Evil Backpack"}
_MENU_ICON_FILE = "settings_icon.png"  # the cog in the top left corner that says "press Esc"
_MAP_ICON_FILE = "floor_map_icon.png"  # a messy doodle of a map, not the map itself
_MAP_ICON_HEIGHT = 0.1
_MAP_ICON_CHECK_SECONDS = 0.5  # how often to ask whether the plan has been taken yet

# walking into a new room: the old room fades to black, stays black for a moment, and the new
# room fades in out of the black. The game waits through all of it, so the new room's text
# only starts once the picture is fully there
_CONTROLS_KEY_COLOR = (
    "khaki"  # the keys on the Controls screen, so they stand out from their meaning
)
_INTRO_ROW_SPACING = 1.7  # the first screen's rows are this many text heights apart
_INTRO_TEXT_FACTOR = 1.35  # the first screen's text, at most this many times the normal size
_INTRO_MAX_WIDTH = 0.94  # the first screen's text may fill this much of the window width
_NAME_NOTICE_SECONDS = 2.5  # how long "Please enter a valid name." stays up
_PICK_DELAY_SECONDS = 0.2  # a confirmed choice shows its click this long, then answers
# the little blip heard while the story is typed out. The backpack has its own sound
# (type_blip.wav); everyone and everything else shares another (type_blip_other.wav). It is a
# steady effect, not one sound per letter: it plays on its own sound channel, never over
# itself, and never closer together than this many seconds, whatever the typing speed. The
# other sound is turned up or down to be exactly as loud as the backpack's, whatever its file
_TYPE_SOUND_FILE = "type_blip.wav"
# every boss shares a tougher blip: lower, with a firmer start and a little grit
_TYPE_SOUND_BOSS_FILE = "type_blip_boss.wav"
_TYPE_SOUND_BOSS_ATTACK = 0.016
# the narrator (nobody in particular speaking) has its own very soft blip, this much of the
# backpack's loudness
_TYPE_SOUND_NARRATOR_FILE = "type_blip_narrator.wav"
_TYPE_SOUND_NARRATOR_SOFTNESS = 0.5
_TYPE_SOUND_GAP = 0.108  # seconds between blips at the normal pace
# seconds the start of each blip takes to swell up to full volume: longer is softer
_TYPE_SOUND_ATTACK = 0.04
_TYPE_SOUND_VOLUME = 0.26  # the backpack's blip: the loudness the other one is matched to
_FADE_TIMES = (0.45, 0.12, 0.65)  # seconds: fading out, staying black, fading in
# the very first room, when a game begins: a long, slow fade in out of the dark
_FIRST_FADE_TIMES = (1.0, 0.6, 3.5)

# the little Undertale-style dialogue box, lower-center - height just grows
# to fit whatever it's currently showing (capped at _BOX_MAX_ROWS so one
# huge menu can't fill the screen). Width is NOT a fixed size any more: text
# is wrapped as if the box were _BOX_WIDTH_FRACTION of the screen wide (so a
# long paragraph still wraps at the same point it always has), but the box
# is then drawn only as wide as its longest actual line needs, down to
# _BOX_MIN_WIDTH_FRACTION - so a short menu like "1) Look at the floor
# plan" gets a box that hugs the text instead of one that's the same width
# as a full paragraph, with empty space padding out both sides.
_BOX_WIDTH_FRACTION = 0.7
_BOX_MIN_WIDTH_FRACTION = 0.28
_BOX_MAX_ROWS = 15
_BOX_PANEL_ALPHA = 150

# set AMAZE_PYGAME_DEBUG=1 to print every fake-stdout write to the real terminal
_DEBUG = os.environ.get("AMAZE_PYGAME_DEBUG") == "1"
_debug_start = time.monotonic()


def _debug_log(message: str) -> None:
    if _DEBUG:
        print(f"[{time.monotonic() - _debug_start:7.3f}s] {message}", file=sys.stderr, flush=True)


class _StreamToQueue:
    """Fake sys.stdout - catches what the game prints and queues it for the window.

    This is also the ONE place that knows, in real time, whether
    what it's catching is being typed out character by character
    (narrate()'s _type_line()) or handed over as a whole line at once
    (say()) - and that's exactly the difference between a line the player
    needs to press through and an instant one (a menu, a prompt). See
    write() below: the moment a typed line's newline arrives, it blocks
    the GAME THREAD itself right there until the player presses something.
    That's deliberate, not just a display trick - if only the window's
    drawing paused, the game thread would keep typing further lines in the
    background at its own pace while the player was still reading the
    first one, so by the time they pressed, everything after it would
    already be sitting there fully typed instead of animating in.

    This treats every typed line - i.e. every line ui.py's own _wrap()
    hands to _type_line() - as one pause point. It doesn't try to guess
    where a sentence "really" ends; that's a room-content problem, not a
    display one. A room whose narrate() text is written as short,
    deliberately-paced parts (see rooms/corridor_blue.py for the pattern)
    already stops in the right places, because each part IS a short line.
    A room written as one long block of prose gets column-wrapped by
    ui.py and stops wherever that wrap happens to land - which is why
    long blocks belong in short parts instead, not something this file
    should be parsing English to work around.
    """

    def __init__(self, out_queue: queue.Queue[str], window: TerminalWindow) -> None:
        self._queue = out_queue
        self._window = window
        self._typing_current_line = False
        self._story_told = False  # a typed line has finished since the player last went on
        # a character (not the narrator) has talked in that story, or the game asked to keep it
        # up (ui.keep_up): it waits for a press once it is told
        self.someone_spoke = False

    def write(self, text: str) -> None:
        # this is the whole trick: print()/say()/narrate() call write(), and it
        # lands here instead of a real screen
        if not text:
            return
        self._window.wait_while_paused()  # the pause menu is open: the game stands still
        _debug_log(f"stdout.write() len={len(text)} text={text!r}")
        if text == "\n":
            was_typed = self._typing_current_line
            self._typing_current_line = False
            self._queue.put(text)
            if was_typed:
                # a real typed line just finished - stop the game thread
                # dead here and don't let it write anything more until the
                # player presses to move on
                self._window.wait_for_line_advance()
                self._story_told = True
            return
        if len(text) > 1 and text.strip():
            self.story_over()  # a menu, a question or the next room is about to be shown
        # _type_line() writes one character at a time; say()'s _write()
        # (== print()) hands over a whole already-built line in a single
        # write() call - a lone character is the signature of the typed
        # path, a longer string is the signature of the instant one
        self._typing_current_line = len(text) == 1
        if self._typing_current_line:
            self._window.narrating = True  # the "SPACE to skip" tag shows while this goes on
        self._queue.put(text)

    def story_over(self) -> None:
        """Keep the story that was just told up until the player presses to go on.

        Called on the GAME THREAD just before something else takes the box: other text, or a
        fresh page (ui.new_page). Waiting here, before that happens, is what keeps the story in
        the box while "SPACE to go on" shows, instead of an empty box.

        Only when a character - a boss, the backpack - had something to say in it: plain
        narration moves on by itself, so the player is not pressing a key after every room.
        """
        if self._story_told and self.someone_spoke:
            self._window.wait_for_story_press()
        self._story_told = False
        self.someone_spoke = False

    def flush(self) -> None:
        pass  # nothing to flush, queue.put() already delivers instantly

    def isatty(self) -> bool:
        # fixes bug where narrate() types instantly instead of one character at a time
        return True


class _QueueToStream:
    """Fake sys.stdin - the game blocks here until the player types something."""

    def __init__(self, in_queue: queue.Queue[object], on_wait_start, on_wait_end) -> None:
        self._queue = in_queue
        self._on_wait_start = on_wait_start
        self._on_wait_end = on_wait_end

    def read_answer(self, prompt: str) -> str:
        """What the game reads every answer with - see read_line_with_clock.

        Never the built-in input(), on purpose: ui.py's own timed-question
        code watches the real keyboard, and the real keyboard is not where
        the player is typing - the window is. On macOS/Linux that crashed, on
        Windows every timed question ran out.
        """
        sys.stdout.write(prompt)
        self._on_wait_start()
        try:
            line = self._queue.get()
        finally:
            self._on_wait_end()
        if line is _EOF:
            raise EOFError
        if line is _TIMED_OUT:
            raise ui.TimedOut  # the same thing ui.py does in a real terminal
        if line is _QUIT_NOW:
            raise ui.QuitRequested  # what a confirmed "quit" does - game.py ends the run
        return line

    def readline(self) -> str:
        # nothing in the game calls this (ui.py reads with read_answer), but a
        # stray input() should still work rather than crash
        try:
            return f"{self.read_answer('')}\n"
        except (EOFError, ui.TimedOut, ui.QuitRequested):
            return ""  # empty string = EOF, same as a real terminal

    def isatty(self) -> bool:
        # fixes the same narrate() bug as above - ui.py checks BOTH stdout and stdin
        return True

    def fileno(self) -> int:
        # no real file behind this, so raise like a closed/fake stream would - not a crash
        raise OSError("this is not a real terminal - no file descriptor")


def _make_dialogue_sleep(window: TerminalWindow):
    """Swaps in for time.sleep() - it is what makes the story text type out.

    It waits out each delay between characters (and between the parts of a
    text) in short slices, so that two things can cut it short: Space, which
    sets ``window.skipping`` and makes every delay after it vanish until the
    next question (see TerminalWindow._skip_narration), and the pause menu,
    which stops this clock for as long as it is open.

    Waiting for the player to read a finished line is not done here: narrate()
    gives no sleep() call between two on-screen lines to hook, so that is
    handled where the text actually is, in _StreamToQueue.write(), which calls
    TerminalWindow.wait_for_line_advance() the instant a typed line finishes.

    Passed into ui.use_io() as the sleep argument - the one official hook
    the game already has for this, so nothing in ui.py gets touched.
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


class TerminalWindow:
    """A fullscreen window: shows the game's fake-stdout output, types into its fake-stdin."""

    # printed after every answered prompt, to separate it from what comes next
    DIVIDER = "-" * 64

    # how long a finished line of story text stays before the next one starts by itself
    AUTO_ADVANCE_SECONDS = 1.0

    def __init__(self) -> None:
        """Set up the window itself, and all the state tracked between frames."""
        pygame.init()
        self.music = Music(
            {name: os.path.join(_ASSETS_DIR, file) for name, file in _MUSIC_FILES.items()}
        )
        self.move_sound = self._load_move_sound()
        self.cue_sounds = {
            name: self._load_sound(file, volume) for name, (file, volume) in _CUE_SOUNDS.items()
        }
        self.move_level = _MOVE_SOUND_START
        self.boss_music = False  # True from getting closer to a boss until its encounter is over
        if os.environ.get("AMAZE_WINDOWED") == "1":
            # a normal 1280x720 window instead of fullscreen - handy for
            # watching the game next to an editor, or for demos
            self.width, self.height = 1280, 720
            self.screen = pygame.display.set_mode((self.width, self.height))
        else:
            info = pygame.display.Info()
            self.width, self.height = info.current_w, info.current_h
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        pygame.display.set_caption("a-maze-ing-delft")

        # how much bigger or smaller this screen is than the reference one -
        # everything below that is measured in pixels is multiplied by it
        self.scale = self.height / _REFERENCE_HEIGHT
        font_size = max(8, round(_REFERENCE_FONT_SIZE * self.scale))
        self._font_size = font_size
        self._intro_fonts: dict[int, pygame.font.Font] = {}  # the first screen's text, by size
        self.font = self._load_main_font(font_size)
        # some puzzle text uses unusual Unicode (Canadian syllabics, math
        # symbols, ...) the main font has no glyphs for - these bundled
        # fonts cover that, and _render_text() below picks whichever one
        # actually has each character instead of drawing a blank box for it
        self.fallback_fonts = self._load_fallback_fonts(font_size)
        # bigger than the main text - used just for the current question
        # (the prompt and its numbered choices) inside the dialogue box, so
        # what the player can actually act on stands out from narration -
        # see _box_lines/_render_text's `big` argument
        self.menu_font = self._load_main_font(int(font_size * 1.35))
        # the word PAUSED on the pause menu
        self.title_font = self._load_main_font(max(12, round(font_size * 2.6)))
        # the hearts on the pause menu are drawn much bigger than the text around them
        hearts_size = max(12, round(font_size * 3.0))
        self.pause_hearts_size = hearts_size
        self.pause_hearts_font = self._load_heart_font(hearts_size)
        self.pause_hearts_text_font = self._load_main_font(hearts_size)
        # the hand-drawn chat box, and the sizes it has been stretched to so far
        chat_box_path = os.path.join(_ASSETS_DIR, _CHAT_BOX_FILE)
        self.chat_box_art: pygame.Surface | None = (
            pygame.image.load(chat_box_path).convert_alpha()
            if os.path.exists(chat_box_path)
            else None
        )
        self.chat_box_closed_art: pygame.Surface | None = (
            self._make_closed_chat_box(self.chat_box_art) if self.chat_box_art else None
        )
        self._chat_box_cache: dict[tuple, pygame.Surface] = {}
        # the drawn floor map, and the size it was last scaled to
        map_path = os.path.join(_ASSETS_DIR, _MAP_FILE)
        self.map_art: pygame.Surface | None = (
            pygame.image.load(map_path).convert_alpha() if os.path.exists(map_path) else None
        )
        self._map_scaled: tuple[tuple[int, int], pygame.Surface] | None = None
        self.map_rooms: dict[str, tuple[int, int]] = {}
        rooms_index = os.path.join(_ASSETS_DIR, _MAP_ROOMS_DIR, "index.json")
        if os.path.exists(rooms_index):
            with open(rooms_index, encoding="utf-8") as handle:
                self.map_rooms = {key: (xy[0], xy[1]) for key, xy in json.load(handle).items()}
        self._map_room_scaled: dict[tuple, pygame.Surface] = {}
        self.map_locks: dict[str, tuple[int, int]] = {}
        locks_index = os.path.join(_ASSETS_DIR, _MAP_LOCKS_DIR, "index.json")
        if os.path.exists(locks_index):
            with open(locks_index, encoding="utf-8") as handle:
                self.map_locks = {key: (xy[0], xy[1]) for key, xy in json.load(handle).items()}
        icon_path = os.path.join(_ASSETS_DIR, _MAP_ICON_FILE)
        self.map_icon_art: pygame.Surface | None = (
            pygame.image.load(icon_path).convert_alpha() if os.path.exists(icon_path) else None
        )
        self._map_icon: pygame.Surface | None = None
        menu_icon_path = os.path.join(_ASSETS_DIR, _MENU_ICON_FILE)
        self.menu_icon_art: pygame.Surface | None = (
            pygame.image.load(menu_icon_path).convert_alpha()
            if os.path.exists(menu_icon_path)
            else None
        )
        self._menu_icon: pygame.Surface | None = None
        self.type_sound = self._load_type_sound(_TYPE_SOUND_FILE)  # the backpack's
        self.type_sound_boss = self._load_type_sound(
            _TYPE_SOUND_BOSS_FILE, like=_TYPE_SOUND_FILE, attack=_TYPE_SOUND_BOSS_ATTACK
        )
        self.type_sound_narrator = self._load_type_sound(
            _TYPE_SOUND_NARRATOR_FILE, like=_TYPE_SOUND_FILE, softness=_TYPE_SOUND_NARRATOR_SOFTNESS
        )
        self._clipped_blips: dict[tuple[str, int], pygame.mixer.Sound] = {}
        self.type_channel: pygame.mixer.Channel | None = None
        self._last_blip = 0.0
        # the speaker's cloud and faces, and who is speaking right now
        cloud_path = os.path.join(_ASSETS_DIR, _SPEAKER_CLOUD_FILE)
        self.speaker_cloud: pygame.Surface | None = (
            pygame.image.load(cloud_path).convert_alpha() if os.path.exists(cloud_path) else None
        )
        self.speaker_faces: dict[tuple[str, str], pygame.Surface] = {}
        for mood in _SPEAKER_MOODS:
            face_path = os.path.join(_ASSETS_DIR, f"backpack_{mood}.png")
            if os.path.exists(face_path):
                self.speaker_faces[("backpack", mood)] = pygame.image.load(
                    face_path
                ).convert_alpha()
        self.speaker: tuple[str, str] | None = None  # (who, mood) while someone is talking
        self.speaker_since = 0.0
        self.speaker_left_at: float | None = None  # when they stopped, while the cloud shrinks away
        # every boss's name, by the speaker it talks as - for the name above its lines
        self.speaker_names = {
            room.boss.speaker: room.boss.name[:1].upper() + room.boss.name[1:]
            for room in world.all_rooms()
            if room.boss is not None and room.boss.speaker is not None
        }
        self.speaker_names.update(_SPEAKER_NAMES)
        # the name last put above the story on this page, so it is only shown when it changes
        self.page_speaker: str | None = None
        # where the last typed line of the story ends in self.lines: a question starts its page here
        self._story_end = 0
        self._typed_line = False  # whether the line being built is being typed out
        self._speaker_face_cache: dict[tuple, pygame.Surface] = {}  # faces scaled to each size
        self._box_rect: tuple[int, int, int, int] | None = None  # where the dialogue box was drawn
        self.fade_started: float | None = None  # when the room change began, if one is going on
        self.fade_snapshot: pygame.Surface | None = None  # the old room, as it last looked
        self._fade_times = _FADE_TIMES  # fade out, hold, fade in - this room change's own timings
        self._fade_cover: pygame.Surface | None = None
        self._has_map = False
        self._has_map_checked_at = 0.0
        # the hearts, at both text sizes - see _HEART_FONT_FILE
        self.heart_font = self._load_heart_font(font_size)
        self.heart_menu_font = self._load_heart_font(int(font_size * 1.35))
        self.row_gap = max(1, round(2 * self.scale))  # space between two rows of the box
        self.line_height = font_size + max(1, round(4 * self.scale))
        self.margin = max(4, round(_REFERENCE_MARGIN * self.scale))

        self.lines: list[tuple[str, str]] = []  # (text, color) for every finished line
        self.current_line = ""  # the line being built right now, character by character
        self.typed = ""  # what the player has typed for their current answer

        # the pinned "== Room Name ==" line, kept separate so it never scrolls away
        self.room_header: str | None = None

        # this room's background image (see _ROOM_IMAGES), swapped in
        # _pump_output() the instant a new room header arrives - None if
        # this room has no image, which just means nothing gets drawn.
        # The intro screen is plain black for now (its photo is _INTRO_IMAGE, which
        # _load_static_image can load again when it comes back) - the first real room
        # header puts that room's picture here.
        self.room_image: pygame.Surface | None = None

        self.game_over = False
        # True from the moment Escape is pressed - the game thread then stops
        # waiting for presses and sleeps, so it reaches its save straight away
        self.quitting = False
        # True once the player has chosen to leave: the window closes the moment
        # the game has saved (or not), without showing its goodbye message
        self.exit_silently = False
        self._quit_requested_at = 0.0

        # True only while the game is blocked waiting on an answer, not while narrating
        self.waiting_for_input = False

        # when a timed question runs out (time.monotonic()), or None if untimed
        self.deadline: float | None = None
        # the last "Hearts: ..." line the game printed, so a timed question can
        # show its countdown next to the hearts even on a page that does not
        # have the hearts line on it any more
        self.hearts_line: str | None = None

        # set the instant a new prompt starts, cleared once used - see _pump_output
        self._prompt_pending = False

        # where the current unanswered question starts in self.lines
        self._prompt_start: int | None = None

        # index of the last blank line seen - every question starts with one
        self._last_blank_index: int | None = None

        # game thread -> window: "here's what I printed"
        self.out_queue: queue.Queue[str] = queue.Queue()
        # window -> game thread: "here's what you typed"
        self.in_queue: queue.Queue[object] = queue.Queue()
        # set by a keypress while a line is still typing - finishes it instantly
        self.skip_event = threading.Event()
        # set by a keypress once a typed line has finished and is waiting to
        # be pressed past - what actually unblocks the game thread (see
        # _StreamToQueue.write / wait_for_line_advance)
        self.advance_event = threading.Event()
        # True once Space has been pressed: the story text then goes by without a single delay
        # until the game next asks the player something (see _skip_narration, _wait_start)
        self.skipping = False
        # True while story text is being told, for the "SPACE to skip" tag
        self.narrating = False
        # True only in that state - the game thread is genuinely blocked,
        # not just "the window happens to not be showing more yet"
        self.waiting_to_advance = False
        # True while the story is over and the box waits for Space or Enter to go on
        self.waiting_for_press = False
        # where the dialogue box's current "page" starts in self.lines -
        # advances only when the player presses past a completed line, or
        # answers a question (see _draw_dialogue_box / _handle_events)
        self.box_start = 0

        # the pause menu (Escape) - see _open_pause_menu. The game thread waits on
        # pause_gate (set = running), so the whole game stops behind the menu
        self.paused = False
        self.pause_gate = threading.Event()
        self.pause_gate.set()
        self._paused_at = 0.0
        self.pause_selected = 0
        self.pause_view = "menu"  # "menu", "scoreboard", "controls", "quit" or "map"
        self.pause_status: dict[str, object] = {}
        self.pause_scores: list[str] = []
        self._scores_read_at = 0.0  # when the scoreboard on screen was last read
        # the blurred freeze-frame drawn behind the menu, made when it opens
        self.pause_backdrop: pygame.Surface | None = None
        # a short message on the menu, such as "Game saved." - and when it goes
        self.pause_notice = ""
        self._pause_notice_until = 0.0

        # which numbered choice Up/Down has highlighted on the question being
        # asked (an index into _menu_options), or None until an arrow key is
        # pressed - so a stray Enter never answers a question by itself
        self.menu_selected: int | None = None
        # when a number key has been pressed on a menu: the moment its choice is answered
        self._pending_pick: float | None = None
        # until when to show "Please enter a valid name." under the name prompt
        self._name_notice_until = 0.0

    def _wait_start(self) -> None:
        self.skipping = False  # the story stops at a question, and so does skipping it
        self.narrating = False
        self.waiting_for_input = True
        self._prompt_pending = True

    def _wait_end(self) -> None:
        self.waiting_for_input = False

    def wait_for_line_advance(self) -> None:
        """Hold the game thread for a second right where a typed line just finished.

        Called from the GAME THREAD (see _StreamToQueue.write) the instant a typed
        line finishes. It stays for AUTO_ADVANCE_SECONDS so the player can read
        it, then carries on by itself - or at once if Space has been pressed. This
        is what stops the game thread racing ahead typing the next lines in the
        background while the player is still reading the one before. The pause
        menu stops the second from running down while it is open.

        The line stays in the box: the next one is typed under it, so the story
        stacks up like a conversation until a question, a pickup or a new room
        starts a fresh page.
        """
        if self.quitting:
            return  # leaving: don't hold anything up on the way to the save
        if not self.skipping:
            self.advance_event.clear()
            self.waiting_to_advance = True
            deadline = time.monotonic() + self.AUTO_ADVANCE_SECONDS
            while not self.advance_event.wait(0.02) and not self.quitting:
                if self.paused:
                    deadline = time.monotonic() + self.AUTO_ADVANCE_SECONDS  # held while paused
                elif time.monotonic() >= deadline:
                    break
        self.waiting_to_advance = False

    def wait_for_story_press(self) -> None:
        """Hold the game thread, with the whole story still in the box, until Space or Enter.

        Called from the GAME THREAD (see _StreamToQueue.write) once the story is over and
        something else is about to be shown. Not on the first screen, and not once Space has
        skipped the story: the player has said they do not want to wait for it.
        """
        if self.quitting or self.skipping or self.room_header is None:
            return
        self.advance_event.clear()
        self.waiting_for_press = True
        while not self.advance_event.wait(0.02) and not self.quitting:
            pass
        self.waiting_for_press = False

    @staticmethod
    def _wave_loudness(path: str, attack_seconds: float = _TYPE_SOUND_ATTACK) -> float:
        """The average loudness (RMS, 0 to 1) of a .wav file as it is played (with its soft start).

        0 if the file can't be read.
        """
        try:
            with wave.open(path) as handle:
                width = handle.getsampwidth()
                rate = handle.getframerate()
                raw = handle.readframes(handle.getnframes())
        except (OSError, wave.Error, EOFError):
            return 0.0
        if width == 1:
            values = [(byte - 128) / 128 for byte in raw]
        elif width == 2:
            samples = array.array("h")
            samples.frombytes(raw[: len(raw) // 2 * 2])
            values = [sample / 32768 for sample in samples]
        else:
            return 0.0
        attack = max(1, int(rate * attack_seconds))
        values = [v * min(1.0, i / attack) ** 2 for i, v in enumerate(values)]
        return math.sqrt(sum(v * v for v in values) / len(values)) if values else 0.0

    @staticmethod
    def _load_type_sound(
        name: str,
        like: str | None = None,
        softness: float = 1.0,
        attack: float = _TYPE_SOUND_ATTACK,
    ) -> pygame.mixer.Sound | None:
        """Load a typing blip, or None if there is no sound file or no sound on this computer.

        With ``like`` (another file's name) the volume is set so it sounds exactly as loud as
        that file does at the normal volume, however loud this file was recorded - or
        ``softness`` times as loud, for a sound meant to be quieter.
        """
        path = os.path.join(_ASSETS_DIR, name)
        if not os.path.exists(path):
            return None
        volume = _TYPE_SOUND_VOLUME
        if like is not None:
            own = TerminalWindow._wave_loudness(path, attack)
            wanted = TerminalWindow._wave_loudness(os.path.join(_ASSETS_DIR, like))
            if own > 0 and wanted > 0:
                volume = min(1.0, _TYPE_SOUND_VOLUME * softness * wanted / own)
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            sound = TerminalWindow._shape_sound(path, None, attack) or pygame.mixer.Sound(path)
            sound.set_volume(volume)
            return sound
        except pygame.error:  # no audio device: the game just stays quiet
            return None

    def _blip_for(self, voice: str, gap: float) -> pygame.mixer.Sound | None:
        """The typing blip for ``voice`` ("backpack", "boss" or "narrator"), cut to fit ``gap``.

        A blip longer than the gap is shortened and faded out.
        """
        sound, name = {
            "backpack": (self.type_sound, _TYPE_SOUND_FILE),
            "boss": (self.type_sound_boss, _TYPE_SOUND_BOSS_FILE),
            "narrator": (self.type_sound_narrator, _TYPE_SOUND_NARRATOR_FILE),
        }[voice]
        if sound is None or sound.get_length() <= gap * 0.96:
            return sound
        milliseconds = int(gap * 960)
        key = (name, milliseconds)
        clipped = self._clipped_blips.get(key)
        if clipped is None:
            attack = _TYPE_SOUND_BOSS_ATTACK if voice == "boss" else _TYPE_SOUND_ATTACK
            clipped = self._shape_sound(
                os.path.join(_ASSETS_DIR, name), milliseconds / 1000, attack
            )
            if clipped is None:
                return sound
            clipped.set_volume(sound.get_volume())
            self._clipped_blips[key] = clipped
        return clipped

    @staticmethod
    def _shape_sound(
        path: str, seconds: float | None, attack_seconds: float = _TYPE_SOUND_ATTACK
    ) -> pygame.mixer.Sound | None:
        """A .wav sound with a soft start (see _TYPE_SOUND_ATTACK), cut to ``seconds`` if given.

        A sound that is cut short is also faded out over its last part, so it does not click.
        """
        try:
            with wave.open(path) as handle:
                params = handle.getparams()
                raw = handle.readframes(handle.getnframes())
        except (OSError, wave.Error, EOFError):
            return None
        width, channels = params.sampwidth, params.nchannels
        if width not in (1, 2):
            return None
        frames = params.nframes
        fade = 0
        if seconds is not None and int(params.framerate * seconds) < frames:
            frames = int(params.framerate * seconds)
            fade = max(1, int(frames * 0.35))
        attack = min(frames, max(1, int(params.framerate * attack_seconds)))
        if width == 1:
            samples = [byte - 128 for byte in raw[: frames * channels]]
        else:
            samples = array.array("h")
            samples.frombytes(raw[: frames * channels * 2])
        for frame in range(frames):
            gain = 1.0
            if frame < attack:
                gain = (frame / attack) ** 2  # a slow, gentle swell up from silence
            if fade and frame >= frames - fade:
                gain *= (frames - frame) / fade
            if gain == 1.0:
                continue
            for channel in range(channels):
                samples[frame * channels + channel] = int(
                    samples[frame * channels + channel] * gain
                )
        data = bytes(sample + 128 for sample in samples) if width == 1 else samples.tobytes()
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as out:
            out.setnchannels(channels)
            out.setsampwidth(width)
            out.setframerate(params.framerate)
            out.writeframes(data)
        buffer.seek(0)
        try:
            return pygame.mixer.Sound(file=buffer)
        except pygame.error:
            return None

    def _blip(self, letter: str) -> None:
        """Play the typing blip for one letter that has just been typed out."""
        backpack_talking = (
            self.speaker is not None
            and self.speaker_left_at is None
            and self.speaker[0] == "backpack"
        )
        # the rhythm follows the mood of whoever is talking: quicker when upset, slower when smiling
        talking = self.speaker is not None and self.speaker_left_at is None
        gap = _TYPE_SOUND_GAP * ui.pace_for(
            self.speaker[0] if talking and self.speaker else None,
            self.speaker[1] if talking and self.speaker else "",
        )
        if backpack_talking:
            voice = "backpack"
        elif self.speaker is not None and self.speaker_left_at is None:
            voice = "boss"  # a boss, or any other character with a speaker name
        else:
            voice = "narrator"
        sound = self._blip_for(voice, gap)
        if sound is None or self.paused or letter.isspace():
            return
        now = time.monotonic()
        if now - self._last_blip < gap:
            return
        if self.type_channel is None:
            self.type_channel = pygame.mixer.Channel(0)  # its own channel: blips never stack up
        if self.type_channel.get_busy():
            return  # the last blip is still sounding: wait for it to end, never overlap it
        self._last_blip = now
        self.type_channel.play(sound)

    def _speaker_from_game(self, screen: _StreamToQueue, who: str | None, mood: str) -> None:
        """On the GAME THREAD: someone starts or stops talking. Tell the window, in text order."""
        if who is not None:
            screen.someone_spoke = True  # what they say will wait for a press once it is told
        self.out_queue.put(_SpeakerChange(who, mood))

    def _speaker_changed(self, change: _SpeakerChange) -> None:
        """Someone started talking (or swapped mood), or stopped: pop the cloud in or out."""
        now = time.monotonic()
        if change.who is None:
            if self.speaker is not None and self.speaker_left_at is None:
                self.speaker_left_at = now
            return
        if self.speaker is None or self.speaker_left_at is not None:
            self.speaker_since = now  # a fresh pop in
        self.speaker = (change.who, change.mood)
        self.speaker_left_at = None

    def _draw_speaker(self) -> None:
        """Draw the cloud with the speaker's face in it, beside the dialogue box."""
        if self.speaker is None or self.speaker_cloud is None or self._box_rect is None:
            return
        face = self.speaker_faces.get(self.speaker)
        if face is None:
            return
        now = time.monotonic()
        if self.speaker_left_at is not None:  # shrinking away
            progress = (now - self.speaker_left_at) / _SPEAKER_OUT_SECONDS
            if progress >= 1:
                self.speaker = None
                self.speaker_left_at = None
                return
            grow = 1 - progress * progress
        else:  # growing in, a little past full size and back
            progress = min(1.0, (now - self.speaker_since) / _SPEAKER_IN_SECONDS)
            back = 1.70158
            grow = 1 + (back + 1) * (progress - 1) ** 3 + back * (progress - 1) ** 2

        box_x, box_y, box_w, box_h = self._box_rect
        cloud_h = self.height * _SPEAKER_HEIGHT
        cloud_w = self.speaker_cloud.get_width() * cloud_h / self.speaker_cloud.get_height()
        # at rest: just left of the box, level with its middle
        rest_x = max(self.margin, box_x - cloud_w * 0.97)
        rest_y = box_y + box_h * 0.5 - cloud_h * 0.97
        # it grows out of its lower right, the side nearest the box
        anchor_x, anchor_y = rest_x + cloud_w * 0.8, rest_y + cloud_h * 0.78
        width = max(2, round(cloud_w * grow))
        height = max(2, round(cloud_h * grow))
        left = round(anchor_x - (anchor_x - rest_x) * grow)
        top = round(anchor_y - (anchor_y - rest_y) * grow)
        cloud = pygame.transform.smoothscale(self.speaker_cloud, (width, height))
        self.screen.blit(cloud, (left, top))

        # the face bounces and tilts while the words are typed, and only wobbles while they sit
        # on screen. The motion is smooth (sine waves, not a new random jump every frame), and
        # the tilt is turned with rotozoom, which smooths the lines - a plain rotate has
        # jagged edges that look like the drawing is warping as it moves
        typing = not self.waiting_to_advance
        strength = _SPEAKER_SHAKE.get(self.speaker[1], 0.6) * (1.0 if typing else 0.25)
        shake_x = math.sin(now * 31.0) * strength * height * 0.012
        shake_y = math.sin(now * 23.0 + 1.3) * strength * height * 0.016
        tilt = math.sin(now * 17.0 + 0.6) * strength * 1.6
        face_size = (max(2, round(width * 0.74)), 0)
        face_size = (
            face_size[0],
            max(2, round(face.get_height() * face_size[0] / face.get_width())),
        )
        key = (self.speaker, face_size)
        face_picture = self._speaker_face_cache.get(key)
        if face_picture is None:
            if len(self._speaker_face_cache) > 80:
                self._speaker_face_cache.clear()
            face_picture = pygame.transform.smoothscale(face, face_size)
            self._speaker_face_cache[key] = face_picture
        face_picture = pygame.transform.rotozoom(face_picture, tilt, 1.0)
        centre_x = left + width * 0.47 + shake_x
        centre_y = top + height * 0.47 + shake_y
        self.screen.blit(
            face_picture,
            (
                round(centre_x - face_picture.get_width() / 2),
                round(centre_y - face_picture.get_height() / 2),
            ),
        )

    @staticmethod
    def _load_sound(name: str, volume: float = 1.0) -> pygame.mixer.Sound | None:
        """Load a sound from assets/, or None if there is no file or no sound on this computer."""
        path = os.path.join(_ASSETS_DIR, name)
        if not os.path.exists(path):
            return None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            sound = pygame.mixer.Sound(path)
            sound.set_volume(volume)
            return sound
        except pygame.error:  # no audio device: the game just stays quiet
            return None

    @staticmethod
    def _load_move_sound() -> pygame.mixer.Sound | None:
        """Load the menu tick (its volume is set each time it plays)."""
        return TerminalWindow._load_sound(_MOVE_SOUND_FILE)

    def _play_cue(self, name: str) -> None:
        """Handle a cue: switch the boss music on or off, or play its sound and dip the music."""
        if name == "boss_music_on":
            self.boss_music = True
            return
        if name == "boss_music_off":
            self.boss_music = False
            return
        sound = self.cue_sounds.get(name)
        if sound is not None:
            sound.play()
            self.music.duck(max(0.8, sound.get_length()))

    def _tick(self) -> None:
        """Play the little sound for moving the highlight to another choice."""
        volume = _MOVE_SOUND_LEVELS[self.move_level][1]
        if self.move_sound is not None and volume > 0:
            self.move_sound.set_volume(volume)
            self.move_sound.play()

    def _update_music(self) -> None:
        """Pick the music for where the player is, and move it on a frame."""
        if self.quitting:
            self.music.want_track(None)  # leaving: let it fade out
        elif self.boss_music:
            self.music.want_track("boss", instant=True)  # a boss: it starts at once, no fades
        else:
            # the intro loop until the first room, the exploring loop from then on
            self.music.want_track("explore" if self.room_header is not None else "intro")
        self.music.set_paused(self.paused)
        self.music.update()

    def _start_fade(self) -> None:
        """Begin fading out of the room on screen, and hold the game while it goes dark."""
        if self.paused or self.quitting or self.fade_started is not None:
            return
        self.fade_snapshot = self.screen.copy()
        # no room header yet means this is the first room of the game
        self._fade_times = _FIRST_FADE_TIMES if self.room_header is None else _FADE_TIMES
        self.fade_started = time.monotonic()
        self.pause_gate.clear()  # the game thread stops at its next word, until the screen is black

    def _end_fade(self) -> None:
        """Stop any room change in progress and let the game carry on."""
        self.fade_started = None
        self.fade_snapshot = None
        if not self.paused:
            self.pause_gate.set()

    def _draw_fade(self) -> None:
        """Draw one frame of the room change: old room to black, then new room up from black."""
        assert self.fade_started is not None
        elapsed = time.monotonic() - self.fade_started
        fade_out, hold, fade_in = self._fade_times
        dark_at = fade_out
        light_at = dark_at + hold
        end_at = light_at + fade_in
        if elapsed < dark_at and self.fade_snapshot is not None:
            self.screen.blit(self.fade_snapshot, (0, 0))  # the room we are leaving
            darkness = elapsed / dark_at
        else:
            if elapsed >= end_at:
                self._end_fade()  # fully lit: now the new room's story may begin
                self._draw_scene()
                self._draw_map_hint()
                self._draw_menu_hint()
                return
            self._draw_scene(box=False)  # the room we have come to, its text not started yet
            darkness = 1.0 if elapsed < light_at else 1.0 - (elapsed - light_at) / fade_in
        if self._fade_cover is None or self._fade_cover.get_size() != self.screen.get_size():
            self._fade_cover = pygame.Surface(self.screen.get_size())
            self._fade_cover.fill((0, 0, 0))
        self._fade_cover.set_alpha(round(255 * max(0.0, min(1.0, darkness))))
        self.screen.blit(self._fade_cover, (0, 0))

    def wait_while_paused(self) -> float:
        """Block the GAME thread while the pause menu is open; return how long it waited."""
        if self.pause_gate.is_set():
            return 0.0
        started = time.monotonic()
        self.pause_gate.wait()
        return time.monotonic() - started

    def _open_pause_menu(self) -> None:
        """Stop the game behind a menu of its own, showing how the player is doing.

        What the menu shows is taken once, now: the game is frozen, so the
        numbers on it are too.
        """
        self._pending_pick = None  # a number pressed a moment ago is forgotten
        self.fade_started = None  # a room change in progress is dropped: the menu holds the game
        self.fade_snapshot = None
        self.pause_status = ui.status() or {}
        # freeze the scene as it is - room, text bubble, map - blurred and dimmed
        self._draw_scene()
        backdrop = self._blurred(self.screen)
        dim = pygame.Surface(backdrop.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, _PAUSE_DIM_ALPHA))
        backdrop.blit(dim, (0, 0))
        self.pause_backdrop = backdrop
        self.pause_selected = 0
        self.pause_view = "menu"
        self._paused_at = time.monotonic()
        self.paused = True
        self.pause_gate.clear()  # the game thread stops at its next word or pause

    def _can_open_map(self) -> bool:
        """True once the floor plan has been taken, unless a typed answer is being written."""
        status = ui.status()
        if self.map_art is None or self.quitting or not status or not status.get("has_map"):
            return False
        typing = self.waiting_for_input and not self.waiting_to_advance and not self._menu_options()
        return not typing  # while typing, M is just a letter

    def _open_map(self) -> None:
        """Stop the game behind the drawn map, like the pause menu does."""
        self._open_pause_menu()
        self.pause_view = "map"

    def _close_pause_menu(self) -> None:
        """Let the game carry on, with every clock set back by the time it stood still."""
        if not self.paused:
            return
        self._settle_pause_clock()  # the time played and every timer get back what the menu took
        self.paused = False
        self.pause_backdrop = None
        self.pause_gate.set()

    def _settle_pause_clock(self) -> None:
        """Count the time the menu has been open so far as paused, then start counting afresh.

        Done when the menu closes - and before saving, so the saved time played
        leaves out the time spent sitting in the menu.
        """
        now = time.monotonic()
        waited = now - self._paused_at
        self._paused_at = now
        if self.deadline is not None:
            self.deadline += waited  # a timed question gets back what the menu took
        ui.hold_time(waited)  # and so do the time played and the boss timers

    def _blurred(self, surface: pygame.Surface) -> pygame.Surface:
        """Return a gaussian-blurred copy of ``surface``: the frozen game behind the menu."""
        radius = max(3, round(_PAUSE_BLUR_RADIUS * self.scale))
        size = surface.get_size()
        # blur a quarter-size copy: four times quicker, and a blur hides the lost detail anyway
        small = pygame.transform.smoothscale(surface, (max(1, size[0] // 4), max(1, size[1] // 4)))
        gaussian_blur = getattr(pygame.transform, "gaussian_blur", None)
        if gaussian_blur is not None:  # pygame-ce, which run_game.bat installs
            small = gaussian_blur(small, max(1, radius // 4))
        else:
            # plain pygame has no blur - shrinking further and growing back smears alike
            tiny = pygame.transform.smoothscale(
                small, (max(1, small.get_width() // 4), max(1, small.get_height() // 4))
            )
            small = pygame.transform.smoothscale(tiny, small.get_size())
        return pygame.transform.smoothscale(small, size)

    def _pause_items(self) -> list[str]:
        """The labels on the pause menu, in order."""
        speed = ui.text_speed().lower()
        return [
            "Resume",
            "Leaderboard",
            "Controls",
            f"Story text: {speed}",
            f"Music: {self.music.level_name.lower()}",
            f"Menu sound: {_MOVE_SOUND_LEVELS[self.move_level][0].lower()}",
            "Save and continue",
            "Save and quit",
            "Quit the game",
        ]

    def _pause_menu_key(self, event: pygame.event.Event) -> None:
        """Handle a key press while the pause menu is open."""
        if self.pause_view == "map":
            if event.key in (
                pygame.K_ESCAPE,
                pygame.K_m,
                pygame.K_RETURN,
                pygame.K_KP_ENTER,
                pygame.K_SPACE,
                pygame.K_BACKSPACE,
            ):
                self._close_pause_menu()
            return
        if self.pause_view in ("scoreboard", "controls"):
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_BACKSPACE):
                self.pause_view = "menu"
            return
        if self.pause_view == "quit":
            self._quit_menu_key(event)
            return
        items = self._pause_items()
        if event.key == pygame.K_ESCAPE:
            self._close_pause_menu()
        elif event.key in (pygame.K_UP, pygame.K_w):
            self.pause_selected = (self.pause_selected - 1) % len(items)
            self._tick()
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.pause_selected = (self.pause_selected + 1) % len(items)
            self._tick()
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._pause_choose(self.pause_selected)
        elif event.unicode.isdigit() and 1 <= int(event.unicode) <= len(items):
            self._pause_choose(int(event.unicode) - 1)

    def _quit_items(self) -> list[str]:
        """The two answers to "Are you sure you want to quit?", in order."""
        return ["Quit the game", "Keep playing"]

    def _quit_menu_key(self, event: pygame.event.Event) -> None:
        """Handle a key press while the pause menu is asking "Are you sure you want to quit?"."""
        if event.key == pygame.K_ESCAPE:
            self._quit_choose(1)  # backing out is the same as keeping on playing
        elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
            self.pause_selected = 1 - self.pause_selected
            self._tick()
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._quit_choose(self.pause_selected)
        elif event.unicode in ("1", "2"):
            self._quit_choose(int(event.unicode) - 1)

    def _quit_choose(self, index: int) -> None:
        """Quit for good (0), or go back to the pause menu (1)."""
        if index == 0:
            self._quit(save=False)  # the game stops at once, saving nothing, and the window closes
        else:
            self.pause_view = "menu"
            self.pause_selected = 8  # back on "Quit the game"

    def _pause_choose(self, index: int) -> None:
        """Do what the pause menu's item number ``index`` says."""
        if index == 0:
            self._close_pause_menu()
        elif index == 1:
            self.pause_scores = scoreboard.lines()
            self.pause_view = "scoreboard"
        elif index == 2:
            self.pause_view = "controls"
        elif index == 3:
            ui.cycle_text_speed()  # slow, normal, fast, instant, and round again
        elif index == 4:
            self.music.cycle_level()  # off, low, normal, and round again
        elif index == 5:
            self.move_level = (self.move_level + 1) % len(_MOVE_SOUND_LEVELS)
            self._tick()  # so the new volume is heard straight away
        elif index == 6:
            self._settle_pause_clock()  # so the saved time played leaves out this pause
            try:
                saved = ui.save_game()
            except Exception:  # a locked or missing database must not take the game down
                traceback.print_exc()
                self.pause_notice = "Could not save the game."
            else:
                self.pause_notice = "Game saved." if saved else "There is nothing to save yet."
            self._pause_notice_until = time.monotonic() + 3.0
        elif index == 7:
            self._quit()  # saves and ends the game, the same as closing the window
        elif index == 8:
            # ask "Are you sure?" right here on the pause screen, on "Keep playing" to start with
            self.pause_view = "quit"
            self.pause_selected = 1

    def start_game_thread(self) -> None:
        """Wire the fake stdout/stdin in, then start the real game in the background."""
        screen = _StreamToQueue(self.out_queue, self)
        sys.stdout = screen
        keyboard = _QueueToStream(self.in_queue, self._wait_start, self._wait_end)
        sys.stdin = keyboard

        # the only place this file changes game behaviour - see _make_dialogue_sleep,
        # and read_line_with_clock below for how answers are read
        ui.use_io(write=print, read=keyboard.read_answer, sleep=_make_dialogue_sleep(self))
        ui.set_pause_menu(True)  # Escape opens the pause menu, so the game menu drops "Options"
        ui.set_cue_handler(lambda name: self.out_queue.put(_Cue(name)))  # sounds, in text order
        ui.set_page_handler(lambda: (screen.story_over(), self.out_queue.put(_PAGE_BREAK)))
        ui.set_keep_up_handler(lambda: setattr(screen, "someone_spoke", True))
        ui.set_map_handler(lambda: (screen.story_over(), self.out_queue.put(_ShowMap())))
        ui.set_speaker_handler(lambda who, mood: self._speaker_from_game(screen, who, mood))
        ui.set_flowing(True)  # the window holds each line itself: no second wait before the next
        # the box wraps every line to its own width in pixels (see _wrap_to_width). Cutting
        # lines at ui.py's 80 characters first would break each one twice, leaving a word or
        # two stranded on a row of its own
        ui.WIDTH = 10_000

        # ui.py's _type_line() has its OWN independent skip check that
        # peeks at the real console's keyboard buffer (msvcrt on Windows) -
        # a different keyboard than the pygame window entirely. run_game.bat
        # leaves that console window open behind this one, so stray input
        # there can trip it, which sets narrate()'s "skipped" flag and
        # writes the REST of that line in one go instead of character by
        # character. That's not just a skipped animation - _StreamToQueue.
        # write() tells a typed line apart from an instant one by whether
        # it arrived as single characters or one whole string (see its
        # docstring), so a line mangled this way would stop needing a press
        # at all. Disabling it keeps every line's typing genuinely one
        # write per character, which the pacing logic depends on.
        ui._pressed_a_key = lambda: False

        _debug_log(
            "after use_io(): "
            f"ui._write is print = {getattr(ui, '_write', None) is print}, "
            f"sys.stdout.isatty() = {sys.stdout.isatty()}, "
            f"ui.CHAR_DELAY = {getattr(ui, 'CHAR_DELAY', 'MISSING')}"
        )

        # wraps every read of an answer: resets the skip flag, so skipping one
        # line doesn't skip the next, and starts the clock if the question is
        # timed. Hooked on ui._read_line rather than ui.ask because it is the
        # one place EVERY answer passes through - ui.choose() reads its menus
        # without going through ask() at all, so a hook on ask() never saw a
        # timed multiple-choice question.
        def read_line_with_clock(prompt: str, timeout: float | None) -> str:
            self.skip_event.clear()
            self.deadline = None if timeout is None else time.monotonic() + timeout
            try:
                return keyboard.read_answer(prompt)
            finally:
                self.deadline = None

        ui._read_line = read_line_with_clock

        thread = threading.Thread(target=self._run_game, daemon=True)
        thread.start()

    def _run_game(self) -> None:
        try:
            run_console_game()
        except (EOFError, ui.PauseRequested, ui.QuitRequested):
            # "pause" (or Escape) or a confirmed "quit" during the very first
            # room's arrival, before game.py's own loop is there to catch it -
            # the game has already saved (or been told not to), so it's a clean end
            pass
        except Exception:
            traceback.print_exc()  # real terminal, not the window - bugs stay visible
        finally:
            self.out_queue.put("\n[Game ended - press any key to close the window]\n")
            self.game_over = True

    @staticmethod
    def _is_room_header(line: str) -> bool:
        # matches "== Room Name ==" - what game.py prints when you walk into a room
        return line.startswith("== ") and line.endswith(" ==") and len(line) > 6

    @staticmethod
    def _option_label(typed: str, block: list[tuple[str, str]]) -> str | None:
        # finds "1) Look around" for typed="1" and returns "Look around"
        prefix = f"{typed}) "
        for text, _color in block:
            stripped = text.strip()
            if stripped.startswith(prefix):
                return stripped[len(prefix) :]
        return None

    def _pump_output(self) -> None:
        """Read what the game has printed since last frame, turn it into screen lines.

        Note this never has to decide which lines need a
        press - _StreamToQueue.write() already settled that on the game
        thread itself, before this ever sees the character (see its
        docstring); by the time text reaches here the pacing has already
        happened, this is purely "turn characters into (text, color) rows".
        """
        try:
            while True:
                chunk = self.out_queue.get_nowait()
                if chunk is _PAGE_BREAK:
                    self._new_page()  # the line before it is filed: a fresh page
                    continue
                if isinstance(chunk, _SpeakerChange):
                    self._speaker_changed(chunk)
                    continue
                if isinstance(chunk, _ShowMap):
                    if self.map_art is not None and not self.quitting:
                        self._open_map()  # stops the game behind it, like pressing M
                    continue
                if isinstance(chunk, _Cue):
                    self._play_cue(chunk.name)
                    continue
                for character in chunk:
                    if character == "\n":
                        if self._is_room_header(self.current_line):
                            # new room = clean screen, but keep the header pinned up top
                            self._start_fade()
                            self.speaker = None  # whoever was talking stays behind
                            self.room_header = self.current_line
                            self.room_image = self._load_room_image(self.current_line)
                            self.lines = []
                            self._prompt_start = None
                            self._last_blank_index = None
                            self._story_end = 0
                            self._new_page()
                        else:
                            self.lines.append((self.current_line, "white"))
                            if self.current_line.startswith("Hearts:"):
                                self.hearts_line = self.current_line
                            if self.current_line == "":
                                self._last_blank_index = len(self.lines) - 1
                            if self._typed_line:
                                self._story_end = len(self.lines)
                        self.current_line = ""
                        # each new line starts fresh - needs its own press to skip
                        self.skip_event.clear()
                    else:
                        if not self.current_line:
                            self._typed_line = len(chunk) == 1
                            if self._typed_line:
                                self._name_the_speaker()  # a line of the story is starting
                        self.current_line += character
                        if len(chunk) == 1:  # one letter at a time means it is being typed out
                            self._blip(character)
                            self.music.typing()
        except queue.Empty:
            pass

        if self._prompt_pending:
            # a new question just started - remember where it began, to collapse it later
            self._prompt_start = self._last_blank_index if self._last_blank_index is not None else 0
            self._prompt_pending = False
            if self.box_start < self._story_end <= len(self.lines):
                self._new_page(self._story_end)  # the question gets the box to itself
            # an untimed menu starts on its first choice, so Enter alone answers it. A timed
            # boss question starts with nothing chosen, so a stray Enter can't answer it
            self.menu_selected = 0 if self._menu_options() and self.deadline is None else None

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
        talking = self.speaker is not None and self.speaker_left_at is None
        who = self.speaker[0] if talking and self.speaker else None
        name = _NARRATOR_NAME if who is None else self.speaker_names.get(who, who)
        if name != self.page_speaker:
            self.lines.append((name, _SPEAKER_LABEL))
            self.page_speaker = name

    def _handle_events(self) -> None:
        # file whatever the game has printed first: a key pressed in the very frame a question
        # starts would otherwise be handled before the question's choices are on screen, and
        # taken for an answer to a question that has no choices
        self._pump_output()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            elif event.type == pygame.KEYDOWN:
                if self.paused:
                    self._pause_menu_key(event)
                    continue
                if self.game_over:
                    self._quit()
                    continue
                if event.key == pygame.K_ESCAPE:
                    if ui.status() is not None and not self.quitting:
                        self._open_pause_menu()  # a game is being played: stop it
                    else:
                        self._quit()  # nothing to pause yet, such as while typing the name
                    continue
                if event.key == pygame.K_m and self._can_open_map():
                    self._open_map()
                    continue
                if self.waiting_for_press:
                    if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.advance_event.set()  # read it: on to what comes next
                    continue
                if self.waiting_to_advance or not self.waiting_for_input:
                    # the story is being told: Space skips all of it, and no other key does
                    # anything (the text moves on by itself - see wait_for_line_advance)
                    if event.key == pygame.K_SPACE:
                        self._skip_narration()
                    continue
                options = self._menu_options()
                if options:
                    # a numbered menu: the arrows (or W and S) pick, Enter answers, a number key
                    # picks that choice and answers a moment later, and nothing is typed
                    if self._pending_pick is not None:
                        continue  # a choice is already lit up, waiting to be answered
                    numbers = [number for number, _row in options]
                    if event.unicode in numbers:
                        self.menu_selected = numbers.index(event.unicode)
                        self.typed = ""
                        self._pending_pick = time.monotonic() + _PICK_DELAY_SECONDS
                    elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                        self._move_menu_selection(down=event.key in (pygame.K_DOWN, pygame.K_s))
                    elif event.key == pygame.K_RETURN and self.menu_selected is not None:
                        self._pending_pick = time.monotonic() + _PICK_DELAY_SECONDS
                    continue
                if event.key == pygame.K_RETURN:
                    if (
                        self.room_header is None
                        and ui.status() is None
                        and not ui.asking_secret()
                        and not self.typed.strip()
                    ):
                        # the name prompt: an empty name is not sent, it is only pointed out
                        self._name_notice_until = time.monotonic() + _NAME_NOTICE_SECONDS
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

    def _menu_options(self) -> list[tuple[str, int]]:
        """Return the numbered choices of the question being asked, in order.

        Each is (the number to answer with, its index in self.lines), found by
        reading the "  1) Look around" lines the game printed - the same way
        _option_label does - so every menu and every multiple-choice boss
        question works without the rooms or the game knowing about it.
        """
        if self._prompt_start is None:
            return []
        options = []
        for index in range(self._prompt_start, len(self.lines)):
            match = re.match(r"(\d+)\) ", self.lines[index][0].strip())
            if match:
                options.append((match.group(1), index))
        return options  # one choice is a menu too: picked with Enter, never typed out

    def _move_menu_selection(self, down: bool) -> None:
        """Move the highlight to the next or previous choice, wrapping round."""
        options = self._menu_options()
        if not options:
            return
        if self.menu_selected is None:
            self.menu_selected = 0 if down else len(options) - 1
        else:
            self.menu_selected = (self.menu_selected + (1 if down else -1)) % len(options)
        self.typed = ""  # the arrows take over from half a typed number
        self._tick()

    def _check_clock(self) -> None:
        """Press Enter for the player when a timed question runs out."""
        deadline = self.deadline
        if self.paused:
            return  # the clock is stopped while the pause menu is open
        if self._pending_pick is not None:
            # a number was pressed: answer with that choice once it has been lit up for a moment,
            # even if the clock of a timed question ran out meanwhile - it was pressed in time
            options = self._menu_options()
            if not self.waiting_for_input or not options or self.menu_selected is None:
                self._pending_pick = None
            elif time.monotonic() >= self._pending_pick:
                self._pending_pick = None
                self.typed = options[self.menu_selected % len(options)][0]
                self._submit(self.typed)
                return
            else:
                return
        if self.waiting_for_input and deadline is not None and time.monotonic() >= deadline:
            self._submit(_TIMED_OUT)

    def _seconds_left(self) -> int | None:
        # what the countdown shows under a timed question, or None if untimed
        if not self.waiting_for_input or self.deadline is None:
            return None
        return max(0, math.ceil(self.deadline - time.monotonic()))

    def _shown_typed(self) -> str:
        """What the player has typed, as shown on screen: a password is shown as stars."""
        return "*" * len(self.typed) if ui.asking_secret() else self.typed

    def _submit(self, answer: object) -> None:
        """Send an answer to the game, and tidy the question away on screen.

        ``answer`` is what the player typed, or _TIMED_OUT when the clock did
        the pressing - either way the screen looks the same as pressing Enter.
        """
        answer_line = self.current_line + self._shown_typed()
        if self._prompt_start is not None:
            # collapse the whole question down to just what you picked
            block = self.lines[self._prompt_start :]
            label = self._option_label(self.typed, block)
            if label is not None:
                # show "Look around", not "1"
                answer_line = f"{self.current_line}{label}"
            del self.lines[self._prompt_start :]
            self._prompt_start = None
            self._last_blank_index = None
        self.lines.append((answer_line, "gray"))
        self.lines.append((self.DIVIDER, "gray"))
        self.current_line = ""
        self.typed = ""
        # stop listening now, not when the game thread gets round to it - so a
        # second Enter (or the clock) in the next frame can't answer twice
        self.waiting_for_input = False
        self.deadline = None
        self.menu_selected = None
        self.in_queue.put(answer)
        # start the box fresh for whatever comes next, instead
        # of leaving the answered question sitting in it
        self._new_page()

    def _quit(self, save: bool = True) -> None:
        """Leave the game and close the window, saving first unless ``save`` is False.

        Saving is the same as typing "pause"; there is nothing to save before a
        game has started (typing your name). The game's goodbye message is not
        shown: the window just closes once the game has finished up.
        """
        if self.quitting:
            return  # don't save twice if Escape gets pressed more than once
        self.quitting = True
        self.exit_silently = True
        self._quit_requested_at = time.monotonic()
        self._close_pause_menu()  # the menu must not hold the game back from saving
        self._end_fade()  # nor must a room change
        if self.game_over:
            return
        # ui.py only has a pause handler once a game is being played - before
        # that (typing your name) there is nothing to save yet
        if ui._pause_handler is not None:
            self.typed = ""
            self.in_queue.put("pause" if save else _QUIT_NOW)
        else:
            self.in_queue.put(_EOF)
        # the game thread might be genuinely blocked in wait_for_line_advance
        # or mid-skip right now - let it go so it can reach the answer above and
        # shut down cleanly instead of hanging until the window is killed
        self.advance_event.set()
        self.skip_event.set()

    def _centered_x(self, surface: pygame.Surface) -> int:
        # centers text horizontally, never further left than the margin
        return max(self.margin, (self.width - surface.get_width()) // 2)

    def _load_room_image(self, header: str) -> pygame.Surface | None:
        # header is the exact "== Room Name ==" text just printed - look it
        # up in _ROOM_IMAGES rather than touching the room files themselves,
        # same reason _is_room_header() only ever pattern-matches on text
        filename = _ROOM_IMAGES.get(header)
        if filename is None:
            return None
        return self._load_static_image(filename)

    def _load_static_image(self, filename: str) -> pygame.Surface | None:
        # shared by _load_room_image (looked up per room) and the intro
        # screen's fixed background (_INTRO_IMAGE) - same file, same scaling
        path = os.path.join(_ASSETS_DIR, filename)
        if not os.path.exists(path):
            # a typo'd filename, or the image just hasn't been added yet -
            # show nothing rather than crash the whole game over a picture
            return None
        image = pygame.image.load(path).convert_alpha()
        # stretches to fill this computer's screen exactly, whatever its
        # resolution happens to be
        return pygame.transform.scale(image, (self.width, self.height))

    @staticmethod
    def _load_main_font(size: int) -> pygame.font.Font:
        # bundled as an actual file (_MAIN_FONT_FILE) instead of asked for
        # by name the way this used to (pygame.font.SysFont("consolas",
        # size)). SysFont only draws with an installed font if a machine
        # genuinely has one by that name - "consolas" is a Windows font, so
        # on the team's Mac and Linux machines it was silently substituting
        # some other monospace font instead, with no error or warning. That
        # meant the exact same line of code could render crisp on one
        # laptop and soft/generic on another - not a bug in any one
        # person's setup, just this never having been guaranteed to be the
        # same font twice. Loading the bundled file guarantees everyone
        # sees the same one, chosen specifically for small on-screen text.
        for filename in (_MAIN_FONT_FILE, _BACKUP_FONT_FILE):
            path = os.path.join(_ASSETS_DIR, filename)
            if os.path.exists(path):
                return pygame.font.Font(path, size)
        return pygame.font.SysFont("consolas", size)  # assets missing - better than crashing

    @staticmethod
    def _load_heart_font(size: int) -> pygame.font.Font | None:
        # None if the file is missing - hearts then draw as boxes, same as
        # before this existed, instead of crashing the game over a symbol
        path = os.path.join(_ASSETS_DIR, _HEART_FONT_FILE)
        return pygame.font.Font(path, size) if os.path.exists(path) else None

    @staticmethod
    def _load_fallback_fonts(font_size: int) -> list[pygame.font.Font]:
        # skips missing files instead of crashing - worst case, unusual
        # characters go back to drawing as boxes, same as before this existed
        fonts = []
        for filename in _FALLBACK_FONT_FILES:
            path = os.path.join(_ASSETS_DIR, filename)
            if os.path.exists(path):
                fonts.append(pygame.font.Font(path, font_size))
        return fonts

    def _font_for(self, character: str, big: bool = False) -> pygame.font.Font:
        # everything except the specific characters _NEEDS_FALLBACK_FONT
        # lists uses the main font (or menu_font, for the current
        # question's prompt/choices - see _render_text's `big` argument),
        # same as before any of this existed - covers ascii and accented
        # letters, all of it. The heart is the exception: its own font, at
        # the same size the text around it is drawn in
        if character in (_HEART, _SKULL) and self.heart_font is not None:
            return self.heart_menu_font if big else self.heart_font
        if character not in _NEEDS_FALLBACK_FONT or not self.fallback_fonts:
            return self.menu_font if big else self.font
        # codepoints under 0x10000 are covered by the first fallback font
        # (assets/unifont-subset.otf) - anything higher needs the second
        # one (assets/unifont-upper-subset.otf), for astral-plane
        # characters like the math-alphabet "J" one puzzle uses. Puzzle
        # text like this never shows up as a menu choice, so there's no
        # bigger version of these two - `big` doesn't apply here
        is_astral = ord(character) >= 0x10000
        if is_astral and len(self.fallback_fonts) > 1:
            return self.fallback_fonts[1]
        return self.fallback_fonts[0]

    def _render_text(self, text: str, color: str, big: bool = False) -> pygame.Surface:
        # renders one line, switching fonts mid-line wherever the current
        # font can't draw the next character - most lines only ever use
        # self.font, so this only costs anything on the unusual ones.
        # `big` renders with menu_font instead - used for the current
        # question's prompt and numbered choices (see _box_lines)
        if not text:
            text = " "
        if text.startswith("Hearts:"):
            text = text.replace("\u00b7", _SKULL)  # an empty heart is drawn as a skull

        runs: list[tuple[pygame.font.Font, str]] = []
        current_font = self._font_for(text[0], big)
        current_text = text[0]
        for character in text[1:]:
            font = self._font_for(character, big)
            if font is current_font:
                current_text += character
            else:
                runs.append((current_font, current_text))
                current_font = font
                current_text = character
        runs.append((current_font, current_text))

        foreground = self._render_runs(runs, color, tint_icons=True)

        # a soft gray shadow sits just behind the real text, offset a
        # couple pixels - keeps every line readable over a busy background
        # image instead of just whatever color the text already was
        shadow = self._render_runs(runs, _TEXT_SHADOW_COLOR)
        shadow.set_alpha(_TEXT_SHADOW_ALPHA)

        combined_width = foreground.get_width() + _TEXT_SHADOW_OFFSET
        combined_height = foreground.get_height() + _TEXT_SHADOW_OFFSET
        combined = pygame.Surface((combined_width, combined_height), pygame.SRCALPHA)
        combined.blit(shadow, (_TEXT_SHADOW_OFFSET, _TEXT_SHADOW_OFFSET))
        combined.blit(foreground, (0, 0))
        return combined

    def _render_runs(
        self, runs: list[tuple[pygame.font.Font, str]], color, tint_icons: bool = False
    ) -> pygame.Surface:
        # renders a list of (font, text) runs side by side as one surface -
        # split out of _render_text() so the same run list can be rendered
        # twice: once for the shadow, once for the real text on top of it
        icon_fonts = (self.heart_font, self.heart_menu_font)
        pieces = [
            font.render(run_text, True, _ICON_COLOR if tint_icons and font in icon_fonts else color)
            for font, run_text in runs
        ]
        if len(pieces) == 1:
            return pieces[0]  # common case - skip building a combined surface
        total_width = sum(piece.get_width() for piece in pieces)
        height = max(piece.get_height() for piece in pieces)
        combined = pygame.Surface((total_width, height), pygame.SRCALPHA)
        x = 0
        for piece in pieces:
            combined.blit(piece, (x, 0))
            x += piece.get_width()
        return combined

    def _box_lines(self) -> list[tuple[str, str, bool]]:
        """What the dialogue box should show right now.

        Only the current "page" (see box_start), never the whole
        scrollback. Every row in the box renders at the same bigger size
        (see _render_text's `big` argument) - narration and the current
        question's prompt/choices alike - only the pinned room header and
        the pre-room intro screen stay at the normal size (see _draw).

        Blank lines are dropped entirely rather than shown as an empty row.
        The game calls ``ui.say()`` with no argument all over commands.py
        and game.py purely to put a blank line between sections in a
        scrolling terminal - that's a real, printed line, so it lands in
        self.lines like any other. In a scrolling terminal a blank line
        just adds a bit of vertical space, harmless. In this box, which
        only ever shows one "page" at a time, that same blank line becomes
        its own full-height row with nothing in it - most visibly when it's
        the very first line of a fresh page (e.g. "Look around" calls
        ui.say() right before narrating the room), where it shows up as a
        big empty gap between the box's top border and the text, for no
        reason a player could ever guess. The box already has its own
        margin and a fresh border every page, so it doesn't need the
        terminal's own spacing convention reproduced inside it.
        """
        options = self._menu_options()
        highlighted = (
            options[self.menu_selected % len(options)][1]
            if self.menu_selected is not None and options
            else None
        )
        shown = []
        option_rows = {row for _number, row in options}
        for index in range(self.box_start, len(self.lines)):
            text, color = self.lines[index]
            if text == "":
                continue
            if index in option_rows:
                # a choice: its number and its words - how it is laid out and marked is up to
                # _draw_dialogue_box
                label = re.sub(r"^\s*(\d+)\)\s*", r"\1. ", text)
                if index == highlighted:
                    clicked = self._pending_pick is not None
                    shown.append((label, _OPTION_PRESSED if clicked else _OPTION_SELECTED, True))
                else:
                    shown.append((label, _OPTION, True))
                continue
            shown.append((text, color, color != _SPEAKER_LABEL))  # a name is smaller than its lines
        if self.waiting_to_advance or self.waiting_for_press:
            # the game thread is genuinely blocked right now (see
            # wait_for_line_advance) - nothing more can arrive until the
            # player presses, so just show what's there. current_line may
            # still hold this line's own text for a moment until
            # _pump_output catches up and files it into self.lines - show
            # it too so the line doesn't flicker away for a frame.
            if self.current_line:
                shown.append((self.current_line, "white", True))
            return shown
        if not (self.waiting_for_input and self._menu_options()):  # a menu has no typing line
            cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
            if self.game_over:
                live_text, live_color = self.current_line, "gray"
            else:
                live_text = self.current_line + self._shown_typed() + cursor
                live_color = "lightgreen"
            shown.append((live_text, live_color, True))
        if (
            self._seconds_left() is not None
            and self.hearts_line is not None
            and not any(text.startswith("Hearts:") for text, _color, _big in shown)
        ):
            # the hearts line belongs to an earlier page - bring it along, so
            # the countdown (drawn next to it) has somewhere to sit
            shown.insert(0, (self.hearts_line, "white", True))
        return shown

    def _wrap_to_width(self, text: str, big: bool, max_width: int) -> list[str]:
        """Break text into lines that fit max_width at the box's font.

        ui.py's own _wrap() (what actually splits narration into lines in
        the first place) only knows about a fixed column count tuned for a
        full terminal - it has no idea this box exists, let alone how wide
        it is in pixels, or that "big" lines use a bigger font than
        "normal" ones. Without this, a line that DOES fit ui.py's column
        count can still be wider than the box and simply run past its edge.
        """
        font = self.menu_font if big else self.font
        # _render_text() pads its combined surface by _TEXT_SHADOW_OFFSET
        # for the shadow copy, so the actual rendered width is always a
        # little more than font.size() alone reports - budget for that here
        # too, or a line right at the edge could still clip by that much
        budget = max_width - _TEXT_SHADOW_OFFSET
        words = text.split(" ")
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}" if current else word
            if not current or font.size(candidate)[0] <= budget:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    @staticmethod
    def _make_closed_chat_box(art: pygame.Surface) -> pygame.Surface:
        """A copy of the drawing with the gap and brackets erased and the edge run across."""
        closed = art.copy()
        up = _CHAT_BOX_UPSCALE
        for rect in _CHAT_BOX_ERASE:
            closed.fill((0, 0, 0, 0), tuple(v * up for v in rect))
        x, y, width, height = (v * up for v in _CHAT_BOX_EDGE_PIECE)
        edge = pygame.transform.smoothscale(
            art.subsurface((x, y, width, height)),
            ((_CHAT_BOX_EDGE_END_X - _CHAT_BOX_EDGE_START_X) * up, height),
        )
        closed.blit(edge, (_CHAT_BOX_EDGE_START_X * up, y))
        return closed

    def _chat_box_inside(
        self, width: int, height: int, gap: int, scale: float, closed: bool
    ) -> pygame.Surface:
        """The dark tint for everything inside the drawn lines, following their wobbly shape.

        Found by flooding the outside of the outline: whatever the flood cannot reach is
        inside, so no small gap is left between the tint and the lines. With the gap open (not
        ``closed``) a line is shut across the bottom of the gap, level with the bottom of the
        leg, so the gap counts as inside too.
        """
        key = ("inside", width, height, gap, round(scale, 3), closed)
        inside = self._chat_box_cache.get(key)
        if inside is None:
            outline = self._chat_box_outline(width, height, gap, scale, closed)
            lines = pygame.mask.from_surface(outline, 100)
            xs = _CHAT_BOX_X_CUTS
            left_cap, foot_cap = round((xs[1] - xs[0]) * scale), round((xs[3] - xs[2]) * scale)
            leg = pygame.Mask((left_cap, height))
            leg.draw(lines, (0, 0))
            shut_row = max(rect.bottom for rect in leg.get_bounding_rects()) - 1
            shut_end = left_cap + gap + foot_cap
            if not closed:  # shut the bottom of the gap, along the lowest point of the leg
                for x in range(shut_end):
                    lines.set_at((x, shut_row), 1)
            lines.invert()  # now the empty pixels are set...
            outside = lines.connected_component((0, 0))  # ...and this is the ones the flood reaches
            outside.invert()
            # stop at the lines instead of running under them, so nothing shows past their edge
            outside.erase(pygame.mask.from_surface(outline, 20), (0, 0))
            if not closed:
                for x in range(shut_end):
                    outside.set_at((x, shut_row), 0)
            inside = outside.to_surface(
                setcolor=(10, 10, 10, _BOX_PANEL_ALPHA), unsetcolor=(0, 0, 0, 0)
            )
            self._chat_box_cache[key] = inside
        return inside

    def _chat_box_outline(
        self, width: int, height: int, gap: int, scale: float, closed: bool = False
    ) -> pygame.Surface:
        """Your drawn chat box, stretched to width x height without thinning its lines.

        The drawing is cut into 5 columns by 3 rows (see _CHAT_BOX_X_CUTS). The leg, the
        foot, the right end and the top and bottom edges keep their size (all scaled by
        ``scale``); the gap is stretched to ``gap`` pixels and the stretchy middle takes
        up the rest. Only straight lines are ever stretched, so they stay as thick as drawn.
        With ``closed`` it uses the copy of the drawing that has no gap or brackets (see
        _make_closed_chat_box), for when there are no words to put there.
        """
        key = (width, height, gap, round(scale, 3), closed)
        outline = self._chat_box_cache.get(key)
        if outline is not None:
            return outline
        art = self.chat_box_closed_art if closed else self.chat_box_art
        xs, ys = _CHAT_BOX_X_CUTS, _CHAT_BOX_Y_CUTS
        natural = [round((xs[i + 1] - xs[i]) * scale) for i in range(5)]
        columns = [
            natural[0],
            gap,
            natural[2],
            max(1, width - natural[0] - gap - natural[2] - natural[4]),
            natural[4],
        ]
        top, bottom = round((ys[1] - ys[0]) * scale), round((ys[3] - ys[2]) * scale)
        rows = [top, max(1, height - top - bottom), bottom]
        outline = pygame.Surface((width, height), pygame.SRCALPHA)
        x = 0
        for column, column_width in enumerate(columns):
            y = 0
            for row, row_height in enumerate(rows):
                up = _CHAT_BOX_UPSCALE
                piece = art.subsurface(
                    (
                        xs[column] * up,
                        ys[row] * up,
                        (xs[column + 1] - xs[column]) * up,
                        (ys[row + 1] - ys[row]) * up,
                    )
                )
                outline.blit(
                    pygame.transform.smoothscale(piece, (max(1, column_width), max(1, row_height))),
                    (x, y),
                )
                y += row_height
            x += column_width
        if len(self._chat_box_cache) > 80:
            self._chat_box_cache.clear()
        self._chat_box_cache[key] = outline
        return outline

    def _draw_dialogue_box(self) -> None:
        """Draw the dialogue box, lower-centre: your hand-drawn chat box with the text in it.

        Shows only _box_lines(). While the story is being told, "SPACE to skip" is written
        in the gap at the bottom left of the box.
        """
        max_box_width = int(self.width * _BOX_WIDTH_FRACTION)
        min_box_width = int(self.width * _BOX_MIN_WIDTH_FRACTION)

        # the drawing is scaled so the words fit between its leg and foot
        hint_text = _CONTINUE_HINT_TEXT if self.waiting_for_press else _SKIP_HINT_TEXT
        hint = self._render_text(hint_text, "white", True)
        scale = hint.get_height() * 1.5 / _CHAT_BOX_FOOT_HEIGHT
        xs, ys = _CHAT_BOX_X_CUTS, _CHAT_BOX_Y_CUTS
        left_cap = round((xs[1] - xs[0]) * scale)
        foot_cap = round((xs[3] - xs[2]) * scale)
        right_cap = round((xs[5] - xs[4]) * scale)
        top_cap = round((ys[1] - ys[0]) * scale)
        bottom_cap = round((ys[3] - ys[2]) * scale)
        gap = hint.get_width() + round(24 * scale)
        # room for the lines of the drawing around the text
        left_pad = round(42 * scale) + self.margin // 2
        right_pad = round(20 * scale) + self.margin // 2
        top_pad = max(top_cap, round(40 * scale)) + self.margin // 2

        # wrap against the MAX width regardless of how wide the box ends up
        # drawn - a long paragraph should still wrap at the same column it
        # always has, not reflow just because a short line elsewhere would
        # let the box shrink
        inner_width = max_box_width - left_pad - right_pad

        wrapped: list[tuple[str, str, bool]] = []
        for text, color, big in self._box_lines():
            for sub_line in self._wrap_to_width(text, big, inner_width):
                wrapped.append((sub_line, color, big))
        wrapped = wrapped[-_BOX_MAX_ROWS:]

        # a timed question shows its countdown in orange, right next to the
        # hearts, at the same text size - on a row of its own only if there
        # is no hearts row to sit beside
        seconds_left = self._seconds_left()
        countdown = None if seconds_left is None else f"[{seconds_left}s left]"
        hearts_row = None
        if countdown is not None:
            for index in range(len(wrapped) - 1, -1, -1):
                if wrapped[index][0].startswith("Hearts:"):
                    hearts_row = index
                    break
            if hearts_row is None:
                wrapped.append((countdown, "orange", True))
                wrapped = wrapped[-_BOX_MAX_ROWS:]
                countdown = None

        colors = {**_OPTION_COLORS, _SPEAKER_LABEL: _SPEAKER_LABEL_COLOR}
        surfaces = [
            self._render_text(text, colors.get(color, color), big) for text, color, big in wrapped
        ]
        # the choices share one column, centred in the box: the same left edge for every
        # one of them, with the ">" in a gutter beside it so the words never shift
        option_rows = [
            row for row, (_text, color, _big) in enumerate(wrapped) if color in _OPTION_COLORS
        ]
        gutter = self.menu_font.size("> ")[0]
        column_width = max((surfaces[row].get_width() for row in option_rows), default=0)
        marker = self._render_text(">", "khaki", True)
        closing_marker = self._render_text("<", "khaki", True)
        pressed_marker = self._render_text(">", "orange", True)
        pressed_closing_marker = self._render_text("<", "orange", True)
        press_shift = max(
            2, round(4 * scale)
        )  # how far a click pushes the markers in and the row down
        tail = self.menu_font.size(" <")[0]  # room for the "<" after the longest choice
        countdown_surface = None
        countdown_x = 0
        if countdown is not None and hearts_row is not None:
            countdown_surface = self._render_text(countdown, "orange", True)
            countdown_x = surfaces[hearts_row].get_width() + self.menu_font.size("  ")[0]
        row_heights = [surface.get_height() + self.row_gap for surface in surfaces]
        box_height = top_pad + sum(row_heights) + bottom_cap

        # now that we know how wide the actual (already-wrapped) lines are,
        # hug the box to the widest one instead of always drawing it at the
        # max width - clamped so it never gets so narrow a line clips, and
        # never wider than what wrapping was budgeted for above
        content_width = max((surface.get_width() for surface in surfaces), default=0)
        if countdown_surface is not None:
            content_width = max(content_width, countdown_x + countdown_surface.get_width())
        if option_rows:
            content_width = max(content_width, gutter + column_width + tail)
        # ...and never narrower than the drawing's own pieces: leg, gap, foot and right end
        drawing_width = left_cap + gap + foot_cap + right_cap + round(20 * scale)
        box_width = min(max_box_width, max(min_box_width, content_width + left_pad + right_pad))
        box_width = max(box_width, drawing_width)

        box = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        panel = (*(10, 10, 10), _BOX_PANEL_ALPHA)
        # words in the gap only while the story is being told - otherwise the gap is closed
        showing_hint = (
            self.chat_box_art is not None
            and self.narrating
            and not (self.skipping or self.game_over or self.quitting)
        )
        if self.chat_box_art is not None:
            # a dark panel right up to the drawn lines - and under the words in the gap
            inside = self._chat_box_inside(box_width, box_height, gap, scale, not showing_hint)
            box.blit(inside, (0, 0))
            outline = self._chat_box_outline(
                box_width, box_height, gap, scale, closed=not showing_hint
            )
            box.blit(outline, (0, 0))
        else:  # the drawing is missing: a plain box, as before
            box.fill(panel)
            pygame.draw.rect(box, "white", box.get_rect(), 1)

        y = top_pad
        for row, (surface, row_height) in enumerate(zip(surfaces, row_heights, strict=True)):
            if row in option_rows:
                # a little left of centre: the column starts 20% of the way along the free space
                free = box_width - left_pad - right_pad - gutter - column_width - tail
                block_x = left_pad + max(0, int(free * 0.2))
                pressed = wrapped[row][1] == _OPTION_PRESSED
                lift = press_shift // 2 if pressed else 0  # a click pushes the whole row down
                if wrapped[row][1] in (_OPTION_SELECTED, _OPTION_PRESSED):
                    left_marker = pressed_marker if pressed else marker
                    right_marker = pressed_closing_marker if pressed else closing_marker
                    box.blit(left_marker, (block_x + (press_shift if pressed else 0), y + lift))
                    box.blit(
                        right_marker,
                        (
                            block_x
                            + gutter
                            + surface.get_width()
                            + tail
                            - right_marker.get_width()
                            - (press_shift if pressed else 0),
                            y + lift,
                        ),
                    )
                box.blit(surface, (block_x + gutter, y + lift))
            else:
                box.blit(surface, (left_pad, y))
            if countdown_surface is not None and row == hearts_row:
                box.blit(countdown_surface, (left_pad + countdown_x, y))
            y += row_height

        if showing_hint:
            words_y = box_height - bottom_cap + round((_CHAT_BOX_WORDS_Y - ys[2]) * scale)
            box.blit(
                hint, (left_cap + (gap - hint.get_width()) // 2, words_y - hint.get_height() // 2)
            )

        x = (self.width - box_width) // 2
        y = self.height - box_height - self.margin * 3
        self._box_rect = (x, y, box_width, box_height)
        self.screen.blit(box, (x, y))

    def _draw_intro(self) -> None:
        """Draw the very first screen, before the player has entered any room.

        self.room_header is still None here - this is the same full-screen,
        centered, top-to-bottom layout every line used before the dialogue box
        existed. The name prompt and the intro blurb aren't dialogue inside
        a room, so they don't belong crammed in the little box - this is
        "where it originally was". Pacing (typed lines still needing a
        press) is unchanged; only where it's drawn is different.
        """
        # the first screen's text is as big as it can be (up to _INTRO_TEXT_FACTOR times the normal
        # size) while its widest line - the banner - still fits the window. The size follows the
        # window like everything else here: a smaller screen gets smaller text, smoothly
        widest = max(
            (self.font.size(line)[0] for line, _color in [*self.lines, (self.current_line, "")]),
            default=0,
        )
        factor = _INTRO_TEXT_FACTOR
        if widest:
            factor = min(factor, self.width * _INTRO_MAX_WIDTH / widest)
        size = max(8, round(self._font_size * factor))
        if size not in self._intro_fonts:
            self._intro_fonts[size] = self._load_main_font(size)
        big_font = self.menu_font
        self.menu_font = self._intro_fonts[size]  # what "big" means, just for this screen
        try:
            self._draw_intro_rows()
        finally:
            self.menu_font = big_font

    def _draw_intro_rows(self) -> None:
        """Draw the rows of the first screen in the (temporarily set) big font."""
        big = True
        # airy rather than packed: a good gap between every row, and some room above the banner
        step = round(self.menu_font.get_height() * _INTRO_ROW_SPACING)
        top = self.margin * 3
        visible_rows = max(1, (self.height - top - self.margin) // step - 1)
        # a numbered question here (who is playing?) works like every other menu: the arrows pick,
        # and the choice that Enter would answer is marked the way the pause menu marks one
        options = self._menu_options() if self.waiting_for_input else []
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
            surface = self._render_text(line, color, big)
            self.screen.blit(surface, (self._centered_x(surface), top + row * step))

        y = top + min(len(self.lines), visible_rows) * step
        if self.waiting_to_advance:
            # game thread is blocked - current_line may still hold this
            # line's own text for a moment until _pump_output catches up
            # and files it into self.lines; show it so it doesn't flicker
            # away for a frame, just without a live cursor
            if self.current_line:
                surface = self._render_text(self.current_line, "white", big)
                self.screen.blit(surface, (self._centered_x(surface), y))
            return
        if options:  # a menu has no typing line
            return
        cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
        typing = self.current_line + self._shown_typed() + cursor
        live_text = self.current_line if self.game_over else typing
        live_color = "gray" if self.game_over else "lightgreen"
        surface = self._render_text(live_text, live_color, big)
        self.screen.blit(surface, (self._centered_x(surface), y))
        if time.monotonic() < self._name_notice_until:
            notice = self._render_text("Please enter a valid name.", "khaki", big)
            self.screen.blit(notice, (self._centered_x(notice), y + step))

    def _render_pause_hearts(self, hearts: str) -> pygame.Surface:
        """The "Hearts: ..." row of the pause menu, with the hearts big and red."""
        icon_font, bracket_font = self.pause_hearts_font, self.pause_hearts_text_font
        if icon_font is None:  # no heart font: the normal row
            return self._render_text(f"Hearts: {hearts}", "white", True)
        label = self._render_text("Hearts:", "white", True)
        pieces = []
        for character in hearts.replace("\u00b7", _SKULL):  # an empty heart is a skull
            icon = character in (_HEART, _SKULL)
            font = icon_font if icon else bracket_font
            pieces.append(font.render(character, True, _ICON_COLOR if icon else (245, 245, 245)))
        gap = self.menu_font.size(" ")[0]
        surface = pygame.Surface(
            (label.get_width() + gap + sum(p.get_width() for p in pieces), icon_font.get_height()),
            pygame.SRCALPHA,
        )
        # the small label is centred on the hearts: the middle of its capital letters level
        # with the middle of a heart (a heart is drawn from 90 to 610 units above the line,
        # so its middle is 350 up, and a capital of this font is about 956 tall)
        heart_middle = icon_font.get_ascent() - 0.35 * self.pause_hearts_size
        label_baseline = heart_middle + 0.5 * 0.956 * self.menu_font.get_height() / 1.32
        surface.blit(label, (0, round(label_baseline - self.menu_font.get_ascent())))
        x = label.get_width() + gap
        for piece in pieces:
            surface.blit(piece, (x, 0))
            x += piece.get_width()
        return surface

    def _draw_pause_menu(self) -> None:
        """Draw the pause menu over the blurred freeze-frame of the game.

        How the player is doing sits around the edges: hearts top left, time
        played top right, how much of the floor is explored along the bottom.
        """
        if self.pause_backdrop is not None:
            self.screen.blit(self.pause_backdrop, (0, 0))
        else:
            self.screen.fill("black")
        if self.pause_view == "map":
            self._draw_map_view()
            return

        status = self.pause_status
        corner = self.margin * 4
        hearts = self._render_pause_hearts(str(status.get("hearts", "")))
        self.screen.blit(hearts, (corner, corner))
        seconds = progress.format_duration(float(status.get("seconds", 0)))  # type: ignore[arg-type]
        played = self._render_text(f"Time played  {seconds}", "white", True)
        self.screen.blit(played, (self.width - corner - played.get_width(), corner))
        explored = self._render_text(
            f"{status.get('percent', 0)}% of the floor explored", "white", True
        )
        self.screen.blit(
            explored,
            (
                (self.width - explored.get_width()) // 2,
                self.height - corner - explored.get_height(),
            ),
        )

        title = self.title_font.render("PAUSED", True, _PAUSE_ACCENT)
        y = self.height // 8
        self.screen.blit(title, ((self.width - title.get_width()) // 2, y))
        y += title.get_height() + self.margin
        name = self._render_text(str(status.get("name", "")), "gray", True)
        self.screen.blit(name, ((self.width - name.get_width()) // 2, y))

        if self.pause_view == "scoreboard":
            if (
                time.monotonic() - self._scores_read_at > 1.0
            ):  # the shared list arrives a moment later
                self.pause_scores = scoreboard.lines()
                self._scores_read_at = time.monotonic()
            rows = [(line, "white") for line in self.pause_scores]
            hint = "Esc or Enter: back"
        elif self.pause_view == "controls":
            rows = [(f"{keys}  -  {what}", "white") for keys, what in _CONTROLS]
            key_names = [keys for keys, _what in _CONTROLS]  # drawn in their own colour below
            hint = "Esc or Enter: back"
        elif self.pause_view == "quit":
            rows = [
                ("Are you sure you want to quit?", "white"),
                ("Any progress from this run will be lost.", "gray"),
                ("", "white"),
            ] + [
                (f"> {label} <", "khaki")
                if number == self.pause_selected
                else (f"  {label}  ", "white")
                for number, label in enumerate(self._quit_items())
            ]
            hint = "Up / Down and Enter, or Esc to keep playing"
        else:
            rows = [
                (f"> {label} <", "khaki")
                if number == self.pause_selected
                else (f"  {label}  ", "white")
                for number, label in enumerate(self._pause_items())
            ]
            hint = "Up / Down and Enter, or Esc to resume"
        y = int(self.height * 0.36)
        for number, (text, color) in enumerate(rows):
            if self.pause_view == "controls":
                row = self._controls_row(key_names[number], text[len(key_names[number]) :])
            else:
                row = self._render_text(text, color, True)
            self.screen.blit(row, ((self.width - row.get_width()) // 2, y))
            y += int(row.get_height() * 1.6)
        hint_row = self._render_text(hint, "gray")
        self.screen.blit(hint_row, ((self.width - hint_row.get_width()) // 2, y + self.margin * 2))
        if self.pause_notice and time.monotonic() < self._pause_notice_until:
            note = self._render_text(self.pause_notice, "khaki", True)
            self.screen.blit(note, ((self.width - note.get_width()) // 2, y + self.margin * 5))

    def _controls_row(self, keys: str, rest: str) -> pygame.Surface:
        """One line of the Controls screen: the keys in khaki, then what they do in white."""
        left = self._render_text(keys, _CONTROLS_KEY_COLOR, True)
        right = self._render_text(rest, "white", True)
        row = pygame.Surface(
            (left.get_width() + right.get_width(), left.get_height()), pygame.SRCALPHA
        )
        row.blit(left, (0, 0))
        row.blit(right, (left.get_width(), 0))
        return row

    def _draw_map_view(self) -> None:
        """Draw the floor map as big as the window allows, with how to close it underneath."""
        hint = self._render_text("M or Esc: close the map", "gray")
        room_below = hint.get_height() + self.margin * 3
        if self.map_art is not None:
            art_w, art_h = self.map_art.get_size()
            scale = min(
                self.width * _MAP_SCREEN_FRACTION / art_w,
                (self.height * _MAP_SCREEN_FRACTION - room_below) / art_h,
            )
            size = (max(1, round(art_w * scale)), max(1, round(art_h * scale)))
            if self._map_scaled is None or self._map_scaled[0] != size:
                self._map_scaled = (size, pygame.transform.smoothscale(self.map_art, size))
            picture = self._map_scaled[1]
            x = (self.width - size[0]) // 2
            y = (self.height - room_below - size[1]) // 2 + self.margin
            self.screen.blit(picture, (x, y))
            here = self._map_room_picture(str(self.pause_status.get("room", "")), size[0] / art_w)
            if here is not None:  # the scribble over the room you are in
                offset_x, offset_y = self.map_rooms[str(self.pause_status.get("room", ""))]
                self.screen.blit(here, (x + round(offset_x * scale), y + round(offset_y * scale)))
            # a padlock on every door and hallway that is still locked
            unlocked = set(self.pause_status.get("unlocked", []))  # type: ignore[arg-type]
            for room, (offset_x, offset_y) in self.map_locks.items():
                if room in unlocked:
                    continue
                lock = self._map_overlay_picture(_MAP_LOCKS_DIR, room, size[0] / art_w)
                if lock is not None:
                    self.screen.blit(
                        lock, (x + round(offset_x * scale), y + round(offset_y * scale))
                    )
        self.screen.blit(
            hint,
            (
                (self.width - hint.get_width()) // 2,
                self.height - hint.get_height() - self.margin * 2,
            ),
        )

    def _map_room_picture(self, room: str, scale: float) -> pygame.Surface | None:
        """The scribble for ``room``, scaled like the map is, or None if the room is not on it."""
        if room not in self.map_rooms:
            return None
        return self._map_overlay_picture(_MAP_ROOMS_DIR, room, scale)

    def _map_overlay_picture(self, folder: str, room: str, scale: float) -> pygame.Surface | None:
        """``room``'s picture from ``folder``, scaled like the map is, or None if there is none."""
        key = (folder, room, round(scale, 4))
        picture = self._map_room_scaled.get(key)
        if picture is None:
            path = os.path.join(_ASSETS_DIR, folder, room + ".png")
            if not os.path.exists(path):
                return None
            original = pygame.image.load(path).convert_alpha()
            size = (
                max(1, round(original.get_width() * scale)),
                max(1, round(original.get_height() * scale)),
            )
            picture = pygame.transform.smoothscale(original, size)
            self._map_room_scaled[key] = picture
        return picture

    def _draw_menu_hint(self) -> None:
        """Draw a cog over "ESC" in the top left corner, once a game is on, to open the menu."""
        if (
            self.menu_icon_art is None
            or self.room_header is None
            or self.game_over
            or self.quitting
        ):
            return
        if self._menu_icon is None:
            height = max(8, round(self.height * _MAP_ICON_HEIGHT * 0.65))
            width = max(
                8, round(self.menu_icon_art.get_width() * height / self.menu_icon_art.get_height())
            )
            self._menu_icon = pygame.transform.smoothscale(self.menu_icon_art, (width, height))
        key = self._render_text("ESC", "white", True)
        icon = self._menu_icon
        column = max(icon.get_width(), key.get_width())
        left = self.margin * 2
        top = self.margin * 2
        self.screen.blit(icon, (left + (column - icon.get_width()) // 2, top))
        self.screen.blit(
            key,
            (left + (column - key.get_width()) // 2, top + icon.get_height() + self.margin // 2),
        )

    def _draw_map_hint(self) -> None:
        """Draw a tiny map over an "M" in the bottom right corner, once there is a map to open."""
        now = time.monotonic()
        if now - self._has_map_checked_at > _MAP_ICON_CHECK_SECONDS:
            self._has_map_checked_at = now
            status = ui.status()
            self._has_map = bool(status and status.get("has_map"))
        if not self._has_map or self.map_art is None or self.game_over or self.quitting:
            return
        if self._map_icon is None:
            height = max(8, round(self.height * _MAP_ICON_HEIGHT))
            art = self.map_icon_art or self.map_art
            width = max(8, round(art.get_width() * height / art.get_height()))
            self._map_icon = pygame.transform.smoothscale(art, (width, height))
        key = self._render_text("M", "white", True)
        icon = self._map_icon
        column = max(icon.get_width(), key.get_width())
        right = self.width - self.margin * 2
        key_y = self.height - self.margin * 2 - key.get_height()
        icon_y = key_y - icon.get_height() - self.margin // 2
        self.screen.blit(icon, (right - (column + icon.get_width()) // 2, icon_y))
        self.screen.blit(key, (right - (column + key.get_width()) // 2, key_y))

    def _draw_scene(self, box: bool = True) -> None:
        """Draw the game itself: the room and its text bubble (left out while a room fades in)."""
        self.screen.fill("black")
        if self.room_image is not None:
            self.screen.blit(self.room_image, (0, 0))

        if self.room_header is None:
            # before the first room - see _draw_intro
            self._draw_intro()
        else:
            surface = self._render_text(self.room_header, "khaki")
            self.screen.blit(surface, (self._centered_x(surface), self.margin))
            if box:
                self._draw_dialogue_box()
                self._draw_speaker()

    def _draw(self) -> None:
        """Redraw the whole window from scratch - Pygame has no "update just this line"."""
        if self.paused:
            self._draw_pause_menu()  # the scene behind it stays frozen
        elif self.fade_started is not None:
            self._draw_fade()
        else:
            self._draw_scene()
            self._draw_map_hint()  # drawn after the scene, so the pause blur never has it in it
            self._draw_menu_hint()
        pygame.display.flip()  # nothing is visible until this swaps the frame onto the screen

    # after quitting, wait this long for the game to save and say goodbye
    QUIT_GRACE_PERIOD = 5.0

    def run(self) -> None:
        """The main loop: read input, pull in new text, draw - 60 times a second."""
        self.start_game_thread()
        clock = pygame.time.Clock()
        while True:
            self._handle_events()
            self._check_clock()
            self._update_music()
            if (
                not self.exit_silently
            ):  # leaving: nothing more to show, just wait for the game to finish
                self._pump_output()
                self._draw()
            if self.quitting and (
                self.game_over
                or time.monotonic() - self._quit_requested_at > self.QUIT_GRACE_PERIOD
            ):
                break
            clock.tick(FPS)  # caps the loop at 60fps instead of spinning as fast as possible
        if not self.exit_silently:
            # one more pass so the game's very last message doesn't get cut off
            self._pump_output()
            self._draw()
        self.music.stop()
        pygame.quit()


if __name__ == "__main__":
    TerminalWindow().run()  # only runs the window if this file is executed directly
