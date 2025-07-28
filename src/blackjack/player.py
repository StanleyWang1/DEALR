from dataclasses import dataclass
from enum import StrEnum, auto

from .cards import Card


class PlayerAction(StrEnum):
    HIT = auto()
    STAND = auto()


class PlayerStatus(StrEnum):
    ACTIVE = auto()
    BUSTED = auto()


@dataclass
class Player:
    hand: list[Card]
    bet: int
    last_action: PlayerAction
    status: PlayerStatus = PlayerStatus.ACTIVE