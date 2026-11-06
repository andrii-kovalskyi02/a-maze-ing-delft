"""The window's sound effects: the typing blips, the menu tick and the one-off cues.

The background music is ``music.py``'s job, not this file's. Every sound is optional: with no
file, or no audio device, the game just stays quiet.
"""

from __future__ import annotations

import array
import io
import math
import os
import time
import wave

import pygame

import ui
from pygame_ui import assets

# one-off sounds for moments in the game, played where ui.cue(name) is called: the file, and how
# loud it is (0 to 1). "combat" is heard as a boss's questions begin
CUE_SOUNDS = {"combat": ("combat_start.wav", 0.32), "victory": ("boss_defeated.wav", 0.32)}

# the small tick heard when the highlight moves from one choice to the next, in any menu, and the
# volumes the player can pick for it in the pause menu (it starts on Low)
MOVE_SOUND_FILE = "ui_move.wav"
MOVE_SOUND_LEVELS = (("Off", 0.0), ("Low", 0.2), ("Normal", 0.3))
MOVE_SOUND_START = 1

# the little blip heard while the story is typed out. It is a steady effect, not one sound per
# letter: it plays on its own channel, never over itself, and never closer together than GAP
# seconds. The backpack has its own sound; bosses share a tougher one, and the narrator a very
# soft one. Both are matched in loudness to the backpack's, whatever their files
TYPE_SOUND_FILE = "type_blip.wav"
TYPE_SOUND_BOSS_FILE = "type_blip_boss.wav"
TYPE_SOUND_BOSS_ATTACK = 0.016
TYPE_SOUND_NARRATOR_FILE = "type_blip_narrator.wav"
TYPE_SOUND_NARRATOR_SOFTNESS = 0.5  # this much of the backpack's loudness
TYPE_SOUND_GAP = 0.108  # seconds between blips at the normal pace
TYPE_SOUND_ATTACK = 0.04  # seconds each blip takes to swell up to full volume: longer is softer
TYPE_SOUND_VOLUME = 0.26  # the backpack's blip: the loudness the others are matched to


def load_sound(name: str, volume: float = 1.0) -> pygame.mixer.Sound | None:
    """Load a sound from assets/, or None if there is no file or no sound on this computer."""
    path = assets.path(name)
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


def load_cue_sounds() -> dict[str, pygame.mixer.Sound | None]:
    """Load every sound in CUE_SOUNDS, by its cue name."""
    return {name: load_sound(file, volume) for name, (file, volume) in CUE_SOUNDS.items()}


def wave_loudness(path: str, attack_seconds: float = TYPE_SOUND_ATTACK) -> float:
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


def shape_sound(
    path: str, seconds: float | None, attack_seconds: float = TYPE_SOUND_ATTACK
) -> pygame.mixer.Sound | None:
    """A .wav sound with a soft start, cut to ``seconds`` if given.

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
            samples[frame * channels + channel] = int(samples[frame * channels + channel] * gain)
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


def load_type_sound(
    name: str,
    like: str | None = None,
    softness: float = 1.0,
    attack: float = TYPE_SOUND_ATTACK,
) -> pygame.mixer.Sound | None:
    """Load a typing blip, or None if there is no sound file or no sound on this computer.

    With ``like`` (another file's name) the volume is set so it sounds exactly as loud as that
    file does at the normal volume, however loud this file was recorded - or ``softness`` times
    as loud, for a sound meant to be quieter.
    """
    path = assets.path(name)
    if not os.path.exists(path):
        return None
    volume = TYPE_SOUND_VOLUME
    if like is not None:
        own = wave_loudness(path, attack)
        wanted = wave_loudness(assets.path(like))
        if own > 0 and wanted > 0:
            volume = min(1.0, TYPE_SOUND_VOLUME * softness * wanted / own)
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        sound = shape_sound(path, None, attack) or pygame.mixer.Sound(path)
        sound.set_volume(volume)
        return sound
    except pygame.error:  # no audio device: the game just stays quiet
        return None


class TypingBlips:
    """The blip heard while the story is typed out, in the voice of whoever is talking."""

    def __init__(self) -> None:
        """Load the three voices: the backpack's, the bosses' and the narrator's."""
        self.voices = {
            "backpack": (load_type_sound(TYPE_SOUND_FILE), TYPE_SOUND_FILE),
            "boss": (
                load_type_sound(
                    TYPE_SOUND_BOSS_FILE, like=TYPE_SOUND_FILE, attack=TYPE_SOUND_BOSS_ATTACK
                ),
                TYPE_SOUND_BOSS_FILE,
            ),
            "narrator": (
                load_type_sound(
                    TYPE_SOUND_NARRATOR_FILE,
                    like=TYPE_SOUND_FILE,
                    softness=TYPE_SOUND_NARRATOR_SOFTNESS,
                ),
                TYPE_SOUND_NARRATOR_FILE,
            ),
        }
        self._clipped: dict[tuple[str, int], pygame.mixer.Sound] = {}
        self._channel: pygame.mixer.Channel | None = None
        self._last_blip = 0.0

    def play(self, letter: str, who: str | None, mood: str, paused: bool) -> None:
        """Play the blip for one letter just typed out, while ``who`` (None: nobody) is talking."""
        # the rhythm follows the mood of whoever is talking: quicker when upset, slower when smiling
        gap = TYPE_SOUND_GAP * ui.pace_for(who, mood if who is not None else "")
        if who == "backpack":
            voice = "backpack"
        elif who is not None:
            voice = "boss"  # a boss, or any other character with a speaker name
        else:
            voice = "narrator"
        sound = self._blip_for(voice, gap)
        if sound is None or paused or letter.isspace():
            return
        now = time.monotonic()
        if now - self._last_blip < gap:
            return
        if self._channel is None:
            self._channel = pygame.mixer.Channel(0)  # its own channel: blips never stack up
        if self._channel.get_busy():
            return  # the last blip is still sounding: wait for it to end, never overlap it
        self._last_blip = now
        self._channel.play(sound)

    def _blip_for(self, voice: str, gap: float) -> pygame.mixer.Sound | None:
        """The blip for ``voice``, cut short and faded out if it is longer than ``gap``."""
        sound, name = self.voices[voice]
        if sound is None or sound.get_length() <= gap * 0.96:
            return sound
        milliseconds = int(gap * 960)
        key = (name, milliseconds)
        clipped = self._clipped.get(key)
        if clipped is None:
            attack = TYPE_SOUND_BOSS_ATTACK if voice == "boss" else TYPE_SOUND_ATTACK
            clipped = shape_sound(assets.path(name), milliseconds / 1000, attack)
            if clipped is None:
                return sound
            clipped.set_volume(sound.get_volume())
            self._clipped[key] = clipped
        return clipped


class MenuTick:
    """The tick heard when the highlight moves to another choice, at the volume picked for it."""

    def __init__(self) -> None:
        """Load the tick (its volume is set each time it plays)."""
        self.sound = load_sound(MOVE_SOUND_FILE)
        self.level = MOVE_SOUND_START

    @property
    def level_name(self) -> str:
        """The name of the volume it is on, such as "Low"."""
        return MOVE_SOUND_LEVELS[self.level][0]

    def cycle_level(self) -> None:
        """Go on to the next volume (off, low, normal, and round again) and let it be heard."""
        self.level = (self.level + 1) % len(MOVE_SOUND_LEVELS)
        self.play()

    def play(self) -> None:
        """Play the tick, unless it is turned off."""
        volume = MOVE_SOUND_LEVELS[self.level][1]
        if self.sound is not None and volume > 0:
            self.sound.set_volume(volume)
            self.sound.play()
