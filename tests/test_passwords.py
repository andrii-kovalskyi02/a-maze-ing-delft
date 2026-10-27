"""Passwords: names are unique, and a taken name needs its password before anyone plays as it."""

from __future__ import annotations

import sqlite3

import main
import persistence
import ui
from game import Game

PASSWORD = "secret"


def make_save(name: str, room: str = "student_society") -> Game:
    persistence.set_password(name, PASSWORD)
    game = Game(player_name=name, current=room)
    persistence.save_game(game)
    return game


def test_only_a_hash_of_the_password_is_kept() -> None:
    persistence.set_password("Krug", PASSWORD)
    connection = sqlite3.connect(persistence.DATABASE_NAME)
    salt, stored = connection.execute("SELECT salt, password_hash FROM players").fetchone()
    connection.close()
    assert PASSWORD.encode() not in stored
    assert persistence.password_matches("Krug", PASSWORD)
    assert not persistence.password_matches("Krug", "wrong")


def test_two_players_with_one_password_get_different_hashes() -> None:
    persistence.set_password("Ann", PASSWORD)
    persistence.set_password("Bob", PASSWORD)
    connection = sqlite3.connect(persistence.DATABASE_NAME)
    hashes = {stored for (stored,) in connection.execute("SELECT password_hash FROM players")}
    connection.close()
    assert len(hashes) == 2


def test_a_name_is_taken_whatever_the_capitals() -> None:
    make_save("Krug")
    assert persistence.player_exists("KRUG")
    assert persistence.password_matches("krug", PASSWORD)


def test_a_new_player_must_type_the_same_good_password_twice(console) -> None:
    console.script("Kru", "abc", PASSWORD, "other", PASSWORD, PASSWORD, "quit", "1")
    main.main()
    assert "too short" in console.output
    assert "not the same" in console.output
    assert persistence.password_matches("Kru", PASSWORD)


def test_the_password_is_asked_for_secretly(console, monkeypatch) -> None:
    seen = []
    monkeypatch.setattr(ui, "_read", lambda prompt: seen.append(ui.asking_secret()) or PASSWORD)
    assert ui.ask_secret("Password: ") == PASSWORD
    assert seen == [True]
    assert not ui.asking_secret()


def test_picking_a_save_needs_its_password(console) -> None:
    make_save("Krug")
    console.script("1", "wrong", "1", PASSWORD, "quit", "1")  # wrong, try again, right
    main.main()
    assert "wrong password" in console.output
    assert "welcome back, krug!" in console.output


def test_giving_up_on_the_password_leaves_the_save_alone(console) -> None:
    original = make_save("Krug", room="projectroom_2")
    console.script("1", "wrong", "2", "Other", PASSWORD, PASSWORD, "quit", "1")
    main.main()
    assert "welcome back, krug!" not in console.output
    assert "no saved game found for other" in console.output
    kept = persistence.load_game("Krug")
    assert kept is not None and kept.current == original.current


def test_a_name_on_the_scoreboard_is_taken_too(console) -> None:
    persistence.set_password("Ann", PASSWORD)
    persistence.record_score("Ann", 50, 100.0)
    console.script("ann", "1", PASSWORD, "quit", "1")  # it is me: a new run for Ann
    main.main()
    assert "the name ann is already taken" in console.output
    assert "starting a new game" in console.output


def test_a_password_without_a_save_does_not_take_the_name(console) -> None:
    persistence.set_password("Kru", "forgotten")  # chose a password, then quit without saving
    assert not persistence.player_exists("Kru")
    console.script("Kru", PASSWORD, PASSWORD, "quit", "1")
    main.main()
    assert "already taken" not in console.output
    assert "no saved game found for kru" in console.output
    assert persistence.password_matches("Kru", PASSWORD)


def test_a_player_from_before_passwords_chooses_one_when_they_come_back(console) -> None:
    persistence.save_game(Game(player_name="Old"))  # a save with no password
    console.script("1", PASSWORD, PASSWORD, "quit", "1")
    main.main()
    assert "no password yet" in console.output
    assert "welcome back, old!" in console.output
    assert persistence.password_matches("Old", PASSWORD)


def test_an_old_scoreboard_keyed_by_name_is_kept(tmp_path, monkeypatch) -> None:
    path = str(tmp_path / "old.db")
    monkeypatch.setattr(persistence, "DATABASE_NAME", path)
    connection = sqlite3.connect(path)
    connection.execute(
        """CREATE TABLE scores (player_name TEXT PRIMARY KEY, percent INTEGER NOT NULL,
        seconds REAL NOT NULL, finished_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"""
    )
    connection.execute("INSERT INTO scores (player_name, percent, seconds) VALUES ('Ann', 40, 9.0)")
    connection.commit()
    connection.close()
    persistence.create_tables()
    assert persistence.top_scores() == [("Ann", 40, 9.0)]
    assert persistence.player_exists("Ann")
    assert not persistence.has_password("Ann")
