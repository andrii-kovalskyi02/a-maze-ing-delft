"""The Pygame window the game runs in: ``python main_pygame.py``.

The real console game (``main.py``) runs unchanged in a background thread. Only its stdout and
stdin are swapped for fakes, so it never knows it is not in a terminal. Each module here does
one job:

- ``window``: ``TerminalWindow``, the main loop. It owns the state, reads keys and draws a frame.
- ``game_bridge``: the fake stdout/stdin, and starting the game thread.
- ``text``: fonts, and drawing a line of text (with its shadow and odd characters).
- ``dialogue_box``: the hand-drawn speech bubble the story is told in.
- ``speaker``: the cloud with the speaker's face that pops up beside the bubble.
- ``pause_menu``: the Escape menu, and the cog in the corner that points to it.
- ``map_view``: the drawn floor map (the M key), and the little map in the corner.
- ``room_fade``: the fade to black and back when walking into another room.
- ``sounds``: the typing blips, the menu tick and the one-off cue sounds.
- ``assets``: finding and loading the files in ``assets/``.
"""
