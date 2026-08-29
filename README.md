# Mi Medidor (DISCAR / Mr.DiMS) — integración para Home Assistant

Integración custom para Home Assistant que se conecta al portal de
autogestión de consumo eléctrico [mimedidor.mrdims.com](https://mimedidor.mrdims.com/)
(sistema **Mr.DiMS** de **DISCAR**, usado por distribuidoras eléctricas
argentinas con medidores inteligentes DiMET).

## Estado actual

✅ **Validado end-to-end contra una cuenta real** (login, `Suministros` y
`Facturacion`).

`mimedidor.mrdims.com` es una SPA de Angular sin API pública/documentada;
no autentica contra un `<form>` HTML sino contra una API JSON separada en
`https://api.mrdims.com/V2/api/`. Los endpoints y nombres de campos que usa
`custom_components/mimedidor/api.py` se extrajeron del bundle de producción
(`main-es2015.*.js`) y se confirmaron contra el sitio en vivo con una cuenta
real: el login devuelve `token` como se esperaba, y `Facturacion` trae
`TotalActivaImportada`, que coincide exactamente con la diferencia entre la
primera y la última lectura del período (`UltimaLectura.ActivaT0 -
PrimeraLectura.ActivaT0`) — es decir, es el consumo del período actual, no
un acumulado de por vida.

Lo que está resuelto:

- Estructura estándar de integración de Home Assistant (config flow,
  coordinator, sensor) instalable vía HACS (repositorio custom) o
  copiando la carpeta a `custom_components/`.
- **Login**: `GET https://api.mrdims.com/V2/api/Usuarios?usuario=...&password=...&versionApp=2`.
- **Suministro**: `GET .../Suministros?token=...` (número de serie del
  medidor, titular, dirección, estado, `ConsumoActual` en tiempo real).
- **Consumo**: `GET .../Facturacion?token=...&periodos=1`, usando
  `Periodos[-1].TotalActivaImportada` (Wh, convertido a kWh) como el
  consumo del período de facturación actual. Por eso el sensor usa
  `state_class: measurement` y no `total_increasing`: el valor se reinicia
  con cada período de facturación.

## Pendiente

Falta instalar la integración en una instancia real de Home Assistant y
confirmar que el config flow y el sensor se comportan bien en la UI (los
endpoints y el parseo de datos ya están probados vía API directa).

## Instalación

1. Copiar la carpeta `custom_components/mimedidor` a la carpeta
   `custom_components` de tu instalación de Home Assistant (o agregar este
   repositorio como repositorio custom en HACS).
2. Reiniciar Home Assistant.
3. Ir a **Configuración → Dispositivos y servicios → Añadir integración**,
   buscar "Mi Medidor" e ingresar usuario y contraseña.

## Entidades

- `sensor.mi_medidor_consumo`: consumo de energía activa (kWh) del período de
  facturación actual (`Facturacion.Periodos[-1].TotalActivaImportada / 1000`).
  Se reinicia con cada período, por eso el `state_class` es `measurement` y
  no `total_increasing`. Expone `suministro` y `periodo_actual` (la
  respuesta cruda de la API) como atributos extra.
