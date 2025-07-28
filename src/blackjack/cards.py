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
