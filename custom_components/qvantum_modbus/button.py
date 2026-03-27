"""Button platform for the Qvantum Modbus integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import QvantumModbusEntity, create_device_info
from .models import BUTTON_DESCRIPTIONS, ModbusButtonEntityDescription

if TYPE_CHECKING:
    from . import QvantumModbusConfigEntry
    from .coordinator import QvantumModbusCoordinator

PARALLEL_UPDATES = 1


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: QvantumModbusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qvantum Modbus button entities from a config entry."""
    coordinator: QvantumModbusCoordinator = entry.runtime_data
    async_add_entities(
        QvantumModbusButton(coordinator, description)
        for description in BUTTON_DESCRIPTIONS
    )


class QvantumModbusButton(QvantumModbusEntity, ButtonEntity):
    """Represents a Modbus holding register write as a Home Assistant button."""

    def __init__(
        self,
        coordinator: QvantumModbusCoordinator,
        description: ModbusButtonEntityDescription,
    ) -> None:
        """Initialise the button."""
        super().__init__(coordinator)
        self.entity_description = description
        config_entry = coordinator.config_entry
        assert config_entry is not None
        self._attr_unique_id = f"{config_entry.entry_id}_{description.key}"
        self._attr_device_info = create_device_info(coordinator)

    async def async_press(self, **kwargs: Any) -> None:
        """Write the configured value to the holding register."""
        desc = self.entity_description
        await self.coordinator.write_holding_register(desc.address, desc.write_value)
