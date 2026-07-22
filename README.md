# DEALR Arm

Minimal Python control software for the second-generation DEALR Dynamixel arm.
The old DEALR application is archived under `legacy/dealr_v1`.

The bring-up program captures and holds the arm's current pose, then optionally
moves all motors to a fixed raw home position. It does not contain joint limits
or a kinematic model yet.

## Hardware configuration

| ID | Role | Model | Operating mode |
|---:|---|---|---:|
| 11 | Base roll | XH540-W270-T | 4, extended position |
| 12 | Coupled shoulder A | XH540-W270-T | 4, extended position |
| 13 | Coupled shoulder B | XH540-W270-T | 4, extended position |
| 14 | Elbow pitch | XH540-W270-T | 4, extended position |
| 21 | Wrist pitch | XL430-W250-T | 4, extended position |
| 22 | Wrist yaw | XL430-W250-T | 4, extended position |
| 23 | Wrist roll | XL430-W250-T | 4, extended position |
| 24 | Rack-and-pinion gripper | XL430-W250-T | 4, extended position |

The bus uses Dynamixel Protocol 2.0 at 1 Mbps. For the current extended-position
test, Goal Current is not written to IDs 11–14 and therefore does not provide a
runtime torque ceiling. The EEPROM Current Limit remains unchanged.

The raw home positions are:

```text
11: 1532    12: 1204    13: 2767    14: 357
21: 2871    22: 1535    23: 1014    24: 3989
```

## Environment

Create the Conda environment:

```bash
conda env create -f environment.yml
conda activate DEALR
```

If the `DEALR` environment already exists:

```bash
conda activate DEALR
python -m pip install "dynamixel-sdk>=3.7.31"
```

Installing the local command is optional:

```bash
python -m pip install -e .
```

## First hold test

Before running:

- Put the arm in its stable, supported resting pose with torque disabled.
- Start with the gripper fully open.
- Close Dynamixel Wizard so it releases the U2D2 serial port.
- Keep the 12 V barrel connector within reach as the hardware cutoff.

List available serial ports:

```bash
python bringup.py --list-ports
```

Run the test on the currently identified macOS U2D2 port:

```bash
python bringup.py --port /dev/cu.usbserial-FT89FILY
```

The program reboots all eight motors to reset multi-turn tracking to the
single-turn absolute range, rewrites the operating modes while torque is
disabled, reads the current encoder positions, copies them into Goal Position,
and then waits for Enter before enabling torque. Once enabled, type `h` or `H`
and press Enter to start a three-second linear position ramp. The host sends all
eight interpolated Goal Positions together at 200 Hz, for 600 small synchronized
steps. No telemetry is read and nothing is redrawn during motion, leaving the
serial bus exclusively to Goal Position commands. Press Enter without typing a
command to disable torque and exit.

Do not remove the physical support until the captured pose is holding correctly.
This program is not an emergency-stop system; disconnect motor power if the arm
moves unexpectedly.
