"""Game logic loop for blackjack."""

import argparse

import zmq

from dealr.blackjack import cards
from dealr.blackjack.dealer import Dealer, dealer_hand_value
from dealr.blackjack.player import Player


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-players", required=False, type=int, default=1)
    args = parser.parse_args()

    # context = zmq.Context()
    # socket = context.socket(zmq.SUB)
    # socket.connect("tcp://localhost:5555")
    # socket.setsockopt_string(zmq.SUBSCRIBE, args["num_players"] if "num_players" in args else "1")


if __name__ == "__main__":
    main()
