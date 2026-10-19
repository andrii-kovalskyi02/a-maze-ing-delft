"""Background music for the Pygame window: two quiet loops that fade into each other.

One track plays at a time and loops. :meth:`Music.want_track` says which one should be playing
and :meth:`Music.update`, called every frame, fades the old one out and the new one in, so
nothing ever cuts off. The music dips a little while story text is typed, so the typing sounds
stay clear, and drops further while the game is paused. The player picks Off, Low or Normal.

Nothing here can stop the game: if there is no sound card, or a file is missing, the music just
stays silent.
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable
from typing import Protocol

#: The volumes the player can pick, as a name and a share of full volume. Both are quiet on purpose.
LEVELS: tuple[tuple[str, float], ...] = (("Off", 0.0), ("Low", 0.1), ("Normal", 0.22))
DEFAULT_LEVEL = 2

FADE_OUT_SECONDS = 1.4  # how long the old track takes to fade away
FADE_IN_SECONDS = 1.5  # and the new one to come up
QUICK_FADE_OUT_SECONDS = 0.8  # the same, when the change is sudden (a boss appears)
QUICK_FADE_IN_SECONDS = 0.8
DUCK_SHARE = 0.55  # the music is this loud while text is being typed
DUCK_HOLD_SECONDS = 0.5  # and stays low this long after the last letter
PAUSED_SHARE = 0.4  # and this loud while the game is paused
SMOOTHING_PER_SECOND = 2.5  # how quickly it moves to a new share, so it never jumps
#: Tracks that keep one steady volume: they do not dip while text is typed (only when paused).
#: All three tracks are steady, so the music's volume never goes up and down by itself.
STEADY_TRACKS = frozenset({"intro", "explore", "boss"})


class Backend(Protocol):
    """What :class:`Music` needs from a sound player (pygame's ``mixer.music`` is one)."""

    def load(self, path: str) -> None:
        """Get a sound file ready to play."""

    def play(self, loops: int = 0) -> None:
        """Start playing it, repeating ``loops`` more times (-1 for ever)."""

    def stop(self) -> None:
        """Stop playing."""

    def set_volume(self, volume: float) -> None:
        """Set how loud it is, from 0 to 1."""


class Music:
    """The game's background music."""

    def __init__(
        self,
        files: dict[str, str],
        backend: Backend | None = None,
        clock: Callable[[], float] = time.monotonic,
        steady: frozenset[str] = STEADY_TRACKS,
    ) -> None:
        """Set up the music.

        Args:
            files: Track name to the path of its looping sound file.
            backend: The sound player. By default pygame's, if there is a sound card.
            clock: The time in seconds. Tests move it by hand.
            steady: The tracks that do not dip while text is typed.
        """
        self._files = files
        self._steady = steady
        self._clock = clock
        self._backend: Backend | None = backend if backend is not None else _pygame_backend()
        self.level = DEFAULT_LEVEL
        self._current: str | None = None  # the track that is loaded and playing
        self._wanted: str | None = None  # the track that should be playing
        self._quick = False  # whether the change to it should be sudden
        self._instant = False  # whether it should start at once, at full volume
        self._fade = 0.0  # 0 silent to 1 full, for the current track
        self._share = 1.0  # the ducking and pause share, smoothed
        self._duck_until = 0.0
        self._paused = False
        self._last = clock()
        self._volume_sent = -1.0

    # ------------------------------------------------------------ what the game tells it

    @property
    def level_name(self) -> str:
        """The name of the volume in use: "Off", "Low" or "Normal"."""
        return LEVELS[self.level][0]

    def cycle_level(self) -> str:
        """Go to the next volume (and back to the first after the last); return its name."""
        self.level = (self.level + 1) % len(LEVELS)
        return self.level_name

    def want_track(self, name: str | None, quick: bool = False, instant: bool = False) -> None:
        """Say which track should be playing, or None for silence.

        With ``quick`` the change is sudden, a short fade instead of a long one. With ``instant``
        the old track is cut off and the new one starts at once at full volume, with no fade
        at all: for a boss.
        """
        self._wanted = name
        self._quick = quick
        self._instant = instant

    def typing(self) -> None:
        """Say that a letter of story text has just been typed: the music dips for a moment."""
        self.duck()

    def duck(self, seconds: float = DUCK_HOLD_SECONDS) -> None:
        """Dip the music for ``seconds`` (a sound effect is about to be heard)."""
        self._duck_until = max(self._duck_until, self._clock() + seconds)

    def set_paused(self, paused: bool) -> None:
        """Say whether the game is paused: the music is quieter while it is."""
        self._paused = paused

    def playing(self) -> str | None:
        """The name of the track that is loaded and playing now, if any."""
        return self._current

    # ------------------------------------------------------------ once a frame

    def update(self) -> None:
        """Fade towards what is wanted. Call this every frame."""
        now = self._clock()
        seconds = max(0.0, min(now - self._last, 0.25))  # a long pause must not jump the fade
        self._last = now
        if self._backend is None:
            return
        try:
            self._advance(now, seconds)
        except Exception:  # a sound problem must never take the game down
            self._backend = None

    def _advance(self, now: float, seconds: float) -> None:
        assert self._backend is not None
        if self._current != self._wanted:
            fade_out = QUICK_FADE_OUT_SECONDS if self._quick else FADE_OUT_SECONDS
            self._fade = 0.0 if self._instant else max(0.0, self._fade - seconds / fade_out)
            if self._fade <= 0.0:
                if self._current is not None:
                    self._backend.stop()
                    self._current = None
                if self._wanted is not None and self._start(self._wanted):
                    self._current = self._wanted
                    if self._instant:
                        self._fade = 1.0  # no fade-in: it starts at full volume
                elif self._wanted is not None:
                    self._wanted = None  # it cannot be played: give up on it quietly
        elif self._current is not None:
            fade_in = QUICK_FADE_IN_SECONDS if self._quick else FADE_IN_SECONDS
            self._fade = min(1.0, self._fade + seconds / fade_in)  # the new one arrives
        ducking = now < self._duck_until and self._current not in self._steady
        target = PAUSED_SHARE if self._paused else (DUCK_SHARE if ducking else 1.0)
        step = SMOOTHING_PER_SECOND * seconds
        self._share += max(-step, min(step, target - self._share))
        volume = LEVELS[self.level][1] * self._fade * self._share
        if abs(volume - self._volume_sent) > 0.002 or (volume == 0.0) != (self._volume_sent == 0.0):
            self._backend.set_volume(volume)
            self._volume_sent = volume

    def _start(self, name: str) -> bool:
        """Load a track and start it looping, silent: the fade brings it up. False if it fails."""
        assert self._backend is not None
        path = self._files.get(name)
        if path is None:
            return False
        try:
            self._backend.load(path)
            self._backend.set_volume(0.0)
            self._volume_sent = 0.0
            self._backend.play(-1)
        except Exception:  # a missing or broken file: no music, no crash
            return False
        return True

    def stop(self) -> None:
        """Stop the music at once (when the window closes)."""
        if self._backend is not None:
            with contextlib.suppress(Exception):
                self._backend.stop()
        self._current = None


def _pygame_backend() -> Backend | None:
    """Pygame's music player, or None if there is no sound card."""
    try:
        import pygame

        if not pygame.mixer.get_init():
            pygame.mixer.init()
        return pygame.mixer.music  # type: ignore[return-value]
    except Exception:
        return None
