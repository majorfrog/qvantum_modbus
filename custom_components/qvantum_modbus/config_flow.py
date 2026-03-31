"""Config flow for the Qvantum Modbus integration."""

from __future__ import annotations

import logging
from typing import Any, Self

from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_BAUDRATE,
    CONF_BYTESIZE,
    CONF_CONNECTION_TYPE,
    CONF_PARITY,
    CONF_UNIT_ID,
    CONF_STOPBITS,
    CONNECTION_TYPE_RTU,
    CONNECTION_TYPE_TCP,
    DEFAULT_BAUDRATE,
    DEFAULT_BYTESIZE,
    DEFAULT_PARITY,
    DEFAULT_UNIT_ID,
    DEFAULT_STOPBITS,
    DEFAULT_TCP_PORT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class QvantumModbusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Qvantum Modbus."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialise the flow."""
        self._connection_type: str | None = None

    def is_matching(self, other_flow: Self) -> bool:
        """Return False — duplicate detection is handled via unique IDs."""
        return False

    # ------------------------------------------------------------------
    # Schema builders — shared by initial and reconfigure flows
    # ------------------------------------------------------------------

    @staticmethod
    def _tcp_schema(
        defaults: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the TCP connection form schema."""
        d = defaults or {}
        return vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=d.get(CONF_HOST, vol.UNDEFINED)
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
                vol.Required(
                    CONF_PORT, default=d.get(CONF_PORT, DEFAULT_TCP_PORT)
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=65535, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_UNIT_ID, default=d.get(CONF_UNIT_ID, DEFAULT_UNIT_ID)
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=247, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
            }
        )

    @staticmethod
    def _rtu_schema(
        defaults: dict[str, Any] | None = None,
    ) -> vol.Schema:
        """Build the RTU connection form schema."""
        d = defaults or {}
        return vol.Schema(
            {
                vol.Required(
                    CONF_PORT, default=d.get(CONF_PORT, vol.UNDEFINED)
                ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
                vol.Required(
                    CONF_UNIT_ID, default=d.get(CONF_UNIT_ID, DEFAULT_UNIT_ID)
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=247, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_BAUDRATE, default=d.get(CONF_BAUDRATE, DEFAULT_BAUDRATE)
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=300, max=115200, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_BYTESIZE, default=d.get(CONF_BYTESIZE, DEFAULT_BYTESIZE)
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=5, max=8, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_PARITY, default=d.get(CONF_PARITY, DEFAULT_PARITY)
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value="N", label="None"),
                            SelectOptionDict(value="E", label="Even"),
                            SelectOptionDict(value="O", label="Odd"),
                        ],
                        mode=SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_STOPBITS,
                    default=str(d.get(CONF_STOPBITS, DEFAULT_STOPBITS)),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value="1", label="1"),
                            SelectOptionDict(value="2", label="2"),
                        ],
                        mode=SelectSelectorMode.LIST,
                    )
                ),
            }
        )

    # ------------------------------------------------------------------
    # Step 0 — YAML import (no user interaction)
    # ------------------------------------------------------------------

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Create a config entry from a configuration.yaml entry.

        Validation has already been performed by CONFIG_SCHEMA in __init__.py.
        A connection test is skipped here on purpose — the device may be
        temporarily offline at startup without that being a fatal error.
        """
        conn_type = import_data[CONF_CONNECTION_TYPE]
        if conn_type == CONNECTION_TYPE_TCP:
            port = import_data.get(CONF_PORT, DEFAULT_TCP_PORT)
            unique_id = (
                f"tcp_{import_data[CONF_HOST]}_{port}"
                f"_{import_data.get(CONF_UNIT_ID, DEFAULT_UNIT_ID)}"
            )
            title = "Qvantum Heat Pump"
            data = {
                CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
                CONF_HOST: import_data[CONF_HOST],
                CONF_PORT: port,
                CONF_UNIT_ID: import_data.get(CONF_UNIT_ID, DEFAULT_UNIT_ID),
            }
        else:
            port = import_data[CONF_PORT]
            unit_id = import_data.get(CONF_UNIT_ID, DEFAULT_UNIT_ID)
            unique_id = f"rtu_{str(port).replace('/', '_')}_{unit_id}"
            title = "Qvantum Heat Pump"
            data = {
                CONF_CONNECTION_TYPE: CONNECTION_TYPE_RTU,
                CONF_PORT: port,
                CONF_UNIT_ID: unit_id,
                CONF_BAUDRATE: import_data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE),
                CONF_BYTESIZE: import_data.get(CONF_BYTESIZE, DEFAULT_BYTESIZE),
                CONF_PARITY: import_data.get(CONF_PARITY, DEFAULT_PARITY),
                CONF_STOPBITS: import_data.get(CONF_STOPBITS, DEFAULT_STOPBITS),
            }

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=title, data=data)

    # ------------------------------------------------------------------
    # Step 1 — select transport type
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user to choose TCP or RTU."""
        if user_input is not None:
            self._connection_type = user_input[CONF_CONNECTION_TYPE]
            if self._connection_type == CONNECTION_TYPE_TCP:
                return await self.async_step_tcp()
            return await self.async_step_rtu()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CONNECTION_TYPE): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(
                                    value=CONNECTION_TYPE_TCP, label="TCP/IP"
                                ),
                                SelectOptionDict(
                                    value=CONNECTION_TYPE_RTU, label="RTU (Serial)"
                                ),
                            ],
                            mode=SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
        )

    # ------------------------------------------------------------------
    # Step 2a — TCP connection details
    # ------------------------------------------------------------------

    async def async_step_tcp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Gather TCP host, port, and unit ID; test the connection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = AsyncModbusTcpClient(
                host=user_input[CONF_HOST],
                port=int(user_input[CONF_PORT]),
            )
            try:
                connected = await client.connect()
            except Exception:  # noqa: BLE001 — catch-all to surface as UI error
                _LOGGER.debug(
                    "TCP connection test failed for %s:%d",
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                    exc_info=True,
                )
                errors["base"] = "cannot_connect"
            else:
                if not connected:
                    errors["base"] = "cannot_connect"
            finally:
                client.close()

            if not errors:
                host = user_input[CONF_HOST]
                port = int(user_input[CONF_PORT])
                unit_id = int(user_input[CONF_UNIT_ID])
                unique_id = f"tcp_{host}_{port}_{unit_id}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Qvantum Heat Pump",
                    data={
                        CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_UNIT_ID: unit_id,
                    },
                )

        return self.async_show_form(
            step_id="tcp",
            data_schema=self._tcp_schema(),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Step 2b — RTU connection details
    # ------------------------------------------------------------------

    async def async_step_rtu(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Gather serial port settings; test the connection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = AsyncModbusSerialClient(
                port=user_input[CONF_PORT],
                baudrate=user_input[CONF_BAUDRATE],
                bytesize=user_input[CONF_BYTESIZE],
                parity=user_input[CONF_PARITY],
                stopbits=user_input[CONF_STOPBITS],
            )
            try:
                connected = await client.connect()
            except Exception:  # noqa: BLE001 — catch-all to surface as UI error
                _LOGGER.debug(
                    "RTU connection test failed for port %s",
                    user_input[CONF_PORT],
                    exc_info=True,
                )
                errors["base"] = "cannot_connect"
            else:
                if not connected:
                    errors["base"] = "cannot_connect"
            finally:
                client.close()

            if not errors:
                port = user_input[CONF_PORT]
                unit_id = int(user_input[CONF_UNIT_ID])
                unique_id = f"rtu_{port.replace('/', '_')}_{unit_id}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Qvantum Heat Pump",
                    data={
                        CONF_CONNECTION_TYPE: CONNECTION_TYPE_RTU,
                        CONF_PORT: port,
                        CONF_UNIT_ID: unit_id,
                        CONF_BAUDRATE: int(user_input[CONF_BAUDRATE]),
                        CONF_BYTESIZE: int(user_input[CONF_BYTESIZE]),
                        CONF_PARITY: user_input[CONF_PARITY],
                        CONF_STOPBITS: int(user_input[CONF_STOPBITS]),
                    },
                )

        return self.async_show_form(
            step_id="rtu",
            data_schema=self._rtu_schema(),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Reconfigure flow — update connection params without removing entry
    # ------------------------------------------------------------------

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow updating connection parameters without removing the entry."""
        entry = self._get_reconfigure_entry()
        conn_type = entry.data[CONF_CONNECTION_TYPE]
        errors: dict[str, str] = {}

        if user_input is not None:
            if conn_type == CONNECTION_TYPE_TCP:
                client: AsyncModbusTcpClient | AsyncModbusSerialClient = (
                    AsyncModbusTcpClient(
                        host=user_input[CONF_HOST],
                        port=int(user_input[CONF_PORT]),
                    )
                )
            else:
                client = AsyncModbusSerialClient(
                    port=user_input[CONF_PORT],
                    baudrate=int(user_input[CONF_BAUDRATE]),
                    bytesize=int(user_input[CONF_BYTESIZE]),
                    parity=user_input[CONF_PARITY],
                    stopbits=int(user_input[CONF_STOPBITS]),
                )

            try:
                connected = await client.connect()
            except Exception:  # noqa: BLE001 — catch-all to surface as UI error
                errors["base"] = "cannot_connect"
            else:
                if not connected:
                    errors["base"] = "cannot_connect"
            finally:
                client.close()

            if not errors:
                if conn_type == CONNECTION_TYPE_TCP:
                    host = user_input[CONF_HOST]
                    port = int(user_input[CONF_PORT])
                    unit_id = int(user_input[CONF_UNIT_ID])
                    new_unique_id = f"tcp_{host}_{port}_{unit_id}"
                    data_updates: dict[str, Any] = {
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_UNIT_ID: unit_id,
                    }
                else:
                    port_str = user_input[CONF_PORT]
                    unit_id = int(user_input[CONF_UNIT_ID])
                    new_unique_id = f"rtu_{port_str.replace('/', '_')}_{unit_id}"
                    data_updates = {
                        CONF_PORT: port_str,
                        CONF_UNIT_ID: unit_id,
                        CONF_BAUDRATE: int(user_input[CONF_BAUDRATE]),
                        CONF_BYTESIZE: int(user_input[CONF_BYTESIZE]),
                        CONF_PARITY: user_input[CONF_PARITY],
                        CONF_STOPBITS: int(user_input[CONF_STOPBITS]),
                    }
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=new_unique_id,
                    data_updates=data_updates,
                )

        # Build schema pre-populated with the current entry values.
        if conn_type == CONNECTION_TYPE_TCP:
            data_schema = self._tcp_schema(defaults=dict(entry.data))
        else:
            data_schema = self._rtu_schema(defaults=dict(entry.data))

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
        )
