from .dispenser_core import Dispenser
from .dispenser_gui import start_gui
from .dynamixel_controller import DynamixelController


def main():
    # Dynamixel connection parameters
    port = "COM8"
    baudrate = 57600
    protocol_version = 2.0

    # Create one shared Dynamixel controller
    motor_controller = DynamixelController(port, baudrate, protocol_version)

    # Initialize two dispenser objects for motor IDs 20 and 21
    disp1 = Dispenser(motor_controller, motor_id=20)
    disp2 = Dispenser(motor_controller, motor_id=21)

    # Start GUI with both dispensers
    start_gui(disp1, disp2)


if __name__ == "__main__":
    main()
