"""Data models for the Qvantum Modbus integration.

This module is intentionally kept free of platform imports so that
coordinator.py and sensor.py can both import from here without creating
an import cycle.

Import hierarchy (no cycles):
    const.py  ←  models.py  ←  coordinator.py  ←  sensor.py
                                               ←  __init__.py

A small note; entities with prefix qgm1 or qgm2.  These registers are currently not working, as they return error on read.
They are left in the codebase for future testing and implementation when the issue is resolved. Could be that the device
testing on does not support it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.button import ButtonEntityDescription
from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import (
    EntityCategory,
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)

from .const import (
    DATA_TYPE_ASCII,
    DATA_TYPE_INT16,
    DATA_TYPE_UINT16,
    INPUT_TYPE_HOLDING,
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
    entity_category: EntityCategory | None = None
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
    # For ENUM sensors: maps raw integer register values to translation key strings.
    # When set, native_value returns the mapped string instead of the raw float.
    value_map: dict[int, str] | None = None
    # Re-declared from SensorEntityDescription for type-checker visibility.
    options: list[str] | None = None


@dataclass(frozen=True, kw_only=True)
class ModbusBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Extends BinarySensorEntityDescription with Modbus-specific register metadata."""

    # Re-declared from parent classes for static type checkers.
    key: str
    translation_key: str | None = None
    entity_registry_enabled_default: bool = True
    entity_category: EntityCategory | None = None
    device_class: BinarySensorDeviceClass | None = None

    # Modbus register address
    address: int = 0
    input_type: str = INPUT_TYPE_INPUT
    data_type: str = DATA_TYPE_UINT16
    # For bitmask registers: which bit to extract (0 = LSB).  None = whole register.
    bit_position: int | None = None


@dataclass(frozen=True, kw_only=True)
class ModbusCombinedSensorEntityDescription(SensorEntityDescription):
    """A sensor whose value is derived by combining multiple Modbus register reads.

    The coordinator polls each description listed in *components* and stores the
    raw float values under the component keys.  The entity then calls *format_fn*
    to produce the displayed string.
    """

    # Re-declared from parent classes for static type checkers.
    key: str
    translation_key: str | None = None
    entity_registry_enabled_default: bool = True
    entity_category: EntityCategory | None = None
    native_unit_of_measurement: str | None = None
    device_class: SensorDeviceClass | None = None

    # Sub-register descriptions the coordinator polls when this sensor is enabled.
    # Use underscore-prefixed keys (e.g. "_fw_major") to mark them as internal.
    components: tuple[ModbusSensorEntityDescription, ...]
    # Receives the list of float values (same order as components) and returns
    # the string to display.  Called only when all values are non-None.
    format_fn: Callable[[list[float]], str]


@dataclass(frozen=True, kw_only=True)
class ModbusSwitchEntityDescription(SwitchEntityDescription):
    """Switch entity backed by a Modbus holding register (0=off, 1=on)."""

    key: str
    translation_key: str | None = None
    entity_registry_enabled_default: bool = True
    entity_category: EntityCategory | None = None

    address: int = 0
    input_type: str = INPUT_TYPE_HOLDING
    data_type: str = DATA_TYPE_UINT16


@dataclass(frozen=True, kw_only=True)
class ModbusSelectEntityDescription(SelectEntityDescription):
    """Select entity backed by a Modbus holding register.

    value_map maps raw integer register values → option strings.
    options must contain the same strings as value_map.values().
    """

    key: str
    translation_key: str | None = None
    entity_registry_enabled_default: bool = True
    entity_category: EntityCategory | None = None

    options: list[str] | None = None
    value_map: dict[int, str]

    address: int = 0
    input_type: str = INPUT_TYPE_HOLDING
    data_type: str = DATA_TYPE_UINT16


@dataclass(frozen=True, kw_only=True)
class ModbusNumberEntityDescription(NumberEntityDescription):
    """Number entity backed by a Modbus holding register.

    The coordinator stores the raw register integer as a float.
    native_value = raw * scale; on write: raw = round(native / scale).
    """

    key: str
    translation_key: str | None = None
    entity_registry_enabled_default: bool = True
    entity_category: EntityCategory | None = None
    native_unit_of_measurement: str | None = None
    device_class: NumberDeviceClass | None = None
    mode: NumberMode = NumberMode.BOX

    address: int = 0
    input_type: str = INPUT_TYPE_HOLDING
    data_type: str = DATA_TYPE_UINT16
    scale: float = 1.0
    native_min_value: float = 0.0
    native_max_value: float = 100.0
    native_step: float = 1.0


@dataclass(frozen=True, kw_only=True)
class ModbusButtonEntityDescription(ButtonEntityDescription):
    """Button entity that writes a fixed value to a Modbus holding register."""

    key: str
    translation_key: str | None = None
    entity_registry_enabled_default: bool = True
    entity_category: EntityCategory | None = None

    address: int = 0
    input_type: str = INPUT_TYPE_HOLDING
    data_type: str = DATA_TYPE_UINT16
    # Value written when the button is pressed.
    write_value: int = 1


def _int_range_options(
    raw_min: int,
    raw_max: int,
    scale: float = 1.0,
    decimal_places: int = 0,
    step: int = 1,
) -> tuple[list[str], dict[int, str]]:
    """Build (options, value_map) for a numeric-range select.

    Each raw integer in [raw_min, raw_max] with the given step maps to a
    display string with decimal_places after the decimal separator.
    """
    value_map: dict[int, str] = {}
    for raw in range(raw_min, raw_max + 1, step):
        native = raw * scale
        opt = (
            str(int(round(native)))
            if decimal_places == 0
            else f"{native:.{decimal_places}f}"
        )
        value_map[raw] = opt
    return list(value_map.values()), value_map


def create_number_entity(
    key: str,
    address: int,
    data_type: str = DATA_TYPE_INT16,
    unit: str | None = UnitOfTemperature.CELSIUS,
    device_class: NumberDeviceClass | None = NumberDeviceClass.TEMPERATURE,
    min_value: float = -30.0,
    max_value: float = 30.0,
    scale: float = 1.0,
    step: float = 1.0,
) -> ModbusNumberEntityDescription:
    """Create a number entity with CONFIG category."""
    return ModbusNumberEntityDescription(
        key=key,
        translation_key=key,
        address=address,
        data_type=data_type,
        native_unit_of_measurement=unit,
        device_class=device_class,
        native_min_value=min_value,
        native_max_value=max_value,
        entity_category=EntityCategory.CONFIG,
        scale=scale,
        native_step=step,
    )


def create_dhw_temp_number(key: str, address: int) -> ModbusNumberEntityDescription:
    """Create a DHW temperature setpoint number (UINT16, 20..80 °C, CONFIG)."""
    return ModbusNumberEntityDescription(
        key=key,
        translation_key=key,
        address=address,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_min_value=20,
        native_max_value=80,
        entity_category=EntityCategory.CONFIG,
    )


def create_heating_curve_point(key: str, address: int) -> ModbusNumberEntityDescription:
    """Create a heating curve supply temperature setpoint (UINT16, 10..80 °C, CONFIG)."""
    return ModbusNumberEntityDescription(
        key=key,
        translation_key=key,
        address=address,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_min_value=10,
        native_max_value=80,
        entity_category=EntityCategory.CONFIG,
    )


def create_percent_number(
    key: str, address: int, *, min_value: float = 0
) -> ModbusNumberEntityDescription:
    """Create a percentage number (UINT16, min..100 %, CONFIG)."""
    return ModbusNumberEntityDescription(
        key=key,
        translation_key=key,
        address=address,
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=min_value,
        native_max_value=100,
        entity_category=EntityCategory.CONFIG,
    )


_PRIORITY_TIME_OPTIONS = ["normal_30min", "plus_1h", "plus_plus_2h", "custom"]
_PRIORITY_TIME_MAP = {30: "normal_30min", 60: "plus_1h", 120: "plus_plus_2h"}


def create_priority_time_number(
    key: str, address: int
) -> ModbusSelectEntityDescription:
    """Create a priority time select (30 / 60 / 120 minutes, CONFIG)."""
    return ModbusSelectEntityDescription(
        key=key,
        translation_key=key,
        address=address,
        options=_PRIORITY_TIME_OPTIONS,
        value_map=_PRIORITY_TIME_MAP,
    )


def create_temp_sensor(
    key: str,
    address: int,
    *,
    scale: float = 0.1,
    precision: int = 1,
    data_type: str = DATA_TYPE_INT16,
    entity_registry_enabled_default: bool = True,
) -> ModbusSensorEntityDescription:
    """Create a temperature sensor description with standard defaults."""
    return ModbusSensorEntityDescription(
        key=key,
        translation_key=key,
        address=address,
        data_type=data_type,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=scale,
        precision=precision,
        entity_registry_enabled_default=entity_registry_enabled_default,
    )


def create_duration_sensor(
    key: str,
    address: int,
    unit: str = UnitOfTime.SECONDS,
    state_class: SensorStateClass | str = SensorStateClass.MEASUREMENT,
    *,
    data_type: str = DATA_TYPE_UINT16,
) -> ModbusSensorEntityDescription:
    """Create a duration sensor description with standard defaults."""
    return ModbusSensorEntityDescription(
        key=key,
        translation_key=key,
        address=address,
        data_type=data_type,
        native_unit_of_measurement=unit,
        device_class=SensorDeviceClass.DURATION,
        state_class=state_class,
    )


def create_energy_sensor(
    key: str,
    address: int,
    unit: str,
) -> ModbusSensorEntityDescription:
    """Create an energy counter sensor description with standard defaults."""
    return ModbusSensorEntityDescription(
        key=key,
        translation_key=key,
        address=address,
        data_type=DATA_TYPE_UINT16,
        native_unit_of_measurement=unit,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    )


def create_generic_sensor(
    key: str,
    address: int,
    data_type: str = DATA_TYPE_UINT16,
    native_unit_of_measurement: str | None = None,
    state_class: SensorStateClass | str | None = SensorStateClass.MEASUREMENT,
    scale: float = 0.1,
    precision: int = 1,
    device_class: SensorDeviceClass | None = None,
    options: list[str] | None = None,
    value_map: dict[int, str] | None = None,
    entity_registry_enabled_default: bool = True,
    entity_category: EntityCategory | None = None,
) -> ModbusSensorEntityDescription:
    """Create a generic sensor description with standard defaults."""
    return ModbusSensorEntityDescription(
        key=key,
        translation_key=key,
        address=address,
        data_type=data_type,
        native_unit_of_measurement=native_unit_of_measurement,
        state_class=state_class,
        scale=scale,
        precision=precision,
        device_class=device_class,
        options=options,
        value_map=value_map,
        entity_registry_enabled_default=entity_registry_enabled_default,
        entity_category=entity_category,
    )


# ---------------------------------------------------------------------------
# Sensor definitions
# Add new sensors here; coordinator and platform pick them up automatically.
# ---------------------------------------------------------------------------
SENSOR_DESCRIPTIONS: tuple[ModbusSensorEntityDescription, ...] = (
    # -------------------------------------------------------------------------
    # Main temperature sensors — Input registers 0–21
    # -------------------------------------------------------------------------
    create_temp_sensor("bt1_outdoor", 0),
    create_temp_sensor("bt2_indoor", 2),
    create_temp_sensor("filtered_room", 3),
    create_temp_sensor("bt4", 4),
    create_temp_sensor("bt10_condenser_outlet", 5),
    create_temp_sensor("bt11_supply_addition", 6),
    create_temp_sensor("bt12_supply_external", 7),
    create_temp_sensor("bt13_condenser_inlet", 8),
    create_temp_sensor("bt14_source_flow", 9),
    create_temp_sensor("bt15_source_return", 10),
    # Refrigerant circuit temperatures
    create_temp_sensor("bt20_discharge_line", 11),
    create_temp_sensor("bt21_liquid_line", 12),
    create_temp_sensor("bt22_evaporator_inlet", 13),
    create_temp_sensor("bt23_suction_line", 14),
    create_temp_sensor("bt24_crank_case", 15),
    # DHW tank temperatures
    create_temp_sensor("bt30_dhw_tank", 16),
    create_temp_sensor("bt31_dhw_inlet", 17),
    create_temp_sensor("bt33_dhw_secondary_inlet", 18),
    create_temp_sensor("bt34_dhw_secondary_outlet", 19),
    create_temp_sensor("bt_aux", 20),
    create_temp_sensor("btx", 21),
    # -------------------------------------------------------------------------
    # Calculated / derived temperatures — Input registers 35–38
    # -------------------------------------------------------------------------
    create_temp_sensor("calc_supply_heating", 35),
    create_temp_sensor("calc_supply_cooling", 36, data_type=DATA_TYPE_UINT16),
    create_temp_sensor("heating_curve_offset", 37),
    create_temp_sensor("parallel_cooling_offset", 38),
    # -------------------------------------------------------------------------
    # QGM1 module temperatures — Input registers 119–124
    # NOTE! These does not work! They return error
    # -------------------------------------------------------------------------
    # create_temp_sensor("qgm1_bt10_outlet", 119),
    # create_temp_sensor("qgm1_bt13_inlet", 120),
    # create_temp_sensor("qgm1_bt14_source_return", 121),
    # create_temp_sensor("qgm1_bt15_source_outlet", 122),
    # create_temp_sensor("qgm1_bt20_exhaust", 123),
    # create_temp_sensor("qgm1_bt23_suction", 124),
    # -------------------------------------------------------------------------
    # QGM2 module temperatures — Input registers 134–139
    # NOTE! These does not work! They return error
    # -------------------------------------------------------------------------
    # create_temp_sensor("qgm2_bt10_outlet", 134),
    # create_temp_sensor("qgm2_bt13_inlet", 135),
    # create_temp_sensor("qgm2_bt14_source_return", 136),
    # create_temp_sensor("qgm2_bt15_source_outlet", 137),
    # create_temp_sensor("qgm2_bt20_exhaust", 138),
    # create_temp_sensor("qgm2_bt23_suction", 139),
    # -------------------------------------------------------------------------
    # Flow and pump speeds — Input registers 26–31
    # -------------------------------------------------------------------------
    create_generic_sensor(
        "bf1_dhw_flow",
        26,
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        scale=0.01,
        precision=2,
    ),
    create_generic_sensor(
        "bf1_rpm", 27, native_unit_of_measurement=REVOLUTIONS_PER_MINUTE
    ),
    create_generic_sensor("gp1_pump_speed", 28, native_unit_of_measurement=PERCENTAGE),
    create_generic_sensor(
        "gp2_pump_speed",
        29,
        native_unit_of_measurement=PERCENTAGE,
        scale=1.0,
        precision=0,
    ),
    create_generic_sensor(
        "fan_speed",
        30,
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        scale=1.0,
        precision=0,
    ),
    create_generic_sensor(
        "compressor_speed",
        31,
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        scale=1.0,
        precision=0,
    ),
    # -------------------------------------------------------------------------
    # Heating metrics — Input register 34
    # -------------------------------------------------------------------------
    create_generic_sensor(
        "degree_minute", 34, data_type=DATA_TYPE_INT16, native_unit_of_measurement="dm"
    ),
    # -------------------------------------------------------------------------
    # Operational state registers — Input registers 40–60
    # (On/Off and Yes/No registers are on the binary_sensor platform)
    # -------------------------------------------------------------------------
    create_generic_sensor(
        "unit_state",
        40,
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        scale=1.0,
        precision=0,
        options=["all_off", "on"],
        value_map={0: "all_off", 1: "on"},
    ),
    create_generic_sensor(
        "heatpump_state",
        41,
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        scale=1.0,
        precision=0,
        options=["none", "defrost", "dhw", "heating", "cooling"],
        value_map={0: "none", 1: "defrost", 2: "dhw", 3: "heating", 4: "cooling"},
    ),
    create_generic_sensor(
        "heat_emitter_type",
        48,
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        scale=1.0,
        precision=0,
        options=["floor_heating", "radiators"],
        value_map={0: "floor_heating", 1: "radiators"},
    ),
    # -------------------------------------------------------------------------
    # Priority timers — Input registers 63–65
    # -------------------------------------------------------------------------
    create_duration_sensor("heating_priority_time_left", 63),
    create_duration_sensor("cooling_priority_time_left", 64),
    create_duration_sensor("dhw_priority_time_left", 65),
    # -------------------------------------------------------------------------
    # Defrost and compressor state — Input registers 67–76
    # (time_to_defrost and compressor_blocked are on the binary_sensor platform)
    # -------------------------------------------------------------------------
    create_generic_sensor(
        "compressor_state",
        70,
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        scale=1.0,
        precision=0,
        options=[
            "off",
            "idle",
            "prepare_heating",
            "prepare_cooling",
            "prepare_dhw_1",
            "prepare_dhw_2",
            "heating",
            "cooling",
            "dhw",
            "defrost_dhw_passive",
            "defrost_heating_passive",
            "prepare_pool",
            "pool",
            "defrost_pool_passive",
        ],
        value_map={
            0: "off",
            1: "idle",
            2: "prepare_heating",
            3: "prepare_cooling",
            4: "prepare_dhw_1",
            5: "prepare_dhw_2",
            6: "heating",
            7: "cooling",
            8: "dhw",
            9: "defrost_dhw_passive",
            10: "defrost_heating_passive",
            11: "prepare_pool",
            12: "pool",
            13: "defrost_pool_passive",
        },
    ),
    create_duration_sensor("compressor_blocked_sec", 72),
    create_generic_sensor(
        "qn8_position",
        76,
        data_type=DATA_TYPE_INT16,
        state_class=None,
        scale=1.0,
        precision=0,
    ),
    # -------------------------------------------------------------------------
    # Run times and counters — Input registers 88–91
    # -------------------------------------------------------------------------
    create_duration_sensor(
        "compressor_run_time", 88, UnitOfTime.HOURS, SensorStateClass.TOTAL_INCREASING
    ),
    create_generic_sensor(
        "compressor_starts",
        89,
        state_class=SensorStateClass.TOTAL_INCREASING,
        scale=1.0,
        precision=0,
    ),
    create_duration_sensor(
        "ventilation_fan_run_time",
        90,
        UnitOfTime.HOURS,
        SensorStateClass.TOTAL_INCREASING,
    ),
    create_duration_sensor("ventilation_filter_time_left", 91, UnitOfTime.HOURS),
    # -------------------------------------------------------------------------
    # Power — Input register 93
    # -------------------------------------------------------------------------
    create_generic_sensor(
        "compressor_power",
        93,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        scale=1.0,
        precision=0,
    ),
    # -------------------------------------------------------------------------
    # Energy counters — Input registers 95–104
    # -------------------------------------------------------------------------
    create_energy_sensor("compressor_energy_mwh", 95, UnitOfEnergy.MEGA_WATT_HOUR),
    create_energy_sensor("compressor_energy_kwh", 96, UnitOfEnergy.KILO_WATT_HOUR),
    create_energy_sensor("additional_energy_mwh", 97, UnitOfEnergy.MEGA_WATT_HOUR),
    create_energy_sensor("additional_energy_kwh", 98, UnitOfEnergy.KILO_WATT_HOUR),
    create_energy_sensor("heating_energy_mwh", 99, UnitOfEnergy.MEGA_WATT_HOUR),
    create_energy_sensor("heating_energy_kwh", 100, UnitOfEnergy.KILO_WATT_HOUR),
    create_energy_sensor("cooling_energy_mwh", 101, UnitOfEnergy.MEGA_WATT_HOUR),
    create_energy_sensor("cooling_energy_kwh", 102, UnitOfEnergy.KILO_WATT_HOUR),
    create_energy_sensor("dhw_energy_mwh", 103, UnitOfEnergy.MEGA_WATT_HOUR),
    create_energy_sensor("dhw_energy_kwh", 104, UnitOfEnergy.KILO_WATT_HOUR),
    # -------------------------------------------------------------------------
    # QGM1 non-temperature sensors — Input registers 125–131
    # NOTE! These does not work! They return error
    # -------------------------------------------------------------------------
    # create_generic_sensor(
    #     "qgm1_bp1_low_pressure", 125, data_type=DATA_TYPE_INT16, scale=0.01, precision=2
    # ),
    # create_generic_sensor(
    #     "qgm1_bp2_high_pressure",
    #     126,
    #     data_type=DATA_TYPE_INT16,
    #     scale=0.01,
    #     precision=2,
    # ),
    # create_generic_sensor(
    #     "qgm1_compressor_speed",
    #     128,
    #     data_type=DATA_TYPE_INT16,
    #     native_unit_of_measurement="rps",
    # ),
    # -------------------------------------------------------------------------
    # QGM2 non-temperature sensors — Input registers 140–146
    # NOTE! These does not work! They return error
    # -------------------------------------------------------------------------
    # create_generic_sensor(
    #     "qgm2_bp1_low_pressure", 140, data_type=DATA_TYPE_INT16, scale=0.01, precision=2
    # ),
    # create_generic_sensor(
    #     "qgm2_bp2_high_pressure",
    #     141,
    #     data_type=DATA_TYPE_INT16,
    #     scale=0.01,
    #     precision=2,
    # ),
    # create_generic_sensor(
    #     "qgm2_compressor_speed",
    #     143,
    #     data_type=DATA_TYPE_INT16,
    #     native_unit_of_measurement="rps",
    # ),
    # -------------------------------------------------------------------------
    # Alarm registers — Input registers 150–155
    # -------------------------------------------------------------------------
    create_generic_sensor(
        "active_alarm_count",
        150,
        scale=1.0,
        precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    create_generic_sensor(
        "alarm_1_code",
        151,
        state_class=None,
        scale=1.0,
        precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    create_generic_sensor(
        "alarm_2_code",
        152,
        state_class=None,
        scale=1.0,
        precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    create_generic_sensor(
        "alarm_3_code",
        153,
        state_class=None,
        scale=1.0,
        precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    create_generic_sensor(
        "alarm_4_code",
        154,
        state_class=None,
        scale=1.0,
        precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    create_generic_sensor(
        "alarm_5_code",
        155,
        state_class=None,
        scale=1.0,
        precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # -------------------------------------------------------------------------
    # Smart grid and DHW features — Input registers 157–166
    # (sg_ready_a/b, smart_price_*, energy_prices_available → binary_sensor platform)
    # -------------------------------------------------------------------------
    create_generic_sensor(
        "sg_mode",
        157,
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        scale=1.0,
        precision=0,
        options=["disabled", "blocked", "normal", "encouraged", "ordered"],
        value_map={
            0: "disabled",
            1: "blocked",
            2: "normal",
            3: "encouraged",
            4: "ordered",
        },
    ),
    create_generic_sensor(
        "smart_dhw_mode",
        161,
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        scale=1.0,
        precision=0,
        options=["off", "eco", "balanced", "comfort"],
        value_map={0: "off", 1: "eco", 2: "balanced", 3: "comfort"},
    ),
    create_generic_sensor(
        "smart_dhw_control_status",
        162,
        device_class=SensorDeviceClass.ENUM,
        state_class=None,
        scale=1.0,
        precision=0,
        options=[
            "unavailable",
            "standby",
            "raising",
            "lowering",
            "lowering_long_term",
            "paused",
        ],
        value_map={
            0: "unavailable",
            1: "standby",
            2: "raising",
            3: "lowering",
            4: "lowering_long_term",
            5: "paused",
        },
    ),
    # Note! This does not work.
    # This sensor does not work. It will return 2 chars top, but region could be SE4.
    # create_generic_sensor(
    #     "electricity_price_region",
    #     165,
    #     data_type=DATA_TYPE_ASCII,
    #     state_class=None,
    #     scale=1.0,
    #     precision=0,
    #     entity_category=EntityCategory.DIAGNOSTIC,
    # ),
    # -------------------------------------------------------------------------
    # Device info (diagnostic) — Input registers 180–193
    # (wifi_connected, cloud_connected, vacation_mode → binary_sensor platform)
    # (ip_address, fw_version, serial_number → combined sensor platform)
    # -------------------------------------------------------------------------
)


# ---------------------------------------------------------------------------
# Binary sensor definitions
# ---------------------------------------------------------------------------
BINARY_SENSOR_DESCRIPTIONS: tuple[ModbusBinarySensorEntityDescription, ...] = (
    # -------------------------------------------------------------------------
    # Relay bitmask — Input register 33 (one binary sensor per bit, LSB first)
    # -------------------------------------------------------------------------
    ModbusBinarySensorEntityDescription(
        key="relay_l1",
        translation_key="relay_l1",
        address=33,
        bit_position=0,
    ),
    ModbusBinarySensorEntityDescription(
        key="relay_l2",
        translation_key="relay_l2",
        address=33,
        bit_position=1,
    ),
    ModbusBinarySensorEntityDescription(
        key="relay_l3",
        translation_key="relay_l3",
        address=33,
        bit_position=2,
    ),
    ModbusBinarySensorEntityDescription(
        key="relay_gp10",
        translation_key="relay_gp10",
        address=33,
        bit_position=3,
    ),
    ModbusBinarySensorEntityDescription(
        key="relay_qm10",
        translation_key="relay_qm10",
        address=33,
        bit_position=4,
    ),
    ModbusBinarySensorEntityDescription(
        key="relay_qn8_1",
        translation_key="relay_qn8_1",
        address=33,
        bit_position=5,
    ),
    ModbusBinarySensorEntityDescription(
        key="relay_qn8_2",
        translation_key="relay_qn8_2",
        address=33,
        bit_position=6,
    ),
    ModbusBinarySensorEntityDescription(
        key="relay_gp3",
        translation_key="relay_gp3",
        address=33,
        bit_position=7,
    ),
    ModbusBinarySensorEntityDescription(
        key="relay_pump",
        translation_key="relay_pump",
        address=33,
        bit_position=8,
    ),
    ModbusBinarySensorEntityDescription(
        key="relay_ha12",
        translation_key="relay_ha12",
        address=33,
        bit_position=9,
    ),
    # -------------------------------------------------------------------------
    # Operational states — Input registers 42–60 (0 = Off/No, 1 = On/Yes)
    # -------------------------------------------------------------------------
    ModbusBinarySensorEntityDescription(
        key="heating_released",
        translation_key="heating_released",
        address=42,
    ),
    ModbusBinarySensorEntityDescription(
        key="cooling_released",
        translation_key="cooling_released",
        address=43,
    ),
    ModbusBinarySensorEntityDescription(
        key="compressor_released",
        translation_key="compressor_released",
        address=44,
    ),
    ModbusBinarySensorEntityDescription(
        key="addition_released",
        translation_key="addition_released",
        address=45,
    ),
    ModbusBinarySensorEntityDescription(
        key="heating_demand",
        translation_key="heating_demand",
        address=50,
    ),
    ModbusBinarySensorEntityDescription(
        key="cooling_demand",
        translation_key="cooling_demand",
        address=51,
    ),
    ModbusBinarySensorEntityDescription(
        key="addition_demand",
        translation_key="addition_demand",
        address=52,
    ),
    ModbusBinarySensorEntityDescription(
        key="addition_demand_dhw",
        translation_key="addition_demand_dhw",
        address=53,
    ),
    ModbusBinarySensorEntityDescription(
        key="dhw_demand",
        translation_key="dhw_demand",
        address=54,
    ),
    ModbusBinarySensorEntityDescription(
        key="heat_priority",
        translation_key="heat_priority",
        address=58,
    ),
    ModbusBinarySensorEntityDescription(
        key="cool_priority",
        translation_key="cool_priority",
        address=59,
    ),
    ModbusBinarySensorEntityDescription(
        key="dhw_priority",
        translation_key="dhw_priority",
        address=60,
    ),
    # -------------------------------------------------------------------------
    # Defrost needed — Input register 67 (1 = defrost required)
    # -------------------------------------------------------------------------
    ModbusBinarySensorEntityDescription(
        key="time_to_defrost",
        translation_key="time_to_defrost",
        address=67,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    # -------------------------------------------------------------------------
    # Compressor blocked — Input register 71
    # -------------------------------------------------------------------------
    ModbusBinarySensorEntityDescription(
        key="compressor_blocked",
        translation_key="compressor_blocked",
        address=71,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    # -------------------------------------------------------------------------
    # Detection and protection — Input registers 86–87
    # -------------------------------------------------------------------------
    ModbusBinarySensorEntityDescription(
        key="bt2_detected",
        translation_key="bt2_detected",
        address=86,
    ),
    ModbusBinarySensorEntityDescription(
        key="freeze_protection_active",
        translation_key="freeze_protection_active",
        address=87,
        device_class=BinarySensorDeviceClass.COLD,
    ),
    # -------------------------------------------------------------------------
    # BBR lock — Input register 117
    # -------------------------------------------------------------------------
    ModbusBinarySensorEntityDescription(
        key="bbr_locked",
        translation_key="bbr_locked",
        address=117,
        device_class=BinarySensorDeviceClass.LOCK,
    ),
    # -------------------------------------------------------------------------
    # QGM1 binary states — Input registers 129–131
    # NOTE! These does not work! They return error
    # -------------------------------------------------------------------------
    # ModbusBinarySensorEntityDescription(
    #     key="qgm1_4way_valve",
    #     translation_key="qgm1_4way_valve",
    #     address=129,
    #
    # ),
    # ModbusBinarySensorEntityDescription(
    #     key="qgm1_flow_switch",
    #     translation_key="qgm1_flow_switch",
    #     address=130,
    #
    # ),
    # ModbusBinarySensorEntityDescription(
    #     key="qgm1_gp4_pump",
    #     translation_key="qgm1_gp4_pump",
    #     address=131,
    #     device_class=BinarySensorDeviceClass.RUNNING,
    #
    # ),
    # -------------------------------------------------------------------------
    # QGM2 binary states — Input registers 144–146
    # NOTE! These does not work! They return error
    # -------------------------------------------------------------------------
    # ModbusBinarySensorEntityDescription(
    #     key="qgm2_4way_valve",
    #     translation_key="qgm2_4way_valve",
    #     address=144,
    #
    # ),
    # ModbusBinarySensorEntityDescription(
    #     key="qgm2_flow_switch",
    #     translation_key="qgm2_flow_switch",
    #     address=145,
    #
    # ),
    # ModbusBinarySensorEntityDescription(
    #     key="qgm2_gp4_pump",
    #     translation_key="qgm2_gp4_pump",
    #     address=146,
    #     device_class=BinarySensorDeviceClass.RUNNING,
    #
    # ),
    # -------------------------------------------------------------------------
    # Smart grid ready — Input registers 158–159
    # -------------------------------------------------------------------------
    ModbusBinarySensorEntityDescription(
        key="sg_ready_a",
        translation_key="sg_ready_a",
        address=158,
        device_class=BinarySensorDeviceClass.POWER,
    ),
    ModbusBinarySensorEntityDescription(
        key="sg_ready_b",
        translation_key="sg_ready_b",
        address=159,
        device_class=BinarySensorDeviceClass.POWER,
    ),
    # -------------------------------------------------------------------------
    # Smart price toggles — Input registers 163–164 (disabled by default)
    # -------------------------------------------------------------------------
    ModbusBinarySensorEntityDescription(
        key="smart_price_dhw_enabled",
        translation_key="smart_price_dhw_enabled",
        address=163,
    ),
    ModbusBinarySensorEntityDescription(
        key="smart_price_heating_enabled",
        translation_key="smart_price_heating_enabled",
        address=164,
    ),
    # -------------------------------------------------------------------------
    # Energy prices and connectivity — Input registers 166–170
    # -------------------------------------------------------------------------
    ModbusBinarySensorEntityDescription(
        key="energy_prices_available",
        translation_key="energy_prices_available",
        address=166,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    ModbusBinarySensorEntityDescription(
        key="wifi_connected",
        translation_key="wifi_connected",
        address=168,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ModbusBinarySensorEntityDescription(
        key="cloud_connected",
        translation_key="cloud_connected",
        address=169,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ModbusBinarySensorEntityDescription(
        key="vacation_mode",
        translation_key="vacation_mode",
        address=170,
    ),
)


# ---------------------------------------------------------------------------
# Combined (multi-register) sensor definitions
# The coordinator polls each component and the entity formats the result.
# ---------------------------------------------------------------------------
COMBINED_SENSOR_DESCRIPTIONS: tuple[ModbusCombinedSensorEntityDescription, ...] = (
    ModbusCombinedSensorEntityDescription(
        key="ip_address",
        translation_key="ip_address",
        entity_category=EntityCategory.DIAGNOSTIC,
        components=(
            ModbusSensorEntityDescription(
                key="_ip_1", address=186, data_type=DATA_TYPE_UINT16
            ),
            ModbusSensorEntityDescription(
                key="_ip_2", address=187, data_type=DATA_TYPE_UINT16
            ),
            ModbusSensorEntityDescription(
                key="_ip_3", address=188, data_type=DATA_TYPE_UINT16
            ),
            ModbusSensorEntityDescription(
                key="_ip_4", address=189, data_type=DATA_TYPE_UINT16
            ),
        ),
        format_fn=lambda vals: ".".join(str(int(v)) for v in vals),
    ),
    ModbusCombinedSensorEntityDescription(
        key="fw_version",
        translation_key="fw_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        components=(
            ModbusSensorEntityDescription(
                key="_fw_major", address=191, data_type=DATA_TYPE_UINT16
            ),
            ModbusSensorEntityDescription(
                key="_fw_minor", address=192, data_type=DATA_TYPE_UINT16
            ),
            ModbusSensorEntityDescription(
                key="_fw_patch", address=193, data_type=DATA_TYPE_UINT16
            ),
        ),
        format_fn=lambda vals: f"{int(vals[0])}.{int(vals[1])}.{int(vals[2])}",
    ),
    ModbusCombinedSensorEntityDescription(
        key="serial_number",
        translation_key="serial_number",
        entity_category=EntityCategory.DIAGNOSTIC,
        components=(
            ModbusSensorEntityDescription(
                key="_sn_1", address=180, data_type=DATA_TYPE_UINT16
            ),
            ModbusSensorEntityDescription(
                key="_sn_2", address=181, data_type=DATA_TYPE_UINT16
            ),
            ModbusSensorEntityDescription(
                key="_sn_3", address=182, data_type=DATA_TYPE_UINT16
            ),
            ModbusSensorEntityDescription(
                key="_sn_4", address=183, data_type=DATA_TYPE_UINT16
            ),
            ModbusSensorEntityDescription(
                key="_sn_5", address=184, data_type=DATA_TYPE_UINT16
            ),
        ),
        format_fn=lambda vals: str(int(vals[0]))
        + "".join(f"{int(v):03d}" for v in vals[1:]),
    ),
)

# ---------------------------------------------------------------------------
# Pre-computed range options for numeric selects
# ---------------------------------------------------------------------------
_TEMP_SELECT_OPTS, _TEMP_SELECT_MAP = _int_range_options(
    150, 250, scale=0.1, decimal_places=0, step=10
)

# Room compensation has exactly four discrete values: 0, 0.5, 1, 2
_ROOM_COMP_OPTS = ["0", "0.5", "1", "2"]
_ROOM_COMP_MAP = {0: "0", 5: "0.5", 10: "1", 20: "2"}
_OFFSET_OPTS, _OFFSET_MAP = _int_range_options(
    -9, 9, scale=1.0, decimal_places=0, step=1
)

# ---------------------------------------------------------------------------
# Switch descriptions (holding registers, 0=off 1=on)
# ---------------------------------------------------------------------------
SWITCH_DESCRIPTIONS: tuple[ModbusSwitchEntityDescription, ...] = (
    ModbusSwitchEntityDescription(
        key="unit_on_off",
        translation_key="unit_on_off",
        address=0,
    ),
    ModbusSwitchEntityDescription(
        key="manual_allow_heating",
        translation_key="manual_allow_heating",
        address=2,
    ),
    ModbusSwitchEntityDescription(
        key="manual_allow_cooling",
        translation_key="manual_allow_cooling",
        address=3,
    ),
    ModbusSwitchEntityDescription(
        key="manual_allow_addition",
        translation_key="manual_allow_addition",
        address=4,
    ),
    ModbusSwitchEntityDescription(
        key="manual_allow_dhw",
        translation_key="manual_allow_dhw",
        address=5,
    ),
    ModbusSwitchEntityDescription(
        key="dew_point_protection",
        translation_key="dew_point_protection",
        address=39,
        entity_category=EntityCategory.CONFIG,
    ),
    ModbusSwitchEntityDescription(
        key="dhw_uninterrupted_cooling",
        translation_key="dhw_uninterrupted_cooling",
        address=61,
        entity_category=EntityCategory.CONFIG,
    ),
    ModbusSwitchEntityDescription(
        key="bt12_mounted",
        translation_key="bt12_mounted",
        address=83,
        entity_category=EntityCategory.CONFIG,
    ),
    ModbusSwitchEntityDescription(
        key="qs_unit_connected",
        translation_key="qs_unit_connected",
        address=84,
        entity_category=EntityCategory.CONFIG,
    ),
    ModbusSwitchEntityDescription(
        key="sg_enabled",
        translation_key="sg_enabled",
        address=88,
        entity_category=EntityCategory.CONFIG,
    ),
    ModbusSwitchEntityDescription(
        key="outdoor_air_mixed",
        translation_key="outdoor_air_mixed",
        address=89,
        entity_category=EntityCategory.CONFIG,
    ),
)

# ---------------------------------------------------------------------------
# Select descriptions (holding registers, enum or numeric-range options)
# ---------------------------------------------------------------------------
SELECT_DESCRIPTIONS: tuple[ModbusSelectEntityDescription, ...] = (
    ModbusSelectEntityDescription(
        key="operation_mode",
        translation_key="operation_mode",
        address=1,
        options=["auto", "manual", "only_addition"],
        value_map={0: "auto", 1: "manual", 2: "only_addition"},
    ),
    ModbusSelectEntityDescription(
        key="use_operation_mode_sensor",
        translation_key="use_operation_mode_sensor",
        address=9,
        entity_category=EntityCategory.CONFIG,
        options=["no", "yes_bt2", "yes_bt3", "yes_aux", "external"],
        value_map={0: "no", 1: "yes_bt2", 2: "yes_bt3", 3: "yes_aux", 4: "external"},
    ),
    ModbusSelectEntityDescription(
        key="desired_indoor_temperature",
        translation_key="desired_indoor_temperature",
        address=12,
        data_type=DATA_TYPE_INT16,
        options=_TEMP_SELECT_OPTS,
        value_map=_TEMP_SELECT_MAP,
    ),
    ModbusSelectEntityDescription(
        key="room_compensation_factor",
        translation_key="room_compensation_factor",
        address=13,
        entity_category=EntityCategory.CONFIG,
        options=_ROOM_COMP_OPTS,
        value_map=_ROOM_COMP_MAP,
    ),
    ModbusSelectEntityDescription(
        key="heating_curve_parallel_offset",
        translation_key="heating_curve_parallel_offset",
        address=15,
        data_type=DATA_TYPE_INT16,
        entity_category=EntityCategory.CONFIG,
        options=_OFFSET_OPTS,
        value_map=_OFFSET_MAP,
    ),
    ModbusSelectEntityDescription(
        key="curve_type_heating",
        translation_key="curve_type_heating",
        address=22,
        entity_category=EntityCategory.CONFIG,
        options=["auto", "user_defined"],
        value_map={0: "auto", 1: "user_defined"},
    ),
    ModbusSelectEntityDescription(
        key="cooling_curve_parallel_offset",
        translation_key="cooling_curve_parallel_offset",
        address=36,
        data_type=DATA_TYPE_INT16,
        entity_category=EntityCategory.CONFIG,
        options=_OFFSET_OPTS,
        value_map=dict(_OFFSET_MAP),
    ),
    ModbusSelectEntityDescription(
        key="dhw_mode",
        translation_key="dhw_mode",
        address=53,
        options=["eco", "normal", "extra", "smart"],
        value_map={0: "eco", 1: "normal", 2: "extra", 3: "smart"},
    ),
    ModbusSelectEntityDescription(
        key="dhw_outlet_temperature",
        translation_key="dhw_outlet_temperature",
        address=60,
        entity_category=EntityCategory.CONFIG,
        options=["normal", "plus", "plus_plus"],
        value_map={0: "normal", 1: "plus", 2: "plus_plus"},
    ),
    ModbusSelectEntityDescription(
        key="ventilation_state",
        translation_key="ventilation_state",
        address=68,
        options=["off", "normal", "extra", "reduced"],
        value_map={0: "off", 1: "normal", 2: "extra", 3: "reduced"},
    ),
    create_priority_time_number("heating_priority_time", 73),
    create_priority_time_number("cooling_priority_time", 74),
    create_priority_time_number("dhw_priority_time", 75),
)

# ---------------------------------------------------------------------------
# Number descriptions (holding registers, numeric range)
# ---------------------------------------------------------------------------
NUMBER_DESCRIPTIONS: tuple[ModbusNumberEntityDescription, ...] = (
    # --- Duration (hours) ---
    ModbusNumberEntityDescription(
        key="time_between_heating_cooling",
        translation_key="time_between_heating_cooling",
        address=6,
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=NumberDeviceClass.DURATION,
        native_min_value=0,
        native_max_value=48,
        entity_category=EntityCategory.CONFIG,
    ),
    ModbusNumberEntityDescription(
        key="filtertime_outdoor_sensor",
        translation_key="filtertime_outdoor_sensor",
        address=8,
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=NumberDeviceClass.DURATION,
        native_min_value=0,
        native_max_value=48,
        entity_category=EntityCategory.CONFIG,
    ),
    # --- Temperature setpoints (INT16 °C) ---
    create_number_entity("allow_addition_temperature", 7, min_value=-29, max_value=30),
    create_number_entity("outdoor_temp_stop_heating", 18),
    create_number_entity("start_cooling_temperature", 38),
    create_number_entity("max_heating_supply_temp", 19, min_value=20, max_value=80),
    create_number_entity(
        "min_heating_supply_temp",
        20,
        data_type=DATA_TYPE_UINT16,
        min_value=10,
        max_value=80,
    ),
    create_number_entity("min_cooling_supply_temp", 40, min_value=7, max_value=30),
    create_number_entity(
        "room_temp_external", 14, min_value=-5.0, max_value=40.0, scale=0.1, step=0.1
    ),
    # --- DHW temperature setpoints (UINT16, 20..80 °C) ---
    create_dhw_temp_number("dhw_start_temp_normal", 56),
    create_dhw_temp_number("dhw_stop_temp_normal", 57),
    create_dhw_temp_number("dhw_start_temp_extra", 58),
    create_dhw_temp_number("dhw_stop_temp_extra", 59),
    # --- Heating curve (dimensionless compensation + user-defined points) ---
    create_number_entity(
        "temp_compensation_curve_heating",
        23,
        data_type=DATA_TYPE_UINT16,
        unit=None,
        device_class=None,
        min_value=1,
        max_value=50,
    ),
    create_heating_curve_point("heating_curve_minus30", 24),
    create_heating_curve_point("heating_curve_minus20", 25),
    create_heating_curve_point("heating_curve_minus10", 26),
    create_heating_curve_point("heating_curve_0", 27),
    create_heating_curve_point("heating_curve_10", 28),
    create_heating_curve_point("heating_curve_20", 29),
    create_heating_curve_point("heating_curve_30", 30),
    # --- Pump speeds (%, min 1) ---
    create_percent_number("pump_speed_heating", 63, min_value=1),
    create_percent_number("pump_speed_cooling", 64, min_value=1),
    create_percent_number("dhw_pump_speed", 65, min_value=1),
    create_percent_number("pump_speed_idle", 66, min_value=1),
    # --- Fan speeds (%, min 0) ---
    create_percent_number("ventilation_fan_speed_reduced", 69),
    create_percent_number("ventilation_fan_speed_normal", 70),
    create_percent_number("ventilation_fan_speed_extra", 71),
    create_percent_number("compressor_fan_speed", 72),
)

# ---------------------------------------------------------------------------
# Button descriptions (holding registers, write-once trigger)
# ---------------------------------------------------------------------------
BUTTON_DESCRIPTIONS: tuple[ModbusButtonEntityDescription, ...] = (
    ModbusButtonEntityDescription(
        key="reset_alarms",
        translation_key="reset_alarms",
        address=99,
        write_value=1,
    ),
)
