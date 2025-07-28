"""FSM for a blackjack dealer."""

from dataclasses import dataclass
from enum import IntEnum, StrEnum, auto
from typing import NamedTuple

from statemachine import State, StateMachine


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


class Dealer(StateMachine):
    idle = State(initial=True)
    initial_deal = State()
    waiting_for_player = State()
    hitting_player = State()
    standing_player = State()
    resolving = State()
    concluding = State(final=True)

    starting_game = idle.to(initial_deal)
    player_action_start = initial_deal.to(waiting_for_player)
    player_action = waiting_for_player.to(hitting_player) | waiting_for_player.to(
        standing_player
    )
    next_player = hitting_player.to(waiting_for_player) | standing_player.to(
        waiting_for_player
    )
    resolve_dealer_hand = waiting_for_player.to(resolving, cond="all_players_done")
    settle_bets = resolving.to(concluding)

    def __init__(self, players: list[Player]) -> None:
        self.players = players
        super().__init__()

    def all_players_done(self) -> bool:
        all_standing = all(p.last_action == PlayerAction.STAND for p in self.players)
        all_busted = all(p.hand_value > 21 for p in self.players)
        return all_standing or all_busted
