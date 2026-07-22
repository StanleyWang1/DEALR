"""Small, model-agnostic wrapper around the official Dynamixel SDK."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, Mapping

from dynamixel_sdk import (
    COMM_SUCCESS,
    GroupSyncRead,
    GroupSyncWrite,
    PacketHandler,
    PortHandler,
)


@dataclass(frozen=True)
class Register:
    """A Dynamixel control-table register."""

    address: int
    size: int
    signed: bool = False


# Registers shared by the XH540-W270-T and XL430-W250-T control tables.
MODEL_NUMBER = Register(0, 2)
OPERATING_MODE = Register(11, 1)
TORQUE_ENABLE = Register(64, 1)
HARDWARE_ERROR_STATUS = Register(70, 1)
GOAL_PWM = Register(100, 2, signed=True)
GOAL_CURRENT = Register(102, 2, signed=True)
PROFILE_ACCELERATION = Register(108, 4)
PROFILE_VELOCITY = Register(112, 4)
GOAL_POSITION = Register(116, 4, signed=True)
PRESENT_CURRENT_OR_LOAD = Register(126, 2, signed=True)
PRESENT_POSITION = Register(132, 4, signed=True)
PRESENT_INPUT_VOLTAGE = Register(144, 2)
PRESENT_TEMPERATURE = Register(146, 1)


class DynamixelError(RuntimeError):
    """Raised when a Dynamixel SDK operation fails."""


class DynamixelBus:
    """Own one serial connection and provide basic and grouped register access."""

    def __init__(
        self,
        device_name: str,
        baudrate: int = 1_000_000,
        protocol_version: float = 2.0,
    ) -> None:
        self.device_name = device_name
        self.baudrate = baudrate
        self.protocol_version = protocol_version
        self.port_handler = PortHandler(device_name)
        self.packet_handler = PacketHandler(protocol_version)
        self.is_open = False

    def open(self) -> None:
        if self.is_open:
            return
        if not self.port_handler.openPort():
            raise DynamixelError(
                f"Could not open {self.device_name}. Close Dynamixel Wizard and "
                "check the --port value."
            )
        self.is_open = True
        if not self.port_handler.setBaudRate(self.baudrate):
            self.close()
            raise DynamixelError(
                f"Could not set {self.device_name} to {self.baudrate:,} baud"
            )

    def close(self) -> None:
        if self.is_open:
            self.port_handler.closePort()
            self.is_open = False

    def __enter__(self) -> DynamixelBus:
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def ping(self, motor_id: int) -> int:
        """Ping one motor and return its model number."""
        self._require_open()
        model_number, comm_result, packet_error = self.packet_handler.ping(
            self.port_handler, motor_id
        )
        self._check_result(motor_id, "ping", comm_result, packet_error)
        return model_number

    def reboot(self, motor_id: int) -> None:
        """Reboot one motor and require its status response."""
        self._require_open()
        comm_result, packet_error = self.packet_handler.reboot(
            self.port_handler, motor_id
        )
        self._check_result(motor_id, "reboot", comm_result, packet_error)

    def read(self, motor_id: int, register: Register) -> int:
        """Read one register from one motor."""
        self._require_open()
        read_method = {
            1: self.packet_handler.read1ByteTxRx,
            2: self.packet_handler.read2ByteTxRx,
            4: self.packet_handler.read4ByteTxRx,
        }.get(register.size)
        if read_method is None:
            raise ValueError(f"Unsupported register size: {register.size}")

        raw_value, comm_result, packet_error = read_method(
            self.port_handler, motor_id, register.address
        )
        self._check_result(motor_id, "read", comm_result, packet_error)
        return self._decode(raw_value, register)

    def write(self, motor_id: int, register: Register, value: int) -> None:
        """Write one register on one motor and require its status response."""
        self._require_open()
        write_method = {
            1: self.packet_handler.write1ByteTxRx,
            2: self.packet_handler.write2ByteTxRx,
            4: self.packet_handler.write4ByteTxRx,
        }.get(register.size)
        if write_method is None:
            raise ValueError(f"Unsupported register size: {register.size}")

        encoded = self._encode_unsigned(value, register)
        comm_result, packet_error = write_method(
            self.port_handler, motor_id, register.address, encoded
        )
        self._check_result(motor_id, "write", comm_result, packet_error)

    def sync_read(
        self,
        register: Register,
        motor_ids: Iterable[int],
        attempts: int = 3,
    ) -> dict[int, int]:
        """Read one register from several motors, retrying brief bus timeouts."""
        self._require_open()
        if attempts < 1:
            raise ValueError("Sync Read attempts must be at least 1")
        ids = tuple(motor_ids)
        group = GroupSyncRead(
            self.port_handler,
            self.packet_handler,
            register.address,
            register.size,
        )
        try:
            for motor_id in ids:
                if not group.addParam(motor_id):
                    raise DynamixelError(
                        f"Could not add motor {motor_id} to Sync Read"
                    )

            last_error = "unknown error"
            for attempt in range(1, attempts + 1):
                comm_result = group.txRxPacket()
                if comm_result == COMM_SUCCESS:
                    missing_ids = [
                        motor_id
                        for motor_id in ids
                        if not group.isAvailable(
                            motor_id, register.address, register.size
                        )
                    ]
                    if not missing_ids:
                        return {
                            motor_id: self._decode(
                                group.getData(
                                    motor_id, register.address, register.size
                                ),
                                register,
                            )
                            for motor_id in ids
                        }
                    last_error = f"missing data from IDs {missing_ids}"
                else:
                    last_error = self.packet_handler.getTxRxResult(comm_result)

                if attempt < attempts:
                    time.sleep(0.02)

            raise DynamixelError(
                f"Sync Read address {register.address} failed after "
                f"{attempts} attempts: {last_error}"
            )
        finally:
            group.clearParam()

    def sync_write(self, register: Register, values: Mapping[int, int]) -> None:
        """Write the same register on several motors in one packet."""
        self._require_open()
        group = GroupSyncWrite(
            self.port_handler,
            self.packet_handler,
            register.address,
            register.size,
        )
        try:
            for motor_id, value in values.items():
                encoded = self._encode_bytes(value, register)
                if not group.addParam(motor_id, encoded):
                    raise DynamixelError(
                        f"Could not add motor {motor_id} to Sync Write"
                    )

            comm_result = group.txPacket()
            if comm_result != COMM_SUCCESS:
                message = self.packet_handler.getTxRxResult(comm_result)
                raise DynamixelError(f"Sync Write communication error: {message}")
        finally:
            group.clearParam()

    def _require_open(self) -> None:
        if not self.is_open:
            raise DynamixelError("Dynamixel serial port is not open")

    def _check_result(
        self,
        motor_id: int,
        operation: str,
        comm_result: int,
        packet_error: int,
    ) -> None:
        if comm_result != COMM_SUCCESS:
            message = self.packet_handler.getTxRxResult(comm_result)
            raise DynamixelError(
                f"Motor {motor_id} {operation} communication error: {message}"
            )
        if packet_error:
            message = self.packet_handler.getRxPacketError(packet_error)
            raise DynamixelError(f"Motor {motor_id} {operation} error: {message}")

    @staticmethod
    def _decode(raw_value: int, register: Register) -> int:
        if register.signed:
            sign_bit = 1 << (register.size * 8 - 1)
            if raw_value & sign_bit:
                raw_value -= 1 << (register.size * 8)
        return raw_value

    @staticmethod
    def _encode_unsigned(value: int, register: Register) -> int:
        DynamixelBus._validate_range(value, register)
        return value & ((1 << (register.size * 8)) - 1)

    @staticmethod
    def _encode_bytes(value: int, register: Register) -> list[int]:
        DynamixelBus._validate_range(value, register)
        return list(
            value.to_bytes(
                register.size,
                byteorder="little",
                signed=register.signed,
            )
        )

    @staticmethod
    def _validate_range(value: int, register: Register) -> None:
        bits = register.size * 8
        if register.signed:
            minimum = -(1 << (bits - 1))
            maximum = (1 << (bits - 1)) - 1
        else:
            minimum = 0
            maximum = (1 << bits) - 1
        if not minimum <= value <= maximum:
            raise ValueError(
                f"Value {value} does not fit a {register.size}-byte "
                f"{'signed' if register.signed else 'unsigned'} register"
            )
