from dynamixel_sdk import *
import numpy as np
import time

from control_table import *
from dynamixel_controller import DynamixelController

from kinematics import num_forward_kinematics, num_jacobian
# Motor IDs
JOINT1 = 12
JOINT2 = 13
JOINT3 = 14
JOINT4 = 15

def dynamixel_connect():
    # Initialize controller
    controller = DynamixelController('COM8', 1000000, 2.0)
    group_sync_write = GroupSyncWrite(controller.port_handler, controller.packet_handler, GOAL_POSITION[0], GOAL_POSITION[1])

    # --------------------------------------------------
    # Reboot WRIST motors to ensure clean startup
    for motor_id in [JOINT1, JOINT2, JOINT3, JOINT4]:
        dxl_comm_result, dxl_error = controller.packet_handler.reboot(controller.port_handler, motor_id)
        if dxl_comm_result != COMM_SUCCESS:
            print(f"Failed to reboot Motor {motor_id}: {controller.packet_handler.getTxRxResult(dxl_comm_result)}")
        elif dxl_error != 0:
            print(f"Error rebooting Motor {motor_id}: {controller.packet_handler.getRxPacketError(dxl_error)}")
        else:
            print(f"Motor {motor_id} rebooted successfully.")

    # Give motors time to reboot
    time.sleep(2)

    # Set Control Mode
    controller.write(JOINT1, OPERATING_MODE, 4)  # extended position control
    controller.write(JOINT2, OPERATING_MODE, 4)
    controller.write(JOINT3, OPERATING_MODE, 4)
    controller.write(JOINT4, OPERATING_MODE, 4)
    time.sleep(0.1)
    # Optional: Force Limit on Gripper
    # controller.WRITE(GRIPPER, PWM_LIMIT, 250)

    # Torque Enable
    controller.write(JOINT1, TORQUE_ENABLE, 1)
    controller.write(JOINT2, TORQUE_ENABLE, 1)
    controller.write(JOINT3, TORQUE_ENABLE, 1)
    controller.write(JOINT4, TORQUE_ENABLE, 1)  # Gripper torque off for now
    time.sleep(0.1)

    return controller, group_sync_write

def dynamixel_drive(controller, group_sync_write, ticks):
    param_success = group_sync_write.addParam(JOINT1, ticks[0].to_bytes(4, 'little', signed=True))
    param_success &= group_sync_write.addParam(JOINT2, ticks[1].to_bytes(4, 'little', signed=True))
    param_success &= group_sync_write.addParam(JOINT3, ticks[2].to_bytes(4, 'little', signed=True))
    param_success &= group_sync_write.addParam(JOINT4, ticks[3].to_bytes(4, 'little', signed=True))

    if not param_success:
        print("Failed to add parameters for SyncWrite")
        return False

    dxl_comm_result = group_sync_write.txPacket()
    if dxl_comm_result != COMM_SUCCESS:
        print(f"SyncWrite communication error: {controller.packet_handler.getTxRxResult(dxl_comm_result)}")
        return False

    group_sync_write.clearParam()
    return True

def dynamixel_disconnect(controller):
    # Torque OFF all motors individually (simple)
    controller.write(JOINT1, TORQUE_ENABLE, 0)
    controller.write(JOINT2, TORQUE_ENABLE, 0)
    controller.write(JOINT3, TORQUE_ENABLE, 0)
    controller.write(JOINT4, TORQUE_ENABLE, 0)
    # controller.port_handler.closePort()

def radians_to_ticks(rad):
    return int(rad / (2 * np.pi) * 4096)

def ticks_to_radians(ticks):
    return ticks / 4096 * 2 * np.pi

def main():
    controller, group_sync_write = dynamixel_connect()
    print("\033[93mDYNAMIXEL: Motors Connected, Driving to Home (5 sec)\033[0m")
    
    # Set temporary velocity limit
    for motor_id in [JOINT1, JOINT2, JOINT3, JOINT4]:
        controller.write(motor_id, PROFILE_VELOCITY, 30)
    home = [0.0, np.pi/2, -np.pi/2, 0]
    dynamixel_drive(controller, group_sync_write, 
                    [MOTOR12_HOME + radians_to_ticks(home[0]),
                     MOTOR13_HOME + radians_to_ticks(home[1]), 
                     MOTOR14_HOME - radians_to_ticks(home[2]), # motor flipped direction
                     MOTOR15_HOME + radians_to_ticks(home[3])])
    time.sleep(5)
    # Remove velocity limit
    for motor_id in [JOINT1, JOINT2, JOINT3, JOINT4]:
        controller.write(motor_id, PROFILE_VELOCITY, 0)
    # Task Space Control Loop
    # [ADD]

    input("Enter to disconnect")
    dynamixel_disconnect(controller)

    while True:
        joint_pos = [ticks_to_radians(controller.read(JOINT1, PRESENT_POSITION) - MOTOR12_HOME),
                    ticks_to_radians(controller.read(JOINT2, PRESENT_POSITION) - MOTOR13_HOME),
                    -ticks_to_radians(controller.read(JOINT3, PRESENT_POSITION) - MOTOR14_HOME),
                    ticks_to_radians(controller.read(JOINT4, PRESENT_POSITION) - MOTOR15_HOME)]
        FK_num = num_forward_kinematics(joint_pos)
        print(np.round(FK_num[:3,3], 2))
        time.sleep(0.1)
        
    print("\033[93mDYNAMIXEL: Motors Disconnected, Torque Off\033[0m")

if __name__ == "__main__":
    main()

