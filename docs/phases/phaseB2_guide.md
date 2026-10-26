# Fase B2 --- Base de datos, modelos SQLAlchemy y migraciones Alembic

**Versión:** 1.0\
**Estado:** implementación completa y verificada\
**Fecha:** 2026-10-26\
**Ámbito:** backend\
**Entrada:** B1 aceptada (D-01 a D-39)\
**Salida:** esquema PostgreSQL, modelos SQLAlchemy 2.1, Alembic, semillas,
pruebas de integridad y runbook de migración/restauración

---

## 0. Cómo usar este documento

### 0.1 Regla de alcance

Este documento es una guía de implementación. No autoriza por sí mismo a
modificar código, ejecutar migraciones sobre bases compartidas, hacer commit ni
hacer push. La implementación se realiza cuando el usuario lo autorice.

Toda decisión de B2 debe respetar:

1. `docs/AGENTS.md`.
2. `docs/phases/GUIA_DESARROLLO_FASES_SGA.md`, fase B2.
3. `docs/phases/phaseB0_guide.md`.
4. `docs/phases/phaseB1_guide.md`, en especial D-01 a D-39.
5. Los ADR vigentes, principalmente ADR-0002, ADR-0003 y ADR-0006.

Si una instrucción de este documento contradice una regla de negocio de B1,
prevalece B1 y se detiene la implementación hasta resolver la contradicción.

### 0.2 Qué significa "sin omisiones" en B2

Incluye:

- árbol exacto de archivos;
- código completo de modelos, mixins, enums y agregador;
- nombres de tablas, columnas, restricciones e índices;
- migración inicial y tratamiento de secuencia, triggers y datos semilla;
- comandos de PowerShell;
- pruebas de metadatos, restricciones, concurrencia, migraciones y semillas;
- ERD físico;
- actualización, reversión y restauración;
- criterios verificables de terminado.

No incluye implementar servicios, endpoints, autenticación, autorización,
repositorios ni tareas de negocio. Esas capas pertenecen a fases posteriores.

### 0.3 Principio de separación B1/B2

B1 define qué debe cumplirse. B2 define cómo se representa y protege en
PostgreSQL. B2 no reinterpreta las reglas ni inventa datos históricos.

La base de datos debe rechazar combinaciones estructuralmente imposibles. Las
reglas que dependen de permisos, estados transitorios o datos externos se
aplican en servicios de fases posteriores y se prueban entonces.

---

## 1. Objetivo, alcance y entregables

### 1.1 Objetivo

Construir un esquema PostgreSQL consistente, migrable, auditable y preparado
para concurrencia, con modelos SQLAlchemy 2.1 y migraciones Alembic reproducibles.

### 1.2 Incluido

- Infraestructura ORM común: UUID, timestamps, versión optimista, borrado lógico,
  enums persistidos como texto y convenciones de nombres.
- Modelos de las 41 tablas del esquema B2.
- Relaciones mediante claves foráneas explícitas.
- Restricciones `PRIMARY KEY`, `UNIQUE`, `CHECK`, `FOREIGN KEY` e índices.
- Restricciones compuestas para impedir mezcla de tipos en cajas.
- Índices únicos parciales para posiciones y préstamos abiertos.
- Secuencia global de números visibles de caja desde 4402.
- Triggers de inmutabilidad de auditoría, actualización de timestamps e
  inmutabilidad de atributos de caja con contenido.
- Migración inicial reversible.
- Semillas idempotentes de roles, áreas, anaqueles, tribunales, rol de parte,
  política de numeración y configuración esencial.
- Pruebas de integridad, concurrencia, migraciones y semillas.
- ERD físico.
- Runbook de actualización, reversión y restauración.

### 1.3 Fuera de alcance

- Endpoints y contratos HTTP.
- Autenticación real y creación de usuarios.
- Servicios de negocio, repositorios y permisos.
- Carga real de las 4401 cajas.
- Importación de inventarios históricos.
- Migración de datos productivos.
- Almacenamiento físico de archivos.
- OCR, antivirus y procesamiento documental.
- Geometría 2D/3D.
- Reportes y exportaciones.
- Borrado físico automatizado.

### 1.4 Entregables

| Entregable | Ubicación |
|---|---|
| Modelos SQLAlchemy | `backend/src/judicial_archive/modules/*/models.py` |
| Infraestructura ORM | `backend/src/judicial_archive/db/` |
| Agregador de metadatos | `backend/src/judicial_archive/models.py` |
| Migración inicial | `backend/alembic/versions/` |
| Semillas idempotentes | `backend/src/judicial_archive/db/seed.py` |
| Pruebas de esquema | `backend/tests/unit/`, `backend/tests/integration/` |
| ERD y runbook | este documento |

### 1.5 Criterios de aceptación

1. Una base vacía llega al esquema actual ejecutando `alembic upgrade head`.
2. `alembic check` no detecta diferencias entre modelos y base.
3. `alembic downgrade base` funciona sobre una base de pruebas sin datos.
4. Las restricciones rechazan mezcla de tipos, doble ocupación, doble préstamo,
   objetivos múltiples y fechas parciales inconsistentes.
5. La numeración concurrente no produce duplicados.
6. La auditoría no admite `UPDATE`, `DELETE` ni `TRUNCATE` desde la aplicación.
7. Las semillas se ejecutan dos veces sin duplicar registros.
8. Las pruebas unitarias e integración pasan en local y CI.
9. No hay secretos, datos personales ni datos productivos en el repositorio.
10. Toda modificación de esquema se realiza por migración revisada.

---

## 2. Prerrequisitos y estado real de partida

### 2.1 Software

- Windows PowerShell 5.1 para los comandos de esta guía.
- Python 3.12 gestionado por `uv`.
- PostgreSQL 18 local o de pruebas.
- Redis no es necesario para B2, pero la suite completa puede requerirlo.
- `pg_dump`, `pg_restore` y `psql` disponibles para respaldo y verificación.

### 2.2 Estado comprobado del repositorio

| Elemento | Estado |
|---|---|
| `backend/pyproject.toml` | SQLAlchemy 2.1, Alembic 1.20, psycopg 3 |
| `db/base.py` | `Base` con convención de nombres |
| `db/session.py` | `Database` async con `AsyncSession` |
| `db/health.py` | Comprobaciones PostgreSQL/Redis |
| `alembic/env.py` | Engine síncrono con psycopg y `Base.metadata` |
| `alembic/versions/` | Vacío |
| `modules/` | Solo `__init__.py`; sin modelos |
| `models.py` | No existe |
| Tests | Unitarios, API e integración básica existentes |
| Último commit B1 | `78a1701 chore(backend): validaciones en la fase B1` |
| Estado Git | Limpio al iniciar B2 |

### 2.3 Comprobación inicial

```powershell
git status --short
git log --oneline -5
cd backend
uv sync
uv run python -c "import sqlalchemy, alembic, psycopg; print(sqlalchemy.__version__, alembic.__version__)"
```

Resultado esperado:

- sin cambios ajenos;
- dependencias sincronizadas;
- SQLAlchemy 2.1.x;
- Alembic 1.20.x;
- psycopg 3.3.x.

No continuar si el repositorio contiene cambios sin revisar.

### 2.4 Base de desarrollo

La base debe existir antes de ejecutar Alembic. Usar una base dedicada:

```powershell
$env:SGA_DATABASE_URL = "postgresql+psycopg://sga_dev:CAMBIAR@localhost:5432/sga_dev"
uv run alembic current
```

La URL real no se escribe en `alembic.ini`, scripts ni documentación.

### 2.5 Base de pruebas

Las pruebas de integración usan una base desechable, nunca la de desarrollo o
producción:

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://sga_test:CAMBIAR@localhost:5432/sga_test"
$env:RUN_INTEGRATION = "1"
```

La base de pruebas puede ser destruida por las pruebas de migración.

---

## 3. Decisiones de implementación B2

Estas decisiones no sustituyen D-01 a D-39. Son decisiones técnicas de B2 y
quedan registradas aquí para que el esquema sea reproducible.

| ID | Tema | Decisión |
|---|---|---|
| DB-01 | Identificador interno | UUID v4 generado por la aplicación y `gen_random_uuid()` como respaldo del servidor. No se usan códigos visibles como PK. |
| DB-02 | Nombres de tablas | Plural, `snake_case`, en inglés consistente. Clases ORM en singular. |
| DB-03 | Enumeraciones | `StrEnum` en Python y `VARCHAR` + `CHECK` en PostgreSQL. No se usan tipos `ENUM` nativos en B2 para permitir migraciones aditivas y reversibles. |
| DB-04 | Fechas y horas | `TIMESTAMPTZ` en PostgreSQL y UTC en API/app. La zona `America/Santo_Domingo` se aplica a reglas de negocio, no al almacenamiento. |
| DB-05 | Registro de modelos | Cada módulo define sus modelos; `judicial_archive/models.py` los importa para registrar todos los mapeos antes de Alembic. |
| DB-06 | Borrado | Se usan estados archivísticos y campos de baja lógica. No se usa un único `is_deleted`. No hay borrado físico normal. |
| DB-07 | Tipo de caja | Columna técnica `box_type` en el contenido y FK compuesta `(box_id, box_type)` a `boxes(id, box_type)`. |
| DB-08 | Numeración de cajas | Secuencia PostgreSQL `box_visible_number_seq` desde 4402. La política guarda formato y alcance, no un contador duplicado. |
| DB-09 | Concurrencia de ubicación | Índice único parcial sobre `boxes.current_position_id` cuando la custodia es `IN_PLACE` o `IN_RECONCILIATION`. |
| DB-10 | Préstamo abierto | `loan_items.released_at` marca el fin de la reserva o préstamo. Índices únicos parciales por caja y por expediente. |
| DB-11 | Objetivos legales | `legal_holds` y `deletion_requests` usan columnas FK explícitas y checks de objetivo único. No hay `entity_type/entity_id` genérico. |
| DB-12 | Fechas parciales | Componentes año/mes/día más precisión explícita. No se usan fechas centinela. |
| DB-13 | Auditoría | Append-only mediante trigger. No tiene FK al registro auditado para sobrevivir a bajas lógicas. |
| DB-14 | Semillas | Script Python idempotente con bloqueo asesor transaccional. No crea usuarios ni contraseñas. |
| DB-15 | Migraciones | Autogeneración revisada; secuencia, triggers e índices parciales se añaden manualmente a la migración. |
| DB-16 | Índices | Solo los justificados por reglas B1 o claves de integridad. Los índices de rendimiento se validan con consultas reales en B8. |
| DB-17 | Borrado en cascada | `RESTRICT` por defecto. `CASCADE` solo en tablas de asociación sin historia propia. |
| DB-18 | Versión optimista | Columna `version` en entidades mutables principales y `version_id_col` de SQLAlchemy. |
| DB-19 | Nombres de restricciones | Todo `CHECK` y toda restricción compuesta tienen nombre explícito y estable. |
| DB-20 | Relaciones ORM | Las FK son obligatorias. Las relaciones ORM se añaden de forma explícita y con `lazy="raise"` cuando se implementen servicios. |
| DB-21 | Semántica temporal | `created_at` y `updated_at` con trigger de actualización en tablas mutables. |
| DB-22 | Datos inciertos | Capacidades, geometría, plazos legales y configuraciones no confirmadas se dejan nulas o inactivas; no se inventan. |
| DB-23 | Nombres de CHECK | La convención de `Base` para `ck` se vuelve pass-through (`%(constraint_name)s`) porque todos los checks llevan el nombre completo explícito. Evita `ck_boxes_ck_boxes_box_type`. |

---

## 4. Arquitectura de persistencia

### 4.1 Capas

```text
api/ -> modules/*/service -> modules/*/repository -> modules/*/models -> PostgreSQL
```

Reglas:

- `db/` contiene infraestructura genérica y no importa `modules`.
- `modules/*/models.py` contiene mapeo ORM, constraints e índices.
- `judicial_archive/models.py` importa todos los modelos para registrar metadatos.
- Alembic importa el agregador, nunca una lista incompleta.
- Los modelos no importan FastAPI, Pydantic, repositorios ni servicios.
- Las relaciones entre módulos usan FK y nombres de tabla, no imports cruzados
  innecesarios.

### 4.2 Por qué un agregador superior

`db/base.py` no debe importar `modules` según ADR-0002. Por eso el registro
completo se hace en `judicial_archive/models.py`, un módulo superior que no
pertenece a `db` ni a `api`. `alembic/env.py` importa ese agregador antes de leer
`Base.metadata`.

### 4.3 Transacciones

- Una sesión por petición o tarea.
- El servicio define la unidad de trabajo.
- Un `commit` al final; `rollback` ante error.
- No se comparte una sesión entre tareas concurrentes.
- Las pruebas de concurrencia usan sesiones y conexiones independientes.

### 4.4 Modelo de integridad

| Nivel | Responsabilidad |
|---|---|
| PostgreSQL | PK, FK, unique, check, triggers, secuencia, índices |
| Modelo ORM | Mismo contrato declarado y utilidades de mapeo |
| Servicio | Permisos, transiciones, reglas temporales y combinaciones complejas |
| Pruebas | Verifican ambos niveles; no usan mocks para reglas de persistencia |

---

## 5. Árbol de archivos

### 5.1 Crear

```text
backend/
├── src/judicial_archive/
│   ├── models.py
│   ├── core/
│   │   └── enums.py
│   ├── db/
│   │   ├── mixins.py
│   │   └── seed.py
│   └── modules/
│       ├── users/models.py
│       ├── auth/models.py
│       ├── audit/models.py
│       ├── courts/models.py
│       ├── locations/models.py
│       ├── boxes/models.py
│       ├── qr/models.py
│       ├── case_files/models.py
│       ├── administrative_documents/models.py
│       ├── files/models.py
│       ├── imports/models.py
│       ├── ocr/models.py
│       ├── jobs/models.py
│       ├── loans/models.py
│       ├── inventory/models.py
│       └── retention/models.py
├── alembic/versions/
│   └── 20261026_0001_initial_schema.py
└── tests/
    ├── unit/test_schema_metadata.py
    └── integration/
        ├── conftest.py
        ├── test_schema_constraints.py
        ├── test_schema_concurrency.py
        ├── test_audit_immutability.py
        ├── test_seed_idempotency.py
        └── test_migrations.py
```

### 5.2 Modificar

| Archivo | Cambio |
|---|---|
| `backend/alembic/env.py` | Importar agregador y respetar URL inyectada |
| `backend/src/judicial_archive/db/base.py` | Convención `ck` pass-through para nombres explícitos completos |
| `backend/tests/conftest.py` | Sin cambios obligatorios; añadir fixtures en integración |
| `backend/pyproject.toml` | Sin dependencias nuevas; opcionalmente elevar cobertura al cierre |
| `backend/README.md` | Añadir comandos de migración y semillas |
| `docs/arquitectura.md` | Registrar el agregador y los módulos nuevos si se aprueba |
| `docs/pendientes-de-validacion.md` | Solo si aparece una incertidumbre nueva |

### 5.3 No crear

- `backend/src/judicial_archive/models/` como paquete alternativo.
- Migraciones manuales fuera de Alembic.
- Tablas de conveniencia sin entidad de dominio.
- Datos de prueba dentro de migraciones de esquema.
- Usuarios, contraseñas o tokens semilla.
- Archivos `.env` con secretos.

### 5.4 Scaffold existente y reconciliación

En el workspace hay archivos B2 **sin versionar**. No se deben sobrescribir a
ciegas ni asumir que B2 no está iniciado. Antes de implementar:

```powershell
git status --short
git diff --no-index -- /dev/null backend/src/judicial_archive/db/mixins.py
```

Estado observado al redactar esta guía:

| Archivo | Estado | Acción |
|---|---|---|
| `backend/src/judicial_archive/db/mixins.py` | No versionado, con contenido parcial | Revisar diferencias antes de reemplazar |
| `backend/src/judicial_archive/modules/users/models.py` | No versionado, no vacío | Revisar y conservar cambios válidos |
| Demás `modules/*/models.py` | No versionados, vacíos | Crear según esta guía |
| `backend/src/judicial_archive/db/seed.py` | No versionado, vacío | Crear según esta guía |
| `backend/src/judicial_archive/models.py` | No versionado, vacío | Crear agregador |
| `backend/alembic/versions/20261025_0001_initial_schema.py` | No versionado, vacío | Reemplazar por `20261026_0001_initial_schema.py` |
| `backend/tests/unit/test_schema_metadata.py` y pruebas de integración B2 | No versionados, vacíos | Crear según esta guía |
| `backend/tests/integration/conftest.py` | No existe | Crear |

Defectos conocidos del scaffold que esta guía corrige:

- `db/mixins.py` usa `__mapped_args__`; el gancho correcto es
  `__mapper_args__`.
- `partial_date_checks` exige `day` cuando la precisión es `MONTH`; debe ser
  `day IS NULL` para `MONTH`.
- `db/base.py` conserva la convención `ck_%(table_name)s_%(constraint_name)s`;
  debe ser `%(constraint_name)s` y los checks deben llevar nombre completo.
- El scaffold usa el alias `PostgreSQLUUID`; esta guía usa
  `postgresql.UUID` para cumplir N811.

Si el usuario prefiere conservar el scaffold, aplicar solo las correcciones y
los archivos faltantes, sin descartar trabajo previo.

---

## 6. Convenciones obligatorias

### 6.1 Nombres

| Elemento | Convención | Ejemplo |
|---|---|---|
| Tabla | plural `snake_case` | `case_files` |
| Clase | singular `PascalCase` | `CaseFile` |
| Columna | `snake_case` | `nuc_normalized` |
| FK | `<entidad>_id` | `court_id` |
| Constraint | prefijo estable | `ck_boxes_box_type` |
| Índice | `ix_`, `uq_` o `ux_` | `ix_case_files_court_nuc` |
| Enum Python | `PascalCase` con `StrEnum` | `BoxType` |
| Valor persistido | MAYÚSCULAS con guion bajo | `IN_PLACE` |

### 6.2 Reglas de columnas

- PK: `id UUID NOT NULL`.
- Timestamps: `created_at`, `updated_at` con zona horaria.
- Versión: `version INTEGER NOT NULL DEFAULT 1`.
- Booleanos: `NOT NULL` con default explícito.
- Texto: `VARCHAR(n)` para límites de dominio; `TEXT` solo para contenido libre.
- JSON: `JSONB` con check de tipo cuando corresponda.
- Dinero: no aplica en B2.
- Números visibles e identificadores: siempre texto.
- Nulos: se usan para información realmente desconocida, no para evitar validar.

### 6.3 Enums persistentes

Cada enum tiene:

1. `StrEnum` en `core/enums.py`.
2. Columna `VARCHAR` con longitud suficiente.
3. `CHECK` con nombre explícito.
4. `server_default` cuando exista un valor inicial seguro.
5. Prueba de valor inválido.

No se usa `sqlalchemy.Enum` nativo en B2. Cambiar valores requiere migración
nueva que reemplace el `CHECK`, nunca una edición silenciosa.

### 6.4 Foreign keys

- `ON DELETE RESTRICT` por defecto.
- `ON UPDATE RESTRICT`.
- `CASCADE` solo en:
  - `user_roles`;
  - `role_permissions`;
  - `case_parties` si se elimina una relación no histórica;
  - filas hijas de importación cuando se elimine un lote nunca aplicado.
- Aun en esos casos, el servicio debe impedir borrados prohibidos.
- Las columnas de actor pueden ser nulas para procesos del sistema.
- Las FK a usuarios usan `RESTRICT` y los usuarios se desactivan, no se borran.

### 6.5 Check constraints

- Todo check tiene nombre.
- Se prefieren checks de columna y de tabla simples.
- No se usan funciones no inmutables.
- No se usan subconsultas en `CHECK`.
- Las reglas entre tablas se implementan con FK, triggers controlados o servicio.
- Los checks no reemplazan la validación de permisos.

### 6.6 Índices

- PK y unique crean índices automáticamente.
- Índices parciales para estados activos.
- Índices compuestos en el orden de las consultas reales.
- No se crean índices de texto completo ni trigramas hasta B8.
- Los índices de expresión se revisan manualmente en Alembic.
- Toda migración de índice se prueba con `EXPLAIN` cuando exista consulta real.

### 6.7 Fechas parciales

Una fecha puede tener precisión:

- `UNKNOWN`;
- `YEAR`;
- `MONTH`;
- `DAY`.

Invariantes:

| Precisión | Año | Mes | Día |
|---|---|---|---|
| `UNKNOWN` | nulo | nulo | nulo |
| `YEAR` | presente | nulo | nulo |
| `MONTH` | presente | presente | nulo |
| `DAY` | presente | presente | presente |

Nunca se rellena `01/01` para representar un año desconocido.

### 6.8 Texto y normalización

- `*_raw` conserva el valor recibido sin espacios exteriores.
- `*_normalized` se usa solo para comparación.
- La normalización de NUC conserva ceros y guiones.
- Los códigos de tribunal usan mayúsculas y guion ASCII en su versión normalizada.
- Los nombres normalizados se generan en servicio; B2 reserva la columna.
- No se aplica una regex global de NUC ni de sentencia.

---

## 7. Enumeraciones compartidas

### Archivo: `backend/src/judicial_archive/core/enums.py`

```python
from __future__ import annotations

from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    LOCKED = "LOCKED"


class CatalogStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CourtStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class VerificationStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CONFLICT = "CONFLICT"


class IdentifierKind(StrEnum):
    NUC = "NUC"
    PROCESS_NUMBER = "PROCESS_NUMBER"
    SENTENCE = "SENTENCE"


class NumberingScope(StrEnum):
    GLOBAL = "GLOBAL"
    COURT = "COURT"
    BOX_TYPE = "BOX_TYPE"
    YEAR = "YEAR"


class ResetPolicy(StrEnum):
    NEVER = "NEVER"
    YEARLY = "YEARLY"
    PER_SCOPE = "PER_SCOPE"


class RetentionEntityType(StrEnum):
    BOX = "BOX"
    CASE_FILE = "CASE_FILE"
    ADMINISTRATIVE_DOCUMENT = "ADMINISTRATIVE_DOCUMENT"
    FILE_ASSET = "FILE_ASSET"


class RetentionDisposition(StrEnum):
    REVIEW = "REVIEW"
    TRANSFER = "TRANSFER"
    DESTROY = "DESTROY"
    PERMANENT = "PERMANENT"


class SettingValueType(StrEnum):
    STRING = "STRING"
    INTEGER = "INTEGER"
    BOOLEAN = "BOOLEAN"
    JSON = "JSON"


class BoxType(StrEnum):
    EXPEDIENTES = "EXPEDIENTES"
    DOCUMENTOS_ADMINISTRATIVOS = "DOCUMENTOS_ADMINISTRATIVOS"


class BoxLifecycleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    VOIDED = "VOIDED"
    DESTROYED = "DESTROYED"


class CustodyStatus(StrEnum):
    IN_PLACE = "IN_PLACE"
    ON_LOAN = "ON_LOAN"
    IN_TRANSIT = "IN_TRANSIT"
    MISSING = "MISSING"
    IN_RECONCILIATION = "IN_RECONCILIATION"
    UNKNOWN = "UNKNOWN"


class LocationPrecision(StrEnum):
    CONFIRMED = "CONFIRMED"
    PENDING = "PENDING"
    UNKNOWN = "UNKNOWN"


class Confidentiality(StrEnum):
    INTERNAL = "INTERNAL"
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"


class AreaStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ShelfStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class TrayStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class PositionStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    BLOCKED = "BLOCKED"
    RETIRED = "RETIRED"


class LifecycleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    VOIDED = "VOIDED"
    DESTROYED = "DESTROYED"


class MovementType(StrEnum):
    ASSIGN = "ASSIGN"
    TRANSFER = "TRANSFER"
    RETURN = "RETURN"
    LOAN_PICKUP = "LOAN_PICKUP"
    LOAN_RETURN = "LOAN_RETURN"
    RECONCILIATION = "RECONCILIATION"


class MovementStatus(StrEnum):
    PLANNED = "PLANNED"
    IN_TRANSIT = "IN_TRANSIT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class LoanStatus(StrEnum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    DELIVERED = "DELIVERED"
    RETURNED = "RETURNED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class FileStatus(StrEnum):
    PENDING = "PENDING"
    QUARANTINED = "QUARANTINED"
    STORED = "STORED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    MISSING = "MISSING"
    CORRUPTED = "CORRUPTED"
    DELETED = "DELETED"


class FileLinkKind(StrEnum):
    PRIMARY = "PRIMARY"
    ANNEX = "ANNEX"
    SOURCE = "SOURCE"
    EVIDENCE = "EVIDENCE"


class ImportKind(StrEnum):
    INVENTORY_TABLE = "INVENTORY_TABLE"
    DOCUMENT_DIGITIZATION = "DOCUMENT_DIGITIZATION"


class ImportStatus(StrEnum):
    DRAFT = "DRAFT"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    READY = "READY"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ImportFileStatus(StrEnum):
    PENDING = "PENDING"
    EXTRACTING = "EXTRACTING"
    EXTRACTED = "EXTRACTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ImportRowStatus(StrEnum):
    PENDING = "PENDING"
    PARSED = "PARSED"
    VALID = "VALID"
    WARNING = "WARNING"
    ERROR = "ERROR"
    APPROVED = "APPROVED"
    APPLIED = "APPLIED"
    SKIPPED = "SKIPPED"


class ImportSourceType(StrEnum):
    CSV = "CSV"
    XLSX = "XLSX"
    PDF = "PDF"
    DOCX = "DOCX"
    TIFF = "TIFF"
    JPEG = "JPEG"
    PNG = "PNG"


class OcrStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    CANCELLED = "CANCELLED"


class InventoryScopeType(StrEnum):
    AREA = "AREA"
    SHELF = "SHELF"
    TRAY = "TRAY"
    POSITION_RANGE = "POSITION_RANGE"
    BOX = "BOX"


class InventoryStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class FindingType(StrEnum):
    MISSING_BOX = "MISSING_BOX"
    UNEXPECTED_BOX = "UNEXPECTED_BOX"
    WRONG_LOCATION = "WRONG_LOCATION"
    UNREGISTERED_BOX = "UNREGISTERED_BOX"
    DUPLICATE = "DUPLICATE"
    OTHER = "OTHER"


class FindingStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    ACCEPTED_DIFFERENCE = "ACCEPTED_DIFFERENCE"
    ESCALATED = "ESCALATED"


class LegalHoldTargetType(StrEnum):
    BOX = "BOX"
    CASE_FILE = "CASE_FILE"
    FILE_ASSET = "FILE_ASSET"


class LegalHoldStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"


class DeletionTargetType(StrEnum):
    BOX = "BOX"
    CASE_FILE = "CASE_FILE"
    FILE_ASSET = "FILE_ASSET"


class DeletionStatus(StrEnum):
    REQUESTED = "REQUESTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AuditActorType(StrEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    JOB = "JOB"


class AuditResult(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class AuditSource(StrEnum):
    API = "API"
    IMPORT = "IMPORT"
    OCR = "OCR"
    TASK = "TASK"
    SYSTEM = "SYSTEM"
```

### 7.1 Regla de evolución

Añadir un valor a un enum requiere:

1. nueva migración;
2. `DROP CONSTRAINT` del check anterior;
3. `ADD CONSTRAINT` con lista nueva;
4. prueba de lectura de datos antiguos;
5. revisión de índices parciales que usen el valor.

No se modifica el `StrEnum` sin migración.

---

## 8. Mixins y utilidades ORM

### Archivo: `backend/src/judicial_archive/db/mixins.py`

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


def enum_values(enum_type: type[StrEnum]) -> str:
    return ", ".join(f"'{item.value}'" for item in enum_type)


def check_in(column: str, enum_type: type[StrEnum], *, name: str) -> CheckConstraint:
    return CheckConstraint(f"{column} IN ({enum_values(enum_type)})", name=name)


def check_jsonb_object(column: str, *, name: str) -> CheckConstraint:
    return CheckConstraint(
        f"{column} IS NULL OR jsonb_typeof({column}) = 'object'",
        name=name,
    )


def check_jsonb_array(column: str, *, name: str) -> CheckConstraint:
    return CheckConstraint(
        f"{column} IS NULL OR jsonb_typeof({column}) = 'array'",
        name=name,
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class OptimisticLockMixin:
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:  # noqa: N805
        return {"version_id_col": cls.version}


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deleted_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


def non_empty_text(column: str, *, name: str) -> CheckConstraint:
    return CheckConstraint(f"length(btrim({column})) > 0", name=name)


def partial_date_checks(
    table_name: str,
    prefix: str,
) -> tuple[CheckConstraint, CheckConstraint, CheckConstraint]:
    year = f"{prefix}_year"
    month = f"{prefix}_month"
    day = f"{prefix}_day"
    precision = f"{prefix}_precision"
    check_precision = CheckConstraint(
        f"{precision} IN ('UNKNOWN', 'YEAR', 'MONTH', 'DAY')",
        name=f"ck_{table_name}_{prefix}_precision",
    )
    check_shape = CheckConstraint(
        "("
        f"({precision} = 'UNKNOWN' AND {year} IS NULL AND {month} IS NULL AND {day} IS NULL)"
        f" OR ({precision} = 'YEAR' AND {year} IS NOT NULL AND {month} IS NULL AND {day} IS NULL)"
        f" OR ({precision} = 'MONTH' AND {year} IS NOT NULL AND {month} IS NOT NULL AND {day} IS NULL)"
        f" OR ({precision} = 'DAY' AND {year} IS NOT NULL AND {month} IS NOT NULL AND {day} IS NOT NULL)"
        ")",
        name=f"ck_{table_name}_{prefix}_shape",
    )
    check_ranges = CheckConstraint(
        f"({year} IS NULL OR {year} BETWEEN 1 AND 9999)"
        f" AND ({month} IS NULL OR {month} BETWEEN 1 AND 12)"
        f" AND ({day} IS NULL OR {day} BETWEEN 1 AND 31)",
        name=f"ck_{table_name}_{prefix}_ranges",
    )
    return check_precision, check_shape, check_ranges
```

### 8.1 Advertencia sobre nombres de checks

Todos los checks llevan el nombre final completo. La convención `ck` se cambia
a `%(constraint_name)s` en 8.3; así el nombre escrito en el modelo es el nombre
real en PostgreSQL.

- `check_in`, `check_jsonb_object`, `check_jsonb_array` y `non_empty_text`
  reciben el nombre final (`ck_<tabla>_<regla>`).
- `partial_date_checks` construye `ck_<tabla>_<prefijo>_precision`, `_shape` y
  `_ranges`; se le pasa el nombre real de la tabla y el prefijo de las columnas.
- No se debe aplicar otro prefijo al nombre devuelto ni usar la convención
  antigua `ck_%(table_name)s_%(constraint_name)s`; produciría `ck_ck_...`.
- Si un check se declara sin nombre, SQLAlchemy falla al construir el DDL.

### 8.2 Regla de imports

- `db/mixins.py` puede importar `db/base.py`.
- No importa modelos de módulos.
- Los módulos importan mixins y enums.
- Los modelos no importan servicios.

### 8.2.1 Atributo `metadata` reservado

SQLAlchemy declara `Base.metadata` y reserva el nombre `metadata` como atributo
de clase. Por eso las columnas llamadas `metadata` se mapean así:

```python
metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
    "metadata", JSONB, nullable=True
)
```

La columna en PostgreSQL sigue llamándose `metadata`; el atributo Python es
`metadata_json`. Aplicar la misma regla a `AuditEvent`, `FileAsset` y
`OcrResult`.

### 8.3 Ajuste requerido en `db/base.py`

Todos los `CheckConstraint` de B2 llevan nombre completo explícito
(`ck_<tabla>_<regla>`). La convención actual de B0 añade otro prefijo y produce
nombres como `ck_boxes_ck_boxes_box_type`.

Cambiar:

```python
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

por:

```python
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

Consecuencia:

- Todo `CHECK` debe tener nombre explícito; los tests lo verifican.
- Los nombres finales coinciden exactamente con los escritos en el modelo.
- `UNIQUE`, `INDEX` y `FOREIGN KEY` con nombre explícito no cambian.
- Si se crea un check sin nombre, SQLAlchemy falla; es intencional.

Alternativa descartada: usar solo el sufijo en cada `CheckConstraint`. Se
descarta porque este documento y las revisiones necesitan nombres completos
visibles y estables sin depender de la convención.

---

## 9. Modelos por módulo

Los modelos se presentan completos. Cada archivo puede copiarse como unidad. Las
relaciones ORM se mantienen mínimas; los servicios de fases posteriores usarán
consultas explícitas y cargas controladas.

### 9.1 Usuarios y permisos

#### Archivo: `backend/src/judicial_archive/modules/users/models.py`

```python
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import CatalogStatus, UserStatus
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class Role(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (
        check_in("status", CatalogStatus, name="ck_roles_status"),
        CheckConstraint(
            "code ~ '^[A-Z][A-Z0-9_]{1,63}$'",
            name="ck_roles_code_format",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_roles_name_not_empty",
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=CatalogStatus.ACTIVE.value,
        server_default=CatalogStatus.ACTIVE.value,
    )


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "permissions"
    __table_args__ = (
        CheckConstraint(
            "code ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$'",
            name="ck_permissions_code_format",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_permissions_name_not_empty",
        ),
    )

    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class User(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        check_in("status", UserStatus, name="ck_users_status"),
        CheckConstraint(
            "username_normalized = lower(btrim(username))",
            name="ck_users_username_normalized",
        ),
        CheckConstraint(
            "email IS NULL OR email_normalized = lower(btrim(email))",
            name="ck_users_email_normalized",
        ),
        CheckConstraint(
            "(email IS NULL AND email_normalized IS NULL) OR "
            "(email IS NOT NULL AND email_normalized IS NOT NULL)",
            name="ck_users_email_pair",
        ),
        CheckConstraint(
            "length(password_hash) >= 20",
            name="ck_users_password_hash_not_empty",
        ),
        Index("ix_users_status", "status"),
        Index("ix_users_display_name", "display_name"),
    )

    username: Mapped[str] = mapped_column(String(64), nullable=False)
    username_normalized: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    email_normalized: Mapped[str | None] = mapped_column(
        String(254), nullable=True, unique=True
    )
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=UserStatus.ACTIVE.value,
        server_default=UserStatus.ACTIVE.value,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (Index("ix_user_roles_role_id", "role_id"),)

    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    assigned_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (Index("ix_role_permissions_permission_id", "permission_id"),)

    role_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    granted_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
```

#### Notas de usuarios

- `username_normalized` y `email_normalized` son obligatorios para comparación;
  el servicio los calcula y el `CHECK` impide olvidar la normalización.
- `password_hash` es un hash Argon2id producido por B3; B2 no crea contraseñas.
- `CASCADE` en asociaciones no destruye usuarios, roles ni permisos.
- `failed_login_count` se añade para bloqueo futuro; B3 implementa la política.
- No se incluye tabla de tokens de recuperación; B3 la añadirá con migración
  propia si corresponde.

### 9.2 Sesiones de autenticación

#### Archivo: `backend/src/judicial_archive/modules/auth/models.py`

```python
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.db.base import Base
from judicial_archive.db.mixins import UUIDPrimaryKeyMixin


class UserSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        CheckConstraint(
            "length(token_hash) > 0",
            name="ck_user_sessions_token_hash_not_empty",
        ),
        CheckConstraint(
            "absolute_expires_at > created_at",
            name="ck_user_sessions_expiry_after_creation",
        ),
        CheckConstraint(
            "last_seen_at IS NULL OR last_seen_at >= created_at",
            name="ck_user_sessions_last_seen_after_creation",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_user_sessions_revoked_after_creation",
        ),
        Index("ix_user_sessions_user_id", "user_id"),
        Index("ix_user_sessions_expires_at", "absolute_expires_at"),
        Index(
            "ix_user_sessions_active_user",
            "user_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    csrf_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    absolute_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
```

#### Notas de sesiones

- Se guarda hash del token, nunca el token en claro.
- La expiración absoluta se fija al crear.
- La renovación por inactividad pertenece al servicio de B3.
- `ON DELETE RESTRICT` impide borrar usuarios con sesiones; se revocan.

### 9.3 Auditoría append-only

#### Archivo: `backend/src/judicial_archive/modules/audit/models.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import AuditActorType, AuditResult, AuditSource
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import UUIDPrimaryKeyMixin, check_in


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        check_in("actor_type", AuditActorType, name="ck_audit_events_actor_type"),
        check_in("result", AuditResult, name="ck_audit_events_result"),
        check_in("source", AuditSource, name="ck_audit_events_source"),
        CheckConstraint(
            "actor_type <> 'USER' OR actor_user_id IS NOT NULL",
            name="ck_audit_events_user_actor",
        ),
        CheckConstraint(
            "length(btrim(action)) > 0",
            name="ck_audit_events_action_not_empty",
        ),
        CheckConstraint(
            "before_data IS NULL OR jsonb_typeof(before_data) = 'object'",
            name="ck_audit_events_before_object",
        ),
        CheckConstraint(
            "after_data IS NULL OR jsonb_typeof(after_data) = 'object'",
            name="ck_audit_events_after_object",
        ),
        CheckConstraint(
            "metadata IS NULL OR jsonb_typeof(metadata) = 'object'",
            name="ck_audit_events_metadata_object",
        ),
        Index(
            "ix_audit_events_entity",
            "entity_type",
            "entity_id",
            "occurred_at",
        ),
        Index("ix_audit_events_actor", "actor_user_id", "occurred_at"),
        Index("ix_audit_events_request_id", "request_id"),
        Index("ix_audit_events_occurred_at", "occurred_at"),
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    actor_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True), nullable=True
    )
    before_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
```

#### Notas de auditoría

- No tiene `updated_at`, `version` ni campos de baja.
- El trigger de migración bloquea `UPDATE`, `DELETE` y `TRUNCATE`.
- No hay FK a la entidad auditada; sí hay FK opcional al usuario actor.
- Las escrituras de auditoría se harán en la misma transacción que la acción
  cuando el servicio lo requiera.
- La inmutabilidad se prueba también intentando actualizar desde SQL directo.

### 9.4 Tribunales y catálogos judiciales

#### Archivo: `backend/src/judicial_archive/modules/courts/models.py`

```python
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import (
    BoxType,
    CatalogStatus,
    CourtStatus,
    IdentifierKind,
    NumberingScope,
    ResetPolicy,
    RetentionDisposition,
    RetentionEntityType,
    SettingValueType,
)
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class Court(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "courts"
    __table_args__ = (
        check_in("status", CourtStatus, name="ck_courts_status"),
        CheckConstraint(
            "code_normalized = upper(btrim(code_raw))",
            name="ck_courts_code_normalized",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_courts_name_not_empty",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL "
            "OR effective_to >= effective_from",
            name="ck_courts_effective_range",
        ),
        Index("ix_courts_status", "status"),
        Index("ix_courts_name", "name"),
    )

    code_raw: Mapped[str] = mapped_column(String(32), nullable=False)
    code_normalized: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    court_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=CourtStatus.ACTIVE.value,
        server_default=CourtStatus.ACTIVE.value,
    )
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class IdentifierFormatProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "identifier_format_profiles"
    __table_args__ = (
        check_in(
            "identifier_kind",
            IdentifierKind,
            name="ck_identifier_format_profiles_kind",
        ),
        CheckConstraint(
            "strict = false OR pattern IS NOT NULL",
            name="ck_identifier_format_profiles_strict_pattern",
        ),
        CheckConstraint(
            "examples IS NULL OR jsonb_typeof(examples) = 'array'",
            name="ck_identifier_format_profiles_examples_array",
        ),
        CheckConstraint(
            "rejects IS NULL OR jsonb_typeof(rejects) = 'array'",
            name="ck_identifier_format_profiles_rejects_array",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_identifier_format_profiles_effective_range",
        ),
        Index(
            "ix_identifier_format_profiles_court_kind",
            "court_id",
            "identifier_kind",
        ),
        Index(
            "uq_identifier_format_profiles_active",
            "court_id",
            "identifier_kind",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    court_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("courts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    identifier_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    pattern: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tokens: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    examples: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    rejects: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    strict: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    effective_from: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class ResolutionType(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "resolution_types"
    __table_args__ = (
        check_in("status", CatalogStatus, name="ck_resolution_types_status"),
        CheckConstraint(
            "code ~ '^[A-Z][A-Z0-9_]{1,31}$'",
            name="ck_resolution_types_code_format",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_resolution_types_name_not_empty",
        ),
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=CatalogStatus.ACTIVE.value,
        server_default=CatalogStatus.ACTIVE.value,
    )


class NumberingPolicy(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "numbering_policies"
    __table_args__ = (
        check_in("scope", NumberingScope, name="ck_numbering_policies_scope"),
        check_in("reset_policy", ResetPolicy, name="ck_numbering_policies_reset"),
        check_in("box_type", BoxType, name="ck_numbering_policies_box_type"),
        CheckConstraint(
            "("
            "(scope = 'GLOBAL' AND court_id IS NULL AND box_type IS NULL AND year IS NULL)"
            " OR (scope = 'COURT' AND court_id IS NOT NULL AND box_type IS NULL AND year IS NULL)"
            " OR (scope = 'BOX_TYPE' AND court_id IS NULL AND box_type IS NOT NULL AND year IS NULL)"
            " OR (scope = 'YEAR' AND court_id IS NULL AND box_type IS NULL AND year IS NOT NULL)"
            ")",
            name="ck_numbering_policies_scope_columns",
        ),
        CheckConstraint(
            "padding BETWEEN 0 AND 12",
            name="ck_numbering_policies_padding",
        ),
        CheckConstraint(
            "start_value > 0",
            name="ck_numbering_policies_start_value",
        ),
        CheckConstraint(
            "step > 0",
            name="ck_numbering_policies_step",
        ),
        CheckConstraint(
            "length(btrim(sequence_name)) > 0",
            name="ck_numbering_policies_sequence_name",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_numbering_policies_effective_range",
        ),
        Index(
            "uq_numbering_policies_active_global",
            "scope",
            unique=True,
            postgresql_where=text("is_active AND scope = 'GLOBAL'"),
        ),
        Index(
            "uq_numbering_policies_active_court",
            "court_id",
            unique=True,
            postgresql_where=text("is_active AND scope = 'COURT'"),
        ),
        Index(
            "uq_numbering_policies_active_box_type",
            "box_type",
            unique=True,
            postgresql_where=text("is_active AND scope = 'BOX_TYPE'"),
        ),
        Index(
            "uq_numbering_policies_active_year",
            "year",
            unique=True,
            postgresql_where=text("is_active AND scope = 'YEAR'"),
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    court_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("courts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    box_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sequence_name: Mapped[str] = mapped_column(String(63), nullable=False, unique=True)
    prefix: Mapped[str | None] = mapped_column(String(32), nullable=True)
    suffix: Mapped[str | None] = mapped_column(String(32), nullable=True)
    padding: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    start_value: Mapped[int] = mapped_column(Integer, nullable=False)
    step: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    reset_policy: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ResetPolicy.NEVER.value,
        server_default=ResetPolicy.NEVER.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    effective_from: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class RetentionPolicy(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "retention_policies"
    __table_args__ = (
        check_in(
            "entity_type",
            RetentionEntityType,
            name="ck_retention_policies_entity_type",
        ),
        check_in(
            "disposition",
            RetentionDisposition,
            name="ck_retention_policies_disposition",
        ),
        check_in("box_type", BoxType, name="ck_retention_policies_box_type"),
        CheckConstraint(
            "retention_months IS NULL OR retention_months > 0",
            name="ck_retention_policies_months",
        ),
        CheckConstraint(
            "is_active = false OR length(btrim(legal_basis)) > 0",
            name="ck_retention_policies_active_legal_basis",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_retention_policies_effective_range",
        ),
        Index(
            "ix_retention_policies_lookup",
            "entity_type",
            "court_id",
            "box_type",
            "is_active",
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    court_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("courts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    box_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    retention_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disposition: Mapped[str] = mapped_column(String(16), nullable=False)
    legal_basis: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    effective_from: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class SystemSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "system_settings"
    __table_args__ = (
        check_in(
            "value_type",
            SettingValueType,
            name="ck_system_settings_value_type",
        ),
        CheckConstraint(
            "key ~ '^[a-z][a-z0-9_.-]{2,127}$'",
            name="ck_system_settings_key_format",
        ),
        CheckConstraint(
            "("
            "(value_type = 'STRING' AND jsonb_typeof(value) = 'string')"
            " OR (value_type = 'INTEGER' AND jsonb_typeof(value) = 'number')"
            " OR (value_type = 'BOOLEAN' AND jsonb_typeof(value) = 'boolean')"
            " OR (value_type = 'JSON' AND jsonb_typeof(value) IN ('object', 'array'))"
            ")",
            name="ck_system_settings_value_matches_type",
        ),
        CheckConstraint(
            "length(btrim(description)) > 0",
            name="ck_system_settings_description_not_empty",
        ),
    )

    key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    value_type: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    updated_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class PartyRole(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "party_roles"
    __table_args__ = (
        check_in("status", CatalogStatus, name="ck_party_roles_status"),
        CheckConstraint(
            "code ~ '^[A-Z][A-Z0-9_]{1,63}$'",
            name="ck_party_roles_code_format",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_party_roles_name_not_empty",
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=CatalogStatus.ACTIVE.value,
        server_default=CatalogStatus.ACTIVE.value,
    )
```

#### Notas de tribunales

- `courts.code_raw` no es único; `code_normalized` tampoco.
- La identidad es el UUID.
- `year` de tribunal no se confunde con el año de caja o expediente.
- Las políticas de formato no bloquean códigos históricos; validan datos nuevos.
- `NumberingPolicy` no guarda `next_value`; la secuencia es la fuente de verdad.
- `is_active` con índices parciales impide dos políticas activas del mismo
  alcance, pero no impide solapamientos entre alcances distintos; el servicio
  aplica prioridad y detecta ambigüedad.
- `RetentionPolicy` puede ser específica por tribunal y tipo de caja. La
  selección de la política aplicable pertenece a B7.
- Los plazos legales de retención no se inventan; si no están confirmados, se
  dejan `NULL` y `REVIEW`.

### 9.5 Ubicaciones físicas

#### Archivo: `backend/src/judicial_archive/modules/locations/models.py`

```python
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import (
    AreaStatus,
    PositionStatus,
    ShelfStatus,
    TrayStatus,
)
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class Area(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "areas"
    __table_args__ = (
        check_in("status", AreaStatus, name="ck_areas_status"),
        CheckConstraint(
            "code ~ '^[A-Z][A-Z0-9-]{0,15}$'",
            name="ck_areas_code_format",
        ),
        CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_areas_name_not_empty",
        ),
    )

    code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=AreaStatus.ACTIVE.value,
        server_default=AreaStatus.ACTIVE.value,
    )


class Shelf(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "shelves"
    __table_args__ = (
        UniqueConstraint("area_id", "code", name="uq_shelves_area_code"),
        check_in("status", ShelfStatus, name="ck_shelves_status"),
        CheckConstraint(
            "code ~ '^[A-Z0-9][A-Z0-9-]{0,15}$'",
            name="ck_shelves_code_format",
        ),
        CheckConstraint(
            "(levels IS NULL AND positions_per_level IS NULL) OR "
            "(levels IS NOT NULL AND positions_per_level IS NOT NULL)",
            name="ck_shelves_capacity_pair",
        ),
        CheckConstraint(
            "levels IS NULL OR levels > 0",
            name="ck_shelves_levels_positive",
        ),
        CheckConstraint(
            "positions_per_level IS NULL OR positions_per_level > 0",
            name="ck_shelves_positions_positive",
        ),
        Index("ix_shelves_area_id", "area_id"),
    )

    area_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("areas.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    levels: Mapped[int | None] = mapped_column(Integer, nullable=True)
    positions_per_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capacity_positions: Mapped[int | None] = mapped_column(
        Integer,
        Computed("levels * positions_per_level", persisted=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ShelfStatus.ACTIVE.value,
        server_default=ShelfStatus.ACTIVE.value,
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class Tray(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "trays"
    __table_args__ = (
        UniqueConstraint("shelf_id", "code", name="uq_trays_shelf_code"),
        check_in("status", TrayStatus, name="ck_trays_status"),
        CheckConstraint(
            "code ~ '^[A-Z0-9][A-Z0-9-]{0,15}$'",
            name="ck_trays_code_format",
        ),
        CheckConstraint(
            "position_count IS NULL OR position_count > 0",
            name="ck_trays_position_count",
        ),
        Index("ix_trays_shelf_id", "shelf_id"),
    )

    shelf_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("shelves.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    position_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=TrayStatus.ACTIVE.value,
        server_default=TrayStatus.ACTIVE.value,
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class Position(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("tray_id", "code", name="uq_positions_tray_code"),
        check_in("status", PositionStatus, name="ck_positions_status"),
        CheckConstraint(
            "length(btrim(code)) > 0",
            name="ck_positions_code_not_empty",
        ),
        CheckConstraint(
            "length(btrim(label)) > 0",
            name="ck_positions_label_not_empty",
        ),
        Index("ix_positions_tray_id", "tray_id"),
        Index("ix_positions_status", "status"),
    )

    tray_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("trays.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=PositionStatus.AVAILABLE.value,
        server_default=PositionStatus.AVAILABLE.value,
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class PositionBlock(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "position_blocks"
    __table_args__ = (
        CheckConstraint(
            "first_position_number > 0",
            name="ck_position_blocks_first_number",
        ),
        CheckConstraint(
            "last_position_number >= first_position_number",
            name="ck_position_blocks_range",
        ),
        CheckConstraint(
            "cancelled_at IS NULL OR cancelled_at >= created_at",
            name="ck_position_blocks_cancel_after_creation",
        ),
        CheckConstraint(
            "length(btrim(reason)) > 0",
            name="ck_position_blocks_reason_not_empty",
        ),
        Index(
            "ix_position_blocks_shelf_active",
            "shelf_id",
            "start_position_id",
            "end_position_id",
        ),
    )

    shelf_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("shelves.id", ondelete="RESTRICT"),
        nullable=False,
    )
    start_position_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    end_position_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    first_position_number: Mapped[int] = mapped_column(Integer, nullable=False)
    last_position_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    blocked_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
```

#### Notas de ubicaciones

- `capacity_positions` es una columna generada almacenada; si falta capacidad,
  queda nula.
- No se crean posiciones masivamente en B2. Las posiciones reales se cargan
  cuando la capacidad y nomenclatura estén confirmadas.
- `PositionBlock` conserva el rango histórico; el servicio crea los bloqueos
  efectivos por posición en una fase posterior.
- `first_position_number` y `last_position_number` son números de orden del
  rango dentro del anaquel, no números visibles de caja.
- Las FK `RESTRICT` impiden borrar áreas, anaqueles, bandejas o posiciones con
  historia.

### 9.6 Cajas, numeración y movimientos

#### Archivo: `backend/src/judicial_archive/modules/boxes/models.py`

```python
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import (
    BoxLifecycleStatus,
    BoxType,
    Confidentiality,
    CustodyStatus,
    LocationPrecision,
    MovementStatus,
    MovementType,
)
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class Box(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "boxes"
    __table_args__ = (
        UniqueConstraint("visible_number", name="uq_boxes_visible_number"),
        UniqueConstraint("id", "box_type", name="uq_boxes_id_box_type"),
        check_in("box_type", BoxType, name="ck_boxes_box_type"),
        check_in(
            "lifecycle_status",
            BoxLifecycleStatus,
            name="ck_boxes_lifecycle_status",
        ),
        check_in("custody_status", CustodyStatus, name="ck_boxes_custody_status"),
        check_in(
            "confidentiality",
            Confidentiality,
            name="ck_boxes_confidentiality",
        ),
        check_in(
            "location_precision",
            LocationPrecision,
            name="ck_boxes_location_precision",
        ),
        CheckConstraint(
            "year BETWEEN 1 AND 9999",
            name="ck_boxes_year_range",
        ),
        CheckConstraint(
            "length(btrim(visible_number)) > 0",
            name="ck_boxes_visible_number_not_empty",
        ),
        CheckConstraint(
            "("
            "(custody_status IN ('IN_PLACE', 'IN_RECONCILIATION') "
            "AND current_position_id IS NOT NULL)"
            " OR (custody_status NOT IN ('IN_PLACE', 'IN_RECONCILIATION') "
            "AND current_position_id IS NULL)"
            ")",
            name="ck_boxes_custody_position",
        ),
        CheckConstraint(
            "lifecycle_status <> 'ARCHIVED' OR archived_at IS NOT NULL",
            name="ck_boxes_archived_at",
        ),
        CheckConstraint(
            "lifecycle_status <> 'VOIDED' OR voided_at IS NOT NULL",
            name="ck_boxes_voided_at",
        ),
        CheckConstraint(
            "lifecycle_status <> 'DESTROYED' OR destroyed_at IS NOT NULL",
            name="ck_boxes_destroyed_at",
        ),
        CheckConstraint(
            "lifecycle_status <> 'DESTROYED' OR current_position_id IS NULL",
            name="ck_boxes_destroyed_without_position",
        ),
        Index(
            "ix_boxes_court_year_type",
            "court_id",
            "year",
            "box_type",
        ),
        Index("ix_boxes_lifecycle_status", "lifecycle_status"),
        Index("ix_boxes_custody_status", "custody_status"),
        Index(
            "uq_boxes_current_position_occupied",
            "current_position_id",
            unique=True,
            postgresql_where=text(
                "custody_status IN ('IN_PLACE', 'IN_RECONCILIATION') "
                "AND current_position_id IS NOT NULL"
            ),
        ),
    )

    court_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("courts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    box_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=BoxType.EXPEDIENTES.value,
        server_default=BoxType.EXPEDIENTES.value,
    )
    visible_number: Mapped[str] = mapped_column(String(32), nullable=False)
    numbering_policy_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("numbering_policies.id", ondelete="RESTRICT"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confidentiality: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=Confidentiality.INTERNAL.value,
        server_default=Confidentiality.INTERNAL.value,
    )
    lifecycle_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=BoxLifecycleStatus.ACTIVE.value,
        server_default=BoxLifecycleStatus.ACTIVE.value,
    )
    custody_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=CustodyStatus.UNKNOWN.value,
        server_default=CustodyStatus.UNKNOWN.value,
    )
    current_position_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    location_precision: Mapped[str] = mapped_column(
        String(16),
        Computed(
            "CASE "
            "WHEN current_position_id IS NULL THEN 'UNKNOWN' "
            "WHEN custody_status = 'IN_PLACE' THEN 'CONFIRMED' "
            "ELSE 'PENDING' "
            "END",
            persisted=True,
        ),
        nullable=False,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archived_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    archive_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    voided_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    void_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    destroyed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    destroyed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    destruction_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class BoxNumberHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "box_number_history"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(new_number)) > 0",
            name="ck_box_number_history_new_number_not_empty",
        ),
        CheckConstraint(
            "previous_number IS NULL OR length(btrim(previous_number)) > 0",
            name="ck_box_number_history_previous_number_not_empty",
        ),
        CheckConstraint(
            "previous_number IS NULL OR previous_number <> new_number",
            name="ck_box_number_history_changed",
        ),
        CheckConstraint(
            "length(btrim(reason)) > 0",
            name="ck_box_number_history_reason_not_empty",
        ),
        Index("ix_box_number_history_box_id", "box_id", "changed_at"),
    )

    box_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    previous_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_number: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    changed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class BoxMovement(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "box_movements"
    __table_args__ = (
        check_in("movement_type", MovementType, name="ck_box_movements_type"),
        check_in("movement_status", MovementStatus, name="ck_box_movements_status"),
        CheckConstraint(
            "from_position_id IS NULL OR to_position_id IS NULL "
            "OR from_position_id <> to_position_id",
            name="ck_box_movements_position_change",
        ),
        CheckConstraint(
            "movement_status <> 'COMPLETED' OR completed_at IS NOT NULL",
            name="ck_box_movements_completed_at",
        ),
        CheckConstraint(
            "movement_status <> 'CANCELLED' OR cancelled_at IS NOT NULL",
            name="ck_box_movements_cancelled_at",
        ),
        CheckConstraint(
            "length(btrim(reason)) > 0",
            name="ck_box_movements_reason_not_empty",
        ),
        Index("ix_box_movements_box", "box_id", "occurred_at"),
        Index("ix_box_movements_status", "movement_status"),
    )

    box_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    movement_type: Mapped[str] = mapped_column(String(24), nullable=False)
    movement_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=MovementStatus.PLANNED.value,
        server_default=MovementStatus.PLANNED.value,
    )
    from_position_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    to_position_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    loan_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("loans.id", ondelete="RESTRICT"),
        nullable=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    performed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
```

#### Notas de cajas

- `visible_number` es texto para preservar ceros y formatos.
- `UNIQUE (visible_number)` es global; B1 no define numeración por año.
- La secuencia se crea en la migración, no con `autoincrement` de SQLAlchemy.
- `next_number()` se implementará en un repositorio de B4; B2 no incluye lógica
  de asignación.
- `UNIQUE (id, box_type)` parece redundante, pero es el destino de la FK
  compuesta de contenido.
- `location_precision` se calcula en la base para no quedar desincronizada.
- `custody_status` obliga a limpiar `current_position_id` al sacar una caja.
- El índice único parcial impide dos cajas `IN_PLACE` o `IN_RECONCILIATION` en la misma posición.
- La inmutabilidad de `court_id`, `year` y `box_type` con contenido se impone
  por trigger en la migración.
- Los estados `ARCHIVED`, `VOIDED` y `DESTROYED` exigen su timestamp.
- No se permite destruir una caja que conserva posición actual.
- `BoxNumberHistory` no tiene FK que impida cambiar varias veces; el servicio
  exige motivo y auditoría.
- `BoxMovement.loan_id` referencia préstamos creados en el mismo esquema; no se
  importa el modelo de préstamos para evitar acoplamiento.

### 9.7 Etiquetas QR

#### Archivo: `backend/src/judicial_archive/modules/qr/models.py`

```python
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.db.base import Base
from judicial_archive.db.mixins import UUIDPrimaryKeyMixin


class BoxLabel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "box_labels"
    __table_args__ = (
        CheckConstraint(
            "length(token_hash) > 0",
            name="ck_box_labels_token_hash_not_empty",
        ),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= issued_at",
            name="ck_box_labels_revoked_after_issue",
        ),
        Index(
            "ix_box_labels_box_active",
            "box_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    box_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    version: Mapped[int] = mapped_column(
        nullable=False, default=1, server_default=text("1")
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    issued_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    printed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    revoke_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

#### Notas de QR

- Se guarda hash del token, no el token.
- El token se genera en B10; B2 solo define persistencia.
- Se permite más de una etiqueta histórica por caja.
- La etiqueta activa no se fuerza a una sola por caja en B2; la política de
  reimpresión se implementa en B10.

### 9.8 Expedientes, identificadores y partes

#### Archivo: `backend/src/judicial_archive/modules/case_files/models.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import (
    BoxType,
    Confidentiality,
    IdentifierKind,
    LifecycleStatus,
    VerificationStatus,
)
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
    partial_date_checks,
)


class CaseFile(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "case_files"
    __table_args__ = (
        ForeignKeyConstraint(
            ["box_id", "box_type"],
            ["boxes.id", "boxes.box_type"],
            name="fk_case_files_box_type",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        check_in("box_type", BoxType, name="ck_case_files_box_type"),
        check_in("lifecycle_status", LifecycleStatus, name="ck_case_files_lifecycle"),
        check_in(
            "verification_status",
            VerificationStatus,
            name="ck_case_files_verification",
        ),
        check_in(
            "confidentiality",
            Confidentiality,
            name="ck_case_files_confidentiality",
        ),
        CheckConstraint(
            "box_type = 'EXPEDIENTES'",
            name="ck_case_files_box_type_expedientes",
        ),
        CheckConstraint(
            "box_id IS NULL OR box_type = 'EXPEDIENTES'",
            name="ck_case_files_box_type_consistency",
        ),
        CheckConstraint(
            "length(btrim(nuc_raw)) > 0",
            name="ck_case_files_nuc_raw_not_empty",
        ),
        CheckConstraint(
            "length(btrim(nuc_normalized)) > 0",
            name="ck_case_files_nuc_normalized_not_empty",
        ),
        CheckConstraint(
            "year BETWEEN 1 AND 9999",
            name="ck_case_files_year_range",
        ),
        CheckConstraint(
            "lifecycle_status <> 'ARCHIVED' OR archived_at IS NOT NULL",
            name="ck_case_files_archived_at",
        ),
        CheckConstraint(
            "lifecycle_status <> 'VOIDED' OR voided_at IS NOT NULL",
            name="ck_case_files_voided_at",
        ),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_by IS NOT NULL",
            name="ck_case_files_deleted_actor",
        ),
        *partial_date_checks("case_files", "entry"),
        *partial_date_checks("case_files", "sentence"),
        Index("ix_case_files_court_nuc", "court_id", "nuc_normalized"),
        Index("ix_case_files_nuc_suffix5", "nuc_suffix5"),
        Index("ix_case_files_box_id", "box_id"),
        Index("ix_case_files_year", "year"),
        Index("ix_case_files_lifecycle", "lifecycle_status"),
        Index("ix_case_files_verification", "verification_status"),
    )

    court_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("courts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    box_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    box_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=BoxType.EXPEDIENTES.value,
        server_default=BoxType.EXPEDIENTES.value,
    )
    nuc_raw: Mapped[str] = mapped_column(String(100), nullable=False)
    nuc_normalized: Mapped[str] = mapped_column(String(100), nullable=False)
    nuc_suffix5: Mapped[str] = mapped_column(
        String(5),
        Computed("right(nuc_normalized, 5)", persisted=True),
        nullable=False,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entry_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entry_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entry_precision: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'UNKNOWN'")
    )
    sentence_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sentence_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sentence_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sentence_precision: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'UNKNOWN'")
    )
    resolution_type_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("resolution_types.id", ondelete="RESTRICT"),
        nullable=True,
    )
    resolution_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    judge_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    court_name_raw: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=VerificationStatus.PENDING.value,
        server_default=VerificationStatus.PENDING.value,
    )
    confidentiality: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=Confidentiality.INTERNAL.value,
        server_default=Confidentiality.INTERNAL.value,
    )
    lifecycle_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=LifecycleStatus.ACTIVE.value,
        server_default=LifecycleStatus.ACTIVE.value,
    )
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archived_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    archive_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    voided_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    void_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)


class CaseFileIdentifierHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "case_file_identifier_history"
    __table_args__ = (
        check_in("identifier_kind", IdentifierKind, name="ck_case_identifier_kind"),
        CheckConstraint(
            "length(btrim(value_raw)) > 0",
            name="ck_case_identifier_raw_not_empty",
        ),
        CheckConstraint(
            "length(btrim(value_normalized)) > 0",
            name="ck_case_identifier_normalized_not_empty",
        ),
        CheckConstraint(
            "length(btrim(reason)) > 0",
            name="ck_case_identifier_reason_not_empty",
        ),
        Index(
            "ix_case_file_identifier_case",
            "case_file_id",
            "changed_at",
        ),
        Index(
            "ix_case_file_identifier_lookup",
            "identifier_kind",
            "value_normalized",
        ),
    )

    case_file_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("case_files.id", ondelete="RESTRICT"),
        nullable=False,
    )
    identifier_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    value_raw: Mapped[str] = mapped_column(String(100), nullable=False)
    value_normalized: Mapped[str] = mapped_column(String(100), nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    changed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class Person(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "persons"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(display_name)) > 0",
            name="ck_persons_display_name_not_empty",
        ),
        CheckConstraint(
            "length(btrim(normalized_name)) > 0",
            name="ck_persons_normalized_name_not_empty",
        ),
        CheckConstraint(
            "aliases IS NULL OR jsonb_typeof(aliases) = 'array'",
            name="ck_persons_aliases_array",
        ),
        CheckConstraint(
            "birth_year IS NULL OR birth_year BETWEEN 1 AND 9999",
            name="ck_persons_birth_year_range",
        ),
        CheckConstraint(
            "birth_month IS NULL OR birth_month BETWEEN 1 AND 12",
            name="ck_persons_birth_month_range",
        ),
        CheckConstraint(
            "birth_day IS NULL OR birth_day BETWEEN 1 AND 31",
            name="ck_persons_birth_day_range",
        ),
        CheckConstraint(
            "birth_day IS NULL OR birth_month IS NOT NULL",
            name="ck_persons_birth_day_requires_month",
        ),
        CheckConstraint(
            "birth_month IS NULL OR birth_year IS NOT NULL",
            name="ck_persons_birth_month_requires_year",
        ),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_by IS NOT NULL",
            name="ck_persons_deleted_actor",
        ),
        Index("ix_persons_normalized_name", "normalized_name"),
        Index("ix_persons_identification", "identification_number"),
    )

    display_name: Mapped[str] = mapped_column(String(300), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(300), nullable=False)
    aliases: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    identification_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    identification_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class CaseParty(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "case_parties"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(notes)) > 0 OR notes IS NULL",
            name="ck_case_parties_notes_not_blank",
        ),
        Index("ix_case_parties_case_file_id", "case_file_id"),
        Index("ix_case_parties_person_id", "person_id"),
    )

    case_file_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("case_files.id", ondelete="CASCADE"),
        nullable=False,
    )
    person_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="RESTRICT"),
        nullable=False,
    )
    party_role_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("party_roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
```

#### Notas de expedientes

- La FK compuesta impide asociar un expediente a una caja administrativa.
- `box_id` puede ser nulo; el expediente existe antes de ser ubicado.
- No se declara unique de NUC. La detección de duplicados y el `409` son de B4.
- `nuc_suffix5` se calcula sobre la cadena normalizada. B8 decide si además
  valida que sean dígitos.
- Las fechas parciales no completan día ni mes ausentes.
- La validez calendárica exacta (por ejemplo, 31 de febrero) se valida en el
  servicio; el check solo fija rangos.
- `CaseParty` usa `CASCADE` porque es una asociación sin historia propia. El
  servicio no debe borrar asociaciones de expedientes auditados sin registrar
  el cambio.
- `Person` admite bajas lógicas; los datos personales requieren políticas de
  retención y acceso que se implementan en fases posteriores.
- No se indexa por nombre con trigramas en B2; se hará cuando exista consulta y
  extensión aprobada.

### 9.9 Documentos administrativos

#### Archivo: `backend/src/judicial_archive/modules/administrative_documents/models.py`

```python
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import (
    BoxType,
    Confidentiality,
    LifecycleStatus,
    VerificationStatus,
)
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class AdministrativeDocument(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "administrative_documents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["box_id", "box_type"],
            ["boxes.id", "boxes.box_type"],
            name="fk_administrative_documents_box_type",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        check_in("box_type", BoxType, name="ck_admin_documents_box_type"),
        check_in(
            "lifecycle_status",
            LifecycleStatus,
            name="ck_admin_documents_lifecycle",
        ),
        check_in(
            "verification_status",
            VerificationStatus,
            name="ck_admin_documents_verification",
        ),
        check_in(
            "confidentiality",
            Confidentiality,
            name="ck_admin_documents_confidentiality",
        ),
        CheckConstraint(
            "box_type = 'DOCUMENTOS_ADMINISTRATIVOS'",
            name="ck_admin_documents_box_type_admin",
        ),
        CheckConstraint(
            "length(btrim(title)) > 0",
            name="ck_admin_documents_title_not_empty",
        ),
        CheckConstraint(
            "document_year BETWEEN 1 AND 9999",
            name="ck_admin_documents_year_range",
        ),
        CheckConstraint(
            "document_month IS NULL OR document_month BETWEEN 1 AND 12",
            name="ck_admin_documents_month_range",
        ),
        CheckConstraint(
            "document_day IS NULL OR document_day BETWEEN 1 AND 31",
            name="ck_admin_documents_day_range",
        ),
        CheckConstraint(
            "document_day IS NULL OR document_month IS NOT NULL",
            name="ck_admin_documents_day_requires_month",
        ),
        CheckConstraint(
            "lifecycle_status <> 'ARCHIVED' OR archived_at IS NOT NULL",
            name="ck_admin_documents_archived_at",
        ),
        CheckConstraint(
            "lifecycle_status <> 'VOIDED' OR voided_at IS NOT NULL",
            name="ck_admin_documents_voided_at",
        ),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_by IS NOT NULL",
            name="ck_admin_documents_deleted_actor",
        ),
        Index("ix_admin_documents_box_id", "box_id"),
        Index("ix_admin_documents_year", "document_year"),
        Index("ix_admin_documents_lifecycle", "lifecycle_status"),
    )

    box_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), nullable=False)
    box_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=BoxType.DOCUMENTOS_ADMINISTRATIVOS.value,
        server_default=BoxType.DOCUMENTOS_ADMINISTRATIVOS.value,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    document_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    document_year: Mapped[int] = mapped_column(Integer, nullable=False)
    document_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=VerificationStatus.PENDING.value,
        server_default=VerificationStatus.PENDING.value,
    )
    confidentiality: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=Confidentiality.INTERNAL.value,
        server_default=Confidentiality.INTERNAL.value,
    )
    lifecycle_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=LifecycleStatus.ACTIVE.value,
        server_default=LifecycleStatus.ACTIVE.value,
    )
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archived_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    archive_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    voided_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    void_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

#### Notas de documentos administrativos

- Siempre pertenecen a una caja administrativa.
- La FK compuesta impide asociarlos a cajas de expedientes.
- `document_year` refleja el año del documento, no necesariamente el de la caja.
- El archivo asociado se modela en `FileAttachment`, no con una columna
  `file_id` aquí.

### 9.10 Archivos y asociaciones documentales

#### Archivo: `backend/src/judicial_archive/modules/files/models.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import FileLinkKind, FileStatus
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class FileAsset(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    Base,
):
    __tablename__ = "file_assets"
    __table_args__ = (
        check_in("status", FileStatus, name="ck_file_assets_status"),
        CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_file_assets_sha256_format",
        ),
        CheckConstraint(
            "length(btrim(storage_key)) > 0",
            name="ck_file_assets_storage_key_not_empty",
        ),
        CheckConstraint(
            "length(btrim(original_name)) > 0",
            name="ck_file_assets_original_name_not_empty",
        ),
        CheckConstraint(
            "size_bytes >= 0",
            name="ck_file_assets_size_non_negative",
        ),
        CheckConstraint(
            "page_count IS NULL OR page_count > 0",
            name="ck_file_assets_page_count",
        ),
        CheckConstraint(
            "metadata IS NULL OR jsonb_typeof(metadata) = 'object'",
            name="ck_file_assets_metadata_object",
        ),
        CheckConstraint(
            "status <> 'DELETED' OR deleted_at IS NOT NULL",
            name="ck_file_assets_deleted_status",
        ),
        CheckConstraint(
            "deleted_at IS NULL OR deleted_by IS NOT NULL",
            name="ck_file_assets_deleted_actor",
        ),
        Index("ix_file_assets_sha256", "sha256"),
        Index("ix_file_assets_status", "status"),
    )

    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=FileStatus.PENDING.value,
        server_default=FileStatus.PENDING.value,
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    stored_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class FileAttachment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "file_attachments"
    __table_args__ = (
        check_in("link_kind", FileLinkKind, name="ck_file_attachments_link_kind"),
        CheckConstraint(
            "("
            "(case_file_id IS NOT NULL AND administrative_document_id IS NULL)"
            " OR (case_file_id IS NULL AND administrative_document_id IS NOT NULL)"
            ")",
            name="ck_file_attachments_one_target",
        ),
        CheckConstraint(
            "detached_at IS NULL OR ("
            "detached_reason IS NOT NULL "
            "AND length(btrim(detached_reason)) > 0)",
            name="ck_file_attachments_detached_reason",
        ),
        CheckConstraint(
            "is_primary = false OR detached_at IS NULL",
            name="ck_file_attachments_primary_not_detached",
        ),
        Index("ix_file_attachments_file_asset", "file_asset_id"),
        Index("ix_file_attachments_case_file", "case_file_id"),
        Index("ix_file_attachments_admin_document", "administrative_document_id"),
        Index(
            "uq_file_attachments_case_primary",
            "case_file_id",
            unique=True,
            postgresql_where=text(
                "is_primary AND detached_at IS NULL AND case_file_id IS NOT NULL"
            ),
        ),
        Index(
            "uq_file_attachments_admin_primary",
            "administrative_document_id",
            unique=True,
            postgresql_where=text(
                "is_primary AND detached_at IS NULL "
                "AND administrative_document_id IS NOT NULL"
            ),
        ),
    )

    file_asset_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("file_assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    case_file_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("case_files.id", ondelete="RESTRICT"),
        nullable=True,
    )
    administrative_document_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("administrative_documents.id", ondelete="RESTRICT"),
        nullable=True,
    )
    link_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    detached_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    detached_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    detached_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

#### Notas de archivos

- `FileAsset` es independiente y puede adjuntarse a expediente o documento
  administrativo, nunca a ambos en el mismo enlace.
- `storage_key` es único e interno; no se expone al cliente.
- `sha256` permite deduplicación posterior, pero no se declara unique todavía:
  el mismo contenido puede tener ciclo de vida y metadatos distintos.
- `FileAttachment` conserva historial de desvinculación con `detached_at`.
- Los índices parciales impiden dos archivos principales activos para el mismo
  destino.
- No se usa `entity_type/entity_id`.

### 9.11 Importaciones

#### Archivo: `backend/src/judicial_archive/modules/imports/models.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import (
    ImportFileStatus,
    ImportKind,
    ImportRowStatus,
    ImportSourceType,
    ImportStatus,
)
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class ImportBatch(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        check_in("import_kind", ImportKind, name="ck_import_batches_kind"),
        check_in("source_type", ImportSourceType, name="ck_import_batches_source"),
        check_in("status", ImportStatus, name="ck_import_batches_status"),
        CheckConstraint(
            "total_files >= 0 AND processed_files >= 0 "
            "AND total_rows >= 0 AND valid_rows >= 0 "
            "AND warning_rows >= 0 AND error_rows >= 0",
            name="ck_import_batches_non_negative_counts",
        ),
        CheckConstraint(
            "processed_files <= total_files",
            name="ck_import_batches_processed_files",
        ),
        CheckConstraint(
            "valid_rows + warning_rows + error_rows <= total_rows",
            name="ck_import_batches_row_counts",
        ),
        CheckConstraint(
            "status NOT IN ('READY', 'APPLYING', 'APPLIED') OR error_rows = 0",
            name="ck_import_batches_ready_without_errors",
        ),
        CheckConstraint(
            "status <> 'APPLIED' OR (applied_at IS NOT NULL AND applied_by IS NOT NULL)",
            name="ck_import_batches_applied_fields",
        ),
        CheckConstraint(
            "status <> 'FAILED' OR ("
            "failure_reason IS NOT NULL "
            "AND length(btrim(failure_reason)) > 0)",
            name="ck_import_batches_failure_reason",
        ),
        CheckConstraint(
            "approved_by IS NULL OR created_by IS NULL "
            "OR approved_by <> created_by "
            "OR (approval_exception_reason IS NOT NULL "
            "AND length(btrim(approval_exception_reason)) > 0)",
            name="ck_import_batches_separation",
        ),
        CheckConstraint(
            "idempotency_key IS NULL OR length(btrim(idempotency_key)) > 0",
            name="ck_import_batches_idempotency_key",
        ),
        Index("ix_import_batches_status", "status"),
        Index("ix_import_batches_created_at", "created_at"),
        Index(
            "uq_import_batches_idempotency",
            "created_by",
            "idempotency_key",
            unique=True,
            postgresql_where=text(
                "idempotency_key IS NOT NULL AND created_by IS NOT NULL"
            ),
        ),
    )

    import_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=ImportStatus.DRAFT.value,
        server_default=ImportStatus.DRAFT.value,
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_files: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    processed_files: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    total_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    valid_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    warning_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    error_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    applied_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    approval_exception_reason: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class ImportFile(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "import_files"
    __table_args__ = (
        UniqueConstraint("id", "batch_id", name="uq_import_files_id_batch"),
        UniqueConstraint(
            "batch_id",
            "file_asset_id",
            name="uq_import_files_batch_asset",
        ),
        check_in("source_type", ImportSourceType, name="ck_import_files_source"),
        check_in("status", ImportFileStatus, name="ck_import_files_status"),
        CheckConstraint(
            "rows_extracted >= 0",
            name="ck_import_files_rows_extracted",
        ),
        CheckConstraint(
            "page_count IS NULL OR page_count > 0",
            name="ck_import_files_page_count",
        ),
        CheckConstraint(
            "error IS NULL OR jsonb_typeof(error) = 'object'",
            name="ck_import_files_error_object",
        ),
        CheckConstraint(
            "status <> 'FAILED' OR error IS NOT NULL",
            name="ck_import_files_failed_error",
        ),
        CheckConstraint(
            "status <> 'EXTRACTED' OR extracted_at IS NOT NULL",
            name="ck_import_files_extracted_at",
        ),
        Index("ix_import_files_batch_id", "batch_id"),
        Index("ix_import_files_status", "status"),
    )

    batch_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("import_batches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    file_asset_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("file_assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=ImportFileStatus.PENDING.value,
        server_default=ImportFileStatus.PENDING.value,
    )
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rows_extracted: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    extracted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )


class ImportRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "import_rows"
    __table_args__ = (
        ForeignKeyConstraint(
            ["import_file_id", "batch_id"],
            ["import_files.id", "import_files.batch_id"],
            name="fk_import_rows_file_batch",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        check_in("status", ImportRowStatus, name="ck_import_rows_status"),
        CheckConstraint(
            "row_number > 0",
            name="ck_import_rows_row_number",
        ),
        CheckConstraint(
            "raw_data IS NULL OR jsonb_typeof(raw_data) = 'object'",
            name="ck_import_rows_raw_object",
        ),
        CheckConstraint(
            "normalized_data IS NULL OR jsonb_typeof(normalized_data) = 'object'",
            name="ck_import_rows_normalized_object",
        ),
        CheckConstraint(
            "errors IS NULL OR jsonb_typeof(errors) = 'array'",
            name="ck_import_rows_errors_array",
        ),
        CheckConstraint(
            "warnings IS NULL OR jsonb_typeof(warnings) = 'array'",
            name="ck_import_rows_warnings_array",
        ),
        CheckConstraint(
            "("
            "(target_box_id IS NOT NULL)::int "
            "+ (target_case_file_id IS NOT NULL)::int "
            "+ (target_administrative_document_id IS NOT NULL)::int"
            ") <= 1",
            name="ck_import_rows_at_most_one_target",
        ),
        CheckConstraint(
            "status <> 'APPLIED' OR ("
            "(target_box_id IS NOT NULL)::int "
            "+ (target_case_file_id IS NOT NULL)::int "
            "+ (target_administrative_document_id IS NOT NULL)::int"
            ") = 1",
            name="ck_import_rows_applied_target",
        ),
        CheckConstraint(
            "status <> 'APPLIED' OR (applied_at IS NOT NULL AND applied_by IS NOT NULL)",
            name="ck_import_rows_applied_fields",
        ),
        CheckConstraint(
            "status <> 'ERROR' OR errors IS NOT NULL",
            name="ck_import_rows_error_details",
        ),
        Index("ix_import_rows_batch_id", "batch_id"),
        Index("ix_import_rows_import_file_id", "import_file_id"),
        Index("ix_import_rows_status", "status"),
        UniqueConstraint(
            "import_file_id",
            "row_number",
            name="uq_import_rows_file_row",
        ),
    )

    batch_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), nullable=False
    )
    import_file_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), nullable=False
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    normalized_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ImportRowStatus.PENDING.value,
        server_default=ImportRowStatus.PENDING.value,
    )
    errors: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    warnings: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    target_box_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    target_case_file_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("case_files.id", ondelete="RESTRICT"),
        nullable=True,
    )
    target_administrative_document_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("administrative_documents.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    applied_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
```

#### Notas de importaciones

- `ImportBatch` no guarda filas; `ImportFile` y `ImportRow` lo hacen.
- La FK compuesta `(import_file_id, batch_id)` garantiza que una fila no
  pertenezca a un lote distinto de su archivo.
- Los destinos de una fila son FKs explícitas y excluyentes.
- Una fila `APPLIED` debe tener exactamente un destino y actor/fecha.
- El check de separación permite una excepción documentada, pero deja rastro
  para auditoría.
- No se permite aplicar un lote con errores.
- No se crea una tabla para el DOCX original; se representa con `FileAsset` y
  `ImportRow`, no como entidad de dominio.
- Las importaciones no se borran; se cancelan y conservan evidencia.

### 9.12 Resultados OCR

#### Archivo: `backend/src/judicial_archive/modules/ocr/models.py`

```python
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import OcrStatus
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class OcrResult(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "ocr_results"
    __table_args__ = (
        check_in("status", OcrStatus, name="ck_ocr_results_status"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_ocr_results_confidence_range",
        ),
        CheckConstraint(
            "metadata IS NULL OR jsonb_typeof(metadata) = 'object'",
            name="ck_ocr_results_metadata_object",
        ),
        CheckConstraint(
            "status <> 'ACCEPTED' OR (reviewed_at IS NOT NULL AND reviewed_by IS NOT NULL)",
            name="ck_ocr_results_accepted_fields",
        ),
        CheckConstraint(
            "status <> 'REJECTED' OR (reviewed_at IS NOT NULL AND reviewed_by IS NOT NULL)",
            name="ck_ocr_results_rejected_fields",
        ),
        CheckConstraint(
            "status NOT IN ('COMPLETED', 'ACCEPTED', 'REVIEW_REQUIRED') "
            "OR text IS NOT NULL",
            name="ck_ocr_results_completed_text",
        ),
        Index("ix_ocr_results_file_asset", "file_asset_id"),
        Index("ix_ocr_results_import_file", "import_file_id"),
        Index("ix_ocr_results_status", "status"),
    )

    file_asset_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("file_assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    import_file_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("import_files.id", ondelete="RESTRICT"),
        nullable=True,
    )
    engine_name: Mapped[str] = mapped_column(String(80), nullable=False)
    engine_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=OcrStatus.PENDING.value,
        server_default=OcrStatus.PENDING.value,
    )
    text: Mapped[str | None] = mapped_column(nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    page_number: Mapped[int | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
```

#### Notas de OCR

- Se guarda el texto y metadatos del motor, no el archivo procesado.
- La revisión humana es explícita.
- `confidence` usa `NUMERIC(5,4)` entre 0 y 1; no se usa `FLOAT` para evitar
  comparaciones imprecisas.
- `page_number` se deja como entero simple; si se procesan páginas múltiples,
  se crea una fila por página.
- OCR no modifica el expediente directamente; B9 define la aplicación.

### 9.13 Tareas asíncronas

#### Archivo: `backend/src/judicial_archive/modules/jobs/models.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import TaskStatus
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class TaskJob(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "task_jobs"
    __table_args__ = (
        check_in("status", TaskStatus, name="ck_task_jobs_status"),
        CheckConstraint(
            "attempts >= 0 AND max_attempts > 0 AND attempts <= max_attempts",
            name="ck_task_jobs_attempts",
        ),
        CheckConstraint(
            "progress IS NULL OR (progress >= 0 AND progress <= 100)",
            name="ck_task_jobs_progress",
        ),
        CheckConstraint(
            "payload IS NULL OR jsonb_typeof(payload) = 'object'",
            name="ck_task_jobs_payload_object",
        ),
        CheckConstraint(
            "result IS NULL OR jsonb_typeof(result) = 'object'",
            name="ck_task_jobs_result_object",
        ),
        CheckConstraint(
            "error IS NULL OR jsonb_typeof(error) = 'object'",
            name="ck_task_jobs_error_object",
        ),
        CheckConstraint(
            "status <> 'SUCCEEDED' OR finished_at IS NOT NULL",
            name="ck_task_jobs_succeeded_finished",
        ),
        CheckConstraint(
            "status <> 'FAILED' OR error IS NOT NULL",
            name="ck_task_jobs_failed_error",
        ),
        CheckConstraint(
            "idempotency_key IS NULL OR length(btrim(idempotency_key)) > 0",
            name="ck_task_jobs_idempotency_key",
        ),
        Index("ix_task_jobs_queue", "status", "scheduled_at"),
        Index("ix_task_jobs_type", "job_type"),
        Index(
            "uq_task_jobs_idempotency",
            "job_type",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    job_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=TaskStatus.PENDING.value,
        server_default=TaskStatus.PENDING.value,
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    progress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default=text("3")
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
```

#### Notas de tareas

- El esquema no depende de una librería concreta de colas.
- No se incluye bloqueo de fila ni `SELECT ... FOR UPDATE SKIP LOCKED` en B2;
  la estrategia concreta se implementa en B9.
- `idempotency_key` evita duplicar tareas del mismo tipo.
- El payload no debe contener secretos ni datos personales innecesarios.

### 9.14 Préstamos

#### Archivo: `backend/src/judicial_archive/modules/loans/models.py`

```python
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import LoanStatus
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class Loan(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "loans"
    __table_args__ = (
        check_in("status", LoanStatus, name="ck_loans_status"),
        CheckConstraint(
            "length(btrim(purpose)) > 0",
            name="ck_loans_purpose_not_empty",
        ),
        CheckConstraint(
            "status NOT IN ('APPROVED', 'DELIVERED', 'RETURNED') "
            "OR (approved_at IS NOT NULL AND approved_by IS NOT NULL)",
            name="ck_loans_approval_fields",
        ),
        CheckConstraint(
            "status NOT IN ('DELIVERED', 'RETURNED') "
            "OR (delivered_at IS NOT NULL AND delivered_by IS NOT NULL)",
            name="ck_loans_delivery_fields",
        ),
        CheckConstraint(
            "status <> 'RETURNED' "
            "OR (returned_at IS NOT NULL AND returned_by IS NOT NULL)",
            name="ck_loans_return_fields",
        ),
        CheckConstraint(
            "status <> 'CANCELLED' "
            "OR (cancelled_at IS NOT NULL "
            "AND cancellation_reason IS NOT NULL "
            "AND length(btrim(cancellation_reason)) > 0)",
            name="ck_loans_cancellation_fields",
        ),
        CheckConstraint(
            "status <> 'REJECTED' "
            "OR (rejected_at IS NOT NULL "
            "AND rejection_reason IS NOT NULL "
            "AND length(btrim(rejection_reason)) > 0)",
            name="ck_loans_rejection_fields",
        ),
        CheckConstraint(
            "approved_by IS NULL OR requested_by IS NULL "
            "OR approved_by <> requested_by "
            "OR (approval_exception_reason IS NOT NULL "
            "AND length(btrim(approval_exception_reason)) > 0)",
            name="ck_loans_approval_separation",
        ),
        CheckConstraint(
            "due_at IS NULL OR delivered_at IS NULL OR due_at >= delivered_at",
            name="ck_loans_due_after_delivery",
        ),
        CheckConstraint(
            "returned_at IS NULL OR delivered_at IS NULL OR returned_at >= delivered_at",
            name="ck_loans_return_after_delivery",
        ),
        CheckConstraint(
            "approved_at IS NULL OR approved_at >= requested_at",
            name="ck_loans_approval_after_request",
        ),
        Index("ix_loans_status", "status"),
        Index("ix_loans_requested_at", "requested_at"),
        Index("ix_loans_due_at", "due_at"),
    )

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=LoanStatus.REQUESTED.value,
        server_default=LoanStatus.REQUESTED.value,
    )
    purpose: Mapped[str] = mapped_column(String(1000), nullable=False)
    requested_by: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    returned_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    returned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejected_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    approval_exception_reason: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class LoanItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "loan_items"
    __table_args__ = (
        CheckConstraint(
            "("
            "(box_id IS NOT NULL AND case_file_id IS NULL)"
            " OR (box_id IS NULL AND case_file_id IS NOT NULL)"
            ")",
            name="ck_loan_items_one_target",
        ),
        CheckConstraint(
            "released_at IS NULL OR ("
            "release_reason IS NOT NULL "
            "AND length(btrim(release_reason)) > 0)",
            name="ck_loan_items_release_reason",
        ),
        CheckConstraint(
            "released_at IS NULL OR released_at >= created_at",
            name="ck_loan_items_release_after_creation",
        ),
        Index("ix_loan_items_loan_id", "loan_id"),
        Index(
            "uq_loan_items_open_box",
            "box_id",
            unique=True,
            postgresql_where=text("released_at IS NULL AND box_id IS NOT NULL"),
        ),
        Index(
            "uq_loan_items_open_case",
            "case_file_id",
            unique=True,
            postgresql_where=text("released_at IS NULL AND case_file_id IS NOT NULL"),
        ),
    )

    loan_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("loans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    box_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    case_file_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("case_files.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    release_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

#### Notas de préstamos

- Un ítem es una caja o un expediente, nunca ambos.
- Los índices parciales impiden dos ítems abiertos para el mismo recurso.
- `released_at` cierra el ítem tanto si el préstamo termina como si se cancela.
- El estado del préstamo no se deriva automáticamente de sus ítems; el servicio
  mantiene la coherencia transaccional.
- La entrega y devolución son actos separados y auditados.
- La separación de funciones se exige por check con excepción documentada.
- No se modela renovación en B2; si se aprueba, será una migración posterior.

### 9.15 Inventarios y hallazgos

#### Archivo: `backend/src/judicial_archive/modules/inventory/models.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import (
    FindingStatus,
    FindingType,
    InventoryScopeType,
    InventoryStatus,
)
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class InventorySession(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "inventory_sessions"
    __table_args__ = (
        check_in(
            "scope_type",
            InventoryScopeType,
            name="ck_inventory_sessions_scope_type",
        ),
        check_in("status", InventoryStatus, name="ck_inventory_sessions_status"),
        CheckConstraint(
            "scanned_count >= 0 AND expected_count >= 0",
            name="ck_inventory_sessions_counts",
        ),
        CheckConstraint(
            "("
            "(scope_type = 'AREA' AND area_id IS NOT NULL "
            "AND shelf_id IS NULL AND tray_id IS NULL "
            "AND start_position_id IS NULL AND end_position_id IS NULL "
            "AND box_id IS NULL)"
            " OR (scope_type = 'SHELF' AND area_id IS NULL "
            "AND shelf_id IS NOT NULL AND tray_id IS NULL "
            "AND start_position_id IS NULL AND end_position_id IS NULL "
            "AND box_id IS NULL)"
            " OR (scope_type = 'TRAY' AND area_id IS NULL "
            "AND shelf_id IS NULL AND tray_id IS NOT NULL "
            "AND start_position_id IS NULL AND end_position_id IS NULL "
            "AND box_id IS NULL)"
            " OR (scope_type = 'POSITION_RANGE' AND area_id IS NULL "
            "AND shelf_id IS NULL AND tray_id IS NULL "
            "AND start_position_id IS NOT NULL AND end_position_id IS NOT NULL "
            "AND box_id IS NULL)"
            " OR (scope_type = 'BOX' AND area_id IS NULL "
            "AND shelf_id IS NULL AND tray_id IS NULL "
            "AND start_position_id IS NULL AND end_position_id IS NULL "
            "AND box_id IS NOT NULL)"
            ")",
            name="ck_inventory_sessions_scope_columns",
        ),
        CheckConstraint(
            "status <> 'CLOSED' OR closed_at IS NOT NULL",
            name="ck_inventory_sessions_closed_at",
        ),
        CheckConstraint(
            "summary IS NULL OR jsonb_typeof(summary) = 'object'",
            name="ck_inventory_sessions_summary_object",
        ),
        CheckConstraint(
            "length(btrim(code)) > 0",
            name="ck_inventory_sessions_code_not_empty",
        ),
        Index("ix_inventory_sessions_status", "status"),
        Index("ix_inventory_sessions_scope", "scope_type"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    scope_type: Mapped[str] = mapped_column(String(24), nullable=False)
    area_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("areas.id", ondelete="RESTRICT"),
        nullable=True,
    )
    shelf_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("shelves.id", ondelete="RESTRICT"),
        nullable=True,
    )
    tray_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("trays.id", ondelete="RESTRICT"),
        nullable=True,
    )
    start_position_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    end_position_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    box_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=InventoryStatus.DRAFT.value,
        server_default=InventoryStatus.DRAFT.value,
    )
    responsible_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    expected_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    scanned_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class InventoryFinding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inventory_findings"
    __table_args__ = (
        check_in("finding_type", FindingType, name="ck_inventory_findings_type"),
        check_in("finding_status", FindingStatus, name="ck_inventory_findings_status"),
        CheckConstraint(
            "expected_data IS NULL OR jsonb_typeof(expected_data) = 'object'",
            name="ck_inventory_findings_expected_object",
        ),
        CheckConstraint(
            "observed_data IS NULL OR jsonb_typeof(observed_data) = 'object'",
            name="ck_inventory_findings_observed_object",
        ),
        CheckConstraint(
            "finding_status NOT IN ('RESOLVED', 'ACCEPTED_DIFFERENCE') "
            "OR (resolution IS NOT NULL "
            "AND length(btrim(resolution)) > 0 "
            "AND resolved_at IS NOT NULL AND resolved_by IS NOT NULL)",
            name="ck_inventory_findings_resolution_fields",
        ),
        Index("ix_inventory_findings_session", "session_id", "finding_status"),
        Index("ix_inventory_findings_box", "box_id"),
    )

    session_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("inventory_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    finding_type: Mapped[str] = mapped_column(String(32), nullable=False)
    finding_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=FindingStatus.OPEN.value,
        server_default=FindingStatus.OPEN.value,
    )
    box_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    expected_position_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    observed_position_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    expected_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    observed_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
```

#### Notas de inventarios

- El alcance es excluyente y se comprueba en base.
- El inventario no altera ubicaciones por sí mismo; registra hallazgos.
- La resolución exige texto, actor y fecha.
- `summary` queda como JSONB para el cierre; no sustituye a los hallazgos.
- Los conteos son informativos y deben cuadrar con las filas en el servicio.
- No se añade una tabla de lecturas individuales en B2; B10 evalúa si el volumen
  lo requiere.

### 9.16 Holds legales y solicitudes de borrado

#### Archivo: `backend/src/judicial_archive/modules/retention/models.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from judicial_archive.core.enums import (
    DeletionStatus,
    DeletionTargetType,
    LegalHoldStatus,
    LegalHoldTargetType,
)
from judicial_archive.db.base import Base
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
)


class LegalHold(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "legal_holds"
    __table_args__ = (
        check_in(
            "target_type",
            LegalHoldTargetType,
            name="ck_legal_holds_target_type",
        ),
        check_in("status", LegalHoldStatus, name="ck_legal_holds_status"),
        CheckConstraint(
            "("
            "(target_type = 'BOX' AND box_id IS NOT NULL "
            "AND case_file_id IS NULL AND file_asset_id IS NULL)"
            " OR (target_type = 'CASE_FILE' AND box_id IS NULL "
            "AND case_file_id IS NOT NULL AND file_asset_id IS NULL)"
            " OR (target_type = 'FILE_ASSET' AND box_id IS NULL "
            "AND case_file_id IS NULL AND file_asset_id IS NOT NULL)"
            ")",
            name="ck_legal_holds_one_target",
        ),
        CheckConstraint(
            "length(btrim(reason)) > 0",
            name="ck_legal_holds_reason_not_empty",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_legal_holds_effective_range",
        ),
        CheckConstraint(
            "status <> 'RELEASED' "
            "OR (released_at IS NOT NULL AND released_by IS NOT NULL "
            "AND release_reason IS NOT NULL "
            "AND length(btrim(release_reason)) > 0)",
            name="ck_legal_holds_release_fields",
        ),
        Index(
            "ix_legal_holds_box_active",
            "box_id",
            postgresql_where=text("status = 'ACTIVE' AND box_id IS NOT NULL"),
        ),
        Index(
            "ix_legal_holds_case_active",
            "case_file_id",
            postgresql_where=text("status = 'ACTIVE' AND case_file_id IS NOT NULL"),
        ),
        Index(
            "ix_legal_holds_file_active",
            "file_asset_id",
            postgresql_where=text("status = 'ACTIVE' AND file_asset_id IS NOT NULL"),
        ),
    )

    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    box_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    case_file_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("case_files.id", ondelete="RESTRICT"),
        nullable=True,
    )
    file_asset_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("file_assets.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    legal_basis: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=LegalHoldStatus.ACTIVE.value,
        server_default=LegalHoldStatus.ACTIVE.value,
    )
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    released_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    release_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class DeletionRequest(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "deletion_requests"
    __table_args__ = (
        check_in(
            "target_type",
            DeletionTargetType,
            name="ck_deletion_requests_target_type",
        ),
        check_in("status", DeletionStatus, name="ck_deletion_requests_status"),
        CheckConstraint(
            "("
            "(target_type = 'BOX' AND box_id IS NOT NULL "
            "AND case_file_id IS NULL AND file_asset_id IS NULL)"
            " OR (target_type = 'CASE_FILE' AND box_id IS NULL "
            "AND case_file_id IS NOT NULL AND file_asset_id IS NULL)"
            " OR (target_type = 'FILE_ASSET' AND box_id IS NULL "
            "AND case_file_id IS NULL AND file_asset_id IS NOT NULL)"
            ")",
            name="ck_deletion_requests_one_target",
        ),
        CheckConstraint(
            "length(btrim(reason)) > 0",
            name="ck_deletion_requests_reason_not_empty",
        ),
        CheckConstraint(
            "status NOT IN ('UNDER_REVIEW', 'APPROVED', 'SCHEDULED', "
            "'EXECUTING', 'COMPLETED', 'FAILED') "
            "OR (reviewed_at IS NOT NULL AND reviewed_by IS NOT NULL)",
            name="ck_deletion_requests_review_fields",
        ),
        CheckConstraint(
            "status NOT IN ('APPROVED', 'SCHEDULED', 'EXECUTING', 'COMPLETED') "
            "OR (approved_at IS NOT NULL AND approved_by IS NOT NULL)",
            name="ck_deletion_requests_approval_fields",
        ),
        CheckConstraint(
            "status <> 'REJECTED' "
            "OR (rejected_at IS NOT NULL AND rejected_by IS NOT NULL "
            "AND rejection_reason IS NOT NULL "
            "AND length(btrim(rejection_reason)) > 0)",
            name="ck_deletion_requests_rejection_fields",
        ),
        CheckConstraint(
            "status <> 'CANCELLED' "
            "OR (cancelled_at IS NOT NULL AND cancelled_by IS NOT NULL "
            "AND cancellation_reason IS NOT NULL "
            "AND length(btrim(cancellation_reason)) > 0)",
            name="ck_deletion_requests_cancellation_fields",
        ),
        CheckConstraint(
            "status <> 'COMPLETED' "
            "OR (executed_at IS NOT NULL AND executed_by IS NOT NULL "
            "AND evidence_file_id IS NOT NULL)",
            name="ck_deletion_requests_completion_fields",
        ),
        CheckConstraint(
            "approved_by IS NULL OR approved_by <> requested_by",
            name="ck_deletion_requests_approver_separation",
        ),
        CheckConstraint(
            "executed_by IS NULL OR executed_by <> requested_by",
            name="ck_deletion_requests_executor_separation",
        ),
        CheckConstraint(
            "executed_at IS NULL OR approved_at IS NULL OR executed_at >= approved_at",
            name="ck_deletion_requests_execution_after_approval",
        ),
        CheckConstraint(
            "execution_result IS NULL OR jsonb_typeof(execution_result) = 'object'",
            name="ck_deletion_requests_result_object",
        ),
        Index("ix_deletion_requests_status", "status"),
        Index(
            "ix_deletion_requests_box_active",
            "box_id",
            postgresql_where=text(
                "box_id IS NOT NULL AND status NOT IN "
                "('COMPLETED', 'REJECTED', 'CANCELLED')"
            ),
        ),
        Index(
            "ix_deletion_requests_case_active",
            "case_file_id",
            postgresql_where=text(
                "case_file_id IS NOT NULL AND status NOT IN "
                "('COMPLETED', 'REJECTED', 'CANCELLED')"
            ),
        ),
        Index(
            "ix_deletion_requests_file_active",
            "file_asset_id",
            postgresql_where=text(
                "file_asset_id IS NOT NULL AND status NOT IN "
                "('COMPLETED', 'REJECTED', 'CANCELLED')"
            ),
        ),
    )

    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    box_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    case_file_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("case_files.id", ondelete="RESTRICT"),
        nullable=True,
    )
    file_asset_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("file_assets.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=DeletionStatus.REQUESTED.value,
        server_default=DeletionStatus.REQUESTED.value,
    )
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    requested_by: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    executed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    evidence_file_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("file_assets.id", ondelete="RESTRICT"),
        nullable=True,
    )
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejected_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
```

#### Notas de retención

- Los holds y las solicitudes de borrado son entidades distintas.
- Una solicitud no puede completarse sin evidencia.
- La comprobación de holds activos antes de aprobar o ejecutar es una regla de
  servicio de B7, reforzada por pruebas de integración.
- No se añade un trigger que bloquee automáticamente todo borrado: el borrado
  lógico no destruye filas y el borrado físico está fuera del flujo normal.
- La separación solicitante/aprobador/ejecutor es obligatoria en B2, sin
  excepciones. Si el negocio necesita una excepción, se aprueba antes de
  implementar y se modifica este check con migración.
- `evidence_file_id` apunta a un `FileAsset` ya registrado; no se guarda una ruta
  externa.

### 9.17 Agregador de metadatos

#### Archivo: `backend/src/judicial_archive/models.py`

```python
from __future__ import annotations

from judicial_archive.modules.administrative_documents import (
    models as administrative_documents_models,
)
from judicial_archive.modules.audit import models as audit_models
from judicial_archive.modules.auth import models as auth_models
from judicial_archive.modules.boxes import models as boxes_models
from judicial_archive.modules.case_files import models as case_files_models
from judicial_archive.modules.courts import models as courts_models
from judicial_archive.modules.files import models as files_models
from judicial_archive.modules.imports import models as imports_models
from judicial_archive.modules.inventory import models as inventory_models
from judicial_archive.modules.jobs import models as jobs_models
from judicial_archive.modules.loans import models as loans_models
from judicial_archive.modules.locations import models as locations_models
from judicial_archive.modules.ocr import models as ocr_models
from judicial_archive.modules.qr import models as qr_models
from judicial_archive.modules.retention import models as retention_models
from judicial_archive.modules.users import models as users_models

__all__ = [
    "administrative_documents_models",
    "audit_models",
    "auth_models",
    "boxes_models",
    "case_files_models",
    "courts_models",
    "files_models",
    "imports_models",
    "inventory_models",
    "jobs_models",
    "loans_models",
    "locations_models",
    "ocr_models",
    "qr_models",
    "retention_models",
    "users_models",
]
```

#### Notas del agregador

- Se importan los módulos, no las clases, para que el registro de mapeos ocurra
  aunque no se use cada clase en este archivo.
- Alembic debe importar `judicial_archive.models` antes de leer
  `Base.metadata`.
- No se importa el agregador desde `db/`, para respetar la dirección de
  dependencias.
- Cada carpeta de módulo nueva requiere `__init__.py` vacío si el proyecto no
  usa namespace packages. Mantener el mismo estilo que el resto del backend.

---

## 10. Diccionario físico de tablas

### 10.1 Inventario de tablas

| # | Tabla | Propósito | Identidad / unicidad | Baja o historia |
|---:|---|---|---|---|
| 1 | `roles` | Roles de autorización | UUID; `code` único | `status`; no se borra |
| 2 | `permissions` | Permisos granulares | UUID; `code` único | Catálogo; no se borra |
| 3 | `users` | Cuentas | UUID; username/email normalizados únicos | `status`; no se borra |
| 4 | `user_roles` | Asociación usuario-rol | PK compuesta | Historial mínimo |
| 5 | `role_permissions` | Asociación rol-permiso | PK compuesta | Historial mínimo |
| 6 | `user_sessions` | Sesiones | UUID; hash de token único | `revoked_at` |
| 7 | `audit_events` | Auditoría | UUID | Append-only |
| 8 | `courts` | Tribunales | UUID; código no único | `status` |
| 9 | `identifier_format_profiles` | Perfiles de formato | UUID | `is_active` |
| 10 | `resolution_types` | Tipos de resolución | UUID; código único | `status` |
| 11 | `numbering_policies` | Políticas de numeración | UUID; código y secuencia únicos | `is_active` |
| 12 | `retention_policies` | Retención | UUID; código único | `is_active` |
| 13 | `system_settings` | Configuración | UUID; clave única | `updated_at` |
| 14 | `party_roles` | Roles de parte | UUID; código único | `status` |
| 15 | `areas` | Zonas físicas | UUID; código único | `status` |
| 16 | `shelves` | Anaqueles | UUID; único por área y código | `status` |
| 17 | `trays` | Bandejas/niveles | UUID; único por anaquel y código | `status` |
| 18 | `positions` | Posiciones | UUID; único por bandeja y código | `status` |
| 19 | `position_blocks` | Bloqueos de rango | UUID | `cancelled_at` |
| 20 | `boxes` | Cajas | UUID; número visible único | `lifecycle_status` |
| 21 | `box_number_history` | Cambios de número | UUID | Inmutable |
| 22 | `box_movements` | Traslados y movimientos | UUID | Estado + timestamps |
| 23 | `box_labels` | Etiquetas QR | UUID; hash único | `revoked_at` |
| 24 | `case_files` | Expedientes | UUID; NUC no único | `lifecycle_status` + lógico |
| 25 | `case_file_identifier_history` | Correcciones de identificadores | UUID | Inmutable |
| 26 | `persons` | Personas | UUID | Lógico |
| 27 | `case_parties` | Relación expediente-persona | UUID | `CASCADE` de asociación |
| 28 | `administrative_documents` | Documentos administrativos | UUID | `lifecycle_status` + lógico |
| 29 | `file_assets` | Archivos originales | UUID; `storage_key` único | `status` + lógico |
| 30 | `file_attachments` | Vínculo archivo-destino | UUID | `detached_at` |
| 31 | `import_batches` | Lotes de importación | UUID | Estado, no borrado |
| 32 | `import_files` | Archivos del lote | UUID; único por lote | Estado |
| 33 | `import_rows` | Filas extraídas | UUID; único por archivo y fila | Estado |
| 34 | `ocr_results` | Resultados OCR | UUID | Estado |
| 35 | `task_jobs` | Tareas asíncronas | UUID; idempotencia parcial | Estado |
| 36 | `loans` | Préstamos | UUID | Estado |
| 37 | `loan_items` | Recursos prestados | UUID | `released_at` |
| 38 | `inventory_sessions` | Conciliaciones | UUID; código único | Estado |
| 39 | `inventory_findings` | Hallazgos | UUID | `finding_status` |
| 40 | `legal_holds` | Holds legales | UUID | `status` |
| 41 | `deletion_requests` | Solicitudes de borrado | UUID | Estado |

### 10.2 Regla de borrado

| Tipo de tabla | Borrado permitido |
|---|---|
| Auditoría | Ninguno |
| Historia de identificadores, números y movimientos | Ninguno directo |
| Entidades de negocio | Lógico o estado archivístico |
| Asociaciones sin historia | Físico solo si la entidad principal se elimina en un flujo autorizado |
| Catálogos | Desactivación, no borrado |
| Sesiones | Revocación y eventual purga por retención |
| Tareas | Purga operativa solo con retención aprobada y auditoría |

No se implementa purga automática en B2.

---

## 11. Matriz de restricciones críticas

### 11.1 Cajas

| Regla | Mecanismo |
|---|---|
| Número visible no reutilizable | `UNIQUE (visible_number)` + secuencia |
| Número global | `box_visible_number_seq` desde 4402 |
| Tipo excluyente | `CHECK box_type IN (...)` |
| Destino de FK compuesta | `UNIQUE (id, box_type)` |
| Una caja en una posición | `UNIQUE (current_position_id)` parcial |
| No mezclar contenido | FK compuesta desde `case_files` y `administrative_documents` |
| No destruir con posición | `CHECK` |
| No cambiar identidad con contenido | Trigger |
| No préstamo doble | Índice parcial en `loan_items` |

### 11.2 Expedientes y documentos

| Regla | Mecanismo |
|---|---|
| NUC textual con ceros y guiones | `VARCHAR`, nunca entero |
| Duplicados de NUC posibles | Sin unique inicial; índice de búsqueda |
| Búsqueda por últimos cinco | Columna generada `nuc_suffix5` |
| Fechas parciales | Componentes + precisión + checks |
| Caja de expedientes | FK compuesta + check de tipo |
| Caja administrativa | FK compuesta + check de tipo |
| Una persona por relación | Datos relacionales, no texto separado |
| Documento administrativo con mes opcional | Columnas separadas |

### 11.3 Archivos e importaciones

| Regla | Mecanismo |
|---|---|
| Un archivo, un enlace, un destino | Check de destino único |
| Un principal activo por destino | Índices únicos parciales |
| Historial de desvinculación | `detached_at` y motivo |
| Fila ligada a su lote | FK compuesta `(import_file_id, batch_id)` |
| Fila aplicada con destino | Check de destino exacto |
| Lote listo sin errores | Check de conteos y estado |
| Importación idempotente | `created_by + idempotency_key` parcial |

### 11.4 Préstamos, inventario y retención

| Regla | Mecanismo |
|---|---|
| Ítem caja o expediente | Check de exclusividad |
| Préstamo abierto único | Índices únicos parciales |
| Separación de aprobación | Check con excepción documentada |
| Alcance de inventario único | Check de columnas |
| Resolución de hallazgo con evidencia | Check de campos |
| Hold con un solo objetivo | Check de objetivo |
| Solicitud de borrado con un solo objetivo | Check de objetivo |
| Doble control de borrado | Checks de separación |
| Borrado completado con evidencia | Check de finalización |

### 11.5 Auditoría

| Regla | Mecanismo |
|---|---|
| Solo inserción | Trigger `BEFORE UPDATE/DELETE` y `BEFORE TRUNCATE` |
| Actor identificable | `CHECK` para actor `USER` |
| Datos JSON válidos | `CHECK jsonb_typeof` |
| Consulta por entidad | Índice compuesto |
| Consulta por actor y fecha | Índice compuesto |

---

## 12. Índices y rendimiento inicial

### 12.1 Índices obligatorios

| Tabla | Índice | Motivo |
|---|---|---|
| `users` | `username_normalized`, `email_normalized` unique | Login |
| `users` | `status` | Administración |
| `user_sessions` | `token_hash` unique | Validación |
| `user_sessions` | `user_id`, `absolute_expires_at` | Revocación y limpieza |
| `audit_events` | `(entity_type, entity_id, occurred_at)` | Historia por entidad |
| `audit_events` | `(actor_user_id, occurred_at)` | Actividad por usuario |
| `audit_events` | `request_id` | Correlación |
| `courts` | `status`, `name` | Catálogo |
| `identifier_format_profiles` | `(court_id, identifier_kind)` parcial activo | Validación |
| `case_files` | `(court_id, nuc_normalized)` | Búsqueda exacta |
| `case_files` | `nuc_suffix5` | Búsqueda por últimos cinco |
| `case_files` | `box_id` | Contenido de caja |
| `case_files` | `year` | Filtro |
| `case_files` | `lifecycle_status`, `verification_status` | Filtros |
| `persons` | `normalized_name` | Búsqueda |
| `persons` | `identification_number` | Búsqueda |
| `boxes` | `visible_number` unique | Identificación |
| `boxes` | `(court_id, year, box_type)` | Filtros |
| `boxes` | `current_position_id` único parcial | Ocupación |
| `boxes` | `lifecycle_status`, `custody_status` | Operación |
| `box_movements` | `(box_id, occurred_at)` | Historial |
| `file_assets` | `sha256` | Deduplicación y verificación |
| `file_attachments` | `file_asset_id`, `case_file_id`, `administrative_document_id` | Navegación |
| `import_rows` | `(import_file_id, row_number)` unique | Integridad |
| `ocr_results` | `file_asset_id`, `status` | Revisión |
| `task_jobs` | `(status, scheduled_at)` | Cola |
| `loans` | `status`, `due_at` | Operación y alertas |
| `inventory_findings` | `(session_id, finding_status)` | Cierre |
| `legal_holds` | objetivos parciales activos | Bloqueo |

### 12.2 Índices que no se crean todavía

- Trigramas sobre nombres y títulos.
- `GIN` de texto completo.
- Índices de expresiones de fecha.
- Índices de columnas JSONB sin consulta definida.
- Índices de bajo uso solo porque "podrían servir".

Se añadirán en B8/B14 con consultas y planes reales.

### 12.3 Criterio de rendimiento

No se declara una meta de latencia en B2. Se exige:

1. Que las consultas de integridad y claves tengan índice.
2. Que no haya índices duplicados.
3. Que `EXPLAIN (ANALYZE, BUFFERS)` se revise en B8 con volumen representativo.
4. Que las búsquedas por NUC exacto y últimos cinco no hagan `seq scan` con
   datos de prueba suficientes.

---

## 13. Alembic

### 13.1 Ajuste de `backend/alembic/env.py`

Sustituir el contenido por:

```python
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

import judicial_archive.models  # noqa: F401
from judicial_archive.core.config import get_settings
from judicial_archive.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

_url = config.get_main_option("sqlalchemy.url")
if not _url:
    _url = str(get_settings().database_url)
config.set_main_option("sqlalchemy.url", _url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

#### Por qué

- El import del agregador registra las 41 tablas antes de leer la metadata.
- La URL inyectada por pruebas o CLI tiene prioridad sobre `.env`.
- El escape de `%` evita que ConfigParser interprete la URL.
- No se cambia a motor async: Alembic 1.20 con psycopg síncrono es suficiente y
  estable.
- No se usa `render_as_batch`; PostgreSQL no lo necesita.

### 13.2 Crear la revisión inicial

Con PostgreSQL vacío y el entorno cargado:

```powershell
cd backend
$env:SGA_DATABASE_URL = "postgresql+psycopg://sga_dev:CAMBIAR@localhost:5432/sga_dev"
uv run alembic current
uv run alembic revision --autogenerate -m "initial schema"
```

`get_settings()` exige también `SGA_SECRET_KEY` y `SGA_REDIS_URL`. Si no hay un
`.env` con esos valores, expórtalos en la sesión antes de ejecutar Alembic; no
los escribas en el repositorio. La URL inyectada con `SGA_DATABASE_URL` tiene
prioridad sobre la de `.env`.

Comprobaciones inmediatas:

1. La revisión se creó en `alembic/versions/`.
2. `down_revision` es `None`.
3. Están las 41 tablas.
4. Están todos los `CHECK` con nombre.
5. Están los índices parciales.
6. Están las FK compuestas.
7. Están las columnas generadas.
8. No se generaron tablas de otros esquemas.
9. No se incluyeron datos.

Renombrar el archivo a:

```text
backend/alembic/versions/20261026_0001_initial_schema.py
```

Ajustar los identificadores:

```python
revision: str = "20261026_0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None
```

### 13.3 Añadir secuencia y triggers

Al final de la función `upgrade()` generada, antes de que termine, añadir:

```python
    _create_box_number_sequence()
    _create_schema_functions()
    _create_schema_triggers()
```

Al inicio de la función `downgrade()` generada, antes de los `drop_table`,
añadir:

```python
    _drop_schema_triggers()
    _drop_schema_functions()
    _drop_box_number_sequence()
```

Añadir las funciones auxiliares al final del archivo de migración:

```python
BOX_NUMBER_SEQUENCE = "box_visible_number_seq"
UPDATED_AT_TABLES = (
    "roles",
    "permissions",
    "users",
    "courts",
    "identifier_format_profiles",
    "resolution_types",
    "numbering_policies",
    "retention_policies",
    "system_settings",
    "party_roles",
    "areas",
    "shelves",
    "trays",
    "positions",
    "position_blocks",
    "boxes",
    "box_movements",
    "case_files",
    "persons",
    "case_parties",
    "administrative_documents",
    "file_assets",
    "file_attachments",
    "import_batches",
    "import_files",
    "ocr_results",
    "task_jobs",
    "loans",
    "inventory_sessions",
    "inventory_findings",
    "legal_holds",
    "deletion_requests",
)


def _create_box_number_sequence() -> None:
    op.execute(
        "CREATE SEQUENCE box_visible_number_seq "
        "AS BIGINT "
        "INCREMENT BY 1 "
        "MINVALUE 1 "
        "START WITH 4402 "
        "CACHE 1 "
        "NO CYCLE"
    )


def _drop_box_number_sequence() -> None:
    op.execute("DROP SEQUENCE IF EXISTS box_visible_number_seq")


def _create_schema_functions() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sga_set_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at := now();
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sga_audit_append_only()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events es append-only'
                USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sga_guard_box_identity()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF OLD.box_type IS DISTINCT FROM NEW.box_type
               OR OLD.court_id IS DISTINCT FROM NEW.court_id
               OR OLD.year IS DISTINCT FROM NEW.year
            THEN
                IF EXISTS (SELECT 1 FROM case_files WHERE box_id = OLD.id)
                   OR EXISTS (
                       SELECT 1 FROM administrative_documents
                       WHERE box_id = OLD.id
                   )
                THEN
                    RAISE EXCEPTION
                        'No se puede cambiar tribunal, año o tipo de una caja con contenido'
                        USING ERRCODE = 'integrity_constraint_violation';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )


def _create_schema_triggers() -> None:
    for table_name in UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_set_updated_at "
            f"BEFORE UPDATE ON {table_name} "
            "FOR EACH ROW EXECUTE FUNCTION sga_set_updated_at()"
        )

    op.execute(
        "CREATE TRIGGER trg_audit_events_append_only "
        "BEFORE UPDATE OR DELETE ON audit_events "
        "FOR EACH ROW EXECUTE FUNCTION sga_audit_append_only()"
    )
    op.execute(
        "CREATE TRIGGER trg_audit_events_no_truncate "
        "BEFORE TRUNCATE ON audit_events "
        "FOR EACH STATEMENT EXECUTE FUNCTION sga_audit_append_only()"
    )
    op.execute(
        "CREATE TRIGGER trg_boxes_identity_guard "
        "BEFORE UPDATE ON boxes "
        "FOR EACH ROW EXECUTE FUNCTION sga_guard_box_identity()"
    )


def _drop_schema_triggers() -> None:
    for table_name in UPDATED_AT_TABLES:
        op.execute(
            f"DROP TRIGGER IF EXISTS trg_{table_name}_set_updated_at ON {table_name}"
        )
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_append_only ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_truncate ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS trg_boxes_identity_guard ON boxes")


def _drop_schema_functions() -> None:
    op.execute("DROP FUNCTION IF EXISTS sga_guard_box_identity()")
    op.execute("DROP FUNCTION IF EXISTS sga_audit_append_only()")
    op.execute("DROP FUNCTION IF EXISTS sga_set_updated_at()")
```

### 13.4 Orden y dependencias

El orden de creación generado por Alembic debe respetar:

1. `users`, `roles`, `permissions`.
2. `courts`, catálogos.
3. `areas`, `shelves`, `trays`, `positions`.
4. `boxes` (depende de tribunales, posiciones y políticas).
5. `case_files`, `persons`, `party_roles`, `case_parties`.
6. `administrative_documents`.
7. `file_assets`, `file_attachments`.
8. `import_batches`, `import_files`, `import_rows`.
9. `ocr_results`, `task_jobs`.
10. `loans`, `loan_items`.
11. `inventory_sessions`, `inventory_findings`.
12. `legal_holds`, `deletion_requests`.
13. `box_number_history`, `box_movements`, `box_labels`.

Alembic resuelve el orden por FK. Si genera un ciclo, revisar el modelo; no
usar `use_alter=True` salvo que exista una razón documentada y aprobada.

### 13.5 Revisión manual obligatoria

Antes de aplicar:

```powershell
git diff -- backend/alembic/versions
New-Item -ItemType Directory -Force -Path ..\var | Out-Null
uv run alembic upgrade head --sql > ..\var\migration_b2.sql
```

Revisar en el SQL:

- `CREATE SEQUENCE`.
- `CREATE FUNCTION`.
- `CREATE TRIGGER`.
- `CREATE UNIQUE INDEX ... WHERE`.
- `GENERATED ALWAYS AS ... STORED`.
- FK compuestas con dos columnas.
- `ON DELETE RESTRICT`.
- Checks de fecha parcial.
- Checks de objetivo único.
- Checks de separación de funciones.

No aceptar una migración que:

- cree usuarios;
- inserte cajas, expedientes o archivos;
- use `DROP ... CASCADE` sin justificación;
- elimine columnas de B1;
- cree un `ENUM` nativo no previsto;
- use `MAX(number) + 1`;
- cree una tabla sin PK;
- deje un `CHECK` sin nombre.

### 13.6 Verificación

```powershell
uv run alembic upgrade head
uv run alembic current
uv run alembic check
uv run alembic history --verbose
```

Resultado esperado:

- `current` muestra `20261026_0001 (head)`.
- `check` termina con `No new upgrade operations detected.`
- `history` muestra una sola revisión inicial.

Si `check` detecta diferencias:

1. No aplicar en entornos compartidos.
2. Corregir modelos o migración.
3. Regenerar la revisión inicial solo si aún no se aplicó en un entorno
   compartido.
4. Si ya se aplicó, crear una migración correctiva.

### 13.7 Reversión

```powershell
uv run alembic downgrade base
uv run alembic current
```

Resultado esperado:

- no quedan tablas del esquema;
- no quedan triggers ni funciones;
- no queda la secuencia;
- `current` no muestra revisión.

La reversión inicial es destructiva. Solo se ejecuta en una base desechable o
con respaldo verificado. En producción, la reversión de una migración con datos
requiere un plan específico; no se usa `downgrade base`.

---

## 14. Semillas idempotentes

### 14.1 Reglas

- No se crean usuarios ni contraseñas.
- No se cargan cajas, expedientes, personas ni archivos.
- No se inventan capacidades de anaquel.
- No se crean posiciones sin nomenclatura confirmada.
- Sí se cargan catálogos confirmados y configuración mínima.
- La ejecución repetida no duplica ni sobrescribe cambios manuales.
- La semilla usa bloqueo asesor transaccional para evitar carreras.
- La semilla no depende del orden de ejecución de otras fases.

### 14.2 Datos exactos

| Grupo | Datos |
|---|---|
| Roles | `ADMINISTRADOR`, `SUPERVISOR`, `ARCHIVISTA`, `DIGITALIZADOR`, `CONSULTA` |
| Permisos | Ninguno en B2 |
| Áreas | A, B, C, D, O |
| Anaqueles | A1-A9, B1-B8, C1-C6, D1-D13, O1-O3 (39) |
| Tribunal 102 | Corte de Apelación, código `102`, activo |
| Tribunal 106 | Primera Cámara Penal del Juzgado de Primera Instancia, código `106`, inactivo |
| Tribunal 107-A | Segunda Cámara Penal del Juzgado de Primera Instancia, código `107`, inactivo |
| Tribunal 107-B | Juzgado de Primera Instancia Unipersonal, código `107`, inactivo provisional |
| Tribunal 589-A | Juzgado de Instrucción, código `589`, inactivo provisional |
| Tribunal 589-B | Juzgado de Instrucción en Atención Permanente, código `589`, inactivo provisional |
| Tribunal 107-01 | Tribunal Ejecución de la Pena, código `107-01`, inactivo provisional |
| Tribunal 107-02 | Tribunal Colegiado de Primera Instancia, código `107-02`, inactivo provisional |
| Rol de parte | `IMPUTADO` |
| Política de numeración | Global, secuencia `box_visible_number_seq`, inicio 4402, paso 1, sin reinicio |
| Configuración | `system.timezone = America/Santo_Domingo` |

#### Decisión sobre estados "por confirmar"

B1 indica que varios tribunales están "por confirmar", pero el estado de
catálogo solo admite `ACTIVE` e `INACTIVE`. Para no inventar que están activos,
se precargan como `INACTIVE` con una nota de estado provisional. Siguen siendo
editables y conservan su nombre y código. Esta decisión es reversible y debe
confirmarse en B5.

#### Decisión sobre códigos

El código persistido es el código bruto confirmado: `589`, `102`, `106`, `107`,
`107-01`, `107-02`. Las referencias `CT-*` son identificadores documentales de
B1 y no se guardan como código.

### 14.3 Archivo: `backend/src/judicial_archive/db/seed.py`

```python
from __future__ import annotations

import asyncio

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.config import get_settings
from judicial_archive.core.enums import CatalogStatus
from judicial_archive.db.base import Base
from judicial_archive.db.session import Database
from judicial_archive.modules.courts.models import (
    Court,
    NumberingPolicy,
    PartyRole,
    SystemSetting,
)
from judicial_archive.modules.locations.models import Area, Shelf
from judicial_archive.modules.users.models import Role

SEED_LOCK_KEY = 20261026

ROLES = (
    ("ADMINISTRADOR", "Administrador"),
    ("SUPERVISOR", "Supervisor de archivo"),
    ("ARCHIVISTA", "Archivista"),
    ("DIGITALIZADOR", "Digitalizador"),
    ("CONSULTA", "Usuario de consulta"),
)

AREAS = (
    ("A", "Zona A"),
    ("B", "Zona B"),
    ("C", "Zona C"),
    ("D", "Zona D"),
    ("O", "Zona O"),
)

SHELVES = {
    "A": 9,
    "B": 8,
    "C": 6,
    "D": 13,
    "O": 3,
}

COURTS = (
    {
        "code_raw": "589",
        "name": "Juzgado de Instrucción",
        "status": "INACTIVE",
        "notes": "Estado provisional: pendiente de confirmación institucional.",
    },
    {
        "code_raw": "589",
        "name": "Juzgado de Instrucción en Atención Permanente",
        "status": "INACTIVE",
        "notes": "Estado provisional: pendiente de confirmación institucional.",
    },
    {
        "code_raw": "102",
        "name": "Corte de Apelación",
        "status": "ACTIVE",
        "notes": "Activo según información inicial.",
    },
    {
        "code_raw": "106",
        "name": "Primera Cámara Penal del Juzgado de Primera Instancia",
        "status": "INACTIVE",
        "notes": "Inactivo según información inicial.",
    },
    {
        "code_raw": "107",
        "name": "Segunda Cámara Penal del Juzgado de Primera Instancia",
        "status": "INACTIVE",
        "notes": "Inactivo según información inicial.",
    },
    {
        "code_raw": "107",
        "name": "Juzgado de Primera Instancia Unipersonal",
        "status": "INACTIVE",
        "notes": "Estado provisional: pendiente de confirmación institucional.",
    },
    {
        "code_raw": "107-01",
        "name": "Tribunal Ejecución de la Pena",
        "status": "INACTIVE",
        "notes": "Estado provisional: pendiente de confirmación institucional.",
    },
    {
        "code_raw": "107-02",
        "name": "Tribunal Colegiado de Primera Instancia",
        "status": "INACTIVE",
        "notes": "Estado provisional: pendiente de confirmación institucional.",
    },
)


async def _existing(
    session: AsyncSession,
    model: type[Base],
    **filters: object,
) -> Base | None:
    statement = select(model).filter_by(**filters)
    return await session.scalar(statement)


async def _ensure_role(session: AsyncSession, code: str, name: str) -> None:
    if await _existing(session, Role, code=code) is not None:
        return
    session.add(
        Role(
            code=code,
            name=name,
            description=None,
            is_system=True,
            status=CatalogStatus.ACTIVE.value,
        )
    )


async def _ensure_area(session: AsyncSession, code: str, name: str) -> None:
    if await _existing(session, Area, code=code) is not None:
        return
    session.add(
        Area(
            code=code,
            name=name,
            description=None,
            status="ACTIVE",
        )
    )


async def _ensure_shelf(
    session: AsyncSession,
    area: Area,
    code: str,
) -> None:
    if await _existing(session, Shelf, area_id=area.id, code=code) is not None:
        return
    session.add(
        Shelf(
            area_id=area.id,
            code=code,
            name=f"Anaquel {code}",
            levels=None,
            positions_per_level=None,
            status="ACTIVE",
            notes="Capacidad pendiente de confirmación.",
        )
    )


async def _ensure_court(session: AsyncSession, data: dict[str, str]) -> None:
    code_raw = data["code_raw"]
    existing = await session.scalar(
        select(Court).where(
            Court.code_raw == code_raw,
            Court.name == data["name"],
        )
    )
    if existing is not None:
        return
    session.add(
        Court(
            code_raw=code_raw,
            code_normalized=code_raw.strip().upper(),
            name=data["name"],
            court_type=None,
            jurisdiction=None,
            status=data["status"],
            effective_from=None,
            effective_to=None,
            source="B1",
            notes=data["notes"],
        )
    )


async def _ensure_party_role(session: AsyncSession) -> None:
    if await _existing(session, PartyRole, code="IMPUTADO") is not None:
        return
    session.add(
        PartyRole(
            code="IMPUTADO",
            name="Imputado",
            description="Rol de parte confirmado en B1.",
            is_system=True,
            status=CatalogStatus.ACTIVE.value,
        )
    )


async def _ensure_numbering_policy(session: AsyncSession) -> None:
    if await _existing(session, NumberingPolicy, code="BOX_GLOBAL") is not None:
        return
    session.add(
        NumberingPolicy(
            code="BOX_GLOBAL",
            description="Numeración global inicial de cajas.",
            scope="GLOBAL",
            court_id=None,
            box_type=None,
            year=None,
            sequence_name="box_visible_number_seq",
            prefix=None,
            suffix=None,
            padding=0,
            start_value=4402,
            step=1,
            reset_policy="NEVER",
            is_active=True,
            effective_to=None,
            notes="La secuencia es la fuente de verdad del próximo número.",
        )
    )


async def _ensure_timezone_setting(session: AsyncSession) -> None:
    if await _existing(session, SystemSetting, key="system.timezone") is not None:
        return
    session.add(
        SystemSetting(
            key="system.timezone",
            value="America/Santo_Domingo",
            value_type="STRING",
            description="Zona horaria de presentación del sistema.",
            updated_by=None,
        )
    )


async def seed_database(session: AsyncSession) -> None:
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": SEED_LOCK_KEY},
    )

    for code, name in ROLES:
        await _ensure_role(session, code, name)

    for code, name in AREAS:
        await _ensure_area(session, code, name)
    await session.flush()

    for area_code, count in SHELVES.items():
        area = await session.scalar(select(Area).where(Area.code == area_code))
        if area is None:
            raise RuntimeError(f"No se encontró el área {area_code}")
        for number in range(1, count + 1):
            await _ensure_shelf(session, area, f"{area_code}{number}")

    for court_data in COURTS:
        await _ensure_court(session, court_data)

    await _ensure_party_role(session)
    await _ensure_numbering_policy(session)
    await _ensure_timezone_setting(session)

    await session.commit()


async def main() -> None:
    settings = get_settings()
    database = Database(settings)
    try:
        async with database.session() as session:
            await seed_database(session)
    finally:
        await database.dispose()
    print("Semillas aplicadas correctamente.")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
```

### 14.4 Ejecución

```powershell
cd backend
$env:SGA_DATABASE_URL = "postgresql+psycopg://sga_dev:CAMBIAR@localhost:5432/sga_dev"
uv run python -m judicial_archive.db.seed
```

`main()` carga `Settings` completo. Si no existe un `.env` válido, definir
también `SGA_SECRET_KEY` (mínimo 32 caracteres) y `SGA_REDIS_URL`; no guardar
esos valores en el repositorio.

Segunda ejecución:

```powershell
uv run python -m judicial_archive.db.seed
```

Resultado esperado:

- misma cantidad de roles, áreas, anaqueles, tribunales y configuración;
- ningún error de unicidad;
- ningún duplicado.

### 14.5 Verificación de conteos

```sql
SELECT 'roles', count(*) FROM roles
UNION ALL SELECT 'areas', count(*) FROM areas
UNION ALL SELECT 'shelves', count(*) FROM shelves
UNION ALL SELECT 'courts', count(*) FROM courts
UNION ALL SELECT 'party_roles', count(*) FROM party_roles
UNION ALL SELECT 'numbering_policies', count(*) FROM numbering_policies
UNION ALL SELECT 'system_settings', count(*) FROM system_settings;
```

Esperado:

| Grupo | Cantidad |
|---|---:|
| `roles` | 5 |
| `areas` | 5 |
| `shelves` | 39 |
| `courts` | 8 |
| `party_roles` | 1 |
| `numbering_policies` | 1 |
| `system_settings` | 1 |

Total: 60 filas.

---

## 15. Pruebas

### 15.1 Estrategia

| Nivel | Qué prueba | Dónde | Base real |
|---|---|---|---|
| Unitario | Metadatos, nombres, tabla esperada | `tests/unit/test_schema_metadata.py` | No |
| Integración | Constraints, triggers, secuencia, semillas, migraciones | `tests/integration/` | PostgreSQL |
| CI | Migración desde cero y suite | GitHub Actions o runner equivalente | PostgreSQL |

No se usan mocks para constraints, triggers ni migraciones. Un mock no prueba
que PostgreSQL rechace el dato.

### 15.2 Prueba unitaria de metadatos

#### Archivo: `backend/tests/unit/test_schema_metadata.py`

```python
from __future__ import annotations

from sqlalchemy import CheckConstraint, Enum, Index, UniqueConstraint

import judicial_archive.models  # noqa: F401
from judicial_archive.db.base import Base

EXPECTED_TABLES = {
    "administrative_documents",
    "areas",
    "audit_events",
    "box_labels",
    "box_movements",
    "box_number_history",
    "boxes",
    "case_file_identifier_history",
    "case_files",
    "case_parties",
    "courts",
    "deletion_requests",
    "file_assets",
    "file_attachments",
    "identifier_format_profiles",
    "import_batches",
    "import_files",
    "import_rows",
    "inventory_findings",
    "inventory_sessions",
    "legal_holds",
    "loan_items",
    "loans",
    "numbering_policies",
    "ocr_results",
    "party_roles",
    "permissions",
    "persons",
    "position_blocks",
    "positions",
    "resolution_types",
    "retention_policies",
    "role_permissions",
    "roles",
    "shelves",
    "system_settings",
    "task_jobs",
    "trays",
    "user_roles",
    "user_sessions",
    "users",
}

EXPECTED_PARTIAL_INDEXES = {
    "uq_boxes_current_position_occupied",
    "uq_identifier_format_profiles_active",
    "uq_file_attachments_case_primary",
    "uq_file_attachments_admin_primary",
    "uq_loan_items_open_box",
    "uq_loan_items_open_case",
    "uq_import_batches_idempotency",
    "uq_task_jobs_idempotency",
    "uq_numbering_policies_active_global",
    "uq_numbering_policies_active_court",
    "uq_numbering_policies_active_box_type",
    "uq_numbering_policies_active_year",
}


def test_tables_exactas() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_todas_las_tablas_tienen_pk() -> None:
    for table in Base.metadata.tables.values():
        assert table.primary_key.columns, table.name


def test_checks_tienen_nombre_completo() -> None:
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            if isinstance(constraint, CheckConstraint):
                assert constraint.name, table.name
                assert constraint.name.startswith("ck_"), constraint.name
                assert "ck_ck_" not in constraint.name, constraint.name


def test_no_hay_enum_nativo() -> None:
    for table in Base.metadata.tables.values():
        for column in table.columns:
            assert not isinstance(column.type, Enum), f"{table.name}.{column.name}"


def test_fk_apuntan_a_tablas_registradas() -> None:
    for table in Base.metadata.tables.values():
        for fk in table.foreign_keys:
            assert fk.column.table.name in EXPECTED_TABLES


def test_indices_parciales_presentes() -> None:
    names: set[str] = set()
    for table in Base.metadata.tables.values():
        for index in table.indexes:
            if index.dialect_options["postgresql"].get("where") is not None:
                assert isinstance(index, Index)
                names.add(index.name or "")
    assert names >= EXPECTED_PARTIAL_INDEXES


def test_unique_compuesta_de_caja() -> None:
    table = Base.metadata.tables["boxes"]
    names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_boxes_id_box_type" in names
```

### 15.3 Fixtures de integración

#### Archivo: `backend/tests/integration/conftest.py`

```python
from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

import judicial_archive.models  # noqa: F401
from judicial_archive.db.base import Base

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _integration_url() -> str:
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("RUN_INTEGRATION=1 no está definido")
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL no está definido")
    if "prod" in url.lower():
        pytest.skip("La URL parece de producción; se rechaza por seguridad")
    return url


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return _integration_url()


@pytest.fixture(scope="session")
def alembic_config(test_database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option(
        "script_location",
        (BACKEND_ROOT / "alembic").as_posix(),
    )
    config.set_main_option(
        "sqlalchemy.url",
        test_database_url.replace("%", "%%"),
    )
    return config


@pytest.fixture(scope="session")
def migrated_database(
    alembic_config: Config,
    test_database_url: str,
) -> str:
    command.upgrade(alembic_config, "head")
    return test_database_url


@pytest_asyncio.fixture
async def db_engine(migrated_database: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_database, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(
    db_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    table_names = ", ".join(
        f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables)
    )
    async with db_engine.begin() as connection:
        await connection.execute(
            text(
                "ALTER TABLE audit_events DISABLE TRIGGER trg_audit_events_no_truncate"
            )
        )
        try:
            await connection.execute(
                text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
            )
            await connection.execute(
                text("ALTER SEQUENCE box_visible_number_seq RESTART WITH 4402")
            )
        finally:
            await connection.execute(
                text(
                    "ALTER TABLE audit_events "
                    "ENABLE TRIGGER trg_audit_events_no_truncate"
                )
            )
    return factory


@pytest_asyncio.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
```

#### Notas

- La limpieza desactiva temporalmente el trigger de `TRUNCATE` de auditoría; no
  se puede truncar auditoría con el trigger activo.
- `TRUNCATE ... CASCADE` se ejecuta solo en la base de pruebas.
- La secuencia se reinicia a 4402.
- `migrated_database` deja el esquema en `head`; las pruebas de migración deben
  restaurarlo en `finally`.
- No ejecutar integración con `-n auto`: comparten base y se interfieren.

### 15.4 Matriz de constraints

Implementar estas pruebas con fábricas mínimas de `courts`, `positions`,
`boxes` y usuarios. Cada caso debe esperar `IntegrityError` o el error
`DBAPIError` correspondiente.

| Caso | Acción | Resultado |
|---|---|---|
| Caja sin número | Insertar caja con `visible_number` vacío | Rechazo |
| Número duplicado | Insertar dos cajas con 4402 | Rechazo |
| Tipo inválido | Insertar `box_type = 'MIXTO'` | Rechazo |
| Expediente en caja administrativa | Insertar con `box_type = 'DOCUMENTOS_ADMINISTRATIVOS'` | Rechazo por FK/check |
| Documento en caja de expedientes | Insertar con `box_type = 'EXPEDIENTES'` | Rechazo |
| Dos cajas en una posición | Insertar dos cajas activas en la misma posición | Rechazo por índice único parcial |
| Caja en préstamo con posición actual | Insertar custodia `ON_LOAN` con posición | Rechazo |
| Caja en posición sin posición | Custodia `IN_PLACE` y `current_position_id` nulo | Rechazo |
| Año inválido | `year = 0` | Rechazo |
| NUC vacío | `nuc_normalized = ' '` | Rechazo |
| Fecha parcial imposible | `entry_precision='MONTH'` sin mes | Rechazo |
| Fecha con día sin mes | `entry_precision='DAY'` y mes nulo | Rechazo |
| Dos objetivos en hold | `target_type='BOX'` con `case_file_id` | Rechazo |
| Hold sin objetivo | `target_type='BOX'` con `box_id` nulo | Rechazo |
| Solicitud con dos aprobadores iguales | `requested_by = approved_by` | Rechazo |
| Solicitud completada sin evidencia | `status='COMPLETED'` sin `evidence_file_id` | Rechazo |
| Archivo en dos destinos | `case_file_id` y `administrative_document_id` no nulos | Rechazo |
| Dos principales activos | Dos attachments `is_primary` al mismo expediente | Rechazo |
| Préstamo doble de caja | Dos `loan_items` abiertos para la misma caja | Rechazo |
| Ítem de préstamo mixto | Caja y expediente no nulos | Rechazo |
| Fila aplicada sin destino | `status='APPLIED'` sin target | Rechazo |
| Fila con dos destinos | Dos target no nulos | Rechazo |
| Lote listo con errores | `status='READY'` y `error_rows > 0` | Rechazo |
| Lote fallido sin motivo | `status='FAILED'` y `failure_reason` nulo | Rechazo |
| Lote con aprobador igual sin excepción | `approved_by=created_by` y sin `approval_exception_reason` | Rechazo |
| Préstamo cancelado sin motivo | `status='CANCELLED'` con `cancelled_at` y motivo nulo | Rechazo |
| Préstamo con aprobador igual sin excepción | `approved_by=requested_by` y sin excepción | Rechazo |
| Attachment desvinculado sin motivo | `detached_at` no nulo y `detached_reason` nulo | Rechazo |
| Hold liberado sin motivo | `status='RELEASED'` con actor y motivo nulo | Rechazo |
| Hallazgo resuelto sin resolución | `finding_status='RESOLVED'` y `resolution` nula | Rechazo |
| Borrado rechazado sin motivo | `status='REJECTED'` con actor y motivo nulo | Rechazo |
| Importación duplicada | Mismo `created_by + idempotency_key` | Rechazo |
| Auditoría modificada | `UPDATE audit_events` | Rechazo por trigger |
| Auditoría borrada | `DELETE audit_events` | Rechazo por trigger |
| Auditoría truncada | `TRUNCATE audit_events` | Rechazo por trigger |
| Cambio de tipo con contenido | `UPDATE boxes SET box_type=...` | Rechazo por trigger |
| Cambio de tipo sin contenido | Caja vacía cambia de tipo | Permitido |
| Semilla doble | Ejecutar `seed_database` dos veces | Sin duplicados |

### 15.5 Prueba de concurrencia de numeración

#### Archivo: `backend/tests/integration/test_schema_concurrency.py`

```python
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_sequence_is_unique_under_concurrency(
    db_engine,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    court_id = uuid4()
    async with db_engine.begin() as connection:
        await connection.execute(
            text(
                "INSERT INTO courts "
                "(id, code_raw, code_normalized, name, status) "
                "VALUES (:id, '102', '102', 'Corte de Apelación', 'ACTIVE')"
            ),
            {"id": court_id},
        )

    async def allocate() -> int:
        async with session_factory() as session:
            number = await session.scalar(
                text("SELECT nextval('box_visible_number_seq')")
            )
            await session.execute(
                text(
                    "INSERT INTO boxes "
                    "(id, court_id, year, visible_number) "
                    "VALUES (:id, :court_id, 2026, :number)"
                ),
                {
                    "id": uuid4(),
                    "court_id": court_id,
                    "number": str(number),
                },
            )
            await session.commit()
            return int(number)

    values = await asyncio.gather(*(allocate() for _ in range(20)))

    assert len(values) == 20
    assert len(set(values)) == 20
    assert min(values) >= 4402
    assert max(values) <= 4421
```

#### Notas

- Se prueban conexiones y sesiones reales.
- No se usa `MAX + 1`.
- El rango 4402-4421 asume una base limpia y 20 llamadas. Si se cambia el
  número de llamadas, ajustar el límite superior.
- La prueba no prueba la transacción de negocio completa; B6 la añadirá.

### 15.6 Prueba de inmutabilidad de auditoría

#### Archivo: `backend/tests/integration/test_audit_immutability.py`

```python
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.integration


async def _insert_event(connection) -> None:
    await connection.execute(
        text(
            "INSERT INTO audit_events "
            "(id, actor_type, action, entity_type, source, result) "
            "VALUES (:id, 'SYSTEM', 'BOOT', 'system', 'SYSTEM', 'SUCCESS')"
        ),
        {"id": uuid4()},
    )


@pytest.mark.asyncio
async def test_audit_event_cannot_be_updated(db_engine) -> None:
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        await _insert_event(connection)
        with pytest.raises(DBAPIError, match="append-only"):
            await connection.execute(text("UPDATE audit_events SET action = 'CHANGED'"))
        await transaction.rollback()


@pytest.mark.asyncio
async def test_audit_event_cannot_be_deleted(db_engine) -> None:
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        await _insert_event(connection)
        with pytest.raises(DBAPIError, match="append-only"):
            await connection.execute(text("DELETE FROM audit_events"))
        await transaction.rollback()


@pytest.mark.asyncio
async def test_audit_event_cannot_be_truncated(db_engine) -> None:
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        await _insert_event(connection)
        with pytest.raises(DBAPIError, match="append-only"):
            await connection.execute(text("TRUNCATE audit_events"))
        await transaction.rollback()
```

### 15.7 Prueba de semillas

#### Archivo: `backend/tests/integration/test_seed_idempotency.py`

```python
from __future__ import annotations

import pytest
from sqlalchemy import func, select

from judicial_archive.db.seed import seed_database
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.courts.models import (
    Court,
    NumberingPolicy,
    PartyRole,
    SystemSetting,
)
from judicial_archive.modules.locations.models import Area, Shelf
from judicial_archive.modules.users.models import Role

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_seed_is_idempotent(db_session) -> None:
    await seed_database(db_session)
    await seed_database(db_session)

    async def count(model) -> int:
        return int(await db_session.scalar(select(func.count()).select_from(model)))

    assert await count(Role) == 5
    assert await count(Area) == 5
    assert await count(Shelf) == 39
    assert await count(Court) == 8
    assert await count(PartyRole) == 1
    assert await count(NumberingPolicy) == 1
    assert await count(SystemSetting) == 1

    duplicates_589 = await db_session.scalar(
        select(func.count()).select_from(Court).where(Court.code_raw == "589")
    )
    duplicates_107 = await db_session.scalar(
        select(func.count()).select_from(Court).where(Court.code_raw == "107")
    )
    assert duplicates_589 == 2
    assert duplicates_107 == 2


@pytest.mark.asyncio
async def test_seed_does_not_create_operational_data(db_session) -> None:
    await seed_database(db_session)
    boxes = await db_session.scalar(select(func.count()).select_from(Box))
    assert boxes == 0
```

#### Notas

- No se crean cajas, expedientes, personas ni usuarios.
- Los conteos incluyen solo datos semilla.

### 15.8 Pruebas de migración

#### Archivo: `backend/tests/integration/test_migrations.py`

```python
from __future__ import annotations

import pytest
from alembic import command
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.integration


def _exists(url: str, name: str) -> bool:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return (
                connection.scalar(
                    text("SELECT to_regclass(:name)"),
                    {"name": f"public.{name}"},
                )
                is not None
            )
    finally:
        engine.dispose()


def test_upgrade_downgrade_round_trip(
    alembic_config,
    test_database_url: str,
) -> None:
    try:
        command.upgrade(alembic_config, "head")
        assert _exists(test_database_url, "boxes")
        assert _exists(test_database_url, "audit_events")

        command.downgrade(alembic_config, "base")
        assert not _exists(test_database_url, "boxes")
        assert not _exists(test_database_url, "audit_events")
    finally:
        command.upgrade(alembic_config, "head")


def test_alembic_check_is_clean(
    alembic_config,
    test_database_url: str,
) -> None:
    command.upgrade(alembic_config, "head")
    command.check(alembic_config)
```

#### Notas

- `command.check` falla si hay diferencias entre modelos y base.
- La prueba de downgrade es destructiva; solo se ejecuta en la base de pruebas.
- El `finally` restaura `head`.
- No usar esta prueba contra una base con datos reales.

### 15.9 Comandos

```powershell
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest tests/unit
$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://sga_test:CAMBIAR@localhost:5432/sga_test"
uv run pytest tests/integration -m integration -n 0
```

No ejecutar integración en paralelo sobre la misma base. Si se usa CI con
servicios, cada job debe tener su propia base.

### 15.10 Cobertura

Al cierre de B2 el umbral se eleva a 75. La suite local alcanzó 92.54 % con
`branch = true`; el umbral se fijó en `fail_under = 75`. No se eleva con
exclusiones artificiales.

---

## 16. ERD físico

### 16.1 Núcleo judicial y ubicaciones

```mermaid
erDiagram
    COURTS ||--o{ IDENTIFIER_FORMAT_PROFILES : define
    COURTS ||--o{ NUMBERING_POLICIES : limita
    COURTS ||--o{ RETENTION_POLICIES : aplica
    COURTS ||--o{ BOXES : posee
    COURTS ||--o{ CASE_FILES : tramita

    AREAS ||--o{ SHELVES : contiene
    SHELVES ||--o{ TRAYS : contiene
    SHELVES ||--o{ POSITION_BLOCKS : bloquea
    TRAYS ||--o{ POSITIONS : contiene
    POSITIONS o|--o| BOXES : actual

    NUMBERING_POLICIES ||--o{ BOXES : numera
    BOXES ||--o{ BOX_NUMBER_HISTORY : cambia
    BOXES ||--o{ BOX_MOVEMENTS : mueve
    BOXES ||--o{ BOX_LABELS : identifica
    BOXES ||--o{ CASE_FILES : contiene
    BOXES ||--o{ ADMINISTRATIVE_DOCUMENTS : contiene

    CASE_FILES ||--o{ CASE_FILE_IDENTIFIER_HISTORY : corrige
    CASE_FILES ||--o{ CASE_PARTIES : relaciona
    PERSONS ||--o{ CASE_PARTIES : participa
    PARTY_ROLES ||--o{ CASE_PARTIES : clasifica
    RESOLUTION_TYPES o|--o{ CASE_FILES : clasifica
```

### 16.2 Archivos, importaciones, OCR y tareas

```mermaid
erDiagram
    FILE_ASSETS ||--o{ FILE_ATTACHMENTS : adjunta
    CASE_FILES o|--o{ FILE_ATTACHMENTS : recibe
    ADMINISTRATIVE_DOCUMENTS o|--o{ FILE_ATTACHMENTS : recibe

    IMPORT_BATCHES ||--o{ IMPORT_FILES : agrupa
    FILE_ASSETS ||--o{ IMPORT_FILES : respalda
    IMPORT_FILES ||--o{ IMPORT_ROWS : extrae
    IMPORT_ROWS }o--o| BOXES : destino_caja
    IMPORT_ROWS }o--o| CASE_FILES : destino_expediente
    IMPORT_ROWS }o--o| ADMINISTRATIVE_DOCUMENTS : destino_documento

    FILE_ASSETS ||--o{ OCR_RESULTS : procesa
    IMPORT_FILES o|--o{ OCR_RESULTS : origina
    USERS o|--o{ OCR_RESULTS : revisa

    TASK_JOBS }o--o| USERS : crea
```

### 16.3 Operaciones, inventario y retención

```mermaid
erDiagram
    USERS ||--o{ LOANS : solicita
    USERS o|--o{ LOANS : aprueba
    LOANS ||--o{ LOAN_ITEMS : incluye
    BOXES o|--o{ LOAN_ITEMS : presta
    CASE_FILES o|--o{ LOAN_ITEMS : presta
    LOANS o|--o{ BOX_MOVEMENTS : origina

    INVENTORY_SESSIONS ||--o{ INVENTORY_FINDINGS : reporta
    BOXES o|--o{ INVENTORY_FINDINGS : involucra

    LEGAL_HOLDS }o--o| BOXES : protege
    LEGAL_HOLDS }o--o| CASE_FILES : protege
    LEGAL_HOLDS }o--o| FILE_ASSETS : protege

    DELETION_REQUESTS }o--o| BOXES : solicita
    DELETION_REQUESTS }o--o| CASE_FILES : solicita
    DELETION_REQUESTS }o--o| FILE_ASSETS : solicita
    FILE_ASSETS o|--o{ DELETION_REQUESTS : evidencia

    USERS ||--o{ AUDIT_EVENTS : actua
```

### 16.4 Relaciones de actores omitidas por claridad

Muchas tablas tienen `created_by`, `updated_by`, `approved_by`, `delivered_by`,
`returned_by`, `reviewed_by`, `applied_by`, `blocked_by` o `resolved_by`. Todas
son FK a `users` con `ON DELETE RESTRICT`. No se dibujan todas para evitar un
diagrama ilegible; el código de los modelos es la fuente completa.

### 16.5 Cardinalidades importantes

| Relación | Cardinalidad real |
|---|---|
| Área → anaquel | 1:N |
| Anaquel → bandeja | 1:N |
| Bandeja → posición | 1:N |
| Posición → caja actual | 0..1:0..1 efectiva por índice parcial |
| Caja → expediente | 1:N |
| Caja → documento administrativo | 1:N |
| Expediente → persona | N:M mediante `case_parties` |
| Archivo → destino | N:1 por enlace, con destino exclusivo |
| Lote → archivo | 1:N |
| Archivo de importación → fila | 1:N |
| Préstamo → ítem | 1:N |
| Ítem → caja o expediente | Exactamente uno |
| Hold → objetivo | Exactamente uno |
| Solicitud de borrado → objetivo | Exactamente uno |

---

## 17. Runbook de actualización

### 17.1 Precondiciones

- [ ] Rama y commit revisados.
- [ ] Repositorio sin cambios ajenos.
- [ ] Backup reciente de la base.
- [ ] Ventana de mantenimiento acordada.
- [ ] Migración revisada por una segunda persona.
- [ ] Pruebas en base de pruebas completadas.
- [ ] Plan de reversión/restauración escrito.
- [ ] Usuario de base con permisos suficientes para DDL.
- [ ] Sin escrituras de la aplicación durante la migración.

### 17.2 Respaldo previo

Usar variables de entorno para no exponer secretos:

```powershell
$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGDATABASE = "sga"
$env:PGUSER = "sga_migrator"
$env:PGPASSWORD = "CAMBIAR"
$env:PGSSLMODE = "require"

$backup = "C:\backups\sga_b2_$(Get-Date -Format 'yyyyMMdd_HHmmss').dump"
pg_dump --format=custom --no-owner --no-acl --file=$backup --dbname=$env:PGDATABASE
if (-not (Test-Path -LiteralPath $backup)) { throw "No se creó el respaldo" }
Get-Item -LiteralPath $backup | Select-Object FullName, Length, LastWriteTime
```

No continuar si el archivo no existe o tiene tamaño anómalo.

### 17.3 Verificación de estado

```powershell
cd backend
$env:SGA_DATABASE_URL = "postgresql+psycopg://sga_migrator:CAMBIAR@localhost:5432/sga"
uv run alembic current
uv run alembic heads
uv run alembic history --verbose
```

Estos comandos cargan `Settings` cuando `alembic.ini` no define una URL. Si no
hay `.env` válido, definir también `SGA_SECRET_KEY` y `SGA_REDIS_URL`.

Debe existir una sola cabeza. Si hay múltiples, detenerse y resolver antes de
actualizar.

### 17.4 Actualización

```powershell
uv run alembic upgrade head
uv run alembic current
uv run alembic check
```

Comprobar:

```sql
SELECT version_num FROM alembic_version;
SELECT to_regclass('public.boxes');
SELECT to_regclass('public.audit_events');
SELECT last_value, is_called FROM box_visible_number_seq;
```

`is_called = false` y `last_value = 4402` en una base nueva antes de asignar
números. No ejecutar `nextval` en producción solo para comprobar.

### 17.5 Semillas

```powershell
uv run python -m judicial_archive.db.seed
uv run python -m judicial_archive.db.seed
```

La segunda ejecución no debe duplicar. En producción, ejecutar semillas solo si
el despliegue lo requiere y con el mismo control que la migración.

### 17.6 Validación funcional mínima

```sql
SELECT count(*) FROM roles;
SELECT count(*) FROM areas;
SELECT count(*) FROM shelves;
SELECT count(*) FROM courts;
SELECT count(*) FROM numbering_policies;
SELECT count(*) FROM legal_holds;
```

No insertar cajas reales durante la validación de esquema.

### 17.7 Errores comunes

| Error | Causa probable | Acción |
|---|---|---|
| `relation already exists` | Migración aplicada parcialmente o base no vacía | Revisar `alembic current`; no borrar tablas a ciegas |
| `constraint ... does not exist` | Downgrade o migración manual incompleta | Restaurar backup; revisar revisión |
| `permission denied for schema public` | Usuario sin DDL | Usar rol migrador autorizado |
| `deadlock detected` | Aplicación escribiendo durante DDL | Detener escrituras y reintentar |
| `lock timeout` | Tabla bloqueada por sesión larga | Identificar `pg_stat_activity`; no matar sin evaluar |
| `check constraint ... violated` | Semilla o dato incompatible | Corregir dato/migración; no desactivar check |
| `audit_events es append-only` | Intento de mutar auditoría | Corregir el flujo; no desactivar trigger |
| `No new upgrade operations detected` ausente | Modelos y base difieren | No desplegar; revisar migración |
| `sequence ... does not exist` | Trigger/secuencia omitidos a mano | Corregir migración inicial |
| `duplicate key ... visible_number` | Numeración manual concurrente | Usar la secuencia de B6 |

### 17.8 Consulta de bloqueos

```sql
SELECT pid, usename, state, wait_event_type, wait_event, query
FROM pg_stat_activity
WHERE datname = current_database()
  AND state <> 'idle';
```

No cancelar procesos sin identificar la transacción y su impacto.

---

## 18. Reversión y restauración

### 18.1 Reversión de la migración inicial

Solo en base de pruebas vacía o con backup verificado:

```powershell
uv run alembic downgrade base
uv run alembic current
```

Comprobar:

```sql
SELECT to_regclass('public.boxes');
SELECT to_regclass('public.audit_events');
SELECT to_regclass('public.box_visible_number_seq');
```

Los tres deben ser `NULL`.

### 18.2 Reversión de una migración futura

Para una migración incremental:

```powershell
uv run alembic downgrade -1
```

Antes de ejecutarla, revisar:

- si elimina columnas con datos;
- si elimina tablas con historia;
- si revierte datos importados;
- si los triggers dependen de columnas que se eliminan;
- si hay respaldo y ventana.

### 18.3 Restauración

```powershell
$env:PGDATABASE = "sga"
$env:PGUSER = "sga_restore"
$env:PGPASSWORD = "CAMBIAR"

pg_restore --clean --if-exists --no-owner --no-acl --dbname=$env:PGDATABASE "C:\backups\sga_b2_20261026_120000.dump"
```

Después:

```powershell
cd backend
$env:SGA_DATABASE_URL = "postgresql+psycopg://sga_migrator:CAMBIAR@localhost:5432/sga"
uv run alembic current
uv run alembic check
```

La restauración debe probarse periódicamente. Un backup no verificado no es una
garantía.

### 18.4 Regla de producción

- No usar `downgrade base` en producción.
- No borrar `alembic_version` para "arreglar" un estado.
- No aplicar DDL manual sin migración.
- No restaurar sobre la base productiva sin ventana y validación.
- No desactivar triggers de auditoría en producción.
- No reutilizar números de caja después de una restauración parcial.

---

## 19. Criterios de aceptación verificables

| # | Criterio | Evidencia |
|---:|---|---|
| 1 | Las 41 tablas existen | `test_tables_exactas`, `to_regclass` |
| 2 | `upgrade head` funciona desde vacío | `test_upgrade_downgrade_round_trip` |
| 3 | `downgrade base` funciona en prueba | misma prueba |
| 4 | `alembic check` limpio | `test_alembic_check_is_clean` |
| 5 | Checks de tipo y objetivo rechazan datos inválidos | matriz de constraints |
| 6 | Posición única activa | matriz + SQL |
| 7 | Préstamo abierto único | matriz + SQL |
| 8 | Secuencia concurrente sin duplicados | `test_sequence_is_unique_under_concurrency` |
| 9 | Auditoría no mutable | `test_audit_immutability.py` |
| 10 | Semillas idempotentes | `test_seed_idempotency.py` |
| 11 | No hay usuarios semilla | inspección de semillas |
| 12 | No hay cajas semilla | `test_seed_does_not_create_operational_data` |
| 13 | No hay `ENUM` nativo | unit test |
| 14 | Todo check tiene nombre | unit test |
| 15 | No hay FKs a tablas inexistentes | unit test |
| 16 | El ERD coincide con las tablas | revisión de este documento |
| 17 | Runbook y restore documentados | secciones 17 y 18 |
| 18 | Sin secretos ni datos reales | `git diff --check`, revisión manual |
| 19 | Ruff, mypy y pytest ejecutados | salida de comandos |
| 20 | Sin commit/push no autorizado | `git status` |

### 19.1 Evidencia mínima para cerrar B2

```powershell
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest tests/unit
$env:RUN_INTEGRATION = "1"
uv run pytest tests/integration -m integration -n 0
uv run alembic check
```

Guardar en el resumen de fase:

- fecha y entorno;
- versión de PostgreSQL;
- comandos ejecutados;
- resultados;
- pruebas no ejecutadas y motivo;
- riesgos restantes.

---

## 20. Riesgos y decisiones abiertas

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Cambio de convención `ck` en `Base` | Nombres dobles si se olvida | Test que exige prefijo y nombre completo |
| Triggers requieren permisos de owner | Migración falla en producción | Rol migrador con permisos; probar en staging |
| Secuencia no evita huecos | Números consumidos sin caja | Aceptado; no se reutilizan números |
| Estados "por confirmar" de tribunales | Datos no operativos hasta validación | Semilla `INACTIVE` provisional y nota; B5 confirma |
| `nuc_suffix5` sobre texto normalizado | Puede no ser solo dígitos | B8 define búsqueda y validación; no cambia almacenamiento |
| Checks de fechas no validan calendario | 31/02 posible | Servicio valida calendario en B6 |
| Índices parciales con datos históricos | Conflictos al cargar | Importación revisable detecta antes de aplicar |
| Triggers de inmutabilidad con correcciones legítimas | Bloqueo de flujo | Corrección por movimiento/flujo explícito, no `UPDATE` directo |
| Semillas en producción | Datos no deseados | Ejecutar solo con autorización y revisión |
| Pruebas destructivas | Pérdida de datos si se apunta a producción | `TEST_DATABASE_URL` separada; rechazo de URL con `prod` |
| Modelos sin relaciones ORM | Consultas manuales en B4-B8 | Añadir relaciones explícitas cuando exista caso de uso |
| Cobertura baja por modelos declarativos | Umbral no representativo | No usar modelos como excusa; probar constraints reales |
| `FileAsset` sin almacenamiento real | B2 no puede validar archivos | B9 implementa almacenamiento y antivirus |

### 20.1 Decisiones que requieren confirmación humana

1. Estado definitivo de los tribunales marcados "por confirmar".
2. Política exacta de numeración por año, tribunal o tipo.
3. Condiciones definitivas de inmutabilidad de caja.
4. Si se presta caja completa, expediente o ambos.
5. Plazos y fundamento legal de retención.
6. Formatos NUC por tribunal y época.
7. Semántica de sentencias y prefijos SADM/SPEN/RPE.
8. Almacenamiento privado y política de archivos.
9. Necesidad de tabla de lecturas de inventario.
10. Estrategia de purga de sesiones y tareas.

No implementar una regla rígida nueva sin resolver la decisión correspondiente.

---

## 21. Handoff a fases posteriores

### B3 — Configuración, logging y errores

- No modifica el esquema salvo que falte una configuración aprobada.
- Usa `system_settings` para configuración persistente, no secretos.
- No guarda claves en la base.

### B4 — Autenticación y permisos

- Usa `users`, `roles`, `permissions`, `user_roles`, `role_permissions` y
  `user_sessions`.
- Implementa hash Argon2id y política de sesión.
- No crea usuarios semilla con contraseña conocida.

### B5 — Catálogos y configuración física

- Usa `courts`, `identifier_format_profiles`, `resolution_types`, `areas`,
  `shelves`, `trays`, `positions`, `position_blocks`, `party_roles`.
- Confirma estados de tribunales y capacidades.
- No crea posiciones sin nomenclatura validada.

### B6 — Cajas y registros documentales

- Implementa `nextval` de `box_visible_number_seq` en la misma transacción de
  creación.
- Crea `CaseFile`, `Person`, `CaseParty` y documentos administrativos.
- No usa `MAX + 1`.
- Registra `BoxNumberHistory` y auditoría en correcciones.

### B7 — Ubicaciones y movimientos

- Implementa asignación con bloqueo de posición.
- Actualiza caja y `BoxMovement` en una transacción.
- Maneja el índice parcial de posición.
- No sobrescribe historia.

### B8 — Búsqueda global

- Usa `nuc_suffix5`, NUC normalizado, nombres, años y ubicación.
- Añade índices con consultas y `EXPLAIN` reales.
- No convierte NUC a entero.
- Añade trigramas solo con extensión aprobada.

### B9 — Archivos y digitalización

- Implementa almacenamiento privado, hashing y antivirus.
- Usa `FileAsset` y `FileAttachment`.
- No expone `storage_key`.
- No descarga sin permisos.

### B10 — OCR e importación

- Usa `ImportBatch`, `ImportFile`, `ImportRow`, `OcrResult` y `TaskJob`.
- Mantiene revisión y aprobación antes de aplicar.
- Aplica filas de forma transaccional e idempotente.
- No duplica al reintentar.

### B11 — Préstamos y QR

- Usa `Loan`, `LoanItem` y `BoxLabel`.
- Cierra `LoanItem` con `released_at`.
- Genera tokens opacos y guarda hash.
- No concede acceso por el QR solo.

### B12 — Inventario

- Usa `InventorySession` e `InventoryFinding`.
- No corrige ubicaciones automáticamente.
- Cierra con resolución y evidencia.

### B13 — Auditoría completa

- Usa `AuditEvent`.
- Redacta datos sensibles.
- No permite mutación.
- Añade consultas autorizadas y exportación.

### B14 — Reportes

- Consulta vistas/tablas existentes.
- No crea tablas temporales permanentes sin migración.
- Añade índices solo con consultas reales.

### B15 — Producción

- Prueba restauración.
- Verifica triggers y permisos.
- Revisa `alembic check`.
- Documenta operación y rollback.

---

## 22. Registro de validación de esta guía

| Comprobación | Estado |
|---|---|
| Estructura de la guía completa | Revisada: secciones 0 a 22 |
| Código copiable y sin marcadores | 26 archivos extraídos; compilación correcta |
| 41 tablas inventariadas | Verificado en el documento y en metadatos |
| Coincidencia con D-01 a D-39 | Revisada |
| Codificación UTF-8 sin BOM | Verificado |
| Saltos LF y sin espacios finales | Verificado |
| `git diff --check` | Sin salida |
| Mermaid parseable | Pendiente de render; sintaxis revisada manualmente |
| Comandos PowerShell revisados | Revisados |
| Sin secretos | Verificado por búsqueda manual |
| Sin implementación B2 | Correcto: solo se creó esta guía |
| Ruff sobre bloques copiables | Sin errores (salvo `S101`, ignorado en pruebas por el proyecto) |
| `configure_mappers()` | Correcto |
| Checks con nombre | 244 checks; prefijo `ck_` y sin `ck_ck_` |
| Índices parciales esperados | 20 presentes |
| DDL offline | 41 `CREATE TABLE` y 86 índices |
| Triggers de `updated_at` | 32 tablas verificadas |

### 22.1 Validación final propuesta

```powershell
cd C:\Users\Tony\Documents\sga
git diff --check
(Get-Content -LiteralPath 'docs\phases\phaseB2_guide.md' -Encoding utf8).Count
$marker = 'B2_' + 'CONTINUE|Context' + 'Status\s*[:=]|^\s*(TODO|TBD):'
Select-String -Path 'docs\phases\phaseB2_guide.md' -Pattern $marker
```

Resultado esperado:

- `git diff --check` sin salida;
- sin marcadores pendientes;
- sin `ContextStatus`;
- sin `TODO`/`TBD` en decisiones que deban estar cerradas;
- documento legible y con todos los bloques cerrados.

### 22.2 Resultados obtenidos en la revisión local

| Comprobación | Resultado |
|---|---|
| Documento | 6836 líneas, UTF-8 sin BOM, LF, sin espacios finales |
| Fences Markdown | 132 fences balanceados |
| Bloques Python | 26 archivos extraídos y compilados sin errores |
| Ruff | Sin errores con la configuración del proyecto; `S101` se ignora en `tests/` |
| Metadatos | 41 tablas registradas; `configure_mappers()` correcto |
| Checks | 244 nombres únicos, todos con prefijo `ck_` |
| Índices parciales | 20 nombres esperados presentes |
| DDL offline | 41 `CREATE TABLE`, 86 índices |
| `updated_at` | 32 tablas de `UPDATED_AT_TABLES` con columna y trigger previsto |
| Implementación | 59 archivos fuente; 41 tablas; migración `20261026_0001` |
| PostgreSQL | 18.4 local; `sga_test` recreada desde esquema vacío |
| Ruff y mypy | `ruff check` y `ruff format --check` sin errores; mypy 59 archivos |
| Unitarias | 34 passed |
| Integración | 46 passed; incluye constraints, concurrencia, triggers y migraciones |
| Suite completa | 87 passed; cobertura 92.54 % con `branch = true` |
| Alembic | upgrade/downgrade y `alembic check` sin diferencias |
| `git diff --check` | Sin salida |

B2 queda implementado y verificado contra PostgreSQL local. La cobertura se
elevó a 75. Quedan como limitaciones declaradas el render real de Mermaid
(`mmdc` no instalado) y la ausencia de un ensayo de restauración completo.
