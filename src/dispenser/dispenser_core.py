"""Dispenser core logic."""

import logging
import threading
import time
from enum import Enum, auto

from . import control_table
from .dynamixel_controller import DynamixelController


class DispenserState(Enum):
    """Possible dispenser states for the chip dispenser."""

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
    """Stateful class for controlling a Dynamixel-based chip dispenser (thread-safe)."""

    def __init__(
        self,
        motor_controller: DynamixelController,
        motor_id: int,
        lock: threading.Lock | None = None,
    ) -> None:
        self.motor_controller = motor_controller
        self.motor_id = motor_id
        self.lock = lock  # shared lock for thread-safe access
        self._chip_count = 0
        self._state = DispenserState.OFF
        self.current_position = 0

    @property
    def state(self) -> DispenserState:
        """Return the current state."""
        return self._state

    @state.setter
    def state(self, new_state: DispenserState) -> None:
        self._state = new_state

    def set_state(self, new_state: DispenserState) -> bool:
        """Attempt a state transition, return True if valid."""
        allowed = ALLOWED_TRANSITIONS.get(self.state, [])
        if new_state not in allowed:
            logging.warning(
                "Invalid transition: %s → %s", self.state.name, new_state.name
            )
            return False
        self.state = new_state
        return True

    @property
    def chip_count(self) -> int:
        """Return the chip count."""
        return self._chip_count

    @chip_count.setter
    def chip_count(self, new_chip_count: int) -> None:
        """Return the chip count."""
        self._chip_count = new_chip_count

    # ----------------- Utility -----------------
    def _with_lock(self, func, *args, **kwargs):
        """Execute a motor controller function with an optional lock."""
        if self.lock:
            with self.lock:
                return func(*args, **kwargs)
        return func(*args, **kwargs)

    def _safe_write(self, address, value):
        """Thread-safe motor write."""
        self._with_lock(self.motor_controller.write, self.motor_id, address, value)

    def _safe_read(self, address):
        """Thread-safe motor read."""
        return self._with_lock(self.motor_controller.read, self.motor_id, address)

    def _safe_reboot(self):
        """Thread-safe motor reboot."""
        self._with_lock(
            self.motor_controller.packet_handler.reboot,
            self.motor_controller.port_handler,
            self.motor_id,
        )

    def _interlock_motion(self) -> bool:
        """Wait for motion to finish or timeout."""
        start_time = time.time()
        while time.time() - start_time < control_table.DISPENSE_TIMEOUT:
            # Optional: Check moving flag with self._safe_read(control_table.MOVING)
            time.sleep(0.01)
        return True

    def home(self) -> None:
        """Move motor to its home position."""
        if not self.set_state(DispenserState.HOMING):
            return

        target = control_table.MOTOR_HOMES[self.motor_id]
        self._safe_write(control_table.GOAL_POSITION, target)

        if not self._interlock_motion():
            self._handle_motion_error("Homing motion error")
            return

        self.current_position = target
        self.set_state(DispenserState.IDLE)

    def dispense(self, quantity: int) -> None:
        """Dispense a specified number of chips."""
        if not self.set_state(DispenserState.DISPENSING):
            return

        if self.chip_count < quantity:
            logging.warning(
                "Trying to dispense %d out of %d available", quantity, self.chip_count
            )
        else:
            for _ in range(quantity):
                self.current_position += control_table.DISPENSE_STEP
                self._safe_write(control_table.GOAL_POSITION, self.current_position)
                time.sleep(0.1)
                if not self._interlock_motion():
                    self._handle_motion_error("Dispense motion error")
                    break
                self.chip_count -= 1

        if self.state != DispenserState.ERROR:
            self.set_state(DispenserState.IDLE)

    def load(self, quantity: int) -> None:
        """Load chips into the dispenser."""

        if not self.set_state(DispenserState.LOADING):
            return

        if self.chip_count == 0:  # re-index carriage if empty
            self.current_position += control_table.DISPENSE_STEP
            self._safe_write(control_table.GOAL_POSITION, self.current_position)
            time.sleep(0.1)
            if not self._interlock_motion():
                self._handle_motion_error("Loading motion error")
                return

        self.chip_count += quantity
        self.set_state(DispenserState.IDLE)

    def initialize_motor(self, velocity: int = 300, acceleration: int = 30) -> None:
        """Reboot and configure the motor."""

        if not self.set_state(DispenserState.ON):
            return

        try:
            self._safe_reboot()
            time.sleep(0.5)
            self._safe_write(control_table.OPERATING_MODE, 4)
            self._safe_write(control_table.PROFILE_VELOCITY, velocity)
            self._safe_write(control_table.PROFILE_ACCELERATION, acceleration)
            self._safe_write(control_table.TORQUE_ENABLE, 1)
        except Exception as e:  # TODO: find more specific exception
            logging.warning("Failed to initialize motor %d: %s", self.motor_id, e)
            self.set_state(DispenserState.ERROR)

    # ----------------- Helper Methods -----------------
    def _handle_motion_error(self, message: str):
        """Set error state and log a message."""
        self.set_state(DispenserState.ERROR)
        logging.error("%s at motor %d", message, self.motor_id)
