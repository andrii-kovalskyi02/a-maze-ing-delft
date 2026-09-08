"""What each command actually does (enabler #92).

Every command is a small function taking the running game and whatever the
player typed after the verb.  Adding a command means writing one function and
adding one line to :data:`HANDLERS` - and one line to
``amazing_delft/help_text.py`` so the player finds out about it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from amazing_delft import floor_map, help_text, ui, world

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from amazing_delft.game import Game


def do_look_around(game: Game, argument: str) -> None:
    """Describe the room, its exits and anything lying around."""
    room = game.room
    ui.say()
    ui.say(room.look_around)

    remaining = game.items_here()
    if remaining:
        names = ", ".join(item.name for item in remaining)
        ui.say(f"You could take: {names}.")
    if room.inspectables:
        names = ", ".join(thing.name for thing in room.inspectables)
        ui.say(f"Worth a closer look: {names}.")
    ui.say(f"Doors lead to: {_exit_names(game)}.")


def do_go(game: Game, argument: str) -> None:
    """Walk to another room, if there is a door and it opens."""
    if not argument:
        ui.say(f"Go where? Doors lead to: {_exit_names(game)}.")
        return

    destination = world.find(argument)
    if destination is None:
        ui.say(f"There is no '{argument}' in this building.")
        return
    if destination.key not in game.room.exits:
        ui.say(f"You cannot get to {destination.name} from here.")
        ui.say(f"Doors lead to: {_exit_names(game)}.")
        return
    if not world.can_enter(destination, game.backpack):
        ui.say(destination.locked_text)
        return

    game.move_to(destination.key)


def do_inspect(game: Game, argument: str) -> None:
    """Look closely at something in the room or in the backpack."""
    if not argument:
        ui.say("Inspect what?")
        return

    thing = game.room.find_inspectable(argument)
    if thing is not None:
        ui.say(thing.text)
        return

    carried = game.backpack.find(argument)
    if carried is not None:
        ui.say(carried.description)
        if carried.key == "note":
            ui.say(help_text.render(game.available_conditionals()))
        return

    ui.say(f"There is no '{argument}' here, and you are not carrying one.")


def do_take(game: Game, argument: str) -> None:
    """Pick something up off the floor, a desk, or a teacher."""
    if not argument:
        ui.say("Take what?")
        return

    for item in game.items_here():
        if argument in (item.key, item.name.casefold()):
            game.take(item.key)
            ui.say(f"You take the {item.name}.")
            return
    ui.say(f"There is no '{argument}' here to take.")


def do_backpack(game: Game, argument: str) -> None:
    """List what the player is carrying."""
    ui.say(game.backpack.describe())


def do_map(game: Game, argument: str) -> None:
    """Show the plan of the 2nd floor."""
    ui.say(floor_map.render(game))


def do_help(game: Game, argument: str) -> None:
    """Reprint the note that came in the backpack."""
    ui.say(help_text.render(game.available_conditionals()))


def do_options(game: Game, argument: str) -> None:
    """Scoreboard, saving and quitting."""
    ui.say("Options: save and the scoreboard are not built yet (issue #121).")
    ui.say("Type 'quit' to stop playing.")


def do_quit(game: Game, argument: str) -> None:
    """Stop playing."""
    ui.say("You step away from the building. Game over.")
    game.running = False


def do_answer(game: Game, argument: str) -> None:
    """Explain that there is nothing to answer right now."""
    ui.say("Nobody has asked you anything.")


#: Which function runs for which verb from :data:`amazing_delft.parser.VERBS`.
HANDLERS: dict[str, Callable[[Game, str], None]] = {
    "look around": do_look_around,
    "go": do_go,
    "inspect": do_inspect,
    "take": do_take,
    "backpack": do_backpack,
    "map": do_map,
    "help": do_help,
    "options": do_options,
    "quit": do_quit,
    "answer": do_answer,
}


def _exit_names(game: Game) -> str:
    """Return the names of the rooms reachable from where the player stands."""
    return ", ".join(room.name for room in world.exits_of(game.room)) or "nowhere"
