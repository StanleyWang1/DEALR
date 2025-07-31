import threading
import time

import control_table
import numpy as np
from dynamixel_driver import (
    dynamixel_connect,
    dynamixel_disconnect,
    dynamixel_drive,
    radians_to_ticks,
    ticks_to_radians,
)
from joystick_driver import joystick_connect, joystick_disconnect, joystick_read
from kinematics import num_forward_kinematics, num_jacobian


class RobotState:
    def __init__(self):
        self.running = True
        self.motor_pos = np.zeros(4)
        self.payload_mode = True
        self.lock = threading.Lock()


def damped_pinv(J, damping=0.01):
    n = J.shape[1]
    return np.linalg.inv(J.T @ J + (damping**2) * np.eye(n)) @ J.T


def joint_limit(motor_id, ticks):
    min_ticks, max_ticks = control_table.JOINT_LIMITS[motor_id]
    return min(max_ticks, max(min_ticks, ticks))


def joystick_estop(state: RobotState):
    js = joystick_connect()
    try:
        while state.running:
            data = joystick_read(js)
            if data["XB"]:  # XB button as e-stop
                with state.lock:
                    state.running = False
            time.sleep(0.05)
    finally:
        joystick_disconnect(js)


def robot_main_loop(state: RobotState):
    controller, group_sync_write = dynamixel_connect()
    print("\033[93mDYNAMIXEL: Motors Connected, Homing...\033[0m")

    JOINTS = [12, 13, 14, 15]
    DISPENSERS = [20, 21]

    # Track dispenser positions
    d1 = control_table.MOTOR20_HOME
    d2 = control_table.MOTOR21_HOME

    # Home joints
    home_q = np.array([0.0, np.pi / 2, -np.pi / 2, 0])
    ticks = [
        control_table.MOTOR12_HOME + radians_to_ticks(home_q[0]),
        control_table.MOTOR13_HOME + radians_to_ticks(home_q[1]),
        control_table.MOTOR14_HOME - radians_to_ticks(home_q[2]),
        control_table.MOTOR15_HOME + radians_to_ticks(home_q[3]),
    ]
    for jid in JOINTS:
        controller.write(jid, control_table.PROFILE_VELOCITY, 60)
    dynamixel_drive(controller, group_sync_write, ticks)
    time.sleep(4)

    # Setup dispensers
    for did in DISPENSERS:
        controller.write(did, control_table.PROFILE_VELOCITY, 300)
        controller.write(did, control_table.PROFILE_ACCELERATION, 30)
    controller.write(DISPENSERS[0], control_table.GOAL_POSITION, d1)
    controller.write(DISPENSERS[1], control_table.GOAL_POSITION, d2)

    # Autonomous waypoints
    waypoints = [
        ("move", np.array([0.25, 0.0, 0.12])),
        ("move", np.array([0.06, 0.275, 0.12])),
        ("dispense1", None),
        ("move", np.array([0.21, 0.27, 0.12])),
        ("dispense2", None),
        ("move", np.array([0.25, 0.0, 0.12])),
        ("drop", None),
    ]

    Kp = 2.0
    q = home_q.copy()

    try:
        while state.running:
            for action, target in waypoints:
                if not state.running:
                    break

                start_time = time.time()

                if action == "move":
                    while time.time() - start_time < 2.5 and state.running:
                        # FK and proportional error
                        FK = num_forward_kinematics(q)
                        p_curr = FK[:3, 3]
                        v_lin = Kp * (target - p_curr)

                        # IK mapping
                        J = num_jacobian(q)
                        J_inv = damped_pinv(J)
                        q_dot = J_inv @ np.array([v_lin[0], v_lin[1], v_lin[2], 0.0])
                        q += q_dot.flatten() * 0.01  # Euler step

                        # Save state
                        with state.lock:
                            state.motor_pos = q.copy()

                        # Compute motor ticks
                        ticks_cmd = [
                            joint_limit(
                                JOINTS[0],
                                control_table.MOTOR12_HOME + radians_to_ticks(q[0]),
                            ),
                            joint_limit(
                                JOINTS[1],
                                control_table.MOTOR13_HOME + radians_to_ticks(q[1]),
                            ),
                            joint_limit(
                                JOINTS[2],
                                control_table.MOTOR14_HOME - radians_to_ticks(q[2]),
                            ),
                            joint_limit(
                                JOINTS[3],
                                control_table.MOTOR15_HOME
                                + radians_to_ticks(q[3])
                                - (500 if not state.payload_mode else 0),
                            ),
                        ]

                        dynamixel_drive(controller, group_sync_write, ticks_cmd)
                        time.sleep(0.01)

                elif action == "dispense1":
                    d1 += control_table.DISPENSE_STEP
                    controller.write(DISPENSERS[0], control_table.GOAL_POSITION, d1)
                    time.sleep(1.0)

                elif action == "dispense2":
                    d2 += control_table.DISPENSE_STEP
                    controller.write(DISPENSERS[1], control_table.GOAL_POSITION, d2)
                    time.sleep(1.0)

                elif action == "drop":
                    state.payload_mode = False
                    # Send updated gripper position immediately
                    ticks_cmd = [
                        joint_limit(
                            JOINTS[0],
                            control_table.MOTOR12_HOME + radians_to_ticks(q[0]),
                        ),
                        joint_limit(
                            JOINTS[1],
                            control_table.MOTOR13_HOME + radians_to_ticks(q[1]),
                        ),
                        joint_limit(
                            JOINTS[2],
                            control_table.MOTOR14_HOME - radians_to_ticks(q[2]),
                        ),
                        joint_limit(
                            JOINTS[3],
                            control_table.MOTOR15_HOME + radians_to_ticks(q[3]) - 500,
                        ),
                    ]
                    dynamixel_drive(controller, group_sync_write, ticks_cmd)
                    time.sleep(1.0)
                    state.payload_mode = True

    finally:
        dynamixel_disconnect(controller)
        print("\033[91mRobot stopped.\033[0m")


def main():
    state = RobotState()

    # Separate thread only for XB emergency stop
    estop_thread = threading.Thread(target=joystick_estop, args=(state,))
    estop_thread.start()

    robot_main_loop(state)

    estop_thread.join()


if __name__ == "__main__":
    main()
