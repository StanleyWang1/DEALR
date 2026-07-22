"""Server for chip dispenser."""

import time

import zmq


def serve(port: int) -> None:
    """Spawns a server for the chip dispenser."""

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{port}")

    while True:
        message = socket.recv_string()
        player, amount = tuple(int(i) for i in message.split())

        time.sleep(0.1)

        socket.send_string(f"Dispensed ${amount} to {player}")
