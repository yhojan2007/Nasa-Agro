# AgroNASA — Reglas del proyecto

## Qué es
Aplicación web para la hackathon de la NASA. El usuario elige un punto en un mapa; el backend consulta
NASA POWER y devuelve recomendaciones de cultivos, alertas climáticas y, opcionalmente, rotación según suelo.
La especificación completa está en `docs/proyecto_agro_nasa.md`. Léela antes de planificar cualquier cambio.

## Stack
- Backend: Python 3.12, FastAPI, httpx, pandas, Pydantic v2, pytest, ruff.
- Frontend: React + Vite, react-leaflet, Recharts.
- Datos de cultivos: `backend/data/crops.json` (sin base de datos relacional en el MVP).
- Despliegue: AWS (frontend en S3 + CloudFront; backend en Lambda con Mangum o contenedor Docker en EC2).

## Comandos
- Backend: `cd backend && pip install -r requirements.txt && pytest && ruff check .`
- Ejecutar API: `cd backend && uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm install && npm run dev`
- Docker: `docker compose up --build`

## Convenciones
- Código, nombres de funciones y variables en inglés. Textos de interfaz y claves del dominio/API en español,
  como en la especificación.
- Toda función con lógica (scoring, alertas, rotación) debe tener pruebas unitarias.
- La lógica de negocio vive en el backend. El frontend solo muestra resultados.
- Type hints obligatorios en Python. Modelos Pydantic para entradas y salidas de la API.

## Reglas de datos (críticas)
- NUNCA inventes valores agronómicos. Cada cultivo en `crops.json` lleva `fuente` y `validado` (true/false).
  Si no conoces la fuente, `validado: false` y márcalo como valor de ejemplo.
- Los valores `-999` de NASA POWER son datos faltantes: filtrarlos siempre.
- Verifica unidades en los metadatos de la respuesta de POWER antes de convertir nada.
- La precipitación de POWER viene en mm/día: multiplicar por los días del mes para acumulados.
- Las alertas son anomalías frente al histórico, NO pronósticos. Nunca redactar "va a haber sequía".
- Toda recomendación incluye explicación y el aviso: "Recomendación orientativa; consulta a un técnico local."

## Seguridad y flujo
- Nunca incluyas secretos ni credenciales en el código. Usa variables de entorno y `.env.example`.
- NASA POWER no requiere API key.
- No ejecutes comandos que creen recursos en AWS ni uses credenciales; genera instrucciones o scripts para que yo los ejecute.
- Antes de cambios grandes, propón un plan y espera confirmación.
- Commits pequeños y descriptivos (Conventional Commits).
- Si una instrucción es ambigua, pregunta antes de suponer.