"""Pesos, cortes y umbrales del proyecto.

EcoCrop aporta los rangos de cada cultivo. Los números de este módulo no son
datos agronómicos: fijan cómo se combina el puntaje y cómo se nombra una
anomalía, para que el ranking sea el mismo en cada ejecución.
"""

AVISO = "Recomendación orientativa; consulta a un técnico local."
AVISO_ROTACION = "Es una guía general; no sustituye un plan de manejo agronómico."
FUENTE_CLIMA = "NASA POWER (comunidad AG)"

GRID_LAT_DEG = 0.5
GRID_LON_DEG = 0.625

# POWER marca el dato faltante con -999. Cualquier valor <= -998 se descarta.
MISSING_THRESHOLD = -998.0

MONTH_KEYS = (
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
)
# Febrero climatológico se cuenta con 28 días (sesgo de cerca del 3 % en ese mes).
DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
MONTH_NAMES = (
    "",
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

CATEGORIAS = (
    "frutas",
    "hortalizas",
    "cereales",
    "legumbres",
    "tuberculos_raices",
    "oleaginosas",
    "otros",
)

# Pesos de la media geométrica. Un factor crítico en 0 anula el puntaje.
WEIGHT_TEMPERATURE = 1.0
WEIGHT_PRECIP = 1.0
WEIGHT_FROST_SENSITIVE = 1.0
WEIGHT_FROST_TOLERANT = 0.4
WEIGHT_PH = 0.6
WEIGHT_TEXTURE = 0.4
WEIGHT_DRAINAGE = 0.4

# Etiquetas sobre el puntaje ya redondeado, de 0 a 100.
LABEL_VERY = 75
LABEL_VIABLE = 50
LABEL_LOW = 25

# Un cultivo entra a la rotación solo si llega a este puntaje en su mes.
MIN_ROTATION_SCORE = 50
# Preferencia de selección, no un cambio del dato climático.
NITROGEN_BONUS = 20
ROOT_BONUS = 10
# Hasta dos meses de espera si el mes exacto no tiene un cultivo apto.
MAX_FALLOW_MONTHS = 2
MATERIA_ORGANICA_BAJA = 2.0

# Textura o drenaje fuera de la lista de EcoCrop: penalización, no un cero.
MISMATCH_FACTOR = 0.35

# Helada del lugar: mínimas diarias bajo este umbral, distinto del KTMP del cultivo.
FROST_ALERT_C = 2.0
FROST_UNUSUAL_PERCENTILE = 75.0
# La mínima mensual deja de limitar cuando está 5 °C sobre la temperatura letal.
FROST_FULL_MARGIN_C = 5.0

# Percentiles de lluvia acumulada. 75 queda en "normal"; por encima de 90 es extremo.
RAIN_SEVERE_BELOW = 10.0
RAIN_DEFICIT_BELOW = 25.0
RAIN_NORMAL_UNTIL = 75.0
RAIN_EXCESS_UNTIL = 90.0

DROUGHT_BONUS = 8
DROUGHT_PENALTY = 12
EXCESS_PENALTY = 8

SOIL_DRY_BELOW = 0.3
SOIL_SATURATED_ABOVE = 0.8

MIN_HISTORY_YEARS = 10
MIN_WINDOW_COVERAGE = 0.8
HISTORY_YEARS = 20
POWER_LAG_DAYS = 7

# Un cero crítico no se rescata con el ajuste de alerta.
ALERT_DROUGHT = ("sequia_severa", "deficit_lluvia")
ALERT_EXCESS = ("exceso_lluvia", "exceso_extremo")
