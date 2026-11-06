"""The connection to the game's Supabase project, used by the accounts and the shared scoreboard.

Everything goes over plain HTTPS: with the standard library on a computer, so the game needs no
extras, and with the browser's own fetch in a web build (see ``browser.py``). The SQL that sets
the project up is in ``supabase/``.
"""

from __future__ import annotations

import asyncio
import json
import urllib.request

import browser

#: The project address from Supabase (Project Settings > API), e.g. "https://abcd1234.supabase.co".
#: Leave it empty to keep everything on this computer.
SUPABASE_URL = "https://ahzmeymxnsbhtdwdibhg.supabase.co"
#: The public key from the same page (called "anon" or "publishable"). It is safe to commit: the
#: tables only allow what ``supabase/*.sql`` grants. Never put the secret / service_role key here.
SUPABASE_KEY = "sb_publishable_IxX7Ql4UqujXXE9NEsFXnw_MClEkPnj"

TIMEOUT = 4.0  # seconds to wait for the server before giving up


def enabled() -> bool:
    """Whether a Supabase project is set up."""
    return bool(SUPABASE_URL and SUPABASE_KEY)


async def send(method: str, path: str, body: dict | None = None, *, minimal: bool = True) -> bytes:
    """Make one request to ``/rest/v1/<path>`` and return the reply. Raises on any problem.

    ``minimal`` asks the server not to send the written row back. On a computer the request runs
    on a worker thread, so the game (and the window) carry on while it waits.
    """
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    if minimal:
        headers["Prefer"] = "return=minimal"
    if SUPABASE_KEY.startswith("eyJ"):  # an older, token-style key also goes in this header
        headers["Authorization"] = f"Bearer {SUPABASE_KEY}"
    data = json.dumps(body).encode() if body is not None else None
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{path}"
    if browser.IN_BROWSER:
        return await browser.fetch(method, url, headers, data)
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    return await asyncio.to_thread(_open, request)


def _open(request: urllib.request.Request) -> bytes:
    """Send ``request`` and return the reply, waiting at most :data:`TIMEOUT` seconds."""
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 - https address from above
        return response.read()


async def call(function: str, **arguments: object) -> object:
    """Run the database function ``function`` with ``arguments`` and return its result."""
    return json.loads(await send("POST", f"rpc/{function}", arguments, minimal=False))
