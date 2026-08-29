<p align="center">
  <img src="https://raw.githubusercontent.com/shakyy95/MiMedidor_HA/main/custom_components/mimedidor/brand/logo@2x.png" alt="Mi Medidor" width="480">
</p>

<h1 align="center">Mi Medidor (DISCAR / Mr.DiMS) para Home Assistant</h1>

<p align="center">
  <a href="https://github.com/hacs/integration"><img alt="HACS Custom" src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg"></a>
  <a href="https://github.com/shakyy95/MiMedidor_HA/releases"><img alt="Version" src="https://img.shields.io/github/v/release/shakyy95/MiMedidor_HA?sort=semver"></a>
  <a href="https://github.com/shakyy95/MiMedidor_HA/blob/main/custom_components/mimedidor/manifest.json"><img alt="IoT Class" src="https://img.shields.io/badge/IoT%20Class-Cloud%20Polling-blue.svg"></a>
</p>

Integración custom para Home Assistant que se conecta al portal de
autogestión de consumo eléctrico [mimedidor.mrdims.com](https://mimedidor.mrdims.com/)
(sistema **Mr.DiMS** de **DISCAR**, usado por cooperativas y distribuidoras
eléctricas argentinas con medidores inteligentes DiMET) y expone el consumo
del período de facturación actual como un sensor de Home Assistant.

> Proyecto independiente, no afiliado ni respaldado por DISCAR. "Mi Medidor"
> y su logo son marcas de DISCAR; se referencian acá únicamente para
> identificar el servicio con el que se integra.

El ícono/logo de `custom_components/mimedidor/brand/` se muestra en HACS y
en HA a partir de **Home Assistant 2026.3** (soporte nativo de imágenes de
marca para integraciones custom, sin depender de
[home-assistant/brands](https://github.com/home-assistant/brands)). En
versiones anteriores simplemente no se ve ícono; no afecta el
funcionamiento de la integración.

## Estado

✅ Validada end-to-end contra una cuenta real: login, obtención del
suministro y lectura del consumo del período actual funcionan tal cual está
implementado. Falta únicamente instalarla y probarla desde la UI de una
instancia real de Home Assistant.

## Instalación vía HACS

El repositorio es público, así que no hace falta darle a HACS ningún
permiso especial.

1. **Agregar este repo como repositorio custom.** HACS → ⋮ (arriba a la
   derecha) → **Repositorios personalizados** → pegar
   `https://github.com/shakyy95/MiMedidor_HA` → categoría **Integración** →
   Agregar.
2. **Instalar.** Buscá "Mi Medidor" dentro de HACS → Integraciones,
   abrilo y tocá **Descargar**.
3. **Reiniciar Home Assistant.**
4. **Configurar la integración.** Configuración → Dispositivos y servicios
   → Añadir integración → buscar "Mi Medidor" → ingresar el usuario y la
   contraseña del portal mimedidor.mrdims.com.

<details>
<summary>Instalación manual (alternativa sin HACS)</summary>

1. Copiar la carpeta `custom_components/mimedidor` de este repo a la
   carpeta `custom_components` de tu configuración de Home Assistant
   (creála si no existe).
2. Reiniciar Home Assistant.
3. Configuración → Dispositivos y servicios → Añadir integración → "Mi
   Medidor" → ingresar usuario y contraseña.

</details>

## Entidades

Todas las entidades se agrupan bajo un único dispositivo "Mi Medidor" (marca
DISCAR, modelo/versión de firmware y número de serie tomados de
`Terminales`). Se actualizan cada 60 minutos
(`DEFAULT_SCAN_INTERVAL_MINUTES` en `const.py`).

| Entidad | Fuente | Notas |
|---|---|---|
| Energía total | `Suministros.UltimoAcumulado.ActivaT0` | Lectura acumulada de por vida del medidor (kWh). `state_class: total_increasing` — úsala como **consumo de red** en el Panel de Energía de HA. |
| Energía total exportada | `Suministros.UltimoAcumulado.ActivaT0e` | Igual que la anterior pero de energía inyectada a la red (kWh). Solo distinto de cero en suministros bidireccionales (con generación/paneles solares) — úsala como **devolución a la red**. |
| Consumo actual | `Suministros.ConsumoActual` | kWh del período en curso, en vivo. |
| Consumo del período de facturación | `Facturacion.Periodos[-1].TotalActivaImportada` | kWh del período actual según facturación; expone `Descripcion`/`Inicio`/`Fin` como atributos. |
| Consumo estimado del mes | `Suministros.ConsumoEstimadoMes` | kWh. |
| Consumo mes anterior | `Suministros.ConsumoMesAnterior` | kWh. |
| Demanda actual | `Suministros.DemandaActual` | Potencia (W). |
| Demanda máxima registrada *(diagnóstico)* | `Terminales.UltimoPeriodico.DemandaMaxW` | Potencia (W). |
| Tensión / Corriente *(por fase)* | `Terminales.UltimoPeriodico` | Un sensor de tensión y uno de corriente por fase: `TensionM`/`CorrienteM` en medidores monofásicos, o `TensionL1..L3`/`CorrienteL1..L3` en trifásicos (se detecta solo con `DatosTerminal.EsTrifasico`). |
| Factor de potencia *(diagnóstico)* | `Terminales.UltimoPeriodico.FactorPotencia` | Adimensional. |
| Frecuencia *(diagnóstico)* | `Terminales.UltimoPeriodico.Frecuencia` | Hz. |
| Estado del suministro *(diagnóstico)* | `Suministros.Estado` | Texto (p.ej. "Activo"). |
| Estado del relé *(diagnóstico)* | `Terminales.UltimoPeriodico.EstadoRele` | Texto ("Cerrado"/"Abierto"). |
| Estado del terminal *(diagnóstico)* | `Terminales.DatosTerminal.Estado` | Texto (p.ej. "O.K."). |

"Consumo del período de facturación" y "Energía total" difieren a
propósito: el primero se reinicia con cada período (`measurement`), el
segundo es la lectura de por vida del medidor y solo crece
(`total_increasing`) — es el que hay que usar para el Panel de Energía.

## Panel de Energía

"Energía total" y "Energía total exportada" ya cumplen lo que pide el
[Panel de Energía](https://www.home-assistant.io/docs/energy/) de Home
Assistant (`device_class: energy` + `state_class: total_increasing` + kWh),
así que aparecen solas en el selector de sensores:

1. Configuración → **Paneles de energía**.
2. En **Red eléctrica** → *Añadir consumo* → elegir `sensor.mi_medidor_energia_total`.
3. Si el suministro es bidireccional (con generación propia), en *Devolución
   a la red* elegir `sensor.mi_medidor_energia_total_exportada` (para un
   suministro unidireccional queda siempre en 0, no hace falta agregarla).
4. Guardar. HA empieza a generar estadísticas horarias/diarias a partir de
   ahí — las tarjetas de energía (resumen diario, gráfico de barras,
   comparativa, etc.) se arman solas una vez que el sensor está cargado en
   el panel, sin configuración adicional.

## Solución de problemas

- **"Usuario o contraseña incorrectos" al configurar la integración**:
  las credenciales son las mismas que usás para entrar a
  <https://mimedidor.mrdims.com/> desde el navegador.
- **El sensor queda en `unknown` o hay errores en el log**: buscá
  "mimedidor" en **Configuración → Sistema → Registros**. El cliente
  (`api.py`) informa explícitamente si algún endpoint cambió de forma
  (falta un campo esperado, código HTTP inesperado, etc.).
- **HACS no encuentra el repositorio o no lo puede descargar**: confirmá
  que la URL sea exactamente `https://github.com/shakyy95/MiMedidor_HA` y
  que la categoría elegida al agregarlo haya sido **Integración**.

<details>
<summary>Cómo funciona por dentro</summary>

`mimedidor.mrdims.com` es una SPA de Angular sin API pública/documentada: no
autentica contra un formulario HTML, sino contra una API JSON separada en
`https://api.mrdims.com/V2/api/`. Los endpoints y nombres de campo que usa
`custom_components/mimedidor/api.py` se extrajeron del bundle de producción
del sitio (`main-es2015.*.js`) y se confirmaron en vivo contra una cuenta
real:

| Paso | Endpoint | Qué devuelve |
|---|---|---|
| Login | `GET Usuarios?usuario=...&password=...&versionApp=2` | `token` de acceso |
| Suministro | `GET Suministros?token=...` | Número de serie del medidor, titular, dirección, estado, consumo/demanda en tiempo real, `UltimoAcumulado.ActivaT0` (lectura de por vida) |
| Facturación | `GET Facturacion?token=...&periodos=1` | `Periodos[-1].TotalActivaImportada` (Wh) del período de facturación actual |
| Terminal | `GET Terminales/{numeroSerie[4:12]}?token=...` | Tensión/corriente por fase, factor de potencia, frecuencia, estado del relé y del terminal |

`TotalActivaImportada` es la diferencia entre la última y la primera lectura
del período (`UltimaLectura.ActivaT0 - PrimeraLectura.ActivaT0`), no un
acumulado de por vida: se reinicia con cada período de facturación. Por eso
el sensor usa `state_class: measurement` en vez de `total_increasing`.

Si un endpoint responde con una forma distinta a la esperada (por ejemplo,
si DISCAR cambia el nombre de un campo), el cliente lanza un error
descriptivo en el log de Home Assistant en vez de fallar en silencio —
revisar `custom_components/mimedidor/api.py` si eso pasa.

### Estructura del proyecto

```
custom_components/mimedidor/
├── __init__.py       # setup/unload de la integración
├── api.py            # cliente HTTP contra api.mrdims.com
├── config_flow.py     # formulario de usuario/contraseña
├── const.py           # DOMAIN, plataformas, intervalo de refresco
├── coordinator.py      # DataUpdateCoordinator (polling + manejo de errores)
├── sensor.py           # entidad sensor.mi_medidor_consumo
└── manifest.json       # metadata de la integración para HA/HACS
```

</details>
