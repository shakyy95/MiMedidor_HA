"""API client for the Mi Medidor (DISCAR / Mr.DiMS) customer portal.

mimedidor.mrdims.com is an Angular SPA, not a site with a plain HTML login
form: it authenticates against a separate JSON REST API at api.mrdims.com.
The endpoints, parameter names and response field names below were pulled
directly out of the production JS bundle
(main-es2015.b8c87b7b683cb96a1e82.js, service class around `urlAPI =
"https://api.mrdims.com/V2/api/"`), specifically the methods
`obtenerUsuarioLogin`, `obtenerDatosSuministro`, `obtenerDatosTerminal` and
`obtenerFacturacion`, and confirmed against a live logged-in account:

- `Usuarios` returns `{"token": ..., "urlLogo": ..., ...}`.
- `Suministros` returns meter/supply identification plus real-time figures
  (`ConsumoActual`, `DemandaActual`, `UltimoAcumulado.ActivaT0`, ...).
- `Terminales/{numeroSerie[4:12]}` returns the terminal's last periodic
  reading (`UltimoPeriodico`: voltage/current/power factor/frequency/relay
  state) and its own copy of `UltimoAcumulado`.
- `Facturacion?periodos=1` returns `{"Periodos": [{...,
  "TotalActivaImportada": ...}]}` for the current billing period;
  `TotalActivaImportada` is a per-period delta (verified equal to
  `UltimoLectura.ActivaT0 - PrimeraLectura.ActivaT0`), not a lifetime
  cumulative reading. `UltimoAcumulado.ActivaT0`, by contrast, *is* the
  lifetime cumulative active-energy reading (grows monotonically), which is
  why it's the one used for the `TOTAL_INCREASING` energy sensor.
- `Consumos?desde=...&hasta=...&agrupadoPor=2&incluirNulos=true` returns a
  list of one entry per day (`FechaHora`, `Activa`/`Reactiva`/`Aparente` in
  Wh/VARh/VAh, `CosPhi`) — this is what the portal's own "Energía" daily bar
  chart is built from; verified the returned `Activa` values against that
  chart. The CO2-estimate figure shown in the portal isn't an API field: the
  Angular bundle computes it client-side as
  `kg_CO2 = (Suministros.ConsumoEstimadoMes / 1000) * 0.43` (Argentina grid
  emission factor) and a "car-equivalent" as `kg_CO2 / 262`; both are
  reproduced the same way here rather than looked up.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://api.mrdims.com/V2/api/"


class MiMedidorError(Exception):
    """Base error for the Mi Medidor client."""


class MiMedidorAuthError(MiMedidorError):
    """Login failed: bad credentials, or an unexpected response shape."""


class MiMedidorDataError(MiMedidorError):
    """Suministro/terminal/consumption data could not be fetched or parsed."""


@dataclass
class MiMedidorData:
    """Raw data pulled from the three read endpoints, bundled together."""

    suministro: dict[str, Any] = field(default_factory=dict)
    facturacion: dict[str, Any] = field(default_factory=dict)
    terminal: dict[str, Any] = field(default_factory=dict)
    consumo_diario: list[dict[str, Any]] = field(default_factory=list)


class MiMedidorApiClient:
    """Client for the api.mrdims.com REST API behind mimedidor.mrdims.com."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._token: str | None = None

    async def async_login(self) -> None:
        """Log in against the Usuarios endpoint and store the access token."""
        params = {"usuario": self._username, "password": self._password, "versionApp": "2"}
        async with self._session.get(BASE_URL + "Usuarios", params=params) as resp:
            if resp.status == 401:
                raise MiMedidorAuthError(await self._error_message(resp))
            if resp.status != 200:
                raise MiMedidorError(
                    f"Error inesperado al iniciar sesión (HTTP {resp.status})"
                )
            data = await resp.json(content_type=None)

        token = data.get("token") if isinstance(data, dict) else None
        if not token:
            raise MiMedidorAuthError(
                "La respuesta de login no incluyó un 'token'; el formato de la API "
                "pudo haber cambiado respecto al esperado."
            )
        self._token = token

    @staticmethod
    async def _error_message(resp: aiohttp.ClientResponse) -> str:
        text = await resp.text()
        try:
            parsed = json.loads(text)
        except ValueError:
            return text or "Usuario o contraseña incorrectos."
        return parsed if isinstance(parsed, str) else str(parsed)

    async def _authed_get(self, path: str, **params: Any) -> Any:
        """GET an endpoint with the current token, logging in/retrying once on 401."""
        if self._token is None:
            await self.async_login()

        for attempt in (1, 2):
            async with self._session.get(
                BASE_URL + path, params={**params, "token": self._token}
            ) as resp:
                if resp.status == 401 and attempt == 1:
                    await self.async_login()
                    continue
                if resp.status != 200:
                    raise MiMedidorDataError(
                        f"No se pudo obtener '{path}' (HTTP {resp.status})"
                    )
                return await resp.json(content_type=None)

        raise MiMedidorAuthError("La sesión expiró y no se pudo renovar el token.")

    async def async_get_suministro(self) -> dict[str, Any]:
        """Fetch the account's supply/meter identification and live figures."""
        return await self._authed_get("Suministros")

    async def async_get_facturacion(self, periodos: int = 1) -> dict[str, Any]:
        """Fetch billing-period data, including the current period's totals."""
        return await self._authed_get("Facturacion", periodos=periodos)

    async def async_get_terminal(self, numero_serie: str) -> dict[str, Any]:
        """Fetch the terminal's last periodic reading (voltage, current, etc.)."""
        return await self._authed_get("Terminales/" + numero_serie[4:12])

    async def async_get_consumo_diario(self) -> list[dict[str, Any]]:
        """Fetch the last few days of daily energy totals (agrupadoPor=2)."""
        hasta = datetime.now()
        desde = hasta - timedelta(days=3)
        result = await self._authed_get(
            "Consumos",
            desde=desde.strftime("%Y-%m-%dT00:00:00"),
            hasta=hasta.strftime("%Y-%m-%dT23:59:59"),
            agrupadoPor=2,
            incluirNulos="true",
        )
        return result if isinstance(result, list) else []

    async def async_get_data(self) -> MiMedidorData:
        """Fetch and bundle everything the sensors need in one call."""
        suministro = await self.async_get_suministro()

        numero_serie = suministro.get("NumeroDeSerieMedidor") if isinstance(suministro, dict) else None
        if not numero_serie:
            raise MiMedidorDataError(
                "La respuesta de Suministros no incluyó 'NumeroDeSerieMedidor'; "
                "el formato de la API pudo haber cambiado."
            )

        facturacion = await self.async_get_facturacion(periodos=1)
        terminal = await self.async_get_terminal(numero_serie)
        consumo_diario = await self.async_get_consumo_diario()

        return MiMedidorData(
            suministro=suministro,
            facturacion=facturacion,
            terminal=terminal,
            consumo_diario=consumo_diario,
        )
