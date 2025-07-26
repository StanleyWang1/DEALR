import time

import control_table
from dynamixel_controller import DynamixelController

ROBOT_HOME = 1030
DISPENSE_STEP = 1024
TIMEOUT = 1_000

PORT = "COM8"
BAUDRATE = 57600
MOTOR_ID = 21

PROTOCOL_VERSION = 2.0


def home(motor_controller: DynamixelController, motor_id: int) -> int:
    motor_controller.write(motor_id, control_table.GOAL_POSITION, ROBOT_HOME)
    time.sleep(1)
    return ROBOT_HOME


def dispense(motor_controller: DynamixelController, motor_id: int, current_position: int, qty: int) -> int:
    for _ in range(qty):
        current_position += DISPENSE_STEP
        motor_controller.write(motor_id, control_table.GOAL_POSITION, current_position)
        time.sleep(0.1)
        for _ in range(TIMEOUT):
            moving = motor_controller.read(MOTOR_ID, control_table.MOVING)
            if moving == 0:
                break
            time.sleep(0.1)
        return current_position  # INTERLOCK to wait until movement is done
        


def main() -> None:
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
            qty = int(qty)  # number of steps to dispense
        except ValueError:
            print(f"Invalid input {qty}, please enter an integer or 'q' to quit.")
            continue
        current_position = dispense(motor_controller, MOTOR_ID, current_position, qty)


if __name__ == "__main__":
    main()
