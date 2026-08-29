# Mi Medidor (DISCAR / Mr.DiMS) — integración para Home Assistant

Integración custom para Home Assistant que se conecta al portal de
autogestión de consumo eléctrico [mimedidor.mrdims.com](https://mimedidor.mrdims.com/)
(sistema **Mr.DiMS** de **DISCAR**, usado por distribuidoras eléctricas
argentinas con medidores inteligentes DiMET).

## Estado actual

⚠️ **Este es un primer borrador funcional en estructura, pero no validado
contra el sitio real.**

El sitio no tiene API pública/documentada, y el entorno donde se generó esta
integración tiene bloqueado el acceso de red a `mimedidor.mrdims.com`, así
que no fue posible probar el login ni el formato real de los datos de
consumo contra el sitio en vivo.

Lo que sí está resuelto:

- Estructura estándar de integración de Home Assistant (config flow,
  coordinator, sensor) instalable vía HACS (repositorio custom) o
  copiando la carpeta a `custom_components/`.
- **Login**: `custom_components/mimedidor/api.py` busca dinámicamente el
  `<form>` de login (el que tiene un `<input type="password">`) y completa
  usuario/contraseña según el tipo de cada campo, en vez de asumir nombres
  de campos fijos. Esto debería funcionar mientras el login sea un form
  HTML tradicional.
- **Consumo**: intenta parsear JSON directo o un blob de estado embebido en
  el HTML (`__INITIAL_STATE__`, `__NUXT__`, `__NEXT_DATA__`) buscando claves
  como `consumo`, `lectura`, `kwh`, etc.

## Qué falta para que funcione con datos reales

Si al instalarla el login falla o el sensor queda en `unknown`/con error en
el log, lo más probable es que el sitio no encaje con los supuestos de
arriba (por ejemplo, si el login es una llamada a una API en vez de un
`<form>`, o si el consumo se sirve desde un endpoint JSON con otro nombre de
campos).

Para terminar de ajustarlo hace falta una captura real del tráfico:

1. Iniciar sesión en <https://mimedidor.mrdims.com/> desde una compu, con
   las DevTools del navegador abiertas (pestaña **Network**).
2. Navegar hasta la pantalla que muestra el consumo.
3. Clic derecho en la lista de requests → **Save all as HAR**.
4. Compartir ese archivo (se pueden tachar contraseñas/tokens, pero no las
   URLs ni la estructura de las respuestas JSON) para ajustar
   `custom_components/mimedidor/api.py` con los endpoints/campos reales.

## Instalación

1. Copiar la carpeta `custom_components/mimedidor` a la carpeta
   `custom_components` de tu instalación de Home Assistant (o agregar este
   repositorio como repositorio custom en HACS).
2. Reiniciar Home Assistant.
3. Ir a **Configuración → Dispositivos y servicios → Añadir integración**,
   buscar "Mi Medidor" e ingresar usuario y contraseña.

## Entidades

- `sensor.mi_medidor_consumo`: último valor de consumo detectado. La unidad
  y si es un valor acumulado o por período todavía no están confirmados
  contra el sitio real.
