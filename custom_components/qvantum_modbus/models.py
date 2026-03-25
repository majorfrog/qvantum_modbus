"""Data models for the Qvantum Modbus integration.

This module is intentionally kept free of platform imports so that
coordinator.py and sensor.py can both import from here without creating
an import cycle.

Import hierarchy (no cycles):
    const.py  ←  models.py  ←  coordinator.py  ←  sensor.py
                                               ←  __init__.py
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature

from .const import (
    DATA_TYPE_INT16,
    INPUT_TYPE_INPUT,
)


@dataclass(frozen=True, kw_only=True)
class ModbusSensorEntityDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with Modbus-specific register metadata."""

    # Modbus register address
    address: int = 0
    # Which FC to use: INPUT_TYPE_INPUT or INPUT_TYPE_HOLDING
    input_type: str = INPUT_TYPE_INPUT
    # Raw value type stored in the register
    data_type: str = DATA_TYPE_INT16
    # Multiplied against the decoded integer to produce the final value
    scale: float = 1.0
    # Number of decimal places to round the final value to
    precision: int = 0


# ---------------------------------------------------------------------------
# Sensor definitions
# Add new sensors here; coordinator and platform pick them up automatically.
# ---------------------------------------------------------------------------
SENSOR_DESCRIPTIONS: tuple[ModbusSensorEntityDescription, ...] = (
    ModbusSensorEntityDescription(
        # Address 0 — BT1 temperature sensor
        key="qvantum_bt1",
        translation_key="qvantum_bt1",
        address=0,
        input_type=INPUT_TYPE_INPUT,
        data_type=DATA_TYPE_INT16,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,  # raw value / 10 → e.g. 215 → 21.5 °C
        precision=1,
    ),
)
