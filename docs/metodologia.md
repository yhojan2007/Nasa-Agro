# Metodología

## Clima

NASA POWER, comunidad agroclimatológica (`AG`), sin API key.

- `climatology/point` alimenta el ranking: `T2M`, `T2M_MAX`, `T2M_MIN`, `PRECTOTCORR`, `RH2M`, `GWETROOT`.
- `daily/point` alimenta las alertas, unos 20 años hasta siete días antes de hoy. POWER publica con retraso.
- La malla meteorológica es 0.5° × 0.625°. La caché redondea la latitud a 0.5° y la longitud a 0.625° antes de llamar, así dos clics cercanos comparten respuesta.
- El valor `ANN` no se usa. En mínima y máxima, POWER lo publica como un extremo de los meses, no como el promedio del año.
- `PRECTOTCORR` de estas respuestas viene en mm/día (está en el encabezado). El mes climatológico es ese valor por los días del mes. Febrero usa 28 días, un sesgo de cerca del 3 % solo en ese mes. Si el encabezado dijera mm/mes, no se multiplicaría.
- `-999` es dato faltante y se elimina. Una ventana no trata un hueco como cero.

La altitud que devuelve POWER es la de la celda, no la del predio. En Cochabamba la celda de referencia queda cerca de 3100 m, más alta que el fondo del valle.

## Cultivos

Diez fichas en `backend/data/crops.json`, generadas por `backend/scripts/extract_crops.py` desde la copia OpenCLIM de FAO EcoCrop (rama master descargada el 2026-11-13; CGIAR cita el commit `ea43ecd` como instantánea de referencia).

Se copiaron, sin reescribir el número:

- temperatura: `TMIN`, `TOPMN`, `TOPMX`, `TMAX`
- lluvia: `RMIN`, `ROPMN`, `ROPMX`, `RMAX`
- pH: `PHMIN`, `PHOPMN`, `PHOPMX`, `PHMAX`
- duración: `GMIN`, `GMAX`
- temperatura letal: `KTMP`, cuando existe

La lluvia de la ficha se compara con la suma de la ventana de ciclo. Es la convención del modelo de aptitud EcoCrop. La ficha no rotula ese milimetraje con una sola palabra (año o ciclo); la nota de cada cultivo lo dice.

Traducciones fijas, no mediciones nuevas: `heavy/medium/light/organic` a textura, `well/poorly/excessive` a drenaje, `high/moderate/low` de `FER` a fertilidad general, `shallow/medium/deep` de `DEP` a profundidad de raíz. `fija_nitrogeno` es true solo si la familia EcoCrop es Leguminosae. `sensible_helada` es true solo si `KTMP` es mayor o igual que 0.

`tolerancia_sequia` queda en null. EcoCrop no trae esa columna y no se inventó. Por eso el ajuste de sequía no mueve el ranking de estos diez cultivos.

`GWETROOT` no entra al puntaje: no hay un rango de humedad de suelo por cultivo en la ficha. Sí refuerza el texto de la alerta (bajo 0.3 o sobre 0.8).

## Puntaje

La ventana mide el punto medio de `GMIN` y `GMAX`, pasado a meses de 30 días, entre 1 y 12, e incluye el mes de siembra. Si el usuario no elige mes, se prueban los doce y se queda el mejor.

Cada factor usa el trapecio de EcoCrop: 0 fuera de los absolutos, 1 en el óptimo, lineal en medio. Si un tramo tiene longitud 0, ese tramo vale 0 en lugar de dividir.

Factores y pesos (reglas del proyecto, no de EcoCrop):

- temperatura 1, crítico
- precipitación 1, crítico
- helada 1 si el cultivo es sensible, 0.4 si no; solo entra cuando hay `KTMP`. Es crítica solo en el caso sensible. Vale 0 en la temperatura letal y 1 cuando la mínima de la ventana la supera por 5 °C
- pH 0.6, crítico, solo si el usuario lo ingresó
- textura 0.4 y drenaje 0.4, no críticos. Fuera de la lista de la ficha valen 0.35

La nota final es la media geométrica ponderada, de 0 a 100. Un factor crítico en 0 anula el puntaje. Un factor no crítico en 0 no entra al producto. El factor limitante es el valor más bajo.

Etiquetas: 75–100 Muy viable, 50–74 Viable con cuidados, 25–49 Poco viable, 0–24 No recomendado.

Nitrógeno, fósforo, potasio y materia orgánica no cambian el número. Generan una observación. NPK no tiene curva en EcoCrop.

## Alertas

Se compara la lluvia de los últimos 30 y 60 días con la misma fecha de años anteriores. Hacen falta al menos 10 años. El percentil 0 es más seco que todo el histórico.

- bajo 10: sequía severa, en el sentido de «entre el 10 % más secas»
- de 10 a menos de 25: déficit
- de 25 a 75, inclusive: normal
- por encima de 75 y hasta 90: exceso
- por encima de 90: exceso extremo

El texto describe el periodo ya ocurrido. No dice que va a haber sequía.

La helada de la alerta es del lugar: días con mínima bajo 2 °C en los últimos 30 días. El `KTMP` del cultivo se queda en el puntaje y no se mezcla con esta alerta.

Si hay alerta de déficit o sequía severa en 30 días, y la ficha tuviera `tolerancia_sequia`, se suman 8 puntos a la tolerancia alta o se restan 12 a la baja, con tope 0–100. Un puntaje 0 por factor crítico no se rescata. El exceso resta 8 solo si la lluvia de la ventana supera el máximo absoluto del cultivo. La respuesta marca `ajuste_alerta`.

## Rotación

Hasta tres pasos. Entra un cultivo con puntaje de al menos 50 en el mes que le toca. No se repite la familia de un eslabón al siguiente. Después de fertilidad alta se prefieren las leguminosas (+20 en la selección, sin tocar el puntaje mostrado). Si uno es de raíz superficial y el otro profunda, se prefieren (+10). La mayoría de estas fichas EcoCrop dice raíz media, así que esa preferencia casi no actúa. Materia orgánica bajo 2 % agrega la nota de abono verde o descanso. El aviso dice que no sustituye un plan de manejo.

## Fuera de este prototipo

NDVI de MODIS, humedad SMAP y precipitación GPM IMERG no están integrados. MODIS pide cuenta Earthdata. No se incrustó una serie inventada. SoilGrids tampoco: el suelo es solo lo que escribe el usuario.

No se usa pandas. Los percentiles caben en la biblioteca estándar y el paquete sigue liviano si más adelante se publica en Lambda.
