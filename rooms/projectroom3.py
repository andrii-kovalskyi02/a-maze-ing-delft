
# -----------------------------------------------------------------------------
# File: projectroom3.py
# ACS School Project - Simple Maze Example
# Organization: THUAS (The Hague University of Applied Sciences)
# Location: Delft
# Date: July 2025
# -----------------------------------------------------------------------------

import sys
from .utils import chooseNextRoom

def enterProjectRoom3(state):
    # --- Check if the player has the key to enter ---
    if not state["visited"]["projectroom3"]:
        if "key" not in state["inventory"]:
            print("\n🚪 The door to Project Room 3 is locked.")
            print("You jiggle the handle. It's no use.")
            print("🔐 You need a key. Perhaps it's hidden elsewhere in the school?")
            return "corridor"
        else:
            print("\n🗝️ You insert the brass key into the lock and turn it with a satisfying click.")
            print("The door creaks open to reveal a bright and lively workspace.")

    # --- Room entry description ---
    print("\n🏗️ You enter Project Room 3.")
    print("Several tables are pushed together, covered in papers, laptops, and half-eaten snacks.")
    print("A group of students is finishing a project while chatting and laughing.")

    # --- Command handlers ---

    def handle_look():
        """Describe the room and give clues."""
        print("\nYou scan the room.")
        print("The walls are covered in sticky notes, whiteboards are full of pseudocode and diagrams.")
        if not state["visited"]["projectroom3"]:
            print("Near the snack table, one student holds up a fruit and says:")
            print("'You know what they say... which fruit keeps the doctor away?'")
            print("Another grins and says, 'Classic. We always bring them during hackathons.'")
            print("Seems like a riddle. Maybe it's part of the challenge?")
        else:
            print("The students have left. Only empty wrappers and a few notebooks remain.")
        print("- Possible exits: corridor")
        print("- Your current inventory:", state["inventory"])

    def handle_help():
        """List available commands."""
        print("\nAvailable commands:")
        print("- look around         : Examine the room for clues.")
        if not state["visited"]["projectroom3"]:
            print("- answer <fruit>      : Solve the riddle about the fruit.")
        print("- go corridor / back  : Leave the room and return to the corridor.")
        print("- ?                   : Show this help message.")
        print("- quit                : Quit the game completely.")

    def handle_go(destination):
        """Handle movement out of the room."""
        if destination in ["corridor", "back"]:
            print("You step away from the lively room and return to the corridor.")
            return "corridor"
        else:
            print(f"❌ You can't go to '{destination}' from here.")
            return None

    def handle_answer(answer):
        """Handle the fruit riddle."""
        if state["visited"]["projectroom3"]:
            print("✅ You've already completed this room.")
            return None
        normalized = answer.strip().lower()
        if normalized in ["apple", "an apple", "apples"]:
            print("✅ Correct! One of the students claps. 'Of course. Apples every time.'")
            state["visited"]["projectroom3"] = True
            state["previous_room"] = "projectroom3"
            print("\n🎉 CONGRATULATIONS!")
            print("You've explored all the essential rooms of the school.")
            print("Your adventure through logic, memory, and mystery ends here.")
            print("\n🏆 You completed the game! 🏆")
            sys.exit()
        else:
            print("❌ The student shrugs. 'Nope, that one's not it. Think classic.'")
            print("You decide to step out and think it over.")
            return "corridor"

    # --- Main command loop ---
    while True:
        command = input("\n> ").strip().lower()

        if command == "look around":
            handle_look()

        elif command == "?":
            handle_help()

        elif command.startswith("go "):
            destination = command[3:].strip()
            result = handle_go(destination)
            if result:
                return result

        elif command.startswith("answer "):
            guess = command[7:].strip()
            result = handle_answer(guess)
            if result:
                return result

        elif command == "quit":
            print("👋 You close your notebook and leave the project behind. Game over.")
            sys.exit()

        else:
            print("❓ Unknown command. Type '?' to see available commands.")
