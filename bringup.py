"""Interactive hold and home-position test for the DEALR arm."""

from __future__ import annotations

import argparse
import os
import sys
import time

from serial.tools import list_ports

from arm import ALL_IDS, HOME_POSITIONS, Arm
from dynamixel_bus import DynamixelBus, DynamixelError


HOME_DURATION_SECONDS = 3.0
HOME_COMMAND_HZ = 200
ANSI_SHOW_CURSOR = "\033[?25h"


def available_ports() -> list[tuple[str, str]]:
    return [(port.device, port.description) for port in list_ports.comports()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Configure the DEALR arm, hold its pose, and optionally home it."
    )
    parser.add_argument(
        "--port",
        default=os.environ.get("DEALR_PORT"),
        help="U2D2 serial port, for example /dev/cu.usbserial-FT89FILY or COM8",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=1_000_000,
        help="Dynamixel baud rate (default: 1000000)",
    )
    parser.add_argument(
        "--list-ports",
        action="store_true",
        help="list serial ports and exit",
    )
    args = parser.parse_args()
    if not args.list_ports and not args.port:
        parser.error("--port is required (use --list-ports to find it)")
    return args


def print_ports() -> None:
    ports = available_ports()
    if not ports:
        print("No serial ports found.")
        return
    for device, description in ports:
        print(f"{device:<32} {description}")


def interpolate_positions(
    start_positions: dict[int, int],
    goal_positions: dict[int, int],
    progress: float,
) -> dict[int, int]:
    return {
        motor_id: round(
            start + progress * (goal_positions[motor_id] - start)
        )
        for motor_id, start in start_positions.items()
    }


def move_home(arm: Arm) -> None:
    arm.prepare_position_ramp()
    start_positions = arm.read_positions()
    step_count = round(HOME_DURATION_SECONDS * HOME_COMMAND_HZ)
    step_period = 1.0 / HOME_COMMAND_HZ

    for step in range(1, step_count + 1):
        cycle_started = time.monotonic()
        progress = step / step_count
        arm.command_positions(
            interpolate_positions(start_positions, HOME_POSITIONS, progress)
        )
        cycle_time = time.monotonic() - cycle_started
        time.sleep(max(0.0, step_period - cycle_time))

    arm.command_positions(HOME_POSITIONS, verify=True)
    arm.set_position_reference(HOME_POSITIONS)


def run_hold_test(port: str, baud: int) -> None:
    with DynamixelBus(port, baudrate=baud) as bus:
        arm = Arm(bus)
        print(
            "Connected. Verifying, rebooting, and configuring all motors "
            "with torque OFF..."
        )
        positions = arm.configure_for_current_pose_hold()

        print("\nCaptured positions:")
        for motor_id in ALL_IDS:
            print(f"  ID {motor_id:>2}: {positions[motor_id]}")
        print("\nThe arm must remain physically supported.")
        input("Press Enter to ENABLE torque and hold this exact pose... ")

        enable_attempted = False
        try:
            enable_attempted = True
            arm.enable_torque()
            while True:
                command = input(
                    "Command [h + Enter = home, blank Enter = torque off]: "
                ).strip().lower()
                if command == "":
                    break
                if command == "h":
                    move_home(arm)
                else:
                    print(f"Unknown command: {command!r}")
        except KeyboardInterrupt:
            pass
        finally:
            if enable_attempted:
                print("Disabling torque...")
                arm.disable_torque()
            print("Torque disabled. Serial port closed.")


def main() -> None:
    args = parse_args()
    if args.list_ports:
        print_ports()
        return

    try:
        run_hold_test(args.port, args.baud)
    except DynamixelError as error:
        sys.stdout.write(ANSI_SHOW_CURSOR)
        print(f"\nDynamixel error: {error}", file=sys.stderr)
        print("Keep the arm supported and disconnect 12 V if its state is uncertain.")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
