"""Sensor platform for the Mi Medidor integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MiMedidorCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Mi Medidor sensors from a config entry."""
    coordinator: MiMedidorCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MiMedidorConsumptionSensor(coordinator, entry)])


class MiMedidorConsumptionSensor(CoordinatorEntity[MiMedidorCoordinator], SensorEntity):
    """Latest consumption reading from Mi Medidor.

    Device class / TOTAL_INCREASING state class are intentionally not set:
    it's not yet known whether the portal exposes a cumulative meter reading
    or a per-period consumption value that resets. Set those once confirmed.
    """

    _attr_has_entity_name = True
    _attr_name = "Consumo"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: MiMedidorCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_consumo"

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.value

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.unit

    @property
    def extra_state_attributes(self) -> dict:
        if self.coordinator.data is None:
            return {}
        return {"raw": self.coordinator.data.raw}
