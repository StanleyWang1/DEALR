import threading
import time

import control_table
import numpy as np
from dynamixel_driver import dynamixel_connect, dynamixel_disconnect, dynamixel_drive, radians_to_ticks, ticks_to_radians
from joystick_driver import joystick_connect, joystick_disconnect, joystick_read
from kinematics import num_forward_kinematics, num_jacobian

# Global Variables
running = True
autonomous_mode = False
running_lock = threading.Lock()

task_velocity = np.zeros((4,))
task_velocity_lock = threading.Lock()

motor_pos = np.zeros((4,))
motor_pos_lock = threading.Lock()

payload_mode = True  # true for holding, false for dump
payload_mode_lock = threading.Lock()

dispense_request = {"d1": False, "d2": False}
dispense_request_lock = threading.Lock()

# Initialize Motors
controller, group_sync_write = dynamixel_connect()
controller_lock = threading.Lock()
print("\033[93mDYNAMIXEL: Motors Connected, Driving to Home (4 sec)\033[0m")


def dispenser_control():
    global running, controller, dispense_request

    DISPENSER1 = 20
    DISPENSER2 = 21

    d1 = control_table.MOTOR20_HOME
    d2 = control_table.MOTOR21_HOME

    # Homing routine
    with controller_lock:
        controller.write(DISPENSER1, control_table.PROFILE_VELOCITY, 300)
        controller.write(DISPENSER2, control_table.PROFILE_VELOCITY, 300)
        controller.write(DISPENSER1, control_table.PROFILE_ACCELERATION, 30)
        controller.write(DISPENSER2, control_table.PROFILE_ACCELERATION, 30)
        time.sleep(0.1)
        controller.write(DISPENSER1, control_table.GOAL_POSITION, d1)
        controller.write(DISPENSER2, control_table.GOAL_POSITION, d2)
    time.sleep(1)

    while True:
        with running_lock:
            if not running:
                break

        with dispense_request_lock:
            if dispense_request["d1"]:
                d1 += control_table.DISPENSE_STEP
                with controller_lock:
                    controller.write(DISPENSER1, control_table.GOAL_POSITION, d1)
                time.sleep(control_table.DISPENSE_TIMEOUT)
                dispense_request["d1"] = False
            if dispense_request["d2"]:
                d2 += control_table.DISPENSE_STEP
                with controller_lock:
                    controller.write(DISPENSER2, control_table.GOAL_POSITION, d2)
                time.sleep(control_table.DISPENSE_TIMEOUT)
                dispense_request["d2"] = False

        time.sleep(0.1)  # 10 Hz loop

def motor_control():
    def joint_limit(motor_id, ticks):
        min_ticks, max_ticks = control_table.JOINT_LIMITS[motor_id]
        return min(max_ticks, max(min_ticks, ticks))

    def damped_pinv(J, damping=0.01):
        n = J.shape[1]
        return np.linalg.inv(J.T @ J + (damping**2) * np.eye(n)) @ J.T

    global running, controller, task_velocity, motor_pos, payload_mode

    # Motor IDs
    JOINT1, JOINT2, JOINT3, JOINT4 = 12, 13, 14, 15

    # Initial velocity limits
    for motor_id in [JOINT1, JOINT2, JOINT3, JOINT4]:
        with controller_lock:
            controller.write(motor_id, control_table.PROFILE_VELOCITY, 30)

    # Home configuration
    q = np.array([0.0, np.pi / 2, -np.pi / 2, 0])
    ticks = [
        control_table.MOTOR12_HOME + radians_to_ticks(q[0]),
        control_table.MOTOR13_HOME + radians_to_ticks(q[1]),
        control_table.MOTOR14_HOME - radians_to_ticks(q[2]),
        control_table.MOTOR15_HOME + radians_to_ticks(q[3]),
    ]

    with controller_lock:
        dynamixel_drive(controller, group_sync_write, ticks)
    time.sleep(4)

    # Remove velocity limits
    for motor_id in [JOINT1, JOINT2, JOINT3]:
        with controller_lock:
            controller.write(motor_id, control_table.PROFILE_VELOCITY, 0)
    with controller_lock:
        controller.write(JOINT4, control_table.PROFILE_VELOCITY, 100)

    try:
        prev_time = time.perf_counter()
        last_drive_time = prev_time
        i = 0

        while True:
            with running_lock:
                if not running:
                    break

            start = time.perf_counter()
            dt = start - prev_time
            prev_time = start

            if i % 100 == 0:
                print(f"Loop execution time: {dt * 1000:.2f} [ms]")
            i += 1

            # Copy task velocity
            with task_velocity_lock:
                v_task = task_velocity.copy()

            # Compute new joint state if velocity is commanded
            if not np.all(v_task == 0.0):
                J = num_jacobian(q)
                J_inv = damped_pinv(J)
                q_dot = J_inv @ v_task
                q += q_dot.flatten() * dt

                with motor_pos_lock:
                    motor_pos = q

            # Compute new ticks
            new_ticks = [
                joint_limit(JOINT1, control_table.MOTOR12_HOME + radians_to_ticks(q[0])),
                joint_limit(JOINT2, control_table.MOTOR13_HOME + radians_to_ticks(q[1])),
                joint_limit(JOINT3, control_table.MOTOR14_HOME - radians_to_ticks(q[2])),
                0,  # placeholder for JOINT4
            ]

            with payload_mode_lock:
                if payload_mode:
                    new_ticks[3] = joint_limit(
                        JOINT4, control_table.MOTOR15_HOME + radians_to_ticks(q[3])
                    )
                else:
                    new_ticks[3] = joint_limit(
                        JOINT4,
                        control_table.MOTOR15_HOME + radians_to_ticks(q[3]) - control_table.PAYLOAD_STEP,
                    )

            now = time.perf_counter()

            # Send new command if ticks changed OR every 50 ms as a refresh
            if not np.allclose(new_ticks, ticks, atol=1) or (now - last_drive_time > 0.05):
                ticks = new_ticks.copy()
                with controller_lock:
                    dynamixel_drive(controller, group_sync_write, ticks)
                last_drive_time = now

            # Maintain consistent loop timing
            elapsed = time.perf_counter() - start
            sleep_time = max(0.0, 0.005 - elapsed)
            time.sleep(sleep_time)

    finally:
        with controller_lock:
            dynamixel_disconnect(controller)

def motor_monitor():
    global running, controller

    # Motor IDs
    JOINT1, JOINT2, JOINT3, JOINT4 = 12, 13, 14, 15

    # Disable torque so motors can be freely backdriven
    with controller_lock:
        dynamixel_disconnect(controller)  # disables torque

    try:
        while True:
            with running_lock:
                if not running:
                    break

            # Read current joint positions in ticks
            with controller_lock:
                ticks = [
                    controller.read(JOINT1, control_table.PRESENT_POSITION),
                    controller.read(JOINT2, control_table.PRESENT_POSITION),
                    controller.read(JOINT3, control_table.PRESENT_POSITION),
                    controller.read(JOINT4, control_table.PRESENT_POSITION),
                ]

            # Convert to joint angles (radians)
            q = [
                ticks_to_radians(ticks[0] - control_table.MOTOR12_HOME),
                ticks_to_radians(ticks[1] - control_table.MOTOR13_HOME),
                -ticks_to_radians(
                    ticks[2] - control_table.MOTOR14_HOME
                ),  # motor flipped
                ticks_to_radians(ticks[3] - control_table.MOTOR15_HOME),
            ]

            # Compute forward kinematics
            FK = num_forward_kinematics(q)

            # Print end-effector position
            pos = FK[:3, 3]
            print(f"EE Position: x={pos[0]:.3f}, y={pos[1]:.3f}, z={pos[2]:.3f}")

            time.sleep(0.1)  # 10 Hz loop
    finally:
        pass

def autonomous_sequencer():
    global running, autonomous_mode, task_velocity, motor_pos, dispense_request, payload_mode

    waypoints = [
        ("move", np.array([0.24, 0.0, 0.09])),  # bowl
        ("move", np.array([0.022, 0.285, 0.13])),  # dispenser 1
        ("dispense1", None),
        ("move", np.array([0.17, 0.285, 0.13])),  # dispenser 2
        ("dispense2", None),
        ("move", np.array([0.25, 0.0, 0.12])),  # bowl
        ("drop", None),
    ]

    Kp = 3.0  # proportional gain for Cartesian velocity

    while running:
        for action, target in waypoints:
            start_time = time.time()
            if action == "move":
                # move for 2 sec toward target
                while autonomous_mode:
                    if time.time() - start_time > 5.0:  # max 5 sec move
                        break
                    with motor_pos_lock:
                        q = motor_pos.copy()

                    # Compute FK
                    FK = num_forward_kinematics(q)
                    p_curr = FK[:3, 3]

                    error = target - p_curr
                    if np.linalg.norm(error) < 0.005:
                        break

                    # Compute v_task as proportional error
                    v_lin = np.clip(Kp * error, -0.3, 0.3)

                    with task_velocity_lock:
                        task_velocity = np.array([v_lin[0], v_lin[1], v_lin[2], 0.0])

                    time.sleep(0.01)

            elif action == "dispense1" and autonomous_mode:
                with task_velocity_lock:
                    task_velocity = np.zeros((4,))
                time.sleep(0.1)
                with dispense_request_lock:
                    dispense_request["d1"] = True
                time.sleep(control_table.DISPENSE_TIMEOUT + 0.3)

            elif action == "dispense2" and autonomous_mode:
                with task_velocity_lock:
                    task_velocity = np.zeros((4,))
                time.sleep(0.1)
                with dispense_request_lock:
                    dispense_request["d2"] = True
                time.sleep(control_table.DISPENSE_TIMEOUT + 0.3)

            elif action == "drop" and autonomous_mode:
                with task_velocity_lock:
                    task_velocity = np.zeros((4,))
                time.sleep(0.1)
                # Toggle payload to False for 0.5 sec
                with payload_mode_lock:
                    payload_mode = False
                time.sleep(1.0)
                with payload_mode_lock:
                    payload_mode = True


def joystick_monitor():
    global running, autonomous_mode, task_velocity, payload_mode, dispense_request

    js = joystick_connect()

    prev_YB = 0
    prev_BB = 0
    prev_AB = 0

    try:
        while True:
            with running_lock:
                if not running:
                    break

            data = joystick_read(js)

            # Unpack and map
            LX = data["LX"]
            LY = data["LY"]
            LT = data["LT"]
            RT = data["RT"]
            LB = data["LB"]
            RB = data["RB"]
            AB = data["AB"]
            BB = data["BB"]
            XB = data["XB"]
            YB = data["YB"]

            if XB:
                with running_lock:
                    running = False
                    autonomous_mode = False
            elif LB and RB:
                x_velocity = -0.2 * LY
                y_velocity = -0.2 * LX
                z_velocity = 0.1 * RT - 0.1 * LT
                phi_velocity = 0.0
                with task_velocity_lock:
                    task_velocity = np.array(
                        [x_velocity, y_velocity, z_velocity, phi_velocity]
                    )

                # Dispense only on button press (rising edge)
                if YB and not prev_YB:
                    with running_lock:
                        autonomous_mode = not autonomous_mode
                if BB and not prev_BB:
                    with dispense_request_lock:
                        dispense_request["d1"] = True
                        dispense_request["d2"] = True

                # Toggle payload_mode on AB rising edge
                if AB and not prev_AB:
                    with payload_mode_lock:
                        payload_mode = not payload_mode  # toggle

                # Update previous states
                prev_YB = YB
                prev_BB = BB
                prev_AB = AB

            else:
                if not autonomous_mode:
                    with task_velocity_lock:
                        task_velocity = np.zeros((4,))

            time.sleep(0.01)
    finally:
        joystick_disconnect(js)


def main():
    dispenser_thread = threading.Thread(target=dispenser_control)
    motor_thread = threading.Thread(target=motor_control)
    joystick_thread = threading.Thread(target=joystick_monitor)
    autonomous_thread = threading.Thread(target=autonomous_sequencer)

    dispenser_thread.start()
    motor_thread.start()
    joystick_thread.start()
    autonomous_thread.start()

    dispenser_thread.join()
    motor_thread.join()
    joystick_thread.join()
    autonomous_thread.join()


if __name__ == "__main__":
    main()

# dispense 1 (0.06, 0.275, 0.12)
# dispense 2 (0.21, 0.27, 0.12)
# drop (0.2)
