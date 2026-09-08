"""The game itself: the player's state and the one main loop (enabler #92).

There is exactly one command loop in this project and it is here.  Rooms never
call ``input`` and never loop; they describe themselves and the engine does the
rest.  That is what lets six people build rooms at the same time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from amazing_delft import commands, encounters, help_text, parser, ui, world
from amazing_delft.backpack import Backpack, get_item
from amazing_delft.models import Item, Room

#: Where a new game starts.
STARTING_ROOM = "classroom_2035"

#: What the player is handed before they take a single step.
STARTING_ITEMS: tuple[str, ...] = ("note",)


@dataclass(slots=True)
class Game:
    """Everything that is true about one play-through."""

    current: str = STARTING_ROOM
    backpack: Backpack = field(default_factory=Backpack)
    visited: set[str] = field(default_factory=set)
    defeated: set[str] = field(default_factory=set)
    taken: set[tuple[str, str]] = field(default_factory=set)
    running: bool = True

    def __post_init__(self) -> None:
        """Hand the player their starting items."""
        for key in STARTING_ITEMS:
            self.backpack.add(key)

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
        """Move the item ``key`` from this room into the backpack."""
        self.taken.add((self.current, key))
        return self.backpack.add(key)

    def available_conditionals(self) -> frozenset[str]:
        """Return the conditional commands that work right now."""
        available = set()
        if self.items_here():
            available.add("take")
        return frozenset(available)

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
        ui.say(room.description)

        if first_time and room.on_first_enter is not None:
            room.on_first_enter(self)

        undefeated_boss = room.boss is not None and room.key not in self.defeated
        if undefeated_boss and encounters.run(self, room.boss):
            self.defeated.add(room.key)

    def step(self, raw: str) -> None:
        """Act on one line of player input."""
        command = parser.parse(raw)
        if command is None:
            ui.say("You cannot do that. Type '?' to see what you can do.")
            return
        commands.HANDLERS[command.verb](self, command.argument)

    def run(self) -> None:
        """Play until the player quits."""
        ui.say(help_text.render(self.available_conditionals()))
        self.enter()
        while self.running:
            self.step(ui.ask("\n> "))
