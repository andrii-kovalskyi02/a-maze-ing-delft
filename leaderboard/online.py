"""The shared scoreboard: finished runs are uploaded, and everyone's best five are shown (US5).

The scores live in a free Supabase table (see ``scores_online.sql``); this module talks to it
over plain HTTPS with nothing but the standard library, so the game still needs no extras.

Nothing here may get in the player's way:

- With no address set below, the whole thing is off and the scoreboard stays local.
- A run is first written to a local outbox, then uploaded. If there is no connection it stays in
  the outbox and goes up the next time the game manages to reach the server.
- The last top list seen is kept on disk, so the scoreboard still shows something offline.
- Every network problem is swallowed; the worst that happens is an out-of-date scoreboard.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import persistence

#: The project address from Supabase (Project Settings > API), e.g. "https://abcd1234.supabase.co".
#: Leave it empty to keep the scoreboard on this computer only.
SUPABASE_URL = "https://ahzmeymxnsbhtdwdibhg.supabase.co"
#: The public key from the same page (called "anon" or "publishable"). It is safe to commit, because
#: the table only lets people read and add scores. Never put the secret / service_role key here.
SUPABASE_KEY = "sb_publishable_IxX7Ql4UqujXXE9NEsFXnw_MClEkPnj"

TIMEOUT = 4.0  # seconds to wait for the server before giving up
FETCH_ROWS = 50  # how many rows to ask for, so a player with several runs does not crowd the top
REFRESH_EVERY = 30.0  # seconds between background refreshes

_last_sync: float | None = None


def enabled() -> bool:
    """Whether the shared scoreboard is set up."""
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _send(method: str, path: str, body: dict | None = None) -> bytes:
    """Make one request to the scores table and return the reply. Raises on any problem."""
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    if SUPABASE_KEY.startswith("eyJ"):  # an older, token-style key also goes in this header
        headers["Authorization"] = f"Bearer {SUPABASE_KEY}"
    data = json.dumps(body).encode() if body is not None else None
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path}"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 - https address from above
        return response.read()


def _upload(run_id: str, name: str, percent: int, seconds: float) -> bool:
    """Send one run. True if the server has it now (also when it already had it)."""
    row = {"run_id": run_id, "name": name, "percent": percent, "seconds": seconds}
    try:
        _send("POST", "scores", row)
    except urllib.error.HTTPError as error:
        return error.code == 409  # that run id is already there: uploaded earlier
    except (OSError, ValueError):
        return False
    return True


def flush_pending() -> None:
    """Upload every run waiting in the outbox, stopping at the first failure (no connection)."""
    for run_id, name, percent, seconds in persistence.pending_scores():
        if not _upload(run_id, name, percent, seconds):
            return
        persistence.delete_pending_score(run_id)


def fetch_top(limit: int = 5) -> list[tuple[str, int, float]] | None:
    """Return everyone's best ``limit`` players as (name, percent, seconds), or None if unreachable.

    Highest percent first, then fastest, one line per player (their best run).
    """
    query = urllib.parse.urlencode(
        {"select": "name,percent,seconds", "order": "percent.desc,seconds.asc", "limit": FETCH_ROWS}
    )
    try:
        rows = json.loads(_send("GET", f"scores?{query}"))
    except (OSError, ValueError):
        return None
    best: dict[str, tuple[str, int, float]] = {}
    for row in rows:
        try:
            name, percent, seconds = str(row["name"]), int(row["percent"]), float(row["seconds"])
        except (KeyError, TypeError, ValueError):
            continue
        best.setdefault(name.casefold(), (name, percent, seconds))  # rows come best first
    return list(best.values())[:limit]


def sync(limit: int = 5) -> None:
    """Upload what is waiting, then keep the latest top list. Never raises."""
    if not enabled():
        return
    try:
        flush_pending()
        top = fetch_top(limit)
        if top is not None:
            persistence.save_online_top(top)
    except sqlite3.Error:
        pass  # a busy or broken local file must not stop the game


def sync_in_background() -> None:
    """Do :func:`sync` on another thread, at most once every ``REFRESH_EVERY`` seconds."""
    global _last_sync  # noqa: PLW0603
    now = time.monotonic()
    if not enabled() or (_last_sync is not None and now - _last_sync < REFRESH_EVERY):
        return
    _last_sync = now
    threading.Thread(target=sync, daemon=True).start()


def submit(name: str, percent: int, seconds: float) -> None:
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
    sync()
