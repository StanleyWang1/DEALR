"""Publisher of card detector data."""

import itertools
import random
import time

import zmq

from dealr.blackjack import cards


def serve(num_players: int, port: int):
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(f"tcp://*:{port}")

    deck = [cards.Card(*args) for args in itertools.product(cards.Rank, cards.Suit)]

    while True:
        time.sleep(1)
        hands = [random.choices(deck, k=2) for _ in range(num_players)]
        socket.send_pyobj(hands)
