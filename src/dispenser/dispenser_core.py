import logging
import time
from enum import Enum, auto

from . import control_table
from .dynamixel_controller import DynamixelController


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
    DispenserState.ON: [
        DispenserState.OFF,
        DispenserState.HOMING,
        DispenserState.ERROR,
    ],
    DispenserState.HOMING: [
        DispenserState.OFF,
        DispenserState.IDLE,
        DispenserState.ERROR,
    ],
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
        self._chip_count = 0
        self._state = DispenserState.OFF
        self.current_position = 0

    @property
    def state(self) -> DispenserState:
        """Return the current state."""
        return self._state

    @state.setter
    def set_state(self, new_state: DispenserState) -> bool:
        """Attempt to change state; return True if allowed."""

        allowed = ALLOWED_TRANSITIONS.get(self.state, [])
        if new_state not in allowed:
            logging.warning(f"Invalid transition: {self.state.name} → {new_state.name}")
            return False
        self._state = new_state
        return True

    @property
    def chip_count(self) -> int:
        """Return the chip count."""
        return self._chip_count

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
            logging.error(f"Homing motion error at motor {self.motor_id}")
            return
        self.current_position = control_table.MOTOR_HOMES[self.motor_id]
        self.set_state(DispenserState.IDLE)

    def dispense(self, quantity: int) -> None:
        """Dispense a given number of chips."""

        if not self.set_state(DispenserState.DISPENSING):
            return
        if self.chip_count < quantity:
            logging.warning(
                f"Not enough chips to dispense {quantity}. Only {self.chip_count} available."
            )
        else:
            for _ in range(quantity):
                self.current_position += control_table.DISPENSE_STEP
                self.motor_controller.write(
                    self.motor_id,
                    control_table.GOAL_POSITION,
                    self.current_position,
                )
                time.sleep(0.1)  # wait for motion to begin
                if not self._interlock_motion():
                    self.set_state(DispenserState.ERROR)
                    logging.error(f"Dispense motion error at motor {self.motor_id}")
                    break
                self.chip_count -= 1
        if self.state != DispenserState.ERROR:
            self.set_state(DispenserState.IDLE)

    def load(self, quantity: int) -> None:
        """Load chips into the dispenser."""

        if not self.set_state(DispenserState.LOADING):
            return
        if (
            self.chip_count == 0
        ):  # loading from empty, re-index chip carriage by one step
            self.current_position += control_table.DISPENSE_STEP
            self.motor_controller.write(
                self.motor_id, control_table.GOAL_POSITION, self.current_position
            )
            time.sleep(0.1)
            if not self._interlock_motion():
                self.set_state(DispenserState.ERROR)
                logging.warning(f"Loading motion error at motor {self.motor_id}")
                return
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
            self.motor_controller.write(
                self.motor_id, control_table.PROFILE_VELOCITY, velocity
            )
            self.motor_controller.write(
                self.motor_id, control_table.PROFILE_ACCELERATION, acceleration
            )
            self.motor_controller.write(self.motor_id, control_table.TORQUE_ENABLE, 1)
        except Exception as e:
            logging.warning(f"Failed to initialize motor {self.motor_id}: {e}")
            self.set_state(DispenserState.ERROR)
