from enum import IntEnum, StrEnum, auto
from typing import NamedTuple


class Suit(StrEnum):
    C = auto()
    D = auto()
    H = auto()
    S = auto()


class Rank(IntEnum):
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
    rank: Rank
    suit: Suit


def hand_value(hand: list[Card]) -> int:
    value = 0
    for card in hand:
        match card.rank:
            case Rank.JACK | Rank.QUEEN | Rank.KING:
                value += 10
            case Rank.ACE:
                value += 1 if value + 11 > 21 else 11
            case number_card:  # HACK: relies on the rank enum being in a specific order
                value += number_card.value
    return value
