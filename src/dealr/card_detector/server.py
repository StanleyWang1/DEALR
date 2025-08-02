"""Publisher of card detector data."""

import itertools
import random
import time

import zmq

from dealr.blackjack import cards


def serve(num_players: int, port: int):
    """Spawns publisher for card detector results.
    Data is in the form of a 2D array where each
    element is a list of the given player's hand.

    Args:
        num_players: Number of players to send on.
        port: Port to send data onto.
    """
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(f"tcp://*:{port}")

    deck = [cards.Card(*args) for args in itertools.product(cards.Rank, cards.Suit)]

    while True:
        hands = [random.choices(deck, k=2) for _ in range(num_players)]  # TODO: get list of hands from CV predictor
        socket.send_pyobj(hands)
