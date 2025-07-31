import numpy as np
import time
import threading

import control_table
from dynamixel_driver import dynamixel_connect, dynamixel_drive, dynamixel_disconnect, radians_to_ticks, ticks_to_radians
from joystick_driver import joystick_connect, joystick_read, joystick_disconnect
from kinematics import num_forward_kinematics, num_jacobian

# Global Variables
running = True
running_lock = threading.Lock()

task_velocity = np.zeros((4,))
task_velocity_lock = threading.Lock()

payload_mode = True # true for holding, false for dump
payload_mode_lock = threading.Lock()

def motor_control():
    def joint_limit(motor_id, ticks):
        min_ticks = control_table.JOINT_LIMITS[motor_id][0]
        max_ticks = control_table.JOINT_LIMITS[motor_id][1]
        return min(max_ticks, (max(min_ticks, ticks)))
    
    def damped_pinv(J, damping=0.01):
        n = J.shape[1]  # number of columns (joints)
        return np.linalg.inv(J.T @ J + (damping**2) * np.eye(n)) @ J.T

    global running, task_velocity, payload_mode

    # Motor IDs
    JOINT1 = 12
    JOINT2 = 13
    JOINT3 = 14
    JOINT4 = 15

    # Initialize
    controller, group_sync_write, group_sync_read = dynamixel_connect()
    print("\033[93mDYNAMIXEL: Motors Connected, Driving to Home (4 sec)\033[0m")
    
    # Set temporary velocity limit
    for motor_id in [JOINT1, JOINT2, JOINT3, JOINT4]:
        controller.write(motor_id, control_table.PROFILE_VELOCITY, 30)

    home = np.array([0.0, np.pi/2, -np.pi/2, 0])
    q = home
    ticks = [control_table.MOTOR12_HOME + radians_to_ticks(home[0]),
            control_table.MOTOR13_HOME + radians_to_ticks(home[1]), 
            control_table.MOTOR14_HOME - radians_to_ticks(home[2]), # motor flipped direction
            control_table.MOTOR15_HOME + radians_to_ticks(home[3])]
    
    dynamixel_drive(controller, group_sync_write, ticks)
    time.sleep(4)

    # Remove velocity limit
    for motor_id in [JOINT1, JOINT2, JOINT3]:
        controller.write(motor_id, control_table.PROFILE_VELOCITY, 0)
    controller.write(JOINT4, control_table.PROFILE_VELOCITY, 100)

    try:
        prev_time = time.perf_counter()
        
        while True:
            with running_lock:
                if not running:
                    break

            start = time.perf_counter()
            dt = start - prev_time
            print(f"Loop execution time: {dt*1000:.2f} [ms]")
            prev_time = start

            with task_velocity_lock:
                v_task = task_velocity.copy()

            J = num_jacobian(q)
            J_inv = damped_pinv(J)
            q_dot = J_inv @ v_task
            q += q_dot.flatten() * dt

            ticks1 = joint_limit(JOINT1, control_table.MOTOR12_HOME + radians_to_ticks(q[0]))
            ticks2 = joint_limit(JOINT2, control_table.MOTOR13_HOME + radians_to_ticks(q[1]))
            ticks3 = joint_limit(JOINT3, control_table.MOTOR14_HOME - radians_to_ticks(q[2]))
            with payload_mode_lock:
                if payload_mode:
                    ticks4 = joint_limit(JOINT4, control_table.MOTOR15_HOME + radians_to_ticks(q[3]))
                else:
                    ticks4 = joint_limit(JOINT4, control_table.MOTOR15_HOME + radians_to_ticks(q[3]) - 500)
            
            dynamixel_drive(controller, group_sync_write, [ticks1, ticks2, ticks3, ticks4])
        
            time.sleep(0.01) # time for motor to move
    finally:
        dynamixel_disconnect(controller)

def joystick_monitor():
    global running, task_velocity, payload_mode

    js = joystick_connect()
    
    try:
        while True:
            with running_lock:
                if not running:
                    break

            data = joystick_read(js)

            # Unpack and map
            LX = data["LX"]
            LY = data["LY"]
            RY = data["RY"]
            LT = data["LT"]
            RT = data["RT"]
            LB = data["LB"]
            RB = data["RB"]
            AB = data["AB"]
            BB = data["BB"]
            XB = data["XB"]

            if XB:
                with running_lock:
                    running = False
            elif LB and RB:
                x_velocity = -0.1 * LY
                y_velocity = -0.1 * LX
                z_velocity = 0.1 * RT - 0.1 * LT
                phi_velocity = 0.0
                with task_velocity_lock:
                    task_velocity = np.array([x_velocity, y_velocity, z_velocity, phi_velocity])

                if AB and not BB:
                    with payload_mode_lock:
                        payload_mode = True
                elif BB and not AB:
                    with payload_mode_lock:
                        payload_mode = False
            else:
                with task_velocity_lock:
                    task_velocity = np.zeros((4,))

            time.sleep(0.01)
    finally:
        joystick_disconnect(js)

def main():
    motor_thread = threading.Thread(target=motor_control)
    joystick_thread = threading.Thread(target=joystick_monitor)

    motor_thread.start()
    joystick_thread.start()

    motor_thread.join()
    joystick_thread.join()

if __name__ == "__main__":
    main()
