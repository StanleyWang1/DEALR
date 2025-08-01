from pathlib import Path
import threading
import time

import tomli

import dealr.card_detector.server as cd_server
import dealr.blackjack.server as bj_server


def main() -> None:
    ports_file = Path("ports.toml")
    ports = tomli.loads(ports_file.read_text(encoding="utf-8"))
    card_detector_pub = threading.Thread(
        target=cd_server.serve, args=(1, ports["card-detector"]), daemon=True
    )
    blackjack_logic = threading.Thread(
        target=bj_server.serve, args=(1, ports["card-detector"]), daemon=True
    )

    card_detector_pub.start()
    blackjack_logic.start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
