"""Pytest fixtures for Qvantum Modbus integration tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

try:
    from pytest_homeassistant_custom_component.common import MockConfigEntry
except ImportError:  # running inside the HA core test suite
    from tests.common import MockConfigEntry  # type: ignore[no-redef]

from custom_components.qvantum_modbus.const import DOMAIN

from .fixtures import (
    MOCK_RTU_ENTRY_DATA,
    MOCK_TCP_ENTRY_DATA,
    mock_register_result,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):  # noqa: PT004
    """Automatically enable custom integrations in every test."""


@pytest.fixture
def mock_tcp_client() -> Generator[MagicMock, None, None]:
    """Patch AsyncModbusTcpClient used by the coordinator and config flow."""
    with patch(
        "custom_components.qvantum_modbus.coordinator.AsyncModbusTcpClient"
    ) as mock_class:
        client = MagicMock()
        client.connected = True
        client.connect = AsyncMock(return_value=True)
        client.close = MagicMock()
        client.read_input_registers = AsyncMock(return_value=mock_register_result())
        mock_class.return_value = client
        yield client


@pytest.fixture
def mock_tcp_config_flow_client() -> Generator[MagicMock, None, None]:
    """Patch AsyncModbusTcpClient used only by the config flow connection test."""
    with patch(
        "custom_components.qvantum_modbus.config_flow.AsyncModbusTcpClient"
    ) as mock_class:
        client = MagicMock()
        client.connect = AsyncMock(return_value=True)
        client.close = MagicMock()
        mock_class.return_value = client
        yield client


@pytest.fixture
def mock_rtu_config_flow_client() -> Generator[MagicMock, None, None]:
    """Patch AsyncModbusSerialClient used only by the config flow connection test."""
    with patch(
        "custom_components.qvantum_modbus.config_flow.AsyncModbusSerialClient"
    ) as mock_class:
        client = MagicMock()
        client.connect = AsyncMock(return_value=True)
        client.close = MagicMock()
        mock_class.return_value = client
        yield client


@pytest.fixture
def mock_tcp_config_entry() -> MockConfigEntry:
    """Return a MockConfigEntry for a TCP connection."""
    return MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_TCP_ENTRY_DATA,
        title=f"{MOCK_TCP_ENTRY_DATA['host']}:{MOCK_TCP_ENTRY_DATA['port']}",
        unique_id=(
            f"tcp_{MOCK_TCP_ENTRY_DATA['host']}"
            f"_{MOCK_TCP_ENTRY_DATA['port']}"
            f"_{MOCK_TCP_ENTRY_DATA['unit_id']}"
        ),
    )


@pytest.fixture
def mock_rtu_config_entry() -> MockConfigEntry:
    """Return a MockConfigEntry for an RTU connection."""
    return MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_RTU_ENTRY_DATA,
        title=f"RTU {MOCK_RTU_ENTRY_DATA['port']} (unit {MOCK_RTU_ENTRY_DATA['unit_id']})",
        unique_id=(
            f"rtu_{MOCK_RTU_ENTRY_DATA['port'].replace('/', '_')}"
            f"_{MOCK_RTU_ENTRY_DATA['unit_id']}"
        ),
    )


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_tcp_config_entry: MockConfigEntry,
    mock_tcp_client: MagicMock,
) -> AsyncGenerator[MockConfigEntry, None]:
    """Set up the integration for testing and tear it down afterwards."""
    mock_tcp_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_tcp_config_entry.entry_id)
    await hass.async_block_till_done()
    yield mock_tcp_config_entry
    await hass.config_entries.async_unload(mock_tcp_config_entry.entry_id)
    await hass.async_block_till_done()
