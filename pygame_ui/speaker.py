"""Who is talking: their face in a cloud beside the dialogue box, and their name over it."""

from __future__ import annotations

import math
import time

import pygame

import world
from pygame_ui import assets
from pygame_ui.game_bridge import SpeakerChange

# the cloud a speaker's face pops up in, and the faces that go in it (assets/<who>_<mood>.png).
# Its height is this share of the window's, and it grows in and shrinks out in these many seconds
CLOUD_FILE = "speaker_cloud.png"
MOODS = ("speaking", "smiling", "upset")
HEIGHT = 0.15
IN_SECONDS = 0.3
OUT_SECONDS = 0.16
SHAKE = {"speaking": 0.6, "smiling": 0.6, "upset": 1.0}  # how hard each mood shakes

# whoever says the next lines is named above them: a boss by its own name, the backpack as below,
# anything nobody in particular says as the narrator
NARRATOR_NAME = "Narrator"
SPEAKER_NAMES = {"backpack": "Evil Backpack"}


class Speaker:
    """Who is talking right now, and the cloud that pops in and out with their face."""

    def __init__(self) -> None:
        """Load the cloud and the faces, and every boss's name."""
        self.cloud = assets.load_picture(CLOUD_FILE)
        self.faces: dict[tuple[str, str], pygame.Surface] = {}
        for mood in MOODS:
            face = assets.load_picture(f"backpack_{mood}.png")
            if face is not None:
                self.faces[("backpack", mood)] = face
        self.names = {
            room.boss.speaker: room.boss.name[:1].upper() + room.boss.name[1:]
            for room in world.all_rooms()
            if room.boss is not None and room.boss.speaker is not None
        }
        self.names.update(SPEAKER_NAMES)
        self.current: tuple[str, str] | None = None  # (who, mood) while someone is talking
        self.since = 0.0
        self.left_at: float | None = None  # when they stopped, while the cloud shrinks away
        self._face_cache: dict[tuple, pygame.Surface] = {}

    @property
    def who(self) -> str | None:
        """Who is talking, or None while nobody is (or they are on their way out)."""
        if self.current is None or self.left_at is not None:
            return None
        return self.current[0]

    @property
    def mood(self) -> str:
        """The mood of whoever is talking, or "" while nobody is."""
        return "" if self.who is None or self.current is None else self.current[1]

    def name(self) -> str:
        """The name to put over the lines being said now."""
        who = self.who
        return NARRATOR_NAME if who is None else self.names.get(who, who)

    def clear(self) -> None:
        """Forget whoever was talking at once (walking into another room leaves them behind)."""
        self.current = None

    def change(self, change: SpeakerChange) -> None:
        """Someone started talking (or swapped mood), or stopped: pop the cloud in or out."""
        now = time.monotonic()
        if change.who is None:
            if self.current is not None and self.left_at is None:
                self.left_at = now
            return
        if self.current is None or self.left_at is not None:
            self.since = now  # a fresh pop in
        self.current = (change.who, change.mood)
        self.left_at = None

    def draw(
        self, screen: pygame.Surface, box_rect: tuple[int, int, int, int], typing: bool, margin: int
    ) -> None:
        """Draw the cloud with the speaker's face in it, just left of the dialogue box."""
        if self.current is None or self.cloud is None:
            return
        face = self.faces.get(self.current)
        if face is None:
            return
        now = time.monotonic()
        if self.left_at is not None:  # shrinking away
            progress = (now - self.left_at) / OUT_SECONDS
            if progress >= 1:
                self.current = None
                self.left_at = None
                return
            grow = 1 - progress * progress
        else:  # growing in, a little past full size and back
            progress = min(1.0, (now - self.since) / IN_SECONDS)
            back = 1.70158
            grow = 1 + (back + 1) * (progress - 1) ** 3 + back * (progress - 1) ** 2

        box_x, box_y, _box_w, box_h = box_rect
        cloud_h = screen.get_height() * HEIGHT
        cloud_w = self.cloud.get_width() * cloud_h / self.cloud.get_height()
        # at rest: just left of the box, level with its middle
        rest_x = max(margin, box_x - cloud_w * 0.97)
        rest_y = box_y + box_h * 0.5 - cloud_h * 0.97
        # it grows out of its lower right, the side nearest the box
        anchor_x, anchor_y = rest_x + cloud_w * 0.8, rest_y + cloud_h * 0.78
        width = max(2, round(cloud_w * grow))
        height = max(2, round(cloud_h * grow))
        left = round(anchor_x - (anchor_x - rest_x) * grow)
        top = round(anchor_y - (anchor_y - rest_y) * grow)
        screen.blit(pygame.transform.smoothscale(self.cloud, (width, height)), (left, top))

        # the face bounces and tilts while the words are typed, and only wobbles while they sit
        # on screen. Smooth sine waves, and rotozoom rather than rotate, so the lines stay clean
        strength = SHAKE.get(self.current[1], 0.6) * (1.0 if typing else 0.25)
        shake_x = math.sin(now * 31.0) * strength * height * 0.012
        shake_y = math.sin(now * 23.0 + 1.3) * strength * height * 0.016
        tilt = math.sin(now * 17.0 + 0.6) * strength * 1.6
        face_width = max(2, round(width * 0.74))
        face_size = (face_width, max(2, round(face.get_height() * face_width / face.get_width())))
        picture = pygame.transform.rotozoom(self._scaled_face(face, face_size), tilt, 1.0)
        centre_x = left + width * 0.47 + shake_x
        centre_y = top + height * 0.47 + shake_y
        screen.blit(
            picture,
            (
                round(centre_x - picture.get_width() / 2),
                round(centre_y - picture.get_height() / 2),
            ),
        )

    def _scaled_face(self, face: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
        key = (self.current, size)
        picture = self._face_cache.get(key)
        if picture is None:
            if len(self._face_cache) > 80:
                self._face_cache.clear()
            picture = pygame.transform.smoothscale(face, size)
            self._face_cache[key] = picture
        return picture
