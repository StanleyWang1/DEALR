from dynamixel_controller import DynamixelController
import control_table
import time

ROBOT_HOME = 1030
DISPENSE_STEP = 1024

PORT = "COM8"
BAUDRATE = 57600
MOTOR_ID = 21

def home(motor_controller):
    motor_controller.write(MOTOR_ID, control_table.GOAL_POSITION, ROBOT_HOME)
    time.sleep(1)
    return ROBOT_HOME

def dispense(motor_controller, current_position, qty):
    for _ in range(qty):
        current_position += DISPENSE_STEP
        motor_controller.write(MOTOR_ID, control_table.GOAL_POSITION, current_position)
        time.sleep(0.1)
        while True: 
            moving = motor_controller.read(MOTOR_ID, control_table.MOVING)
            if moving == 0:
                break # INTERLOCK to wait until movement is done
            time.sleep(0.1)
    return current_position

motor_controller = DynamixelController(PORT, BAUDRATE, 2.0)
motor_controller.packet_handler.reboot(motor_controller.port_handler, MOTOR_ID) # reboot motor
print("Rebooted motor")
time.sleep(0.5) # wait for reboot
motor_controller.write(MOTOR_ID, control_table.OPERATING_MODE, 4) # extended position mode
motor_controller.write(MOTOR_ID, control_table.PROFILE_VELOCITY, 300) # set velocity
motor_controller.write(MOTOR_ID, control_table.PROFILE_ACCELERATION, 30) # set acceleration
print("Motor initialized")
motor_controller.write(MOTOR_ID, control_table.TORQUE_ENABLE, 1) # enable torque
print("Torque enabled")
current_position = home(motor_controller)
print("Homed to position", current_position)

while True:
    qty = input("Enter quantity to dispense (or 'q' to quit): ")
    if qty.lower() == 'q':
        break
    try:
        qty = int(qty)  # number of steps to dispense           
    except ValueError:
        print("Invalid input, please enter an integer or 'q' to quit.")
        continue
    current_position = dispense(motor_controller, current_position, qty)


