"""Sensor platform tests — covers sensor.py and __init__.py for Silver test-coverage."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import EntityRegistry
from pymodbus.exceptions import ConnectionException

from custom_components.qvantum_modbus.const import DOMAIN
from custom_components.qvantum_modbus.models import (
    ModbusCombinedSensorEntityDescription,
    ModbusSensorEntityDescription,
)
from custom_components.qvantum_modbus.sensor import (
    QvantumModbusCombinedSensor,
    QvantumModbusSensor,
)

from .fixtures import MOCK_BT1_VALUE, mock_register_result


# ---------------------------------------------------------------------------
# Entity creation
# ---------------------------------------------------------------------------


async def test_sensor_entity_created(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    entity_registry: EntityRegistry,
    setup_integration,
) -> None:
    """BT1 temperature sensor entity is registered after integration setup."""
    # Look up by domain + unique_id instead; unique_id is deterministic
    entry = entity_registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{mock_tcp_config_entry.entry_id}_bt1_outdoor",
    )
    assert entry is not None


# ---------------------------------------------------------------------------
# native_value — happy path
# ---------------------------------------------------------------------------


async def test_sensor_native_value(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    setup_integration,
) -> None:
    """BT1 sensor reports the decoded register value."""

    # Find the sensor state — entity_id may vary by title; check via unique_id
    from homeassistant.helpers import entity_registry as er

    ent_reg = er.async_get(hass)
    entry = ent_reg.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{mock_tcp_config_entry.entry_id}_bt1_outdoor",
    )
    assert entry is not None
    state = hass.states.get(entry)
    assert state is not None
    assert float(state.state) == pytest.approx(MOCK_BT1_VALUE)


# ---------------------------------------------------------------------------
# available — coordinator data is None
# ---------------------------------------------------------------------------


async def test_sensor_unavailable_when_coordinator_fails(
    hass: HomeAssistant,
    mock_tcp_config_entry,
) -> None:
    """Sensor is unavailable when coordinator raises UpdateFailed on first refresh."""
    mock_client = MagicMock()
    mock_client.connected = False
    mock_client.connect = AsyncMock(return_value=False)
    mock_client.close = MagicMock()

    with patch(
        "custom_components.qvantum_modbus.coordinator.AsyncModbusTcpClient",
        return_value=mock_client,
    ):
        mock_tcp_config_entry.add_to_hass(hass)
        # async_config_entry_first_refresh raises ConfigEntryNotReady on failure,
        # so the entry fails to set up — that is the expected behaviour.
        await hass.config_entries.async_setup(mock_tcp_config_entry.entry_id)
        await hass.async_block_till_done()

    from homeassistant.config_entries import ConfigEntryState

    assert mock_tcp_config_entry.state == ConfigEntryState.SETUP_RETRY, (
        "Entry should be in SETUP_RETRY after first-refresh failure"
    )


# ---------------------------------------------------------------------------
# available — register value is None
# ---------------------------------------------------------------------------


async def test_sensor_unavailable_when_register_is_none(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    mock_tcp_client: MagicMock,
) -> None:
    """Sensor is unavailable when the register value is None (e.g. protocol error)."""
    from .fixtures import mock_error_result

    # Error result → coordinator returns {key: None}
    mock_tcp_client.read_input_registers = AsyncMock(return_value=mock_error_result())
    mock_tcp_client.read_holding_registers = AsyncMock(return_value=mock_error_result())
    mock_tcp_client.write_register = AsyncMock(return_value=mock_error_result())
    mock_tcp_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_tcp_config_entry.entry_id)
    await hass.async_block_till_done()

    from homeassistant.helpers import entity_registry as er

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{mock_tcp_config_entry.entry_id}_bt1_outdoor",
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"


# ---------------------------------------------------------------------------
# async_setup_entry / async_unload_entry
# ---------------------------------------------------------------------------


async def test_setup_and_unload_entry(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    setup_integration: MagicMock,
) -> None:
    """Integration sets up and unloads cleanly."""
    from homeassistant.config_entries import ConfigEntryState

    mock_client = setup_integration

    assert mock_tcp_config_entry.state == ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(mock_tcp_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_tcp_config_entry.state == ConfigEntryState.NOT_LOADED
    mock_client.close.assert_called_once()


# ---------------------------------------------------------------------------
# QvantumModbusSensor.available — coordinator failure (line 65 super False)
# ---------------------------------------------------------------------------


async def test_sensor_unavailable_when_coordinator_update_fails(
    hass: HomeAssistant,
    init_integration,
    mock_tcp_client: MagicMock,
) -> None:
    """Sensor becomes unavailable after coordinator raises UpdateFailed."""
    mock_tcp_client.read_input_registers = AsyncMock(
        side_effect=ConnectionException("link down")
    )
    coordinator = init_integration.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{init_integration.entry_id}_bt1_outdoor"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"


# ---------------------------------------------------------------------------
# QvantumModbusSensor.native_value — ENUM sensor with value_map (line 76)
# ---------------------------------------------------------------------------


async def test_sensor_enum_value_map_returns_mapped_string(
    hass: HomeAssistant,
    mock_tcp_config_entry,
    mock_tcp_client: MagicMock,
) -> None:
    """ENUM sensor with value_map returns the mapped string from native_value."""
    # unit_state at address 40 has value_map={0: "all_off", 1: "on"}
    mock_tcp_client.read_input_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(value=1, count=kw.get("count", 1))
    )
    mock_tcp_client.read_holding_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(value=1, count=kw.get("count", 1))
    )
    mock_tcp_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_tcp_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{mock_tcp_config_entry.entry_id}_unit_state"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "on"


# ---------------------------------------------------------------------------
# QvantumModbusSensor.native_value — value_map called directly (line 76)
# ---------------------------------------------------------------------------


def test_sensor_native_value_enum_direct() -> None:
    """QvantumModbusSensor.native_value maps raw integers via value_map directly."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {"unit_state": 0.0}
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test"
    coordinator.config_entry = coordinator.config_entry

    from custom_components.qvantum_modbus.models import SENSOR_DESCRIPTIONS

    desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "unit_state")
    entity = QvantumModbusSensor(coordinator, desc)
    entity._attr_device_info = MagicMock()

    result = entity.native_value

    assert result == "all_off"  # value_map[0]


def test_alarm_sensor_keeps_code_and_exposes_metadata() -> None:
    """Alarm sensors retain the numeric state and expose catalog metadata."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {"alarm_1_code": 33.0}
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test"

    from custom_components.qvantum_modbus.models import SENSOR_DESCRIPTIONS

    desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "alarm_1_code")
    entity = QvantumModbusSensor(coordinator, desc)
    entity._attr_device_info = MagicMock()

    assert entity.native_value == 33.0
    assert entity.extra_state_attributes == {
        "code": 33,
        "friendly_name": "High Pressure Alarm",
        "trigger": "Pressure envelope exceeded (high-pressure transmitter, BP2).",
        "possible_cause": "Insufficient flow.",
        "product_action": "Manual reset required; block compressor; force immersion heater.",
        "service_action": (
            "Check circulation pump; ensure sufficient flow in heating system."
        ),
    }


def test_alarm_sensor_unknown_code_keeps_raw_value() -> None:
    """Unknown alarm codes remain available without fabricated metadata."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {"alarm_1_code": 999.0}
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test"

    from custom_components.qvantum_modbus.models import SENSOR_DESCRIPTIONS

    desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "alarm_1_code")
    entity = QvantumModbusSensor(coordinator, desc)
    entity._attr_device_info = MagicMock()

    assert entity.native_value == 999.0
    assert entity.extra_state_attributes == {
        "code": 999,
        "friendly_name": "Unknown alarm code (999)",
        "trigger": None,
        "possible_cause": None,
        "product_action": None,
        "service_action": None,
    }


# ---------------------------------------------------------------------------
# QvantumModbusCombinedSensor.available — coordinator failure (line 103)
# ---------------------------------------------------------------------------


async def test_combined_sensor_unavailable_when_coordinator_fails(
    hass: HomeAssistant,
    init_integration,
    mock_tcp_client: MagicMock,
) -> None:
    """Combined sensor becomes unavailable after coordinator raises UpdateFailed."""
    mock_tcp_client.read_input_registers = AsyncMock(
        side_effect=ConnectionException("link down")
    )
    coordinator = init_integration.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{init_integration.entry_id}_ip_address"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"


# ---------------------------------------------------------------------------
# QvantumModbusCombinedSensor.native_value — component None (line 116)
# ---------------------------------------------------------------------------


def test_combined_sensor_native_value_none_when_component_missing() -> None:
    """native_value returns None when any component register value is None."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coord_data = {"_ip_1": 192.0, "_ip_2": None, "_ip_3": 1.0, "_ip_4": 1.0}
    coordinator.data = coord_data
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test"

    from custom_components.qvantum_modbus.models import COMBINED_SENSOR_DESCRIPTIONS

    desc = next(d for d in COMBINED_SENSOR_DESCRIPTIONS if d.key == "ip_address")
    entity = QvantumModbusCombinedSensor(coordinator, desc)
    entity._attr_device_info = MagicMock()

    assert entity.native_value is None


# ---------------------------------------------------------------------------
# QvantumModbusCombinedSensor.native_value — no value_fn or format_fn (line 122)
# ---------------------------------------------------------------------------


def test_combined_sensor_native_value_none_when_no_fn() -> None:
    """native_value returns None when neither value_fn nor format_fn is set."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {"_c1": 1.0, "_c2": 2.0}
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test"

    # Build a description with no value_fn and no format_fn
    desc = ModbusCombinedSensorEntityDescription(
        key="test_combined",
        components=(
            ModbusSensorEntityDescription(key="_c1", address=0),
            ModbusSensorEntityDescription(key="_c2", address=1),
        ),
        format_fn=None,
        value_fn=None,
    )
    entity = QvantumModbusCombinedSensor(coordinator, desc)
    entity._attr_device_info = MagicMock()

    assert entity.native_value is None


# ---------------------------------------------------------------------------
# QvantumModbusSensor.native_value — returns None when raw is None (line 76)
# ---------------------------------------------------------------------------


def test_sensor_native_value_none_when_data_is_none() -> None:
    """native_value returns None when coordinator.data[key] is None."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {"bt1_outdoor": None}
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test"

    from custom_components.qvantum_modbus.models import SENSOR_DESCRIPTIONS

    desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == "bt1_outdoor")
    entity = QvantumModbusSensor(coordinator, desc)
    entity._attr_device_info = MagicMock()

    assert entity.native_value is None
