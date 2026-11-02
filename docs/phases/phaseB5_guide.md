# Fase B5 --- Catálogos y configuración administrativa

- **Versión:** 1.0
- **Estado:** guía de implementación; código B5 aún no implementado
- **Fecha:** 2026-10-29
- **Ámbito:** backend
- **Entrada:** B0-B4 cerradas. B4 en `15d0828`. Head Alembic esperado: `88ae4fe9cb05`.
- **Salida:** catálogos judiciales y configuración física administrables por API, con permisos, validaciones, auditoría, migración de unicidad de áreas, pruebas y documentación.

---

## 0. Cómo usar este documento

### 0.1 Regla de alcance

Este documento es una guía de implementación. **No autoriza por sí mismo** a modificar código, ejecutar migraciones sobre bases compartidas, hacer commit ni hacer push. La implementación se realiza únicamente cuando el usuario lo autorice de forma explícita.

Toda decisión de B5 debe respetar, en este orden:

1. `docs/AGENTS.md`.
2. La fase B5 de `docs/phases/GUIA_DESARROLLO_FASES_SGA.md`.
3. Las reglas de dominio de `docs/phases/phaseB1_guide.md`.
4. El esquema real creado en B2 y documentado en `docs/phases/phaseB2_guide.md`.
5. Los patrones de API, seguridad y pruebas cerrados en B3/B4.
6. El estado real del repositorio y de Alembic, verificado antes de escribir código.

Si una instrucción contradice una regla de seguridad o de negocio, prevalece la más restrictiva.

### 0.2 Qué significa "sin omisiones" en B5

Esta guía incluye:

- Alcance funcional, límites con B6/B7 y criterios de aceptación verificables.
- Decisiones de diseño explícitas y puntos que requieren validación humana.
- Árbol exacto de archivos a crear y modificar.
- Contratos de API completos, incluidos permisos, filtros, paginación, errores y auditoría.
- Modelos, esquemas Pydantic, repositorios, servicios y routers propuestos.
- Migración Alembic para la única brecha de esquema detectada: unicidad de `areas.code`.
- Servicio de auditoría de negocio reutilizable.
- Validación de patrones de identificador, políticas de numeración y planificador de capacidad.
- Reglas de desactivación sin borrado físico.
- Pruebas unitarias, de API e integración.
- Actualización de documentación y runbook de despliegue.
- Riesgos, mitigaciones y handoff a fases posteriores.

**Fuera de alcance de B5:**

- Asignar cajas a posiciones, traslados, historial de ubicación y conciliación (B6/B7).
- Implementar el frontend.
- CRUD de tipos de caja: `BoxType` permanece como enumeración cerrada.
- Cambiar permisos granulares existentes o crear permisos nuevos.
- Añadir tablas o columnas no aprobadas. La única migración de esquema B5 es `uq_areas_code`.
- Revalidar retroactivamente datos históricos al cambiar un perfil de identificador.
- Borrar secuencias, posiciones, bandejas o registros históricos.

### 0.3 Principios obligatorios

- **La API y la base de datos son autoritativas.** El frontend no replica reglas.
- **Desactivar no es borrar.** No se exponen endpoints `DELETE` para catálogos.
- **El UUID es la identidad.** Los códigos visibles no sustituyen claves internas.
- **Los códigos de tribunal no son únicos.** Los duplicados `589` y `107` son datos existentes y deben conservarse.
- **Solo `Area.code` requiere unicidad.** No imponer unicidad global a códigos judiciales sin decisión institucional.
- **Los cambios de catálogo se auditan** en la misma transacción de negocio.
- **La auditoría no guarda secretos.** Nunca tokens, contraseñas, claves ni contenido documental.
- **Las operaciones compuestas son transaccionales.** Perfil reemplazado, secuencia creada y capacidad aplicada deben confirmarse o revertirse juntas.
- **No hay borrado silencioso.** Si una operación física afecta posiciones ocupadas o bloqueadas, responde `409 conflict`.
- **Los patrones configurables son de administrador.** Se validan, se limitan y se documenta el riesgo residual de expresiones regulares.
- **Las pruebas no usan datos de producción.** No se inventan datos históricos.

---

## 1. Objetivo, alcance y entregables

### 1.1 Objetivo

Hacer configurables los datos institucionales y físicos sin modificar el código fuente, manteniendo integridad, trazabilidad y compatibilidad con datos históricos.

### 1.2 Incluido

| Bloque | Incluido en B5 |
|---|---|
| Tribunales | CRUD lógico, filtros, búsqueda, estado, vigencia, auditoría |
| Tipos de resolución | Catálogo editable, código estable, activar/desactivar |
| Perfiles de identificador | Versionado, reemplazo explícito, validación de ejemplos y rechazos |
| Políticas de numeración | Alta con secuencia PostgreSQL, consulta, activación/desactivación, vista previa de formato |
| Roles de parte | Catálogo editable con protección de registros del sistema |
| Áreas | CRUD lógico, código único, filtros, protección de dependencias |
| Anaqueles | CRUD lógico, capacidad configurable, relación con área |
| Bandejas | CRUD lógico, relación con anaquel, estado |
| Posiciones | CRUD lógico, estado `AVAILABLE/BLOCKED/RETIRED`, protección de ocupación |
| Capacidad | Planificador determinista, vista previa y aplicación transaccional |
| Tipos de caja | Solo consulta del enum cerrado `EXPEDIENTES` y `DOCUMENTOS_ADMINISTRATIVOS` |
| Configuración del sistema | Consulta y upsert tipado de claves no secretas |
| Auditoría | Eventos de negocio para altas, cambios, activaciones y desactivaciones |
| Pruebas | Unitarias, API e integración con PostgreSQL real |
| Documentación | API, modelo, reglas, permisos, pruebas, inventario y pendientes |

### 1.3 Fuera de alcance

- Generación automática de cajas o números visibles. B5 prepara la política; B6 consume la secuencia.
- Asignación y liberación de posiciones. B5 solo define el catálogo físico.
- Préstamos, movimientos, conciliación y planos 2D/3D.
- Administración de usuarios, roles y permisos, ya cerrada en B4.
- Cifrado o almacenamiento de secretos en `system_settings`. Las claves sensibles se rechazan.
- Edición directa de `Shelf.capacity_positions`; es una columna calculada por PostgreSQL.

### 1.4 Entregables

| Entregable | Ubicación | Acción |
|---|---|---|
| Migración de unicidad de áreas | `backend/alembic/versions/<rev>_b5_area_code_unique.py` | CREAR |
| Modelo `Area` actualizado | `backend/src/judicial_archive/modules/locations/models.py` | MODIFICAR |
| Utilidades de texto y validación | `backend/src/judicial_archive/core/text.py` | CREAR |
| Servicio de auditoría de negocio | `backend/src/judicial_archive/modules/audit/services.py` | CREAR |
| Módulo tribunales | `backend/src/judicial_archive/modules/courts/*` | CREAR/MODIFICAR |
| Módulo tipos de resolución | `backend/src/judicial_archive/modules/resolution_types/*` | CREAR |
| Módulo perfiles de identificador | `backend/src/judicial_archive/modules/identifier_profiles/*` | CREAR |
| Módulo políticas de numeración | `backend/src/judicial_archive/modules/numbering/*` | CREAR |
| Módulo roles de parte | `backend/src/judicial_archive/modules/party_roles/*` | CREAR |
| Módulo configuración | `backend/src/judicial_archive/modules/settings/*` | CREAR |
| Módulo catálogos físicos | `backend/src/judicial_archive/modules/locations/{schemas,repositories,services,routers,capacity}.py` | CREAR |
| Integración de routers | `backend/src/judicial_archive/api/v1/router.py` | MODIFICAR |
| Pruebas | `backend/tests/unit/`, `backend/tests/api/`, `backend/tests/integration/` | CREAR/MODIFICAR |
| Documentación | `docs/api.md`, `docs/modelo-de-datos.md`, `docs/reglas-de-negocio.md`, `docs/roles-y-permisos.md`, `docs/pruebas.md`, `docs/inventario-fisico.md`, `docs/pendientes-de-validacion.md` | MODIFICAR/CREAR |

### 1.5 Criterios de aceptación

- Un administrador autorizado mantiene todos los catálogos por API.
- Un usuario con `catalog.read` puede consultar; sin `catalog.manage` recibe `403` en escritura.
- Un usuario con `settings.read` puede consultar configuración; sin `settings.manage` recibe `403` en escritura.
- Desactivar un tribunal no altera cajas, expedientes ni documentos históricos.
- Los códigos `589` y `107` duplicados siguen siendo válidos.
- Crear dos áreas con el mismo código falla con `409` y la restricción `uq_areas_code` existe en PostgreSQL.
- Cambiar capacidad no elimina posiciones ocupadas ni bloqueadas de forma silenciosa.
- No existe ningún endpoint `DELETE` de catálogos.
- Toda mutación genera un `AuditEvent` con actor, acción, entidad, valores anteriores/nuevos y `request_id` cuando existe.
- Las secuencias de numeración se crean y se conservan; desactivar una política no las elimina.
- Los perfiles de identificador no se actualizan retroactivamente: se reemplazan creando una versión nueva.
- Los tipos de caja se consultan, no se administran.
- Las pruebas nuevas pasan y la suite existente no retrocede.

---

## 2. Prerrequisitos y estado real de partida

### 2.1 Verificación inicial

Ejecutar desde la raíz del repositorio:

```powershell
Set-Location C:\Users\Tony\Documents\sga
git status --short
git log --oneline -5
Set-Location backend
uv sync
uv run alembic current
uv run alembic heads
```

Resultado esperado antes de implementar B5:

- B4 cerrado en `15d0828`.
- Head Alembic `88ae4fe9cb05`.
- `docs/phases/phaseB5_guide.md` existe, pero no existe código B5.
- El árbol puede contener cambios no confirmados en `docs/phases/GUIA_DESARROLLO_FASES_SGA.md`; no sobrescribirlos.

### 2.2 Estado comprobado del código

| Elemento | Estado real |
|---|---|
| `modules/courts/models.py` | Existen `Court`, `ResolutionType`, `IdentifierFormatProfile`, `NumberingPolicy`, `PartyRole`, `SystemSetting` |
| `modules/locations/models.py` | Existen `Area`, `Shelf`, `Tray`, `Position`, `PositionBlock` |
| Schemas/repositorios/servicios/routers B5 | No existen |
| `Area.code` | Tiene formato, pero no unicidad |
| `Court.code_raw` | No es único; correcto para los duplicados históricos |
| `Shelf.capacity_positions` | Columna generada `levels * positions_per_level` |
| `Tray.position_count` | Columna editable; el planificador debe mantenerla coherente |
| `Position.status` | `AVAILABLE`, `BLOCKED`, `RETIRED` |
| `BoxType` | Enum cerrado, sin tabla |
| `AuditEvent.metadata` | Atributo Python `metadata_json` |
| Permisos | `catalog.read/manage`, `settings.read/manage` ya existen |
| `SUPERVISOR` | Tiene `catalog.manage`, `catalog.read` y `settings.read`; no `settings.manage` |
| `ADMINISTRADOR` | Tiene todos los permisos del seed |
| `CONSULTA` | Tiene `catalog.read`; no escritura |
| Secuencia inicial | `box_visible_number_seq`, inicio `4402` |

### 2.3 Reglas que no se deben romper

- `Court.code_normalized` debe ser exactamente `upper(btrim(code_raw))`.
- No crear una restricción única sobre `courts.code_raw` ni sobre `courts.code_normalized`.
- No fusionar tribunales automáticamente por código.
- No crear una tabla `box_types` ni un CRUD de tipos de caja.
- No borrar posiciones, bandejas ni secuencias para "liberar" capacidad.
- No cambiar el pasado de un perfil de identificador: crear una versión nueva.
- No añadir `format_profile_id` a `ResolutionType` en B5. El esquema B2 no lo tiene y no forma parte de esta migración.
- No usar `MAX(visible_number) + 1`; la secuencia es la fuente del próximo número.

### 2.4 Base de datos de pruebas

B5 reutiliza las fixtures de B2/B4. Las pruebas de integración requieren PostgreSQL real:

```powershell
$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://USER:PASS@localhost:5432/sga_test"
uv run pytest tests/integration -n 0
```

No ejecutar pruebas de integración contra una URL que contenga `prod`.

---

## 3. Decisiones de implementación B5

| ID | Decisión | Motivo | Consecuencia |
|---|---|---|---|
| D-B5-01 | Reutilizar `catalog.read`, `catalog.manage`, `settings.read`, `settings.manage` | Evitar permisos ficticios y mantener la matriz B4 | No hay permisos por catálogo individual |
| D-B5-02 | No exponer `DELETE`; usar activar/desactivar/retirar | Preservar historia y relaciones | La UI debe usar acciones de baja lógica |
| D-B5-03 | Añadir `uq_areas_code` | B1 exige código de área único; el modelo actual no lo cumple | Migración y preflight de duplicados |
| D-B5-04 | `BoxType` sigue siendo enum cerrado | El negocio no confirmó tipos extensibles | Solo `GET /box-types` |
| D-B5-05 | Perfiles de identificador versionados con reemplazo | Evitar reinterpretar datos históricos | `PATCH` limitado y `POST /{id}/replace` |
| D-B5-06 | Validar patrones con límite, ejemplos y rechazos | Reducir errores de configuración | Riesgo residual de ReDoS documentado |
| D-B5-07 | Crear la secuencia PostgreSQL al crear la política | La secuencia es la fuente de verdad | DDL y fila en una sola transacción |
| D-B5-08 | No implementar reinicio anual automático | No hay requisito cerrado | Solo se acepta `reset_policy=NEVER` en B5 |
| D-B5-09 | Planificador de capacidad puro, máximo 5000 posiciones | Evitar operaciones masivas no verificables | Vista previa y aplicación con conflictos |
| D-B5-10 | No borrar posiciones/bandejas; retirar o desactivar | Mantener trazabilidad física | Reactivación dentro del objetivo |
| D-B5-11 | Configuración tipada y sin secretos | `SystemSetting` no es un almacén de secretos | Rechazar claves y valores sensibles |
| D-B5-12 | Auditoría en la misma transacción | Evitar cambios sin trazabilidad | Helper `record_audit_event` y pruebas |
| D-B5-13 | `PartyRole` se administra en B5 | El modelo existe y B6/B7 lo necesitan | CRUD lógico con `is_system` protegido |
| D-B5-14 | Códigos de tribunal editables pero auditados | No son clave; se corrigen errores históricos | No hay unicidad ni fusión automática |
| D-B5-15 | Semántica de `SADM`, `SPEN`, `RPE` no se inventa | Falta validación institucional (D-07) | Nombres/descripciones editables; no expandir siglas |

### 3.1 Incertidumbres que no bloquean B5

- Nombre y semántica definitivos de `SADM`, `SPEN`, `RPE`: se cargan como catálogo editable y se validan después.
- Tipos de caja adicionales: no se implementan; se registra la necesidad si aparece.
- Capacidad inicial de anaqueles: los seed actuales tienen `levels=NULL` y `positions_per_level=NULL`; B5 permite configurarla, pero no inventa valores.
- Política de reinicio anual: se rechaza hasta que exista una regla operativa y una estrategia de concurrencia.
- Formato exacto de perfiles por tribunal/periodo: se configura con ejemplos y rechazos, no con una lista fija.

---

## 4. Árbol de archivos

### 4.1 Crear

```text
backend/src/judicial_archive/core/text.py
backend/src/judicial_archive/modules/audit/services.py
backend/src/judicial_archive/modules/courts/schemas.py
backend/src/judicial_archive/modules/courts/repositories.py
backend/src/judicial_archive/modules/courts/services.py
backend/src/judicial_archive/modules/courts/routers.py
backend/src/judicial_archive/modules/resolution_types/__init__.py
backend/src/judicial_archive/modules/resolution_types/schemas.py
backend/src/judicial_archive/modules/resolution_types/repositories.py
backend/src/judicial_archive/modules/resolution_types/services.py
backend/src/judicial_archive/modules/resolution_types/routers.py
backend/src/judicial_archive/modules/identifier_profiles/__init__.py
backend/src/judicial_archive/modules/identifier_profiles/schemas.py
backend/src/judicial_archive/modules/identifier_profiles/repositories.py
backend/src/judicial_archive/modules/identifier_profiles/services.py
backend/src/judicial_archive/modules/identifier_profiles/routers.py
backend/src/judicial_archive/modules/numbering/__init__.py
backend/src/judicial_archive/modules/numbering/schemas.py
backend/src/judicial_archive/modules/numbering/repositories.py
backend/src/judicial_archive/modules/numbering/services.py
backend/src/judicial_archive/modules/numbering/routers.py
backend/src/judicial_archive/modules/party_roles/__init__.py
backend/src/judicial_archive/modules/party_roles/schemas.py
backend/src/judicial_archive/modules/party_roles/repositories.py
backend/src/judicial_archive/modules/party_roles/services.py
backend/src/judicial_archive/modules/party_roles/routers.py
backend/src/judicial_archive/modules/settings/__init__.py
backend/src/judicial_archive/modules/settings/schemas.py
backend/src/judicial_archive/modules/settings/repositories.py
backend/src/judicial_archive/modules/settings/services.py
backend/src/judicial_archive/modules/settings/routers.py
backend/src/judicial_archive/modules/locations/schemas.py
backend/src/judicial_archive/modules/locations/repositories.py
backend/src/judicial_archive/modules/locations/services.py
backend/src/judicial_archive/modules/locations/capacity.py
backend/src/judicial_archive/modules/locations/routers.py
backend/alembic/versions/<rev>_b5_area_code_unique.py
backend/tests/unit/test_b5_text_and_validation.py
backend/tests/unit/test_b5_capacity_planner.py
backend/tests/unit/test_b5_numbering_format.py
backend/tests/api/test_b5_catalogs_api.py
backend/tests/integration/test_b5_catalogs_api.py
backend/tests/integration/test_b5_numbering_sequence.py
backend/tests/integration/test_b5_capacity.py
backend/tests/integration/test_b5_audit.py
```

### 4.2 Modificar

```text
backend/src/judicial_archive/modules/locations/models.py
backend/src/judicial_archive/api/v1/router.py
backend/tests/unit/test_schema_metadata.py
backend/tests/integration/test_schema_constraints.py
docs/api.md
docs/modelo-de-datos.md
docs/reglas-de-negocio.md
docs/roles-y-permisos.md
docs/pruebas.md
docs/inventario-fisico.md
docs/pendientes-de-validacion.md
```

`db/seed.py` solo se modifica si se aplica el ajuste opcional de la sección 19.2. No es obligatorio y no se añaden datos nuevos.

### 4.3 No crear

```text
backend/src/judicial_archive/modules/box_types/
backend/alembic/versions/*_b5_box_types.py
backend/src/judicial_archive/modules/courts/delete.py
```

No se crean endpoints, tablas ni permisos para funcionalidades que no forman parte de B5.

---

## 5. Convenciones y utilidades compartidas

### 5.1 Reglas de nombres

- Clases, funciones, módulos y columnas: inglés.
- Mensajes de API, documentación y textos visibles: español.
- Códigos visibles: mayúsculas, sin espacios accidentales.
- `sequence_name`: minúsculas, `snake_case`, máximo 63 caracteres.
- Acciones de auditoría: `entidad.accion`, por ejemplo `court.created`.
- `entity_type`: singular y estable, por ejemplo `court`, `area`, `position`.

### 5.2 Crear `backend/src/judicial_archive/core/text.py`

```python
from __future__ import annotations

import re
from datetime import date

from judicial_archive.core.errors import InvalidParameterError

_SEQUENCE_NAME = re.compile(r"^[a-z][a-z0-9_]{2,62}$")
_POSITION_CODE = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,31}$")
_TRAY_CODE = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,15}$")
_SHELF_CODE = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,15}$")
_AREA_CODE = re.compile(r"^[A-Z][A-Z0-9-]{0,15}$")
_RESOLUTION_TYPE_CODE = re.compile(r"^[A-Z][A-Z0-9_]{1,31}$")
_PARTY_ROLE_CODE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_SETTING_KEY = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")


def normalize_upper_code(value: str) -> str:
    return value.strip().upper()


def normalize_lower_key(value: str) -> str:
    return value.strip().lower()


def clean_optional_text(value: str | None, *, max_length: int) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_length:
        raise InvalidParameterError(
            "El texto supera la longitud permitida.",
            details={"max_length": max_length},
        )
    return cleaned


def ensure_pattern(
    value: str, pattern: re.Pattern[str], *, field: str, message: str
) -> str:
    cleaned = value.strip()
    if not pattern.fullmatch(cleaned):
        raise InvalidParameterError(message, details={"field": field})
    return cleaned


def ensure_area_code(value: str) -> str:
    return ensure_pattern(
        normalize_upper_code(value),
        _AREA_CODE,
        field="code",
        message="El codigo de area no tiene un formato valido.",
    )


def ensure_resolution_type_code(value: str) -> str:
    return ensure_pattern(
        normalize_upper_code(value),
        _RESOLUTION_TYPE_CODE,
        field="code",
        message="El codigo de tipo de resolucion no tiene un formato valido.",
    )


def ensure_party_role_code(value: str) -> str:
    return ensure_pattern(
        normalize_upper_code(value),
        _PARTY_ROLE_CODE,
        field="code",
        message="El codigo de rol de parte no tiene un formato valido.",
    )


def ensure_tray_code(value: str) -> str:
    return ensure_pattern(
        normalize_upper_code(value),
        _TRAY_CODE,
        field="code",
        message="El codigo de bandeja no tiene un formato valido.",
    )


def ensure_shelf_code(value: str) -> str:
    return ensure_pattern(
        normalize_upper_code(value),
        _SHELF_CODE,
        field="code",
        message="El codigo de anaquel no tiene un formato valido.",
    )


def ensure_position_code(value: str) -> str:
    return ensure_pattern(
        normalize_upper_code(value),
        _POSITION_CODE,
        field="code",
        message="El codigo de posicion no tiene un formato valido.",
    )


def ensure_sequence_name(value: str) -> str:
    return ensure_pattern(
        normalize_lower_key(value),
        _SEQUENCE_NAME,
        field="sequence_name",
        message="El nombre de secuencia no tiene un formato valido.",
    )


def ensure_setting_key(value: str) -> str:
    return ensure_pattern(
        normalize_lower_key(value),
        _SETTING_KEY,
        field="key",
        message="La clave de configuracion no tiene un formato valido.",
    )


def validate_effective_range(
    effective_from: date | None, effective_to: date | None
) -> None:
    if (
        effective_from is not None
        and effective_to is not None
        and effective_to < effective_from
    ):
        raise InvalidParameterError(
            "La fecha de fin de vigencia no puede ser anterior a la de inicio.",
            details={
                "effective_from": effective_from.isoformat(),
                "effective_to": effective_to.isoformat(),
            },
        )


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
```

**Regla:** la base de datos sigue siendo la última defensa. Las funciones anteriores mejoran el error de API, pero los `CHECK` existentes no se eliminan.

### 5.3 Añadir constantes de estado

No crear un enum nuevo. Usar `CatalogStatus`, `CourtStatus`, `AreaStatus`, `ShelfStatus`, `TrayStatus` y `PositionStatus` de `core/enums.py`. En Pydantic se aceptan los literales en mayúsculas que ya persiste la base de datos.

### 5.4 Paginación y ordenamiento

Reutilizar `Page`, `PageParams`, `SortOrder`, `pagination_params` y `build_sort_params` de `core/pagination.py`.

Reglas:

- Tamaño máximo: 100.
- Orden por defecto: `created_at desc` o `code asc`, según el catálogo.
- `sort_by` solo admite campos de una lista blanca.
- `q` busca en código y nombre; nunca en notas.
- Los filtros de estado usan valores exactos.
- Las búsquedas usan `ilike` con `escape_like`.
- No devolver `total` calculado con una consulta sin filtros.

### 5.5 Errores

Usar las excepciones de `core/errors.py`:

| Situación | Excepción | HTTP |
|---|---|---|
| No existe | `NotFoundError` | 404 |
| Duplicado | `ConflictError` | 409 |
| Valor inválido de negocio | `InvalidParameterError` | 422 |
| Permiso insuficiente | `require_permissions` | 403 |
| Conflicto de capacidad/estado | `ConflictError` | 409 |

No devolver `HTTPException` genérica en servicios nuevos salvo integración con B4. No exponer detalles internos de SQLAlchemy.

### 5.6 Auditoría de negocio

`security_events` es para autenticación y seguridad. Los cambios de catálogo usan `audit_events`.

Crear `backend/src/judicial_archive/modules/audit/services.py`:

```python
from __future__ import annotations

import ipaddress
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.enums import AuditActorType, AuditResult, AuditSource
from judicial_archive.modules.audit.models import AuditEvent
from judicial_archive.modules.users.models import User


def _client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    raw = request.client.host
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return None


def _request_id(request: Request | None) -> str | None:
    if request is None:
        return None
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else None


async def record_audit_event(
    session: AsyncSession,
    *,
    request: Request | None,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    result: AuditResult = AuditResult.SUCCESS,
    source: AuditSource = AuditSource.API,
) -> AuditEvent:
    user_agent = None
    if request is not None:
        user_agent = (request.headers.get("user-agent") or "").strip()[:512] or None

    event = AuditEvent(
        actor_type=AuditActorType.USER.value if actor else AuditActorType.SYSTEM.value,
        actor_user_id=actor.id if actor else None,
        actor_label=actor.username if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_data=before,
        after_data=after,
        metadata_json=metadata,
        request_id=_request_id(request),
        ip_address=_client_ip(request),
        user_agent=user_agent,
        source=source.value,
        result=result.value,
    )
    session.add(event)
    await session.flush()
    return event
```

Reglas:

- Llamar **antes** del `commit` de la operación.
- Pasar `before` y `after` solo con campos relevantes; no incluir objetos ORM.
- No guardar tokens, contraseñas ni patrones que contengan secretos.
- Para fallos de negocio, usar `result=AuditResult.FAILURE` solo si la transacción no se revierte. Si se revierte, el evento también se revierte; esto es correcto para no auditar una operación inexistente.
- `request` puede ser `None` en scripts y tareas.
- `metadata_json` es el nombre correcto del atributo; la columna física es `metadata`.

### 5.7 Snapshot de entidades

Cada servicio debe construir snapshots JSON serializables. Ejemplo:

```python
def court_snapshot(court: Court) -> dict[str, object]:
    return {
        "code_raw": court.code_raw,
        "code_normalized": court.code_normalized,
        "name": court.name,
        "court_type": court.court_type,
        "jurisdiction": court.jurisdiction,
        "status": court.status,
        "effective_from": court.effective_from.isoformat()
        if court.effective_from
        else None,
        "effective_to": court.effective_to.isoformat() if court.effective_to else None,
        "source": court.source,
        "notes": court.notes,
    }
```

No incluir `created_at`, `updated_at` ni `version` salvo que expliquen la operación.

---

## 6. Cambio de esquema: unicidad de `areas.code`

### 6.1 Modificar el modelo

En `backend/src/judicial_archive/modules/locations/models.py`, añadir `UniqueConstraint` a `Area.__table_args__`:

```python
class Area(UUIDPrimaryKeyMixin, TimestampMixin, OptimisticLockMixin, Base):
    __tablename__ = "areas"
    __table_args__ = (
        UniqueConstraint("code", name="uq_areas_code"),
        check_in("status", AreaStatus, name="ck_areas_status"),
        CheckConstraint("code ~ '^[A-Z][A-Z0-9-]{0,15}$'", name="ck_areas_code_format"),
        CheckConstraint("length(btrim(name)) > 0", name="ck_areas_name_not_empty"),
    )
```

No cambiar el tipo de `code` ni su longitud. La normalización a mayúsculas se hace en el servicio y el `CHECK` sigue validando el valor persistido.

### 6.2 Preflight obligatorio antes de migrar

```sql
SELECT code, count(*) AS total
FROM areas
GROUP BY code
HAVING count(*) > 1
ORDER BY code;
```

Si devuelve filas, **detenerse**. No eliminar áreas ni renombrarlas automáticamente. Registrar el conflicto en `docs/pendientes-de-validacion.md` y pedir decisión humana. La migración no debe resolver duplicados por su cuenta.

### 6.3 Generar la migración

```powershell
Set-Location backend
uv run alembic revision -m "b5 area code unique"
```

Renombrar el archivo generado a `<rev>_b5_area_code_unique.py` y revisar manualmente:

```python
"""b5 area code unique

Revision ID: <rev>
Revises: 88ae4fe9cb05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "<rev>"
down_revision: str | Sequence[str] | None = "88ae4fe9cb05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_areas_code", "areas", ["code"])


def downgrade() -> None:
    op.drop_constraint("uq_areas_code", "areas", type_="unique")
```
### 6.4 Aplicar y verificar

```powershell
uv run alembic upgrade head
uv run alembic current
uv run python -c "from sqlalchemy import create_engine, inspect; import os; e=create_engine(os.environ['SGA_DATABASE_URL']); print([c['name'] for c in inspect(e).get_unique_constraints('areas')])"
```

La salida debe incluir `uq_areas_code`.

### 6.5 Prueba de migración

Añadir a `tests/integration/test_schema_constraints.py`:

```python
@pytest.mark.asyncio
async def test_area_code_is_unique(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await _insert(session, "areas", code="Z", name="Zona Z")
        await session.commit()
        await _expect_insert_violation(
            session, "areas", code="Z", name="Zona duplicada"
        )
```

También actualizar `tests/unit/test_schema_metadata.py` para comprobar que la tabla `areas` contiene una restricción única sobre `code`.

### 6.6 Reversión

`downgrade` elimina la restricción. Es una operación segura solo si no se introdujeron duplicados después de aplicar la migración. Antes de revertir:

```sql
SELECT code, count(*) FROM areas GROUP BY code HAVING count(*) > 1;
```

Si hay duplicados, no revertir sin un plan de datos.

---

## 7. Módulo Tribunales

### 7.1 Esquemas `modules/courts/schemas.py`

```python
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

CourtStatusValue = Literal["ACTIVE", "INACTIVE"]


class CourtCreate(BaseModel):
    code_raw: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)
    court_type: str | None = Field(default=None, max_length=80)
    jurisdiction: str | None = Field(default=None, max_length=120)
    effective_from: date | None = None
    effective_to: date | None = None
    source: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("code_raw", "name")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El valor no puede estar vacio.")
        return value

    @field_validator("court_type", "jurisdiction", "source", "notes")
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class CourtUpdate(BaseModel):
    code_raw: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    court_type: str | None = Field(default=None, max_length=80)
    jurisdiction: str | None = Field(default=None, max_length=120)
    effective_from: date | None = None
    effective_to: date | None = None
    source: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("code_raw", "name")
    @classmethod
    def _not_blank_when_present(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("El valor no puede estar vacio.")
        return value


class CourtOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code_raw: str
    code_normalized: str
    name: str
    court_type: str | None
    jurisdiction: str | None
    status: str
    effective_from: date | None
    effective_to: date | None
    source: str | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class CourtStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
```

Notas:

- `version` viene de `OptimisticLockMixin`.
- El estado no se modifica por `PATCH`; se usan endpoints explícitos para auditar la transición.
- `CourtUpdate` usa `exclude_unset=True` para distinguir “no enviado” de `null`.
- `code_raw` sigue siendo editable, pero la operación se audita y no se usa como clave.

### 7.2 Repositorio `modules/courts/repositories.py`

```python
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.enums import CourtStatus
from judicial_archive.core.pagination import SortOrder
from judicial_archive.core.text import escape_like
from judicial_archive.modules.courts.models import Court


class CourtsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, court_id: UUID) -> Court | None:
        return await self.session.get(Court, court_id)

    async def list_courts(
        self,
        *,
        q: str | None,
        status: str | None,
        court_type: str | None,
        effective_on: date | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Court], int]:
        conditions = []
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(
                or_(
                    Court.code_normalized.ilike(pattern, escape="\\"),
                    Court.name.ilike(pattern, escape="\\"),
                )
            )
        if status:
            conditions.append(Court.status == status)
        if court_type:
            conditions.append(Court.court_type == court_type)
        if effective_on:
            conditions.append(
                or_(
                    Court.effective_from.is_(None), Court.effective_from <= effective_on
                )
            )
            conditions.append(
                or_(Court.effective_to.is_(None), Court.effective_to >= effective_on)
            )

        base = select(Court).where(*conditions)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        column = getattr(Court, sort_by)
        ordering = column.asc() if order is SortOrder.ASC else column.desc()
        result = await self.session.execute(
            base.order_by(ordering, Court.id.asc()).offset(offset).limit(limit)
        )
        return result.scalars().all(), int(total or 0)

    async def count_by_normalized_code(self, code_normalized: str) -> int:
        result = await self.session.scalar(
            select(func.count())
            .select_from(Court)
            .where(
                Court.code_normalized == code_normalized,
                Court.status == CourtStatus.ACTIVE.value,
            )
        )
        return int(result or 0)
```

`id.asc()` como desempate garantiza paginación estable.

### 7.3 Servicio `modules/courts/services.py`

```python
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.enums import AuditSource, CourtStatus
from judicial_archive.core.errors import (
    ConflictError,
    InvalidParameterError,
    NotFoundError,
)
from judicial_archive.core.pagination import Page, PageParams, SortOrder
from judicial_archive.core.text import (
    clean_optional_text,
    normalize_upper_code,
    validate_effective_range,
)
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.courts import schemas
from judicial_archive.modules.courts.models import Court
from judicial_archive.modules.courts.repositories import CourtsRepository
from judicial_archive.modules.users.models import User

_ALLOWED_SORT = frozenset(
    {"code_normalized", "name", "status", "created_at", "updated_at"}
)

_COURT_STATUS_ACTIONS = {
    CourtStatus.ACTIVE.value: "court.activated",
    CourtStatus.INACTIVE.value: "court.deactivated",
}


def court_snapshot(court: Court) -> dict[str, object]:
    return {
        "code_raw": court.code_raw,
        "code_normalized": court.code_normalized,
        "name": court.name,
        "court_type": court.court_type,
        "jurisdiction": court.jurisdiction,
        "status": court.status,
        "effective_from": court.effective_from.isoformat()
        if court.effective_from
        else None,
        "effective_to": court.effective_to.isoformat() if court.effective_to else None,
        "source": court.source,
        "notes": court.notes,
    }


def _validate(
    court_type: str | None, jurisdiction: str | None
) -> tuple[str | None, str | None]:
    return (
        clean_optional_text(court_type, max_length=80),
        clean_optional_text(jurisdiction, max_length=120),
    )


async def list_courts(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    status: str | None,
    court_type: str | None,
    effective_on: date | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.CourtOut]:
    repo = CourtsRepository(session)
    rows, total = await repo.list_courts(
        q=q,
        status=status,
        court_type=court_type,
        effective_on=effective_on,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.CourtOut.model_validate(row) for row in rows]
    return Page[schemas.CourtOut].build(items, total=total, params=params)


async def get_court(session: AsyncSession, court_id: UUID) -> schemas.CourtOut:
    court = await CourtsRepository(session).get_by_id(court_id)
    if court is None:
        raise NotFoundError("Tribunal no encontrado.")
    return schemas.CourtOut.model_validate(court)


async def create_court(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.CourtCreate,
) -> schemas.CourtOut:
    validate_effective_range(body.effective_from, body.effective_to)
    court_type, jurisdiction = _validate(body.court_type, body.jurisdiction)
    code_normalized = normalize_upper_code(body.code_raw)
    duplicates = await CourtsRepository(session).count_by_normalized_code(
        code_normalized
    )

    court = Court(
        code_raw=body.code_raw.strip(),
        code_normalized=code_normalized,
        name=body.name.strip(),
        court_type=court_type,
        jurisdiction=jurisdiction,
        status=CourtStatus.ACTIVE.value,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
        source=clean_optional_text(body.source, max_length=64),
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    session.add(court)
    await session.flush()

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="court.created",
        entity_type="court",
        entity_id=court.id,
        after=court_snapshot(court),
        metadata={"duplicate_active_code": duplicates > 0},
        source=AuditSource.API,
    )
    await session.commit()
    await session.refresh(court)
    return schemas.CourtOut.model_validate(court)


async def update_court(
    request: Request,
    session: AsyncSession,
    actor: User,
    court_id: UUID,
    body: schemas.CourtUpdate,
) -> schemas.CourtOut:
    repo = CourtsRepository(session)
    court = await repo.get_by_id(court_id)
    if court is None:
        raise NotFoundError("Tribunal no encontrado.")

    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return schemas.CourtOut.model_validate(court)

    before = court_snapshot(court)
    if "code_raw" in changes:
        code_raw = str(changes["code_raw"]).strip()
        court.code_raw = code_raw
        court.code_normalized = normalize_upper_code(code_raw)
    if "name" in changes:
        court.name = str(changes["name"]).strip()
    if "court_type" in changes:
        court.court_type = clean_optional_text(changes["court_type"], max_length=80)
    if "jurisdiction" in changes:
        court.jurisdiction = clean_optional_text(
            changes["jurisdiction"], max_length=120
        )
    if "effective_from" in changes:
        court.effective_from = changes["effective_from"]
    if "effective_to" in changes:
        court.effective_to = changes["effective_to"]
    if "source" in changes:
        court.source = clean_optional_text(changes["source"], max_length=64)
    if "notes" in changes:
        court.notes = clean_optional_text(changes["notes"], max_length=1000)

    validate_effective_range(court.effective_from, court.effective_to)
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="court.updated",
        entity_type="court",
        entity_id=court.id,
        before=before,
        after=court_snapshot(court),
    )
    await session.commit()
    await session.refresh(court)
    return schemas.CourtOut.model_validate(court)


async def set_court_status(
    request: Request,
    session: AsyncSession,
    actor: User,
    court_id: UUID,
    target: CourtStatus,
    reason: str | None,
) -> schemas.CourtOut:
    court = await CourtsRepository(session).get_by_id(court_id)
    if court is None:
        raise NotFoundError("Tribunal no encontrado.")
    if court.status == target.value:
        raise ConflictError("El tribunal ya tiene el estado solicitado.")
    if target is CourtStatus.INACTIVE and not (reason or "").strip():
        raise InvalidParameterError("La desactivacion requiere un motivo.")

    before = court_snapshot(court)
    court.status = target.value
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action=_COURT_STATUS_ACTIONS[target.value],
        entity_type="court",
        entity_id=court.id,
        before=before,
        after=court_snapshot(court),
        metadata={"reason": clean_optional_text(reason, max_length=500)},
    )
    await session.commit()
    await session.refresh(court)
    return schemas.CourtOut.model_validate(court)
```

### 7.4 Router `modules/courts/routers.py`

```python
from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.enums import CourtStatus
from judicial_archive.core.pagination import (
    Page,
    PageParams,
    SortOrder,
    build_sort_params,
    pagination_params,
)
from judicial_archive.modules.courts import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/courts", tags=["Catalogos - Tribunales"])
_ALLOWED_SORT = frozenset(
    {"code_normalized", "name", "status", "created_at", "updated_at"}
)


@router.get("", response_model=Page[schemas.CourtOut])
async def list_courts(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=120)] = None,
    court_status: Annotated[CourtStatus | None, Query(alias="status")] = None,
    court_type: Annotated[str | None, Query(max_length=80)] = None,
    effective_on: date | None = None,
    sort_by: str | None = None,
    order: SortOrder = SortOrder.ASC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.CourtOut]:
    sort = build_sort_params(sort_by, order, allowed_fields=_ALLOWED_SORT)
    return await services.list_courts(
        session,
        params=params,
        q=q,
        status=court_status.value if court_status else None,
        court_type=court_type,
        effective_on=effective_on,
        sort_by=sort.sort_by or "name",
        order=sort.order,
    )


@router.get("/{court_id}", response_model=schemas.CourtOut)
async def get_court(
    court_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.CourtOut:
    return await services.get_court(session, court_id)


@router.post("", response_model=schemas.CourtOut, status_code=status.HTTP_201_CREATED)
async def create_court(
    request: Request,
    body: schemas.CourtCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.CourtOut:
    return await services.create_court(request, session, current_user, body)


@router.patch("/{court_id}", response_model=schemas.CourtOut)
async def update_court(
    request: Request,
    court_id: UUID,
    body: schemas.CourtUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.CourtOut:
    return await services.update_court(request, session, current_user, court_id, body)


@router.post("/{court_id}/activate", response_model=schemas.CourtOut)
async def activate_court(
    request: Request,
    court_id: UUID,
    body: schemas.CourtStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.CourtOut:
    return await services.set_court_status(
        request, session, current_user, court_id, CourtStatus.ACTIVE, body.reason
    )


@router.post("/{court_id}/deactivate", response_model=schemas.CourtOut)
async def deactivate_court(
    request: Request,
    court_id: UUID,
    body: schemas.CourtStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.CourtOut:
    return await services.set_court_status(
        request, session, current_user, court_id, CourtStatus.INACTIVE, body.reason
    )
```

### 7.5 Contrato de tribunales

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| GET | `/api/v1/courts` | `catalog.read` | Lista paginada con `q`, `status`, `court_type`, `effective_on` |
| GET | `/api/v1/courts/{id}` | `catalog.read` | Detalle |
| POST | `/api/v1/courts` | `catalog.manage` | Alta; permite códigos duplicados |
| PATCH | `/api/v1/courts/{id}` | `catalog.manage` | Modifica datos; no cambia estado |
| POST | `/api/v1/courts/{id}/activate` | `catalog.manage` | Reactiva |
| POST | `/api/v1/courts/{id}/deactivate` | `catalog.manage` | Desactiva con motivo |
| DELETE | — | — | No existe |

### 7.6 Reglas de tribunales

- `code_normalized` se calcula con `normalize_upper_code`, equivalente a `upper(btrim(...))`.
- Un código duplicado se permite y se registra en auditoría como `duplicate_active_code=true` si ya existía uno activo.
- No se fusionan registros.
- Desactivar no modifica cajas, expedientes, documentos ni perfiles.
- No se permite crear o reactivar con un rango de vigencia inválido.
- La desactivación exige motivo; la activación no.
- El estado `INACTIVE` no bloquea consultas históricas.
- `PATCH` no acepta `status` para evitar transiciones accidentales.

---

## 8. Módulo Tipos de resolución

### 8.1 Alcance

`ResolutionType` es un catálogo editable. El código es estable y único; el nombre y la descripción se pueden corregir. La semántica de `SADM`, `SPEN` y `RPE` **no se inventa**: los registros se crean con nombres editables y se validan con el área usuaria (D-07).

El modelo actual no tiene `format_profile_id` ni vigencias. No añadirlos en B5. Si se necesitan, será una decisión y migración posterior.

### 8.2 Esquemas `modules/resolution_types/schemas.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

CatalogStatusValue = Literal["ACTIVE", "INACTIVE"]


class ResolutionTypeCreate(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("code")
    @classmethod
    def _code_format(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized or not normalized[0].isalpha():
            raise ValueError("El codigo debe comenzar con una letra.")
        if not all(ch.isalnum() or ch == "_" for ch in normalized):
            raise ValueError("El codigo solo admite letras, digitos y guion bajo.")
        return normalized

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El nombre no puede estar vacio.")
        return value


class ResolutionTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)


class ResolutionTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


class ResolutionTypeStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
```

### 8.3 Repositorio `modules/resolution_types/repositories.py`

```python
from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.pagination import SortOrder
from judicial_archive.core.text import escape_like
from judicial_archive.modules.courts.models import ResolutionType

_SORT_FIELDS = frozenset({"code", "name", "status", "created_at", "updated_at"})


class ResolutionTypesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, item_id: UUID) -> ResolutionType | None:
        return await self.session.get(ResolutionType, item_id)

    async def get_by_code(self, code: str) -> ResolutionType | None:
        return await self.session.scalar(
            select(ResolutionType).where(ResolutionType.code == code)
        )

    async def list_items(
        self,
        *,
        q: str | None,
        status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[ResolutionType], int]:
        if sort_by not in _SORT_FIELDS:
            raise ValueError("Campo de ordenamiento no permitido.")

        conditions = []
        if q:
            pattern = f"%{escape_like(q)}%"
            conditions.append(
                or_(
                    ResolutionType.code.ilike(pattern, escape="\\"),
                    ResolutionType.name.ilike(pattern, escape="\\"),
                )
            )
        if status:
            conditions.append(ResolutionType.status == status)

        total = await self.session.scalar(
            select(func.count()).select_from(ResolutionType).where(*conditions)
        )
        column = getattr(ResolutionType, sort_by)
        ordering = column.asc() if order == SortOrder.ASC else column.desc()
        rows = (
            await self.session.scalars(
                select(ResolutionType)
                .where(*conditions)
                .order_by(ordering, ResolutionType.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return rows, int(total or 0)
```

### 8.4 Servicio `modules/resolution_types/services.py`

```python
from __future__ import annotations

from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import (
    ConflictError,
    InvalidParameterError,
    NotFoundError,
)
from judicial_archive.core.pagination import Page, PageParams, SortOrder
from judicial_archive.core.text import ensure_resolution_type_code
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.courts.models import ResolutionType
from judicial_archive.modules.resolution_types import schemas
from judicial_archive.modules.resolution_types.repositories import (
    ResolutionTypesRepository,
)
from judicial_archive.modules.users.models import User


def _snapshot(item: ResolutionType) -> dict[str, object]:
    return {
        "code": item.code,
        "name": item.name,
        "description": item.description,
        "status": item.status,
    }


async def _get_or_404(repo: ResolutionTypesRepository, item_id: UUID) -> ResolutionType:
    item = await repo.get_by_id(item_id)
    if item is None:
        raise NotFoundError("Tipo de resolucion no encontrado.")
    return item


async def list_resolution_types(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.ResolutionTypeOut]:
    rows, total = await ResolutionTypesRepository(session).list_items(
        q=q,
        status=status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.ResolutionTypeOut.model_validate(row) for row in rows]
    return Page[schemas.ResolutionTypeOut].build(items, total=total, params=params)


async def get_resolution_type(
    session: AsyncSession, item_id: UUID
) -> schemas.ResolutionTypeOut:
    item = await _get_or_404(ResolutionTypesRepository(session), item_id)
    return schemas.ResolutionTypeOut.model_validate(item)


async def create_resolution_type(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.ResolutionTypeCreate,
) -> schemas.ResolutionTypeOut:
    repo = ResolutionTypesRepository(session)
    code = ensure_resolution_type_code(body.code)
    if await repo.get_by_code(code) is not None:
        raise ConflictError("Ya existe un tipo de resolucion con ese codigo.")

    item = ResolutionType(
        code=code,
        name=body.name.strip(),
        description=(body.description or "").strip() or None,
        status="ACTIVE",
    )
    session.add(item)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Ya existe un tipo de resolucion con ese codigo.") from exc

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="resolution_type.created",
        entity_type="resolution_type",
        entity_id=item.id,
        after=_snapshot(item),
    )
    await session.commit()
    await session.refresh(item)
    return schemas.ResolutionTypeOut.model_validate(item)


async def update_resolution_type(
    request: Request,
    session: AsyncSession,
    actor: User,
    item_id: UUID,
    body: schemas.ResolutionTypeUpdate,
) -> schemas.ResolutionTypeOut:
    repo = ResolutionTypesRepository(session)
    item = await _get_or_404(repo, item_id)
    before = _snapshot(item)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("name") is not None:
        name = changes["name"].strip()
        if not name:
            raise InvalidParameterError("El nombre no puede estar vacio.")
        item.name = name
    if "description" in changes:
        item.description = (changes["description"] or "").strip() or None
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="resolution_type.updated",
        entity_type="resolution_type",
        entity_id=item.id,
        before=before,
        after=_snapshot(item),
    )
    await session.commit()
    await session.refresh(item)
    return schemas.ResolutionTypeOut.model_validate(item)


async def set_resolution_type_status(
    request: Request,
    session: AsyncSession,
    actor: User,
    item_id: UUID,
    *,
    active: bool,
    reason: str | None,
) -> schemas.ResolutionTypeOut:
    repo = ResolutionTypesRepository(session)
    item = await _get_or_404(repo, item_id)
    before = _snapshot(item)
    if active:
        item.status = "ACTIVE"
        action = "resolution_type.activated"
    else:
        if not reason or not reason.strip():
            from judicial_archive.core.errors import InvalidParameterError

            raise InvalidParameterError("La desactivacion requiere motivo.")
        item.status = "INACTIVE"
        action = "resolution_type.deactivated"

    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action=action,
        entity_type="resolution_type",
        entity_id=item.id,
        before=before,
        after=_snapshot(item),
        metadata={"reason": reason} if reason else None,
    )
    await session.commit()
    await session.refresh(item)
    return schemas.ResolutionTypeOut.model_validate(item)
```

### 8.5 Router `modules/resolution_types/routers.py`

```python
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.modules.users import permissions
from judicial_archive.core.pagination import (
    Page,
    PageParams,
    SortOrder,
    pagination_params,
)
from judicial_archive.modules.resolution_types import schemas, services
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/resolution-types", tags=["resolution-types"])


@router.get("", response_model=Page[schemas.ResolutionTypeOut])
async def list_resolution_types(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    sort_by: Annotated[str, Query()] = "code",
    order: Annotated[SortOrder, Query()] = SortOrder.ASC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.ResolutionTypeOut]:
    return await services.list_resolution_types(
        session,
        params=params,
        q=q,
        status=status_filter,
        sort_by=sort_by,
        order=order,
    )


@router.get("/{item_id}", response_model=schemas.ResolutionTypeOut)
async def get_resolution_type(
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.ResolutionTypeOut:
    return await services.get_resolution_type(session, item_id)


@router.post(
    "", response_model=schemas.ResolutionTypeOut, status_code=status.HTTP_201_CREATED
)
async def create_resolution_type(
    request: Request,
    body: schemas.ResolutionTypeCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.ResolutionTypeOut:
    return await services.create_resolution_type(request, session, current_user, body)


@router.patch("/{item_id}", response_model=schemas.ResolutionTypeOut)
async def update_resolution_type(
    request: Request,
    item_id: UUID,
    body: schemas.ResolutionTypeUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.ResolutionTypeOut:
    return await services.update_resolution_type(
        request, session, current_user, item_id, body
    )


@router.post("/{item_id}/activate", response_model=schemas.ResolutionTypeOut)
async def activate_resolution_type(
    request: Request,
    item_id: UUID,
    body: schemas.ResolutionTypeStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.ResolutionTypeOut:
    return await services.set_resolution_type_status(
        request,
        session,
        current_user,
        item_id,
        active=True,
        reason=body.reason,
    )


@router.post("/{item_id}/deactivate", response_model=schemas.ResolutionTypeOut)
async def deactivate_resolution_type(
    request: Request,
    item_id: UUID,
    body: schemas.ResolutionTypeStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.ResolutionTypeOut:
    return await services.set_resolution_type_status(
        request,
        session,
        current_user,
        item_id,
        active=False,
        reason=body.reason,
    )
```

### 8.6 Contrato

| Método | Ruta | Permiso |
|---|---|---|
| GET | `/api/v1/resolution-types` | `catalog.read` |
| GET | `/api/v1/resolution-types/{id}` | `catalog.read` |
| POST | `/api/v1/resolution-types` | `catalog.manage` |
| PATCH | `/api/v1/resolution-types/{id}` | `catalog.manage` |
| POST | `/api/v1/resolution-types/{id}/activate` | `catalog.manage` |
| POST | `/api/v1/resolution-types/{id}/deactivate` | `catalog.manage` |
| DELETE | — | No existe |

### 8.7 Datos iniciales

No ampliar `seed.py` con nombres inventados. Si el área usuaria confirma la semántica, añadir un seed idempotente con `code`, `name` y `description`. Mientras tanto, el catálogo puede empezar vacío y administrarse por API.

---

## 9. Módulo Perfiles de identificador

### 9.1 Reglas de negocio

- Un perfil pertenece a un tribunal y a un `identifier_kind`.
- Solo puede existir **un perfil activo** por `(court_id, identifier_kind)`; el índice parcial `uq_identifier_format_profiles_active` ya lo garantiza.
- Un cambio de patrón no revalida datos históricos.
- La actualización de patrón se realiza con `POST /identifier-profiles/{id}/replace`, que crea una versión nueva y desactiva la anterior.
- `PATCH` solo permite `notes` y `effective_to`.
- Si `strict=true`, debe existir `pattern` y al menos 3 ejemplos válidos.
- Los `rejects` no pueden coincidir con el patrón.
- El patrón se limita a 255 caracteres.
- Se rechazan construcciones con riesgo evidente de retroceso catastrófico y retroreferencias numéricas.
- El riesgo residual de ReDoS se documenta y se mitiga con permisos de administrador y límites de longitud.

### 9.2 Esquemas `modules/identifier_profiles/schemas.py`

```python
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

IdentifierKindValue = Literal["NUC", "PROCESS_NUMBER", "SENTENCE"]


class IdentifierProfileCreate(BaseModel):
    court_id: UUID
    identifier_kind: IdentifierKindValue
    pattern: str | None = Field(default=None, max_length=255)
    tokens: dict[str, Any] | None = None
    examples: list[str] | None = Field(default=None, max_length=50)
    rejects: list[str] | None = Field(default=None, max_length=50)
    strict: bool = False
    effective_from: date | None = None
    effective_to: date | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("pattern")
    @classmethod
    def _pattern_not_blank(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("examples", "rejects")
    @classmethod
    def _values_not_blank(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError("Los ejemplos y rechazos no pueden estar vacios.")
        return cleaned


class IdentifierProfileReplace(BaseModel):
    pattern: str | None = Field(default=None, max_length=255)
    tokens: dict[str, Any] | None = None
    examples: list[str] | None = Field(default=None, max_length=50)
    rejects: list[str] | None = Field(default=None, max_length=50)
    strict: bool = False
    effective_from: date
    notes: str | None = Field(default=None, max_length=1000)


class IdentifierProfileUpdate(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)
    effective_to: date | None = None


class IdentifierProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    court_id: UUID
    identifier_kind: str
    pattern: str | None
    tokens: dict[str, Any] | None
    examples: list[Any] | None
    rejects: list[Any] | None
    strict: bool
    is_active: bool
    effective_from: date
    effective_to: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class IdentifierProfileStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
```

### 9.3 Validación del patrón

Crear las funciones en `modules/identifier_profiles/services.py`:

```python
from __future__ import annotations

import re
from datetime import date

from judicial_archive.core.errors import InvalidParameterError
from judicial_archive.core.text import validate_effective_range

_NESTED_QUANTIFIER = re.compile(
    r"\((?:[^()]|\([^()]*\))*[+*][^()]*\)[+*{]"
    r"|\[[^\]]*[+*][^\]]*\][+*{]"
)
_NUMERIC_BACKREF = re.compile(r"\\[1-9]")


def validate_identifier_pattern(
    *,
    pattern: str | None,
    examples: list[str] | None,
    rejects: list[str] | None,
    strict: bool,
    effective_from: date,
    effective_to: date | None,
) -> None:
    validate_effective_range(effective_from, effective_to)
    if strict and not pattern:
        raise InvalidParameterError("Un perfil estricto requiere patron.")
    if not pattern:
        return
    if len(pattern) > 255:
        raise InvalidParameterError("El patron supera 255 caracteres.")
    if _NESTED_QUANTIFIER.search(pattern):
        raise InvalidParameterError(
            "El patron contiene cuantificadores anidados potencialmente peligrosos."
        )
    if _NUMERIC_BACKREF.search(pattern):
        raise InvalidParameterError("El patron no admite retroreferencias numericas.")

    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise InvalidParameterError(
            "El patron no es una expresion regular valida.",
            details={"error": str(exc)},
        ) from exc

    cleaned_examples = examples or []
    if strict and len(cleaned_examples) < 3:
        raise InvalidParameterError("Un perfil estricto requiere al menos 3 ejemplos.")

    invalid_examples = [
        item for item in cleaned_examples if compiled.fullmatch(item) is None
    ]
    if invalid_examples:
        raise InvalidParameterError(
            "Uno o mas ejemplos no cumplen el patron.",
            details={"invalid_examples": invalid_examples[:10]},
        )

    accepted_rejects = [
        item for item in (rejects or []) if compiled.fullmatch(item) is not None
    ]
    if accepted_rejects:
        raise InvalidParameterError(
            "Uno o mas rechazos cumplen el patron.",
            details={"invalid_rejects": accepted_rejects[:10]},
        )
```

**Limitación documentada:** Python `re` no permite timeout por llamada. El control es administrativo, se limita el tamaño y se rechazan formas obvias. Si en producción se requieren patrones hostiles o de terceros, evaluar `regex` con timeout en una fase posterior; no añadir esa dependencia sin análisis.

### 9.4 Repositorio `modules/identifier_profiles/repositories.py`

```python
from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.modules.courts.models import IdentifierFormatProfile


class IdentifierProfilesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, profile_id: UUID) -> IdentifierFormatProfile | None:
        return await self.session.get(IdentifierFormatProfile, profile_id)

    async def get_active_for_update(
        self, court_id: UUID, kind: str
    ) -> IdentifierFormatProfile | None:
        return await self.session.scalar(
            select(IdentifierFormatProfile)
            .where(
                IdentifierFormatProfile.court_id == court_id,
                IdentifierFormatProfile.identifier_kind == kind,
                IdentifierFormatProfile.is_active.is_(True),
            )
            .with_for_update()
        )

    async def list_profiles(
        self,
        *,
        court_id: UUID | None,
        identifier_kind: str | None,
        is_active: bool | None,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[IdentifierFormatProfile], int]:
        conditions = []
        if court_id is not None:
            conditions.append(IdentifierFormatProfile.court_id == court_id)
        if identifier_kind is not None:
            conditions.append(
                IdentifierFormatProfile.identifier_kind == identifier_kind
            )
        if is_active is not None:
            conditions.append(IdentifierFormatProfile.is_active.is_(is_active))

        total = await self.session.scalar(
            select(func.count()).select_from(IdentifierFormatProfile).where(*conditions)
        )
        rows = (
            await self.session.scalars(
                select(IdentifierFormatProfile)
                .where(*conditions)
                .order_by(
                    IdentifierFormatProfile.effective_from.desc(),
                    IdentifierFormatProfile.id,
                )
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return rows, int(total or 0)
```

### 9.5 Servicio `modules/identifier_profiles/services.py`

Además de `validate_identifier_pattern` (sección 9.3), añadir:

```python
from datetime import date, timedelta
from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import (
    ConflictError,
    InvalidParameterError,
    NotFoundError,
)
from judicial_archive.core.pagination import Page, PageParams
from judicial_archive.core.text import validate_effective_range
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.courts.models import Court, IdentifierFormatProfile
from judicial_archive.modules.identifier_profiles import schemas
from judicial_archive.modules.identifier_profiles.repositories import (
    IdentifierProfilesRepository,
)
from judicial_archive.modules.users.models import User


def _snapshot(profile: IdentifierFormatProfile) -> dict[str, object]:
    return {
        "court_id": str(profile.court_id),
        "identifier_kind": profile.identifier_kind,
        "pattern": profile.pattern,
        "strict": profile.strict,
        "is_active": profile.is_active,
        "effective_from": profile.effective_from.isoformat(),
        "effective_to": profile.effective_to.isoformat()
        if profile.effective_to
        else None,
        "notes": profile.notes,
    }


async def _get_or_404(
    repo: IdentifierProfilesRepository, profile_id: UUID
) -> IdentifierFormatProfile:
    profile = await repo.get_by_id(profile_id)
    if profile is None:
        raise NotFoundError("Perfil de identificador no encontrado.")
    return profile


async def _require_active_court(session: AsyncSession, court_id: UUID) -> Court:
    court = await session.get(Court, court_id)
    if court is None:
        raise NotFoundError("Tribunal no encontrado.")
    if court.status != "ACTIVE":
        raise InvalidParameterError(
            "No se puede crear un perfil para un tribunal inactivo."
        )
    return court


async def list_identifier_profiles(
    session: AsyncSession,
    *,
    params: PageParams,
    court_id: UUID | None,
    identifier_kind: str | None,
    is_active: bool | None,
) -> Page[schemas.IdentifierProfileOut]:
    rows, total = await IdentifierProfilesRepository(session).list_profiles(
        court_id=court_id,
        identifier_kind=identifier_kind,
        is_active=is_active,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.IdentifierProfileOut.model_validate(row) for row in rows]
    return Page[schemas.IdentifierProfileOut].build(items, total=total, params=params)


async def get_identifier_profile(
    session: AsyncSession, profile_id: UUID
) -> schemas.IdentifierProfileOut:
    profile = await _get_or_404(IdentifierProfilesRepository(session), profile_id)
    return schemas.IdentifierProfileOut.model_validate(profile)


async def create_identifier_profile(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.IdentifierProfileCreate,
) -> schemas.IdentifierProfileOut:
    await _require_active_court(session, body.court_id)
    effective_from = body.effective_from or date.today()
    validate_identifier_pattern(
        pattern=body.pattern,
        examples=body.examples,
        rejects=body.rejects,
        strict=body.strict,
        effective_from=effective_from,
        effective_to=body.effective_to,
    )

    repo = IdentifierProfilesRepository(session)
    if (
        await repo.get_active_for_update(body.court_id, body.identifier_kind)
        is not None
    ):
        raise ConflictError(
            "Ya existe un perfil activo para ese tribunal y tipo; use /replace."
        )

    profile = IdentifierFormatProfile(
        court_id=body.court_id,
        identifier_kind=body.identifier_kind,
        pattern=body.pattern,
        tokens=body.tokens,
        examples=body.examples,
        rejects=body.rejects,
        strict=body.strict,
        is_active=True,
        effective_from=effective_from,
        effective_to=body.effective_to,
        notes=body.notes,
    )
    session.add(profile)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "Ya existe un perfil activo para ese tribunal y tipo."
        ) from exc

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="identifier_profile.created",
        entity_type="identifier_profile",
        entity_id=profile.id,
        after=_snapshot(profile),
    )
    await session.commit()
    await session.refresh(profile)
    return schemas.IdentifierProfileOut.model_validate(profile)


async def replace_identifier_profile(
    request: Request,
    session: AsyncSession,
    actor: User,
    profile_id: UUID,
    body: schemas.IdentifierProfileReplace,
) -> schemas.IdentifierProfileOut:
    repo = IdentifierProfilesRepository(session)
    old = await _get_or_404(repo, profile_id)
    if not old.is_active:
        raise ConflictError("El perfil indicado no esta activo.")
    if body.effective_from <= old.effective_from:
        raise InvalidParameterError(
            "La nueva vigencia debe comenzar despues de la vigencia del perfil anterior."
        )
    validate_identifier_pattern(
        pattern=body.pattern,
        examples=body.examples,
        rejects=body.rejects,
        strict=body.strict,
        effective_from=body.effective_from,
        effective_to=None,
    )

    old_end = body.effective_from - timedelta(days=1)
    before = _snapshot(old)
    old.is_active = False
    if old.effective_to is None or old.effective_to > old_end:
        old.effective_to = old_end
    await session.flush()

    new = IdentifierFormatProfile(
        court_id=old.court_id,
        identifier_kind=old.identifier_kind,
        pattern=body.pattern,
        tokens=body.tokens,
        examples=body.examples,
        rejects=body.rejects,
        strict=body.strict,
        is_active=True,
        effective_from=body.effective_from,
        effective_to=None,
        notes=body.notes,
    )
    session.add(new)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "No se pudo reemplazar el perfil; recargue y reintente."
        ) from exc

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="identifier_profile.replaced",
        entity_type="identifier_profile",
        entity_id=new.id,
        before=before,
        after=_snapshot(new),
    )
    await session.commit()
    await session.refresh(new)
    return schemas.IdentifierProfileOut.model_validate(new)


async def update_identifier_profile(
    request: Request,
    session: AsyncSession,
    actor: User,
    profile_id: UUID,
    body: schemas.IdentifierProfileUpdate,
) -> schemas.IdentifierProfileOut:
    repo = IdentifierProfilesRepository(session)
    profile = await _get_or_404(repo, profile_id)
    before = _snapshot(profile)
    changes = body.model_dump(exclude_unset=True)
    if "notes" in changes:
        profile.notes = changes["notes"]
    if "effective_to" in changes:
        profile.effective_to = changes["effective_to"]
        validate_effective_range(profile.effective_from, profile.effective_to)
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="identifier_profile.updated",
        entity_type="identifier_profile",
        entity_id=profile.id,
        before=before,
        after=_snapshot(profile),
    )
    await session.commit()
    await session.refresh(profile)
    return schemas.IdentifierProfileOut.model_validate(profile)


async def set_identifier_profile_status(
    request: Request,
    session: AsyncSession,
    actor: User,
    profile_id: UUID,
    *,
    active: bool,
    reason: str | None,
) -> schemas.IdentifierProfileOut:
    repo = IdentifierProfilesRepository(session)
    profile = await _get_or_404(repo, profile_id)
    if active and profile.is_active:
        return schemas.IdentifierProfileOut.model_validate(profile)
    before = _snapshot(profile)

    if active:
        if (
            await repo.get_active_for_update(profile.court_id, profile.identifier_kind)
            is not None
        ):
            raise ConflictError("Ya existe un perfil activo para ese tribunal y tipo.")
        profile.is_active = True
        action = "identifier_profile.activated"
    else:
        if not reason or not reason.strip():
            raise InvalidParameterError("La desactivacion requiere motivo.")
        profile.is_active = False
        action = "identifier_profile.deactivated"

    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action=action,
        entity_type="identifier_profile",
        entity_id=profile.id,
        before=before,
        after=_snapshot(profile),
        metadata={"reason": reason} if reason else None,
    )
    await session.commit()
    await session.refresh(profile)
    return schemas.IdentifierProfileOut.model_validate(profile)
```

### 9.6 Router `modules/identifier_profiles/routers.py`

```python
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.modules.users import permissions
from judicial_archive.core.pagination import Page, PageParams, pagination_params
from judicial_archive.modules.identifier_profiles import schemas, services
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/identifier-profiles", tags=["identifier-profiles"])


@router.get("", response_model=Page[schemas.IdentifierProfileOut])
async def list_identifier_profiles(
    params: Annotated[PageParams, Depends(pagination_params)],
    court_id: Annotated[UUID | None, Query()] = None,
    identifier_kind: Annotated[str | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.IdentifierProfileOut]:
    return await services.list_identifier_profiles(
        session,
        params=params,
        court_id=court_id,
        identifier_kind=identifier_kind,
        is_active=is_active,
    )


@router.get("/{profile_id}", response_model=schemas.IdentifierProfileOut)
async def get_identifier_profile(
    profile_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.IdentifierProfileOut:
    return await services.get_identifier_profile(session, profile_id)


@router.post(
    "", response_model=schemas.IdentifierProfileOut, status_code=status.HTTP_201_CREATED
)
async def create_identifier_profile(
    request: Request,
    body: schemas.IdentifierProfileCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.IdentifierProfileOut:
    return await services.create_identifier_profile(
        request, session, current_user, body
    )


@router.patch("/{profile_id}", response_model=schemas.IdentifierProfileOut)
async def update_identifier_profile(
    request: Request,
    profile_id: UUID,
    body: schemas.IdentifierProfileUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.IdentifierProfileOut:
    return await services.update_identifier_profile(
        request, session, current_user, profile_id, body
    )


@router.post("/{profile_id}/replace", response_model=schemas.IdentifierProfileOut)
async def replace_identifier_profile(
    request: Request,
    profile_id: UUID,
    body: schemas.IdentifierProfileReplace,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.IdentifierProfileOut:
    return await services.replace_identifier_profile(
        request, session, current_user, profile_id, body
    )


@router.post("/{profile_id}/activate", response_model=schemas.IdentifierProfileOut)
async def activate_identifier_profile(
    request: Request,
    profile_id: UUID,
    body: schemas.IdentifierProfileStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.IdentifierProfileOut:
    return await services.set_identifier_profile_status(
        request,
        session,
        current_user,
        profile_id,
        active=True,
        reason=body.reason,
    )


@router.post("/{profile_id}/deactivate", response_model=schemas.IdentifierProfileOut)
async def deactivate_identifier_profile(
    request: Request,
    profile_id: UUID,
    body: schemas.IdentifierProfileStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.IdentifierProfileOut:
    return await services.set_identifier_profile_status(
        request,
        session,
        current_user,
        profile_id,
        active=False,
        reason=body.reason,
    )
```

### 9.7 Contrato

| Método | Ruta | Permiso |
|---|---|---|
| GET | `/api/v1/identifier-profiles` | `catalog.read` |
| GET | `/api/v1/identifier-profiles/{id}` | `catalog.read` |
| POST | `/api/v1/identifier-profiles` | `catalog.manage` |
| PATCH | `/api/v1/identifier-profiles/{id}` | `catalog.manage` |
| POST | `/api/v1/identifier-profiles/{id}/replace` | `catalog.manage` |
| POST | `/api/v1/identifier-profiles/{id}/activate` | `catalog.manage` |
| POST | `/api/v1/identifier-profiles/{id}/deactivate` | `catalog.manage` |
| DELETE | — | No existe |

Filtros de lista: `court_id`, `identifier_kind`, `is_active`, `page`, `page_size`.

---

## 10. Módulo Políticas de numeración

### 10.1 Reglas de negocio

- Una política activa por alcance:
  - `GLOBAL`: una sola.
  - `COURT`: una por tribunal.
  - `BOX_TYPE`: una por tipo de caja.
  - `YEAR`: una por año.
- El alcance y sus columnas deben ser coherentes con el `CHECK` existente.
- La secuencia PostgreSQL es la fuente de verdad del próximo número.
- Crear la secuencia y la fila de política en la misma transacción.
- No usar `MAX(visible_number) + 1`.
- Desactivar una política no elimina ni reinicia la secuencia.
- No se permite reinicio automático en B5: `reset_policy` debe ser `NEVER`.
- La identidad de la política (`scope`, `court_id`, `box_type`, `year`, `sequence_name`, `start_value`, `step`) es inmutable después del alta.
- `padding` se fija en el alta; un cambio de padding alteraría la representación de números futuros y no se permite por `PATCH`.
- `prefix` y `suffix` se fijan en el alta.
- La secuencia puede tener un valor actual mayor que `start_value`; nunca se reinicia al reactivar.
- `Box.visible_number` es texto; la política solo formatea, no asigna.

### 10.2 Esquemas `modules/numbering/schemas.py`

```python
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

NumberingScopeValue = Literal["GLOBAL", "COURT", "BOX_TYPE", "YEAR"]
BoxTypeValue = Literal["EXPEDIENTES", "DOCUMENTOS_ADMINISTRATIVOS"]


class NumberingPolicyCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    description: str | None = Field(default=None, max_length=500)
    scope: NumberingScopeValue
    court_id: UUID | None = None
    box_type: BoxTypeValue | None = None
    year: int | None = Field(default=None, ge=2000, le=2200)
    sequence_name: str = Field(min_length=3, max_length=63)
    prefix: str | None = Field(default=None, max_length=32)
    suffix: str | None = Field(default=None, max_length=32)
    padding: int = Field(default=0, ge=0, le=12)
    start_value: int = Field(ge=1)
    step: int = Field(default=1, ge=1, le=1000)
    reset_policy: Literal["NEVER"] = "NEVER"
    effective_from: date | None = None
    effective_to: date | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("code", "sequence_name")
    @classmethod
    def _code_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El valor no puede estar vacio.")
        return value


class NumberingPolicyUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=500)
    effective_to: date | None = None
    notes: str | None = Field(default=None, max_length=1000)


class NumberingPolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    description: str | None
    scope: str
    court_id: UUID | None
    box_type: str | None
    year: int | None
    sequence_name: str
    prefix: str | None
    suffix: str | None
    padding: int
    start_value: int
    step: int
    reset_policy: str
    is_active: bool
    effective_from: date
    effective_to: date | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class NumberingPolicyStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class NumberingPreviewOut(BaseModel):
    policy_id: UUID
    value: int
    formatted: str
```

### 10.3 Formato y validación puros

Crear en `modules/numbering/services.py`:

```python
from __future__ import annotations

from judicial_archive.core.errors import InvalidParameterError
from judicial_archive.modules.courts.models import NumberingPolicy

_SCOPE_REQUIRED = {
    "GLOBAL": (False, False, False),
    "COURT": (True, False, False),
    "BOX_TYPE": (False, True, False),
    "YEAR": (False, False, True),
}


def validate_scope_columns(
    *,
    scope: str,
    court_id: object | None,
    box_type: str | None,
    year: int | None,
) -> None:
    try:
        require_court, require_box_type, require_year = _SCOPE_REQUIRED[scope]
    except KeyError as exc:
        raise InvalidParameterError("Alcance de numeracion invalido.") from exc
    if (court_id is not None) is not require_court:
        raise InvalidParameterError("El alcance y el tribunal no son coherentes.")
    if (box_type is not None) is not require_box_type:
        raise InvalidParameterError("El alcance y el tipo de caja no son coherentes.")
    if (year is not None) is not require_year:
        raise InvalidParameterError("El alcance y el anio no son coherentes.")


def format_visible_number(policy: NumberingPolicy, value: int) -> str:
    if value < 1:
        raise InvalidParameterError("El valor de numeracion debe ser positivo.")
    number = str(value).zfill(policy.padding)
    formatted = f"{policy.prefix or ''}{number}{policy.suffix or ''}"
    if len(formatted) > 32:
        raise InvalidParameterError(
            "El numero visible formateado supera 32 caracteres.",
            details={"formatted_length": len(formatted)},
        )
    return formatted


def validate_format_capacity(policy: NumberingPolicy) -> None:
    probe = format_visible_number(policy, max(policy.start_value, 1))
    if len(probe) > 32:
        raise InvalidParameterError(
            "La configuracion produce numeros visibles demasiado largos."
        )
```

### 10.4 Servicio de secuencia

```python
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import ConflictError, InvalidParameterError
from judicial_archive.core.text import ensure_sequence_name


async def _sequence_exists(session: AsyncSession, name: str) -> bool:
    result = await session.scalar(
        text("SELECT to_regclass(:name)"),
        {"name": f"public.{name}"},
    )
    return result is not None


async def create_sequence(
    session: AsyncSession,
    *,
    sequence_name: str,
    start_value: int,
    step: int,
) -> None:
    name = ensure_sequence_name(sequence_name)
    if await _sequence_exists(session, name):
        raise ConflictError("La secuencia ya existe.")
    await session.execute(
        text(
            f'CREATE SEQUENCE "{name}" START WITH {int(start_value)} INCREMENT BY {int(step)}'
        )
    )
```

La validación `ensure_sequence_name` impide inyección porque solo admite `^[a-z][a-z0-9_]{2,62}$`. Aun así, el nombre se entrecomilla. Los valores numéricos se convierten explícitamente a `int`; PostgreSQL no admite parámetros vinculados en todos los DDL de secuencia.

### 10.5 Repositorio `modules/numbering/repositories.py`

```python
from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.pagination import SortOrder
from judicial_archive.core.text import escape_like
from judicial_archive.modules.courts.models import NumberingPolicy

_SORT_FIELDS = frozenset(
    {"code", "scope", "is_active", "effective_from", "created_at", "updated_at"}
)


class NumberingPoliciesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, policy_id: UUID) -> NumberingPolicy | None:
        return await self.session.get(NumberingPolicy, policy_id)

    async def get_by_code(self, code: str) -> NumberingPolicy | None:
        return await self.session.scalar(
            select(NumberingPolicy).where(NumberingPolicy.code == code)
        )

    async def get_by_sequence_name(self, name: str) -> NumberingPolicy | None:
        return await self.session.scalar(
            select(NumberingPolicy).where(NumberingPolicy.sequence_name == name)
        )

    async def get_active_for_update(
        self,
        *,
        scope: str,
        court_id: UUID | None,
        box_type: str | None,
        year: int | None,
    ) -> NumberingPolicy | None:
        conditions = [
            NumberingPolicy.scope == scope,
            NumberingPolicy.is_active.is_(True),
        ]
        if scope == "COURT":
            conditions.append(NumberingPolicy.court_id == court_id)
        elif scope == "BOX_TYPE":
            conditions.append(NumberingPolicy.box_type == box_type)
        elif scope == "YEAR":
            conditions.append(NumberingPolicy.year == year)
        return await self.session.scalar(
            select(NumberingPolicy).where(*conditions).with_for_update()
        )

    async def list_items(
        self,
        *,
        q: str | None,
        scope: str | None,
        is_active: bool | None,
        court_id: UUID | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[NumberingPolicy], int]:
        if sort_by not in _SORT_FIELDS:
            raise ValueError("Campo de ordenamiento no permitido.")

        conditions = []
        if q:
            pattern = f"%{escape_like(q)}%"
            conditions.append(
                or_(
                    NumberingPolicy.code.ilike(pattern, escape="\\"),
                    NumberingPolicy.description.ilike(pattern, escape="\\"),
                )
            )
        if scope:
            conditions.append(NumberingPolicy.scope == scope)
        if is_active is not None:
            conditions.append(NumberingPolicy.is_active.is_(is_active))
        if court_id is not None:
            conditions.append(NumberingPolicy.court_id == court_id)

        total = await self.session.scalar(
            select(func.count()).select_from(NumberingPolicy).where(*conditions)
        )
        column = getattr(NumberingPolicy, sort_by)
        ordering = column.asc() if order == SortOrder.ASC else column.desc()
        rows = (
            await self.session.scalars(
                select(NumberingPolicy)
                .where(*conditions)
                .order_by(ordering, NumberingPolicy.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return rows, int(total or 0)
```

### 10.6 Servicio de políticas `modules/numbering/services.py`

Añadir al mismo archivo de las funciones puras:

```python
from datetime import date
from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import (
    ConflictError,
    InvalidParameterError,
    NotFoundError,
)
from judicial_archive.core.pagination import Page, PageParams, SortOrder
from judicial_archive.core.text import ensure_sequence_name, validate_effective_range
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.courts.models import Court, NumberingPolicy
from judicial_archive.modules.numbering import schemas
from judicial_archive.modules.numbering.repositories import NumberingPoliciesRepository
from judicial_archive.modules.users.models import User


def _snapshot(policy: NumberingPolicy) -> dict[str, object]:
    return {
        "code": policy.code,
        "scope": policy.scope,
        "court_id": str(policy.court_id) if policy.court_id else None,
        "box_type": policy.box_type,
        "year": policy.year,
        "sequence_name": policy.sequence_name,
        "prefix": policy.prefix,
        "suffix": policy.suffix,
        "padding": policy.padding,
        "start_value": policy.start_value,
        "step": policy.step,
        "reset_policy": policy.reset_policy,
        "is_active": policy.is_active,
        "effective_from": policy.effective_from.isoformat(),
        "effective_to": policy.effective_to.isoformat()
        if policy.effective_to
        else None,
    }


async def _get_or_404(
    repo: NumberingPoliciesRepository, policy_id: UUID
) -> NumberingPolicy:
    policy = await repo.get_by_id(policy_id)
    if policy is None:
        raise NotFoundError("Politica de numeracion no encontrada.")
    return policy


async def list_numbering_policies(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    scope: str | None,
    is_active: bool | None,
    court_id: UUID | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.NumberingPolicyOut]:
    rows, total = await NumberingPoliciesRepository(session).list_items(
        q=q,
        scope=scope,
        is_active=is_active,
        court_id=court_id,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.NumberingPolicyOut.model_validate(row) for row in rows]
    return Page[schemas.NumberingPolicyOut].build(items, total=total, params=params)


async def get_numbering_policy(
    session: AsyncSession, policy_id: UUID
) -> schemas.NumberingPolicyOut:
    policy = await _get_or_404(NumberingPoliciesRepository(session), policy_id)
    return schemas.NumberingPolicyOut.model_validate(policy)


async def create_numbering_policy(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.NumberingPolicyCreate,
) -> schemas.NumberingPolicyOut:
    code = body.code.strip().upper()
    sequence_name = ensure_sequence_name(body.sequence_name)
    validate_scope_columns(
        scope=body.scope,
        court_id=body.court_id,
        box_type=body.box_type,
        year=body.year,
    )

    repo = NumberingPoliciesRepository(session)
    if await repo.get_by_code(code) is not None:
        raise ConflictError("Ya existe una politica con ese codigo.")
    if await repo.get_by_sequence_name(sequence_name) is not None:
        raise ConflictError("Ya existe una politica con ese nombre de secuencia.")
    if body.scope == "COURT":
        court = await session.get(Court, body.court_id)
        if court is None:
            raise NotFoundError("Tribunal no encontrado.")
        if court.status != "ACTIVE":
            raise InvalidParameterError("El tribunal esta inactivo.")

    effective_from = body.effective_from or date.today()
    validate_effective_range(effective_from, body.effective_to)

    if (
        await repo.get_active_for_update(
            scope=body.scope,
            court_id=body.court_id,
            box_type=body.box_type,
            year=body.year,
        )
        is not None
    ):
        raise ConflictError("Ya existe una politica activa para ese alcance.")

    policy = NumberingPolicy(
        code=code,
        description=(body.description or "").strip() or None,
        scope=body.scope,
        court_id=body.court_id,
        box_type=body.box_type,
        year=body.year,
        sequence_name=sequence_name,
        prefix=body.prefix,
        suffix=body.suffix,
        padding=body.padding,
        start_value=body.start_value,
        step=body.step,
        reset_policy="NEVER",
        is_active=True,
        effective_from=effective_from,
        effective_to=body.effective_to,
        notes=body.notes,
    )
    validate_format_capacity(policy)
    session.add(policy)
    try:
        await session.flush()
        await create_sequence(
            session,
            sequence_name=sequence_name,
            start_value=body.start_value,
            step=body.step,
        )
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("No se pudo crear la politica de numeracion.") from exc

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="numbering_policy.created",
        entity_type="numbering_policy",
        entity_id=policy.id,
        after=_snapshot(policy),
    )
    await session.commit()
    await session.refresh(policy)
    return schemas.NumberingPolicyOut.model_validate(policy)


async def update_numbering_policy(
    request: Request,
    session: AsyncSession,
    actor: User,
    policy_id: UUID,
    body: schemas.NumberingPolicyUpdate,
) -> schemas.NumberingPolicyOut:
    repo = NumberingPoliciesRepository(session)
    policy = await _get_or_404(repo, policy_id)
    before = _snapshot(policy)
    changes = body.model_dump(exclude_unset=True)
    if "description" in changes:
        policy.description = (changes["description"] or "").strip() or None
    if "notes" in changes:
        policy.notes = changes["notes"]
    if "effective_to" in changes:
        policy.effective_to = changes["effective_to"]
        validate_effective_range(policy.effective_from, policy.effective_to)
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="numbering_policy.updated",
        entity_type="numbering_policy",
        entity_id=policy.id,
        before=before,
        after=_snapshot(policy),
    )
    await session.commit()
    await session.refresh(policy)
    return schemas.NumberingPolicyOut.model_validate(policy)


async def set_numbering_policy_status(
    request: Request,
    session: AsyncSession,
    actor: User,
    policy_id: UUID,
    *,
    active: bool,
    reason: str | None,
) -> schemas.NumberingPolicyOut:
    repo = NumberingPoliciesRepository(session)
    policy = await _get_or_404(repo, policy_id)
    before = _snapshot(policy)

    if active:
        if not await _sequence_exists(session, policy.sequence_name):
            raise ConflictError("La secuencia de la politica no existe.")
        other = await repo.get_active_for_update(
            scope=policy.scope,
            court_id=policy.court_id,
            box_type=policy.box_type,
            year=policy.year,
        )
        if other is not None and other.id != policy.id:
            raise ConflictError("Ya existe otra politica activa para ese alcance.")
        policy.is_active = True
        action = "numbering_policy.activated"
    else:
        if not reason or not reason.strip():
            raise InvalidParameterError("La desactivacion requiere motivo.")
        policy.is_active = False
        action = "numbering_policy.deactivated"

    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action=action,
        entity_type="numbering_policy",
        entity_id=policy.id,
        before=before,
        after=_snapshot(policy),
        metadata={"reason": reason} if reason else None,
    )
    await session.commit()
    await session.refresh(policy)
    return schemas.NumberingPolicyOut.model_validate(policy)


async def preview_numbering_policy(
    session: AsyncSession, policy_id: UUID, value: int
) -> schemas.NumberingPreviewOut:
    policy = await _get_or_404(NumberingPoliciesRepository(session), policy_id)
    return schemas.NumberingPreviewOut(
        policy_id=policy.id,
        value=value,
        formatted=format_visible_number(policy, value),
    )
```

**Nota:** `create_sequence` es DDL transaccional en PostgreSQL. Si el `commit` falla después, la secuencia también se revierte. No ejecutar la creación en una sesión separada.

### 10.7 Router `modules/numbering/routers.py`

```python
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.modules.users import permissions
from judicial_archive.core.pagination import (
    Page,
    PageParams,
    SortOrder,
    pagination_params,
)
from judicial_archive.modules.numbering import schemas, services
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/numbering-policies", tags=["numbering-policies"])


@router.get("", response_model=Page[schemas.NumberingPolicyOut])
async def list_numbering_policies(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    scope: Annotated[str | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    court_id: Annotated[UUID | None, Query()] = None,
    sort_by: Annotated[str, Query()] = "code",
    order: Annotated[SortOrder, Query()] = SortOrder.ASC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.NumberingPolicyOut]:
    return await services.list_numbering_policies(
        session,
        params=params,
        q=q,
        scope=scope,
        is_active=is_active,
        court_id=court_id,
        sort_by=sort_by,
        order=order,
    )


@router.get("/{policy_id}", response_model=schemas.NumberingPolicyOut)
async def get_numbering_policy(
    policy_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.NumberingPolicyOut:
    return await services.get_numbering_policy(session, policy_id)


@router.get("/{policy_id}/preview", response_model=schemas.NumberingPreviewOut)
async def preview_numbering_policy(
    policy_id: UUID,
    value: Annotated[int, Query(ge=1)] = 1,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.NumberingPreviewOut:
    return await services.preview_numbering_policy(session, policy_id, value)


@router.post(
    "", response_model=schemas.NumberingPolicyOut, status_code=status.HTTP_201_CREATED
)
async def create_numbering_policy(
    request: Request,
    body: schemas.NumberingPolicyCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SETTINGS_MANAGE)),
) -> schemas.NumberingPolicyOut:
    return await services.create_numbering_policy(request, session, current_user, body)


@router.patch("/{policy_id}", response_model=schemas.NumberingPolicyOut)
async def update_numbering_policy(
    request: Request,
    policy_id: UUID,
    body: schemas.NumberingPolicyUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SETTINGS_MANAGE)),
) -> schemas.NumberingPolicyOut:
    return await services.update_numbering_policy(
        request, session, current_user, policy_id, body
    )


@router.post("/{policy_id}/activate", response_model=schemas.NumberingPolicyOut)
async def activate_numbering_policy(
    request: Request,
    policy_id: UUID,
    body: schemas.NumberingPolicyStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SETTINGS_MANAGE)),
) -> schemas.NumberingPolicyOut:
    return await services.set_numbering_policy_status(
        request,
        session,
        current_user,
        policy_id,
        active=True,
        reason=body.reason,
    )


@router.post("/{policy_id}/deactivate", response_model=schemas.NumberingPolicyOut)
async def deactivate_numbering_policy(
    request: Request,
    policy_id: UUID,
    body: schemas.NumberingPolicyStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SETTINGS_MANAGE)),
) -> schemas.NumberingPolicyOut:
    return await services.set_numbering_policy_status(
        request,
        session,
        current_user,
        policy_id,
        active=False,
        reason=body.reason,
    )
```

### 10.8 Contrato

| Método | Ruta | Permiso |
|---|---|---|
| GET | `/api/v1/numbering-policies` | `catalog.read` |
| GET | `/api/v1/numbering-policies/{id}` | `catalog.read` |
| POST | `/api/v1/numbering-policies` | `settings.manage` |
| PATCH | `/api/v1/numbering-policies/{id}` | `settings.manage` |
| POST | `/api/v1/numbering-policies/{id}/activate` | `settings.manage` |
| POST | `/api/v1/numbering-policies/{id}/deactivate` | `settings.manage` |
| GET | `/api/v1/numbering-policies/{id}/preview?value=4402` | `catalog.read` |
| DELETE | — | No existe |

**Permiso:** la política de numeración es configuración global; se usa `settings.manage`, no `catalog.manage`. `SUPERVISOR` puede consultar (`catalog.read` y `settings.read`) pero no modificar.

### 10.9 Datos iniciales

El seed existente crea `BOX_GLOBAL` con secuencia `box_visible_number_seq`, inicio `4402`, `padding=0`, `reset_policy=NEVER`. B5 no debe duplicarla. El seed debe seguir siendo idempotente y usar la misma secuencia.

### 10.10 Pruebas críticas

- Crear política `GLOBAL` con secuencia nueva: existe fila y secuencia.
- Crear con `sequence_name` inválido: `422`.
- Crear con nombre de secuencia existente: `409`.
- Intentar `reset_policy=YEARLY`: `422` por el esquema Pydantic.
- Desactivar: la secuencia sigue existiendo y conserva su valor.
- Reactivar: no reinicia la secuencia.
- Intentar cambiar `sequence_name` por `PATCH`: no está en el esquema; no se acepta.
- Dos políticas activas `GLOBAL`: `409`.
- `preview` no modifica `last_value` de la secuencia.

---

## 11. Módulo Roles de parte

### 11.1 Alcance

`PartyRole` ya existe y contiene el rol de sistema `IMPUTADO`. B5 lo expone como catálogo editable para que B6/B7 no tengan que modificar código cuando se confirmen otros roles.

### 11.2 Esquemas

```python
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PartyRoleCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)


class PartyRoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)


class PartyRoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    is_system: bool
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


class PartyRoleStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
```

### 11.3 Reglas

- Código único, mayúsculas, formato `^[A-Z][A-Z0-9_]{1,63}$`.
- El código no se modifica después del alta.
- `is_system=True` no se puede desactivar ni eliminar.
- `IMPUTADO` se mantiene activo.
- No se borra; se desactiva con motivo.
- `q` busca en código y nombre.
- Orden permitido: `code`, `name`, `status`, `created_at`, `updated_at`.

### 11.4 Repositorio `modules/party_roles/repositories.py`

```python
from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.pagination import SortOrder
from judicial_archive.core.text import escape_like
from judicial_archive.modules.courts.models import PartyRole

_SORT_FIELDS = frozenset({"code", "name", "status", "created_at", "updated_at"})


class PartyRolesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, item_id: UUID) -> PartyRole | None:
        return await self.session.get(PartyRole, item_id)

    async def get_by_code(self, code: str) -> PartyRole | None:
        return await self.session.scalar(
            select(PartyRole).where(PartyRole.code == code)
        )

    async def list_items(
        self,
        *,
        q: str | None,
        status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[PartyRole], int]:
        if sort_by not in _SORT_FIELDS:
            raise ValueError("Campo de ordenamiento no permitido.")
        conditions = []
        if q:
            pattern = f"%{escape_like(q)}%"
            conditions.append(
                or_(
                    PartyRole.code.ilike(pattern, escape="\\"),
                    PartyRole.name.ilike(pattern, escape="\\"),
                )
            )
        if status:
            conditions.append(PartyRole.status == status)

        total = await self.session.scalar(
            select(func.count()).select_from(PartyRole).where(*conditions)
        )
        column = getattr(PartyRole, sort_by)
        ordering = column.asc() if order == SortOrder.ASC else column.desc()
        rows = (
            await self.session.scalars(
                select(PartyRole)
                .where(*conditions)
                .order_by(ordering, PartyRole.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return rows, int(total or 0)
```

### 11.5 Servicio `modules/party_roles/services.py`

```python
from __future__ import annotations

from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import (
    ConflictError,
    InvalidParameterError,
    NotFoundError,
)
from judicial_archive.core.pagination import Page, PageParams, SortOrder
from judicial_archive.core.text import ensure_party_role_code
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.courts.models import PartyRole
from judicial_archive.modules.party_roles import schemas
from judicial_archive.modules.party_roles.repositories import PartyRolesRepository
from judicial_archive.modules.users.models import User


def _snapshot(item: PartyRole) -> dict[str, object]:
    return {
        "code": item.code,
        "name": item.name,
        "description": item.description,
        "is_system": item.is_system,
        "status": item.status,
    }


async def _get_or_404(repo: PartyRolesRepository, item_id: UUID) -> PartyRole:
    item = await repo.get_by_id(item_id)
    if item is None:
        raise NotFoundError("Rol de parte no encontrado.")
    return item


async def list_party_roles(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.PartyRoleOut]:
    rows, total = await PartyRolesRepository(session).list_items(
        q=q,
        status=status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.PartyRoleOut.model_validate(row) for row in rows]
    return Page[schemas.PartyRoleOut].build(items, total=total, params=params)


async def get_party_role(session: AsyncSession, item_id: UUID) -> schemas.PartyRoleOut:
    item = await _get_or_404(PartyRolesRepository(session), item_id)
    return schemas.PartyRoleOut.model_validate(item)


async def create_party_role(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.PartyRoleCreate,
) -> schemas.PartyRoleOut:
    repo = PartyRolesRepository(session)
    code = ensure_party_role_code(body.code)
    if await repo.get_by_code(code) is not None:
        raise ConflictError("Ya existe un rol de parte con ese codigo.")
    item = PartyRole(
        code=code,
        name=body.name.strip(),
        description=(body.description or "").strip() or None,
        is_system=False,
        status="ACTIVE",
    )
    session.add(item)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Ya existe un rol de parte con ese codigo.") from exc
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="party_role.created",
        entity_type="party_role",
        entity_id=item.id,
        after=_snapshot(item),
    )
    await session.commit()
    await session.refresh(item)
    return schemas.PartyRoleOut.model_validate(item)


async def update_party_role(
    request: Request,
    session: AsyncSession,
    actor: User,
    item_id: UUID,
    body: schemas.PartyRoleUpdate,
) -> schemas.PartyRoleOut:
    repo = PartyRolesRepository(session)
    item = await _get_or_404(repo, item_id)
    before = _snapshot(item)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("name") is not None:
        name = changes["name"].strip()
        if not name:
            raise InvalidParameterError("El nombre no puede estar vacio.")
        item.name = name
    if "description" in changes:
        item.description = (changes["description"] or "").strip() or None
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="party_role.updated",
        entity_type="party_role",
        entity_id=item.id,
        before=before,
        after=_snapshot(item),
    )
    await session.commit()
    await session.refresh(item)
    return schemas.PartyRoleOut.model_validate(item)


async def set_party_role_status(
    request: Request,
    session: AsyncSession,
    actor: User,
    item_id: UUID,
    *,
    active: bool,
    reason: str | None,
) -> schemas.PartyRoleOut:
    repo = PartyRolesRepository(session)
    item = await _get_or_404(repo, item_id)
    if not active and item.is_system:
        raise InvalidParameterError("No se puede desactivar un rol de sistema.")
    before = _snapshot(item)
    if active:
        item.status = "ACTIVE"
        action = "party_role.activated"
    else:
        if not reason or not reason.strip():
            raise InvalidParameterError("La desactivacion requiere motivo.")
        item.status = "INACTIVE"
        action = "party_role.deactivated"
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action=action,
        entity_type="party_role",
        entity_id=item.id,
        before=before,
        after=_snapshot(item),
        metadata={"reason": reason} if reason else None,
    )
    await session.commit()
    await session.refresh(item)
    return schemas.PartyRoleOut.model_validate(item)
```

### 11.6 Router `modules/party_roles/routers.py`

```python
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.modules.users import permissions
from judicial_archive.core.pagination import (
    Page,
    PageParams,
    SortOrder,
    pagination_params,
)
from judicial_archive.modules.party_roles import schemas, services
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/party-roles", tags=["party-roles"])


@router.get("", response_model=Page[schemas.PartyRoleOut])
async def list_party_roles(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    sort_by: Annotated[str, Query()] = "code",
    order: Annotated[SortOrder, Query()] = SortOrder.ASC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.PartyRoleOut]:
    return await services.list_party_roles(
        session,
        params=params,
        q=q,
        status=status_filter,
        sort_by=sort_by,
        order=order,
    )


@router.get("/{item_id}", response_model=schemas.PartyRoleOut)
async def get_party_role(
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.PartyRoleOut:
    return await services.get_party_role(session, item_id)


@router.post(
    "", response_model=schemas.PartyRoleOut, status_code=status.HTTP_201_CREATED
)
async def create_party_role(
    request: Request,
    body: schemas.PartyRoleCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PartyRoleOut:
    return await services.create_party_role(request, session, current_user, body)


@router.patch("/{item_id}", response_model=schemas.PartyRoleOut)
async def update_party_role(
    request: Request,
    item_id: UUID,
    body: schemas.PartyRoleUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PartyRoleOut:
    return await services.update_party_role(
        request, session, current_user, item_id, body
    )


@router.post("/{item_id}/activate", response_model=schemas.PartyRoleOut)
async def activate_party_role(
    request: Request,
    item_id: UUID,
    body: schemas.PartyRoleStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PartyRoleOut:
    return await services.set_party_role_status(
        request,
        session,
        current_user,
        item_id,
        active=True,
        reason=body.reason,
    )


@router.post("/{item_id}/deactivate", response_model=schemas.PartyRoleOut)
async def deactivate_party_role(
    request: Request,
    item_id: UUID,
    body: schemas.PartyRoleStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PartyRoleOut:
    return await services.set_party_role_status(
        request,
        session,
        current_user,
        item_id,
        active=False,
        reason=body.reason,
    )
```

### 11.7 Contrato

| Método | Ruta | Permiso |
|---|---|---|
| GET | `/api/v1/party-roles` | `catalog.read` |
| GET | `/api/v1/party-roles/{id}` | `catalog.read` |
| POST | `/api/v1/party-roles` | `catalog.manage` |
| PATCH | `/api/v1/party-roles/{id}` | `catalog.manage` |
| POST | `/api/v1/party-roles/{id}/activate` | `catalog.manage` |
| POST | `/api/v1/party-roles/{id}/deactivate` | `catalog.manage` |
| DELETE | — | No existe |

Acciones: `party_role.created`, `party_role.updated`, `party_role.activated`, `party_role.deactivated`.

---

## 12. Módulo Configuración del sistema

### 12.1 Alcance y límites

`SystemSetting` es configuración administrativa tipada. **No es un almacén de secretos.** Las claves y valores sensibles se rechazan. La configuración de conexión, claves de firma, contraseñas y tokens permanece en variables de entorno o en un gestor de secretos.

### 12.2 Esquemas `modules/settings/schemas.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SettingType = Literal["STRING", "INTEGER", "BOOLEAN", "JSON"]


class SettingUpsert(BaseModel):
    value: Any
    value_type: SettingType
    description: str = Field(min_length=1, max_length=500)

    @field_validator("value")
    @classmethod
    def _value_not_none(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("El valor no puede ser nulo.")
        return value


class SettingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    value: Any
    value_type: str
    description: str
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime
```

### 12.3 Validación de tipo y secretos

```python
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from judicial_archive.core.errors import InvalidParameterError

_SENSITIVE_KEY_PARTS = frozenset(
    {
        "secret",
        "password",
        "passwd",
        "token",
        "api_key",
        "apikey",
        "private_key",
        "credential",
    }
)
_MAX_JSON_BYTES = 16_384


def validate_setting_value(key: str, value: object, value_type: str) -> None:
    lowered = key.lower()
    if any(part in lowered for part in _SENSITIVE_KEY_PARTS):
        raise InvalidParameterError(
            "La clave parece contener un secreto y no se admite."
        )

    if value_type == "STRING":
        if not isinstance(value, str):
            raise InvalidParameterError("El valor debe ser texto.")
        if any(part in value.lower() for part in ("password=", "token=", "secret=")):
            raise InvalidParameterError("El valor parece contener un secreto.")
    elif value_type == "INTEGER":
        if isinstance(value, bool) or not isinstance(value, int):
            raise InvalidParameterError("El valor debe ser un entero.")
    elif value_type == "BOOLEAN":
        if not isinstance(value, bool):
            raise InvalidParameterError("El valor debe ser booleano.")
    elif value_type == "JSON":
        if not isinstance(value, (dict, list)):
            raise InvalidParameterError("El valor JSON debe ser objeto o arreglo.")
    else:
        raise InvalidParameterError("Tipo de configuracion invalido.")

    encoded = json.dumps(value, ensure_ascii=False).encode("utf-8")
    if len(encoded) > _MAX_JSON_BYTES:
        raise InvalidParameterError("El valor de configuracion supera 16 KiB.")

    if key == "system.timezone":
        if not isinstance(value, str):
            raise InvalidParameterError("La zona horaria debe ser texto.")
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise InvalidParameterError("La zona horaria no existe.") from exc
```

### 12.4 Repositorio `modules/settings/repositories.py`

```python
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.text import escape_like
from judicial_archive.modules.courts.models import SystemSetting


class SettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_key(self, key: str) -> SystemSetting | None:
        return await self.session.scalar(
            select(SystemSetting).where(SystemSetting.key == key)
        )

    async def get_by_key_for_update(self, key: str) -> SystemSetting | None:
        return await self.session.scalar(
            select(SystemSetting).where(SystemSetting.key == key).with_for_update()
        )

    async def list_items(
        self,
        *,
        q: str | None,
        value_type: str | None,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[SystemSetting], int]:
        conditions = []
        if q:
            pattern = f"%{escape_like(q)}%"
            conditions.append(
                or_(
                    SystemSetting.key.ilike(pattern, escape="\\"),
                    SystemSetting.description.ilike(pattern, escape="\\"),
                )
            )
        if value_type:
            conditions.append(SystemSetting.value_type == value_type)

        total = await self.session.scalar(
            select(func.count()).select_from(SystemSetting).where(*conditions)
        )
        rows = (
            await self.session.scalars(
                select(SystemSetting)
                .where(*conditions)
                .order_by(SystemSetting.key, SystemSetting.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return rows, int(total or 0)
```

### 12.5 Servicio `modules/settings/services.py`

```python
from __future__ import annotations

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import (
    ConflictError,
    InvalidParameterError,
    NotFoundError,
)
from judicial_archive.core.pagination import Page, PageParams
from judicial_archive.core.text import ensure_setting_key
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.courts.models import SystemSetting
from judicial_archive.modules.settings import schemas
from judicial_archive.modules.settings.repositories import SettingsRepository
from judicial_archive.modules.users.models import User


def _snapshot(item: SystemSetting) -> dict[str, object]:
    return {
        "key": item.key,
        "value": item.value,
        "value_type": item.value_type,
        "description": item.description,
    }


async def list_settings(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    value_type: str | None,
) -> Page[schemas.SettingOut]:
    rows, total = await SettingsRepository(session).list_items(
        q=q,
        value_type=value_type,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.SettingOut.model_validate(row) for row in rows]
    return Page[schemas.SettingOut].build(items, total=total, params=params)


async def get_setting(session: AsyncSession, key: str) -> schemas.SettingOut:
    item = await SettingsRepository(session).get_by_key(key)
    if item is None:
        raise NotFoundError("Configuracion no encontrada.")
    return schemas.SettingOut.model_validate(item)


async def upsert_setting(
    request: Request,
    session: AsyncSession,
    actor: User,
    key: str,
    body: schemas.SettingUpsert,
) -> schemas.SettingOut:
    normalized_key = ensure_setting_key(key)
    validate_setting_value(normalized_key, body.value, body.value_type)
    description = body.description.strip()
    if not description:
        raise InvalidParameterError("La descripcion no puede estar vacia.")

    repo = SettingsRepository(session)
    item = await repo.get_by_key_for_update(normalized_key)
    if item is None:
        item = SystemSetting(
            key=normalized_key,
            value=body.value,
            value_type=body.value_type,
            description=description,
            updated_by=actor.id,
        )
        session.add(item)
        action = "system_setting.created"
        before = None
        try:
            await session.flush()
        except IntegrityError as exc:
            await session.rollback()
            raise ConflictError(
                "La configuracion ya existe; recargue y reintente."
            ) from exc
    else:
        if item.value_type != body.value_type:
            raise ConflictError(
                "No se puede cambiar el tipo de una configuracion existente."
            )
        before = _snapshot(item)
        item.value = body.value
        item.description = description
        item.updated_by = actor.id
        action = "system_setting.updated"
        await session.flush()

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action=action,
        entity_type="system_setting",
        entity_id=item.id,
        before=before,
        after=_snapshot(item),
    )
    await session.commit()
    await session.refresh(item)
    return schemas.SettingOut.model_validate(item)
```

### 12.6 Router `modules/settings/routers.py`

```python
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.modules.users import permissions
from judicial_archive.core.pagination import Page, PageParams, pagination_params
from judicial_archive.modules.settings import schemas, services
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=Page[schemas.SettingOut])
async def list_settings(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    value_type: Annotated[str | None, Query()] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SETTINGS_READ)),
) -> Page[schemas.SettingOut]:
    return await services.list_settings(
        session,
        params=params,
        q=q,
        value_type=value_type,
    )


@router.get("/{key}", response_model=schemas.SettingOut)
async def get_setting(
    key: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SETTINGS_READ)),
) -> schemas.SettingOut:
    return await services.get_setting(session, key)


@router.put("/{key}", response_model=schemas.SettingOut)
async def upsert_setting(
    request: Request,
    key: str,
    body: schemas.SettingUpsert,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SETTINGS_MANAGE)),
) -> schemas.SettingOut:
    return await services.upsert_setting(request, session, current_user, key, body)
```

### 12.7 Contrato

| Método | Ruta | Permiso |
|---|---|---|
| GET | `/api/v1/settings` | `settings.read` |
| GET | `/api/v1/settings/{key}` | `settings.read` |
| PUT | `/api/v1/settings/{key}` | `settings.manage` |
| DELETE | — | No existe |

### 12.8 Datos iniciales

El seed existente crea `system.timezone = America/Santo_Domingo`. B5 no debe duplicarlo. Si se añaden claves nuevas, usar un seed idempotente con valor y descripción confirmados. No inventar políticas globales.

---

## 13. Tipos de caja: solo consulta

`BoxType` es un enum cerrado:

```python
class BoxType(StrEnum):
    EXPEDIENTES = "EXPEDIENTES"
    DOCUMENTOS_ADMINISTRATIVOS = "DOCUMENTOS_ADMINISTRATIVOS"
```

No crear tabla, repositorio, servicio de escritura ni permisos nuevos.

### 13.1 Esquema de salida

`BoxTypeOut` se define en `modules/locations/schemas.py` (ver sección 15). No crear un módulo `box_types`.

### 13.2 Router

```python
@router.get("/box-types", response_model=list[schemas.BoxTypeOut])
async def list_box_types(
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> list[schemas.BoxTypeOut]:
    return [
        schemas.BoxTypeOut(value=BoxType.EXPEDIENTES.value, label="Expedientes"),
        schemas.BoxTypeOut(
            value=BoxType.DOCUMENTOS_ADMINISTRATIVOS.value,
            label="Documentos administrativos",
        ),
    ]
```

Ruta final: `GET /api/v1/box-types`. No existe `POST`, `PATCH` ni `DELETE`.

Si el negocio confirma tipos extensibles, se abre una decisión nueva, se diseña una tabla `box_types`, se migran los dos valores actuales y se actualizan las FK. No hacerlo en B5 por conveniencia.

---

## 14. Catálogos físicos: reglas y límites con B6

### 14.1 Modelo existente

| Entidad | Campos relevantes | Restricciones existentes |
|---|---|---|
| `Area` | `code`, `name`, `description`, `status` | Formato de código; **sin unicidad actual** |
| `Shelf` | `area_id`, `code`, `name`, `levels`, `positions_per_level`, `capacity_positions`, `status` | Único por `(area_id, code)`; capacidad en par; columna generada |
| `Tray` | `shelf_id`, `code`, `name`, `position_count`, `status` | Único por `(shelf_id, code)` |
| `Position` | `tray_id`, `code`, `label`, `status`, `notes` | Único por `(tray_id, code)`; `AVAILABLE/BLOCKED/RETIRED` |
| `PositionBlock` | Rangos de bloqueo | Se usa en B6; B5 no crea bloqueos |

No existen columnas `display_order`. El orden será lexicográfico por `code`. Para que sea estable, los códigos generados usan ancho fijo (`N01`, `P001`, etc.).

### 14.2 Separación B5/B6

**B5:**

- Alta, edición, activación y desactivación de áreas, anaqueles, bandejas y posiciones.
- Configuración de capacidad y generación determinista de estructura.
- Consultas de estructura y ocupación teórica.
- Protección contra retirar posiciones ocupadas o bloqueadas.

**B6:**

- Asignar/liberar cajas en posiciones.
- Confirmar ubicación, mover cajas, historial y conciliación.
- Crear/cancelar `PositionBlock` con motivo y vigencia.
- Generar planos y reportes de ocupación.

**B7:** movimientos, préstamos y devoluciones.

B5 puede leer `Box.current_position_id` para impedir retirar posiciones ocupadas, pero no modifica cajas.

### 14.3 Reglas de desactivación

| Entidad | Permitido desactivar si | Si no |
|---|---|---|
| Área | No tiene anaqueles activos | `409 conflict` |
| Anaquel | No tiene bandejas activas y ninguna caja ocupa una posición | `409 conflict` |
| Bandeja | No tiene posiciones no retiradas y ninguna caja la ocupa | `409 conflict` |
| Posición | No está ocupada y no está `BLOCKED` | `409 conflict` |

No se hace cascada silenciosa. El operador debe desactivar de abajo hacia arriba.

### 14.4 Reglas de capacidad

- `Shelf.capacity_positions` es generada por PostgreSQL; nunca se asigna desde Python.
- `levels >= 1`, `positions_per_level >= 1`, total `<= 5000`.
- `levels` y `positions_per_level` se configuran juntos.
- Aumentar capacidad crea o reactiva bandejas/posiciones.
- Disminuir capacidad retira posiciones y desactiva bandejas excedentes.
- Una posición ocupada o bloqueada que quedaría fuera del objetivo produce `409`, sin cambios.
- Las posiciones retiradas se reactivan antes de crear nuevas.
- No se eliminan filas de `positions`, `trays` ni `shelves`.
- `Tray.position_count` se actualiza al número de posiciones no retiradas de la bandeja seleccionada.
- La aplicación de capacidad es transaccional y bloquea el anaquel con `FOR UPDATE`.
- La vista previa calcula el mismo plan sin modificar datos.

### 14.5 Reglas de edición

- `Area.code` se normaliza a mayúsculas y es único.
- `Shelf.code`, `Tray.code` y `Position.code` se normalizan a mayúsculas.
- No se permite mover un anaquel de área, una bandeja de anaquel ni una posición de bandeja mediante `PATCH`. Un traslado estructural requiere un flujo explícito posterior.
- El código de una posición puede corregirse si no colisiona; se audita.
- Cambiar el código de un área/anaquel/bandeja se permite con auditoría, porque la identidad es el UUID y no hay datos históricos que dependan del texto.
- No se acepta `DELETE`.

---

## 15. Esquemas de catálogos físicos

Crear `backend/src/judicial_archive/modules/locations/schemas.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

AreaStatusValue = Literal["ACTIVE", "INACTIVE"]
ShelfStatusValue = Literal["ACTIVE", "INACTIVE"]
TrayStatusValue = Literal["ACTIVE", "INACTIVE"]
PositionStatusValue = Literal["AVAILABLE", "BLOCKED", "RETIRED"]


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("El valor no puede estar vacio.")
    return value


class AreaCreate(BaseModel):
    code: str = Field(min_length=1, max_length=16)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("code", "name")
    @classmethod
    def _required_text(cls, value: str) -> str:
        return _not_blank(value)


class AreaUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=16)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class AreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


class AreaStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class CapacityTarget(BaseModel):
    levels: int = Field(ge=1, le=5000)
    positions_per_level: int = Field(ge=1, le=5000)

    @field_validator("positions_per_level")
    @classmethod
    def _max_total(cls, value: int, info: object) -> int:
        data = getattr(info, "data", {})
        levels = int(data.get("levels", 1))
        if levels * value > 5000:
            raise ValueError("La capacidad total no puede superar 5000 posiciones.")
        return value


class ShelfCreate(BaseModel):
    area_id: UUID
    code: str = Field(min_length=1, max_length=16)
    name: str | None = Field(default=None, max_length=120)
    levels: int | None = Field(default=None, ge=1, le=5000)
    positions_per_level: int | None = Field(default=None, ge=1, le=5000)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("code")
    @classmethod
    def _code_not_blank(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("positions_per_level")
    @classmethod
    def _pair_and_total(cls, value: int | None, info: object) -> int | None:
        data = getattr(info, "data", {})
        levels = data.get("levels")
        if (levels is None) != (value is None):
            raise ValueError("levels y positions_per_level deben enviarse juntos.")
        if levels is not None and int(levels) * int(value) > 5000:
            raise ValueError("La capacidad total no puede superar 5000 posiciones.")
        return value


class ShelfUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=16)
    name: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class ShelfOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    area_id: UUID
    code: str
    name: str | None
    levels: int | None
    positions_per_level: int | None
    capacity_positions: int | None
    status: str
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class ShelfStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class CapacityApplyRequest(CapacityTarget):
    expected_version: int = Field(ge=1)


class CapacityConflictOut(BaseModel):
    level: str
    code: str
    message: str


class CapacityPlanOut(BaseModel):
    shelf_id: UUID
    target_levels: int
    target_positions_per_level: int
    target_total: int
    current_total: int
    trays_to_create: int
    trays_to_reactivate: int
    trays_to_retire: int
    positions_to_create: int
    positions_to_reactivate: int
    positions_to_retire: int
    conflicts: list[CapacityConflictOut]
    can_apply: bool


class CapacityApplyOut(BaseModel):
    shelf: ShelfOut
    plan: CapacityPlanOut


class TrayCreate(BaseModel):
    shelf_id: UUID
    code: str = Field(min_length=1, max_length=16)
    name: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("code")
    @classmethod
    def _code_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class TrayUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=16)
    name: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class TrayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shelf_id: UUID
    code: str
    name: str | None
    position_count: int | None
    status: str
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class TrayStatusRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class PositionCreate(BaseModel):
    tray_id: UUID
    code: str = Field(min_length=1, max_length=32)
    label: str = Field(min_length=1, max_length=80)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("code", "label")
    @classmethod
    def _required_text(cls, value: str) -> str:
        return _not_blank(value)


class PositionUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    label: str | None = Field(default=None, min_length=1, max_length=80)
    notes: str | None = Field(default=None, max_length=1000)


class PositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tray_id: UUID
    code: str
    label: str
    status: str
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class PositionRetireRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class BoxTypeOut(BaseModel):
    value: str
    label: str
```

**Nota Pydantic:** los validadores dependientes de otros campos usan `info.data`; si el orden de campos cambia, el total se valida igualmente en el servicio. La regla autoritativa es la comprobación `levels * positions_per_level <= 5000` en el servicio y en el planificador.

---

## 16. Repositorio de catálogos físicos

Crear `backend/src/judicial_archive/modules/locations/repositories.py`:

```python
from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.pagination import SortOrder
from judicial_archive.core.text import escape_like
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.locations.models import Area, Position, Shelf, Tray


class LocationsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_area(self, area_id: UUID) -> Area | None:
        return await self.session.get(Area, area_id)

    async def get_shelf(self, shelf_id: UUID) -> Shelf | None:
        return await self.session.get(Shelf, shelf_id)

    async def get_tray(self, tray_id: UUID) -> Tray | None:
        return await self.session.get(Tray, tray_id)

    async def get_position(self, position_id: UUID) -> Position | None:
        return await self.session.get(Position, position_id)

    async def list_areas(
        self,
        *,
        q: str | None,
        status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Area], int]:
        conditions = []
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(
                or_(
                    Area.code.ilike(pattern, escape="\\"),
                    Area.name.ilike(pattern, escape="\\"),
                )
            )
        if status:
            conditions.append(Area.status == status)
        base = select(Area).where(*conditions)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        column = getattr(Area, sort_by)
        ordering = column.asc() if order is SortOrder.ASC else column.desc()
        rows = await self.session.execute(
            base.order_by(ordering, Area.id.asc()).offset(offset).limit(limit)
        )
        return rows.scalars().all(), int(total or 0)

    async def list_shelves(
        self,
        *,
        area_id: UUID | None,
        q: str | None,
        status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Shelf], int]:
        conditions = []
        if area_id:
            conditions.append(Shelf.area_id == area_id)
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(
                or_(
                    Shelf.code.ilike(pattern, escape="\\"),
                    Shelf.name.ilike(pattern, escape="\\"),
                )
            )
        if status:
            conditions.append(Shelf.status == status)
        base = select(Shelf).where(*conditions)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        column = getattr(Shelf, sort_by)
        ordering = column.asc() if order is SortOrder.ASC else column.desc()
        rows = await self.session.execute(
            base.order_by(ordering, Shelf.id.asc()).offset(offset).limit(limit)
        )
        return rows.scalars().all(), int(total or 0)

    async def list_trays(
        self,
        *,
        shelf_id: UUID | None,
        q: str | None,
        status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Tray], int]:
        conditions = []
        if shelf_id:
            conditions.append(Tray.shelf_id == shelf_id)
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(
                or_(
                    Tray.code.ilike(pattern, escape="\\"),
                    Tray.name.ilike(pattern, escape="\\"),
                )
            )
        if status:
            conditions.append(Tray.status == status)
        base = select(Tray).where(*conditions)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        column = getattr(Tray, sort_by)
        ordering = column.asc() if order is SortOrder.ASC else column.desc()
        rows = await self.session.execute(
            base.order_by(ordering, Tray.id.asc()).offset(offset).limit(limit)
        )
        return rows.scalars().all(), int(total or 0)

    async def list_positions(
        self,
        *,
        tray_id: UUID | None,
        q: str | None,
        status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Position], int]:
        conditions = []
        if tray_id:
            conditions.append(Position.tray_id == tray_id)
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(
                or_(
                    Position.code.ilike(pattern, escape="\\"),
                    Position.label.ilike(pattern, escape="\\"),
                )
            )
        if status:
            conditions.append(Position.status == status)
        base = select(Position).where(*conditions)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        column = getattr(Position, sort_by)
        ordering = column.asc() if order is SortOrder.ASC else column.desc()
        rows = await self.session.execute(
            base.order_by(ordering, Position.id.asc()).offset(offset).limit(limit)
        )
        return rows.scalars().all(), int(total or 0)

    async def count_active_shelves(self, area_id: UUID) -> int:
        result = await self.session.scalar(
            select(func.count())
            .select_from(Shelf)
            .where(Shelf.area_id == area_id, Shelf.status == "ACTIVE")
        )
        return int(result or 0)

    async def count_active_trays(self, shelf_id: UUID) -> int:
        result = await self.session.scalar(
            select(func.count())
            .select_from(Tray)
            .where(Tray.shelf_id == shelf_id, Tray.status == "ACTIVE")
        )
        return int(result or 0)

    async def count_non_retired_positions(self, tray_id: UUID) -> int:
        result = await self.session.scalar(
            select(func.count())
            .select_from(Position)
            .where(Position.tray_id == tray_id, Position.status != "RETIRED")
        )
        return int(result or 0)

    async def get_shelf_structure_for_update(
        self, shelf_id: UUID
    ) -> tuple[Shelf | None, Sequence[Tray], Sequence[Position]]:
        shelf = await self.session.scalar(
            select(Shelf).where(Shelf.id == shelf_id).with_for_update()
        )
        if shelf is None:
            return None, [], []
        trays = (
            await self.session.scalars(
                select(Tray)
                .where(Tray.shelf_id == shelf_id)
                .order_by(Tray.code, Tray.id)
                .with_for_update()
            )
        ).all()
        positions = (
            await self.session.scalars(
                select(Position)
                .join(Tray, Tray.id == Position.tray_id)
                .where(Tray.shelf_id == shelf_id)
                .order_by(Tray.code, Position.code, Position.id)
                .with_for_update()
            )
        ).all()
        return shelf, trays, positions

    async def get_shelf_structure(
        self, shelf_id: UUID
    ) -> tuple[Shelf | None, Sequence[Tray], Sequence[Position]]:
        shelf = await self.session.get(Shelf, shelf_id)
        if shelf is None:
            return None, [], []
        trays = (
            await self.session.scalars(
                select(Tray)
                .where(Tray.shelf_id == shelf_id)
                .order_by(Tray.code, Tray.id)
            )
        ).all()
        positions = (
            await self.session.scalars(
                select(Position)
                .join(Tray, Tray.id == Position.tray_id)
                .where(Tray.shelf_id == shelf_id)
                .order_by(Tray.code, Position.code, Position.id)
            )
        ).all()
        return shelf, trays, positions

    async def get_tray_structure_for_update(
        self, tray_id: UUID
    ) -> tuple[Tray | None, Sequence[Position]]:
        tray = await self.session.scalar(
            select(Tray).where(Tray.id == tray_id).with_for_update()
        )
        if tray is None:
            return None, []
        positions = (
            await self.session.scalars(
                select(Position)
                .where(Position.tray_id == tray_id)
                .order_by(Position.code, Position.id)
                .with_for_update()
            )
        ).all()
        return tray, positions

    async def occupied_position_ids(self, position_ids: Sequence[UUID]) -> set[UUID]:
        if not position_ids:
            return set()
        rows = await self.session.scalars(
            select(Box.current_position_id).where(
                Box.current_position_id.in_(position_ids)
            )
        )
        return {row for row in rows.all() if row is not None}

    async def is_position_occupied(self, position_id: UUID) -> bool:
        result = await self.session.scalar(
            select(func.count())
            .select_from(Box)
            .where(Box.current_position_id == position_id)
        )
        return bool(result)
```

**Nota:** `with_for_update()` bloquea el anaquel y las filas hijas. Las operaciones de capacidad deben usar este método; no cargar la estructura con `session.get()` y aplicarla después.

---

## 17. Planificador puro de capacidad

Crear `backend/src/judicial_archive/modules/locations/capacity.py`. El planificador **no toca la base de datos**. Recibe entidades cargadas, devuelve un plan y conflictos.

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import InvalidParameterError
from judicial_archive.modules.locations.models import Position, Shelf, Tray

MAX_CAPACITY = 5000


@dataclass(frozen=True)
class CapacityConflict:
    level: str
    code: str
    message: str


@dataclass(frozen=True)
class NewPosition:
    code: str
    label: str


@dataclass(frozen=True)
class TrayAction:
    tray_id: UUID | None
    code: str
    action: Literal["create", "reactivate", "keep", "retire"]
    target_positions: int
    new_positions: tuple[NewPosition, ...]
    reactivate_position_ids: tuple[UUID, ...]
    retire_position_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class CapacityPlan:
    shelf_id: UUID
    target_levels: int
    target_positions_per_level: int
    target_total: int
    current_total: int
    tray_actions: tuple[TrayAction, ...]
    conflicts: tuple[CapacityConflict, ...]

    @property
    def can_apply(self) -> bool:
        return not self.conflicts

    @property
    def trays_to_create(self) -> int:
        return sum(1 for action in self.tray_actions if action.action == "create")

    @property
    def trays_to_reactivate(self) -> int:
        return sum(1 for action in self.tray_actions if action.action == "reactivate")

    @property
    def trays_to_retire(self) -> int:
        return sum(1 for action in self.tray_actions if action.action == "retire")

    @property
    def positions_to_create(self) -> int:
        return sum(len(action.new_positions) for action in self.tray_actions)

    @property
    def positions_to_reactivate(self) -> int:
        return sum(len(action.reactivate_position_ids) for action in self.tray_actions)

    @property
    def positions_to_retire(self) -> int:
        return sum(len(action.retire_position_ids) for action in self.tray_actions)


def _validate_target(levels: int, positions_per_level: int) -> int:
    if levels < 1 or positions_per_level < 1:
        raise InvalidParameterError("La capacidad debe ser positiva.")
    total = levels * positions_per_level
    if total > MAX_CAPACITY:
        raise InvalidParameterError(
            "La capacidad supera el maximo permitido.",
            details={"max_capacity": MAX_CAPACITY, "requested": total},
        )
    return total


def _next_tray_code(used: set[str]) -> str:
    for number in range(1, 10_000):
        candidate = f"N{number:02d}"
        if candidate not in used:
            used.add(candidate)
            return candidate
    raise InvalidParameterError("No fue posible generar un codigo de bandeja.")


def _new_positions(
    tray_code: str,
    used_codes: set[str],
    count: int,
) -> tuple[NewPosition, ...]:
    created: list[NewPosition] = []
    for number in range(1, count + 1):
        candidate = f"P{number:03d}"
        suffix = number
        while candidate in used_codes:
            suffix += 1
            candidate = f"P{suffix:03d}"
        used_codes.add(candidate)
        created.append(
            NewPosition(
                code=candidate,
                label=f"Nivel {tray_code} - Posicion {suffix:03d}",
            )
        )
    return tuple(created)


def build_capacity_plan(
    *,
    shelf_id: UUID,
    target_levels: int,
    positions_per_level: int,
    trays: Sequence[Tray],
    positions_by_tray: dict[UUID, Sequence[Position]],
    occupied_position_ids: set[UUID],
) -> CapacityPlan:
    target_total = _validate_target(target_levels, positions_per_level)
    ordered = sorted(trays, key=lambda tray: (tray.code, str(tray.id)))
    selected = ordered[:target_levels]
    unselected = ordered[target_levels:]
    used_tray_codes = {tray.code.upper() for tray in ordered}
    actions: list[TrayAction] = []
    conflicts: list[CapacityConflict] = []

    current_total = sum(
        1
        for tray in ordered
        for position in positions_by_tray.get(tray.id, ())
        if position.status != "RETIRED"
    )

    for tray in selected:
        positions = sorted(
            positions_by_tray.get(tray.id, ()),
            key=lambda position: (position.code, str(position.id)),
        )
        non_retired = [
            position for position in positions if position.status != "RETIRED"
        ]
        retired = [position for position in positions if position.status == "RETIRED"]
        retire_ids: list[UUID] = []
        reactivate_ids: list[UUID] = []
        created: tuple[NewPosition, ...] = ()

        if len(non_retired) > positions_per_level:
            for position in non_retired[positions_per_level:]:
                if position.id in occupied_position_ids:
                    conflicts.append(
                        CapacityConflict(
                            level="position",
                            code=position.code,
                            message="La posicion esta ocupada y quedaria fuera del objetivo.",
                        )
                    )
                elif position.status == "BLOCKED":
                    conflicts.append(
                        CapacityConflict(
                            level="position",
                            code=position.code,
                            message="La posicion esta bloqueada y quedaria fuera del objetivo.",
                        )
                    )
                else:
                    retire_ids.append(position.id)
        elif len(non_retired) < positions_per_level:
            needed = positions_per_level - len(non_retired)
            reactivate_ids = [position.id for position in retired[:needed]]
            remaining = needed - len(reactivate_ids)
            used_codes = {position.code.upper() for position in positions}
            created = _new_positions(tray.code, used_codes, remaining)

        action = "reactivate" if tray.status != "ACTIVE" else "keep"
        actions.append(
            TrayAction(
                tray_id=tray.id,
                code=tray.code,
                action=action,  # type: ignore[arg-type]
                target_positions=positions_per_level,
                new_positions=created,
                reactivate_position_ids=tuple(reactivate_ids),
                retire_position_ids=tuple(retire_ids),
            )
        )

    missing_levels = target_levels - len(selected)
    for _ in range(max(0, missing_levels)):
        code = _next_tray_code(used_tray_codes)
        used_codes: set[str] = set()
        created = _new_positions(code, used_codes, positions_per_level)
        actions.append(
            TrayAction(
                tray_id=None,
                code=code,
                action="create",
                target_positions=positions_per_level,
                new_positions=created,
                reactivate_position_ids=(),
                retire_position_ids=(),
            )
        )

    for tray in unselected:
        positions = sorted(
            positions_by_tray.get(tray.id, ()),
            key=lambda position: (position.code, str(position.id)),
        )
        retire_ids: list[UUID] = []
        for position in positions:
            if position.status == "RETIRED":
                continue
            if position.id in occupied_position_ids:
                conflicts.append(
                    CapacityConflict(
                        level="position",
                        code=position.code,
                        message="La posicion esta ocupada; no se puede retirar la bandeja.",
                    )
                )
            elif position.status == "BLOCKED":
                conflicts.append(
                    CapacityConflict(
                        level="position",
                        code=position.code,
                        message="La posicion esta bloqueada; no se puede retirar la bandeja.",
                    )
                )
            else:
                retire_ids.append(position.id)
        if tray.status == "ACTIVE" or retire_ids:
            actions.append(
                TrayAction(
                    tray_id=tray.id,
                    code=tray.code,
                    action="retire",
                    target_positions=0,
                    new_positions=(),
                    reactivate_position_ids=(),
                    retire_position_ids=tuple(retire_ids),
                )
            )

    return CapacityPlan(
        shelf_id=shelf_id,
        target_levels=target_levels,
        target_positions_per_level=positions_per_level,
        target_total=target_total,
        current_total=current_total,
        tray_actions=tuple(actions),
        conflicts=tuple(conflicts),
    )


async def apply_capacity_plan(
    *,
    session: AsyncSession,
    shelf: Shelf,
    plan: CapacityPlan,
    trays_by_id: dict[UUID, Tray],
    positions_by_id: dict[UUID, Position],
) -> None:
    if not plan.can_apply:
        raise InvalidParameterError("El plan de capacidad tiene conflictos.")

    for action in plan.tray_actions:
        if action.action == "create":
            tray = Tray(
                shelf_id=shelf.id,
                code=action.code,
                name=f"Nivel {action.code}",
                position_count=action.target_positions,
                status="ACTIVE",
            )
            session.add(tray)
            await session.flush()
            for new_position in action.new_positions:
                session.add(
                    Position(
                        tray_id=tray.id,
                        code=new_position.code,
                        label=new_position.label,
                        status="AVAILABLE",
                    )
                )
            continue

        tray = trays_by_id[action.tray_id]  # type: ignore[index]
        if action.action == "retire":
            tray.status = "INACTIVE"
        else:
            tray.status = "ACTIVE"
            tray.position_count = action.target_positions

        for position_id in action.reactivate_position_ids:
            positions_by_id[position_id].status = "AVAILABLE"
        for position_id in action.retire_position_ids:
            positions_by_id[position_id].status = "RETIRED"
        for new_position in action.new_positions:
            session.add(
                Position(
                    tray_id=tray.id,
                    code=new_position.code,
                    label=new_position.label,
                    status="AVAILABLE",
                )
            )

    shelf.levels = plan.target_levels
    shelf.positions_per_level = plan.target_positions_per_level
```

`apply_capacity_plan` debe importar `AsyncSession` en el módulo. No acceder a `_sa_instance_state` ni a atributos privados de SQLAlchemy.

### 17.2 Invariantes del planificador

- El plan nunca contiene operaciones `delete`.
- Si hay conflictos, `can_apply=False` y el servicio responde `409`.
- Las posiciones retiradas se reactivan antes de crear nuevas.
- Las bandejas inactivas se reactivan antes de crear nuevas.
- Los códigos generados no colisionan con los existentes.
- El plan es determinista para el mismo estado.
- El total objetivo nunca supera 5000.
- La reducción de capacidad no toca posiciones ocupadas o bloqueadas.
- `Tray.position_count` se actualiza solo en bandejas seleccionadas; las retiradas conservan su último valor histórico.

### 17.3 Pruebas unitarias del planificador

- Aumentar de 7×7 a 7×9 crea 14 posiciones.
- Reducir de 7×9 a 7×7 retira 14 posiciones disponibles.
- Reducir con una posición ocupada en el excedente devuelve conflicto.
- Reducir con una posición bloqueada en el excedente devuelve conflicto.
- Bandeja inactiva con posiciones retiradas se reactiva y reutiliza.
- Códigos personalizados no se pisan.
- `5001` posiciones devuelve `InvalidParameterError`.
- Plan idempotente: aplicar dos veces produce como máximo creación reactivación, sin duplicados.

---

## 18. Servicios y routers de catálogos físicos

### 18.1 Servicio `modules/locations/services.py`

```python
from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.enums import AuditSource
from judicial_archive.core.errors import (
    ConflictError,
    InvalidParameterError,
    NotFoundError,
)
from judicial_archive.core.pagination import Page, PageParams, SortOrder
from judicial_archive.core.text import (
    clean_optional_text,
    ensure_area_code,
    ensure_position_code,
    ensure_shelf_code,
    ensure_tray_code,
    normalize_upper_code,
)
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.locations import capacity, schemas
from judicial_archive.modules.locations.models import Area, Position, Shelf, Tray
from judicial_archive.modules.locations.repositories import LocationsRepository
from judicial_archive.modules.users.models import User


def _area_snapshot(area: Area) -> dict[str, object]:
    return {
        "code": area.code,
        "name": area.name,
        "description": area.description,
        "status": area.status,
    }


def _shelf_snapshot(shelf: Shelf) -> dict[str, object]:
    return {
        "area_id": str(shelf.area_id),
        "code": shelf.code,
        "name": shelf.name,
        "levels": shelf.levels,
        "positions_per_level": shelf.positions_per_level,
        "capacity_positions": shelf.capacity_positions,
        "status": shelf.status,
        "notes": shelf.notes,
    }


def _tray_snapshot(tray: Tray) -> dict[str, object]:
    return {
        "shelf_id": str(tray.shelf_id),
        "code": tray.code,
        "name": tray.name,
        "position_count": tray.position_count,
        "status": tray.status,
        "notes": tray.notes,
    }


def _position_snapshot(position: Position) -> dict[str, object]:
    return {
        "tray_id": str(position.tray_id),
        "code": position.code,
        "label": position.label,
        "status": position.status,
        "notes": position.notes,
    }


async def _flush_or_conflict(session: AsyncSession, message: str) -> None:
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(message) from exc


async def _recount_tray(session: AsyncSession, tray: Tray) -> None:
    count = await LocationsRepository(session).count_non_retired_positions(tray.id)
    tray.position_count = count or None


def _plan_out(plan: capacity.CapacityPlan) -> schemas.CapacityPlanOut:
    return schemas.CapacityPlanOut(
        shelf_id=plan.shelf_id,
        target_levels=plan.target_levels,
        target_positions_per_level=plan.target_positions_per_level,
        target_total=plan.target_total,
        current_total=plan.current_total,
        trays_to_create=plan.trays_to_create,
        trays_to_reactivate=plan.trays_to_reactivate,
        trays_to_retire=plan.trays_to_retire,
        positions_to_create=plan.positions_to_create,
        positions_to_reactivate=plan.positions_to_reactivate,
        positions_to_retire=plan.positions_to_retire,
        conflicts=[
            schemas.CapacityConflictOut(
                level=item.level, code=item.code, message=item.message
            )
            for item in plan.conflicts
        ],
        can_apply=plan.can_apply,
    )


def _positions_by_tray(positions: Sequence[Position]) -> dict[UUID, list[Position]]:
    grouped: dict[UUID, list[Position]] = defaultdict(list)
    for position in positions:
        grouped[position.tray_id].append(position)
    return grouped


async def get_area(session: AsyncSession, area_id: UUID) -> schemas.AreaOut:
    area = await LocationsRepository(session).get_area(area_id)
    if area is None:
        raise NotFoundError("Area no encontrada.")
    return schemas.AreaOut.model_validate(area)


async def get_shelf(session: AsyncSession, shelf_id: UUID) -> schemas.ShelfOut:
    shelf = await LocationsRepository(session).get_shelf(shelf_id)
    if shelf is None:
        raise NotFoundError("Anaquel no encontrado.")
    return schemas.ShelfOut.model_validate(shelf)


async def get_tray(session: AsyncSession, tray_id: UUID) -> schemas.TrayOut:
    tray = await LocationsRepository(session).get_tray(tray_id)
    if tray is None:
        raise NotFoundError("Bandeja no encontrada.")
    return schemas.TrayOut.model_validate(tray)


async def get_position(session: AsyncSession, position_id: UUID) -> schemas.PositionOut:
    position = await LocationsRepository(session).get_position(position_id)
    if position is None:
        raise NotFoundError("Posicion no encontrada.")
    return schemas.PositionOut.model_validate(position)


async def list_areas(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.AreaOut]:
    rows, total = await LocationsRepository(session).list_areas(
        q=q,
        status=status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.AreaOut.model_validate(row) for row in rows]
    return Page[schemas.AreaOut].build(items, total=total, params=params)


async def create_area(
    request: Request, session: AsyncSession, actor: User, body: schemas.AreaCreate
) -> schemas.AreaOut:
    code = ensure_area_code(body.code)
    area = Area(
        code=code,
        name=body.name.strip(),
        description=clean_optional_text(body.description, max_length=500),
        status="ACTIVE",
    )
    session.add(area)
    await _flush_or_conflict(session, "Ya existe un area con ese codigo.")
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="area.created",
        entity_type="area",
        entity_id=area.id,
        after=_area_snapshot(area),
    )
    await session.commit()
    await session.refresh(area)
    return schemas.AreaOut.model_validate(area)


async def update_area(
    request: Request,
    session: AsyncSession,
    actor: User,
    area_id: UUID,
    body: schemas.AreaUpdate,
) -> schemas.AreaOut:
    area = await LocationsRepository(session).get_area(area_id)
    if area is None:
        raise NotFoundError("Area no encontrada.")
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return schemas.AreaOut.model_validate(area)
    before = _area_snapshot(area)
    if "code" in changes:
        area.code = ensure_area_code(str(changes["code"]))
    if "name" in changes:
        area.name = str(changes["name"]).strip()
    if "description" in changes:
        area.description = clean_optional_text(changes["description"], max_length=500)
    await _flush_or_conflict(session, "Ya existe un area con ese codigo.")
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="area.updated",
        entity_type="area",
        entity_id=area.id,
        before=before,
        after=_area_snapshot(area),
    )
    await session.commit()
    await session.refresh(area)
    return schemas.AreaOut.model_validate(area)


async def set_area_status(
    request: Request,
    session: AsyncSession,
    actor: User,
    area_id: UUID,
    target: str,
    reason: str | None,
) -> schemas.AreaOut:
    repo = LocationsRepository(session)
    area = await repo.get_area(area_id)
    if area is None:
        raise NotFoundError("Area no encontrada.")
    if area.status == target:
        raise ConflictError("El area ya tiene el estado solicitado.")
    if target == "INACTIVE":
        if not (reason or "").strip():
            raise InvalidParameterError("La desactivacion requiere un motivo.")
        if await repo.count_active_shelves(area.id) > 0:
            raise ConflictError("No se puede desactivar un area con anaqueles activos.")
    before = _area_snapshot(area)
    area.status = target
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="area.deactivated" if target == "INACTIVE" else "area.activated",
        entity_type="area",
        entity_id=area.id,
        before=before,
        after=_area_snapshot(area),
        metadata={"reason": clean_optional_text(reason, max_length=500)},
    )
    await session.commit()
    await session.refresh(area)
    return schemas.AreaOut.model_validate(area)


async def list_shelves(
    session: AsyncSession,
    *,
    params: PageParams,
    area_id: UUID | None,
    q: str | None,
    status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.ShelfOut]:
    rows, total = await LocationsRepository(session).list_shelves(
        area_id=area_id,
        q=q,
        status=status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.ShelfOut.model_validate(row) for row in rows]
    return Page[schemas.ShelfOut].build(items, total=total, params=params)


async def create_shelf(
    request: Request, session: AsyncSession, actor: User, body: schemas.ShelfCreate
) -> schemas.ShelfOut:
    repo = LocationsRepository(session)
    area = await repo.get_area(body.area_id)
    if area is None:
        raise NotFoundError("Area no encontrada.")
    if area.status != "ACTIVE":
        raise InvalidParameterError("No se puede crear un anaquel en un area inactiva.")

    shelf = Shelf(
        area_id=area.id,
        code=ensure_shelf_code(body.code),
        name=clean_optional_text(body.name, max_length=120),
        levels=None,
        positions_per_level=None,
        status="ACTIVE",
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    session.add(shelf)
    await _flush_or_conflict(session, "Ya existe un anaquel con ese codigo en el area.")

    plan: capacity.CapacityPlan | None = None
    if body.levels is not None and body.positions_per_level is not None:
        plan = capacity.build_capacity_plan(
            shelf_id=shelf.id,
            target_levels=body.levels,
            positions_per_level=body.positions_per_level,
            trays=[],
            positions_by_tray={},
            occupied_position_ids=set(),
        )
        await capacity.apply_capacity_plan(
            session=session, shelf=shelf, plan=plan, trays_by_id={}, positions_by_id={}
        )

    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="shelf.created",
        entity_type="shelf",
        entity_id=shelf.id,
        after=_shelf_snapshot(shelf),
        metadata={
            "capacity": None
            if plan is None
            else {
                "levels": plan.target_levels,
                "positions_per_level": plan.target_positions_per_level,
                "positions_created": plan.positions_to_create,
            }
        },
    )
    await session.commit()
    await session.refresh(shelf)
    return schemas.ShelfOut.model_validate(shelf)


async def update_shelf(
    request: Request,
    session: AsyncSession,
    actor: User,
    shelf_id: UUID,
    body: schemas.ShelfUpdate,
) -> schemas.ShelfOut:
    shelf = await LocationsRepository(session).get_shelf(shelf_id)
    if shelf is None:
        raise NotFoundError("Anaquel no encontrado.")
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return schemas.ShelfOut.model_validate(shelf)
    before = _shelf_snapshot(shelf)
    if "code" in changes:
        shelf.code = ensure_shelf_code(str(changes["code"]))
    if "name" in changes:
        shelf.name = clean_optional_text(changes["name"], max_length=120)
    if "notes" in changes:
        shelf.notes = clean_optional_text(changes["notes"], max_length=1000)
    await _flush_or_conflict(session, "Ya existe un anaquel con ese codigo en el area.")
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="shelf.updated",
        entity_type="shelf",
        entity_id=shelf.id,
        before=before,
        after=_shelf_snapshot(shelf),
    )
    await session.commit()
    await session.refresh(shelf)
    return schemas.ShelfOut.model_validate(shelf)


async def preview_capacity(
    session: AsyncSession, shelf_id: UUID, body: schemas.CapacityTarget
) -> schemas.CapacityPlanOut:
    repo = LocationsRepository(session)
    shelf, trays, positions = await repo.get_shelf_structure(shelf_id)
    if shelf is None:
        raise NotFoundError("Anaquel no encontrado.")
    occupied = await repo.occupied_position_ids([position.id for position in positions])
    plan = capacity.build_capacity_plan(
        shelf_id=shelf.id,
        target_levels=body.levels,
        positions_per_level=body.positions_per_level,
        trays=trays,
        positions_by_tray=_positions_by_tray(positions),
        occupied_position_ids=occupied,
    )
    return _plan_out(plan)


async def apply_capacity(
    request: Request,
    session: AsyncSession,
    actor: User,
    shelf_id: UUID,
    body: schemas.CapacityApplyRequest,
) -> schemas.CapacityApplyOut:
    repo = LocationsRepository(session)
    shelf, trays, positions = await repo.get_shelf_structure_for_update(shelf_id)
    if shelf is None:
        raise NotFoundError("Anaquel no encontrado.")
    if shelf.version != body.expected_version:
        raise ConflictError(
            "El anaquel fue modificado por otra operacion; recargue y reintente."
        )
    if shelf.status != "ACTIVE":
        raise InvalidParameterError(
            "No se puede cambiar la capacidad de un anaquel inactivo."
        )

    occupied = await repo.occupied_position_ids([position.id for position in positions])
    plan = capacity.build_capacity_plan(
        shelf_id=shelf.id,
        target_levels=body.levels,
        positions_per_level=body.positions_per_level,
        trays=trays,
        positions_by_tray=_positions_by_tray(positions),
        occupied_position_ids=occupied,
    )
    if not plan.can_apply:
        raise ConflictError(
            "La capacidad solicitada entra en conflicto con posiciones ocupadas o bloqueadas.",
            details={"conflicts": [item.__dict__ for item in plan.conflicts]},
        )

    before = _shelf_snapshot(shelf)
    trays_by_id = {tray.id: tray for tray in trays}
    positions_by_id = {position.id: position for position in positions}
    await capacity.apply_capacity_plan(
        session=session,
        shelf=shelf,
        plan=plan,
        trays_by_id=trays_by_id,
        positions_by_id=positions_by_id,
    )
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="shelf.capacity_applied",
        entity_type="shelf",
        entity_id=shelf.id,
        before=before,
        after=_shelf_snapshot(shelf),
        metadata={
            "target_total": plan.target_total,
            "trays_created": plan.trays_to_create,
            "trays_reactivated": plan.trays_to_reactivate,
            "trays_retired": plan.trays_to_retire,
            "positions_created": plan.positions_to_create,
            "positions_reactivated": plan.positions_to_reactivate,
            "positions_retired": plan.positions_to_retire,
        },
    )
    await session.commit()
    await session.refresh(shelf)
    return schemas.CapacityApplyOut(
        shelf=schemas.ShelfOut.model_validate(shelf), plan=_plan_out(plan)
    )


async def set_shelf_status(
    request: Request,
    session: AsyncSession,
    actor: User,
    shelf_id: UUID,
    target: str,
    reason: str | None,
) -> schemas.ShelfOut:
    repo = LocationsRepository(session)
    shelf, trays, positions = await repo.get_shelf_structure_for_update(shelf_id)
    if shelf is None:
        raise NotFoundError("Anaquel no encontrado.")
    if shelf.status == target:
        raise ConflictError("El anaquel ya tiene el estado solicitado.")
    if target == "INACTIVE":
        if not (reason or "").strip():
            raise InvalidParameterError("La desactivacion requiere un motivo.")
        if any(tray.status == "ACTIVE" for tray in trays):
            raise ConflictError(
                "No se puede desactivar un anaquel con bandejas activas."
            )
        if any(position.status != "RETIRED" for position in positions):
            raise ConflictError("Todas las posiciones deben estar retiradas.")
        if await repo.occupied_position_ids([position.id for position in positions]):
            raise ConflictError("El anaquel tiene posiciones ocupadas.")
    before = _shelf_snapshot(shelf)
    shelf.status = target
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="shelf.deactivated" if target == "INACTIVE" else "shelf.activated",
        entity_type="shelf",
        entity_id=shelf.id,
        before=before,
        after=_shelf_snapshot(shelf),
        metadata={"reason": clean_optional_text(reason, max_length=500)},
    )
    await session.commit()
    await session.refresh(shelf)
    return schemas.ShelfOut.model_validate(shelf)


async def list_trays(
    session: AsyncSession,
    *,
    params: PageParams,
    shelf_id: UUID | None,
    q: str | None,
    status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.TrayOut]:
    rows, total = await LocationsRepository(session).list_trays(
        shelf_id=shelf_id,
        q=q,
        status=status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.TrayOut.model_validate(row) for row in rows]
    return Page[schemas.TrayOut].build(items, total=total, params=params)


async def create_tray(
    request: Request, session: AsyncSession, actor: User, body: schemas.TrayCreate
) -> schemas.TrayOut:
    repo = LocationsRepository(session)
    shelf = await repo.get_shelf(body.shelf_id)
    if shelf is None:
        raise NotFoundError("Anaquel no encontrado.")
    if shelf.status != "ACTIVE":
        raise InvalidParameterError(
            "No se puede crear una bandeja en un anaquel inactivo."
        )
    tray = Tray(
        shelf_id=shelf.id,
        code=ensure_tray_code(body.code),
        name=clean_optional_text(body.name, max_length=120),
        position_count=None,
        status="ACTIVE",
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    session.add(tray)
    await _flush_or_conflict(
        session, "Ya existe una bandeja con ese codigo en el anaquel."
    )
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="tray.created",
        entity_type="tray",
        entity_id=tray.id,
        after=_tray_snapshot(tray),
    )
    await session.commit()
    await session.refresh(tray)
    return schemas.TrayOut.model_validate(tray)


async def update_tray(
    request: Request,
    session: AsyncSession,
    actor: User,
    tray_id: UUID,
    body: schemas.TrayUpdate,
) -> schemas.TrayOut:
    tray = await LocationsRepository(session).get_tray(tray_id)
    if tray is None:
        raise NotFoundError("Bandeja no encontrada.")
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return schemas.TrayOut.model_validate(tray)
    before = _tray_snapshot(tray)
    if "code" in changes:
        tray.code = ensure_tray_code(str(changes["code"]))
    if "name" in changes:
        tray.name = clean_optional_text(changes["name"], max_length=120)
    if "notes" in changes:
        tray.notes = clean_optional_text(changes["notes"], max_length=1000)
    await _flush_or_conflict(
        session, "Ya existe una bandeja con ese codigo en el anaquel."
    )
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="tray.updated",
        entity_type="tray",
        entity_id=tray.id,
        before=before,
        after=_tray_snapshot(tray),
    )
    await session.commit()
    await session.refresh(tray)
    return schemas.TrayOut.model_validate(tray)


async def set_tray_status(
    request: Request,
    session: AsyncSession,
    actor: User,
    tray_id: UUID,
    target: str,
    reason: str | None,
) -> schemas.TrayOut:
    repo = LocationsRepository(session)
    tray, positions = await repo.get_tray_structure_for_update(tray_id)
    if tray is None:
        raise NotFoundError("Bandeja no encontrada.")
    if tray.status == target:
        raise ConflictError("La bandeja ya tiene el estado solicitado.")
    if target == "INACTIVE":
        if not (reason or "").strip():
            raise InvalidParameterError("La desactivacion requiere un motivo.")
        if any(position.status != "RETIRED" for position in positions):
            raise ConflictError("Todas las posiciones deben estar retiradas.")
        occupied = await repo.occupied_position_ids(
            [position.id for position in positions]
        )
        if occupied:
            raise ConflictError("La bandeja tiene posiciones ocupadas.")
    before = _tray_snapshot(tray)
    tray.status = target
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="tray.deactivated" if target == "INACTIVE" else "tray.activated",
        entity_type="tray",
        entity_id=tray.id,
        before=before,
        after=_tray_snapshot(tray),
        metadata={"reason": clean_optional_text(reason, max_length=500)},
    )
    await session.commit()
    await session.refresh(tray)
    return schemas.TrayOut.model_validate(tray)


async def list_positions(
    session: AsyncSession,
    *,
    params: PageParams,
    tray_id: UUID | None,
    q: str | None,
    status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.PositionOut]:
    rows, total = await LocationsRepository(session).list_positions(
        tray_id=tray_id,
        q=q,
        status=status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.PositionOut.model_validate(row) for row in rows]
    return Page[schemas.PositionOut].build(items, total=total, params=params)


async def create_position(
    request: Request, session: AsyncSession, actor: User, body: schemas.PositionCreate
) -> schemas.PositionOut:
    repo = LocationsRepository(session)
    tray = await repo.get_tray(body.tray_id)
    if tray is None:
        raise NotFoundError("Bandeja no encontrada.")
    if tray.status != "ACTIVE":
        raise InvalidParameterError(
            "No se puede crear una posicion en una bandeja inactiva."
        )
    position = Position(
        tray_id=tray.id,
        code=ensure_position_code(body.code),
        label=body.label.strip(),
        status="AVAILABLE",
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    session.add(position)
    await _flush_or_conflict(
        session, "Ya existe una posicion con ese codigo en la bandeja."
    )
    await _recount_tray(session, tray)
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="position.created",
        entity_type="position",
        entity_id=position.id,
        after=_position_snapshot(position),
    )
    await session.commit()
    await session.refresh(position)
    return schemas.PositionOut.model_validate(position)


async def update_position(
    request: Request,
    session: AsyncSession,
    actor: User,
    position_id: UUID,
    body: schemas.PositionUpdate,
) -> schemas.PositionOut:
    position = await LocationsRepository(session).get_position(position_id)
    if position is None:
        raise NotFoundError("Posicion no encontrada.")
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return schemas.PositionOut.model_validate(position)
    before = _position_snapshot(position)
    if "code" in changes:
        position.code = ensure_position_code(str(changes["code"]))
    if "label" in changes:
        position.label = str(changes["label"]).strip()
    if "notes" in changes:
        position.notes = clean_optional_text(changes["notes"], max_length=1000)
    await _flush_or_conflict(
        session, "Ya existe una posicion con ese codigo en la bandeja."
    )
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="position.updated",
        entity_type="position",
        entity_id=position.id,
        before=before,
        after=_position_snapshot(position),
    )
    await session.commit()
    await session.refresh(position)
    return schemas.PositionOut.model_validate(position)


async def retire_position(
    request: Request,
    session: AsyncSession,
    actor: User,
    position_id: UUID,
    body: schemas.PositionRetireRequest,
) -> schemas.PositionOut:
    repo = LocationsRepository(session)
    position = await repo.get_position(position_id)
    if position is None:
        raise NotFoundError("Posicion no encontrada.")
    if position.status == "RETIRED":
        raise ConflictError("La posicion ya esta retirada.")
    if position.status == "BLOCKED":
        raise ConflictError("No se puede retirar una posicion bloqueada.")
    if await repo.is_position_occupied(position.id):
        raise ConflictError("No se puede retirar una posicion ocupada.")
    before = _position_snapshot(position)
    position.status = "RETIRED"
    tray = await repo.get_tray(position.tray_id)
    if tray is not None:
        await _recount_tray(session, tray)
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="position.retired",
        entity_type="position",
        entity_id=position.id,
        before=before,
        after=_position_snapshot(position),
        metadata={"reason": body.reason.strip()},
    )
    await session.commit()
    await session.refresh(position)
    return schemas.PositionOut.model_validate(position)


async def activate_position(
    request: Request, session: AsyncSession, actor: User, position_id: UUID
) -> schemas.PositionOut:
    repo = LocationsRepository(session)
    position = await repo.get_position(position_id)
    if position is None:
        raise NotFoundError("Posicion no encontrada.")
    if position.status == "AVAILABLE":
        raise ConflictError("La posicion ya esta disponible.")
    if position.status == "BLOCKED":
        raise ConflictError("Use el flujo de desbloqueo de B6.")
    before = _position_snapshot(position)
    position.status = "AVAILABLE"
    tray = await repo.get_tray(position.tray_id)
    if tray is not None:
        await _recount_tray(session, tray)
    await session.flush()
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="position.activated",
        entity_type="position",
        entity_id=position.id,
        before=before,
        after=_position_snapshot(position),
    )
    await session.commit()
    await session.refresh(position)
    return schemas.PositionOut.model_validate(position)
```

### 18.2 Reglas de los servicios físicos

- No se puede crear un anaquel, bandeja o posición bajo un padre inactivo.
- No se puede mover una entidad a otro padre por `PATCH`.
- La capacidad usa bloqueo y versión optimista.
- La vista previa usa el mismo planificador, pero no modifica datos.
- El endpoint de retiro de posición no acepta `BLOCKED`; B6 gestiona desbloqueos.
- La activación de posición retirada no comprueba ocupación porque una posición retirada no debería estar ocupada; si lo está, es un conflicto de datos y B6 debe resolverlo.
- Toda mutación registra auditoría antes del `commit`.
- Los conflictos de unicidad se convierten en `409`.

### 18.3 Routers `modules/locations/routers.py`

```python
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.enums import BoxType
from judicial_archive.core.pagination import (
    Page,
    PageParams,
    SortOrder,
    build_sort_params,
    pagination_params,
)
from judicial_archive.modules.locations import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

areas_router = APIRouter(prefix="/areas", tags=["Catalogos - Areas"])
shelves_router = APIRouter(prefix="/shelves", tags=["Catalogos - Anaqueles"])
trays_router = APIRouter(prefix="/trays", tags=["Catalogos - Bandejas"])
positions_router = APIRouter(prefix="/positions", tags=["Catalogos - Posiciones"])
box_types_router = APIRouter(tags=["Catalogos - Tipos de caja"])

_AREA_SORT = frozenset({"code", "name", "status", "created_at", "updated_at"})
_SHELF_SORT = frozenset(
    {"code", "name", "status", "capacity_positions", "created_at", "updated_at"}
)
_TRAY_SORT = frozenset({"code", "status", "position_count", "created_at", "updated_at"})
_POSITION_SORT = frozenset({"code", "label", "status", "created_at", "updated_at"})


@areas_router.get("", response_model=Page[schemas.AreaOut])
async def list_areas(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=120)] = None,
    area_status: Annotated[str | None, Query(alias="status")] = None,
    sort_by: str | None = None,
    order: SortOrder = SortOrder.ASC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.AreaOut]:
    sort = build_sort_params(sort_by, order, allowed_fields=_AREA_SORT)
    return await services.list_areas(
        session,
        params=params,
        q=q,
        status=area_status,
        sort_by=sort.sort_by or "code",
        order=sort.order,
    )


@areas_router.post(
    "", response_model=schemas.AreaOut, status_code=status.HTTP_201_CREATED
)
async def create_area(
    request: Request,
    body: schemas.AreaCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.AreaOut:
    return await services.create_area(request, session, current_user, body)


@areas_router.patch("/{area_id}", response_model=schemas.AreaOut)
async def update_area(
    request: Request,
    area_id: UUID,
    body: schemas.AreaUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.AreaOut:
    return await services.update_area(request, session, current_user, area_id, body)


@areas_router.post("/{area_id}/activate", response_model=schemas.AreaOut)
async def activate_area(
    request: Request,
    area_id: UUID,
    body: schemas.AreaStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.AreaOut:
    return await services.set_area_status(
        request, session, current_user, area_id, "ACTIVE", body.reason
    )


@areas_router.post("/{area_id}/deactivate", response_model=schemas.AreaOut)
async def deactivate_area(
    request: Request,
    area_id: UUID,
    body: schemas.AreaStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.AreaOut:
    return await services.set_area_status(
        request, session, current_user, area_id, "INACTIVE", body.reason
    )


@areas_router.get("/{area_id}", response_model=schemas.AreaOut)
async def get_area(
    area_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.AreaOut:
    return await services.get_area(session, area_id)


@box_types_router.get("/box-types", response_model=list[schemas.BoxTypeOut])
async def list_box_types(
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> list[schemas.BoxTypeOut]:
    return [
        schemas.BoxTypeOut(value=BoxType.EXPEDIENTES.value, label="Expedientes"),
        schemas.BoxTypeOut(
            value=BoxType.DOCUMENTOS_ADMINISTRATIVOS.value,
            label="Documentos administrativos",
        ),
    ]
```

Por brevedad, los routers de anaqueles, bandejas y posiciones siguen exactamente el mismo patrón. Deben incluir:

- `GET /shelves`, `GET /shelves/{id}`, `POST /shelves`, `PATCH /shelves/{id}`.
- `POST /shelves/{id}/activate`, `POST /shelves/{id}/deactivate`.
- `POST /shelves/{id}/capacity/preview`, `POST /shelves/{id}/capacity/apply`.
- `GET /trays`, `GET /trays/{id}`, `POST /trays`, `PATCH /trays/{id}`, activar/desactivar.
- `GET /positions`, `GET /positions/{id}`, `POST /positions`, `PATCH /positions/{id}`.
- `POST /positions/{id}/retire`, `POST /positions/{id}/activate`.
- Todos usan `catalog.read` o `catalog.manage`.
- No existe `DELETE`.

### 18.4 Contrato físico

| Método | Ruta | Permiso |
|---|---|---|
| GET | `/api/v1/areas` | `catalog.read` |
| GET | `/api/v1/areas/{id}` | `catalog.read` |
| POST | `/api/v1/areas` | `catalog.manage` |
| PATCH | `/api/v1/areas/{id}` | `catalog.manage` |
| POST | `/api/v1/areas/{id}/activate` | `catalog.manage` |
| POST | `/api/v1/areas/{id}/deactivate` | `catalog.manage` |
| GET | `/api/v1/shelves` | `catalog.read` |
| GET | `/api/v1/shelves/{id}` | `catalog.read` |
| POST | `/api/v1/shelves` | `catalog.manage` |
| PATCH | `/api/v1/shelves/{id}` | `catalog.manage` |
| POST | `/api/v1/shelves/{id}/activate` | `catalog.manage` |
| POST | `/api/v1/shelves/{id}/deactivate` | `catalog.manage` |
| POST | `/api/v1/shelves/{id}/capacity/preview` | `catalog.manage` |
| POST | `/api/v1/shelves/{id}/capacity/apply` | `catalog.manage` |
| GET | `/api/v1/trays` | `catalog.read` |
| GET | `/api/v1/trays/{id}` | `catalog.read` |
| POST | `/api/v1/trays` | `catalog.manage` |
| PATCH | `/api/v1/trays/{id}` | `catalog.manage` |
| POST | `/api/v1/trays/{id}/activate` | `catalog.manage` |
| POST | `/api/v1/trays/{id}/deactivate` | `catalog.manage` |
| GET | `/api/v1/positions` | `catalog.read` |
| GET | `/api/v1/positions/{id}` | `catalog.read` |
| POST | `/api/v1/positions` | `catalog.manage` |
| PATCH | `/api/v1/positions/{id}` | `catalog.manage` |
| POST | `/api/v1/positions/{id}/retire` | `catalog.manage` |
| POST | `/api/v1/positions/{id}/activate` | `catalog.manage` |
| GET | `/api/v1/box-types` | `catalog.read` |
| DELETE | — | No existe |

### 18.5 Filtros

| Recurso | Filtros | Orden permitido |
|---|---|---|
| Áreas | `q`, `status` | `code`, `name`, `status`, fechas |
| Anaqueles | `area_id`, `q`, `status` | `code`, `name`, `status`, `capacity_positions`, fechas |
| Bandejas | `shelf_id`, `q`, `status` | `code`, `status`, `position_count`, fechas |
| Posiciones | `tray_id`, `q`, `status` | `code`, `label`, `status`, fechas |

`q` no busca en `notes` ni en descripciones.

### 18.6 Integración de routers

Modificar `backend/src/judicial_archive/api/v1/router.py`:

```python
from judicial_archive.modules.courts.routers import router as courts_router
from judicial_archive.modules.identifier_profiles.routers import (
    router as identifier_profiles_router,
)
from judicial_archive.modules.locations.routers import (
    areas_router,
    box_types_router,
    positions_router,
    shelves_router,
    trays_router,
)
from judicial_archive.modules.numbering.routers import router as numbering_router
from judicial_archive.modules.party_roles.routers import router as party_roles_router
from judicial_archive.modules.resolution_types.routers import (
    router as resolution_types_router,
)
from judicial_archive.modules.settings.routers import router as settings_router

api_router.include_router(courts_router)
api_router.include_router(resolution_types_router)
api_router.include_router(identifier_profiles_router)
api_router.include_router(numbering_router)
api_router.include_router(party_roles_router)
api_router.include_router(areas_router)
api_router.include_router(shelves_router)
api_router.include_router(trays_router)
api_router.include_router(positions_router)
api_router.include_router(box_types_router)
api_router.include_router(settings_router)
```

Actualizar `_OPENAPI_TAGS` en `main.py` con las etiquetas nuevas si se desea una documentación ordenada. No es obligatorio para el funcionamiento, pero sí para calidad de OpenAPI.

---

## 19. Semillas y datos iniciales

### 19.1 Regla

B5 **no inventa datos**. Los datos iniciales ya existen en `db/seed.py`:

- 5 áreas: `A`, `B`, `C`, `D`, `O`.
- 39 anaqueles: `A1-A9`, `B1-B8`, `C1-C6`, `D1-D13`, `O1-O3`.
- 8 tribunales, incluidos los duplicados `589` y `107`.
- 1 rol de parte: `IMPUTADO`.
- 1 política de numeración: `BOX_GLOBAL`.
- 1 configuración: `system.timezone`.

No añadir tipos de resolución, perfiles de identificador ni capacidades inventadas.

### 19.2 Ajuste opcional del seed

El seed actual usa `Area(code=code, ...)` con códigos ya en mayúsculas. Para reforzar la coherencia, se puede cambiar `_ensure_area` a:

```python
from judicial_archive.core.text import ensure_area_code


async def _ensure_area(session: AsyncSession, code: str, name: str) -> None:
    normalized = ensure_area_code(code)
    if await _existing(session, Area, code=normalized) is not None:
        return
    session.add(Area(code=normalized, name=name, description=None, status="ACTIVE"))
```

No es obligatorio si los valores siguen siendo válidos. Si se modifica, ejecutar `test_seed_idempotency.py`.

### 19.3 Prueba de seed

Mantener las aserciones existentes y añadir:

```python
@pytest.mark.asyncio
async def test_seed_area_codes_are_unique(db_session: AsyncSession) -> None:
    await seed_database(db_session)
    duplicates = await db_session.execute(
        select(Area.code, func.count()).group_by(Area.code).having(func.count() > 1)
    )
    assert duplicates.all() == []
```

---

## 20. Pruebas

### 20.1 Estrategia

| Nivel | Qué prueba | Base de datos |
|---|---|---|
| Unitaria | Normalización, patrones, formato, planificador, validación de settings | No |
| API | Contratos, permisos, códigos HTTP, CSRF, OpenAPI | No/Sí según fixture |
| Integración | CRUD real, constraints, secuencias, auditoría, capacidad, migración | PostgreSQL real |

Las pruebas de integración usan `RUN_INTEGRATION=1`, `TEST_DATABASE_URL`, `-n 0` y las fixtures de B2/B4.

### 20.2 Pruebas unitarias

`backend/tests/unit/test_b5_text_and_validation.py`:

```python
from datetime import date

import pytest

from judicial_archive.core.errors import InvalidParameterError
from judicial_archive.core.text import (
    ensure_area_code,
    ensure_sequence_name,
    normalize_upper_code,
    validate_effective_range,
)
from judicial_archive.modules.identifier_profiles.services import (
    validate_identifier_pattern,
)


def test_normalize_court_code() -> None:
    assert normalize_upper_code("  107-01 ") == "107-01"


def test_area_code_rejects_lowercase_after_normalization() -> None:
    assert ensure_area_code(" zona-a ") == "ZONA-A"
    with pytest.raises(InvalidParameterError):
        ensure_area_code("1A")


def test_sequence_name_rejects_hyphen() -> None:
    with pytest.raises(InvalidParameterError):
        ensure_sequence_name("box-seq")


def test_effective_range_rejects_inverted_dates() -> None:
    with pytest.raises(InvalidParameterError):
        validate_effective_range(date(2026, 1, 2), date(2026, 1, 1))


def test_strict_profile_requires_three_examples() -> None:
    with pytest.raises(InvalidParameterError):
        validate_identifier_pattern(
            pattern=r"^\d{5}$",
            examples=["00001", "00002"],
            rejects=["ABCDE"],
            strict=True,
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )


def test_profile_rejects_nested_quantifier() -> None:
    with pytest.raises(InvalidParameterError):
        validate_identifier_pattern(
            pattern=r"^(a+)+$",
            examples=["aaa", "aaaa", "aaaaa"],
            rejects=[],
            strict=True,
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )


def test_profile_rejects_accepted_reject_value() -> None:
    with pytest.raises(InvalidParameterError):
        validate_identifier_pattern(
            pattern=r"^\d{5}$",
            examples=["00001", "00002", "00003"],
            rejects=["12345"],
            strict=True,
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )
```

`backend/tests/unit/test_b5_numbering_format.py`:

```python
from judicial_archive.modules.courts.models import NumberingPolicy
from judicial_archive.modules.numbering.services import format_visible_number


def _policy(**overrides: object) -> NumberingPolicy:
    values = {
        "code": "TEST",
        "scope": "GLOBAL",
        "sequence_name": "test_seq",
        "prefix": "C-",
        "suffix": None,
        "padding": 6,
        "start_value": 4402,
        "step": 1,
    }
    values.update(overrides)
    return NumberingPolicy(**values)


def test_format_visible_number_pads() -> None:
    assert format_visible_number(_policy(), 4402) == "C-004402"


def test_format_visible_number_rejects_too_long() -> None:
    import pytest
    from judicial_archive.core.errors import InvalidParameterError

    with pytest.raises(InvalidParameterError):
        format_visible_number(_policy(prefix="X" * 32, padding=12), 10**11)
```

`backend/tests/unit/test_b5_capacity_planner.py`:

Usar objetos ORM en memoria, sin sesión, para probar el planificador:

```python
from uuid import uuid4

from judicial_archive.modules.locations.capacity import build_capacity_plan
from judicial_archive.modules.locations.models import Position, Tray


def test_increase_capacity_creates_positions() -> None:
    shelf_id = uuid4()
    plan = build_capacity_plan(
        shelf_id=shelf_id,
        target_levels=2,
        positions_per_level=3,
        trays=[],
        positions_by_tray={},
        occupied_position_ids=set(),
    )
    assert plan.can_apply
    assert plan.trays_to_create == 2
    assert plan.positions_to_create == 6


def test_retire_occupied_position_conflicts() -> None:
    shelf_id = uuid4()
    tray = Tray(
        id=uuid4(), shelf_id=shelf_id, code="N01", status="ACTIVE", position_count=2
    )
    p1 = Position(
        id=uuid4(), tray_id=tray.id, code="P001", label="P1", status="AVAILABLE"
    )
    p2 = Position(
        id=uuid4(), tray_id=tray.id, code="P002", label="P2", status="AVAILABLE"
    )
    plan = build_capacity_plan(
        shelf_id=shelf_id,
        target_levels=1,
        positions_per_level=1,
        trays=[tray],
        positions_by_tray={tray.id: [p1, p2]},
        occupied_position_ids={p2.id},
    )
    assert not plan.can_apply
    assert plan.conflicts[0].code == "P002"
```

Añadir casos para bandeja inactiva, código personalizado, reducción y máximo 5000.

### 20.3 Fixture de API B5

`backend/tests/integration/test_b5_catalogs_api.py`:

```python
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from judicial_archive.core.config import Settings
from judicial_archive.main import create_app
from tests.integration.auth_helpers import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    USER_PASSWORD,
    create_user,
    csrf_headers,
    login,
    logout,
    seed_admin,
)

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def api_client(
    migrated_database: str,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> AsyncIterator[TestClient]:
    await seed_admin(session_factory)
    app = create_app(settings, configure_logs=False)
    with TestClient(app) as client:
        yield client
```

### 20.4 Pruebas de permisos

```python
def test_consulta_cannot_create_court(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    create_user(api_client, username="consulta-b5", role_codes=("CONSULTA",))
    logout(api_client)
    login(api_client, "consulta-b5", USER_PASSWORD)

    response = api_client.post(
        "/api/v1/courts",
        json={"code_raw": "999", "name": "Tribunal de prueba"},
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 403


def test_supervisor_can_manage_catalog_but_not_settings(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    create_user(api_client, username="supervisor-b5", role_codes=("SUPERVISOR",))
    logout(api_client)
    login(api_client, "supervisor-b5", USER_PASSWORD)

    created = api_client.post(
        "/api/v1/courts",
        json={"code_raw": "998", "name": "Tribunal de supervisor"},
        headers=csrf_headers(api_client),
    )
    assert created.status_code == 201

    forbidden = api_client.put(
        "/api/v1/settings/system.timezone",
        json={"value": "UTC", "value_type": "STRING", "description": "Zona horaria"},
        headers=csrf_headers(api_client),
    )
    assert forbidden.status_code == 403
```

### 20.5 Pruebas de tribunales

```python
def test_duplicate_court_codes_are_allowed(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    payload = {"code_raw": "589", "name": "Juzgado de Instruccion"}
    first = api_client.post(
        "/api/v1/courts", json=payload, headers=csrf_headers(api_client)
    )
    second = api_client.post(
        "/api/v1/courts",
        json={"code_raw": "589", "name": "Juzgado en Atencion Permanente"},
        headers=csrf_headers(api_client),
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["code_normalized"] == "589"


def test_court_has_no_delete_endpoint(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    created = api_client.post(
        "/api/v1/courts",
        json={"code_raw": "997", "name": "Tribunal sin borrado"},
        headers=csrf_headers(api_client),
    )
    court_id = created.json()["id"]
    response = api_client.delete(
        f"/api/v1/courts/{court_id}", headers=csrf_headers(api_client)
    )
    assert response.status_code == 405
```

### 20.6 Pruebas de áreas y auditoría

```python
def test_area_code_is_unique_via_api(api_client: TestClient) -> None:
    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    payload = {"code": "z", "name": "Zona Z"}
    first = api_client.post(
        "/api/v1/areas", json=payload, headers=csrf_headers(api_client)
    )
    second = api_client.post(
        "/api/v1/areas", json=payload, headers=csrf_headers(api_client)
    )
    assert first.status_code == 201
    assert first.json()["code"] == "Z"
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_court_create_writes_audit_event(
    api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from uuid import UUID

    from sqlalchemy import select
    from judicial_archive.modules.audit.models import AuditEvent

    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    created = api_client.post(
        "/api/v1/courts",
        json={"code_raw": "996", "name": "Tribunal auditado"},
        headers=csrf_headers(api_client),
    )
    assert created.status_code == 201

    async with session_factory() as session:
        event = await session.scalar(
            select(AuditEvent).where(
                AuditEvent.entity_type == "court",
                AuditEvent.entity_id == UUID(created.json()["id"]),
                AuditEvent.action == "court.created",
            )
        )
        assert event is not None
        assert event.actor_user_id is not None
        assert event.after_data is not None
        assert event.after_data["code_raw"] == "996"
```

No usar `asyncio.run` dentro de una prueba con `TestClient`: el cliente ya gestiona un portal y la sesión puede quedar ligada a otro event loop. La prueba anterior es asíncrona y consulta con la misma `session_factory` de la fixture.

### 20.7 Pruebas de perfiles

- Crear perfil estricto con 3 ejemplos válidos: `201`.
- Crear perfil estricto con 2 ejemplos: `422`.
- Crear perfil con patrón inválido: `422`.
- Crear segundo perfil activo para el mismo tribunal/tipo: `409`.
- Reemplazar: el anterior queda `is_active=false`, `effective_to = nuevo.effective_from - 1 día`; el nuevo queda activo.
- Reemplazar con `effective_from` anterior o igual: `422`/`409`.
- `PATCH` con `pattern`: no se acepta (campo no expuesto).
- Desactivar y reactivar: no cambia el perfil histórico.

### 20.8 Pruebas de numeración

```python
@pytest.mark.asyncio
async def test_numbering_policy_creates_sequence(
    api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from uuid import uuid4
    from sqlalchemy import text

    login(api_client, ADMIN_USERNAME, ADMIN_PASSWORD)
    name = f"test_box_seq_{uuid4().hex[:8]}"
    response = api_client.post(
        "/api/v1/numbering-policies",
        json={
            "code": f"TEST_{uuid4().hex[:8].upper()}",
            "scope": "GLOBAL",
            "sequence_name": name,
            "padding": 6,
            "start_value": 1,
            "step": 1,
            "reset_policy": "NEVER",
        },
        headers=csrf_headers(api_client),
    )
    assert response.status_code == 201, response.text

    try:
        async with session_factory() as session:
            value = await session.scalar(
                text("SELECT to_regclass(:name)"), {"name": f"public.{name}"}
            )
            assert value is not None
    finally:
        async with session_factory() as session:
            await session.execute(text(f'DROP SEQUENCE IF EXISTS "{name}"'))
            await session.commit()
```

Añadir:

- Desactivar y verificar que la secuencia sigue existiendo.
- Intentar crear otra política con la misma secuencia: `409`.
- `reset_policy="YEARLY"`: `422`.
- `preview` no consume: comparar `last_value` antes/después.
- Limpiar la secuencia de prueba en un `finally` con `DROP SEQUENCE IF EXISTS`; solo en pruebas.

### 20.9 Pruebas de capacidad

- Crear anaquel con `2×2`: 2 bandejas y 4 posiciones.
- Aplicar `2×3`: 2 posiciones nuevas, versión incrementada.
- Aplicar `2×2` con una posición ocupada en el excedente: `409`.
- Aplicar `2×2` con una posición bloqueada en el excedente: `409`.
- Aplicar `5001`: `422`.
- Verificar que no se eliminan filas: contar posiciones antes/después; las retiradas siguen existiendo.
- Verificar que `capacity_positions` coincide con `levels * positions_per_level`.

### 20.10 Pruebas de settings

- `GET /settings/system.timezone` devuelve el valor del seed.
- `PUT` con `system.timezone=UTC` funciona para admin.
- `PUT` con `system.timezone=No/Existe` devuelve `422`.
- `PUT` con clave `db.password` devuelve `422`.
- `PUT` con tipo cambiado devuelve `409`.
- `updated_by` coincide con el actor.

### 20.11 Comandos

```powershell
Set-Location C:\Users\Tony\Documents\sga\backend

# Unitarias puras
uv run pytest tests/unit -q

# Integracion (PostgreSQL real, sin xdist)
$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://USER:PASS@localhost:5432/sga_test"
uv run pytest tests/integration -n 0 -q

# Suite completa
uv run pytest -n 0 -q

# Calidad
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
```

No declarar B5 terminada si las pruebas de integración no se ejecutaron. Si no hay PostgreSQL disponible, indicar la limitación y no inventar resultados.

---

## 21. Documentación que debe actualizarse

Actualizar solo lo que realmente cambie. No reescribir documentos completos ni borrar decisiones de fases anteriores.

### 21.1 `docs/api.md`

Añadir:

- Prefijo `/api/v1`.
- Tabla de endpoints por recurso: método, ruta, permiso, parámetros y respuestas.
- Paginación común: `page`, `page_size`, `sort_by`, `order`.
- Filtros: `q`, `status`, `court_id`, `resolution_type_id`, `area_id`, `shelf_id`, `tray_id`.
- Errores: `400`, `403`, `404`, `409`, `422`.
- Regla: no existen endpoints `DELETE` para catálogos.
- `GET /box-types` es solo lectura.
- `POST /identifier-profiles/{id}/replace` y `POST /numbering-policies/{id}/deactivate`.
- `POST /shelves/{id}/capacity/apply` con `expected_version`.
- `GET /settings` y `GET|PUT /settings/{key}`.
- CSRF obligatorio en métodos mutables.

### 21.2 `docs/modelo-de-datos.md`

Documentar:

- `uq_areas_code` y el motivo.
- Que `Court.code_raw` no es único y que `code_normalized` es solo búsqueda.
- `Shelf.capacity_positions` es calculada.
- `Tray.position_count` se deriva de posiciones activas.
- `Position` no se borra; se retira.
- `IdentifierFormatProfile` es versionado.
- `NumberingPolicy.sequence_name` es inmutable tras el alta.
- `AuditEvent.metadata_json` se serializa como `metadata` en la API.

### 21.3 `docs/reglas-de-negocio.md`

Añadir o enlazar:

- BR-CAT-01: desactivar no borra.
- BR-CAT-02: códigos de tribunal pueden repetirse.
- BR-CAT-03: área única por código.
- BR-CAT-04: no mezclar catálogos con datos operativos.
- BR-CAT-05: perfiles versionados y estrictos.
- BR-CAT-06: numeración transaccional y sin reutilización.
- BR-LOC-01: capacidad teórica, ocupación y disponibilidad separadas.
- BR-LOC-02: no borrar posiciones; retirar.
- BR-LOC-03: no reducir capacidad sobre posiciones ocupadas/bloqueadas.
- BR-LOC-04: no asignar dos cajas activas a una posición; B7 lo garantiza con constraint/transacción.

### 21.4 `docs/roles-y-permisos.md`

Documentar la matriz B5:

| Acción | Permiso |
|---|---|
| Listar/ver catálogos | `catalog.read` |
| Crear/editar/desactivar tribunales, resoluciones, perfiles, roles, áreas, anaqueles, bandejas, posiciones | `catalog.manage` |
| Consultar configuración | `settings.read` |
| Crear/editar políticas de numeración y settings | `settings.manage` |
| Aplicar capacidad | `catalog.manage` |

No crear permisos nuevos en B5.

### 21.5 `docs/pruebas.md`

Añadir:

- Comandos unitarios/integración.
- Requisito de PostgreSQL real.
- Casos obligatorios de B5.
- Limitación de `-n 0` por el estado de sesión y las secuencias.
- Que las secuencias de prueba se limpian explícitamente.

### 21.6 `docs/inventario-fisico.md`

Documentar:

- Área, anaquel, bandeja y posición.
- Capacidad configurable por anaquel.
- `levels × positions_per_level = capacity_positions`.
- Posiciones retiradas/bloqueadas no disponibles.
- La asignación de cajas es B7; B5 solo prepara la estructura.

### 21.7 `docs/pendientes-de-validacion.md`

Registrar:

- Semántica exacta de tipos de resolución y prefijos.
- Patrones de identificador por tribunal/periodo.
- Si se requiere `box_types` administrable.
- Política de reinicio de numeración.
- Reglas de capacidad reales por anaquel.
- Confirmación de la unicidad de `areas.code`.
- Si `Court.status` debe admitir `UNKNOWN` o solo `ACTIVE/INACTIVE`.

### 21.8 Guía maestra

Solo al cerrar B5, actualizar `docs/phases/GUIA_DESARROLLO_FASES_SGA.md`:

- Estado de B5 a completada.
- Fecha, commit y comandos ejecutados.
- Desviaciones respecto a esta guía.
- Riesgos residuales.

No sobrescribir cambios existentes en ese archivo.

---

## 22. Orden de implementación

1. `core/text.py` y pruebas unitarias.
2. `audit/services.py` y pruebas unitarias.
3. Migración `uq_areas_code` y actualización de `locations/models.py`.
4. Módulo `courts`.
5. `resolution_types`.
6. `identifier_profiles`.
7. `numbering`.
8. `party_roles`.
9. `settings`.
10. `locations`: schemas, repositorio, planificador, servicios.
11. Routers de `locations` y `box-types`.
12. Integración en `api/v1/router.py`.
13. Pruebas de API e integración.
14. Documentación.
15. Validación final.

No avanzar al siguiente módulo si el anterior no pasa sus pruebas unitarias y de esquema.

---

## 23. Comandos de verificación

```powershell
Set-Location C:\Users\Tony\Documents\sga\backend

# 1. Dependencias y estado
uv sync
uv run alembic current

# 2. Migracion B5
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head

# 3. Metadatos y esquema
uv run pytest tests/unit/test_schema_metadata.py -q
$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://USER:PASS@localhost:5432/sga_test"
uv run pytest tests/integration/test_schema_constraints.py -n 0 -q

# 4. Pruebas B5
uv run pytest tests/unit -q
uv run pytest tests/integration/test_b5_catalogs_api.py -n 0 -q
uv run pytest tests/integration/test_b5_numbering_sequence.py -n 0 -q
uv run pytest tests/integration/test_b5_capacity.py -n 0 -q
uv run pytest tests/integration/test_b5_audit.py -n 0 -q

# 5. Suite completa
uv run pytest -n 0 -q

# 6. Calidad
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src

# 7. Revision del diff
Set-Location C:\Users\Tony\Documents\sga
git diff --check
git status --short
```

No ejecutar `alembic downgrade` sobre una base con datos reales. El `downgrade -1` de la migración de unicidad solo elimina el constraint; no borra datos, pero debe probarse en la base de pruebas.

---

## 24. Checklist de aceptación B5

### Esquema

- [ ] `Area.code` tiene `uq_areas_code`.
- [ ] La migración falla de forma explícita si existen duplicados.
- [ ] `downgrade` elimina solo el constraint.
- [ ] `test_schema_metadata.py` incluye el constraint.
- [ ] `test_schema_constraints.py` verifica el rechazo de duplicados.
- [ ] No se crearon tablas nuevas.
- [ ] No se modificó `BoxType`.

### Tribunales

- [ ] `GET /courts` pagina, filtra y ordena.
- [ ] `POST /courts` normaliza `code_raw` a `code_normalized`.
- [ ] Se permiten códigos repetidos.
- [ ] `PATCH` no permite cambiar el código.
- [ ] `POST /{id}/deactivate` y `/{id}/reactivate` funcionan.
- [ ] No existe `DELETE`.
- [ ] Cada mutación escribe auditoría.

### Tipos de resolución

- [ ] CRUD lógico completo.
- [ ] Código único.
- [ ] Prefijo validado.
- [ ] No se borran tipos con uso futuro; se desactivan.
- [ ] No se inventan datos iniciales.

### Perfiles de identificador

- [ ] Patrón validado y sin cuantificadores anidados.
- [ ] `strict=true` exige patrón, 3 ejemplos y rechazos válidos.
- [ ] Un solo perfil activo por tribunal/tipo.
- [ ] `replace` cierra el anterior y crea el nuevo.
- [ ] `PATCH` no permite cambiar `pattern`.
- [ ] Fechas coherentes.

### Numeración

- [ ] `POST` crea la secuencia en la misma transacción.
- [ ] `sequence_name` es único y válido.
- [ ] `step`, `start_value`, `padding` y prefijo/sufijo validados.
- [ ] `deactivate` no borra la secuencia.
- [ ] `preview` no consume.
- [ ] Identidad inmutable tras el alta.
- [ ] `reset_policy` no admite valores no implementados.

### Roles de parte

- [ ] CRUD lógico completo.
- [ ] Código único.
- [ ] No se borra un rol usado; se desactiva.
- [ ] No se crean roles iniciales nuevos.

### Configuración

- [ ] `GET /settings` y `GET /settings/{key}` funcionan.
- [ ] `PUT` valida según `value_type`.
- [ ] No se permiten claves sensibles.
- [ ] No se cambia el tipo de una clave existente.
- [ ] `updated_by` se registra.
- [ ] `settings.manage` es obligatorio para escribir.

### Catálogos físicos

- [ ] Área única y normalizada.
- [ ] Anaquel con capacidad válida.
- [ ] `capacity_positions` calculada correctamente.
- [ ] Bandejas y posiciones generadas según plan.
- [ ] Códigos de bandeja/posición validados y únicos.
- [ ] No se borran bandejas/posiciones.
- [ ] `apply` exige `expected_version`.
- [ ] No se reduce capacidad con posiciones ocupadas/bloqueadas.
- [ ] Posiciones retiradas pueden reactivarse.
- [ ] Máximo 5000 posiciones.
- [ ] `preview` no modifica datos ni bloquea filas.

### Integración

- [ ] Routers incluidos en `api/v1/router.py`.
- [ ] OpenAPI muestra etiquetas y esquemas correctos.
- [ ] Permisos aplicados en lectura y escritura.
- [ ] CSRF aplicado en métodos mutables.
- [ ] Errores usan el formato uniforme de B3.
- [ ] No hay `DELETE` en catálogos.
- [ ] `GET /box-types` responde solo lectura.

### Calidad

- [ ] `ruff check` pasa.
- [ ] `ruff format --check` pasa.
- [ ] `mypy` pasa o las excepciones están documentadas.
- [ ] Pruebas unitarias pasan.
- [ ] Pruebas de integración pasan o se declara la limitación.
- [ ] No hay secretos ni datos reales en el diff.
- [ ] Documentación actualizada.
- [ ] `git diff --check` sin errores.

---

## 25. Riesgos y decisiones abiertas

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Duplicados de `Area.code` en datos existentes | La migración falla | Precheck y detenerse; no borrar datos |
| Nombres de secuencia colisionan | Error de transacción | Validar `to_regclass` y unique |
| Secuencias huérfanas | Residuos | No borrar en producción; documentar |
| ReDoS en patrones de identificador | Bloqueo de CPU | Rechazar cuantificadores anidados y limitar longitud |
| Concurrencia al aplicar capacidad | Plan obsoleto | `expected_version` y bloqueo de filas |
| Posición ocupada durante reducción | Pérdida de integridad | Conflicto y no aplicar |
| `metadata` reservado en SQLAlchemy | Error de mapeo | Usar `metadata_json` |
| Permisos insuficientes | `403` en operaciones legítimas | Probar cada rol |
| `Court.code_raw` duplicado | Confusión operativa | No imponer unicidad; conservar y documentar |
| `BoxType` cerrado | Solicitud de CRUD | No implementar sin aprobación |
| `settings` con claves arbitrarias | Riesgo de secretos | Lista blanca de claves y tipos |
| `preview` con lock | Bloqueos innecesarios | Consulta de solo lectura |
| Pruebas con `asyncio.run` | Event loop incorrecto | Usar pruebas async o helper sincrónico |
| `test_schema_metadata` desactualizado | Falso verde | Actualizar junto con el modelo |

Decisiones que requieren validación humana:

1. ¿`Court.status` debe incluir `UNKNOWN`?
2. ¿Los tipos de resolución requieren prefijo obligatorio?
3. ¿La numeración se reinicia por año o es global?
4. ¿Se requiere CRUD de tipos de caja?
5. ¿La capacidad real de cada anaquel coincide con `7×9`, `7×8`, `7×7` u otra?
6. ¿`Area.code` debe ser único global o por sede?
7. ¿Los perfiles de identificador aplican a NUC, sentencia o ambos?

---

## 26. Handoff a fases posteriores

### B6 — Cajas y registros documentales

- Usar `numbering.services.preview_next_value` y `allocate_next_value`; no usar `MAX(number)+1`.
- Usar `Court` y `ResolutionType` activos.
- Usar `IdentifierFormatProfile` activo para validar, sin rechazar datos históricos sin revisión.
- `BoxType` sigue siendo enum.
- La asignación de posición es B7, no B6.

### B7 — Ubicaciones y movimientos

- Usar `Position` con estados `AVAILABLE/BLOCKED/RETIRED`.
- Garantizar una sola caja activa por posición con constraint/transacción.
- No borrar posiciones; retirar.
- Respetar `capacity_positions` y no excederlo.
- Registrar movimientos y auditoría en la misma transacción.

### B8 — Búsqueda global

- Indexar `Court.code_normalized`, `Area.code`, `Shelf.code`, `Tray.code`, `Position.code`.
- Buscar por área/anaquel/bandeja/posición.
- No usar `code_normalized` como clave primaria.
- Respetar permisos de catálogo.

### B13 — Auditoría completa

- Reutilizar `audit/services.record_audit_event`.
- No duplicar el helper.
- Añadir consultas y filtros de auditoría, no cambiar el contrato de escritura sin migración.

### B15 — Endurecimiento

- Revisar ReDoS, límites de página, secuencias y concurrencia.
- Probar migración desde el esquema B4 y desde base vacía.
- Revisar que no haya endpoints `DELETE` de catálogos.
- Verificar OpenAPI y permisos.

---

## 27. Registro de validación

Completar al implementar. No inventar resultados.

| Fecha | Commit | Comando | Resultado | Observaciones |
|---|---|---|---|---|
| | | `uv run alembic upgrade head` | | |
| | | `uv run pytest tests/unit -q` | | |
| | | `uv run pytest tests/integration -n 0 -q` | | |
| | | `uv run ruff check src tests` | | |
| | | `uv run ruff format --check src tests` | | |
| | | `uv run mypy src` | | |
| | | `git diff --check` | | |

Criterio de cierre: todas las casillas obligatorias del checklist están marcadas, las pruebas de integración se ejecutaron en PostgreSQL real y las limitaciones restantes están documentadas en `docs/pendientes-de-validacion.md`.
