"""Player class."""

from dataclasses import dataclass, field
from enum import StrEnum, auto

from dealr.blackjack.cards import Card


class PlayerAction(StrEnum):
    """Enum of possible player actions."""

    HIT = auto()
    STAND = auto()


@dataclass
class Player:
    """Player record class."""

    bet: int
    last_action: PlayerAction | None = None
    hand: list[Card] = field(default_factory=list)
    active: bool = True
