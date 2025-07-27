import time
import logging
from enum import Enum, auto
from typing import Optional

from dynamixel_controller import DynamixelController
import control_table


class DispenserState(Enum):
    """Possible dispenser states."""

    OFF = auto()
    ON = auto()
    IDLE = auto()
    HOMING = auto()
    DISPENSING = auto()
    LOADING = auto()
    ERROR = auto()


ALLOWED_TRANSITIONS = {
    DispenserState.OFF: [DispenserState.ON, DispenserState.ERROR],
    DispenserState.ON: [DispenserState.OFF, DispenserState.HOMING, DispenserState.ERROR],
    DispenserState.HOMING: [DispenserState.OFF, DispenserState.IDLE, DispenserState.ERROR],
    DispenserState.IDLE: [
        DispenserState.OFF,
        DispenserState.LOADING,
        DispenserState.DISPENSING,
        DispenserState.ERROR,
    ],
    DispenserState.LOADING: [DispenserState.IDLE, DispenserState.ERROR],
    DispenserState.DISPENSING: [DispenserState.IDLE, DispenserState.ERROR],
    DispenserState.ERROR: [DispenserState.OFF, DispenserState.ERROR],
}


class Dispenser:
    """Stateful class for controlling a Dynamixel chip dispenser."""

    def __init__(self, motor_controller: DynamixelController, motor_id: int) -> None:
        """Initialize a Dispenser instance."""
        self.motor_controller = motor_controller
        self.motor_id = motor_id
        self.chip_count = 0
        self.state = DispenserState.OFF
        self.current_position = 0

    def set_state(self, new_state: DispenserState) -> bool:
        """Attempt to change state; return True if allowed."""
        allowed = ALLOWED_TRANSITIONS.get(self.state, [])
        if new_state not in allowed:
            logging.warning("Invalid transition: %s → %s", self.state.name, new_state.name)
            return False
        self.state = new_state
        return True

    def _interlock_motion(self) -> bool:
        """Wait until motion completes or timeout expires."""
        start_time = time.time()
        while time.time() - start_time < control_table.DISPENSE_TIMEOUT:
            if self.motor_controller.read(self.motor_id, control_table.MOVING) == 0:
                return True
            time.sleep(0.01)
        return False

    def home(self) -> None:
        """Move the motor to the home position."""
        if not self.set_state(DispenserState.HOMING):
            return
        self.motor_controller.write(
            self.motor_id,
            control_table.GOAL_POSITION,
            control_table.MOTOR_HOMES[self.motor_id],
        )
        if not self._interlock_motion():
            self.set_state(DispenserState.ERROR)
            logging.error("Homing motion error at motor %d", self.motor_id)
            return
        self.current_position = control_table.MOTOR_HOMES[self.motor_id]
        self.set_state(DispenserState.IDLE)

    def dispense(self, quantity: int) -> None:
        """Dispense a given number of chips."""
        if not self.set_state(DispenserState.DISPENSING):
            return
        if self.chip_count < quantity:
            logging.warning(
                "Not enough chips to dispense %d. Only %d available.",
                quantity,
                self.chip_count,
            )
        else:
            for _ in range(quantity):
                self.current_position += control_table.DISPENSE_STEP
                self.motor_controller.write(
                    self.motor_id,
                    control_table.GOAL_POSITION,
                    self.current_position,
                )
                time.sleep(0.1) # wait for motion to begin
                if not self._interlock_motion():
                    self.set_state(DispenserState.ERROR)
                    logging.error("Dispense motion error at motor %d", self.motor_id)
                    break
                self.chip_count -= 1
        if self.state != DispenserState.ERROR:
            self.set_state(DispenserState.IDLE)

    def load(self, quantity: int) -> None:
        """Load chips into the dispenser."""
        if not self.set_state(DispenserState.LOADING):
            return
        self.current_position += control_table.DISPENSE_STEP
        self.motor_controller.write(
            self.motor_id, control_table.GOAL_POSITION, self.current_position
        )
        time.sleep(0.1)
        if not self._interlock_motion():
            self.set_state(DispenserState.ERROR)
            logging.warning("Loading motion error at motor %d", self.motor_id)
        else:
            self.chip_count += quantity
            self.set_state(DispenserState.IDLE)

    def initialize_motor(self, velocity: int = 300, acceleration: int = 30) -> None:
        """Reboot and configure the motor."""
        if not self.set_state(DispenserState.ON):
            return
        try:
            self.motor_controller.packet_handler.reboot(
                self.motor_controller.port_handler, self.motor_id
            )
            time.sleep(0.5)
            self.motor_controller.write(self.motor_id, control_table.OPERATING_MODE, 4)
            self.motor_controller.write(self.motor_id, control_table.PROFILE_VELOCITY, velocity)
            self.motor_controller.write(self.motor_id, control_table.PROFILE_ACCELERATION, acceleration)
            self.motor_controller.write(self.motor_id, control_table.TORQUE_ENABLE, 1)
        except Exception as e:
            logging.warning("Failed to initialize motor %d: %s", self.motor_id, e)
            self.set_state(DispenserState.ERROR)

    def get_state(self) -> DispenserState:
        """Return the current state."""
        return self.state

    def get_chip_count(self) -> int:
        """Return the chip count."""
        return self.chip_count


def main() -> None:
    """Run the dispenser control loop."""
    port = "COM8"
    baudrate = 57600
    motor_id = 21
    protocol_version = 2.0

    motor_controller = DynamixelController(port, baudrate, protocol_version)
    dispenser = Dispenser(motor_controller, motor_id)

    dispenser.initialize_motor()
    logging.info("Motor initialized.")
    dispenser.home()
    logging.info("Homing complete.")

    while True:
        qty = input("Enter quantity ('L' to load, 'Q' to quit): ").strip()
        if qty.lower() == "q":
            break
        if qty.lower() == "l":
            load_qty = input("Enter quantity to load: ").strip()
            try:
                load_int = int(load_qty)
                dispenser.load(load_int)
                logging.info(
                    "Loaded %d chips. Total: %d", load_int, dispenser.get_chip_count()
                )
            except ValueError:
                logging.warning("Invalid input '%s'.", load_qty)
            continue
        try:
            qty_int = int(qty)
            if qty_int <= dispenser.get_chip_count():
                dispenser.dispense(qty_int)
                logging.info("Dispensed %d chips.", qty_int)
            else:
                logging.warning(
                    "Only %d chips available. Please load more.",
                    dispenser.get_chip_count(),
                )
        except ValueError:
            logging.warning("Invalid input '%s'.", qty)


if __name__ == "__main__":
    main()
