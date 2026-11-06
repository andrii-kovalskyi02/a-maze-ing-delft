"""Who may play as a name: registering a name with a password, and checking that password.

With Supabase set up (``cloud.py``), accounts live online in a ``players`` table that nobody can
read: the game only calls the database functions in ``supabase/accounts.sql``, which hash the
password on the server (bcrypt) and lock a name for a minute after five wrong guesses. So a name is
the same player on every computer, and no password hash is ever stored on a player's computer.

Without Supabase (the tests, or a copy of the game with no project set up), the hashes are kept in
the local database instead - see ``persistence.set_password``.
"""

from __future__ import annotations

import cloud
import persistence


class Unreachable(Exception):
    """The account server could not be reached, so a password cannot be checked or kept."""


class Locked(Exception):
    """Too many wrong passwords in a row: the name is locked for a minute."""


def _call(function: str, **arguments: object) -> object:
    """Run an account function on the server, turning any network problem into Unreachable."""
    try:
        return cloud.call(function, **arguments)
    except (OSError, ValueError) as error:  # no connection, an error reply, or a garbled one
        raise Unreachable(str(error)) from error


def taken(name: str) -> bool:
    """Return True if ``name`` belongs to somebody: here, by a save or a score, or online."""
    if persistence.player_exists(name):
        return True
    return cloud.enabled() and bool(_call("player_exists", player_name=name))


def has_password(name: str) -> bool:
    """Return True if ``name`` has a password. Players from before passwords existed do not."""
    if cloud.enabled():
        return bool(_call("player_exists", player_name=name))
    return persistence.has_password(name)


def set_password(name: str, password: str) -> bool:
    """Give ``name`` its password. False if somebody else registered that name first."""
    if cloud.enabled():
        return bool(_call("register_player", player_name=name, password=password))
    persistence.set_password(name, password)
    return True


def password_matches(name: str, password: str) -> bool:
    """Return True if ``password`` is ``name``'s password.

    Raises:
        Locked: Online, after too many wrong passwords in a row.
    """
    if not cloud.enabled():
        return persistence.password_matches(name, password)
    answer = _call("check_password", player_name=name, password=password)
    if answer == "locked":
        raise Locked
    return answer == "ok"
