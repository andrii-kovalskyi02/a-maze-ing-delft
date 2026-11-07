"""The shared scoreboard: finished runs are uploaded, and everyone's best five are shown (US5).

The scores live in a Supabase table (see ``supabase/scores.sql``), reached through ``cloud.py``.

Nothing here may get in the player's way:

- With no Supabase address set in ``cloud.py``, this is off and the scoreboard stays local.
- A run is first written to a local outbox, then uploaded. If there is no connection it stays in
  the outbox and goes up the next time the game manages to reach the server.
- The last top list seen is kept on disk, so the scoreboard still shows something offline.
- Every network problem is swallowed; the worst that happens is an out-of-date scoreboard.

Runs from before names were registered online can share a name, so every run carries its player's
tag (random, see ``persistence.create_tables``), and two different players with one name in the top
list are shown as "Kru #a3f9" and "Kru #07bc".
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
import urllib.error
import urllib.parse
import uuid

import cloud
import persistence

FETCH_ROWS = 50  # how many rows to ask for, so a player with several runs does not crowd the top
TAG_SHOWN = 4  # how many letters of a tag are shown after a name that two players share
REFRESH_EVERY = 30.0  # seconds between background refreshes

_last_sync: float | None = None
_running: set[asyncio.Task] = set()


def enabled() -> bool:
    """Whether the shared scoreboard is set up."""
    return cloud.enabled()


async def _upload(run_id: str, name: str, tag: str | None, percent: int, seconds: float) -> bool:
    """Send one run. True if the server has it now (also when it already had it)."""
    row = {
        "run_id": run_id,
        "name": name,
        "player_tag": tag,
        "percent": percent,
        "seconds": seconds,
    }
    try:
        await cloud.send("POST", "scores", row)
    except urllib.error.HTTPError as error:
        return error.code == 409  # that run id is already there: uploaded earlier
    except (OSError, ValueError):
        return False
    return True


async def flush_pending() -> None:
    """Upload every run waiting in the outbox, stopping at the first failure (no connection)."""
    for run_id, name, tag, percent, seconds in persistence.pending_scores():
        if not await _upload(run_id, name, tag, percent, seconds):
            return
        persistence.delete_pending_score(run_id)


async def fetch_top(limit: int = 5) -> list[tuple[str, int, float]] | None:
    """Return everyone's best ``limit`` players as (name, percent, seconds), or None if unreachable.

    Highest percent first, then fastest, one line per player (their best run). A player is a name
    and a tag, so two players with one name get a line each, told apart by their tags.
    """
    query = urllib.parse.urlencode(
        {
            "select": "name,player_tag,percent,seconds",
            "order": "percent.desc,seconds.asc",
            "limit": FETCH_ROWS,
        }
    )
    try:
        rows = json.loads(await cloud.send("GET", f"scores?{query}"))
    except (OSError, ValueError):
        return None
    best: dict[tuple[str, str], tuple[str, str, int, float]] = {}
    for row in rows:
        try:
            name, percent, seconds = str(row["name"]), int(row["percent"]), float(row["seconds"])
        except (KeyError, TypeError, ValueError):
            continue
        tag = str(row.get("player_tag") or "")  # runs from before tags have none
        best.setdefault((name.casefold(), tag), (name, tag, percent, seconds))  # best come first
    top = list(best.values())[:limit]
    names = [name.casefold() for name, _, _, _ in top]
    shown = []
    for name, tag, percent, seconds in top:
        if tag and names.count(name.casefold()) > 1:  # two players with this name are on the list
            name = f"{name} #{tag[:TAG_SHOWN]}"
        shown.append((name, percent, seconds))
    return shown


async def sync(limit: int = 5) -> None:
    """Upload what is waiting, then keep the latest top list. Never raises."""
    if not enabled():
        return
    try:
        await flush_pending()
        top = await fetch_top(limit)
        if top is not None:
            persistence.save_online_top(top)
    except sqlite3.Error:
        pass  # a busy or broken local file must not stop the game


def sync_in_background() -> None:
    """Start :func:`sync` alongside the game, at most once every ``REFRESH_EVERY`` seconds.

    It runs whenever the game is waiting, and only while the game is running: with no asyncio
    loop going (a test that only reads the scoreboard) nothing is started.
    """
    global _last_sync  # noqa: PLW0603
    now = time.monotonic()
    if not enabled() or (_last_sync is not None and now - _last_sync < REFRESH_EVERY):
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _last_sync = now
    task = loop.create_task(sync())
    _running.add(task)  # asyncio only keeps a weak reference to a task: keep it until it ends
    task.add_done_callback(_running.discard)


async def submit(name: str, percent: int, seconds: float) -> None:
    """Put a finished run on the shared scoreboard (and refresh the top list), if it is set up.

    This waits for the server for a few seconds at most, so the new score is on the board that is
    shown next. If the server cannot be reached the run waits in the outbox for next time.
    """
    if not enabled():
        return
    try:
        persistence.add_pending_score(str(uuid.uuid4()), name, percent, seconds)
    except sqlite3.Error:
        return
    await sync()
