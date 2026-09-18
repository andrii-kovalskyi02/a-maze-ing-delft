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
import ui
import world
from inventory import Inventory, get_item
from models import Item, Room

#: Where a new game starts (US1a).
STARTING_ROOM = "classroom_2035"

#: US1a establishes that the player starts on three hearts. Losing them is the
#: hearts enabler's job (#108); this is only where the number lives.
STARTING_HEARTS = 3

#: What the player is carrying at the start: nothing. They have no backpack
#: until the Evil Backpack becomes one in classroom 2.031 (US1c).
STARTING_ITEMS: tuple[str, ...] = ()

HOW_TO_PLAY = """\
You will not have to remember any commands. Each turn you are shown a numbered
list of what you can do right then - press the number and enter. Some lists
offer 0 to go back, and a key you press that is not on the list simply shows
the list again.

The only time you type words is when somebody asks you a question you have to
answer yourself.\
"""


@dataclass(slots=True)
class Game:
    """Everything that is true about one play-through."""

    current: str = STARTING_ROOM
    name: str = "Player"
    carrying: Inventory = field(default_factory=Inventory)
    hearts: int = STARTING_HEARTS
    visited: set[str] = field(default_factory=set)
    defeated: set[str] = field(default_factory=set)
    taken: set[tuple[str, str]] = field(default_factory=set)
    approached: set[str] = field(default_factory=set)
    running: bool = True
    #: When this play-through began, for the status command's "time played".
    #: A monotonic clock, so a system clock change mid-game cannot make it
    #: run backwards.
    started_at: float = field(default_factory=time.monotonic)

    def __post_init__(self) -> None:
        """Hand the player their starting items, if the story gives them any."""
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
        return self.carrying.add(key)

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

        if first_time and room.on_first_enter is not None:
            room.on_first_enter(self)

    def turn(self) -> None:
        """Offer the menu once, and carry out whatever the player picks."""
        menu = commands.build_menu(self)
        chosen = ui.choose("What do you do?", [item.label for item in menu])
        menu[chosen].action(self)

    def run(self) -> None:
        """Play until the player quits, or until there is no more input."""
        try:
            typed = ui.ask("What should we call you?: ")
            if typed:
                self.name = typed
        except EOFError:
            # Nobody at the keyboard even for the name - keep the default and
            # let the main loop below hit the same EOFError and end cleanly.
            pass

        ui.say(HOW_TO_PLAY)
        self.enter()
        while self.running:
            try:
                self.turn()
            except EOFError:
                ui.say()
                ui.say("There is nobody at the keyboard any more. Game over.")
                self.running = False