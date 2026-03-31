"""Switch platform for the Qvantum Modbus integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import QvantumModbusEntity, create_device_info
from .models import SWITCH_DESCRIPTIONS, ModbusSwitchEntityDescription

if TYPE_CHECKING:
    from . import QvantumModbusConfigEntry
    from .coordinator import QvantumModbusCoordinator

PARALLEL_UPDATES = 1


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: QvantumModbusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Qvantum Modbus switch entities from a config entry."""
    coordinator: QvantumModbusCoordinator = entry.runtime_data
    async_add_entities(
        QvantumModbusSwitch(coordinator, description)
        for description in SWITCH_DESCRIPTIONS
    )


class QvantumModbusSwitch(QvantumModbusEntity, SwitchEntity):
    """Represents a Modbus holding register as a Home Assistant switch."""

    def __init__(
        self,
        coordinator: QvantumModbusCoordinator,
        description: ModbusSwitchEntityDescription,
    ) -> None:
        """Initialise the switch."""
        super().__init__(coordinator)
        self.entity_description = description
        config_entry = coordinator.config_entry
        assert config_entry is not None
        self._attr_unique_id = f"{config_entry.entry_id}_{description.key}"
        self._attr_device_info = create_device_info(coordinator)

    @property
    def available(self) -> bool:
        """Return True when coordinator succeeded and the register has a value.

        If the description specifies ``available_when``, also requires that
        every listed key in coordinator data equals the expected value.  This
        makes mode-gated entities (e.g. manual-mode switches) appear
        unavailable when the device is not in the relevant mode.
        """
        if not super().available:
            return False
        data = self.coordinator.data
        if data is None or data.get(self.entity_description.key) is None:
            return False
        condition = self.entity_description.available_when
        if condition and any(data.get(k) != v for k, v in condition.items()):
            return False
        return True

    @property
    def is_on(self) -> bool | None:
        """Return the current on/off state."""
        raw = self.coordinator.data.get(self.entity_description.key)
        if raw is None:
            return None
        return bool(int(raw))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on by writing 1 to the holding register."""
        await self.coordinator.write_holding_register(
            self.entity_description.address, 1
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off by writing 0 to the holding register."""
        await self.coordinator.write_holding_register(
            self.entity_description.address, 0
        )
        await self.coordinator.async_request_refresh()
