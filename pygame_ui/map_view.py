"""The drawn floor map, opened with M once the floor plan has been taken from the wall."""

from __future__ import annotations

import time

import pygame

import ui
from pygame_ui import assets
from pygame_ui.text import TextRenderer

# the map (assets/floor_map.png), sized to fill this much of the window
MAP_FILE = "floor_map.png"
SCREEN_FRACTION = 0.92
# the white scribble drawn over the room you are in, and the padlocks drawn over every room that
# is still locked: one picture per room, and where each goes in the folder's index.json
ROOMS_DIR = "floor_map_rooms"
LOCKS_DIR = "floor_map_locks"
# the little map in the bottom right corner that says "press M": a messy doodle, this tall as a
# share of the window. It is only shown once the plan has been taken, checked this often
ICON_FILE = "floor_map_icon.png"
ICON_HEIGHT = 0.1
ICON_CHECK_SECONDS = 0.5


class FloorMap:
    """The floor map, with where you are and what is still locked, and its corner hint."""

    def __init__(self) -> None:
        """Load the map and its overlays; with no map file, there is simply no map."""
        self.art = assets.load_picture(MAP_FILE)
        self.rooms = assets.load_positions(ROOMS_DIR)
        self.locks = assets.load_positions(LOCKS_DIR)
        self.icon_art = assets.load_picture(ICON_FILE)
        self._scaled: tuple[tuple[int, int], pygame.Surface] | None = None
        self._overlays: dict[tuple, pygame.Surface] = {}
        self._icon: pygame.Surface | None = None
        self._has_map = False
        self._has_map_checked_at = 0.0

    def draw(self, screen: pygame.Surface, text: TextRenderer, status: dict, margin: int) -> None:
        """Draw the map as big as the window allows, with how to close it underneath."""
        width, height = screen.get_size()
        hint = text.render("M or Esc: close the map", "gray")
        room_below = hint.get_height() + margin * 3
        if self.art is not None:
            art_w, art_h = self.art.get_size()
            scale = min(
                width * SCREEN_FRACTION / art_w,
                (height * SCREEN_FRACTION - room_below) / art_h,
            )
            size = (max(1, round(art_w * scale)), max(1, round(art_h * scale)))
            if self._scaled is None or self._scaled[0] != size:
                self._scaled = (size, pygame.transform.smoothscale(self.art, size))
            x = (width - size[0]) // 2
            y = (height - room_below - size[1]) // 2 + margin
            screen.blit(self._scaled[1], (x, y))

            def put(folder: str, room: str, offset: tuple[int, int]) -> None:
                picture = self._overlay(folder, room, size[0] / art_w)
                if picture is not None:
                    screen.blit(
                        picture, (x + round(offset[0] * scale), y + round(offset[1] * scale))
                    )

            here = str(status.get("room", ""))
            if here in self.rooms:  # the scribble over the room you are in
                put(ROOMS_DIR, here, self.rooms[here])
            unlocked = set(status.get("unlocked", []))
            for room, offset in self.locks.items():  # a padlock on every door still locked
                if room not in unlocked:
                    put(LOCKS_DIR, room, offset)
        screen.blit(
            hint,
            ((width - hint.get_width()) // 2, height - hint.get_height() - margin * 2),
        )

    def draw_hint(self, screen: pygame.Surface, text: TextRenderer, margin: int) -> None:
        """Draw a tiny map over an "M" in the bottom right corner, once there is a map to open."""
        now = time.monotonic()
        if now - self._has_map_checked_at > ICON_CHECK_SECONDS:
            self._has_map_checked_at = now
            status = ui.status()
            self._has_map = bool(status and status.get("has_map"))
        if not self._has_map or self.art is None:
            return
        width, height = screen.get_size()
        if self._icon is None:
            icon_height = max(8, round(height * ICON_HEIGHT))
            art = self.icon_art or self.art
            icon_width = max(8, round(art.get_width() * icon_height / art.get_height()))
            self._icon = pygame.transform.smoothscale(art, (icon_width, icon_height))
        key = text.render("M", "white", True)
        icon = self._icon
        column = max(icon.get_width(), key.get_width())
        right = width - margin * 2
        key_y = height - margin * 2 - key.get_height()
        icon_y = key_y - icon.get_height() - margin // 2
        screen.blit(icon, (right - (column + icon.get_width()) // 2, icon_y))
        screen.blit(key, (right - (column + key.get_width()) // 2, key_y))

    def _overlay(self, folder: str, room: str, scale: float) -> pygame.Surface | None:
        """``room``'s picture from ``folder``, scaled like the map is, or None if there is none."""
        key = (folder, room, round(scale, 4))
        picture = self._overlays.get(key)
        if picture is None:
            original = assets.load_picture(folder, room + ".png")
            if original is None:
                return None
            size = (
                max(1, round(original.get_width() * scale)),
                max(1, round(original.get_height() * scale)),
            )
            picture = pygame.transform.smoothscale(original, size)
            self._overlays[key] = picture
        return picture
