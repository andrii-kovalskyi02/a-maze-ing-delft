"""The four digits and the exit door (enabler #116, E7.3).

These test the mechanism, not the story: which room hands out which digit is
the room owner's business, and these tests keep working while they decide.
"""

from __future__ import annotations

import commands
import digits
import rooms  # noqa: F401  (importing rooms registers them)
import world
from game import Game


def carrying_everything() -> Game:
    """Return a game whose player has found all four digits."""
    game = Game(current="corridor_blue")
    for digit in digits.all_digits():
        game.carrying.add(digit.key)
    return game


def test_there_is_one_digit_per_colour() -> None:
    """E7.1: four digits, one for each passage, in the order the door reads them."""
    assert [digit.colour for digit in digits.all_digits()] == list(digits.ORDER)


def test_the_code_is_made_of_the_digits_themselves() -> None:
    """Nobody writes the code down twice: it is whatever the four digits show."""
    assert digits.code() == "".join(digit.value for digit in digits.all_digits())
    assert len(digits.code()) == len(digits.ORDER)


def test_a_digit_cannot_be_collected_twice() -> None:
    """E7.1: picking the same digit up again changes nothing."""
    game = Game()
    first = digits.all_digits()[0]
    game.carrying.add(first.key)
    game.carrying.add(first.key)
    assert len(game.carrying) == 1
    assert len(digits.carried(game)) == 1


def test_an_empty_backpack_knows_every_colour_is_missing() -> None:
    game = Game()
    assert digits.missing(game) == digits.ORDER
    assert digits.assemble(game) == digits.BLANK * len(digits.ORDER)
    assert not digits.is_complete(game)


def test_a_partial_code_shows_the_gaps_in_the_right_places() -> None:
    """E7.3: the player can see which colour they are still short of."""
    game = Game()
    blue, red = digits.all_digits()[0], digits.all_digits()[1]
    game.carrying.add(red.key)

    assert digits.assemble(game) == f"{digits.BLANK}{red.value}{digits.BLANK}{digits.BLANK}"
    assert blue.colour in digits.missing(game)
    assert red.colour not in digits.missing(game)
    assert not digits.opens_the_door(game)
    assert blue.colour in digits.summary(game)


def test_a_complete_code_is_the_code_the_door_wants() -> None:
    """E7.2: four digits in colour order is exactly the door's code."""
    game = carrying_everything()
    assert digits.is_complete(game)
    assert digits.assemble(game) == digits.code()
    assert digits.opens_the_door(game)


def test_the_exit_stays_shut_until_the_code_is_complete(console) -> None:
    """E7.2: US1e - an incomplete code is refused, and says what is missing."""
    game = Game(current="corridor_blue")
    door = world.get("stair_exit")

    assert not commands._code_opens_the_exit(game, door)
    assert "still missing" in console.output


def test_the_complete_code_opens_the_exit_and_ends_the_game(console) -> None:
    """E7.2: walking out of the building is the ending, with the final status."""
    game = carrying_everything()
    door = world.get("stair_exit")

    assert commands._code_opens_the_exit(game, door)
    game.move_to(door.key)
    game.finish()

    assert not game.running
    assert "out of the building" in console.output


def test_every_digit_a_room_hands_out_is_a_real_digit() -> None:
    """A boss whose reward is a digit must use one of the four in the catalogue.

    This is the test that catches ``reward="digit_3"`` when nobody has added
    digit 3 to ``ITEM_CATALOGUE`` yet.
    """
    known = {digit.key for digit in digits.all_digits()}
    for room in world.all_rooms():
        rewards = {room.approach_reward}
        if room.boss is not None:
            rewards |= {room.boss.reward, room.boss.lose_reward, room.boss.lose_reward_2}
        for reward in rewards - {None}:
            if reward.startswith("digit"):
                assert reward in known, (
                    f"{room.key} hands out {reward!r}, which is not one of the four digits"
                )
