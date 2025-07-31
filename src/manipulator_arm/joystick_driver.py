import pygame
import time

def joystick_connect():
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        raise RuntimeError("No joystick found.")
    js = pygame.joystick.Joystick(0)
    js.init()
    return js

def joystick_read(js):
    def apply_deadzone(value, deadzone=0.1):
        return 0.0 if abs(value) < deadzone else value

    pygame.event.pump()

    # Axes
    lx_raw = js.get_axis(0)  # Left Stick X
    ly_raw = js.get_axis(1)  # Left Stick Y
    rx_raw = js.get_axis(2)  # Right Stick X
    ry_raw = js.get_axis(3)  # Right Stick Y
    lt_raw = js.get_axis(4)  # Left Trigger (-1 to 1)
    rt_raw = js.get_axis(5)  # Right Trigger (-1 to 1)

    return {
        # Analog sticks (apply deadzone)
        "LX": apply_deadzone(lx_raw),
        "LY": apply_deadzone(ly_raw),
        "RX": apply_deadzone(rx_raw),
        "RY": apply_deadzone(ry_raw),

        # Triggers (remap from [-1,1] to [0,1] and apply deadzone)
        "LT": apply_deadzone((lt_raw + 1) / 2),
        "RT": apply_deadzone((rt_raw + 1) / 2),

        # Face buttons
        "AB": js.get_button(0),  # A
        "BB": js.get_button(1),  # B
        "XB": js.get_button(2),  # X
        "YB": js.get_button(3),  # Y

        # Bumpers
        "LB": js.get_button(4),
        "RB": js.get_button(5),

        # D-pad (hat returns a tuple like (0, 1) = up)
        "DPAD": js.get_hat(0)
    }

def joystick_disconnect(js):
    js.quit()

# Optional: test
if __name__ == "__main__":
    js = joystick_connect()
    try:
        while True:
            start = time.perf_counter()
            data = joystick_read(js)
            end = time.perf_counter()

            loop_time_ms = (end - start) * 1000  # convert to ms
            print(f"{loop_time_ms:.3f} ms | {data}")

            time.sleep(0.05)  # Sleep excluded from timing
    except KeyboardInterrupt:
        joystick_disconnect(js)
        print("Joystick disconnected.")
