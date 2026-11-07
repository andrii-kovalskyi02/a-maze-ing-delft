"""Names and profiles: what a name may be, matching ignoring case, and picking who plays."""

from __future__ import annotations

import asyncio

import pytest

import main
import persistence
import profiles
from game import Game

#: The password every saved player in these tests has.
PASSWORD = "secret"


def make_save(name: str, room: str = "student_society") -> Game:
    persistence.set_password(name, PASSWORD)
    game = Game(player_name=name, current=room)
    persistence.save_game(game)
    return game


@pytest.mark.parametrize(
    ("raw", "tidy"),
    [
        ("Kru", "Kru"),
        ("  Kru   Jr ", "Kru Jr"),
        ("Zoë", "Zoë"),
        ("A-b_c.d'e 9", "A-b_c.d'e 9"),
    ],
)
def test_good_names_are_accepted_and_tidied(raw: str, tidy: str) -> None:
    assert profiles.check_name(raw) == (tidy, None)


@pytest.mark.parametrize("raw", ["", "   ", "x" * 31, "bad;name", "no/slash", "emoji🙂"])
def test_bad_names_come_with_a_message(raw: str) -> None:
    assert profiles.check_name(raw)[1] is not None


def test_thirty_characters_is_the_limit() -> None:
    assert profiles.check_name("x" * 30)[1] is None
    assert "30" in (profiles.check_name("x" * 31)[1] or "")


def test_a_too_long_name_is_asked_for_again(console) -> None:
    console.script("x" * 40, "Kru")
    assert asyncio.run(main.ask_name()) == "Kru"
    assert "too long" in console.output


def test_a_name_matches_the_spelling_already_on_file_whatever_the_capitals(console) -> None:
    make_save("Krug")
    console.script("krug")
    assert asyncio.run(main.ask_name()) == "Krug"
    persistence.record_score("Ann", 10, 5.0)
    console.script("ANN")
    assert asyncio.run(main.ask_name()) == "Ann"


def test_with_no_saves_the_player_just_types_a_name(console) -> None:
    console.script("Kru", PASSWORD, PASSWORD, "quit", "1")
    asyncio.run(main.main())
    assert "who is playing?" not in console.output
    assert "no saved game found for kru" in console.output


def test_saves_are_listed_newest_first_and_picking_one_resumes_it(console) -> None:
    make_save("Old")
    make_save("New")
    assert persistence.recent_saves(8)[0] == "New"
    console.script("2", PASSWORD, "quit", "1")  # the second in the list is Old
    asyncio.run(main.main())
    assert "who is playing?" in console.output
    assert "welcome back, old!" in console.output


def test_the_list_shows_how_far_each_player_is(console) -> None:
    make_save("Krug")
    # "New player" is last: after the one save
    console.script("2", "Newbie", PASSWORD, PASSWORD, "quit", "1")
    asyncio.run(main.main())
    assert "krug - 0% explored - 00:00 played" in console.output
    assert "no saved game found for newbie" in console.output


def test_the_list_holds_at_most_eight_saves(console) -> None:
    for number in range(profiles.MAX_PROFILES + 3):
        make_save(f"P{number}")
    # 8 saves, then "New player" is number 9
    console.script("9", "Newbie", PASSWORD, PASSWORD, "quit", "1")
    asyncio.run(main.main())
    assert console.output.count("explored -") == profiles.MAX_PROFILES
    assert "no saved game found for newbie" in console.output


def test_typing_a_name_with_a_save_asks_before_resuming(console) -> None:
    make_save("Krug")
    # new player, "krug" has a save, yes that's me
    console.script("2", "krug", "1", PASSWORD, "quit", "1")
    asyncio.run(main.main())
    assert "there is already a saved game for krug:" in console.output
    assert "welcome back, krug!" in console.output


def test_saying_no_picks_another_name_and_leaves_the_save_alone(console) -> None:
    original = make_save("Krug", room="projectroom_2")
    # not me: try "Other"
    console.script("2", "Krug", "2", "Other", PASSWORD, PASSWORD, "quit", "1")
    asyncio.run(main.main())
    assert "no saved game found for other" in console.output
    kept = persistence.load_game("Krug")
    assert kept is not None and kept.current == original.current
    assert persistence.load_game("Other") is None  # quit saves nothing


def test_there_is_no_way_to_start_over_a_save(console) -> None:
    make_save("Krug")
    console.script("2", "Krug", "2", "Other", PASSWORD, PASSWORD, "quit", "1")
    asyncio.run(main.main())
    assert "start over" not in console.output
    assert "delete" not in console.output


def test_an_old_database_without_saved_at_still_loads_its_saves(tmp_path, monkeypatch) -> None:
    import sqlite3

    path = str(tmp_path / "old.db")
    monkeypatch.setattr(persistence, "DATABASE_NAME", path)
    connection = sqlite3.connect(path)
    connection.execute(
        """CREATE TABLE game_states (player_name TEXT PRIMARY KEY, current_room TEXT NOT NULL,
        inventory TEXT NOT NULL, hearts INTEGER NOT NULL, digits TEXT NOT NULL,
        visited_rooms TEXT NOT NULL, unlocked_rooms TEXT NOT NULL,
        defeated_challenges TEXT NOT NULL, taken_items TEXT NOT NULL,
        approached TEXT NOT NULL, elapsed_time REAL NOT NULL)"""
    )
    empty = "'[]'"
    connection.execute(
        f"INSERT INTO game_states VALUES ('Old', 'student_society', {empty}, 6, "
        f"{empty}, {empty}, {empty}, {empty}, {empty}, {empty}, 5.0)"
    )
    connection.commit()
    connection.close()
    persistence.create_tables()
    assert persistence.recent_saves(8) == ["Old"]
    assert persistence.load_game("Old") is not None
