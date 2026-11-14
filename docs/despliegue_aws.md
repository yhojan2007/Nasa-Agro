# Despliegue

Hoy AgroNASA corre en local. Esta nota queda para cuando quieras publicarla en AWS. No crees recursos desde un script automático sin mirar la factura, y no pongas credenciales en el repositorio.

## Antes de crear nada

1. En Billing, revisa si tu cuenta es de créditos (las abiertas desde el 15 de julio de 2025) o del plan gratuito anterior, y anota la fecha en que se acaban.
2. Crea una alerta de presupuesto (AWS Budgets) el primer día, con un tope bajo.
3. No crees un NAT Gateway. Se cobra por hora y no entra en lo gratuito.
4. No crees RDS ni un balanceador mientras el prototipo no los necesite.

## Opción prevista

Frontend estático en S3, servido por CloudFront para tener HTTPS. Sin HTTPS el navegador no comparte la ubicación.

API en Lambda con una Function URL. FastAPI ya expone `handler = Mangum(app)` en `backend/app/main.py`. Empaqueta el contenido de `backend/` (sin `tests/` ni la caché). Sube el timeout de la función a 60 segundos y la memoria a 512 MB: la serie diaria de POWER puede tardar.

En la Function URL, la variable `CORS_ORIGINS` tiene que ser el dominio de CloudFront. `NASA_TIMEOUT_SECONDS` puede quedarse en 60. POWER no usa API key.

La caché en `/tmp` de Lambda se pierde entre instancias. Las tres zonas de `backend/data/demo/` responden igual si POWER falla en la demo.

## Al terminar la hackathon

Borra o detén la distribución de CloudFront, el bucket y la función si ya no los usas. Vuelve a mirar Budgets.
