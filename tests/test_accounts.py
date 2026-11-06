"""Accounts online (accounts.py): names registered on Supabase, passwords checked on the server."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import urllib.error

import pytest

import accounts
import cloud
import main
import persistence
from game import Game

PASSWORD = "secret"


class FakeAccounts:
    """Stands in for the functions in supabase/accounts.sql; can be switched off."""

    def __init__(self) -> None:
        self.passwords: dict[str, str] = {}
        self.wrong_in_a_row = 0
        self.up = True

    async def __call__(self, method: str, path: str, body: dict | None = None, **_options) -> bytes:
        if not self.up:
            raise urllib.error.URLError("no connection")
        assert method == "POST" and body is not None
        name = body["player_name"].casefold()
        if path == "rpc/player_exists":
            answer: object = name in self.passwords
        elif path == "rpc/register_player":
            answer = name not in self.passwords
            self.passwords.setdefault(name, body["password"])
        elif self.wrong_in_a_row >= 5:
            answer = "locked"
        elif self.passwords.get(name) == body["password"]:
            answer = "ok"
        else:
            self.wrong_in_a_row += 1
            answer = "wrong"
        return json.dumps(answer).encode()


@pytest.fixture
def server(monkeypatch) -> FakeAccounts:
    fake = FakeAccounts()
    monkeypatch.setattr(cloud, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(cloud, "SUPABASE_KEY", "public-key")
    monkeypatch.setattr(cloud, "send", fake)
    return fake


def test_a_new_name_is_registered_online_and_nothing_is_kept_here(console, server) -> None:
    console.script("Kru", PASSWORD, PASSWORD, "quit", "1")
    asyncio.run(main.main())
    assert server.passwords == {"kru": PASSWORD}
    connection = sqlite3.connect(persistence.DATABASE_NAME)
    stored = connection.execute("SELECT password_hash FROM players").fetchall()
    connection.close()
    assert all(password_hash is None for (password_hash,) in stored)


def test_a_name_registered_on_another_computer_needs_its_password(console, server) -> None:
    server.passwords["kru"] = PASSWORD
    console.script("Kru", "1", "wrong", "1", PASSWORD, "quit", "1")
    asyncio.run(main.main())
    assert "already taken" in console.output
    assert "wrong password." in console.output
    assert "starting a new game." in console.output


def test_a_save_is_resumed_once_the_server_says_the_password_is_right(console, server) -> None:
    server.passwords["krug"] = PASSWORD
    persistence.save_game(Game(player_name="Krug", current="student_society"))
    console.script("1", PASSWORD, "quit", "1")
    asyncio.run(main.main())
    assert "welcome back, krug!" in console.output


def test_too_many_wrong_passwords_lock_the_name(console, server) -> None:
    server.passwords["krug"] = PASSWORD
    server.wrong_in_a_row = 5
    persistence.save_game(Game(player_name="Krug", current="student_society"))
    console.script("1", PASSWORD, "2")  # then a different name: the script ends there
    with pytest.raises(EOFError):
        asyncio.run(main.main())
    assert "wait a minute" in console.output
    assert "welcome back" not in console.output


def test_a_password_that_cannot_be_checked_is_not_accepted(console, server) -> None:
    server.up = False
    console.script("Kru")  # then the name is asked for again: the script ends there
    with pytest.raises(EOFError):
        asyncio.run(main.main())
    assert main.UNREACHABLE.lower() in console.output
    assert "starting a new game." not in console.output


def test_an_unreachable_server_is_reported_not_raised(server) -> None:
    server.up = False
    with pytest.raises(accounts.Unreachable):
        asyncio.run(accounts.password_matches("Krug", PASSWORD))
