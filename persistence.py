"""Save and load game state using SQLite."""

from __future__ import annotations

import contextlib
import json
import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game


DATABASE_NAME = "game.db"


def get_connection() -> sqlite3.Connection:
    """Return a connection to the game database."""
    return sqlite3.connect(DATABASE_NAME)


def create_tables() -> None:
    """Create the game save table if it does not exist."""
    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS game_states (
            player_name TEXT PRIMARY KEY,
            current_room TEXT NOT NULL,
            inventory TEXT NOT NULL,
            hearts INTEGER NOT NULL,
            digits TEXT NOT NULL,
            visited_rooms TEXT NOT NULL,
            unlocked_rooms TEXT NOT NULL,
            defeated_challenges TEXT NOT NULL,
            taken_items TEXT NOT NULL,
            approached TEXT NOT NULL,
            elapsed_time REAL NOT NULL,
            completion INTEGER,
            finish_time REAL
        )
        """
    )

    for column in ("completion INTEGER", "finish_time REAL"):
        # An older game.db has no scoreboard columns yet; the error means it already has them.
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute(f"ALTER TABLE game_states ADD COLUMN {column}")

    connection.commit()
    connection.close()


def save_game(game: Game) -> None:
    """Save the complete state of a game."""
    inventory = [item.key for item in game.carrying]

    digits = [key for key in inventory if key.startswith("digit_")]

    taken_items = [[room, item] for room, item in game.taken]

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO game_states (
            player_name,
            current_room,
            inventory,
            hearts,
            digits,
            visited_rooms,
            unlocked_rooms,
            defeated_challenges,
            taken_items,
            approached,
            elapsed_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(player_name) DO UPDATE SET
            current_room = excluded.current_room,
            inventory = excluded.inventory,
            hearts = excluded.hearts,
            digits = excluded.digits,
            visited_rooms = excluded.visited_rooms,
            unlocked_rooms = excluded.unlocked_rooms,
            defeated_challenges = excluded.defeated_challenges,
            taken_items = excluded.taken_items,
            approached = excluded.approached,
            elapsed_time = excluded.elapsed_time
        """,
        (
            game.player_name,
            game.current,
            json.dumps(inventory),
            game.hearts.halves,
            json.dumps(digits),
            json.dumps(sorted(game.visited)),
            json.dumps(sorted(game.unlocked)),
            json.dumps(sorted(game.defeated)),
            json.dumps(taken_items),
            json.dumps(sorted(game.approached)),
            game.elapsed_time,
        ),
    )

    connection.commit()
    connection.close()


def save_score(player_name: str, completion: int, play_time: float) -> None:
    """Save a finished run's score on the player's row in game_states."""
    connection = get_connection()

    connection.execute(
        "UPDATE game_states SET completion = ?, finish_time = ? WHERE player_name = ?",
        (completion, play_time, player_name),
    )

    connection.commit()
    connection.close()


def top_scores() -> list[tuple[str, int, float]]:
    """Return the top 5 runs, best completion first, then fastest time."""
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT player_name, completion, finish_time
        FROM game_states
        WHERE completion IS NOT NULL
        ORDER BY completion DESC, finish_time ASC
        LIMIT 5
        """
    ).fetchall()

    connection.close()

    return rows


def load_game(player_name: str) -> Game | None:
    """Load a saved game for ``player_name`` if one exists."""
    connection = get_connection()

    row = connection.execute(
        """
        SELECT
            current_room,
            inventory,
            hearts,
            digits,
            visited_rooms,
            unlocked_rooms,
            defeated_challenges,
            taken_items,
            approached,
            elapsed_time
        FROM game_states
        WHERE player_name = ?
        """,
        (player_name,),
    ).fetchone()

    connection.close()

    if row is None:
        return None

    from game import Game
    from health import Health

    (
        current_room,
        inventory_json,
        hearts,
        digits_json,
        visited_json,
        unlocked_json,
        defeated_json,
        taken_json,
        approached_json,
        elapsed_time,
    ) = row

    game = Game(
        player_name=player_name,
        current=current_room,
        hearts=Health(hearts),
        visited=set(json.loads(visited_json)),
        unlocked=set(json.loads(unlocked_json)),
        defeated=set(json.loads(defeated_json)),
        taken={(room, item) for room, item in json.loads(taken_json)},
        approached=set(json.loads(approached_json)),
        elapsed_time=elapsed_time,
    )

    for item_key in json.loads(inventory_json):
        game.carrying.add(item_key)

    return game
