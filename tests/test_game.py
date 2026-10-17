"""Playing the game through the menu, with scripted keypresses.

These tests are written against the user stories, not against the code: if a
story says the player starts with nothing, the test says so too.
"""

from __future__ import annotations

import commands
import main
import memories
import persistence
import rooms  # noqa: F401  (importing rooms registers them)
import world
from commands import build_menu
from game import STARTING_HEARTS, Game


def start() -> Game:
    """Return a game that has been walked into, ready for a turn."""
    game = Game()
    game.enter()
    return game


def option(game: Game, label: str) -> str:
    """Return the number the player would press for the menu line ``label``."""
    for number, item in enumerate(build_menu(game), start=1):
        if label.casefold() in item.label.casefold():
            return str(number)
    raise AssertionError(f"the menu has no option matching {label!r}")


def labels(game: Game) -> list[str]:
    """Return the menu as the player would read it."""
    return [item.label for item in build_menu(game)]


def test_the_player_starts_in_2035_with_nothing(console) -> None:
    """US1a: the player wakes up here, on three hearts, carrying nothing."""
    game = start()
    assert game.current == "classroom_2035"
    assert len(game.carrying) == 0
    assert game.hearts.hearts == STARTING_HEARTS


def test_the_opening_menu_offers_only_what_the_story_gives(console) -> None:
    """No backpack, no map, no help: none of them exist yet in the story."""
    assert labels(start()) == ["Look around", "Go through a door", "Options"]


def test_looking_around_offers_the_three_objects(console) -> None:
    """US1a: the clock, the laptop and the desk must all be inspectable."""
    game = start()
    console.script(option(game, "Look around"), "0")
    game.turn()
    assert "the clock" in console.output
    assert "the laptop" in console.output
    assert "the desk" in console.output


def test_the_clock_reads_the_time_the_memory_keeper_asks_about(console) -> None:
    """US1a: this time must match the clock in Project room 3 (US1l)."""
    game = start()
    console.script(option(game, "Look around"), "1", "0")
    game.turn()
    assert memories.CLOCK_TIME in console.output
    assert memories.CLOCK_TIME == "23:17"


def test_the_laptop_shows_the_deadline_notification(console) -> None:
    game = start()
    console.script(option(game, "Look around"), "2", "0")
    game.turn()
    assert memories.LAPTOP_NOTIFICATION.casefold() in console.output


def test_the_desk_holds_the_note_the_memory_keeper_asks_about(console) -> None:
    """US1a: the note is a memory hook - it is seen, not taken."""
    game = start()
    console.script(option(game, "Look around"), "3", "0")
    game.turn()
    assert memories.DESK_CONTENTS in console.output
    assert len(game.carrying) == 0


def test_there_is_only_one_backpack_in_the_game(console) -> None:
    """The Evil Backpack (US1c) is the only backpack. 2.035 must not have one."""
    game = start()
    console.script(option(game, "Look around"), "0")
    game.turn()
    assert "backpack" not in console.output


def test_nothing_can_be_taken_in_the_starting_room(console) -> None:
    """US1a lists no rewards: there is nothing here to pick up."""
    assert start().items_here() == ()


def test_the_only_way_out_is_the_corridor(console) -> None:
    game = start()
    console.script(option(game, "Go through a door"), "1")
    game.turn()
    assert game.current == "corridor_blue"
    assert world.get("classroom_2035").exits == ("corridor_blue",)


def test_backing_out_of_a_door_changes_nothing(console) -> None:
    game = start()
    console.script(option(game, "Go through a door"), "0")
    game.turn()
    assert game.current == "classroom_2035"


def test_a_locked_door_turns_the_player_away(console) -> None:
    """The blue card comes from 2.031 (US1c), so this door cannot open yet."""
    game = start()
    game.move_to("corridor_blue")
    doors = world.exits_of(game.room)
    staff_room = str(doors.index(world.get("teachers_room_4")) + 1)

    console.script(option(game, "Go through a door"), staff_room)
    game.turn()
    assert "key card" in console.output
    assert game.current == "corridor_blue"


def test_taking_the_evacuation_plan_unlocks_the_map_choice(console) -> None:
    """US1b: the map is not offered until the player has the plan."""
    game = start()
    game.move_to("corridor_blue")
    assert "Look at the floor plan" not in labels(game)

    console.script(option(game, "Look around"), "2", "0")
    game.turn()
    assert "evacuation_plan" in game.carrying
    assert "Look at the floor plan" in labels(game)


def test_revisiting_a_room_says_so(console) -> None:
    """US1 template: the player can see they have been somewhere before."""
    game = start()
    game.move_to("corridor_blue")
    game.move_to("classroom_2035")
    assert "you have been here before" in console.output


def option_in_options(game: Game, label: str) -> str:
    """Return the number the player would press for ``label`` under Options.

    Asked of the menu itself rather than counted by hand, so adding a choice
    to Options does not quietly break this test.
    """
    for number, item in enumerate(commands.options_menu(game), start=1):
        if label.casefold() in item.label.casefold():
            return str(number)
    raise AssertionError(f"Options has no choice matching {label!r}")


def test_quitting_from_the_options_menu_after_confirmation(console) -> None:
    game = start()
    console.script(option(game, "Options"), option_in_options(game, "Quit"), "1")
    game.turn()
    assert game.running is False
    assert "game over" in console.output


def test_canceling_quit_keeps_the_game_running(console) -> None:
    game = start()
    console.script(option(game, "Options"), option_in_options(game, "Quit"), "2")
    game.turn()
    assert game.running is True
    assert "game over" not in console.output


def test_the_game_ends_cleanly_when_the_input_runs_out(console) -> None:
    """Piping a script into the game must not end in a traceback."""
    game = Game()
    game.run()
    assert game.running is False
    assert "nobody at the keyboard" in console.output


def test_the_wake_up_scene_plays_once(console) -> None:
    """US1a.3: the wake-up opening runs on arrival, and only the first time."""
    game = start()
    assert "cheek is stuck to the desk" in console.output

    console.lines.clear()
    game.move_to("corridor_blue")
    game.move_to("classroom_2035")
    assert "cheek is stuck to the desk" not in console.output


def test_project_room_2_supervisor_meeting_plays_once(console) -> None:
    """US1o: the supervisor meeting runs when entering Project Room 2."""
    game = start()
    console.lines.clear()

    console.script("1", "1", "1")
    game.move_to("projectroom_2")

    assert "you're late for the meeting." in console.output
    assert "the project meeting." in console.output

    console.lines.clear()
    game.move_to("lobby")
    game.move_to("projectroom_2")

    assert "You're late for the meeting." not in console.output

    def test_project_room_2_has_todo_list(console) -> None:
        """US1o: the TODO list can be inspected."""
        game = start()
        console.lines.clear()

        game.move_to("projectroom_2")

        console.lines.clear()
        console.script(option(game, "Look around"), "1", "0")
        game.turn()

        assert "finish project" in console.output
        assert "finish documentation" in console.output
        assert "test everything" in console.output
        assert "fix everything" in console.output
        assert "do not panic" in console.output


def test_project_room_2_supervisor_dialogue_reaches_the_end(console) -> None:
    """US1o: the supervisor dialogue reaches its final joke."""
    game = start()
    console.lines.clear()

    console.script("1", "2", "1")
    game.move_to("projectroom_2")

    assert "what progress?" in console.output
    assert "exactly." in console.output


def test_typing_quit_and_confirming_ends_the_game_without_saving(console) -> None:
    """US2: quit works at any prompt, asks first, and leaves no save behind."""
    console.script("Krug", "quit", "1")

    main.main()  # returns normally: no traceback, exit code 0

    assert "game over" in console.output
    assert persistence.load_game("Krug") is None


def test_taking_back_a_typed_quit_asks_the_same_question_again(console) -> None:
    console.script("Krug", "quit", "2")

    main.main()

    assert "step away from the building" not in console.output
    assert console.output.count("what do you do?") == 2


def test_typing_scoreboard_shows_it_and_carries_on(console) -> None:
    """US5: the scoreboard can be typed at any prompt as well as found in Options."""
    console.script("Krug", "scoreboard")

    main.main()

    assert "scoreboard - top 5" in console.output
    assert console.output.count("what do you do?") == 2
