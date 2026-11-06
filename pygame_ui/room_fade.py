"""Walking into another room: the old room fades to black, and the new one fades in.

The game waits through all of it (see TerminalWindow.start_fade), so the new room's text only
starts once its picture is fully there.
"""

from __future__ import annotations

import time

import pygame

TIMES = (0.45, 0.12, 0.65)  # seconds: fading out, staying black, fading in
FIRST_TIMES = (1.0, 0.6, 3.5)  # the very first room of a game: a long, slow fade in


class RoomFade:
    """One room change at a time: when it started, and how dark the screen is now."""

    def __init__(self) -> None:
        """No room change going on yet."""
        self.started: float | None = None
        self.snapshot: pygame.Surface | None = None  # the old room, as it last looked
        self._times = TIMES
        self._cover: pygame.Surface | None = None

    @property
    def active(self) -> bool:
        """Whether a room change is going on."""
        return self.started is not None

    def start(self, snapshot: pygame.Surface, first: bool) -> None:
        """Begin fading out of ``snapshot``, the room on screen."""
        self.snapshot = snapshot
        self._times = FIRST_TIMES if first else TIMES
        self.started = time.monotonic()

    def stop(self) -> None:
        """Drop the room change."""
        self.started = None
        self.snapshot = None

    def phase(self) -> tuple[str, float]:
        """Where the change is now: ("leaving", darkness), ("arriving", darkness) or ("done", 0).

        Darkness goes from 0 (the picture as it is) to 1 (black).
        """
        assert self.started is not None
        elapsed = time.monotonic() - self.started
        fade_out, hold, fade_in = self._times
        light_at = fade_out + hold
        if elapsed < fade_out and self.snapshot is not None:
            return "leaving", elapsed / fade_out
        if elapsed >= light_at + fade_in:
            return "done", 0.0
        return "arriving", 1.0 if elapsed < light_at else 1.0 - (elapsed - light_at) / fade_in

    def darken(self, screen: pygame.Surface, darkness: float) -> None:
        """Lay black over ``screen``, from 0 (none) to 1 (all black)."""
        if self._cover is None or self._cover.get_size() != screen.get_size():
            self._cover = pygame.Surface(screen.get_size())
            self._cover.fill((0, 0, 0))
        self._cover.set_alpha(round(255 * max(0.0, min(1.0, darkness))))
        screen.blit(self._cover, (0, 0))
