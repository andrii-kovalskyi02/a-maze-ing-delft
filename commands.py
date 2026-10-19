"""The menu the player picks from, and what each choice does.

The player never types a command. Every turn they are shown a numbered list of
what they can do *right now*, and they press a number.

The list is short on purpose. It is built from what the player has actually
earned, so the opening room offers only what the story gives them: look
around, and walk out of the door. The backpack appears once they have one
(US1c) and the map appears once they have taken the floor plan (US1b).

Looking around leads to interacting with what is in the room - the objects,
anything worth taking, and whatever is waiting for them - as the design doc
puts it: `look around -> interact <item, boss>`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import digits
import encounters
import floor_map
import models
import narrator
import progress
import scoreboard
import ui
import world
from inventory import get_item

if TYPE_CHECKING:  # pragma: no cover - import only needed for type checking
    from game import Game
    from models import Room


@dataclass(frozen=True, slots=True)
class MenuItem:
    """One line of a menu.

    Args:
        label: What the player reads next to the number.
        action: What happens when they pick it.
        ends_interaction: If True, choosing this backs straight out to the
            main "Look around / Go through a door" menu afterwards, instead
            of asking "What do you do?" again. Use this for an action that
            naturally finishes the "look around" moment, like taking an item.
    """

    label: str
    action: Callable[[Game], None]
    ends_interaction: bool = False


def do_look_around(game: Game) -> None:
    """Describe the room, if it has anything to describe, then offer what is in it."""
    if game.room.look_around is not None:
        told = models.resolve(game.room.look_around, game.has_taken)
        if told:
            ui.say()
            ui.narrate(told)
    _offer_interactions(game)


def do_go(game: Game) -> None:
    """Offer the doors out of this room, and walk through the chosen one."""
    doors = world.exits_of(game.room)
    chosen = ui.choose("Which door?", [_door_label(game, d) for d in doors], back="Stay here")
    if chosen is None:
        return

    destination = doors[chosen]
    if game.items_here():
        narrator.remark(game, "left_behind")

    if destination.approach_reward is not None and destination.key not in game.approached:
        game.approached.add(destination.key)
        item = game.carrying.add(destination.approach_reward)
        # The story first, then the plain fact: the player reads what they
        # found before being told it is in their pocket.
        ui.new_page()  # picking something up is a moment of its own
        if destination.approach_reward_text is not None:
            ui.say()
            ui.narrate(destination.approach_reward_text)
        ui.say()
        ui.narrate(f"You are now carrying the {item.name}.")
        ui.new_page()

    if destination.is_exit and not _code_opens_the_exit(game, destination):
        return

    if not world.can_enter(destination, game.carrying, game.unlocked):
        ui.say()
        ui.say(destination.locked_text)
        # The backpack only notices the player rattling the same handle, not
        # an honest first attempt at a door they have never tried (#103).
        tries = game.refused.get(destination.key, 0) + 1
        game.refused[destination.key] = tries
        if tries > 1:
            narrator.remark(game, "locked_again")
        return

    if destination.requires is not None and destination.key not in game.unlocked:
        item = get_item(destination.requires)
        if item.single_use:
            game.carrying.consume(destination.requires)
        if destination.requires in ("red_card", "yellow_card"):
            ui.say()
            ui.narrate(
                f"You hold the {item.name} up to the reader. "
                f"It beeps, and the door to {destination.name} slides open."
            )
        game.unlocked.add(destination.key)

    game.move_to(destination.key)
    if destination.is_exit:
        game.finish()


def _code_opens_the_exit(game: Game, door: Room) -> bool:
    """Key the digits the player has into the exit door (enabler #116).

    The player never types the code: they key in what they are carrying, which
    is why finding the digits is the game and typing them is not.
    """
    if digits.opens_the_door(game):
        ui.say()
        ui.narrate(f"You key in {digits.assemble(game)}. The lock gives.")
        return True

    ui.say()
    ui.say(door.locked_text)
    ui.say(digits.summary(game))
    return False


def do_backpack(game: Game) -> None:
    """List what the player carries, and let them look at any of it."""
    carried = list(game.carrying)
    if digits.carried(game):
        ui.say()
        ui.say(digits.summary(game))
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


def options_menu(game: Game) -> tuple[MenuItem, ...]:
    """Return the Options menu: everything that is not part of the story.

    Built as data, like every other menu here, so a test can find "Quit" by
    name instead of counting lines, and adding a choice breaks nothing.
    """
    return (
        MenuItem("Status", do_status),
        MenuItem("Scoreboard", scoreboard.show),
        MenuItem(_text_speed_label(), do_text_speed),
        MenuItem("Save and continue later", _save_and_continue),
        MenuItem("Quit the game", do_quit),
    )


def _save_and_continue(game: Game) -> None:
    """Save the current game and leave it for later."""
    game.pause()
    ui.say()
    ui.say("Game saved. See you next time!")


def do_options(game: Game) -> None:
    """Offer the things that are not part of the story."""
    menu = options_menu(game)
    chosen = ui.choose("Options:", [item.label for item in menu], back="Back to the game")
    if chosen is not None:
        menu[chosen].action(game)


def _not_built_yet(what: str, issue: int) -> Callable[[Game], None]:
    """Return an action that says ``what`` is still somebody's open issue."""

    def action(game: Game) -> None:
        ui.say()
        ui.say(f"{what} is not built yet (issue #{issue}).")

    return action


def _text_speed_label() -> str:
    """Name the text-speed choice after what picking it would do."""
    return "Type the story out again" if ui.is_instant() else "Show the story instantly"


def do_text_speed(game: Game) -> None:
    """Turn the typing animation off, or back on (issue #151).

    A player on their second or third run has read all of this already. One
    choice here spares them pressing Enter through every room.
    """
    ui.set_instant(not ui.is_instant())
    ui.say()
    ui.say(
        "The story will appear instantly from now on."
        if ui.is_instant()
        else "The story will be typed out again."
    )


def do_status(game: Game) -> None:
    """Show what the player has earned so far (Project Guide 3.1).

    Read-only: it looks at ``game`` but never changes it, so it costs nothing
    to check - no turn, no heart, no matter how the hearts enabler (#108)
    ends up spending those elsewhere.
    """
    percent = progress.percent_explored(game)
    played = progress.format_duration(game.time_played())
    digits_had, digits_total = len(digits.carried(game)), len(digits.all_digits())

    ui.say()
    ui.say(f"{game.name} - {played} played - {percent}% of the floor explored.")
    ui.say(f"Hearts: {game.hearts}   Digits: {digits_had}/{digits_total}")


def do_quit(game: Game) -> None:
    """Stop playing after confirming with the player."""
    if confirm_quit():
        game.quit()


def confirm_quit() -> bool:
    """Ask the player whether they really want to quit, and return their answer.

    Used by Options -> Quit and by typing ``quit`` at any prompt (US2).
    """
    chosen = ui.choose(
        "Are you sure you want to quit? Any progress from this run will be lost.",
        ["Quit the game", "Keep playing"],
    )
    return chosen == 0


def build_menu(game: Game) -> tuple[MenuItem, ...]:
    """Return the menu for this turn.

    Only what the player has earned is offered, so they are never shown a
    choice that would just tell them they cannot do it yet.
    """
    items: list[MenuItem] = []
    # A room with no look_around text (a staircase you only pass through) only
    # offers "Look around" while there is still something in it to interact with.
    if game.room.look_around is not None or _interactions(game):
        items.append(MenuItem("Look around", do_look_around))

    if game.room.exits:
        items.append(MenuItem("Go through a door", do_go))
    if "backpack" in game.carrying:
        items.append(MenuItem("Open your backpack", do_backpack))
    if "evacuation_plan" in game.carrying and not ui.has_pause_menu():
        # the Pygame window opens the drawn map with the M key instead
        items.append(MenuItem("Look at the floor plan", do_map))

    if not ui.has_pause_menu():
        # the Pygame window keeps these in its Escape menu instead
        items.append(MenuItem("Options", do_options))
    return tuple(items)


def _offer_interactions(game: Game) -> None:
    """Offer everything in this room worth touching, until the player is done."""
    while True:
        actions = _interactions(game)
        if not actions:
            return

        ui.pause(0.4)
        chosen = ui.choose(
            "What do you do?", [action.label for action in actions], back="Nothing, for now"
        )
        if chosen is None:
            return
        picked = actions[chosen]
        picked.action(game)
        if picked.ends_interaction:
            return


def _interactions(game: Game) -> tuple[MenuItem, ...]:
    """Return what is in this room right now: objects, items, and any boss."""
    actions = [
        MenuItem(f"Look at {thing.name}", _inspect(thing.name))
        for thing in game.room.inspectables
        if thing.gone_once_taken is None or not game.has_taken(thing.gone_once_taken)
    ]
    actions += [
        MenuItem(
            f"Take the {item.name.upper() if game.room.key == 'storage' else item.name}",
            _take(item.key),
            ends_interaction=True,
        )
        for item in game.items_here()
    ]

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
                ui.narrate(thing.text)
                return

    return action


def _take(key: str) -> Callable[[Game], None]:
    """Return an action that picks up the item called ``key``."""

    def action(game: Game) -> None:
        item = game.take(key)
        ui.say()
        name = item.name.upper() if game.room.key == "storage" else item.name
        ui.say(f"You take the {name}.")
        ui.new_page()  # picking something up is a moment of its own
        ui.narrate(f"You take the {get_item(key).name}.")
        game.take(key)  # the backpack may have something to say about it
        ui.new_page()

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
    """Name a door, saying whether the player has been through it before.

    Hallways are excluded: the player passes through a corridor or lobby
    every trip, so tagging it as "visited" would just be noise.
    """
    if door.key in game.visited and not door.is_hallway:
        return f"{door.name} (you have been there)"
    return door.name
