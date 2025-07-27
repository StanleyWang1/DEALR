from dispenser_core import Dispenser
from dispenser_gui import start_gui
from dynamixel_controller import DynamixelController

def main():
    port = "COM8"
    baudrate = 57600
    motor_id = 21
    protocol_version = 2.0

    motor_controller = DynamixelController(port, baudrate, protocol_version)
    dispenser = Dispenser(motor_controller, motor_id)

    start_gui(dispenser)

if __name__ == "__main__":
    main()
