# -----------------------------------------------------------------------------
# File: classroom2015.py
# ACS School Project - Simple Maze Example
# Organization: THUAS (The Hague University of Applied Sciences)
# Location: Delft
# Date: July 2025
# -----------------------------------------------------------------------------

import sys
from .utils import chooseNextRoom

def enterClassroom2015(state):
    print("\n🏫 You step into Classroom 2.015.")
    print("The classroom is filled with students. A teacher turns toward you, visibly annoyed.")
    print("The door creaks shut behind you. Everyone is looking at you; it's completely silent.")

    # --- Helperfuncties voor commandoverwerking ---

    def handle_look():
        print("\nYou take a careful look around the room.")
        print("At the front is a whiteboard completely filled with formulas.")
        print("Desks with students are arranged in neat rows, though one chair is oddly turned toward the window.")
        print("On the teacher's desk, a calculator is lying in a strange position on the table.")
        if not state["visited"]["classroom2015"]:
            print("The teacher says, you are late! And he asks you a question:")
            print("\"What is 7 * 6?\"")
        else:
            print("The teacher sighs: You again? You already solved the challenge.")
            if "key" not in state["inventory"]:
                print("On the desk, beneath the calculator, something metallic glints. It looks like a small key.")
            else:
                print("The desk is empty. You've already taken the key.")
        print("- Possible exits: corridor")
        print("- Your current inventory:", state["inventory"])

    def handle_help():
        print("\nAvailable commands:")
        print("- look around         : Examine the room and its contents.")
        if not state["visited"]["classroom2015"]:
            print("- answer <number>     : Attempt to solve the math question.")
        if state["visited"]["classroom2015"] and "key" not in state["inventory"]:
            print("- take key            : Pick up the key once it's revealed.")
        print("- go corridor / back  : Leave the room and return to the corridor.")
        print("- ?                   : Show this help message.")
        print("- quit                : Quit the game entirely.")

    def handle_take(item):
        if item == "key":
            if not state["visited"]["classroom2015"]:
                print("❌ There's no key visible yet. Maybe solving the puzzle will reveal more.")
            elif "key" in state["inventory"]:
                print("You already have the key in your backpack.")
            else:
                print("🔑 You lift the calculator from te desk and find a small brass key underneath.")
                print("You take it and tuck it safely into your backpack.")
                state["inventory"].append("key")
        else:
            print(f"There is no '{item}' here to take.")

    def handle_go(destination):
        if destination in ["corridor", "back"]:
            print("🚪 You open the door and step back into the corridor.")
            return "corridor"
        else:
            print(f"❌ You can't go to '{destination}' from here.")
            return None

    def handle_answer(answer):
        if state["visited"]["classroom2015"]:
            print("✅ You've already solved this challenge.")
        elif answer == "42":
            print("✅ Correct! The teacher invites you to the desk.")
            state["visited"]["classroom2015"] = True
            print("Suddenly you see something on the desk.")
        else:
            print("❌ Incorrect. The teacher opens the door of the classroom.")
            print("You are gently guided back into the corridor.")
            return "corridor"

    # --- Commandoloop ---
    while True:
        command = input("\n> ").strip().lower()

        if command == "look around":
            handle_look()

        elif command == "?":
            handle_help()

        elif command.startswith("take "):
            item = command[5:].strip()
            handle_take(item)

        elif command.startswith("go "):
            destination = command[3:].strip()
            result = handle_go(destination)
            if result:
                return result

        elif command.startswith("answer "):
            answer = command[7:].strip()
            result = handle_answer(answer)
            if result:
                return result

        elif command == "quit":
            print("👋 You drop your backpack, leave the maze behind, and step back into the real world.")
            sys.exit()

        else:
            print("❓ Unknown command. Type '?' to see available commands.")
