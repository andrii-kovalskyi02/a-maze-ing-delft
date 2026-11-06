"""What is different when the game runs in a web browser (a pygbag build).

The browser's Python has no sockets and no lasting files: ``urllib`` cannot reach the internet,
and a file written there is gone when the page closes. So in the browser:

- requests go through the browser's own ``fetch`` (see :func:`fetch`), and
- the game database is copied into the browser's ``localStorage`` after every change and copied
  back when the game starts (see :func:`keep_file` and :func:`restore_file`).

Everywhere else every function here does nothing, or is never called.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error

#: True when the game runs in a web browser.
IN_BROWSER = sys.platform == "emscripten"

_STORAGE_PREFIX = "after_hours:"  # in front of every localStorage key this game uses

# a generator the browser's fetch fills in: Python polls it (platform.jsiter) until the reply is
# there, as {"status": ..., "body": ...}. Status 0 means the request never got an answer
_FETCH_JS = """
window.afterHoursFetch = function * (method, url, headers, body) {
    var reply = null;
    var options = {method: method, headers: JSON.parse(headers)};
    if (body !== null) options.body = body;
    fetch(url, options)
        .then(r => r.text().then(t => { reply = JSON.stringify({status: r.status, body: t}); }))
        .catch(e => { reply = JSON.stringify({status: 0, body: String(e)}); });
    while (reply === null) { yield; }
    yield reply;
}
"""
_fetch_ready = False


def _window():
    """The browser's ``window`` object, as pygbag hands it to Python."""
    import platform  # pygbag's own module in the browser, not the standard library's

    return platform.window


async def fetch(method: str, url: str, headers: dict[str, str], body: bytes | None) -> bytes:
    """Make one HTTP request with the browser's fetch and return the reply's body.

    Raises the same errors ``urllib.request.urlopen`` would: ``urllib.error.HTTPError`` for an
    error status, and ``OSError`` when there was no answer at all.
    """
    import platform

    global _fetch_ready
    if not _fetch_ready:
        _window().eval(_FETCH_JS)
        _fetch_ready = True
    text = None if body is None else body.decode()
    raw = await platform.jsiter(_window().afterHoursFetch(method, url, json.dumps(headers), text))
    reply = json.loads(raw)
    status, content = int(reply["status"]), str(reply["body"]).encode()
    if status == 0:
        raise OSError(f"no answer from {url}: {content.decode()}")
    if status >= 400:
        raise urllib.error.HTTPError(url, status, content.decode(), {}, None)  # type: ignore[arg-type]
    return content


def keep_file(path: str) -> None:
    """Copy the file at ``path`` into localStorage, so it is still there next visit."""
    if not IN_BROWSER or not os.path.exists(path):
        return
    with open(path, "rb") as handle:
        encoded = base64.b64encode(handle.read()).decode()
    _window().localStorage.setItem(_STORAGE_PREFIX + os.path.basename(path), encoded)


def restore_file(path: str) -> None:
    """Put back the copy :func:`keep_file` made of ``path`` on an earlier visit, if there is one."""
    if not IN_BROWSER:
        return
    encoded = _window().localStorage.getItem(_STORAGE_PREFIX + os.path.basename(path))
    if encoded:
        with open(path, "wb") as handle:
            handle.write(base64.b64decode(str(encoded)))
