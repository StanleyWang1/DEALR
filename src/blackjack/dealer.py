"""FSM for a blackjack dealer."""

import itertools
import random

from statemachine import State, StateMachine

from . import cards
from .player import Player, PlayerAction, PlayerStatus

DEALER_LIMIT = 17
BLACKJACK = 21


def dealer_hand_value(hand: list[cards.Card]) -> int:
    value = 0
    for card in hand:
        match card.rank:
            case cards.Rank.JACK | cards.Rank.QUEEN | cards.Rank.KING:
                value += 10
            case cards.Rank.ACE:
                value += 11 if DEALER_LIMIT < value + 11 < BLACKJACK else 1
            case number_card:
                value += number_card.value
    return value


class Dealer(StateMachine):
    idle = State(initial=True)
    initial_deal = State()
    waiting_for_player = State()
    resolving_dealer = State()
    done = State(final=True)

    start_game = idle.to(initial_deal)
    player_action_start = initial_deal.to(waiting_for_player)
    player_hits = waiting_for_player.to.itself()
    player_stands = waiting_for_player.to.itself()
    player_blackjack = waiting_for_player.to(done, cond="player_has_blackjack")
    resolve_dealer_hand = waiting_for_player.to(
        resolving_dealer, cond="all_players_done"
    )
    settling_bets = resolve_dealer_hand.to(done)

    def __init__(self, players: list[Player]) -> None:
        self.players = players
        self.deck = list(itertools.product(cards.Rank, cards.Suit))
        self.hand: list[cards.Card] = []
        self.player_index = 0
        super().__init__()

    def all_players_done(self) -> bool:
        all_standing = all(
            p.last_action == PlayerAction.STAND
            for p in self.players
            if p.status == PlayerStatus.ACTIVE
        )
        all_busted = all(p.status == PlayerStatus.BUSTED for p in self.players)
        return all_standing or all_busted

    def player_has_blackjack(self) -> bool:
        return any(cards.hand_value(p.hand) == BLACKJACK for p in self.players)

    def on_start_game(self) -> None:
        random.shuffle(self.deck)
        # TODO: add hardware shuffling
        for _ in range(2):
            for player in self.players:
                card = self.deck.pop()
                player.hand.append(card)
            dealer_card = self.deck.pop()
            self.hand.append(dealer_card)

    def on_player_hits(self) -> None:
        player = self.players[self.player_index]
        card = self.deck.pop()
        player.hand.append(card)
        player.last_action = PlayerAction.HIT
        if cards.hand_value(player.hand) > BLACKJACK:
            player.status = PlayerStatus.BUSTED
            player.bet = 0
        self.player_index = (self.player_index + 1) % len(self.players)

    def on_player_stands(self, player: Player) -> None:
        player.last_action = PlayerAction.STAND
        self.player_index = (self.player_index + 1) % len(self.players)

    def on_resolve_dealer_hand(self) -> None:
        while dealer_hand_value(self.hand) < DEALER_LIMIT:
            card = self.deck.pop()
            self.hand.append(card)

    def on_player_blackjack(self) -> None:
        active_players = [p for p in self.players if p.status == PlayerStatus.ACTIVE]
        if cards.hand_value(self.hand) != BLACKJACK:
            for p in active_players:
                if cards.hand_value(p.hand) == BLACKJACK:
                    p.bet = p.bet + p.bet // 2

    def on_settling_bets(self) -> None:
        dealer_value = dealer_hand_value(self.hand)
        active_players = [p for p in self.players if p.status == PlayerStatus.ACTIVE]
        if dealer_value > BLACKJACK:
            for p in active_players:
                p.bet *= 2
        else:
            for p in active_players:
                player_value = cards.hand_value(p.hand)
                if player_value > dealer_value:
                    p.bet *= 2
                elif player_value < dealer_value:
                    p.bet = 0
