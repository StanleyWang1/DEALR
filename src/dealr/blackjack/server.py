"""Game logic loop for blackjack."""

import argparse

import zmq

from dealr.blackjack import cards
from dealr.blackjack.dealer import Dealer, dealer_hand_value
from dealr.blackjack.player import Player


def serve(num_players: int, port: int) -> None:
    players = [Player(bet=100) for _ in range(num_players)]
    game = Dealer(players)
    context = zmq.Context()
    sockets = [context.socket(zmq.SUB) for _ in range(num_players)]
    for player_id, socket in enumerate(sockets):
        socket.connect(f"tcp://localhost:{port}")
        socket.setsockopt_string(zmq.SUBSCRIBE, str(player_id))
    
    while True:
        for player_id, socket in enumerate(sockets):
            player_hand: list[cards.Card] = socket.recv_json()
            players[player_id].hand = player_hand
            

if __name__ == "__main__":
    main()
