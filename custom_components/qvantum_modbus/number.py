"""Number platform for the Qvantum Modbus integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import QvantumModbusEntity, create_device_info
from .models import NUMBER_DESCRIPTIONS, ModbusNumberEntityDescription

if TYPE_CHECKING:
    from . import QvantumModbusConfigEntry
    from .coordinator import QvantumModbusCoordinator

PARALLEL_UPDATES = 1


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: QvantumModbusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qvantum Modbus number entities from a config entry."""
    coordinator: QvantumModbusCoordinator = entry.runtime_data
    async_add_entities(
        QvantumModbusNumber(coordinator, description)
        for description in NUMBER_DESCRIPTIONS
    )


class QvantumModbusNumber(QvantumModbusEntity, NumberEntity):
    """Represents a Modbus holding register as a Home Assistant number."""

    def __init__(
        self,
        coordinator: QvantumModbusCoordinator,
        description: ModbusNumberEntityDescription,
    ) -> None:
        """Initialise the number."""
        super().__init__(coordinator)
        self.entity_description = description
        config_entry = coordinator.config_entry
        assert config_entry is not None
        self._attr_unique_id = f"{config_entry.entry_id}_{description.key}"
        self._attr_device_info = create_device_info(coordinator)
        self._attr_native_min_value = description.native_min_value
        self._attr_native_max_value = description.native_max_value
        self._attr_native_step = description.native_step
        self._attr_mode = description.mode

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
    def native_value(self) -> float | None:
        """Return the current value, applying scale from the raw register integer."""
        raw = self.coordinator.data.get(self.entity_description.key)
        if raw is None:
            return None
        return raw * self.entity_description.scale

    async def async_set_native_value(self, value: float) -> None:
        """Write the value to the holding register."""
        desc = self.entity_description
        raw = round(value / desc.scale)
        min_raw = round(desc.native_min_value / desc.scale)
        max_raw = round(desc.native_max_value / desc.scale)
        await self.coordinator.write_holding_register(
            desc.address, raw, min_raw=min_raw, max_raw=max_raw
        )
        await self.coordinator.async_request_refresh()
