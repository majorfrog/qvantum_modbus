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
    DATA_TYPE_UINT16,
    INPUT_TYPE_INPUT,
)


@dataclass(frozen=True, kw_only=True)
class ModbusSensorEntityDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with Modbus-specific register metadata."""

    # Re-declared from parent classes so that static type checkers (pyright/Pylance)
    # generate the correct __init__ signature.  At runtime, FrozenOrThawed injects
    # these annotations automatically; we just make them visible to the type checker.
    key: str
    translation_key: str | None = None
    entity_registry_enabled_default: bool = True
    native_unit_of_measurement: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | str | None = None

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
    # -------------------------------------------------------------------------
    # Main temperature sensors — Input registers 0–21
    # -------------------------------------------------------------------------
    ModbusSensorEntityDescription(
        key="qvantum_bt1",
        translation_key="qvantum_bt1",
        address=0,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
    ),
    ModbusSensorEntityDescription(
        key="bt2_indoor",
        translation_key="bt2_indoor",
        address=2,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
    ),
    ModbusSensorEntityDescription(
        key="filtered_room",
        translation_key="filtered_room",
        address=3,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="bt4",
        translation_key="bt4",
        address=4,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="bt10_condenser_outlet",
        translation_key="bt10_condenser_outlet",
        address=5,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
    ),
    ModbusSensorEntityDescription(
        key="bt11_supply_addition",
        translation_key="bt11_supply_addition",
        address=6,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
    ),
    ModbusSensorEntityDescription(
        key="bt12_supply_external",
        translation_key="bt12_supply_external",
        address=7,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="bt13_condenser_inlet",
        translation_key="bt13_condenser_inlet",
        address=8,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
    ),
    ModbusSensorEntityDescription(
        key="bt14_source_flow",
        translation_key="bt14_source_flow",
        address=9,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
    ),
    ModbusSensorEntityDescription(
        key="bt15_source_return",
        translation_key="bt15_source_return",
        address=10,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
    ),
    # Refrigerant circuit temperatures — disabled by default
    ModbusSensorEntityDescription(
        key="bt20_discharge_line",
        translation_key="bt20_discharge_line",
        address=11,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="bt21_liquid_line",
        translation_key="bt21_liquid_line",
        address=12,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="bt22_evaporator_inlet",
        translation_key="bt22_evaporator_inlet",
        address=13,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="bt23_suction_line",
        translation_key="bt23_suction_line",
        address=14,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="bt24_crank_case",
        translation_key="bt24_crank_case",
        address=15,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    # DHW tank temperatures
    ModbusSensorEntityDescription(
        key="bt30_dhw_tank",
        translation_key="bt30_dhw_tank",
        address=16,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
    ),
    ModbusSensorEntityDescription(
        key="bt31_dhw_inlet",
        translation_key="bt31_dhw_inlet",
        address=17,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
    ),
    ModbusSensorEntityDescription(
        key="bt33_dhw_secondary_inlet",
        translation_key="bt33_dhw_secondary_inlet",
        address=18,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="bt34_dhw_secondary_outlet",
        translation_key="bt34_dhw_secondary_outlet",
        address=19,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="bt_aux",
        translation_key="bt_aux",
        address=20,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="btx",
        translation_key="btx",
        address=21,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    # -------------------------------------------------------------------------
    # Calculated / derived temperatures — Input registers 35–38
    # -------------------------------------------------------------------------
    ModbusSensorEntityDescription(
        key="calc_supply_heating",
        translation_key="calc_supply_heating",
        address=35,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
    ),
    ModbusSensorEntityDescription(
        key="calc_supply_cooling",
        translation_key="calc_supply_cooling",
        address=36,
        data_type=DATA_TYPE_UINT16,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="heating_curve_offset",
        translation_key="heating_curve_offset",
        address=37,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="parallel_cooling_offset",
        translation_key="parallel_cooling_offset",
        address=38,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    # -------------------------------------------------------------------------
    # QGM1 module temperatures — Input registers 119–124
    # NOTE! These does not work! They return error
    # -------------------------------------------------------------------------
    ModbusSensorEntityDescription(
        key="qgm1_bt10_outlet",
        translation_key="qgm1_bt10_outlet",
        address=119,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="qgm1_bt13_inlet",
        translation_key="qgm1_bt13_inlet",
        address=120,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="qgm1_bt14_source_return",
        translation_key="qgm1_bt14_source_return",
        address=121,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="qgm1_bt15_source_outlet",
        translation_key="qgm1_bt15_source_outlet",
        address=122,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="qgm1_bt20_exhaust",
        translation_key="qgm1_bt20_exhaust",
        address=123,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="qgm1_bt23_suction",
        translation_key="qgm1_bt23_suction",
        address=124,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    # -------------------------------------------------------------------------
    # QGM2 module temperatures — Input registers 134–139
    # NOTE! These does not work! They return error
    # -------------------------------------------------------------------------
    ModbusSensorEntityDescription(
        key="qgm2_bt10_outlet",
        translation_key="qgm2_bt10_outlet",
        address=134,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="qgm2_bt13_inlet",
        translation_key="qgm2_bt13_inlet",
        address=135,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="qgm2_bt14_source_return",
        translation_key="qgm2_bt14_source_return",
        address=136,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="qgm2_bt15_source_outlet",
        translation_key="qgm2_bt15_source_outlet",
        address=137,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="qgm2_bt20_exhaust",
        translation_key="qgm2_bt20_exhaust",
        address=138,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
    ModbusSensorEntityDescription(
        key="qgm2_bt23_suction",
        translation_key="qgm2_bt23_suction",
        address=139,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
        precision=1,
        entity_registry_enabled_default=False,
    ),
)
