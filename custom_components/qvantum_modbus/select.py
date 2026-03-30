"""Select platform for the Qvantum Modbus integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import QvantumModbusEntity, create_device_info
from .models import SELECT_DESCRIPTIONS, ModbusSelectEntityDescription

if TYPE_CHECKING:
    from . import QvantumModbusConfigEntry
    from .coordinator import QvantumModbusCoordinator

PARALLEL_UPDATES = 1


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: QvantumModbusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qvantum Modbus select entities from a config entry."""
    coordinator: QvantumModbusCoordinator = entry.runtime_data
    async_add_entities(
        QvantumModbusSelect(coordinator, description)
        for description in SELECT_DESCRIPTIONS
    )


class QvantumModbusSelect(QvantumModbusEntity, SelectEntity):
    """Represents a Modbus holding register as a Home Assistant select."""

    def __init__(
        self,
        coordinator: QvantumModbusCoordinator,
        description: ModbusSelectEntityDescription,
    ) -> None:
        """Initialise the select."""
        super().__init__(coordinator)
        self.entity_description = description
        config_entry = coordinator.config_entry
        assert config_entry is not None
        self._attr_unique_id = f"{config_entry.entry_id}_{description.key}"
        self._attr_device_info = create_device_info(coordinator)
        self._attr_options = description.options

    @property
    def available(self) -> bool:
        """Return True when coordinator succeeded and the register has a value."""
        if not super().available:
            return False
        return (
            self.coordinator.data is not None
            and self.coordinator.data.get(self.entity_description.key) is not None
        )

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option.

        Returns ``"custom"`` when the device reports a value that is not in the
        predefined option map and ``"custom"`` is listed as a valid option.
        This avoids the entity showing no selection for out-of-spec values.
        """
        raw = self.coordinator.data.get(self.entity_description.key)
        if raw is None:
            return None
        mapped = self.entity_description.value_map.get(int(raw))
        if mapped is None and "custom" in self.entity_description.options:
            return "custom"
        return mapped

    async def async_select_option(self, option: str) -> None:
        """Write the selected option to the holding register."""
        if option == "custom":
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
            )
        desc = self.entity_description
        raw = next((k for k, v in desc.value_map.items() if v == option), None)
        if raw is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
            )
        await self.coordinator.write_holding_register(desc.address, raw)
        await self.coordinator.async_request_refresh()
