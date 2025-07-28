"""FSM for a blackjack dealer."""
import itertools
import random

from statemachine import State, StateMachine

from . import cards
from .player import Player, PlayerAction, PlayerStatus


def dealer_hand_value(hand: list[cards.Card]) -> int:
    value = 0
    for card in hand:
        match card.rank:
            case cards.Rank.JACK | cards.Rank.QUEEN | cards.Rank.KING:
                value += 10
            case cards.Rank.ACE:
                value += 11 if 17 < value + 11 < 21 else 1
            case number_card:
                value += number_card.value
    return value


class Dealer(StateMachine):
    idle = State(initial=True)
    initial_deal = State()
    waiting_for_player = State()
    resolving = State(final=True)

    start_game = idle.to(initial_deal)
    player_action_start = initial_deal.to(waiting_for_player)
    player_hits = waiting_for_player.to(waiting_for_player)
    player_stands = waiting_for_player.to(waiting_for_player)
    resolve_dealer_hand = waiting_for_player.to(resolving, cond="all_players_done", final=True)

    def __init__(self, players: list[Player]) -> None:
        self.players = players
        self.deck = list(itertools.product(cards.Rank, cards.Suit))
        self.hand: list[cards.Card] = []
        self.player_index = 0
        super().__init__()

    def all_players_done(self) -> bool:
        all_standing = all(p.last_action == PlayerAction.STAND for p in self.players if p.status == PlayerStatus.ACTIVE)
        all_busted = all(p.status == PlayerStatus.BUSTED for p in self.players)
        return all_standing or all_busted
    
    def before_start_game(self) -> None:
        random.shuffle(self.deck)
        # TODO: add hardware shuffling
        for _ in range(2):
            for player in self.players:
                card = self.deck.pop()
                player.hand.append(card)
            dealer_card = self.deck.pop()
            self.hand.append(dealer_card)
        
    def on_exit_waiting_for_player(self) -> None:
        self.player_index = (self.player_index + 1) % len(self.players)

    def on_player_hits(self) -> None:
        player = self.players[self.player_index]
        card = self.deck.pop()
        player.hand.append(card)
        player.last_action = PlayerAction.HIT
        if cards.hand_value(player.hand) > 21:
            player.status = PlayerStatus.BUSTED

    def on_player_stands(self, player: Player) -> None:
        player.last_action = PlayerAction.STAND

    def on_resolve_dealer_hand(self) -> None:
        while dealer_hand_value(self.hand) < 17:
            card = self.deck.pop()
            self.hand.append(card)
        # TODO: settle bets
