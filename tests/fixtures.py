"""Static mock data for Qvantum Modbus integration tests.

All pymodbus response objects are plain MagicMock instances — no HA imports.
Test files and conftest.py import from here instead of constructing mocks inline.
"""

from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Representative register values
# ---------------------------------------------------------------------------
# BT1 raw register value → 215 → 21.5 °C after ÷10 scale
MOCK_BT1_RAW = 215
MOCK_BT1_VALUE = 21.5  # expected native_value

# Config-entry data constants used across multiple test files
MOCK_HOST = "192.168.1.100"
MOCK_PORT = 502
MOCK_UNIT_ID = 1
MOCK_TCP_ENTRY_DATA: dict = {
    "connection_type": "tcp",
    "host": MOCK_HOST,
    "port": MOCK_PORT,
    "unit_id": MOCK_UNIT_ID,
}
MOCK_RTU_PORT = "/dev/ttyUSB0"
MOCK_RTU_ENTRY_DATA: dict = {
    "connection_type": "rtu",
    "port": MOCK_RTU_PORT,
    "unit_id": MOCK_UNIT_ID,
    "baudrate": 9600,
    "bytesize": 8,
    "parity": "N",
    "stopbits": 1,
}


# ---------------------------------------------------------------------------
# pymodbus mock response factories
# ---------------------------------------------------------------------------


def mock_register_result(value: int = MOCK_BT1_RAW) -> MagicMock:
    """Return a mock successful read_input_registers / read_holding_registers result."""
    result = MagicMock()
    result.isError.return_value = False
    result.registers = [value]
    return result


def mock_error_result() -> MagicMock:
    """Return a mock error response (device returned Modbus exception response)."""
    result = MagicMock()
    result.isError.return_value = True
    result.registers = []
    return result


def mock_empty_result() -> MagicMock:
    """Return a mock result with an empty registers list."""
    result = MagicMock()
    result.isError.return_value = False
    result.registers = []
    return result
