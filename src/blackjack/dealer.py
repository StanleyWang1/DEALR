"""FSM for a blackjack dealer."""
from statemachine import State, StateMachine

from .player import Player, PlayerAction


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
