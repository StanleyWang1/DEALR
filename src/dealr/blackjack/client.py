"""Game logic server for blackjack."""

import zmq

from dealr.blackjack import cards
from dealr.blackjack.game import Dealer
from dealr.blackjack.player import Player


def serve(num_players: int, port: int) -> None:
    """Spawns a blackjack 0MQ server/client.

    Args:
        num_players: Number of players to listen for.
        port: TCP port to listen on.
    """
    players = [Player(bet=100) for _ in range(num_players)]
    game = Dealer(players)
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect(f"tcp://localhost:{port}")
    socket.setsockopt_string(zmq.SUBSCRIBE, "")

    while True:
        player_hands: list[list[cards.Card]] = socket.recv_pyobj()
        print(player_hands)
        for player_id, hand in enumerate(player_hands):
            players[player_id].hand = hand
