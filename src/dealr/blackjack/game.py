"""FSM for a blackjack dealer."""

import itertools
import queue
import random

from statemachine import State, StateMachine

from dealr.blackjack import cards
from dealr.blackjack.player import Player, PlayerAction, PlayerStatus

DEALER_LIMIT = 17
BLACKJACK = 21


def dealer_hand_value(hand: list[cards.Card]) -> int:
    """Calculates the value of the dealer's hand taking into account ace hard 11s.

    Args:
        hand: Dealer's current end.

    Returns:
        int: Value of the hand.
    """
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
    """State machine for a blackjack dealer."""

    idle = State(initial=True)
    waiting_for_player = State()
    resolving_dealer = State()
    done = State(final=True)

    start_game = idle.to(waiting_for_player)
    player_hits = waiting_for_player.to.itself()
    player_stands = waiting_for_player.to.itself()
    dealer_blackjack = waiting_for_player.to(done)
    player_blackjack = waiting_for_player.to(done)
    resolve_dealer_hand = waiting_for_player.to(resolving_dealer)
    settle_bets = resolving_dealer.to(done)

    def __init__(self, players: list[Player]) -> None:
        self.players = players
        self.deck = list(
            cards.Card(*args) for args in itertools.product(cards.Rank, cards.Suit)
        )
        self.hand: list[cards.Card] = []
        self.player_queue: queue.SimpleQueue[Player] = queue.SimpleQueue()
        for p in self.players:
            self.player_queue.put(p)
        super().__init__()

    def player_has_blackjack(self) -> bool:
        """Check for any blackjacks.

        Returns:
            bool: If any players have a blackjack.
        """
        return any(cards.hand_value(p.hand) == BLACKJACK for p in self.players)

    def on_start_game(self) -> None:
        """Deal the initial cards from the deck, dealers included."""
        random.shuffle(self.deck)
        # TODO: add hardware shuffling
        for _ in range(2):
            for player in self.players:
                card = self.deck.pop()
                player.hand.append(card)  # TODO: deal card
            dealer_card = self.deck.pop()
            self.hand.append(dealer_card)

    def on_enter_waiting_for_player(self) -> None:
        """Automatically check and transition to done state."""
        self.current_player = self.player_queue.get()

        if cards.hand_value(self.hand) == BLACKJACK:
            self.dealer_blackjack()
        if self.player_has_blackjack():
            self.player_blackjack()
        if self.player_queue.empty():
            self.resolve_dealer_hand()

    def on_player_hits(self) -> None:
        """Give players a card."""
        card = self.deck.pop()
        self.current_player.hand.append(card)
        self.current_player.last_action = PlayerAction.HIT
        if cards.hand_value(self.current_player.hand) > BLACKJACK:
            self.current_player.status = PlayerStatus.BUSTED
            self.current_player.bet = 0  # TODO: collect chips
        else:
            self.player_queue.put(self.current_player)

    def on_player_stands(self) -> None:
        """Does nothing but updates the player indices and state."""
        self.current_player.last_action = PlayerAction.STAND

    def on_resolve_dealer_hand(self) -> None:
        """Draws to the dealer until 17."""
        while dealer_hand_value(self.hand) < DEALER_LIMIT:
            card = self.deck.pop()
            self.hand.append(card)
        self.settle_bets()

    def on_player_blackjack(self) -> None:
        """Automatically finishes the game and pays out to all blackjacked players."""
        active_players = [p for p in self.players if p.status == PlayerStatus.ACTIVE]
        if cards.hand_value(self.hand) != BLACKJACK:
            for p in active_players:
                if cards.hand_value(p.hand) == BLACKJACK:
                    p.bet = p.bet + p.bet // 2  # TODO: deal out chips

    def on_settle_bets(self) -> None:
        """Settles bets after game conclusion."""
        dealer_value = dealer_hand_value(self.hand)
        active_players = [p for p in self.players if p.status == PlayerStatus.ACTIVE]
        if dealer_value > BLACKJACK:
            for p in active_players:
                p.bet *= 2  # TODO: deal out chips
        else:
            for p in active_players:
                player_value = cards.hand_value(p.hand)
                if player_value > dealer_value:
                    p.bet *= 2  # TODO: deal out chips
                elif player_value < dealer_value:
                    p.bet = 0  # TODO: collect chips
