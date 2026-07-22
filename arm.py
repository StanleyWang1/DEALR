"""Hardware configuration and initial hold behavior for the DEALR arm."""

from __future__ import annotations

import time
from dataclasses import dataclass

from dynamixel_bus import (
    GOAL_POSITION,
    HARDWARE_ERROR_STATUS,
    OPERATING_MODE,
    PRESENT_CURRENT_OR_LOAD,
    PRESENT_INPUT_VOLTAGE,
    PRESENT_POSITION,
    PRESENT_TEMPERATURE,
    PROFILE_ACCELERATION,
    PROFILE_VELOCITY,
    TORQUE_ENABLE,
    DynamixelBus,
    DynamixelError,
    Register,
)


XH540_MODEL_NUMBER = 1100
XL430_MODEL_NUMBER = 1060
EXTENDED_POSITION_MODE = 4

HOME_POSITIONS = {
    11: 1532,
    12: 1204,
    13: 2767,
    14: 357,
    21: 2871,
    22: 1535,
    23: 1014,
    24: 3989,
}
INITIAL_PROFILE_VELOCITY = 20  # 20 * 0.229 rpm ~= 4.58 rpm
INITIAL_PROFILE_ACCELERATION = 5  # conservative preliminary value


@dataclass(frozen=True)
class MotorConfig:
    motor_id: int
    name: str
    model_name: str
    model_number: int
    operating_mode: int


MOTORS = (
    MotorConfig(
        11,
        "base_roll",
        "XH540-W270-T",
        XH540_MODEL_NUMBER,
        EXTENDED_POSITION_MODE,
    ),
    MotorConfig(
        12,
        "shoulder_a",
        "XH540-W270-T",
        XH540_MODEL_NUMBER,
        EXTENDED_POSITION_MODE,
    ),
    MotorConfig(
        13,
        "shoulder_b",
        "XH540-W270-T",
        XH540_MODEL_NUMBER,
        EXTENDED_POSITION_MODE,
    ),
    MotorConfig(
        14,
        "elbow_pitch",
        "XH540-W270-T",
        XH540_MODEL_NUMBER,
        EXTENDED_POSITION_MODE,
    ),
    MotorConfig(
        21,
        "wrist_pitch",
        "XL430-W250-T",
        XL430_MODEL_NUMBER,
        EXTENDED_POSITION_MODE,
    ),
    MotorConfig(
        22,
        "wrist_yaw",
        "XL430-W250-T",
        XL430_MODEL_NUMBER,
        EXTENDED_POSITION_MODE,
    ),
    MotorConfig(
        23,
        "wrist_roll",
        "XL430-W250-T",
        XL430_MODEL_NUMBER,
        EXTENDED_POSITION_MODE,
    ),
    MotorConfig(
        24,
        "gripper",
        "XL430-W250-T",
        XL430_MODEL_NUMBER,
        EXTENDED_POSITION_MODE,
    ),
)

ALL_IDS = tuple(motor.motor_id for motor in MOTORS)
XH_IDS = tuple(
    motor.motor_id for motor in MOTORS if motor.model_number == XH540_MODEL_NUMBER
)
XL_IDS = tuple(
    motor.motor_id for motor in MOTORS if motor.model_number == XL430_MODEL_NUMBER
)


@dataclass(frozen=True)
class ArmSnapshot:
    positions: dict[int, int]
    xh_currents: dict[int, int]
    voltages: dict[int, int]
    temperatures: dict[int, int]
    hardware_errors: dict[int, int]
    shoulder_relative_residual: int


class Arm:
    """Configure and monitor the known eight-motor DEALR arm."""

    def __init__(self, bus: DynamixelBus) -> None:
        self.bus = bus
        self.hold_positions: dict[int, int] | None = None
        self.torque_enabled = False

    def configure_for_current_pose_hold(self) -> dict[int, int]:
        """Configure modes with torque off and seed goals from live positions."""
        self._verify_models()
        self._reboot_all()

        # The arm must be physically supported before this method is called.
        self._sync_write_and_verify(
            TORQUE_ENABLE, {motor_id: 0 for motor_id in ALL_IDS}
        )
        self.torque_enabled = False
        time.sleep(0.05)  # Allow EEPROM access to settle after torque is disabled.

        # EEPROM configuration is intentionally acknowledged one motor at a time.
        # Sync Write has no per-motor response and can hide a rejected write.
        for motor in MOTORS:
            self.bus.write(motor.motor_id, OPERATING_MODE, motor.operating_mode)
        self._verify_register(
            OPERATING_MODE,
            {motor.motor_id: motor.operating_mode for motor in MOTORS},
        )

        # Mode changes reset these RAM registers, so write them afterwards.
        self._write_each_and_verify(
            PROFILE_ACCELERATION,
            {motor_id: INITIAL_PROFILE_ACCELERATION for motor_id in ALL_IDS},
        )
        self._write_each_and_verify(
            PROFILE_VELOCITY,
            {motor_id: INITIAL_PROFILE_VELOCITY for motor_id in ALL_IDS},
        )
        # Goal Current is intentionally not written during the extended-position
        # mode test. It only acts as a torque ceiling in current-based mode.

        positions = self.bus.sync_read(PRESENT_POSITION, ALL_IDS)
        self._sync_write_and_verify(GOAL_POSITION, positions, tolerance=1)
        self.hold_positions = positions
        return positions.copy()

    def enable_torque(self) -> None:
        if self.hold_positions is None:
            raise RuntimeError("Configure and seed hold positions before enabling torque")
        self._sync_write_and_verify(
            TORQUE_ENABLE, {motor_id: 1 for motor_id in ALL_IDS}
        )
        self.torque_enabled = True

    def disable_torque(self) -> None:
        self._sync_write_and_verify(
            TORQUE_ENABLE, {motor_id: 0 for motor_id in ALL_IDS}
        )
        self.torque_enabled = False

    def read_positions(self) -> dict[int, int]:
        return self.bus.sync_read(PRESENT_POSITION, ALL_IDS)

    def prepare_position_ramp(self) -> None:
        """Let the host-provided position ramp define the motion profile."""
        self._write_each_and_verify(
            PROFILE_ACCELERATION, {motor_id: 0 for motor_id in ALL_IDS}
        )
        self._write_each_and_verify(
            PROFILE_VELOCITY, {motor_id: 0 for motor_id in ALL_IDS}
        )

    def command_positions(
        self, positions: dict[int, int], *, verify: bool = False
    ) -> None:
        if set(positions) != set(ALL_IDS):
            raise ValueError(f"Position command must contain exactly IDs {ALL_IDS}")
        if verify:
            self._sync_write_and_verify(GOAL_POSITION, positions, tolerance=1)
        else:
            self.bus.sync_write(GOAL_POSITION, positions)

    def set_position_reference(self, positions: dict[int, int]) -> None:
        """Set the reference used by the coupled-shoulder drift display."""
        self.hold_positions = positions.copy()

    def read_snapshot(self) -> ArmSnapshot:
        if self.hold_positions is None:
            raise RuntimeError("Hold positions have not been captured")

        positions = self.bus.sync_read(PRESENT_POSITION, ALL_IDS)
        currents = self.bus.sync_read(PRESENT_CURRENT_OR_LOAD, XH_IDS)
        voltages = self.bus.sync_read(PRESENT_INPUT_VOLTAGE, ALL_IDS)
        temperatures = self.bus.sync_read(PRESENT_TEMPERATURE, ALL_IDS)
        hardware_errors = self.bus.sync_read(HARDWARE_ERROR_STATUS, ALL_IDS)

        # Motors 12 and 13 turn oppositely. Their position changes should sum to zero.
        shoulder_residual = abs(
            (positions[12] - self.hold_positions[12])
            + (positions[13] - self.hold_positions[13])
        )
        return ArmSnapshot(
            positions=positions,
            xh_currents=currents,
            voltages=voltages,
            temperatures=temperatures,
            hardware_errors=hardware_errors,
            shoulder_relative_residual=shoulder_residual,
        )

    def _verify_models(self) -> None:
        for motor in MOTORS:
            actual_model = self.bus.ping(motor.motor_id)
            if actual_model != motor.model_number:
                raise DynamixelError(
                    f"Motor {motor.motor_id} ({motor.name}) reported model "
                    f"{actual_model}; expected {motor.model_number} "
                    f"({motor.model_name})"
                )

    def _reboot_all(self) -> None:
        """Reset RAM and multi-turn tracking before configuring the arm."""
        for motor in MOTORS:
            self.bus.reboot(motor.motor_id)
            time.sleep(0.05)
        time.sleep(1.0)
        self._verify_models()

    def _write_each_and_verify(
        self, register: Register, expected: dict[int, int]
    ) -> None:
        """Use acknowledged writes for setup values that need no synchronization."""
        for motor_id, value in expected.items():
            self.bus.write(motor_id, register, value)
        self._verify_register(register, expected)

    def _sync_write_and_verify(
        self,
        register: Register,
        expected: dict[int, int],
        attempts: int = 3,
        tolerance: int = 0,
    ) -> None:
        """Retry an unacknowledged grouped write until readback matches."""
        mismatches: dict[int, tuple[int, int]] = {}
        for attempt in range(1, attempts + 1):
            self.bus.sync_write(register, expected)
            time.sleep(0.05)
            actual = self.bus.sync_read(register, expected)
            mismatches = {
                motor_id: (expected_value, actual[motor_id])
                for motor_id, expected_value in expected.items()
                if abs(actual[motor_id] - expected_value) > tolerance
            }
            if not mismatches:
                return
            if attempt < attempts:
                time.sleep(0.05)

        details = ", ".join(
            f"ID {motor_id}: expected {values[0]}, read {values[1]}"
            for motor_id, values in mismatches.items()
        )
        raise DynamixelError(
            f"Sync Write address {register.address} failed after "
            f"{attempts} attempts: {details}"
        )

    def _verify_register(
        self,
        register: Register,
        expected: dict[int, int],
        attempts: int = 3,
    ) -> None:
        mismatches: dict[int, tuple[int, int]] = {}
        for attempt in range(1, attempts + 1):
            actual = self.bus.sync_read(register, expected)
            mismatches = {
                motor_id: (expected_value, actual[motor_id])
                for motor_id, expected_value in expected.items()
                if actual[motor_id] != expected_value
            }
            if not mismatches:
                return
            if attempt < attempts:
                time.sleep(0.05)

        details = ", ".join(
            f"ID {motor_id}: expected {values[0]}, read {values[1]}"
            for motor_id, values in mismatches.items()
        )
        raise DynamixelError(
            f"Register {register.address} verification failed after "
            f"{attempts} attempts: {details}"
        )
