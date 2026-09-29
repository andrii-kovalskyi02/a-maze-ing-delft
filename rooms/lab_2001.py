from __future__ import annotations

from models import Area, Boss, Inspectable, Question, Room

ROOM = Room(
    key="lab_room_3",
    name="Forest room",
    area=Area.BLUE,
    description="It's a classroom filled with grass and vines."
                " There is no one inside it except a tree sits in the center of it.",
    look_around=(
        "there are many small animals around the room, rabbits,foxes,birds and other small creatures. "
        "Most of them are gathered around the tree."
        "Past the tree, you can see a glistening object on the teacher desk. "
    ),
    exits=("corridor_red",),
    requires="digit_2",
    locked_text="The door is locked. Something with a blue stripe would help.",
    inspectables=(
        Inspectable(name="poster", text="A dont give up cat poster, curling at the corners."),
    ),
    items=(),
    boss=Boss(
        name="tree guard",
        intro="The tree shakes as a loud voice came out of it"
              "If you want to take the key you have answer our quizzes three!! Or 5.",
        questions=(
            Question(
                prompt=" On what day does autumn start?",
                answers=("September 21st", "October 10th ", "December 1st"),
            ),
            Question(
                prompt="What is the fastest animal on earth?",
                answers=("the 2nd",),
                choices=("Chetahs", "Peregrine falcons ", "Horse flies", "cockroaches"),
            ),
            Question(
                prompt="What is the largest fish on earth?",
                answers=("the 1nd",),
                choices=("Whale shark", "Manta ray", "Great white shark"),
            ),
             Question(
                prompt="Which animal species can live in extremes of both heat and cold, from −28 °C to 49 °C?",
                answers=("the 3nd",),
                choices=("Polar bear", "iguana", "Camel"),
            ),
            Question(
                prompt="What is the tallest tree on earth?",
                answers=("the 2nd",),
                choices=("Lincoln", "General sherman", "Cedar "),
            ),
    ),
        win_text="a hamster came out of the tree to congratulate you "
                 "'you've proven yourself. you can take the key.'",
        lose_text="you did not take the key and you were flung out of the room.",
        reward="digit_3",
    ),
)
