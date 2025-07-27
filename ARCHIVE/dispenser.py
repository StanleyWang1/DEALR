from enum import Enum, auto
import time

import control_table

RED = "\033[91m"
RESET = "\033[0m"

# ------------------------------
# State Definitions
# ------------------------------
class DispenserState(Enum):
    OFF = auto()
    ON = auto()
    IDLE = auto()
    LOADING = auto()
    DISPENSING = auto()
    ERROR = auto()

ALLOWED_TRANSITIONS = {
    DispenserState.OFF:        [DispenserState.ON, DispenserState.ERROR],
    DispenserState.ON:         [DispenserState.OFF, DispenserState.LOADING, DispenserState.ERROR],
    DispenserState.IDLE:       [DispenserState.OFF, DispenserState.LOADING, DispenserState.DISPENSING, DispenserState.ERROR],
    DispenserState.LOADING:    [DispenserState.IDLE, DispenserState.ERROR],
    DispenserState.DISPENSING: [DispenserState.IDLE, DispenserState.ERROR],
    DispenserState.ERROR:      [DispenserState.OFF, DispenserState.ERROR],
}

# ------------------------------
# Dispenser Class
# ------------------------------
class Dispenser:
    def __init__(self, motor_controller, motor_id):
        # State variables
        self.state = DispenserState.OFF
        self.chip_count = 0
        self.dispense_request = 0
        self.error_status = None
        # Hardware interface
        self.motor_controller = motor_controller
        self.motor_id = motor_id
        # Motor Position
        self.motor_pos = control_table.MOTOR21_HOME
        self.dispense_step = 1024

    # ------------------------------
    # State Transition Helper
    # ------------------------------

    def logger(self, message: str):
        print(message)

    def check_hardware_error(self) -> bool:
        """Check if the motor has any hardware error. Returns True if error exists."""
        error_status = self.motor_controller.read(self.motor_id, control_table.HARDWARE_ERROR_STATUS)

        if error_status is False:  # your read function failed
            self.logger(f"{RED}[ERROR] Failed to read hardware error status.{RESET}")
            return True

        if error_status == 0:  # no error
            return False
        
        # Decode specific bits
        if error_status & (1 << 5):
            self.logger(f"{RED}[ERROR] Overload Error – persistent load exceeds maximum output{RESET}")
        if error_status & (1 << 4):
            self.logger(f"{RED}[ERROR] Electrical Shock / Insufficient Power{RESET}")
        if error_status & (1 << 3):
            self.logger(f"{RED}[ERROR] Motor Encoder Malfunction{RESET}")
        if error_status & (1 << 2):
            self.logger(f"{RED}[ERROR] Overheating – internal temp exceeds limit{RESET}")
        if error_status & (1 << 0):
            self.logger(f"{RED}[ERROR] Input Voltage Error – out of safe range{RESET}")

        return True

    
    def set_state(self, new_state: DispenserState) -> bool:
        """Attempt to change state. Returns True if successful, False otherwise."""

        allowed = ALLOWED_TRANSITIONS.get(self.state, [])
        if new_state not in allowed: # check if transition is valid
            self.logger(f"{RED}[WARNING] Invalid transition: {self.state.name} → {new_state.name}{RESET}")
            return False
        # Valid transition
        self.state = new_state
        return True

    # ------------------------------
    # Action Transitions
    # ------------------------------
    def power_on(self):
        if self.check_hardware_error():
            self.set_state(DispenserState.ERROR)
            return False
        elif not self.set_state(DispenserState.ON):
            return False
        try:
            self.motor_controller.reboot(self.motor_controller.port_handler, self.motor_id)
            time.sleep(0.5)  # wait for reboot
            self.motor_controller.write(self.motor_id, control_table.OPERATING_MODE, 4)  # extended position mode
            self.motor_controller.write(self.motor_id, control_table.PROFILE_VELOCITY, 300)  # set velocity
            self.motor_controller.write(self.motor_id, control_table.PROFILE_ACCELERATION, 30)  # set acceleration
            self.motor_controller.write(self.motor_id, control_table.TORQUE_ENABLE, 1)  # enable torque
            return True
        except Exception as e:
            self.logger(f"{RED}[ERROR] Failed to power on: {e}{RESET}")
            self.set_state(DispenserState.ERROR)
            return False

    def home(self):
        if self.check_hardware_error():
            self.set_state(DispenserState.ERROR)
            return False
        elif not self.set_state(DispenserState.LOADING):
            return False
        try:
            self.motor_controller.write(self.motor_id, control_table.GOAL_POSITION, control_table.MOTOR21_HOME)
            return True
        except Exception as e:
            self.logger(f"{RED}[ERROR] Failed to home: {e}{RESET}")
            self.set_state(DispenserState.ERROR)
            return False

    def loading(self, count: int):
        if self.check_hardware_error():
            self.set_state(DispenserState.ERROR)
            return False
        elif not self.set_state(DispenserState.IDLE):
            return False
        try:
            self.motor_controller.write(self.motor_id, control_table.GOAL_POSITION, self.motor_pos + self.dispense_step)
            self.motor_pos += self.dispense_step
            self.chip_count += count
            return True
        except Exception as e:
            self.logger(f"{RED}[ERROR] Failed to home: {e}{RESET}")
            self.set_state(DispenserState.ERROR)
            return False


    def dispense(self, count: int):
        if self.check_hardware_error():
            self.set_state(DispenserState.ERROR)
            return False
        elif not self.set_state(DispenserState.DISPENSING):
            return False
        try:
            self.motor_controller.write(self.motor_id, control_table.GOAL_POSITION, self.motor_pos + self.dispense_step)
            self.motor_pos += self.dispense_step
            self.chip_count += count
            return True
        except Exception as e:
            self.logger(f"{RED}[ERROR] Failed to home: {e}{RESET}")
            self.set_state(DispenserState.ERROR)
            return False

    def reset_error(self):
        if self.state == DispenserState.ERROR:
            self.error_status = None
            self.set_state(DispenserState.IDLE)

    # ------------------------------
    # Utility
    # ------------------------------
    def status(self):
        return {
            "state": self.state.name,
            "chip_count": self.chip_count,
            "dispense_request": self.dispense_request,
            "error_status": self.error_status,
        }
