"""Entity base class tests — covers entity.py for Silver test-coverage requirement."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pymodbus.exceptions import ConnectionException

from custom_components.qvantum_modbus.const import DOMAIN
from custom_components.qvantum_modbus.entity import create_device_info

from .fixtures import mock_register_result


# ---------------------------------------------------------------------------
# create_device_info — no config entry raises RuntimeError
# ---------------------------------------------------------------------------


def test_create_device_info_raises_when_no_config_entry() -> None:
    """create_device_info raises RuntimeError when coordinator has no config entry."""
    coordinator = MagicMock()
    coordinator.config_entry = None

    with pytest.raises(RuntimeError, match="create_device_info called before"):
        create_device_info(coordinator)


# ---------------------------------------------------------------------------
# QvantumModbusEntity.available — unavailability logging (lines 77-83)
# ---------------------------------------------------------------------------


async def test_entity_logs_once_when_unavailable(
    hass: HomeAssistant,
    init_integration,
    mock_tcp_client: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Entity logs 'is unavailable' once when the coordinator update fails."""
    mock_tcp_client.read_input_registers = AsyncMock(
        side_effect=ConnectionException("link down")
    )
    coordinator = init_integration.runtime_data

    with caplog.at_level(
        logging.INFO, logger="custom_components.qvantum_modbus.entity"
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    unavailable_msgs = [r for r in caplog.records if "is unavailable" in r.message]
    assert len(unavailable_msgs) >= 1

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{init_integration.entry_id}_bt1_outdoor"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"


# ---------------------------------------------------------------------------
# QvantumModbusEntity.available — recovery logging (lines 85-86)
# ---------------------------------------------------------------------------


async def test_entity_logs_once_when_recovering(
    hass: HomeAssistant,
    init_integration,
    mock_tcp_client: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Entity logs 'back online' once when the coordinator recovers after a failure."""
    coordinator = init_integration.runtime_data

    # Trigger unavailability first
    mock_tcp_client.read_input_registers = AsyncMock(
        side_effect=ConnectionException("link down")
    )
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # Restore healthy client
    mock_tcp_client.read_input_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(count=kw.get("count", 1))
    )
    mock_tcp_client.read_holding_registers = AsyncMock(
        side_effect=lambda **kw: mock_register_result(count=kw.get("count", 1))
    )

    caplog.clear()
    with caplog.at_level(
        logging.INFO, logger="custom_components.qvantum_modbus.entity"
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    recovery_msgs = [r for r in caplog.records if "back online" in r.message]
    assert len(recovery_msgs) >= 1

    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(
        "sensor", DOMAIN, f"{init_integration.entry_id}_bt1_outdoor"
    )
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state != "unavailable"
