"""Main driver for DEALR stack."""

import argparse
import threading
import time
from pathlib import Path

import tomli

import dealr.blackjack.client as bj_client
import dealr.card_detector.server as cd_server
import dealr.dispenser.server as ds_server


def main() -> None:
    """Spawns all necessary threads."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--num-players", type=int, default=1, required=False)
    args = parser.parse_args()

    ports_file = Path.cwd() / "src" / "dealr" / "ports.toml"
    ports = tomli.loads(ports_file.read_text(encoding="utf-8"))
    card_detector_pub = threading.Thread(
        target=cd_server.serve, args=(args.num_players, ports["card-detector"]), daemon=True
    )
    dispenser_server = threading.Thread(
        target=ds_server.serve, args=(ports["dispenser"],), daemon=True
    )
    blackjack_logic = threading.Thread(
        target=bj_client.serve, args=(args.num_players,), kwargs=ports, daemon=True
    )

    card_detector_pub.start()
    blackjack_logic.start()
    dispenser_server.start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
