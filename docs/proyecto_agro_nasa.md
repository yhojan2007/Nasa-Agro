# AgroNASA — Especificación completa del proyecto

> Nombre provisional (cámbialo cuando lo decidas). Hackathon de la NASA: aplicación web que traduce datos de observación de la Tierra en recomendaciones de siembra para agricultores.

---

## 1. Resumen ejecutivo

**Problema.** Los pequeños agricultores deciden qué y cuándo sembrar con poca información climática localizada, y el cambio climático vuelve cada vez más inciertas las lluvias, las heladas y las sequías.

**Solución.** Una aplicación web donde el usuario elige un punto en un mapa (o usa su ubicación real). La aplicación consulta los datos climáticos de la NASA para esas coordenadas y devuelve:

1. Un ranking de cultivos recomendados, con puntaje y explicación de por qué.
2. Alertas de sequía, exceso de lluvia y heladas, comparando el clima reciente con el histórico de la zona.
3. Una recomendación mejorada si el usuario ingresa datos de su suelo, con un ciclo de rotación de cultivos para mejorar la tierra.
4. Un explorador de viabilidad por categorías (frutas, verduras, cereales, etc.) para cualquier planta que el usuario quiera evaluar.

**Fuente principal de datos:** NASA POWER (agroclimatología, por coordenadas). Un segundo dataset de la NASA (opcional) refuerza el impacto: NDVI de MODIS, humedad de suelo de SMAP o precipitación de GPM IMERG.

**Despliegue:** AWS (cuenta con plan gratuito).

---

## 2. Alcance y prioridades

| Prioridad | Módulo | Notas |
|---|---|---|
| **P0 (imprescindible)** | Mapa + selección de punto + geolocalización | Sin esto no hay proyecto |
| **P0** | Cliente de NASA POWER (climatología por punto) | Núcleo técnico |
| **P0** | Motor de recomendación de cultivos por reglas | Núcleo de valor |
| **P0** | Explicación de cada recomendación | Lo que más impresiona a un jurado |
| **P1** | Alertas de sequía / exceso de lluvia / helada | Anomalía frente al histórico, no pronóstico |
| **P1** | Explorador por categorías | Es el mismo motor con un filtro, cuesta poco |
| **P1** | Despliegue en AWS | Hazlo con el prototipo ya funcionando |
| **P2** | Módulo de suelo + ciclo de rotación | Aporta mucho, pero requiere datos agronómicos |
| **P2** | Segundo dataset NASA (NDVI / SMAP / GPM) | Diferenciador si sobra tiempo |
| **P3** | Multi-idioma, exportar PDF, cuentas de usuario | Solo si sobra tiempo |

**Fuera de alcance (decirlo explícitamente en el pitch):** pronósticos meteorológicos, asesoría agronómica certificada, datos a escala de parcela.

---

## 3. Limitaciones que hay que reconocer (y decir en el pitch)

- **Resolución espacial.** La meteorología de NASA POWER tiene una malla de unos 0.5° × 0.625° (decenas de km). En zonas de valles y altiplano hay microclimas que esa malla no captura. Presenta el resultado como "tendencia climática de tu zona".
- **No es un pronóstico.** POWER es reanálisis y observación con unos días de retraso. Las "alertas" indican cuánto se desvía el periodo reciente del histórico, no lo que va a pasar.
- **El CSV horario de prueba no sirve para la lógica.** Solo trae radiación, temperatura, punto de rocío y UV. Para este proyecto la app debe consultar la API directamente y pedir precipitación, humedad y humedad de suelo (ver sección 5).
- **Las recomendaciones son orientativas.** Incluir un aviso en la interfaz: consultar a un técnico agrónomo local antes de decidir.

---

## 4. Arquitectura

```
┌──────────────┐    HTTPS     ┌─────────────────────┐    HTTPS    ┌──────────────────┐
│  Frontend    │ ───────────▶ │  Backend (FastAPI)  │ ──────────▶ │  NASA POWER API  │
│ React+Leaflet│ ◀─────────── │  - cliente NASA     │ ◀────────── │  (y otros NASA)  │
└──────────────┘     JSON     │  - motor de reglas  │             └──────────────────┘
                              │  - caché            │
                              └─────────┬───────────┘
                                        │ lee
                                        ▼
                              ┌─────────────────────┐
                              │ Base de cultivos    │
                              │ (JSON/CSV en repo)  │
                              └─────────────────────┘
```

Decisiones de diseño:

- **Sin base de datos relacional** para el MVP. Las reglas de cultivos viven en un archivo JSON o CSV versionado en el repositorio.
- **Caché de respuestas de NASA** por celda de la malla (redondear lat/lon), porque la API es lenta y varios usuarios consultarán zonas cercanas.
- **El backend hace todo el cálculo.** El frontend solo muestra resultados. Así la lógica es testeable y reutilizable.

---

## 5. Datos de la NASA

### 5.1 NASA POWER (fuente principal)

- Comunidad a usar: `AG` (agroclimatología).
- Endpoints relevantes (base: `https://power.larc.nasa.gov/api/temporal/`):
  - `climatology/point`: promedios mensuales de largo plazo. Úsalo para recomendar cultivos.
  - `daily/point`: serie diaria entre dos fechas. Úsalo para las alertas.
  - `monthly/point`: serie mensual por año.
- Parámetros que hay que pedir:

| Parámetro | Significado | Uso |
|---|---|---|
| `T2M` | Temperatura media a 2 m (°C) | Aptitud térmica |
| `T2M_MAX` / `T2M_MIN` | Máxima / mínima diaria (°C) | Estrés por calor, heladas |
| `PRECTOTCORR` | Precipitación corregida (mm/día) | Aptitud hídrica, sequía, exceso |
| `RH2M` | Humedad relativa a 2 m (%) | Riesgo de hongos |
| `GWETROOT` / `GWETTOP` | Humedad de suelo (0–1) en zona de raíces / superficie | Sequía y saturación |
| `ALLSKY_SFC_SW_DWN` | Radiación solar en superficie | Opcional |
| `ALLSKY_SFC_PAR_TOT` | Radiación fotosintéticamente activa | Opcional |
| `WS2M` | Viento a 2 m | Opcional |

- Los valores faltantes vienen como `-999`: filtrarlos siempre.
- Verifica las unidades en los metadatos de cada respuesta antes de convertir nada.

Ejemplo de consulta (Python):

```python
import httpx

POWER_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"

def get_climatology(lat: float, lon: float) -> dict:
    params = {
        "parameters": "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,GWETROOT",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "format": "JSON",
    }
    r = httpx.get(POWER_URL, params=params, timeout=60)
    r.raise_for_status()
    return r.json()["properties"]["parameter"]  # {"T2M": {"JAN": ..., "ANN": ...}, ...}
```

Nota: la precipitación viene en mm/día. Para el acumulado de un mes, multiplica por los días del mes.

### 5.2 Datasets NASA complementarios (P2)

- **MODIS / VIIRS NDVI:** salud histórica de la vegetación en la zona. Requiere cuenta de Earthdata y puede ser lento de integrar. Alternativa realista: precalcular NDVI promedio mensual para unas pocas regiones de demostración.
- **SMAP:** humedad del suelo (resolución aún más gruesa).
- **GPM IMERG:** precipitación satelital, útil para validar sequías y exceso de lluvia.

### 5.3 Datos no-NASA necesarios

- **Requisitos de cultivos:** base abierta de la FAO (EcoCrop) como punto de partida para rangos de temperatura, precipitación, pH y duración del ciclo. Verifica su disponibilidad y licencia, y complétala con fuentes locales para los cultivos de tu región.
- **Suelo (opcional, fallback):** si el usuario no tiene análisis, se puede ofrecer SoilGrids (ISRIC) como estimación por coordenadas. Es global, pero de baja resolución.

---

## 6. Modelo de datos de cultivos

Archivo `data/crops.json`. Cada cultivo:

```json
{
  "id": "maiz",
  "nombre": "Maíz",
  "categoria": "cereales",
  "familia": "gramineas",
  "ciclo_dias": [90, 150],
  "temp": { "abs_min": 10, "opt_min": 20, "opt_max": 30, "abs_max": 38 },
  "temp_min_helada": 2,
  "precip_ciclo_mm": { "abs_min": 400, "opt_min": 500, "opt_max": 800, "abs_max": 1500 },
  "suelo": {
    "ph": { "abs_min": 5.0, "opt_min": 5.8, "opt_max": 7.2, "abs_max": 8.0 },
    "texturas": ["franco", "franco-arcilloso", "franco-arenoso"],
    "drenaje": ["bueno", "moderado"]
  },
  "demanda_nutrientes": { "N": "alta", "P": "media", "K": "media" },
  "fija_nitrogeno": false,
  "tolerancia_sequia": "media",
  "sensible_helada": true,
  "notas": "Valores de ejemplo. Validar con FAO EcoCrop y técnicos locales."
}
```

Categorías propuestas: `frutas`, `hortalizas`, `cereales`, `legumbres`, `tuberculos_raices`, `oleaginosas`, `otros`.

Cultivos iniciales sugeridos para el MVP (8 a 15, con foco local): maíz, papa, quinua, soya, frijol, haba, yuca, arroz, tomate, cebolla, zanahoria, plátano, cítricos, maní, girasol. Mantén la lista chica y bien validada antes que grande y dudosa.

---

## 7. Motor de recomendación

### 7.1 Idea central

Para cada cultivo, se calcula un puntaje de aptitud de 0 a 100 combinando factores. Cada factor se evalúa con una función trapezoidal (el enfoque de EcoCrop): vale 0 fuera de los límites absolutos, 1 dentro del rango óptimo, y baja linealmente entre ambos.

```python
def trapezoid(x, abs_min, opt_min, opt_max, abs_max):
    if x <= abs_min or x >= abs_max:
        return 0.0
    if opt_min <= x <= opt_max:
        return 1.0
    if x < opt_min:
        return (x - abs_min) / (opt_min - abs_min)
    return (abs_max - x) / (abs_max - opt_max)
```

### 7.2 Pasos del cálculo

1. **Ventana de cultivo.** El usuario elige el mes de siembra (o la app evalúa los 12 meses y sugiere el mejor). La ventana cubre desde ese mes hasta cumplir `ciclo_dias`.
2. **Variables climáticas de la ventana**, a partir de la climatología mensual:
   - `T2M` medio de los meses de la ventana → factor térmico.
   - `T2M_MIN` mínimo de la ventana → factor de helada (penalización fuerte si el cultivo es sensible).
   - `PRECTOTCORR` × días del mes, sumado en la ventana → factor hídrico.
   - `GWETROOT` medio → factor de humedad de suelo (opcional).
3. **Factores de suelo** (solo si el usuario los ingresó): pH, textura, drenaje.
4. **Puntaje final.** Media geométrica ponderada de los factores. Si algún factor crítico vale 0, el puntaje es 0.
5. **Factor limitante.** Guardar cuál fue el factor más bajo, para explicar el resultado.
6. **Explicación en lenguaje natural**, por ejemplo: *"Puntaje 82. La temperatura de tu zona (24 °C promedio) es ideal para el maíz. Lo que más lo limita es la lluvia: se esperan unos 430 mm en el ciclo y el cultivo prefiere más de 500."*

### 7.3 Ajustes por riesgo reciente

Si hay alerta activa (sección 8), el ranking se ajusta: ante sequía, subir cultivos con `tolerancia_sequia: alta` y penalizar los de alta demanda de agua. Mostrar siempre que se aplicó este ajuste.

### 7.4 Explorador por categorías

El mismo motor filtrado por `categoria`. Devuelve una tabla con todos los cultivos de la categoría, su puntaje, el factor limitante y una etiqueta: **Muy viable / Viable con cuidados / Poco viable / No recomendado**.

---

## 8. Alertas de sequía, exceso de lluvia y helada

Enfoque: comparar el periodo reciente con la misma época de años anteriores en el mismo punto.

1. Pedir la serie diaria de `PRECTOTCORR` (y `T2M_MIN`, `GWETROOT`) desde unos 15 a 20 años atrás hasta hoy.
2. Para los últimos 30 y 60 días, calcular la precipitación acumulada.
3. Calcular esa misma ventana para cada año histórico y ubicar el valor actual en la distribución (percentil).
4. Clasificar:

| Percentil de lluvia acumulada | Estado |
|---|---|
| < 10 | Sequía severa |
| 10 – 25 | Déficit de lluvia |
| 25 – 75 | Normal |
| 75 – 90 | Exceso de lluvia |
| > 90 | Exceso extremo / riesgo de inundación |

5. Reforzar con `GWETROOT` (suelo muy seco o saturado) y con días de lluvia intensa. Los umbrales exactos son configurables y deben calibrarse por región.
6. **Helada:** si `T2M_MIN` reciente o la climatología del mes de siembra baja del umbral del cultivo sensible, mostrar advertencia.

Redacción de la alerta: *"Las últimas 4 semanas están entre el 10 % más secas de los últimos 20 años en tu zona."* Nunca "va a haber sequía".

---

## 9. Módulo de suelo y rotación (P2)

### 9.1 Entradas (todas opcionales)

- pH
- Textura (arenoso, franco, arcilloso, etc.)
- Materia orgánica (%)
- Nitrógeno, fósforo y potasio (nivel bajo / medio / alto)
- Drenaje (bueno, moderado, pobre)

Si el usuario no tiene estudio de suelo, ofrecer campos simples que pueda estimar a simple vista (textura, drenaje) y dejar claro que la recomendación es menos precisa.

### 9.2 Efecto en la recomendación

Los factores de suelo se agregan al puntaje (sección 7). Además, se generan observaciones: *"pH 4.8: muy ácido; considera encalado antes de sembrar maíz"*.

### 9.3 Ciclo de rotación sugerido

Reglas simples, explicables y fáciles de defender:

- No repetir la misma **familia botánica** en ciclos consecutivos (reduce plagas y enfermedades del suelo).
- Alternar cultivos de **alta demanda de nutrientes** con **leguminosas** que fijan nitrógeno (frijol, haba, soya, maní).
- Alternar **raíz profunda** con **raíz superficial**.
- Si el suelo tiene materia orgánica baja o está degradado, incluir **abono verde** o un periodo de descanso.
- Cada cultivo del ciclo debe tener puntaje climático aceptable para su mes de siembra.

Ejemplo de salida (3 ciclos): maíz (alta demanda) → frijol (fija N) → papa (raíz distinta, rompe ciclo de plagas) → abono verde o descanso.

Incluir aviso: es una guía general, no sustituye a un plan de manejo agronómico.

---

## 10. API del backend (FastAPI)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio |
| GET | `/api/climate?lat=&lon=` | Climatología mensual resumida del punto |
| GET | `/api/alerts?lat=&lon=` | Estado de sequía / exceso / helada |
| POST | `/api/recommend` | Ranking de cultivos para el punto |
| GET | `/api/crops?categoria=` | Catálogo de cultivos |
| POST | `/api/explore` | Viabilidad de una lista o categoría de cultivos |
| POST | `/api/rotation` | Ciclo de rotación sugerido (requiere suelo) |

Ejemplo de `POST /api/recommend`:

```json
{
  "lat": -17.39,
  "lon": -66.28,
  "mes_siembra": 10,
  "categorias": ["cereales", "hortalizas"],
  "suelo": { "ph": 6.2, "textura": "franco", "drenaje": "bueno" }
}
```

Respuesta (resumida):

```json
{
  "punto": { "lat": -17.39, "lon": -66.28, "celda_nasa": [-17.5, -66.25] },
  "alertas": [{ "tipo": "deficit_lluvia", "percentil": 18, "mensaje": "..." }],
  "recomendaciones": [
    {
      "cultivo": "Maíz",
      "puntaje": 82,
      "etiqueta": "Muy viable",
      "factor_limitante": "precipitacion",
      "explicacion": "..."
    }
  ],
  "fuente": "NASA POWER (comunidad AG)",
  "aviso": "Recomendación orientativa; consulta a un técnico local."
}
```

Validaciones: `lat` entre -90 y 90, `lon` entre -180 y 180, `mes_siembra` entre 1 y 12. Manejar con mensajes claros el caso de que la API de NASA no responda (reintentos y mensaje al usuario).

---

## 11. Frontend

### 11.1 Pantallas

1. **Inicio / mapa:** mapa mundial (Leaflet + OpenStreetMap). El usuario hace clic para fijar un punto, busca un lugar o pulsa "Usar mi ubicación". La geolocalización del navegador requiere HTTPS, así que funcionará bien en el despliegue final.
2. **Resultados:**
   - Tarjeta de alertas (colores semáforo).
   - Ranking de cultivos con puntaje, etiqueta y explicación expandible.
   - Gráfico de temperatura y lluvia mensual del punto (Recharts o Chart.js).
3. **Suelo:** formulario simple y opcional; al enviarlo, se recalcula el ranking y aparece la rotación sugerida.
4. **Explorador por categorías:** selector de categoría o de cultivos específicos y tabla comparativa.
5. **Acerca de / metodología:** datos usados, limitaciones y avisos (útil para el jurado).

### 11.2 Criterios de usabilidad

- Pensada para celular primero (el agricultor probablemente la abrirá desde el teléfono).
- Lenguaje simple, sin jerga técnica.
- Mostrar siempre de dónde viene el dato ("Fuente: NASA POWER").
- Estados de carga y de error visibles (la API de NASA puede tardar).

---

## 12. Stack tecnológico

| Capa | Opción recomendada | Alternativa rápida |
|---|---|---|
| Backend | Python 3.12 + FastAPI + httpx + pandas | Flask |
| Frontend | React + Vite + react-leaflet + Recharts | Streamlit + streamlit-folium |
| Datos de cultivos | JSON/CSV en el repositorio | SQLite |
| Caché | Memoria + archivos en `/tmp` | DynamoDB (capa siempre gratuita) |
| Contenedores | Docker (backend) | — |
| Tests | pytest | — |
| CI | GitHub Actions (lint + tests) | — |

Streamlit te permite tener un prototipo visual en pocas horas; React da más control y mejor aspecto para el pitch. Elige según el tiempo disponible.

---

## 13. Despliegue en AWS

**Verifica primero qué tipo de cuenta tienes.** Las cuentas creadas desde el 15 de julio de 2025 usan un plan gratuito basado en créditos (hasta unos 200 USD) con duración máxima de 6 meses, y la cuenta se cierra al agotarse lo uno o lo otro. Las cuentas anteriores siguen el modelo antiguo. Revisa la página de Créditos en la consola de Billing.

Opciones de despliegue:

- **Opción A (liviana):** frontend en S3 + CloudFront (da HTTPS, necesario para geolocalización) y backend en AWS Lambda con Function URL (empaquetando FastAPI con Mangum).
- **Opción B (aprendizaje de Docker):** backend en contenedor Docker sobre una instancia EC2 pequeña, con el frontend estático en S3 + CloudFront.

Guardarraíles obligatorios:

- Crear una **alerta de presupuesto** (AWS Budgets) desde el primer día.
- **No crear NAT Gateway** (cobra por hora y no entra en lo gratuito).
- Evitar servicios administrados innecesarios (RDS, balanceadores) mientras el proyecto no los necesite.
- Configurar **CORS** del backend para el dominio del frontend.
- Terminar o detener los recursos que no uses al acabar la hackathon.

---

## 14. Estructura del repositorio

```
agronasa/
├── README.md
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py            # rutas FastAPI
│   │   ├── nasa_client.py     # cliente NASA POWER + caché
│   │   ├── climate.py         # climatología y ventanas de cultivo
│   │   ├── alerts.py          # percentiles y alertas
│   │   ├── scoring.py         # trapezoides y puntaje
│   │   ├── rotation.py        # reglas de rotación
│   │   └── schemas.py         # modelos Pydantic
│   ├── data/crops.json
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/        # Map, Results, SoilForm, Explorer
│   │   ├── api.js
│   │   └── App.jsx
│   └── package.json
├── docs/                      # metodología, capturas, pitch
└── .github/workflows/ci.yml
```

---

## 15. Plan de trabajo (por fases)

Ajusta los tiempos al plazo real de la hackathon; lo importante es el orden.

- **Fase 0 — Preparación:** definir el reto exacto de la hackathon y sus criterios de evaluación, repartir roles, crear el repositorio y la cuenta de AWS con alerta de presupuesto.
- **Fase 1 — Núcleo de datos:** `nasa_client.py` + endpoint `/api/climate`. Verificar con 2 o 3 puntos conocidos.
- **Fase 2 — Motor de recomendación:** `crops.json` con 8 a 10 cultivos, `scoring.py`, endpoint `/api/recommend`, pruebas unitarias.
- **Fase 3 — Interfaz mínima:** mapa, clic, resultados. Con esto ya hay un demo funcional (**haz aquí tu primer despliegue**).
- **Fase 4 — Alertas** y gráficos de clima.
- **Fase 5 — Explorador por categorías.**
- **Fase 6 — Suelo y rotación.**
- **Fase 7 — Segundo dataset NASA** (si el tiempo lo permite).
- **Fase 8 — Pulido y pitch:** metodología, limitaciones, capturas, video de demo, ensayo del discurso.

---

## 16. Pruebas

- **Unitarias:** función trapezoidal, cálculo de ventana de cultivo, percentiles, reglas de rotación.
- **De integración:** endpoints con respuesta de NASA simulada (mock) y con una respuesta real guardada como fixture.
- **Casos de referencia:** 3 o 4 zonas de clima muy distinto (por ejemplo valle, altiplano, llanos tropicales) donde sepas qué cultivos deberían salir bien posicionados. Si el ranking contradice la realidad local, revisa las reglas.
- **Manuales:** celular real, conexión lenta, API de NASA caída.

---

## 17. Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| La API de NASA es lenta o falla en la demo | Caché + datos de ejemplo precargados para 3 zonas de demostración |
| Reglas agronómicas dudosas | Basarlas en FAO EcoCrop, citar fuentes, marcar valores como orientativos |
| Alcance demasiado grande | Respetar prioridades P0 a P3; cortar suelo y segundo dataset primero |
| Cobros inesperados en AWS | Budgets, sin NAT Gateway, revisar el tipo de cuenta |
| El jurado ve "otro recomendador de cultivos" | Foco local, explicaciones claras, uso de un segundo dataset NASA, métricas de impacto |
| Sobrepromesa ("predice sequías") | Lenguaje honesto: anomalías históricas, no pronósticos |

---

## 18. Guion de pitch (3 minutos)

1. **Problema (30 s):** el agricultor decide a ciegas frente a un clima cada vez más incierto.
2. **Solución (30 s):** haces clic en el mapa y los datos de la NASA te dicen qué sembrar y cuándo tener cuidado.
3. **Demo en vivo (60 s):** elegir un punto → ranking con explicación → alerta → suelo y rotación.
4. **Cómo usamos los datos NASA (30 s):** POWER (clima), y el segundo dataset si se logró. Escala global por coordenadas.
5. **Impacto y honestidad (30 s):** a quién ayuda, limitaciones reconocidas, próximos pasos (pronóstico estacional, validación con agrónomos locales, versión offline/SMS para zonas sin internet).

---

## 19. Próximos pasos tras la hackathon

- Validar reglas y alertas con técnicos agrónomos y agricultores reales.
- Integrar pronóstico estacional.
- Mejorar la resolución con datos de estaciones locales.
- Versión por WhatsApp o SMS para zonas con conectividad limitada.
- Más cultivos y variedades locales.

---

## 20. Pendientes por definir

- [ ] Nombre definitivo del proyecto
- [ ] Reto exacto de la hackathon y criterios de evaluación
- [ ] Fecha límite y tamaño del equipo
- [ ] Frontend: React o Streamlit
- [ ] Región(es) de demostración
- [ ] Lista final de cultivos del MVP y fuente de sus datos
- [ ] Tipo de cuenta AWS y fecha de expiración de créditos