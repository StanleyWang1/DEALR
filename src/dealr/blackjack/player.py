"""Player class."""

from dataclasses import dataclass
from enum import StrEnum, auto

from dealr.blackjack.cards import Card


class PlayerAction(StrEnum):
    """Enum of possible player actions."""
    HIT = auto()
    STAND = auto()


class PlayerStatus(StrEnum):
    """Enum of possible player statuses."""
    ACTIVE = auto()
    BUSTED = auto()


@dataclass
class Player:
    """Player record class."""
    hand: list[Card]
    bet: int
    last_action: PlayerAction
    status: PlayerStatus = PlayerStatus.ACTIVE
