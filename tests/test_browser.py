"""The web build's stand-ins (browser.py): the database kept in localStorage, and fetch."""

from __future__ import annotations

import asyncio
import json
import sys
import types
import urllib.error

import pytest

import browser
import persistence
from game import Game


class FakeStorage:
    """Stands in for the browser's localStorage."""

    def __init__(self) -> None:
        self.items: dict[str, str] = {}

    def setItem(self, key: str, value: str) -> None:  # noqa: N802 - the browser's own name
        self.items[key] = value

    def getItem(self, key: str) -> str | None:  # noqa: N802 - the browser's own name
        return self.items.get(key)


@pytest.fixture
def in_a_browser(monkeypatch) -> FakeStorage:
    storage = FakeStorage()
    window = types.SimpleNamespace(localStorage=storage)
    monkeypatch.setattr(browser, "IN_BROWSER", True)
    monkeypatch.setattr(browser, "_window", lambda: window)
    return storage


def test_a_save_outlives_the_page(in_a_browser, tmp_path, monkeypatch) -> None:
    persistence.save_game(Game(player_name="Krug", current="lobby"))
    assert in_a_browser.items  # the database was copied into localStorage

    # a new visit: the page starts with no files at all
    monkeypatch.setattr(persistence, "DATABASE_NAME", str(tmp_path / "fresh" / "test.db"))
    (tmp_path / "fresh").mkdir()
    persistence.create_tables()
    saved = persistence.load_game("Krug")
    assert saved is not None and saved.current == "lobby"


def test_reading_the_database_does_not_copy_it_again(in_a_browser) -> None:
    persistence.load_game("Nobody")
    assert in_a_browser.items == {}


def test_outside_a_browser_nothing_is_copied() -> None:
    persistence.save_game(Game(player_name="Krug"))
    browser.keep_file(persistence.DATABASE_NAME)  # does nothing, and needs no browser


def _fake_fetch(monkeypatch, status: int, body: str) -> list:
    """Make browser.fetch answer ``status`` and ``body``; return the requests it was asked for."""
    asked: list = []

    def request(method, url, headers, text):
        asked.append((method, url, json.loads(headers), text))
        return json.dumps({"status": status, "body": body})

    async def jsiter(reply):
        return reply

    window = types.SimpleNamespace(eval=lambda _code: None, afterHoursFetch=request)
    monkeypatch.setattr(browser, "_window", lambda: window)
    monkeypatch.setitem(sys.modules, "platform", types.SimpleNamespace(jsiter=jsiter))
    return asked


def test_fetch_hands_back_the_body(monkeypatch) -> None:
    asked = _fake_fetch(monkeypatch, 200, "[1, 2]")
    reply = asyncio.run(browser.fetch("POST", "https://x", {"apikey": "k"}, b'{"a": 1}'))
    assert reply == b"[1, 2]"
    assert asked == [("POST", "https://x", {"apikey": "k"}, '{"a": 1}')]


def test_fetch_raises_what_urllib_would(monkeypatch) -> None:
    _fake_fetch(monkeypatch, 409, "duplicate")
    with pytest.raises(urllib.error.HTTPError) as error:
        asyncio.run(browser.fetch("POST", "https://x", {}, None))
    assert error.value.code == 409

    _fake_fetch(monkeypatch, 0, "TypeError: Failed to fetch")
    with pytest.raises(OSError):
        asyncio.run(browser.fetch("GET", "https://x", {}, None))
