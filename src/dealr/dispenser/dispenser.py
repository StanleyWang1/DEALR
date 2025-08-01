import threading

from .dispenser_core import Dispenser
from .dispenser_gui import start_gui
from ..motor.dynamixel_controller import DynamixelController


def main():
    # Dynamixel connection parameters
    port = "COM8"
    baudrate = 57600
    protocol_version = 2.0

    # Create one shared Dynamixel controller
    motor_controller = DynamixelController(port, baudrate, protocol_version)
    motor_lock = threading.Lock()

    # Initialize three dispenser objects for motor IDs 20, 21, 22
    disp1 = Dispenser(motor_controller, motor_id=20, lock=motor_lock)
    disp2 = Dispenser(motor_controller, motor_id=21, lock=motor_lock)
    disp3 = Dispenser(motor_controller, motor_id=22, lock=motor_lock)

    # Start GUI with both dispensers
    start_gui(disp1, disp2, disp3)


if __name__ == "__main__":
    main()
