"""The menu the player picks from, and what each choice does.

The player never types a command. Every turn they are shown a numbered list of
what they can do *right now*, and they press a number.

The list is short on purpose. It is built from what the player has actually
earned, so the opening room offers only what the story gives them: look
around, and walk out of the door. The backpack appears once they have one
(US1c) and the map appears once they have taken the evacuation plan (US1b).

Looking around leads to interacting with what is in the room - the objects,
anything worth taking, and whatever is waiting for them - as the design doc
puts it: `look around -> interact <item, boss>`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import encounters
import floor_map
import ui
import world

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from game import Game
    from models import Room


@dataclass(frozen=True, slots=True)
class MenuItem:
    """One line of a menu.

    Args:
        label: What the player reads next to the number.
        action: What happens when they pick it.
    """

    label: str
    action: Callable[[Game], None]


def do_look_around(game: Game) -> None:
    """Describe the room, then offer whatever is in it."""
    ui.say()
    ui.say(game.room.look_around)
    _offer_interactions(game)


def do_go(game: Game) -> None:
    """Offer the doors out of this room, and walk through the chosen one."""
    doors = world.exits_of(game.room)
    chosen = ui.choose("Which door?", [_door_label(game, d) for d in doors], back="Stay here")
    if chosen is None:
        return

    destination = doors[chosen]
    if not world.can_enter(destination, game.carrying):
        ui.say()
        ui.say(destination.locked_text)
        return

    game.move_to(destination.key)


def do_backpack(game: Game) -> None:
    """List what the player carries, and let them look at any of it."""
    carried = list(game.carrying)
    chosen = ui.choose(
        "You are carrying:", [item.name for item in carried], back="Close the backpack"
    )
    if chosen is not None:
        ui.say()
        ui.say(carried[chosen].description)


def do_map(game: Game) -> None:
    """Show the plan of the 2nd floor."""
    ui.say()
    ui.say(floor_map.render(game))


def do_options(game: Game) -> None:
    """Offer the things that are not part of the story."""
    chosen = ui.choose(
        "Options:",
        ["Scoreboard", "Save and continue later", "Quit the game"],
        back="Back to the game",
    )
    if chosen == 0:
        ui.say()
        ui.say("The scoreboard is not built yet (issue #121).")
    elif chosen == 1:
        ui.say()
        ui.say("Saving is not built yet (issue #121).")
    elif chosen == 2:
        do_quit(game)


def do_quit(game: Game) -> None:
    """Stop playing."""
    ui.say()
    ui.say("You step away from the building. Game over.")
    game.running = False


def build_menu(game: Game) -> tuple[MenuItem, ...]:
    """Return the menu for this turn.

    Only what the player has earned is offered, so they are never shown a
    choice that would just tell them they cannot do it yet.
    """
    items = [MenuItem("Look around", do_look_around)]

    if game.room.exits:
        items.append(MenuItem("Go through a door", do_go))
    if "backpack" in game.carrying:
        items.append(MenuItem("Open your backpack", do_backpack))
    if "evacuation_plan" in game.carrying:
        items.append(MenuItem("Look at the evacuation plan", do_map))

    items.append(MenuItem("Options", do_options))
    return tuple(items)


def _offer_interactions(game: Game) -> None:
    """Offer everything in this room worth touching, until the player is done."""
    while True:
        actions = _interactions(game)
        if not actions:
            return

        chosen = ui.choose(
            "What do you do?", [action.label for action in actions], back="Nothing, for now"
        )
        if chosen is None:
            return
        actions[chosen].action(game)


def _interactions(game: Game) -> tuple[MenuItem, ...]:
    """Return what is in this room right now: objects, items, and any boss."""
    actions = [
        MenuItem(f"Look at {thing.name}", _inspect(thing.name)) for thing in game.room.inspectables
    ]
    actions += [MenuItem(f"Take the {item.name}", _take(item.key)) for item in game.items_here()]

    boss = game.room.boss
    if boss is not None and game.room.key not in game.defeated:
        actions.append(MenuItem(f"Get closer to {boss.name}", _fight(game.room)))
    return tuple(actions)


def _inspect(name: str) -> Callable[[Game], None]:
    """Return an action that reads out the object called ``name``."""

    def action(game: Game) -> None:
        for thing in game.room.inspectables:
            if thing.name == name:
                ui.say()
                ui.say(thing.text)
                return

    return action


def _take(key: str) -> Callable[[Game], None]:
    """Return an action that picks up the item called ``key``."""

    def action(game: Game) -> None:
        item = game.take(key)
        ui.say()
        ui.say(f"You take the {item.name}.")

    return action


def _fight(room: Room) -> Callable[[Game], None]:
    """Return an action that starts ``room``'s boss encounter."""

    def action(game: Game) -> None:
        if room.boss is None:
            return
        won = encounters.run(game, room.boss)
        if won or room.boss.single_attempt:
            game.defeated.add(room.key)

    return action


def _door_label(game: Game, door: Room) -> str:
    """Name a door, saying whether the player has been through it before."""
    if door.key in game.visited:
        return f"{door.name} (you have been there)"
    return door.name