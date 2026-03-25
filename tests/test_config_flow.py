"""Config flow tests — 100 % branch coverage (Bronze requirement)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

try:
    from pytest_homeassistant_custom_component.common import MockConfigEntry  # noqa: F401
except ImportError:
    from tests.common import MockConfigEntry  # type: ignore[no-redef]  # noqa: F401

from custom_components.qvantum_modbus.const import (
    CONF_BAUDRATE,
    CONF_BYTESIZE,
    CONF_CONNECTION_TYPE,
    CONF_PARITY,
    CONF_UNIT_ID,
    CONF_STOPBITS,
    CONNECTION_TYPE_RTU,
    CONNECTION_TYPE_TCP,
    DOMAIN,
)
from homeassistant.const import CONF_HOST, CONF_PORT

from .fixtures import MOCK_RTU_ENTRY_DATA, MOCK_TCP_ENTRY_DATA


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tcp_connect_patch(connected: bool = True):
    """Context manager that patches the config-flow TCP client."""

    class _Ctx:
        def __enter__(self):
            self._patcher = patch(
                "custom_components.qvantum_modbus.config_flow.AsyncModbusTcpClient"
            )
            mock_class = self._patcher.__enter__()
            client = MagicMock()
            client.connect = AsyncMock(return_value=connected)
            client.close = MagicMock()
            mock_class.return_value = client
            return client

        def __exit__(self, *args):
            self._patcher.__exit__(*args)

    return _Ctx()


def _rtu_connect_patch(connected: bool = True):
    """Context manager that patches the config-flow RTU client."""

    class _Ctx:
        def __enter__(self):
            self._patcher = patch(
                "custom_components.qvantum_modbus.config_flow.AsyncModbusSerialClient"
            )
            mock_class = self._patcher.__enter__()
            client = MagicMock()
            client.connect = AsyncMock(return_value=connected)
            client.close = MagicMock()
            mock_class.return_value = client
            return client

        def __exit__(self, *args):
            self._patcher.__exit__(*args)

    return _Ctx()


# ---------------------------------------------------------------------------
# User → TCP happy path
# ---------------------------------------------------------------------------


async def test_tcp_flow_success(hass: HomeAssistant) -> None:
    """Full user → TCP flow creates a config entry."""
    with _tcp_connect_patch():
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "tcp"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: MOCK_TCP_ENTRY_DATA["host"],
                CONF_PORT: MOCK_TCP_ENTRY_DATA["port"],
                CONF_UNIT_ID: MOCK_TCP_ENTRY_DATA["unit_id"],
            },
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == MOCK_TCP_ENTRY_DATA["host"]
    assert result["data"][CONF_PORT] == MOCK_TCP_ENTRY_DATA["port"]
    assert result["data"][CONF_UNIT_ID] == MOCK_TCP_ENTRY_DATA["unit_id"]


# ---------------------------------------------------------------------------
# TCP — cannot connect error then recovery
# ---------------------------------------------------------------------------


async def test_tcp_flow_cannot_connect_then_retry(hass: HomeAssistant) -> None:
    """TCP flow shows 'cannot_connect' error and lets the user retry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP}
    )

    # First attempt fails
    with _tcp_connect_patch(connected=False):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: MOCK_TCP_ENTRY_DATA["host"],
                CONF_PORT: MOCK_TCP_ENTRY_DATA["port"],
                CONF_UNIT_ID: MOCK_TCP_ENTRY_DATA["unit_id"],
            },
        )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "tcp"
    assert result["errors"] == {"base": "cannot_connect"}

    # Second attempt succeeds
    with _tcp_connect_patch(connected=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: MOCK_TCP_ENTRY_DATA["host"],
                CONF_PORT: MOCK_TCP_ENTRY_DATA["port"],
                CONF_UNIT_ID: MOCK_TCP_ENTRY_DATA["unit_id"],
            },
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY


# ---------------------------------------------------------------------------
# TCP — exception during connect (e.g. OSError)
# ---------------------------------------------------------------------------


async def test_tcp_flow_connect_raises_exception(hass: HomeAssistant) -> None:
    """TCP flow shows 'cannot_connect' when connect() raises an exception."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP}
    )

    with patch(
        "custom_components.qvantum_modbus.config_flow.AsyncModbusTcpClient"
    ) as mock_class:
        client = MagicMock()
        client.connect = AsyncMock(side_effect=OSError("refused"))
        client.close = MagicMock()
        mock_class.return_value = client

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: MOCK_TCP_ENTRY_DATA["host"],
                CONF_PORT: MOCK_TCP_ENTRY_DATA["port"],
                CONF_UNIT_ID: MOCK_TCP_ENTRY_DATA["unit_id"],
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


# ---------------------------------------------------------------------------
# User → RTU happy path
# ---------------------------------------------------------------------------


async def test_rtu_flow_success(hass: HomeAssistant) -> None:
    """Full user → RTU flow creates a config entry."""
    with _rtu_connect_patch():
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: CONNECTION_TYPE_RTU},
        )
        assert result["step_id"] == "rtu"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_PORT: MOCK_RTU_ENTRY_DATA["port"],
                CONF_UNIT_ID: MOCK_RTU_ENTRY_DATA["unit_id"],
                CONF_BAUDRATE: MOCK_RTU_ENTRY_DATA["baudrate"],
                CONF_BYTESIZE: MOCK_RTU_ENTRY_DATA["bytesize"],
                CONF_PARITY: MOCK_RTU_ENTRY_DATA["parity"],
                CONF_STOPBITS: str(MOCK_RTU_ENTRY_DATA["stopbits"]),
            },
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PORT] == MOCK_RTU_ENTRY_DATA["port"]
    assert result["data"][CONF_UNIT_ID] == MOCK_RTU_ENTRY_DATA["unit_id"]
    assert result["data"][CONF_STOPBITS] == MOCK_RTU_ENTRY_DATA["stopbits"]


# ---------------------------------------------------------------------------
# RTU — cannot connect
# ---------------------------------------------------------------------------


async def test_rtu_flow_cannot_connect(hass: HomeAssistant) -> None:
    """RTU flow shows 'cannot_connect' and presents the form again."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONNECTION_TYPE: CONNECTION_TYPE_RTU}
    )

    with _rtu_connect_patch(connected=False):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_PORT: MOCK_RTU_ENTRY_DATA["port"],
                CONF_UNIT_ID: MOCK_RTU_ENTRY_DATA["unit_id"],
                CONF_BAUDRATE: MOCK_RTU_ENTRY_DATA["baudrate"],
                CONF_BYTESIZE: MOCK_RTU_ENTRY_DATA["bytesize"],
                CONF_PARITY: MOCK_RTU_ENTRY_DATA["parity"],
                CONF_STOPBITS: str(MOCK_RTU_ENTRY_DATA["stopbits"]),
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


# ---------------------------------------------------------------------------
# Duplicate entry prevention
# ---------------------------------------------------------------------------


async def test_duplicate_tcp_entry_aborts(hass: HomeAssistant) -> None:
    """A second TCP entry with the same host/port/unit ID is aborted."""
    with _tcp_connect_patch():
        # First entry
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: MOCK_TCP_ENTRY_DATA["host"],
                CONF_PORT: MOCK_TCP_ENTRY_DATA["port"],
                CONF_UNIT_ID: MOCK_TCP_ENTRY_DATA["unit_id"],
            },
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Duplicate attempt
        result2 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], {CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_HOST: MOCK_TCP_ENTRY_DATA["host"],
                CONF_PORT: MOCK_TCP_ENTRY_DATA["port"],
                CONF_UNIT_ID: MOCK_TCP_ENTRY_DATA["unit_id"],
            },
        )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


# ---------------------------------------------------------------------------
# YAML import (async_step_import)
# ---------------------------------------------------------------------------


async def test_import_tcp(hass: HomeAssistant) -> None:
    """YAML import creates a TCP config entry without a connection test."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=MOCK_TCP_ENTRY_DATA,
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == MOCK_TCP_ENTRY_DATA["host"]
    assert result["data"][CONF_PORT] == MOCK_TCP_ENTRY_DATA["port"]


async def test_import_rtu(hass: HomeAssistant) -> None:
    """YAML import creates an RTU config entry without a connection test."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=MOCK_RTU_ENTRY_DATA,
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PORT] == MOCK_RTU_ENTRY_DATA["port"]


async def test_import_duplicate_aborts(hass: HomeAssistant) -> None:
    """Duplicate YAML import is aborted silently."""
    # First import
    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=MOCK_TCP_ENTRY_DATA,
    )
    # Second import of same device
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=MOCK_TCP_ENTRY_DATA,
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
