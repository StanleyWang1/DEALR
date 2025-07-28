from dataclasses import dataclass
from enum import StrEnum, auto

from .cards import Card, Rank

class PlayerAction(StrEnum):
    HIT = auto()
    STAND = auto()


@dataclass
class Player:
    hand: list[Card]
    bet: int
    last_action: PlayerAction

    @property
    def hand_value(self) -> int:
        value = 0
        for card in self.hand:
            match card.rank:
                case Rank.JACK | Rank.QUEEN | Rank.KING:
                    value += 10
                case Rank.ACE:
                    value += 1 if value > 11 else 11
                case number_card:
                    value += number_card.value
        return value