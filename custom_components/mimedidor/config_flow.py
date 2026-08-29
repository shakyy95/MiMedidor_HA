"""Config flow for the Mi Medidor integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MiMedidorApiClient, MiMedidorAuthError, MiMedidorError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class MiMedidorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mi Medidor."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME])
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = MiMedidorApiClient(
                session, user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            try:
                await client.async_login()
            except MiMedidorAuthError:
                errors["base"] = "invalid_auth"
            except (MiMedidorError, aiohttp.ClientError):
                _LOGGER.exception("Error connecting to mimedidor.mrdims.com")
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=user_input[CONF_USERNAME], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
