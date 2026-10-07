"""The game itself: the player's state and the one main loop (enabler #92).

There is exactly one loop in this project and it is here. Rooms never call
``input``, never print a menu and never loop; they describe themselves and the
engine does the rest. That is what lets six people build rooms at the same
time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import commands
import narrator
import persistence
import ui
import world
from health import Health
from inventory import Inventory, get_item
from models import Item, Room

#: Where a new game starts (US1a).
STARTING_ROOM = "classroom_2035"

#: US1a establishes that the player starts on three hearts. How they are spent
#: is in ``health.py`` (#108); this is the number the story gives them.
STARTING_HEARTS = 3

#: What the player reads when the last heart goes (#108, E5.3). The team's
#: decision: running out ends the run. Hearts are worth something only if
#: losing them costs the play-through.
OUT_OF_HEARTS = """\
Your last heart goes out.

The corridor tilts, the alarm thins to nothing, and the floor of the 2nd floor
of THUAS Delft comes up to meet you. Whatever this building is, it is finished
with you for tonight.\
"""

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
the typing off altogether.\
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
    #: When this play-through began, for the status command's "time played".
    #: A monotonic clock, so a system clock change mid-game cannot make it
    #: run backwards.
    started_at: float = field(default_factory=time.monotonic)
    _session_started: float = field(
        default_factory=time.monotonic,
        repr=False,
        compare=False,
    )
    percent_explored: float = 0

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

    def items_here(self) -> tuple[Item, ...]:
        """Return the items still lying in this room, un-taken."""
        return tuple(
            get_item(key) for key in self.room.items if (self.current, key) not in self.taken
        )

    def take(self, key: str) -> Item:
        """Move the item ``key`` from this room into what the player carries."""
        self.taken.add((self.current, key))
        item = self.carrying.add(key)
        narrator.remark(self, "took", what=item.name)
        return item

    def move_to(self, key: str) -> None:
        """Walk into the room ``key`` and let it introduce itself."""
        self.current = key
        self.enter()

    def enter(self) -> None:
        """Print the current room, and run whatever happens on arrival."""
        room = self.room
        first_time = room.key not in self.visited
        self.visited.add(room.key)

        ui.say()
        ui.say(f"== {room.name} ==")
        ui.narrate(room.description)
        if not first_time:
            ui.say("You have been here before.")
            if not room.is_hallway:
                narrator.remark(self, "backtrack")

        if first_time and room.on_first_enter is not None:
            room.on_first_enter(self)

    def update_elapsed_time(self) -> None:
        """Add the current session duration to the total play time."""
        now = time.monotonic()
        self.elapsed_time += now - self._session_started
        self._session_started = now

    def pause(self) -> None:
        """Save the game and stop the current play session."""
        from persistence import save_game

        self.update_elapsed_time()
        save_game(self)
        self.running = False

    def finish(self) -> None:
        """End the game: the player has walked out of the building (US1e).

        Shows the final status so the player sees how much of the floor they
        explored. Writing the run to the scoreboard belongs to the
        persistence enabler (#121).
        """
        ui.say()
        ui.say("You are out of the building. Fresh air, at last.")
        commands.do_status(self)
        self.update_elapsed_time()
        persistence.save_score(self.name, commands.percent_explored(self), self.elapsed_time)
        commands.do_scoreboard(self)
        self.running = False

    def turn(self) -> None:
        """Offer the menu once, and carry out whatever the player picks."""
        menu = commands.build_menu(self)
        chosen = ui.choose("What do you do?", [item.label for item in menu])
        menu[chosen].action(self)
        self._collapse_if_out_of_hearts()

    def _collapse_if_out_of_hearts(self) -> None:
        """End the run if the last heart has gone (#108, E5.3).

        Checked here, after whatever the player just did, rather than inside
        the encounter engine: one place notices, so anything that costs a
        heart later - a trap, a timer, a fall - ends the game the same way
        without having to remember to.
        """
        if self.hearts.is_empty and self.running:
            ui.say()
            ui.narrate(OUT_OF_HEARTS)
            self.running = False

    def run(self) -> None:
        """Play until the player quits, pauses, or until there is no more input."""
        ui.set_pause_handler(self.pause)
        ui.set_scoreboard_handler(lambda: commands.do_scoreboard(self))

        try:
            ui.say(HOW_TO_PLAY)
            self.enter()

            while self.running:
                try:
                    self.turn()
                except ui.PauseRequested:
                    ui.say()
                    ui.say("Game saved. See you next time!")
                    self.running = False
                except EOFError:
                    ui.say()
                    ui.say("There is nobody at the keyboard any more. Game over.")
                    self.running = False
        finally:
            ui.set_pause_handler(None)
            ui.set_scoreboard_handler(None)
