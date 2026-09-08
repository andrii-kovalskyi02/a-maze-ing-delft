# -----------------------------------------------------------------------------
# File: utils.py
# ACS School Project - Simple Maze Example
# Organization: THUAS (The Hague University of Applied Sciences)
# Location: Delft
# Date: July 2025
# -----------------------------------------------------------------------------

import os

def clearScreen():
    if os.getenv("PYCHARM_HOSTED"):
        print("\n" * 50)  # fallback for PyCharm
    else:
        os.system('cls' if os.name == 'nt' else 'clear')

def chooseNextRoom(choices):
    print("\n🔀 Choose a door:")
    for i, room in enumerate(choices, start=1):
        print(f"{i}. {room}")
    choice = input("Enter the number of your choice: ")

    try:
        index = int(choice) - 1
        if 0 <= index < len(choices):
            clearScreen()  # ✅ Clear screen before entering the selected room
            return choices[index]
        else:
            print("Invalid choice.")
            return None
    except ValueError:
        print("Invalid input.")
        return None
