# Mi Medidor (DISCAR / Mr.DiMS) — integración para Home Assistant

Integración custom para Home Assistant que se conecta al portal de
autogestión de consumo eléctrico [mimedidor.mrdims.com](https://mimedidor.mrdims.com/)
(sistema **Mr.DiMS** de **DISCAR**, usado por cooperativas y distribuidoras
eléctricas argentinas con medidores inteligentes DiMET) y expone el consumo
del período de facturación actual como un sensor de Home Assistant.

## Estado

✅ Validada end-to-end contra una cuenta real: login, obtención del
suministro y lectura del consumo del período actual funcionan tal cual está
implementado. Falta únicamente instalarla y probarla desde la UI de una
instancia real de Home Assistant.

## Cómo funciona

`mimedidor.mrdims.com` es una SPA de Angular sin API pública/documentada: no
autentica contra un formulario HTML, sino contra una API JSON separada en
`https://api.mrdims.com/V2/api/`. Los endpoints y nombres de campo que usa
`custom_components/mimedidor/api.py` se extrajeron del bundle de producción
del sitio (`main-es2015.*.js`) y se confirmaron en vivo contra una cuenta
real:

| Paso | Endpoint | Qué devuelve |
|---|---|---|
| Login | `GET Usuarios?usuario=...&password=...&versionApp=2` | `token` de acceso |
| Suministro | `GET Suministros?token=...` | Número de serie del medidor, titular, dirección, estado, `ConsumoActual` en tiempo real |
| Consumo | `GET Facturacion?token=...&periodos=1` | `Periodos[-1].TotalActivaImportada` (Wh) del período de facturación actual |

`TotalActivaImportada` es la diferencia entre la última y la primera lectura
del período (`UltimaLectura.ActivaT0 - PrimeraLectura.ActivaT0`), no un
acumulado de por vida: se reinicia con cada período de facturación. Por eso
el sensor usa `state_class: measurement` en vez de `total_increasing`.

Si un endpoint responde con una forma distinta a la esperada (por ejemplo,
si DISCAR cambia el nombre de un campo), el cliente lanza un error
descriptivo en el log de Home Assistant en vez de fallar en silencio —
revisar `custom_components/mimedidor/api.py` si eso pasa.

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

## Instalación manual (alternativa sin HACS)

1. Copiar la carpeta `custom_components/mimedidor` de este repo a la
   carpeta `custom_components` de tu configuración de Home Assistant
   (creála si no existe).
2. Reiniciar Home Assistant.
3. Configuración → Dispositivos y servicios → Añadir integración → "Mi
   Medidor" → ingresar usuario y contraseña.

## Entidad

- **`sensor.mi_medidor_consumo`** — consumo de energía activa (kWh) del
  período de facturación actual
  (`Facturacion.Periodos[-1].TotalActivaImportada / 1000`).
  - `device_class`: `energy`
  - `state_class`: `measurement` (se reinicia con cada período, no es un
    total acumulado de por vida)
  - Atributos extra: `suministro` (respuesta completa de `Suministros`) y
    `periodo_actual` (el período de facturación en curso, tal cual lo
    devuelve la API), útiles para automatizaciones o para armar sensores
    derivados con [templates](https://www.home-assistant.io/docs/configuration/templating/).
- Se actualiza cada 60 minutos (`DEFAULT_SCAN_INTERVAL_MINUTES` en
  `const.py`); se puede editar ese valor si se necesita otra frecuencia.

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

## Estructura del proyecto

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
