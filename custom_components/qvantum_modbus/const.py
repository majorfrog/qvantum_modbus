"""Constants for the Qvantum Modbus integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "qvantum_modbus"

# Device identity constants
MANUFACTURER: Final = "Qvantum"
MODEL: Final = "Qvantum Heat Pump"

# Connection type configuration key and values
CONF_CONNECTION_TYPE: Final = "connection_type"
CONNECTION_TYPE_TCP: Final = "tcp"
CONNECTION_TYPE_RTU: Final = "rtu"

# Shared configuration keys
CONF_UNIT_ID: Final = "unit_id"

# RTU-specific configuration keys
CONF_BAUDRATE: Final = "baudrate"
CONF_BYTESIZE: Final = "bytesize"
CONF_PARITY: Final = "parity"
CONF_STOPBITS: Final = "stopbits"

# TCP defaults
DEFAULT_TCP_PORT: Final = 502

# RTU / shared defaults
DEFAULT_UNIT_ID: Final = 1
DEFAULT_BAUDRATE: Final = 9600
DEFAULT_BYTESIZE: Final = 8
DEFAULT_PARITY: Final = "N"
DEFAULT_STOPBITS: Final = 1

# How often the coordinator polls the device (seconds).
# Modbus TCP over a local LAN is low-latency and the protocol itself is
# lightweight, so 5 s is the practical floor recommended by HA for local
# devices. Going faster risks saturating single-connection devices that
# cannot queue requests.
SCAN_INTERVAL_SECONDS: Final = 5

# --- Register / data-type Constants ---

# input_type values (which Modbus FC to use for reading)
INPUT_TYPE_INPUT: Final = "input"  # FC 4 — read input registers
INPUT_TYPE_HOLDING: Final = "holding"  # FC 3 — read holding registers

# data_type values
DATA_TYPE_INT16: Final = "int16"
DATA_TYPE_UINT16: Final = "uint16"
DATA_TYPE_INT32: Final = "int32"
DATA_TYPE_UINT32: Final = "uint32"
DATA_TYPE_FLOAT32: Final = "float32"
