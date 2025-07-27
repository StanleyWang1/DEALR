import time

from .errors import DispenserError

from . import control_table
from .dynamixel_controller import DynamixelController

ROBOT_HOME = 1030
DISPENSE_STEP = 1024
TIMEOUT_SECONDS = 1

PORT = "COM8"
BAUDRATE = 57600
MOTOR_ID = 21

PROTOCOL_VERSION = 2.0


def home(motor_controller: DynamixelController, motor_id: int) -> int:
    """Resets the motor controller to home position.

    Args:
        motor_controller: Master motor network.
        motor_id: Specific motor ID.

    Returns:
        int: Home position code.
    
    Raises:
        DispenserError: If the motor stalls.
    """

    motor_controller.write(motor_id, control_table.GOAL_POSITION, ROBOT_HOME)
    if not poll_motor_for_moving(motor_controller, motor_id):
        raise DispenserError(f"Homing error at motor {motor_id}")
    return ROBOT_HOME


def poll_motor_for_moving(motor_controller: DynamixelController, motor_id: int) -> bool:
    """Polls the motor to see if it is moving within the timeout window.

    Args:
        motor_controller: Master motor network.
        motor_id: Motor ID.

    Returns:
        bool: If the motor has successfully completed movement.
    """
    success = False
    reference = time.time()
    while time.time() - reference < TIMEOUT_SECONDS:
        moving = motor_controller.read(motor_id, control_table.MOVING)
        if moving == 0:
            success = True
            break
        time.sleep(0.01)
    return success


def dispense(
    motor_controller: DynamixelController,
    motor_id: int,
    current_position: int,
    quantity: int,
) -> int:
    """Continuously moves the motor to dispense N chips.

    Args:
        motor_controller: Master motor network.
        motor_id: Motor ID.
        current_position: Current encoded position of motor.
        quantity: Number of movements to make.

    Raises:
        DispenserError: If the motor stalls.

    Returns:
        int: New current position.
    """

    for _ in range(quantity):
        current_position += DISPENSE_STEP
        motor_controller.write(motor_id, control_table.GOAL_POSITION, current_position)
        time.sleep(0.1)
        if not poll_motor_for_moving(motor_controller, motor_id):
            raise DispenserError(f"Dispense error at motor {motor_id}")
    return current_position


def main() -> None:
    """Dispenser motor driver."""

    motor_controller = DynamixelController(PORT, BAUDRATE, PROTOCOL_VERSION)
    motor_controller.packet_handler.reboot(
        motor_controller.port_handler, MOTOR_ID
    )  # reboot motor
    print("Rebooted motor")
    time.sleep(0.5)  # wait for reboot
    motor_controller.write(
        MOTOR_ID, control_table.OPERATING_MODE, 4
    )  # extended position mode
    motor_controller.write(
        MOTOR_ID, control_table.PROFILE_VELOCITY, 300
    )  # set velocity
    motor_controller.write(
        MOTOR_ID, control_table.PROFILE_ACCELERATION, 30
    )  # set acceleration
    print("Motor initialized")
    motor_controller.write(MOTOR_ID, control_table.TORQUE_ENABLE, 1)  # enable torque
    print("Torque enabled")
    current_position = home(motor_controller, MOTOR_ID)
    print("Homed to position", current_position)

    while True:
        qty = input("Enter quantity to dispense (or 'q' to quit): ")
        if qty.lower() == "q":
            break
        try:
            qty_int = int(qty)  # number of steps to dispense
            current_position = dispense(motor_controller, MOTOR_ID, current_position, qty_int)
        except ValueError:
            print(f"Invalid input {qty}, please enter an integer or 'q' to quit.")
            continue
        except DispenserError as e:
            raise e


if __name__ == "__main__":
    main()
