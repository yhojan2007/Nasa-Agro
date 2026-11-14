# AgroNASA

Aplicación web para una hackathon de la NASA. Eliges un punto en el mapa y el backend consulta [NASA POWER](https://power.larc.nasa.gov/) para decirte qué cultivos encajan con el clima de esa zona, si el periodo reciente fue más seco o más frío que su histórico, y —si ingresas suelo— un ciclo de rotación orientativo.

No es un pronóstico ni un diagnóstico de parcela. La recomendación lleva siempre este aviso: «Recomendación orientativa; consulta a un técnico local.»

## Cómo correrlo

Hacen falta Python 3.12 o superior y Node.js 22.

Terminal 1, API:

```bash
cd backend
pip install -r requirements.txt
pytest
ruff check .
uvicorn app.main:app --reload
```

La API queda en `http://127.0.0.1:8000`. Prueba rápida: `http://127.0.0.1:8000/health`.

Terminal 2, interfaz:

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173`. Vite reenvía `/api` y `/health` al API local.

Con Docker, desde la raíz del repo:

```bash
docker compose up --build
```

La interfaz usa el puerto 5173 y el API el 8000. Copia [`.env.example`](.env.example) a `.env` solo si quieres cambiar el timeout o los orígenes CORS. NASA POWER no usa API key.

## Qué puedes probar

En el mapa hay tres zonas de referencia en Bolivia: Cochabamba, El Alto y Santa Cruz. Un clic consulta la climatología y el ranking. La primera llamada al histórico diario puede tardar cerca de un minuto; la siguiente sale de la caché por celda (0.5° × 0.625°).

Si POWER no responde y el punto cae en una de esas tres celdas, la app usa la consulta guardada en `backend/data/demo/`.

## Datos

- Clima: NASA POWER, comunidad `AG`. La lluvia diaria viene en mm/día; el acumulado mensual multiplica por los días del mes (febrero, 28). Los `-999` se descartan. La unidad se lee del encabezado de cada respuesta.
- Cultivos: 10 fichas copiadas de FAO EcoCrop (copia OpenCLIM) por [`backend/scripts/extract_crops.py`](backend/scripts/extract_crops.py). Cada una trae `fuente` y `validado`. No hay tolerancia a sequía porque EcoCrop no la trae.
- La metodología, los pesos y lo que la app no promete están en [docs/metodologia.md](docs/metodologia.md).

## Variables

| Variable | Ejemplo | Para qué |
|---|---|---|
| `CORS_ORIGINS` | `http://localhost:5173` | Orígenes que pueden llamar al API |
| `CACHE_DIR` | vacío | Carpeta de caché. Vacío usa `backend/data/cache` |
| `NASA_TIMEOUT_SECONDS` | `60` | Espera de cada llamada a POWER |
| `VITE_PROXY_TARGET` | `http://localhost:8000` | Destino del proxy de Vite, útil dentro de Docker |
| `VITE_API_URL` | vacío | Si lo defines, el navegador llama a esa URL en lugar del proxy |

## Despliegue

Esta versión se usa en local. Los pasos de AWS (S3, CloudFront y Lambda), la alerta de presupuesto y la prohibición de crear un NAT Gateway están en [docs/despliegue_aws.md](docs/despliegue_aws.md) para cuando decidas publicarla. No hay credenciales en el repo.

## Pendiente

- [COMPLETAR: autores]
- [COMPLETAR: licencia]
