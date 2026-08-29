"""API client for the Mi Medidor (DISCAR / Mr.DiMS) customer portal.

mimedidor.mrdims.com has no public/documented API, so this client can't be
verified against real traffic from this environment (its network policy
blocks that domain). The login step discovers the login form dynamically
(looks for a <form> containing a password input, then fills whichever
inputs look like username/password) instead of hardcoding field names, so
it should survive minor markup differences.

Consumption parsing is best effort: it tries a JSON response first, then a
JS-embedded state blob (__INITIAL_STATE__/__NUXT__/__NEXT_DATA__ patterns
common in SPA dashboards), and raises MiMedidorDataError if neither matches.
If that happens in practice, capture a HAR of the logged-in consumption page
and use it to replace `_extract_reading_from_mapping` with real field names.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

BASE_URL = "https://mimedidor.mrdims.com"
LOGIN_PAGE_URL = BASE_URL + "/"
DASHBOARD_CANDIDATE_PATHS = ("/", "/dashboard", "/panel", "/consumo")

_STATE_BLOB_RE = re.compile(
    r"(?:__INITIAL_STATE__|__NUXT__|__NEXT_DATA__)\s*=\s*(\{.*?\})\s*;", re.DOTALL
)
_CONSUMPTION_KEYS = ("consumo", "consumption", "lectura", "reading", "kwh", "valor", "value")


class MiMedidorError(Exception):
    """Base error for the Mi Medidor client."""


class MiMedidorAuthError(MiMedidorError):
    """Login failed: bad credentials, or no recognizable login form."""


class MiMedidorDataError(MiMedidorError):
    """Consumption data could not be found/parsed on the authenticated pages."""


@dataclass
class MiMedidorReading:
    """A single consumption/reading data point pulled from the portal."""

    value: float
    unit: str | None
    raw: dict[str, Any]


class MiMedidorApiClient:
    """Client for the mimedidor.mrdims.com customer portal."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._logged_in = False

    async def async_login(self) -> None:
        """Log in by discovering the login form on the homepage and submitting it."""
        async with self._session.get(LOGIN_PAGE_URL) as resp:
            if resp.status != 200:
                raise MiMedidorAuthError(f"No se pudo cargar la página de login (HTTP {resp.status})")
            html = await resp.text()

        form = self._find_login_form(BeautifulSoup(html, "html.parser"))
        if form is None:
            raise MiMedidorAuthError(
                "No se encontró un formulario de login reconocible en la página de inicio. "
                "El sitio puede ser una SPA que autentica vía una API en lugar de un form HTML; "
                "hace falta una captura de tráfico real (HAR) para adaptar el cliente."
            )

        action = form.get("action") or LOGIN_PAGE_URL
        post_url = action if action.startswith("http") else BASE_URL + action

        payload: dict[str, str] = {}
        user_field = pass_field = None
        for inp in form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            input_type = (inp.get("type") or "text").lower()
            if input_type == "password":
                pass_field = name
                payload[name] = self._password
            elif input_type in ("text", "email") or "user" in name.lower() or "mail" in name.lower():
                user_field = name
                payload[name] = self._username
            else:
                payload[name] = inp.get("value", "")

        if user_field is None or pass_field is None:
            raise MiMedidorAuthError(
                "No se pudieron identificar los campos de usuario/contraseña del formulario de login."
            )

        async with self._session.post(post_url, data=payload, allow_redirects=True) as resp:
            html = await resp.text()
            final_url = str(resp.url)

        if "login" in final_url.lower() and self._find_login_form(BeautifulSoup(html, "html.parser")):
            raise MiMedidorAuthError("Usuario o contraseña incorrectos.")

        self._logged_in = True

    @staticmethod
    def _find_login_form(soup: BeautifulSoup):
        for form in soup.find_all("form"):
            if form.find("input", {"type": "password"}) is not None:
                return form
        return None

    async def async_get_consumption(self) -> MiMedidorReading:
        """Fetch and parse the consumption dashboard.

        Tries a JSON response and an embedded JS state blob, in that order,
        across a handful of likely dashboard paths.
        """
        if not self._logged_in:
            await self.async_login()

        last_error: Exception | None = None
        for path in DASHBOARD_CANDIDATE_PATHS:
            try:
                async with self._session.get(BASE_URL + path) as resp:
                    if resp.status != 200:
                        continue
                    content_type = resp.headers.get("Content-Type", "")
                    text = await resp.text()
            except aiohttp.ClientError as err:
                last_error = err
                continue

            reading = self._try_parse_json(text, content_type) or self._try_parse_embedded_state(text)
            if reading is not None:
                return reading

        raise MiMedidorDataError(
            "No se pudo encontrar/interpretar el dato de consumo en el panel. "
            "Hace falta una captura real (HAR) de la página de consumo para poder parsearla."
        ) from last_error

    @staticmethod
    def _try_parse_json(text: str, content_type: str) -> MiMedidorReading | None:
        if "json" not in content_type:
            return None
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None
        return MiMedidorApiClient._extract_reading_from_mapping(data)

    @staticmethod
    def _try_parse_embedded_state(html: str) -> MiMedidorReading | None:
        match = _STATE_BLOB_RE.search(html)
        if not match:
            return None
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
        return MiMedidorApiClient._extract_reading_from_mapping(data)

    @staticmethod
    def _extract_reading_from_mapping(data: Any) -> MiMedidorReading | None:
        """Walk a nested dict/list looking for a plausible consumption value."""

        def walk(node: Any) -> tuple[float, dict[str, Any]] | None:
            if isinstance(node, dict):
                for key, value in node.items():
                    if isinstance(value, (int, float)) and key.lower() in _CONSUMPTION_KEYS:
                        return float(value), node
                for value in node.values():
                    found = walk(value)
                    if found is not None:
                        return found
            elif isinstance(node, list):
                for item in node:
                    found = walk(item)
                    if found is not None:
                        return found
            return None

        found = walk(data)
        if found is None:
            return None
        value, raw = found
        return MiMedidorReading(value=value, unit="kWh", raw=raw)
