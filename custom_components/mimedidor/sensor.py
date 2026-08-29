"""Sensor platform for the Mi Medidor integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import MiMedidorData
from .const import DOMAIN
from .coordinator import MiMedidorCoordinator


def _get(data: dict[str, Any] | None, *path: str) -> Any:
    """Walk a chain of dict keys, returning None if anything is missing."""
    node: Any = data
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _wh_to_kwh(value: Any) -> float | None:
    return None if value is None else round(float(value) / 1000, 3)


@dataclass(frozen=True, kw_only=True)
class MiMedidorSensorEntityDescription(SensorEntityDescription):
    """Sensor description bound to a function that pulls its value from MiMedidorData."""

    value_fn: Callable[[MiMedidorData], Any]
    attrs_fn: Callable[[MiMedidorData], dict[str, Any]] | None = None


SENSOR_DESCRIPTIONS: tuple[MiMedidorSensorEntityDescription, ...] = (
    # -- Energy --------------------------------------------------------
    MiMedidorSensorEntityDescription(
        key="energia_total",
        name="Energía total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda d: _wh_to_kwh(_get(d.suministro, "UltimoAcumulado", "ActivaT0")),
    ),
    MiMedidorSensorEntityDescription(
        key="energia_total_exportada",
        name="Energía total exportada",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda d: _wh_to_kwh(_get(d.suministro, "UltimoAcumulado", "ActivaT0e")),
    ),
    MiMedidorSensorEntityDescription(
        key="consumo_actual",
        name="Consumo actual",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda d: _wh_to_kwh(_get(d.suministro, "ConsumoActual")),
    ),
    MiMedidorSensorEntityDescription(
        key="consumo_periodo_facturacion",
        name="Consumo del período de facturación",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda d: _wh_to_kwh(
            (d.facturacion.get("Periodos") or [{}])[-1].get("TotalActivaImportada")
        ),
        attrs_fn=lambda d: {
            k: (d.facturacion.get("Periodos") or [{}])[-1].get(k)
            for k in ("Descripcion", "Inicio", "Fin")
        },
    ),
    MiMedidorSensorEntityDescription(
        key="consumo_estimado_mes",
        name="Consumo estimado del mes",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda d: _wh_to_kwh(_get(d.suministro, "ConsumoEstimadoMes")),
    ),
    MiMedidorSensorEntityDescription(
        key="consumo_mes_anterior",
        name="Consumo mes anterior",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda d: _wh_to_kwh(_get(d.suministro, "ConsumoMesAnterior")),
    ),
    # -- Power / demand --------------------------------------------------
    MiMedidorSensorEntityDescription(
        key="demanda_actual",
        name="Demanda actual",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda d: _get(d.suministro, "DemandaActual"),
    ),
    MiMedidorSensorEntityDescription(
        key="demanda_maxima",
        name="Demanda máxima registrada",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _get(d.terminal, "UltimoPeriodico", "DemandaMaxW"),
    ),
    MiMedidorSensorEntityDescription(
        key="demanda_maxima_contratada",
        name="Demanda máxima contratada",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _get(d.suministro, "DemandaMaximaServicio"),
    ),
    # -- Power quality ----------------------------------------------------
    MiMedidorSensorEntityDescription(
        key="coseno_phi_facturacion",
        name="Coseno φ (facturación)",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _get(d.terminal, "UltimoPeriodico", "CosPhi"),
    ),
    MiMedidorSensorEntityDescription(
        key="frecuencia",
        name="Frecuencia",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _get(d.terminal, "UltimoPeriodico", "Frecuencia"),
    ),
    # -- Environmental impact (reproduces the portal's own client-side formula) --
    MiMedidorSensorEntityDescription(
        key="co2_estimado_mes",
        name="CO2 estimado del mes",
        native_unit_of_measurement="kg",
        suggested_display_precision=2,
        value_fn=lambda d: round(
            (_get(d.suministro, "ConsumoEstimadoMes") or 0) / 1000 * 0.43, 2
        ),
        attrs_fn=lambda d: {
            "autos_equivalentes": round(
                (_get(d.suministro, "ConsumoEstimadoMes") or 0) / 1000 * 0.43 / 262, 2
            )
        },
    ),
    MiMedidorSensorEntityDescription(
        key="reduccion_estimada_consumo",
        name="Reducción estimada de consumo",
        native_unit_of_measurement="%",
        suggested_display_precision=1,
        value_fn=lambda d: (
            round(
                (
                    (_get(d.suministro, "ConsumoMesAnterior") or 0)
                    - (_get(d.suministro, "ConsumoEstimadoMes") or 0)
                )
                / _get(d.suministro, "ConsumoMesAnterior")
                * 100,
                1,
            )
            if _get(d.suministro, "ConsumoMesAnterior")
            else None
        ),
    ),
    # -- Daily energy (portal's "Energía" daily bar chart) -----------------
    MiMedidorSensorEntityDescription(
        key="energia_hoy",
        name="Energía de hoy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda d: _wh_to_kwh((d.consumo_diario or [{}])[-1].get("Activa")),
        attrs_fn=lambda d: {
            k: (d.consumo_diario or [{}])[-1].get(v)
            for k, v in (
                ("fecha", "FechaHora"),
                ("reactiva_kvarh", "Reactiva"),
                ("aparente_kvah", "Aparente"),
                ("coseno_phi", "CosPhi"),
            )
        },
    ),
    MiMedidorSensorEntityDescription(
        key="energia_ayer",
        name="Energía de ayer",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda d: _wh_to_kwh(
            (d.consumo_diario[-2] if len(d.consumo_diario) >= 2 else {}).get("Activa")
        ),
        attrs_fn=lambda d: {
            k: (d.consumo_diario[-2] if len(d.consumo_diario) >= 2 else {}).get(v)
            for k, v in (
                ("fecha", "FechaHora"),
                ("reactiva_kvarh", "Reactiva"),
                ("aparente_kvah", "Aparente"),
                ("coseno_phi", "CosPhi"),
            )
        },
    ),
    # -- Status -------------------------------------------------------
    MiMedidorSensorEntityDescription(
        key="estado_suministro",
        name="Estado del suministro",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _get(d.suministro, "Estado"),
    ),
    MiMedidorSensorEntityDescription(
        key="estado_rele",
        name="Estado del relé",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _get(d.terminal, "UltimoPeriodico", "EstadoRele"),
    ),
    MiMedidorSensorEntityDescription(
        key="estado_terminal",
        name="Estado del terminal",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _get(d.terminal, "DatosTerminal", "Estado"),
    ),
)


def _phase_sensor_descriptions(data: MiMedidorData) -> list[MiMedidorSensorEntityDescription]:
    """Build voltage/current sensors matching the terminal's monofásico/trifásico wiring."""
    es_trifasico = bool(_get(data.terminal, "DatosTerminal", "EsTrifasico"))
    fases = ("L1", "L2", "L3") if es_trifasico else ("M",)

    descriptions: list[MiMedidorSensorEntityDescription] = []
    for fase in fases:
        suffix = "" if fase == "M" else f" {fase}"
        descriptions.append(
            MiMedidorSensorEntityDescription(
                key=f"tension_{fase.lower()}",
                name=f"Tensión{suffix}",
                device_class=SensorDeviceClass.VOLTAGE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                value_fn=lambda d, f=fase: _get(d.terminal, "UltimoPeriodico", f"Tension{f}"),
            )
        )
        descriptions.append(
            MiMedidorSensorEntityDescription(
                key=f"corriente_{fase.lower()}",
                name=f"Corriente{suffix}",
                device_class=SensorDeviceClass.CURRENT,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                value_fn=lambda d, f=fase: _get(d.terminal, "UltimoPeriodico", f"Corriente{f}"),
            )
        )

    # Power-quality figures (factor de potencia, coseno φ medido, THD) are only
    # ever populated on the L1..L3 channel keys, even on monofásico terminals
    # (where voltage/current instead live under "M") — confirmed against a
    # live monofásico account, where CosPhiL1/FactorPotenciaL1/THDVL1/THDIL1
    # were populated while the L2/L3 equivalents stayed at 0.
    fases_calidad = ("L1", "L2", "L3") if es_trifasico else ("L1",)
    for fase in fases_calidad:
        suffix = "" if not es_trifasico else f" {fase}"
        descriptions.append(
            MiMedidorSensorEntityDescription(
                key=f"factor_potencia_{fase.lower()}",
                name=f"Factor de potencia{suffix}",
                device_class=SensorDeviceClass.POWER_FACTOR,
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d, f=fase: _get(
                    d.terminal, "UltimoPeriodico", f"FactorPotencia{f}"
                ),
            )
        )
        descriptions.append(
            MiMedidorSensorEntityDescription(
                key=f"coseno_phi_medido_{fase.lower()}",
                name=f"Coseno φ medido{suffix}",
                device_class=SensorDeviceClass.POWER_FACTOR,
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d, f=fase: _get(d.terminal, "UltimoPeriodico", f"CosPhi{f}"),
            )
        )
        descriptions.append(
            MiMedidorSensorEntityDescription(
                key=f"thd_tension_{fase.lower()}",
                name=f"THD tensión{suffix}",
                native_unit_of_measurement="%",
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d, f=fase: _get(d.terminal, "UltimoPeriodico", f"THDV{f}"),
            )
        )
        descriptions.append(
            MiMedidorSensorEntityDescription(
                key=f"thd_corriente_{fase.lower()}",
                name=f"THD corriente{suffix}",
                native_unit_of_measurement="%",
                state_class=SensorStateClass.MEASUREMENT,
                entity_category=EntityCategory.DIAGNOSTIC,
                value_fn=lambda d, f=fase: _get(d.terminal, "UltimoPeriodico", f"THDI{f}"),
            )
        )
    return descriptions


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Mi Medidor sensors from a config entry."""
    coordinator: MiMedidorCoordinator = hass.data[DOMAIN][entry.entry_id]
    descriptions = SENSOR_DESCRIPTIONS + tuple(_phase_sensor_descriptions(coordinator.data))
    async_add_entities(
        MiMedidorSensor(coordinator, entry, description) for description in descriptions
    )


class MiMedidorSensor(CoordinatorEntity[MiMedidorCoordinator], SensorEntity):
    """A single Mi Medidor value, driven by a MiMedidorSensorEntityDescription."""

    _attr_has_entity_name = True
    entity_description: MiMedidorSensorEntityDescription

    def __init__(
        self,
        coordinator: MiMedidorCoordinator,
        entry: ConfigEntry,
        description: MiMedidorSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

        suministro = coordinator.data.suministro
        terminal = coordinator.data.terminal
        numero_serie = suministro.get("NumeroDeSerieMedidor")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Mi Medidor",
            manufacturer="DISCAR",
            model=_get(terminal, "DatosTerminal", "TipoTerminal") or "DiMET",
            sw_version=_get(terminal, "DatosTerminal", "VersionFirm"),
            serial_number=numero_serie,
        )

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
