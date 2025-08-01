"""Playing card class."""

from enum import IntEnum, StrEnum, auto
from typing import NamedTuple


class Suit(StrEnum):
    """Enum for all card suits."""

    C = auto()
    D = auto()
    H = auto()
    S = auto()


class Rank(IntEnum):
    """Enum for all card ranks."""

    ACE = auto()
    TWO = auto()
    THREE = auto()
    FOUR = auto()
    FIVE = auto()
    SIX = auto()
    SEVEN = auto()
    EIGHT = auto()
    NINE = auto()
    TEN = auto()
    JACK = auto()
    QUEEN = auto()
    KING = auto()


class Card(NamedTuple):
    """Union of rank and suit."""

    rank: Rank
    suit: Suit


def hand_value(hand: list[Card]) -> int:
    """Calculates the blackjack value of a list of cards.

    Args:
        hand: List of cards to calculate the value of.

    Returns:
        int: Blackjack card value.
    """
    value = 0
    for card in hand:
        if card.rank != Rank.ACE:
            match card.rank:
                case Rank.JACK | Rank.QUEEN | Rank.KING:
                    value += 10
                case Rank.ACE:
                    value += 1 if value + 11 > 21 else 11
                case (
                    number_card
                ):  # HACK: relies on the rank enum being in a specific order
                    value += number_card.value

    # count aces last to avoid edge cases
    for card in hand:
        if card.rank == Rank.ACE:
            value += 1 if value + 11 > 21 else 11
    return value
