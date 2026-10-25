# Arquitectura del backend

## 1. Principios
- Backend primero, contratos antes que pantallas.
- Reglas de negocio independientes de FastAPI; los modelos ORM se aíslan
  dentro de cada módulo.
- Una sola fuente de verdad: PostgreSQL.
- Redis no almacena verdad de negocio.
- Seguridad y auditoría desde el diseño.
- Módulos por capacidad de negocio, no por tipo técnico.

## 2. Capas
HTTP (api/) -> servicio (modules/*/service.py) -> repositorio
(modules/*/repository.py) -> modelos (modules/*/models.py) -> PostgreSQL.

- `api/`: valida transporte, aplica dependencias, traduce errores.
- `service/`: reglas, transacciones, permisos y auditoría.
- `repository/`: consultas y persistencia; no decide reglas.
- `models/`: mapeo ORM; sin lógica HTTP.
- `schemas/`: contratos Pydantic; no se exponen modelos ORM.

## 3. Dependencias permitidas
- `api` puede importar `core`, `db` y `modules`.
- `modules` puede importar `core` y `db`, nunca `api`.
- `db` puede importar `core`, nunca `modules`.
- `core` no importa `api`, `db` ni `modules`.
- `tasks` puede importar `core`, `db` y servicios de módulos.
- Evitar dependencias circulares entre módulos.

## 4. Flujo de una petición
1. Middleware asigna `request_id` y valida host.
2. CORS responde preflight.
3. Router resuelve endpoint y dependencias.
4. Se valida entrada con Pydantic.
5. Servicio verifica permisos y reglas.
6. Repositorio consulta o persiste.
7. Servicio confirma la transacción.
8. Se devuelve el esquema de respuesta.
9. Un error se traduce al sobre uniforme con `request_id`.

## 5. Transacciones
- Una sesión por petición.
- El servicio define la unidad de trabajo.
- `commit` único al finalizar; `rollback` ante error.
- Operaciones que afectan caja, ubicación, préstamo, importación o
  auditoría son atómicas.
- No se comparte sesión entre peticiones ni tareas.

## 6. Módulos previstos
auth, users, courts, locations, boxes, case_files,
administrative_documents, search, files, imports, ocr, loans, movements,
qr, inventory, audit, reports.

Cada módulo se crea en su fase, con modelos, migración, permisos y
pruebas. No se crean carpetas vacías.

## 7. Tareas asíncronas
ARQ + Redis para OCR, importaciones y exportaciones. Las tareas son
idempotentes, observables y con timeout. El estado durable vive en
PostgreSQL.

## 8. Almacenamiento
Interfaz `StorageBackend`; implementación local privada en B0/B9 y
posible S3/MinIO futuro. El nombre original no se usa como ruta. Hash
SHA-256 y escritura atómica.

## 9. Observabilidad
Logs JSON con `request_id`, nivel, evento y duración. Redacción de
secretos. Errores uniformes sin trazas en producción. `/live` y `/ready`.

## 10. Decisiones
Ver `docs/decisiones/ADR-0001` a `ADR-0011`.
