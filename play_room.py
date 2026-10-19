"""Play the game starting in one room, to try it out: run this file (in PyCharm, right-click > Run).

Change ROOM below to the room you want. Nothing from the run is saved or put on the scoreboard.
You can also name the room when running it: ``python play_room.py lab_2003``.

The rooms:
    classroom_2015   classroom_2021   classroom_2031   classroom_2035
    corridor_blue    corridor_red     front_desk_office
    lab_2001 (Forest room)            lab_2003         lobby
    project_room_1   projectroom_2    projectroom_3    stair_exit
    storage          student_society  teacher_rooms    teachers_room_4
"""

import os
import sys

ROOM = "lab_2001"

os.environ["AMAZE_START_ROOM"] = sys.argv[1] if len(sys.argv) > 1 else ROOM
import main_pygame  # noqa: E402  (it reads the variable above when the game starts)

main_pygame.TerminalWindow().run()
