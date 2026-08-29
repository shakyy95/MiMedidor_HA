"""Data update coordinator for the Mi Medidor integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MiMedidorApiClient, MiMedidorAuthError, MiMedidorError, MiMedidorReading
from .const import DEFAULT_SCAN_INTERVAL_MINUTES, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MiMedidorCoordinator(DataUpdateCoordinator[MiMedidorReading]):
    """Coordinates polling of mimedidor.mrdims.com."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES),
        )
        self.entry = entry
        session = async_get_clientsession(hass)
        self.client = MiMedidorApiClient(
            session, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
        )

    async def _async_update_data(self) -> MiMedidorReading:
        try:
            return await self.client.async_get_consumption()
        except MiMedidorAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except MiMedidorError as err:
            raise UpdateFailed(str(err)) from err
