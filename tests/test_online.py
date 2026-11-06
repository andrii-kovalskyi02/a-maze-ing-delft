"""The shared scoreboard (leaderboard/online.py): uploads, the offline outbox, cache and display."""

from __future__ import annotations

import asyncio
import json
import urllib.error

import pytest

import cloud
import persistence
from game import Game
from leaderboard import online, scoreboard


class FakeServer:
    """Stands in for the Supabase table: remembers what was posted, can be switched off."""

    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.up = True

    def __call__(self, method: str, path: str, body: dict | None = None, **_options) -> bytes:
        if not self.up:
            raise urllib.error.URLError("no connection")
        if method == "POST":
            if any(row["run_id"] == body["run_id"] for row in self.rows):
                raise urllib.error.HTTPError("url", 409, "duplicate", {}, None)  # type: ignore[arg-type]
            self.rows.append(body)
            return b""
        best_first = sorted(self.rows, key=lambda r: (-r["percent"], r["seconds"]))
        return json.dumps(best_first).encode()


@pytest.fixture
def server(monkeypatch) -> FakeServer:
    fake = FakeServer()
    monkeypatch.setattr(cloud, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(cloud, "SUPABASE_KEY", "public-key")
    monkeypatch.setattr(cloud, "send", fake)
    monkeypatch.setattr(online, "sync_in_background", online.sync)  # no threads in tests
    return fake


def test_it_is_off_until_an_address_is_set(console) -> None:
    assert not online.enabled()
    online.submit("Krug", 50, 100.0)
    assert persistence.pending_scores() == []
    assert scoreboard.lines()[0] == "Leaderboard - top 5"


def test_a_finished_run_is_uploaded_and_leaves_the_outbox(server) -> None:
    online.submit("Krug", 50, 100.0)
    assert [(r["name"], r["percent"], r["seconds"]) for r in server.rows] == [("Krug", 50, 100.0)]
    assert persistence.pending_scores() == []


def test_a_run_waits_in_the_outbox_when_offline_and_goes_up_later(server) -> None:
    server.up = False
    online.submit("Krug", 50, 100.0)
    assert server.rows == []
    assert len(persistence.pending_scores()) == 1
    server.up = True
    online.sync()
    assert len(server.rows) == 1
    assert persistence.pending_scores() == []


def test_a_run_the_server_already_has_is_not_sent_twice(server) -> None:
    online.submit("Krug", 50, 100.0)
    run_id = server.rows[0]["run_id"]
    persistence.add_pending_score(run_id, "Krug", 50, 100.0)  # e.g. the delete was lost
    online.sync()
    assert len(server.rows) == 1
    assert persistence.pending_scores() == []


def test_the_top_list_has_one_line_per_player_best_first(server) -> None:
    for name, percent, seconds in [
        ("Ann", 40, 90.0),
        ("Bob", 80, 300.0),
        ("ann", 80, 200.0),  # Ann again, better
        ("Cy", 80, 100.0),
        ("Di", 10, 5.0),
        ("Ed", 20, 5.0),
        ("Flo", 30, 5.0),
    ]:
        online.submit(name, percent, seconds)
    assert online.fetch_top(5) == [
        ("Cy", 80, 100.0),
        ("ann", 80, 200.0),
        ("Bob", 80, 300.0),
        ("Flo", 30, 5.0),
        ("Ed", 20, 5.0),
    ]


def test_an_unreachable_server_gives_none_and_keeps_the_last_list(server) -> None:
    online.submit("Ann", 40, 90.0)
    server.up = False
    assert online.fetch_top() is None
    online.sync()
    assert persistence.online_top() == [("Ann", 40, 90.0)]


def test_the_scoreboard_shows_everyone_when_online_and_this_computer_when_not(server) -> None:
    persistence.record_score("local", 10, 50.0)
    server.up = False
    assert scoreboard.lines()[:2] == [
        "Leaderboard - top 5 (this computer only)",
        "1. local - 10% - 00:50",
    ]
    server.up = True
    online.submit("Ann", 40, 90.0)
    assert scoreboard.lines()[:2] == ["Leaderboard - top 5", "1. Ann - 40% - 01:30"]
    server.up = False
    assert scoreboard.lines()[0] == "Leaderboard - top 5"  # the last list is kept offline


def test_walking_out_of_the_building_uploads_the_run(console, server) -> None:
    game = Game(player_name="Krug")
    asyncio.run(game.finish())
    assert [row["name"] for row in server.rows] == ["Krug"]
    assert "shared leaderboard" in console.output.lower()
    assert "leaderboard - top 5" in console.output.lower()


def test_a_fetched_but_empty_shared_board_is_not_mistaken_for_no_connection(server) -> None:
    assert persistence.online_top() is None  # never fetched
    online.sync()
    assert persistence.online_top() == []
    assert scoreboard.lines() == [
        "Leaderboard - top 5",
        "Nobody is on the leaderboard yet.",
    ]


def test_every_run_carries_its_players_tag(server) -> None:
    persistence.set_password("Krug", "secret")
    online.submit("Krug", 50, 100.0)
    assert server.rows[0]["player_tag"] == persistence.player_tag("Krug")
    assert len(server.rows[0]["player_tag"]) == 8


def test_two_players_with_one_name_are_told_apart_by_their_tags(server) -> None:
    for run, (tag, percent) in enumerate([("a3f9c0de", 80), ("07bc11aa", 60), (None, 40)]):
        server.rows.append(
            {
                "run_id": str(run),
                "name": "Kru",
                "player_tag": tag,
                "percent": percent,
                "seconds": 9.0,
            }
        )
    server.rows.append(
        {"run_id": "x", "name": "Ann", "player_tag": "ffff0000", "percent": 10, "seconds": 9.0}
    )
    assert online.fetch_top(5) == [
        ("Kru #a3f9", 80, 9.0),
        ("Kru #07bc", 60, 9.0),
        ("Kru", 40, 9.0),  # a run from before tags: no tag to show
        ("Ann", 10, 9.0),  # nobody else is called Ann: no tag needed
    ]
