"""The game itself: the player's state and the one main loop (enabler #92).

Rooms never call ``input``, print a menu or loop; they describe themselves and the engine does
the rest.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, fields

import commands
import digits
import narrator
import persistence
import progress
import ui
import world
from health import Health, OutOfHearts
from inventory import Inventory, get_item
from leaderboard import online, scoreboard
from models import Item, Room

#: Where a new game starts (US1a).
STARTING_ROOM = "classroom_2035"

#: The hearts a new game starts with (US1a). How they are spent is in ``health.py``.
STARTING_HEARTS = 3

#: What the player reads when the last heart goes (#108, E5.3). They are then
#: sent back to their last save, or to the very start if they have none.
OUT_OF_HEARTS = (
    "Your last heart goes out.",
    "The corridor tilts, the lights thin to nothing, and the floor of the 2nd floor of "
    "THUAS Delft comes up to meet you. Whatever this building is, it is finished with you "
    "for tonight.",
)

#: What the player reads when they wake up at their last save instead (#217).
BACK_AT_THE_SAVE = (
    "...and then you are standing up again, a little earlier, a little further back, with "
    "every heart back where it belongs. The building is not finished with you after all."
)

#: What the player reads when they had no save and wake up at the very start instead.
BACK_AT_THE_START = (
    "...and then you are waking up again, cheek on the desk, as if the whole night has not "
    "happened yet. The building is not finished with you after all."
)

#: What is not rolled back when the player is sent back to their last save:
#: who they are, and how long they have been playing - time spent is spent.
_KEPT_ON_RESPAWN = {"player_name", "name", "elapsed_time", "started_at", "running"}

#: What the player is carrying at the start: nothing. They have no backpack
#: until the Evil Backpack becomes one in classroom 2.031 (US1c).
STARTING_ITEMS: tuple[str, ...] = ()

HOW_TO_PLAY = """\
You will not have to remember any commands. Each turn you are shown a numbered
list of what you can do right then - press the number and enter. Some lists
offer 0 to go back, and a key you press that is not on the list simply shows
the list again.

The only time you type words is when somebody asks you a question you have to
answer yourself. Some of those questions are timed, and you have three hearts
to lose before the building is finished with you.

The story is typed out a letter at a time. Press Enter while it is typing and
the rest of it appears at once - handy the second time round. Options can turn
the typing off altogether.

Three words work at any prompt, even in the middle of a fight: pause (save and
come back later), quit (stop without saving), and leaderboard.\
"""


@dataclass(slots=True)
class Game:
    """Everything that is true about one play-through."""

    player_name: str = ""
    current: str = STARTING_ROOM
    name: str = "Player"
    carrying: Inventory = field(default_factory=Inventory)
    hearts: Health = field(default_factory=Health)
    visited: set[str] = field(default_factory=set)
    defeated: set[str] = field(default_factory=set)
    taken: set[tuple[str, str]] = field(default_factory=set)
    approached: set[str] = field(default_factory=set)
    unlocked: set[str] = field(default_factory=set)
    #: How many times the backpack has had something to say about each kind
    #: of event, so it can keep quiet most of the time - see narrator.py.
    heard: dict[str, int] = field(default_factory=dict)
    #: How many times each door has refused the player, so the backpack can
    #: notice them rattling the same handle (#103).
    refused: dict[str, int] = field(default_factory=dict)
    running: bool = True
    #: Time played in earlier sessions, carried over by a saved game (US3).
    elapsed_time: float = 0.0
    #: When this session began. A monotonic clock, so a system clock change
    #: mid-game cannot make it run backwards.
    started_at: float = field(default_factory=time.monotonic)
    percent_explored: float = 0
    #: True for the first arrival of a game that was loaded from a save. The backpack,
    #: if the player has it, greets them instead of the room describing itself again.
    resumed: bool = False
    #: True once the player has looked around in the room they are in. The next "Look around"
    #: becomes "Interact" and skips the telling. It starts again in every room they walk into.
    looked_around: bool = False
    #: The number (from 0) of the boss question being asked right now, or None outside a
    #: fight. Saved with the game, so a game saved mid-question resumes on that question.
    in_question: int | None = None

    def __post_init__(self) -> None:
        """Use the name the player logged in with, and hand them their starting items."""
        if self.player_name:
            self.name = self.player_name
        for key in STARTING_ITEMS:
            self.carrying.add(key)

    @property
    def room(self) -> Room:
        """The room the player is standing in."""
        return world.get(self.current)

    def has_taken(self, key: str) -> bool:
        """Return True if the player has picked up the item ``key``, here or anywhere."""
        return key in self.carrying or any(item == key for _, item in self.taken)

    def items_here(self) -> tuple[Item, ...]:
        """Return the items still lying in this room, un-taken."""
        return tuple(
            get_item(key) for key in self.room.items if (self.current, key) not in self.taken
        )

    async def take(self, key: str) -> Item:
        """Move the item ``key`` from this room into what the player carries."""
        self.taken.add((self.current, key))
        item = self.carrying.add(key)
        await narrator.remark(self, "took", what=item.name)
        return item

    async def move_to(self, key: str) -> None:
        """Walk into the room ``key`` and let it introduce itself."""
        self.current = key
        self.looked_around = False
        await self.enter()

    async def enter(self) -> None:
        """Print the current room, and run whatever happens on arrival."""
        room = self.room
        first_time = room.key not in self.visited
        self.visited.add(room.key)

        await ui.say()
        await ui.say(f"== {room.name} ==")
        if self.resumed:
            self.resumed = False
            if narrator.BACKPACK in self.carrying:
                await self._greet_back(room)
                return
        if first_time:
            await ui.narrate(room.description)
        elif room.return_description is not None:  # a room with nothing to say again says nothing
            await ui.narrate(room.return_description)
        if not first_time:
            await ui.say("You have been here before.")
            if not room.is_hallway:
                await narrator.remark(self, "backtrack")

        if first_time and room.on_first_enter is not None:
            await room.on_first_enter(self)

    async def _greet_back(self, room: Room) -> None:
        """The backpack welcomes the player back to the room they saved in."""
        place = room.name
        if place.startswith("The "):
            place = "the " + place[4:]  # "in the Blue corridor", not "in The Blue corridor"
        with ui.speaking(narrator.BACKPACK, "speaking"):
            await ui.narrate(f'"Right where you left off... in {place}."')

    def update_elapsed_time(self) -> None:
        """Add the current session duration to the total play time."""
        now = time.monotonic()
        self.elapsed_time += now - self.started_at
        self.started_at = now

    def time_played(self) -> float:
        """Return the total time played, earlier sessions included (US3)."""
        return self.elapsed_time + time.monotonic() - self.started_at

    def hold_time(self, seconds: float) -> None:
        """Take ``seconds`` off the time played: the game sat in the pause menu that long."""
        self.started_at += seconds

    def status(self) -> dict[str, object]:
        """Return what the window shows: name, progress and whether there is a map."""
        return {
            "name": self.name,
            "has_map": "evacuation_plan" in self.carrying,
            "room": self.current,
            "unlocked": sorted(self.unlocked),
            "hearts": str(self.hearts),
            "seconds": self.time_played(),
            "percent": progress.percent_explored(self),
        }

    def save(self) -> None:
        """Write the game to the database and carry on playing."""
        self.update_elapsed_time()
        persistence.save_game(self)

    def pause(self) -> None:
        """Save the game and stop the current play session."""
        self.save()
        self.running = False

    async def finish(self) -> None:
        """End the game: the player has walked out of the building (US1e).

        Shows the final status so the player sees how much of the floor they
        explored, puts the run on the scoreboard (and the shared one, if it is set up), and
        shows it (US5). The save is removed, so a finished run cannot be resumed and finished
        again.
        """
        await ui.say()
        await ui.say("You are out of the building. Fresh air, at last.")
        await commands.do_status(self)
        self.update_elapsed_time()
        percent = progress.percent_explored(self)
        persistence.record_score(self.name, percent, self.elapsed_time)
        if online.enabled():
            await ui.say("Your time is going on the shared leaderboard.")
        online.submit(self.name, percent, self.elapsed_time)
        persistence.delete_save(self.player_name)
        await scoreboard.show()
        self.running = False

    async def turn(self) -> None:
        """Offer the menu once, and carry out whatever the player picks."""
        digits_before = len(digits.carried(self))
        if self.in_question is not None:
            await commands.back_into_the_fight(self)  # saved mid-question: straight back to it
        else:
            menu = commands.build_menu(self)
            chosen = await ui.choose("What do you do?", [item.label for item in menu])
            await menu[chosen].action(self)
        if self.running and len(digits.carried(self)) > digits_before:
            await self.autosave()

    async def autosave(self) -> None:
        """Save without stopping, so a digit once found is never lost (#216).

        Checked once per turn rather than wherever a digit is handed out, so any new way of
        handing one out is covered too.
        """
        self.update_elapsed_time()
        persistence.save_game(self)
        await ui.say()
        await ui.say("Digit found - your progress has been saved.")

    async def collapse(self) -> None:
        """The last heart has gone (#108, E5.3, #217).

        Called by the main loop the moment :class:`~health.OutOfHearts` is
        raised, wherever that heart was lost. If the player has a save, they
        are sent back to it on full hearts, so dying costs the progress since
        then rather than the whole run. Without one, they start the game over.
        """
        await ui.say()
        await ui.narrate(OUT_OF_HEARTS)
        saved = persistence.load_game(self.player_name) if self.player_name else None
        woke_up_to = BACK_AT_THE_SAVE
        if saved is None:
            saved = Game(player_name=self.player_name)
            woke_up_to = BACK_AT_THE_START

        for each in fields(self):
            if each.name not in _KEPT_ON_RESPAWN:
                setattr(self, each.name, getattr(saved, each.name))
        self.hearts = Health()
        self.update_elapsed_time()
        if self.player_name:
            persistence.save_game(self)
        await ui.say()
        await ui.narrate(woke_up_to)
        await self.enter()

    async def quit(self) -> None:
        """End the run without saving it (US2)."""
        await ui.say()
        await ui.say("You step away from the building. Game over.")
        self.running = False

    async def run(self) -> None:
        """Play until the player quits, pauses, or until there is no more input."""
        ui.set_pause_handler(self.pause)
        ui.set_quit_handler(commands.confirm_quit)
        ui.set_scoreboard_handler(scoreboard.show)
        ui.set_status_provider(self.status)
        ui.set_time_hold_handler(self.hold_time)
        ui.set_save_handler(self.save)

        try:
            await ui.say(HOW_TO_PLAY)
            await self.enter()

            while self.running:
                try:
                    await self.turn()
                except ui.PauseRequested:
                    await ui.say()
                    await ui.say("Game saved. See you next time!")
                    self.running = False
                except ui.QuitRequested:
                    await self.quit()
                except OutOfHearts:
                    await self.collapse()
                except EOFError:
                    await ui.say()
                    await ui.say("There is nobody at the keyboard any more. Game over.")
                    self.running = False
        finally:
            ui.set_pause_handler(None)
            ui.set_quit_handler(None)
            ui.set_scoreboard_handler(None)
            ui.set_status_provider(None)
            ui.set_time_hold_handler(None)
            ui.set_save_handler(None)
