"""The leaderboard: the top 5 shown in the game, and the optional shared online one.

- ``scoreboard``: builds and shows the top 5 (US5).
- ``online``: uploads finished runs and fetches everyone's best five (Supabase).
- ``scores_online.sql``: the table to create in Supabase, once.

The local tables behind it live in ``persistence.py``, next to the saved games, because they share
the same ``game.db``.
"""
