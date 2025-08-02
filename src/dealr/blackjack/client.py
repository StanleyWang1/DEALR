"""Game logic server for blackjack."""

import random

import zmq

from dealr.blackjack import cards
from dealr.blackjack.game import Dealer
from dealr.blackjack.player import Player


def serve(num_players: int, **ports: dict[str, int]) -> None:
    """Spawns a blackjack 0MQ server/client.

    Args:
        num_players: Number of players to listen for.
        port: TCP port to listen on.
    """
    players = [Player(bet=100) for _ in range(num_players)]
    game = Dealer(players)
    context = zmq.Context()

    if "card-detector" in ports:
        card_detector_socket = context.socket(zmq.SUB)
        card_detector_socket.connect(f"tcp://localhost:{ports['card-detector']}")
        card_detector_socket.setsockopt_string(zmq.SUBSCRIBE, "")

    if "dispenser" in ports:
        dispenser_socket = context.socket(zmq.REQ)
        dispenser_socket.connect(f"tcp://localhost:{ports['dispenser']}")

    while True:
        player_hands: list[list[cards.Card]] = card_detector_socket.recv_pyobj()
        for player_id, hand in enumerate(player_hands):
            players[player_id].hand = hand

            amount = random.randint(-5, 5) * 100
            dispenser_socket.send_string(f"{player_id} {amount}")
            reply = dispenser_socket.recv_string()

            print(players[player_id].hand)
            print(reply)
