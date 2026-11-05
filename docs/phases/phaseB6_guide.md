# Fase B6 - Inventario fisico y ubicaciones

**Version:** 1.0
**Fecha:** 2026-11-02
**Estado:** Guia de implementacion
**Depende de:** B5 - Catalogos judiciales y configuracion fisica
**Habilita:** B7, B8, B11, B12 y B14
**Alcance:** Backend, PostgreSQL, Alembic, pruebas y documentacion
**Documento unico de la fase:** `docs/phases/phaseB6_guide.md`

---

## 0. Como usar esta guia

1. Leer completos `docs/AGENTS.md` y `docs/phases/GUIA_DESARROLLO_FASES_SGA.md` antes de escribir codigo.
2. Leer `docs/phases/phaseB5_guide.md` para conservar convenciones, patrones de auditoria, paginacion, permisos y manejo de errores.
3. Ejecutar los pasos en el orden indicado. No crear rutas antes de la migracion y de los modelos.
4. No implementar CRUD de cajas, expedientes, documentos administrativos, prestamos, QR ni conciliacion de inventario en esta fase. B6 opera sobre las cajas existentes y deja los puntos de extension documentados.
5. Toda mutacion de ubicacion debe actualizar la caja, crear historial y registrar auditoria en la misma transaccion.
6. Toda correccion debe incluir prueba de regresion. No se aceptan `xfail` nuevos ni `skip` para funcionalidad B6.
7. Los comandos se ejecutan desde `backend/` salvo que se indique otra ruta.
8. Mantener documentacion en espanol y sin datos reales, secretos ni credenciales.

---

## 1. Resumen ejecutivo

B5 construyo el catalogo fisico: areas, anaqueles, bandejas, posiciones, capacidad y tipos de caja. B6 convierte ese catalogo en un sistema operativo de ubicacion fisica:

- completa los endpoints de anaqueles, bandejas, posiciones, capacidad y bloqueos;
- calcula ocupacion real y capacidad visible;
- asigna, confirma, desasigna y traslada cajas;
- conserva historial completo e inmutable de ubicaciones;
- diferencia caja no registrada, caja sin ubicacion confirmada, caja pendiente y posicion vacia;
- protege la ocupacion concurrente de una posicion;
- expone plano jerarquico, escaneo y reportes de ocupacion;
- deja preparada la integracion con prestamos, conciliacion y reportes avanzados.

B6 **no** crea cajas. La tabla `boxes`, sus reglas de numeracion y el CRUD documental pertenecen a B7. Para pruebas y para operar datos existentes, B6 usa cajas creadas por fixtures ORM o por importaciones futuras. La lectura de cajas y la escritura de su ubicacion si forman parte de B6.

---

## 2. Alcance y no alcance

### 2.1 Dentro de alcance

| Area | Incluido |
|---|---|
| Catalogos fisicos | Listar, crear, consultar, editar, activar y desactivar anaqueles, bandejas y posiciones. |
| Capacidad | Previsualizar y aplicar capacidad por anaquel; comparar capacidad configurada con posiciones visibles. |
| Bloqueos | Bloquear y desbloquear rangos de posiciones con motivo, usuario y vigencia. |
| Ocupacion | Resumen por area, anaquel, bandeja o global; listado paginado de posiciones ocupadas/libres/bloqueadas. |
| Ubicacion de cajas | Asignar, confirmar, desasignar y trasladar cajas existentes. |
| Movimientos | Listar, consultar, completar y cancelar movimientos de ubicacion. |
| Historial | Historial append-only por caja, con origen, destino, custodia, precision, motivo, actor y movimiento. |
| Escaneo | Resolver numero visible de caja o UUID de posicion y devolver estado operativo. |
| Reportes | Reporte JSON y CSV de ocupacion, con permisos separados de lectura y exportacion. |
| Concurrencia | Bloqueo de filas, version optimista y restricciones unicas como ultima defensa. |
| Auditoria | Eventos de auditoria para toda mutacion, en la misma transaccion. |
| Pruebas | Unitarias, API, integracion, concurrencia, migraciones e inmutabilidad. |
| Documentacion | API, modelo de datos, reglas, inventario fisico, pruebas, seguridad y permisos. |

### 2.2 Fuera de alcance

| Area | Fase responsable |
|---|---|
| CRUD de cajas, numeracion visible y contenido documental | B7 |
| Expedientes, imputados y documentos administrativos | B7 |
| Busqueda global combinada | B8 |
| Prestamos, devoluciones y QR imprimible | B11 |
| Sesiones de conciliacion y resolucion de diferencias | B12 |
| Auditoria avanzada con consultas historicas | B13 |
| Excel, PDF y exportaciones avanzadas | B14 |
| Frontend, plano 2D/3D y etiquetas visuales | Fases F |

B6 puede leer y actualizar `Box.current_position_id`, `Box.custody_status` y crear `BoxMovement`/`BoxLocationHistory`; no puede crear, borrar ni cambiar atributos documentales de una caja.

---

## 3. Conflicto de numeracion B6/B7 y decision

Existe una inconsistencia documental real:

- `docs/AGENTS.md`, seccion 14, indica **B6 = Cajas y registros documentales** y **B7 = Ubicaciones y movimientos**.
- `docs/phases/GUIA_DESARROLLO_FASES_SGA.md` y la solicitud actual indican **B6 = Inventario fisico y ubicaciones** y **B7 = Cajas, expedientes e inventario administrativo**.

**Decision para esta guia:** se implementa B6 como inventario fisico y ubicaciones, y B7 como cajas y registros documentales. Esta decision no cambia el modelo de datos ni el orden tecnico de B5; solo cambia el nombre de la fase.

Consecuencias:

1. B6 debe funcionar con cajas existentes. No se duplican reglas de creacion de cajas.
2. B7 agregara el CRUD de cajas y podra reutilizar los servicios de ubicacion de B6.
3. Registrar una ADR en `docs/decisiones/ADR-0002-numeracion-fases-b6-b7.md` con contexto, decision y consecuencias.
4. Corregir la referencia de handoff en `docs/phases/phaseB5_guide.md` cuando se actualice la documentacion de cierre, sin reescribir la historia de la fase.
5. No cambiar codigo existente solo por el numero de fase.

---

## 4. Estado de partida y brechas B5

### 4.1 Lo que ya existe

| Archivo | Estado |
|---|---|
| `modules/locations/models.py` | `Area`, `Shelf`, `Tray`, `Position`, `PositionBlock`; capacidad y estados. |
| `modules/locations/services.py` | CRUD de areas, anaqueles, bandejas, posiciones y capacidad. |
| `modules/locations/capacity.py` | Planificador y aplicador de capacidad. |
| `modules/locations/repositories.py` | Consultas, locks de estructura y ocupacion basica. |
| `modules/locations/routers.py` | Solo rutas de areas y `box-types`; routers de shelves/trays/positions declarados pero sin endpoints. |
| `modules/boxes/models.py` | `Box`, `BoxNumberHistory`, `BoxMovement`; custodia, precision calculada e indices unicos parciales. |
| `modules/inventory/models.py` | Modelos de sesiones y hallazgos, sin servicios B6. |
| `modules/loans/models.py` | Modelo de prestamos, integracion futura. |
| `alembic/versions/20261026_0001_initial_schema.py` | Tablas, constraints, triggers e indices iniciales. |
| `tests/integration/test_capacity.py` | Pruebas de capacidad a nivel servicio/ORM. |
| `tests/api/test_catalogs_api.py` | Dos `xfail` por rutas faltantes de shelves/trays/positions/capacity. |

### 4.2 Brechas que B6 debe cerrar

1. Endpoints de `shelves`, `trays`, `positions` y `capacity` no expuestos.
2. `ShelfCreate` rechaza toda capacidad valida cuando se envian `levels` y `positions_per_level`; el validador debe comparar el total, no lanzar siempre.
3. No existe servicio de bloqueo/desbloqueo de posiciones.
4. No existe asignacion, confirmacion, desasignacion ni traslado de cajas.
5. No existe historial de ubicaciones; `BoxMovement` conserva el traslado, pero no el cambio de custodia/precision.
6. No existe proteccion contra dos movimientos abiertos para la misma caja.
7. No existe distincion operativa entre caja no registrada, caja sin ubicacion, caja pendiente y posicion vacia.
8. No existe resumen de ocupacion ni comparacion capacidad configurada/visible.
9. No existe reporte de ocupacion ni exportacion CSV.
10. No existe prueba de concurrencia de asignacion a la misma posicion.
11. No existe documentacion de estados de ubicacion.
12. Los `xfail` de rutas B5 deben desaparecer al completar los endpoints.

### 4.3 Baseline esperado antes de B6

Con PostgreSQL y Redis activos:

```powershell
Set-Location backend
$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:Santi.15@localhost:5432/sga_test"
$env:TEST_REDIS_URL = "redis://localhost:6379/15"
uv run pytest -q -n 0 --no-cov --tb=short
```

Resultado de referencia al cierre de B5: `269 passed, 2 xfailed`. Los dos `xfail` corresponden exactamente a rutas faltantes. Al terminar B6 no debe quedar ninguno de esos `xfail`.

---

## 5. Requisitos y criterios de aceptacion

| Criterio de aceptacion | Implementacion | Prueba obligatoria |
|---|---|---|
| No se puede ocupar dos veces una misma posicion | Indice unico parcial `uq_boxes_current_position_occupied`, lock de posicion y validacion de servicio | Dos asignaciones concurrentes: una 200 y una 409 `position_occupied` |
| Una caja no puede estar en dos posiciones activas | `Box.current_position_id` unico cuando la custodia es activa; lock de caja | Asignar caja ya ubicada devuelve 409 `box_already_located` |
| Los movimientos mantienen historial completo | `BoxMovement` + `BoxLocationHistory` append-only + auditoria | Asignar, transferir, completar y cancelar; verificar secuencia de historial y auditoria |
| Se diferencia caja no registrada, caja sin ubicacion confirmada y posicion vacia | `GET /locations/scan` con `ScanResponse` discriminado | Escanear numero inexistente, caja sin posicion, caja pendiente, posicion vacia y posicion ocupada |
| La capacidad visible coincide con la configuracion fisica | `OccupancySummaryOut.visible_capacity`, `configured_capacity` y `capacity_mismatches` | Crear anaquel con capacidad y verificar igualdad; luego retirar una posicion y verificar discrepancia |
| Los bloqueos impiden asignar | `Position.status = BLOCKED` y validacion de servicio | Intentar asignar a posicion bloqueada devuelve 409 `position_blocked` |
| Los traslados conservan origen, destino, fecha, usuario y motivo | `BoxMovement` y `BoxLocationHistory` | Verificar snapshot de movimiento e historial |
| No se pierde la ubicacion de origen en salida temporal | Movimiento `IN_TRANSIT` conserva `from_position_id`; historial conserva custodia/precision de origen | Iniciar transito, cancelar y verificar restauracion exacta |
| Las operaciones son atomicas | Un solo `commit` por mutacion; historial y auditoria en la misma transaccion | Forzar fallo de auditoria o constraint y verificar que no quede caja movida |
| La concurrencia no depende de Redis | Locks PostgreSQL, version optimista y constraints | Prueba de concurrencia con dos sesiones reales |
| Los permisos se respetan | `require_permissions` por ruta | 403 para roles sin permiso; 200 para autorizados |
| No hay `DELETE` de catalogos | Solo activate/deactivate/retire/cancel | OpenAPI no expone `delete` en rutas B6 |

Ademas, B6 debe cumplir:

- toda mutacion requiere CSRF cuando esta habilitado;
- toda mutacion registra auditoria con actor, fecha, entidad, antes/despues y metadata;
- ninguna ruta devuelve modelos ORM sin esquema;
- los errores usan el sobre `{"error": {...}}`;
- las fechas son timezone-aware en UTC;
- no se exponen datos personales ni documentos en respuestas de ubicacion.

---

## 6. Modelo de dominio

### 6.1 Estados de custodia y precision

`CustodyStatus` describe la situacion fisica de la caja:

| Valor | Significado | `current_position_id` | Precision calculada |
|---|---|---|---|
| `IN_PLACE` | Caja confirmada en su posicion | Obligatorio | `CONFIRMED` |
| `PENDING_VERIFICATION` | Caja colocada, pendiente de confirmar | Obligatorio | `PENDING` |
| `IN_RECONCILIATION` | Caja en proceso de conciliacion | Obligatorio | `PENDING` |
| `ON_LOAN` | Caja prestada, fuera de su posicion | Debe ser `NULL` | `UNKNOWN` |
| `IN_TRANSIT` | Caja en traslado | Debe ser `NULL` | `UNKNOWN` |
| `MISSING` | Caja no localizada | Debe ser `NULL` | `UNKNOWN` |
| `UNKNOWN` | Sin ubicacion conocida | Debe ser `NULL` | `UNKNOWN` |

`location_precision` es una columna calculada por PostgreSQL:

```sql
CASE
  WHEN current_position_id IS NULL THEN 'UNKNOWN'
  WHEN custody_status = 'IN_PLACE' THEN 'CONFIRMED'
  ELSE 'PENDING'
END
```

No asignar `location_precision` desde Python. Es de solo lectura y la base la recalcula. Para historial y respuestas, calcularla con la misma regla en Python antes del `flush`.

### 6.2 Estado operativo derivado

`LocationState` no se almacena. Se deriva de custodia y posicion:

| `custody_status` | `current_position_id` | `LocationState` |
|---|---|---|
| `IN_PLACE` | No nulo | `CONFIRMED` |
| `PENDING_VERIFICATION` | No nulo | `PENDING_CONFIRMATION` |
| `IN_RECONCILIATION` | No nulo | `IN_RECONCILIATION` |
| `ON_LOAN` | Nulo | `ON_LOAN` |
| `IN_TRANSIT` | Nulo | `IN_TRANSIT` |
| `MISSING` | Nulo | `MISSING` |
| `UNKNOWN` | Nulo | `UNASSIGNED` |

Para escaneo, `ScanKind` distingue ademas `UNREGISTERED_BOX`. Una posicion puede estar `EMPTY`, `OCCUPIED`, `BLOCKED` o `RETIRED`.

### 6.3 Transiciones permitidas en B6

| Operacion | Estado inicial | Estado final | Movimiento | Historial |
|---|---|---|---|---|
| Asignar confirmada | `UNKNOWN`/`MISSING`, sin posicion | `IN_PLACE`, posicion destino | `ASSIGN` completado | Si |
| Asignar pendiente | `UNKNOWN`/`MISSING`, sin posicion | `PENDING_VERIFICATION`, posicion destino | `ASSIGN` completado | Si |
| Confirmar | `PENDING_VERIFICATION`, con posicion | `IN_PLACE`, misma posicion | No | Si |
| Desasignar | `IN_PLACE`/`PENDING_VERIFICATION`, con posicion | `UNKNOWN`, sin posicion | `UNASSIGN` completado | Si |
| Traslado inmediato confirmado | `IN_PLACE`/`PENDING_VERIFICATION`, con posicion | `IN_PLACE`, posicion destino | `TRANSFER` completado | Si |
| Traslado inmediato pendiente | `IN_PLACE`/`PENDING_VERIFICATION`, con posicion | `PENDING_VERIFICATION`, posicion destino | `TRANSFER` completado | Si |
| Iniciar traslado | `IN_PLACE`/`PENDING_VERIFICATION`, con posicion | `IN_TRANSIT`, sin posicion | `TRANSFER` en transito | Si |
| Completar traslado | `IN_TRANSIT`, sin posicion | `IN_PLACE`/`PENDING_VERIFICATION`, destino | Mismo `TRANSFER` completado | Si |
| Cancelar traslado | `IN_TRANSIT`, sin posicion | Custodia y posicion de origen | Mismo `TRANSFER` cancelado | Si |
| Bloquear rango | Posiciones `AVAILABLE` | Posiciones `BLOCKED` | No | Auditoria |
| Desbloquear rango | Posiciones `BLOCKED` | Posiciones `AVAILABLE` | No | Auditoria |

Transiciones no permitidas en B6:

- asignar una caja `ON_LOAN`, `IN_TRANSIT`, `IN_RECONCILIATION`, `VOIDED` o `DESTROYED`;
- transferir desde `UNKNOWN` o `MISSING`; primero se asigna o se resuelve por conciliacion;
- confirmar una caja sin posicion o que no este `PENDING_VERIFICATION`;
- ocupar una posicion `BLOCKED` o `RETIRED`;
- asignar a un anaquel, bandeja o area inactiva;
- cancelar un movimiento `COMPLETED` o ya `CANCELLED`;
- completar un movimiento que no este `IN_TRANSIT`;
- crear dos movimientos abiertos para la misma caja.

### 6.4 Invariantes

1. `current_position_id` solo puede estar ocupado por una caja cuando la custodia es `IN_PLACE`, `PENDING_VERIFICATION` o `IN_RECONCILIATION`.
2. `ON_LOAN`, `IN_TRANSIT`, `MISSING` y `UNKNOWN` exigen `current_position_id IS NULL`.
3. Una posicion solo puede tener una caja con custodia activa. Lo garantiza `uq_boxes_current_position_occupied`.
4. Una caja solo puede tener un movimiento `PLANNED` o `IN_TRANSIT` a la vez. Lo garantiza `uq_box_movements_open_box`.
5. Toda mutacion de posicion o custodia crea una fila en `box_location_history`.
6. `box_location_history` es append-only: no se actualiza ni se borra.
7. Toda mutacion crea un evento de auditoria en la misma transaccion.
8. El historial conserva el estado anterior y posterior de custodia, precision y posicion.
9. El traslado en transito conserva el origen en el movimiento y en el historial; la caja no queda falsamente ubicada.
10. La capacidad visible es el numero de posiciones no retiradas; la configurada es `levels * positions_per_level`.
11. Una posicion bloqueada no cuenta como disponible y no puede recibir cajas.
12. No se elimina fisicamente ninguna entidad con historial, movimientos o auditoria.

### 6.5 Formulas de ocupacion

Para un anaquel:

```text
configured_capacity = shelf.capacity_positions            # puede ser NULL
visible_capacity    = count(positions where status != RETIRED)
retired_positions   = count(positions where status == RETIRED)
blocked_positions   = count(positions where status == BLOCKED)
occupied_positions  = count(positions with active box)
available_positions = max(0, visible_capacity - occupied_positions - blocked_positions)
occupancy_rate      = round(occupied_positions / visible_capacity, 4) si visible_capacity > 0, si no 0.0
capacity_matches    = configured_capacity IS NULL OR configured_capacity == visible_capacity
```

Para un area o el global, sumar los valores de sus anaqueles y recalcular la tasa con los totales. `configured_capacity` agregado es `NULL` solo si ningun anaquel tiene capacidad configurada.

Cajas sin ubicacion:

```text
unlocated_boxes             = boxes con current_position_id IS NULL y custody IN (UNKNOWN, MISSING)
pending_confirmation_boxes  = boxes con custody = PENDING_VERIFICATION
in_transit_boxes            = boxes con custody = IN_TRANSIT
```

### 6.6 Movimientos

Tipos usados por B6:

- `ASSIGN`: asignacion inicial de una caja a una posicion.
- `UNASSIGN`: retiro de ubicacion sin destino.
- `TRANSFER`: traslado entre posiciones, inmediato o en transito.

Tipos reservados para fases posteriores:

- `RETURN`: devolucion desde prestamo o salida temporal (B11).
- `LOAN_PICKUP` y `LOAN_RETURN`: ciclo de prestamo (B11).
- `RECONCILIATION`: ajuste autorizado por conciliacion (B12).

Estados:

- `PLANNED`: reservado para aprobaciones futuras. B6 no lo expone como flujo publico.
- `IN_TRANSIT`: traslado iniciado; la caja no esta en origen ni en destino.
- `COMPLETED`: operacion aplicada; `completed_at` obligatorio.
- `CANCELLED`: operacion anulada; `cancelled_at` obligatorio.

Regla de oro: la actualizacion de `Box` y la creacion de `BoxMovement`/`BoxLocationHistory` ocurren en la misma transaccion. Si falla cualquiera, no se confirma ninguna.

### 6.7 Concurrencia y bloqueo

Orden de bloqueo obligatorio para evitar deadlocks:

1. bloquear la caja con `SELECT ... FOR UPDATE`;
2. bloquear las posiciones implicadas ordenadas por `id` ascendente;
3. bloquear el anaquel solo si la operacion modifica capacidad o bloqueos;
4. validar version optimista;
5. mutar, crear historial y auditoria;
6. un unico `commit`.

Reglas:

- `expected_version` es obligatorio en asignar, desasignar, transferir, confirmar, completar y cancelar.
- Si `box.version != expected_version`, responder `409 conflict` con `details.reason = "stale_version"`.
- Si la posicion destino ya esta ocupada, responder `409` con `details.reason = "position_occupied"`.
- Si la caja ya tiene un movimiento abierto, responder `409` con `details.reason = "open_movement_exists"`.
- Si el indice unico de posicion se dispara por una carrera, traducir a `409 position_occupied`.
- Si el indice unico de movimiento abierto se dispara, traducir a `409 open_movement_exists`.
- No usar Redis para locks de negocio. Redis es solo para cache, rate limiting o tareas.

### 6.8 Auditoria e historial

Acciones de auditoria:

| Accion | Entidad | Cuando |
|---|---|---|
| `box.location_assigned` | `box` | Asignacion inicial |
| `box.location_confirmed` | `box` | Confirmacion de ubicacion pendiente |
| `box.location_unassigned` | `box` | Desasignacion |
| `box.location_transferred` | `box` | Traslado inmediato o inicio de transito |
| `box.location_transfer_completed` | `box` | Fin de transito |
| `box.location_transfer_cancelled` | `box` | Cancelacion de transito |
| `position_block.created` | `position_block` | Bloqueo de rango |
| `position_block.cancelled` | `position_block` | Desbloqueo |
| `shelf.capacity_applied` | `shelf` | Ya existe en B5; conservar |

Cada evento debe incluir:

- `before` y `after` con `current_position_id`, `custody_status`, `location_precision`, `version`;
- `metadata` con `movement_id`, `history_id`, `position_id`, `mode` y motivo cuando aplique;
- actor autenticado, request id, IP y user agent provistos por `record_audit_event`.

`BoxLocationHistory` es la fuente de verdad del recorrido fisico. La auditoria es la fuente de verdad de quien hizo que y por que. No duplicar en auditoria todo el historial; usar referencias.

---

## 7. Arquitectura y arbol de archivos

### 7.1 Principios

- Mantener separacion `router -> service -> repository -> model`.
- No importar FastAPI desde servicios de dominio salvo `Request` para auditoria, siguiendo el patron B5.
- Esquemas Pydantic separados de modelos ORM.
- Funciones puras de ocupacion en un modulo sin acceso a base de datos.
- Un modulo nuevo `movements` para la maquina de estados de traslados.
- Reutilizar `record_audit_event`, `Page`, `PageParams`, `build_sort_params`, `require_permissions` y errores existentes.
- No crear dependencias nuevas. CSV se genera con `csv` y `io` de la biblioteca estandar.

### 7.2 Arbol objetivo

```text
backend/
  alembic/versions/
    20261102_0002_b6_locations.py                  NUEVO
  src/judicial_archive/
    core/
      enums.py                                     MODIFICAR
    modules/
      boxes/
        constants.py                               NUEVO
        models.py                                  MODIFICAR
        repositories.py                            NUEVO
        schemas.py                                 NUEVO
      locations/
        models.py                                  MODIFICAR
        schemas.py                                 MODIFICAR
        repositories.py                            MODIFICAR
        services.py                                MODIFICAR
        capacity.py                                MODIFICAR (validacion de capacidad)
        occupancy.py                               NUEVO
        blocks.py                                  NUEVO
        routers.py                                 MODIFICAR
        occupancy_router.py                        NUEVO
        blocks_router.py                           NUEVO
        reports.py                                 NUEVO
      movements/
        __init__.py                                NUEVO
        schemas.py                                 NUEVO
        repositories.py                            NUEVO
        services.py                                NUEVO
        routers.py                                 NUEVO
    api/v1/router.py                               MODIFICAR
  tests/
    unit/
      test_location_state.py                       NUEVO
      test_occupancy.py                            NUEVO
    api/
      test_catalogs_api.py                         MODIFICAR (quitar xfail)
      test_locations_openapi.py                    NUEVO
    integration/
      conftest.py                                  MODIFICAR (truncate de historial)
      test_schema_metadata.py                      MODIFICAR
      test_schema_constraints.py                   MODIFICAR
      test_migrations.py                           MODIFICAR
      test_capacity.py                             MODIFICAR (casos API)
      test_location_movements.py                   NUEVO
      test_location_scan.py                        NUEVO
      test_location_concurrency.py                 NUEVO
      test_location_history.py                     NUEVO
docs/
  api.md                                           MODIFICAR
  modelo-de-datos.md                               MODIFICAR
  reglas-de-negocio.md                             MODIFICAR
  inventario-fisico.md                             NUEVO
  pruebas.md                                       MODIFICAR
  seguridad.md                                     MODIFICAR
  roles-y-permisos.md                              MODIFICAR
  decisiones/ADR-0002-numeracion-fases-b6-b7.md    NUEVO
```

### 7.3 Regla de dependencias

```text
routers -> services -> repositories -> models
                 \-> occupancy (puro)
                 \-> audit services
movements/services -> boxes/repositories, locations/repositories, audit
locations/services -> boxes/repositories, locations/repositories, occupancy
boxes/repositories -> boxes/models
locations/repositories -> locations/models, boxes/models
```

Evitar:

- `locations.models` importando `movements`;
- `occupancy.py` importando repositorios o FastAPI;
- `boxes.schemas` importando `movements.schemas`;
- servicios llamando routers.

---

## 8. Implementacion paso a paso

### 8.1 Paso 1 - Enums de dominio

**Archivo:** `backend/src/judicial_archive/core/enums.py`

Agregar `PENDING_VERIFICATION` a `CustodyStatus`:

```python
class CustodyStatus(StrEnum):
    IN_PLACE = "IN_PLACE"
    ON_LOAN = "ON_LOAN"
    IN_TRANSIT = "IN_TRANSIT"
    MISSING = "MISSING"
    IN_RECONCILIATION = "IN_RECONCILIATION"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    UNKNOWN = "UNKNOWN"
```

Agregar `UNASSIGN` a `MovementType`:

```python
class MovementType(StrEnum):
    ASSIGN = "ASSIGN"
    UNASSIGN = "UNASSIGN"
    TRANSFER = "TRANSFER"
    RETURN = "RETURN"
    LOAN_PICKUP = "LOAN_PICKUP"
    LOAN_RETURN = "LOAN_RETURN"
    RECONCILIATION = "RECONCILIATION"
```

Agregar los siguientes enums al final del archivo, antes de `AuditActorType` o en el bloque de enums de ubicacion:

```python
class TransferMode(StrEnum):
    IMMEDIATE = "IMMEDIATE"
    IN_TRANSIT = "IN_TRANSIT"


class LocationState(StrEnum):
    CONFIRMED = "CONFIRMED"
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    IN_RECONCILIATION = "IN_RECONCILIATION"
    ON_LOAN = "ON_LOAN"
    IN_TRANSIT = "IN_TRANSIT"
    MISSING = "MISSING"
    UNASSIGNED = "UNASSIGNED"


class LocationHistorySource(StrEnum):
    API = "API"
    RECONCILIATION = "RECONCILIATION"
    IMPORT = "IMPORT"
    SYSTEM = "SYSTEM"
    MIGRATION = "MIGRATION"


class PositionOccupancyState(StrEnum):
    EMPTY = "EMPTY"
    OCCUPIED = "OCCUPIED"
    BLOCKED = "BLOCKED"
    RETIRED = "RETIRED"


class ScanKind(StrEnum):
    BOX = "BOX"
    POSITION = "POSITION"
    UNREGISTERED_BOX = "UNREGISTERED_BOX"
```

No modificar el orden de enums existentes que ya esten persistidos; los `CHECK` usan valores, no indices.

### 8.2 Paso 2 - Modelos SQLAlchemy

#### 8.2.1 Archivo `backend/src/judicial_archive/modules/boxes/constants.py` (NUEVO)

```python
from __future__ import annotations

from judicial_archive.core.enums import CustodyStatus, MovementStatus

ACTIVE_LOCATION_CUSTODY_STATUSES = frozenset(
    {
        CustodyStatus.IN_PLACE.value,
        CustodyStatus.IN_RECONCILIATION.value,
        CustodyStatus.PENDING_VERIFICATION.value,
    }
)

OPEN_MOVEMENT_STATUSES = frozenset(
    {
        MovementStatus.PLANNED.value,
        MovementStatus.IN_TRANSIT.value,
    }
)

CUSTODY_WITH_POSITION_SQL = (
    "custody_status IN ('IN_PLACE', 'IN_RECONCILIATION', 'PENDING_VERIFICATION') "
    "AND current_position_id IS NOT NULL"
)
CUSTODY_WITHOUT_POSITION_SQL = (
    "custody_status NOT IN ('IN_PLACE', 'IN_RECONCILIATION', 'PENDING_VERIFICATION') "
    "AND current_position_id IS NULL"
)
```

#### 8.2.2 Archivo `backend/src/judicial_archive/modules/boxes/models.py`

**a) Imports.** Agregar `LocationHistorySource` y `enum_values`:

```python
from judicial_archive.core.enums import (
    BoxLifecycleStatus,
    BoxType,
    Confidentiality,
    CustodyStatus,
    LocationHistorySource,
    LocationPrecision,
    MovementStatus,
    MovementType,
)
from judicial_archive.db.mixins import (
    OptimisticLockMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_in,
    enum_values,
)
```

**b) `Box.__table_args__`.** Reemplazar el `CheckConstraint` de custodia/posicion por:

```python
(
    CheckConstraint(
        "("
        "(custody_status IN ('IN_PLACE', 'IN_RECONCILIATION', 'PENDING_VERIFICATION') "
        "AND current_position_id IS NOT NULL)"
        " OR (custody_status NOT IN ('IN_PLACE', 'IN_RECONCILIATION', 'PENDING_VERIFICATION') "
        "AND current_position_id IS NULL)"
        ")",
        name="ck_boxes_custody_position",
    ),
)
```

Reemplazar el indice unico parcial por:

```python
(
    Index(
        "uq_boxes_current_position_occupied",
        "current_position_id",
        unique=True,
        postgresql_where=text(
            "custody_status IN ('IN_PLACE', 'IN_RECONCILIATION', 'PENDING_VERIFICATION') "
            "AND current_position_id IS NOT NULL"
        ),
    ),
)
```

**c) `BoxMovement.__table_args__`.** Agregar el indice de movimiento abierto:

```python
(
    Index(
        "uq_box_movements_open_box",
        "box_id",
        unique=True,
        postgresql_where=text("movement_status IN ('PLANNED', 'IN_TRANSIT')"),
    ),
)
```

**d) Nueva clase `BoxLocationHistory`.** Insertar despues de `BoxNumberHistory` y antes de `BoxMovement`:

```python
class BoxLocationHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "box_location_history"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(reason)) > 0",
            name="ck_box_location_history_reason_not_empty",
        ),
        CheckConstraint(
            "from_custody_status IS NULL OR "
            f"from_custody_status IN ({enum_values(CustodyStatus)})",
            name="ck_box_location_history_from_custody",
        ),
        CheckConstraint(
            f"to_custody_status IN ({enum_values(CustodyStatus)})",
            name="ck_box_location_history_to_custody",
        ),
        CheckConstraint(
            "from_location_precision IS NULL OR "
            f"from_location_precision IN ({enum_values(LocationPrecision)})",
            name="ck_box_location_history_from_precision",
        ),
        CheckConstraint(
            f"to_location_precision IN ({enum_values(LocationPrecision)})",
            name="ck_box_location_history_to_precision",
        ),
        check_in(
            "source", LocationHistorySource, name="ck_box_location_history_source"
        ),
        Index("ix_box_location_history_box_changed", "box_id", "changed_at"),
        Index("ix_box_location_history_to_position", "to_position_id", "changed_at"),
        Index("ix_box_location_history_movement", "movement_id"),
    )

    box_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("boxes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    movement_id: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("box_movements.id", ondelete="RESTRICT"),
        nullable=True,
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
    from_custody_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    to_custody_status: Mapped[str] = mapped_column(String(24), nullable=False)
    from_location_precision: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    to_location_precision: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=LocationHistorySource.API.value,
        server_default=LocationHistorySource.API.value,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    changed_by: Mapped[UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
```

No agregar `TimestampMixin` ni `OptimisticLockMixin` a `BoxLocationHistory`: es append-only y no se actualiza.

#### 8.2.3 Archivo `backend/src/judicial_archive/modules/locations/models.py`

**a) `PositionBlock.__table_args__`.** Agregar:

```python
(
    CheckConstraint(
        "cancelled_at IS NULL OR "
        "(cancellation_reason IS NOT NULL AND length(btrim(cancellation_reason)) > 0)",
        name="ck_position_blocks_cancellation_reason",
    ),
)
```

**b) `PositionBlock`.** Agregar despues de `cancelled_by`:

```python
    cancellation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

No cambiar `PositionStatus`: `BLOCKED` ya existe. La ocupacion se deriva de `Box`, no se agrega un estado `OCCUPIED` a la posicion.

### 8.3 Paso 3 - Migracion Alembic

**Archivo:** `backend/alembic/versions/20261102_0002_b6_locations.py`

```python
"""B6 locations, history and movement constraints

Revision ID: 20261102_0002
Revises: 8c8fec15b660
Create Date: 2026-11-02 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261102_0002"
down_revision: Union[str, Sequence[str], None] = "8c8fec15b660"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CUSTODY_VALUES = (
    "'IN_PLACE', 'ON_LOAN', 'IN_TRANSIT', 'MISSING', "
    "'IN_RECONCILIATION', 'PENDING_VERIFICATION', 'UNKNOWN'"
)
ACTIVE_CUSTODY = "'IN_PLACE', 'IN_RECONCILIATION', 'PENDING_VERIFICATION'"
MOVEMENT_TYPES = (
    "'ASSIGN', 'UNASSIGN', 'TRANSFER', 'RETURN', "
    "'LOAN_PICKUP', 'LOAN_RETURN', 'RECONCILIATION'"
)


def upgrade() -> None:
    op.drop_constraint("ck_boxes_custody_status", "boxes", type_="check")
    op.create_check_constraint(
        "ck_boxes_custody_status",
        "boxes",
        f"custody_status IN ({CUSTODY_VALUES})",
    )

    op.drop_constraint("ck_boxes_custody_position", "boxes", type_="check")
    op.create_check_constraint(
        "ck_boxes_custody_position",
        "boxes",
        "("
        f"(custody_status IN ({ACTIVE_CUSTODY}) AND current_position_id IS NOT NULL)"
        f" OR (custody_status NOT IN ({ACTIVE_CUSTODY}) AND current_position_id IS NULL)"
        ")",
    )

    op.drop_index("uq_boxes_current_position_occupied", table_name="boxes")
    op.create_index(
        "uq_boxes_current_position_occupied",
        "boxes",
        ["current_position_id"],
        unique=True,
        postgresql_where=sa.text(
            f"custody_status IN ({ACTIVE_CUSTODY}) AND current_position_id IS NOT NULL"
        ),
    )

    op.drop_constraint("ck_box_movements_type", "box_movements", type_="check")
    op.create_check_constraint(
        "ck_box_movements_type",
        "box_movements",
        f"movement_type IN ({MOVEMENT_TYPES})",
    )

    op.create_index(
        "uq_box_movements_open_box",
        "box_movements",
        ["box_id"],
        unique=True,
        postgresql_where=sa.text("movement_status IN ('PLANNED', 'IN_TRANSIT')"),
    )

    op.add_column(
        "position_blocks",
        sa.Column("cancellation_reason", sa.String(length=500), nullable=True),
    )
    op.create_check_constraint(
        "ck_position_blocks_cancellation_reason",
        "position_blocks",
        "cancelled_at IS NULL OR "
        "(cancellation_reason IS NOT NULL AND length(btrim(cancellation_reason)) > 0)",
    )

    op.create_table(
        "box_location_history",
        sa.Column("box_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_position_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("to_position_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_custody_status", sa.String(length=24), nullable=True),
        sa.Column("to_custody_status", sa.String(length=24), nullable=False),
        sa.Column("from_location_precision", sa.String(length=16), nullable=True),
        sa.Column("to_location_precision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column(
            "source",
            sa.String(length=16),
            server_default="API",
            nullable=False,
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(reason)) > 0",
            name="ck_box_location_history_reason_not_empty",
        ),
        sa.CheckConstraint(
            f"from_custody_status IS NULL OR from_custody_status IN ({CUSTODY_VALUES})",
            name="ck_box_location_history_from_custody",
        ),
        sa.CheckConstraint(
            f"to_custody_status IN ({CUSTODY_VALUES})",
            name="ck_box_location_history_to_custody",
        ),
        sa.CheckConstraint(
            "from_location_precision IS NULL OR "
            "from_location_precision IN ('CONFIRMED', 'PENDING', 'UNKNOWN')",
            name="ck_box_location_history_from_precision",
        ),
        sa.CheckConstraint(
            "to_location_precision IN ('CONFIRMED', 'PENDING', 'UNKNOWN')",
            name="ck_box_location_history_to_precision",
        ),
        sa.CheckConstraint(
            "source IN ('API', 'RECONCILIATION', 'IMPORT', 'SYSTEM', 'MIGRATION')",
            name="ck_box_location_history_source",
        ),
        sa.ForeignKeyConstraint(
            ["box_id"],
            ["boxes.id"],
            name="fk_box_location_history_box_id_boxes",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["movement_id"],
            ["box_movements.id"],
            name="fk_box_location_history_movement_id_box_movements",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["from_position_id"],
            ["positions.id"],
            name="fk_box_location_history_from_position_id_positions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["to_position_id"],
            ["positions.id"],
            name="fk_box_location_history_to_position_id_positions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by"],
            ["users.id"],
            name="fk_box_location_history_changed_by_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_box_location_history"),
    )
    op.create_index(
        "ix_box_location_history_box_changed",
        "box_location_history",
        ["box_id", "changed_at"],
        unique=False,
    )
    op.create_index(
        "ix_box_location_history_to_position",
        "box_location_history",
        ["to_position_id", "changed_at"],
        unique=False,
    )
    op.create_index(
        "ix_box_location_history_movement",
        "box_location_history",
        ["movement_id"],
        unique=False,
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION sga_location_history_append_only()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'box_location_history es append-only'
                USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$;
        """
    )
    op.execute(
        "CREATE TRIGGER trg_box_location_history_append_only "
        "BEFORE UPDATE OR DELETE ON box_location_history "
        "FOR EACH ROW EXECUTE FUNCTION sga_location_history_append_only()"
    )
    op.execute(
        "CREATE TRIGGER trg_box_location_history_no_truncate "
        "BEFORE TRUNCATE ON box_location_history "
        "FOR EACH STATEMENT EXECUTE FUNCTION sga_location_history_append_only()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_box_location_history_no_truncate "
        "ON box_location_history"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_box_location_history_append_only "
        "ON box_location_history"
    )
    op.execute("DROP FUNCTION IF EXISTS sga_location_history_append_only()")

    op.drop_index("ix_box_location_history_movement", table_name="box_location_history")
    op.drop_index(
        "ix_box_location_history_to_position",
        table_name="box_location_history",
    )
    op.drop_index(
        "ix_box_location_history_box_changed",
        table_name="box_location_history",
    )
    op.drop_table("box_location_history")

    op.drop_constraint(
        "ck_position_blocks_cancellation_reason",
        "position_blocks",
        type_="check",
    )
    op.drop_column("position_blocks", "cancellation_reason")

    op.drop_index("uq_box_movements_open_box", table_name="box_movements")

    op.drop_constraint("ck_box_movements_type", "box_movements", type_="check")
    op.create_check_constraint(
        "ck_box_movements_type",
        "box_movements",
        "movement_type IN ('ASSIGN', 'TRANSFER', 'RETURN', "
        "'LOAN_PICKUP', 'LOAN_RETURN', 'RECONCILIATION')",
    )

    op.drop_index("uq_boxes_current_position_occupied", table_name="boxes")
    op.create_index(
        "uq_boxes_current_position_occupied",
        "boxes",
        ["current_position_id"],
        unique=True,
        postgresql_where=sa.text(
            "custody_status IN ('IN_PLACE', 'IN_RECONCILIATION') "
            "AND current_position_id IS NOT NULL"
        ),
    )

    op.drop_constraint("ck_boxes_custody_position", "boxes", type_="check")
    op.create_check_constraint(
        "ck_boxes_custody_position",
        "boxes",
        "("
        "(custody_status IN ('IN_PLACE', 'IN_RECONCILIATION') "
        "AND current_position_id IS NOT NULL)"
        " OR (custody_status NOT IN ('IN_PLACE', 'IN_RECONCILIATION') "
        "AND current_position_id IS NULL)"
        ")",
    )

    op.drop_constraint("ck_boxes_custody_status", "boxes", type_="check")
    op.create_check_constraint(
        "ck_boxes_custody_status",
        "boxes",
        "custody_status IN ('IN_PLACE', 'ON_LOAN', 'IN_TRANSIT', "
        "'MISSING', 'IN_RECONCILIATION', 'UNKNOWN')",
    )
```

**Preflight obligatorio antes de downgrade:**

```sql
SELECT count(*) FROM boxes WHERE custody_status = 'PENDING_VERIFICATION';
SELECT count(*) FROM box_movements WHERE movement_type = 'UNASSIGN';
```

Si cualquiera es mayor que cero, el downgrade fallara al restaurar los `CHECK`. No borrar datos para forzar el downgrade. Documentar y resolver con una migracion correctiva o un plan de datos aprobado.

### 8.4 Paso 4 - Esquemas Pydantic

#### 8.4.1 Correccion obligatoria en `modules/locations/schemas.py`

Reemplazar el validador defectuoso de `ShelfCreate`:

```python
    @field_validator("positions_per_level")
    @classmethod
    def _pair_and_total(cls, value: int | None, info: ValidationInfo) -> int | None:
        levels = info.data.get("levels")

        if (levels is None) != (value is None):
            raise ValueError("levels y positions_per_level deben enviarse juntos.")

        if levels is not None and value is not None and levels * value > 5000:
            raise ValueError("La capacidad total no puede superar 5000 posiciones.")
        return value
```

Agregar los esquemas de ubicacion al final de `modules/locations/schemas.py`:

```python
class AreaPathOut(BaseModel):
    id: UUID
    code: str
    name: str


class ShelfPathOut(BaseModel):
    id: UUID
    code: str
    name: str | None


class TrayPathOut(BaseModel):
    id: UUID
    code: str
    name: str | None


class PositionPathOut(BaseModel):
    position_id: UUID
    position_code: str
    label: str
    position_status: str
    tray: TrayPathOut
    shelf: ShelfPathOut
    area: AreaPathOut


class CapacityMismatchOut(BaseModel):
    shelf_id: UUID
    shelf_code: str
    configured: int
    visible: int
    delta: int


class OccupancySummaryOut(BaseModel):
    scope: Literal["GLOBAL", "AREA", "SHELF", "TRAY"]
    scope_id: UUID | None
    configured_capacity: int | None
    visible_capacity: int
    occupied_positions: int
    available_positions: int
    blocked_positions: int
    retired_positions: int
    occupancy_rate: float
    unlocated_boxes: int
    pending_confirmation_boxes: int
    in_transit_boxes: int
    capacity_matches_configuration: bool
    capacity_mismatches: list[CapacityMismatchOut]
    conflicts: list[str]


class PositionOccupancyOut(BaseModel):
    position: PositionPathOut
    state: Literal["EMPTY", "OCCUPIED", "BLOCKED", "RETIRED"]
    box: BoxSummaryOut | None
    block_id: UUID | None


class LocationPlanPositionOut(PositionOccupancyOut):
    pass


class LocationPlanTrayOut(BaseModel):
    tray: TrayPathOut
    visible_capacity: int
    occupied_positions: int
    positions: list[LocationPlanPositionOut] | None


class LocationPlanShelfOut(BaseModel):
    shelf: ShelfPathOut
    configured_capacity: int | None
    visible_capacity: int
    occupied_positions: int
    available_positions: int
    blocked_positions: int
    trays: list[LocationPlanTrayOut]


class LocationPlanOut(BaseModel):
    area: AreaPathOut | None
    shelves: list[LocationPlanShelfOut]
    summary: OccupancySummaryOut


class UnlocatedBoxOut(BaseModel):
    box: BoxSummaryOut
    location_state: Literal["UNASSIGNED", "PENDING_CONFIRMATION", "MISSING"]
    last_movement_at: datetime | None


class ScanBoxOut(BaseModel):
    kind: Literal["BOX"]
    box: BoxSummaryOut
    current_position: PositionPathOut | None
    location_state: str
    operable: bool
    message: str


class ScanPositionOut(BaseModel):
    kind: Literal["POSITION"]
    position: PositionPathOut
    state: Literal["EMPTY", "OCCUPIED", "BLOCKED", "RETIRED"]
    box: BoxSummaryOut | None
    message: str


class ScanUnregisteredOut(BaseModel):
    kind: Literal["UNREGISTERED_BOX"]
    box_number: str
    message: str


class ScanResponse(BaseModel):
    kind: Literal["BOX", "POSITION", "UNREGISTERED_BOX"]
    box: BoxSummaryOut | None = None
    position: PositionPathOut | None = None
    position_state: Literal["EMPTY", "OCCUPIED", "BLOCKED", "RETIRED"] | None = None
    box_number: str | None = None
    current_position: PositionPathOut | None = None
    location_state: str | None = None
    operable: bool | None = None
    message: str


class PositionBlockCreate(BaseModel):
    shelf_id: UUID
    start_position_id: UUID
    end_position_id: UUID
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class PositionBlockCancel(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class PositionBlockOut(BaseModel):
    id: UUID
    shelf_id: UUID
    start_position: PositionPathOut
    end_position: PositionPathOut
    first_position_number: int
    last_position_number: int
    reason: str
    notes: str | None
    blocked_by: UUID | None
    cancelled_at: datetime | None
    cancelled_by: UUID | None
    cancellation_reason: str | None
    created_at: datetime


class OccupancyReportRowOut(BaseModel):
    area_code: str
    area_name: str
    shelf_code: str
    shelf_name: str | None
    configured_capacity: int | None
    visible_capacity: int
    occupied_positions: int
    available_positions: int
    blocked_positions: int
    retired_positions: int
    occupancy_rate: float
    capacity_matches: bool


class OccupancyReportOut(BaseModel):
    generated_at: datetime
    area_id: UUID | None
    shelf_id: UUID | None
    totals: OccupancySummaryOut
    rows: list[OccupancyReportRowOut]
```

Agregar al inicio del archivo, despues de imports:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from judicial_archive.modules.boxes.schemas import BoxSummaryOut
```

Y al final, para resolver las referencias forward:

```python
from judicial_archive.modules.boxes.schemas import BoxSummaryOut  # noqa: E402

PositionOccupancyOut.model_rebuild()
UnlocatedBoxOut.model_rebuild()
ScanBoxOut.model_rebuild()
ScanPositionOut.model_rebuild()
ScanResponse.model_rebuild()
```

No usar `from __future__ import annotations` para resolver esto en runtime; el archivo ya lo tiene, pero Pydantic necesita los tipos reales para `model_rebuild`. Si se prefiere evitar el import tardio, mover `BoxSummaryOut` a un modulo neutral `modules/boxes/schemas.py` y importarlo normalmente al inicio. La guia usa el import tardio para no romper la carga circular.

#### 8.4.2 Archivo `modules/boxes/schemas.py` (NUEVO)

```python
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BoxSummaryOut(BaseModel):
    box_id: UUID
    visible_number: str
    box_type: str
    year: int
    court_id: UUID
    lifecycle_status: str
    custody_status: str
    location_precision: str
    location_state: str


class BoxLocationOut(BaseModel):
    box: BoxSummaryOut
    current_position_id: UUID | None
    version: int


class BoxLocationHistoryOut(BaseModel):
    id: UUID
    box_id: UUID
    movement_id: UUID | None
    from_position_id: UUID | None
    to_position_id: UUID | None
    from_custody_status: str | None
    to_custody_status: str
    from_location_precision: str | None
    to_location_precision: str
    reason: str
    source: str
    changed_at: datetime
    changed_by: UUID | None
    notes: str | None
```

#### 8.4.3 Archivo `modules/movements/schemas.py` (NUEVO)

```python
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from judicial_archive.core.enums import TransferMode
from judicial_archive.modules.boxes.schemas import (
    BoxLocationHistoryOut,
    BoxSummaryOut,
)
from judicial_archive.modules.locations.schemas import PositionPathOut


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("El valor no puede estar vacio.")
    return value


class AssignRequest(BaseModel):
    position_id: UUID
    confirmed: bool = False
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class UnassignRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class TransferRequest(BaseModel):
    to_position_id: UUID
    mode: TransferMode = TransferMode.IMMEDIATE
    confirmed: bool = False
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class ConfirmRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class CompleteMovementRequest(BaseModel):
    confirmed: bool = True
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class CancelMovementRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)
    expected_version: int = Field(ge=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        return _not_blank(value)


class MovementOut(BaseModel):
    id: UUID
    box_id: UUID
    movement_type: str
    movement_status: str
    from_position: PositionPathOut | None
    to_position: PositionPathOut | None
    occurred_at: datetime
    completed_at: datetime | None
    cancelled_at: datetime | None
    reason: str
    performed_by: UUID | None
    notes: str | None
    version: int


class BoxLocationDetailOut(BaseModel):
    box: BoxSummaryOut
    current_position: PositionPathOut | None
    open_movement: MovementOut | None
    last_movement: MovementOut | None
    history_count: int
    operable: bool
    version: int


class LocationMutationOut(BaseModel):
    box: BoxLocationDetailOut
    movement: MovementOut | None
    history: BoxLocationHistoryOut
```

### 8.5 Paso 5 - Repositorios

#### 8.5.1 Archivo `modules/boxes/repositories.py` (NUEVO)

```python
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.enums import CustodyStatus
from judicial_archive.core.text import escape_like
from judicial_archive.modules.boxes.models import Box, BoxLocationHistory


class BoxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, box_id: UUID) -> Box | None:
        return await self.session.get(Box, box_id)

    async def get_for_update(self, box_id: UUID) -> Box | None:
        return await self.session.scalar(
            select(Box).where(Box.id == box_id).with_for_update()
        )

    async def get_by_visible_number(self, visible_number: str) -> Box | None:
        return await self.session.scalar(
            select(Box).where(Box.visible_number == visible_number.strip())
        )

    async def list_unlocated(
        self,
        *,
        state: str | None,
        q: str | None,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Box], int]:
        conditions = []
        if state == "UNASSIGNED":
            conditions.append(Box.current_position_id.is_(None))
            conditions.append(
                Box.custody_status.in_(
                    [CustodyStatus.UNKNOWN.value, CustodyStatus.MISSING.value]
                )
            )
        elif state == "PENDING_CONFIRMATION":
            conditions.append(
                Box.custody_status == CustodyStatus.PENDING_VERIFICATION.value
            )
        else:
            conditions.append(
                or_(
                    Box.current_position_id.is_(None),
                    Box.custody_status == CustodyStatus.PENDING_VERIFICATION.value,
                )
            )
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(Box.visible_number.ilike(pattern, escape="\\"))

        base = select(Box).where(*conditions)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        rows = await self.session.execute(
            base.order_by(Box.visible_number.asc(), Box.id.asc())
            .offset(offset)
            .limit(limit)
        )
        return rows.scalars().all(), int(total or 0)

    async def list_history(
        self,
        box_id: UUID,
        *,
        from_date: datetime | None,
        to_date: datetime | None,
        source: str | None,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[BoxLocationHistory], int]:
        conditions = [BoxLocationHistory.box_id == box_id]
        if from_date is not None:
            conditions.append(BoxLocationHistory.changed_at >= from_date)
        if to_date is not None:
            conditions.append(BoxLocationHistory.changed_at <= to_date)
        if source:
            conditions.append(BoxLocationHistory.source == source)

        base = select(BoxLocationHistory).where(*conditions)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        rows = await self.session.execute(
            base.order_by(
                BoxLocationHistory.changed_at.desc(),
                BoxLocationHistory.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return rows.scalars().all(), int(total or 0)

    async def count_history(self, box_id: UUID) -> int:
        result = await self.session.scalar(
            select(func.count())
            .select_from(BoxLocationHistory)
            .where(BoxLocationHistory.box_id == box_id)
        )
        return int(result or 0)

    async def get_last_history_for_movement(
        self, movement_id: UUID
    ) -> BoxLocationHistory | None:
        return await self.session.scalar(
            select(BoxLocationHistory)
            .where(BoxLocationHistory.movement_id == movement_id)
            .order_by(
                BoxLocationHistory.changed_at.desc(),
                BoxLocationHistory.id.desc(),
            )
            .limit(1)
        )
```

#### 8.5.2 Archivo `modules/movements/repositories.py` (NUEVO)

```python
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.modules.boxes.constants import OPEN_MOVEMENT_STATUSES
from judicial_archive.modules.boxes.models import BoxMovement


class MovementsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, movement_id: UUID) -> BoxMovement | None:
        return await self.session.get(BoxMovement, movement_id)

    async def get_for_update(self, movement_id: UUID) -> BoxMovement | None:
        return await self.session.scalar(
            select(BoxMovement).where(BoxMovement.id == movement_id).with_for_update()
        )

    async def get_open_for_box(self, box_id: UUID) -> BoxMovement | None:
        return await self.session.scalar(
            select(BoxMovement)
            .where(
                BoxMovement.box_id == box_id,
                BoxMovement.movement_status.in_(OPEN_MOVEMENT_STATUSES),
            )
            .order_by(BoxMovement.occurred_at.desc())
            .limit(1)
        )

    async def list(
        self,
        *,
        box_id: UUID | None,
        movement_type: str | None,
        movement_status: str | None,
        from_date: datetime | None,
        to_date: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[BoxMovement], int]:
        conditions = []
        if box_id:
            conditions.append(BoxMovement.box_id == box_id)
        if movement_type:
            conditions.append(BoxMovement.movement_type == movement_type)
        if movement_status:
            conditions.append(BoxMovement.movement_status == movement_status)
        if from_date is not None:
            conditions.append(BoxMovement.occurred_at >= from_date)
        if to_date is not None:
            conditions.append(BoxMovement.occurred_at <= to_date)

        base = select(BoxMovement).where(*conditions)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        rows = await self.session.execute(
            base.order_by(
                BoxMovement.occurred_at.desc(),
                BoxMovement.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return rows.scalars().all(), int(total or 0)

    async def get_last_for_box(self, box_id: UUID) -> BoxMovement | None:
        return await self.session.scalar(
            select(BoxMovement)
            .where(BoxMovement.box_id == box_id)
            .order_by(
                BoxMovement.occurred_at.desc(),
                BoxMovement.id.desc(),
            )
            .limit(1)
        )
```

#### 8.5.3 Ampliar `modules/locations/repositories.py`

Agregar imports:

```python
from datetime import datetime
from sqlalchemy import and_
from judicial_archive.modules.boxes.constants import (
    ACTIVE_LOCATION_CUSTODY_STATUSES,
)
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.locations.models import (
    Area,
    Position,
    PositionBlock,
    Shelf,
    Tray,
)
```

Agregar metodos:

```python
async def get_position_for_update(self, position_id: UUID) -> Position | None:
    return await self.session.scalar(
        select(Position).where(Position.id == position_id).with_for_update()
    )


async def get_positions_for_update(
    self, position_ids: Sequence[UUID]
) -> Sequence[Position]:
    if not position_ids:
        return []
    rows = await self.session.scalars(
        select(Position)
        .where(Position.id.in_(sorted(set(position_ids), key=str)))
        .order_by(Position.id.asc())
        .with_for_update()
    )
    return rows.all()


async def get_position_path(
    self, position_id: UUID
) -> tuple[Position, Tray, Shelf, Area] | None:
    row = await self.session.execute(
        select(Position, Tray, Shelf, Area)
        .join(Tray, Tray.id == Position.tray_id)
        .join(Shelf, Shelf.id == Tray.shelf_id)
        .join(Area, Area.id == Shelf.area_id)
        .where(Position.id == position_id)
    )
    result = row.one_or_none()
    return None if result is None else tuple(result)


async def list_position_paths(
    self, position_ids: Sequence[UUID]
) -> dict[UUID, tuple[Position, Tray, Shelf, Area]]:
    if not position_ids:
        return {}
    rows = await self.session.execute(
        select(Position, Tray, Shelf, Area)
        .join(Tray, Tray.id == Position.tray_id)
        .join(Shelf, Shelf.id == Tray.shelf_id)
        .join(Area, Area.id == Shelf.area_id)
        .where(Position.id.in_(position_ids))
    )
    return {position.id: tuple(row) for row in rows.all()}


async def list_shelves_for_scope(
    self, *, area_id: UUID | None, shelf_id: UUID | None
) -> Sequence[Shelf]:
    conditions = []
    if area_id:
        conditions.append(Shelf.area_id == area_id)
    if shelf_id:
        conditions.append(Shelf.id == shelf_id)
    rows = await self.session.scalars(
        select(Shelf).where(*conditions).order_by(Shelf.code.asc(), Shelf.id.asc())
    )
    return rows.all()


async def list_trays_for_scope(
    self, *, area_id: UUID | None, shelf_id: UUID | None, tray_id: UUID | None
) -> Sequence[Tray]:
    conditions = []
    if area_id:
        conditions.append(Shelf.area_id == area_id)
    if shelf_id:
        conditions.append(Tray.shelf_id == shelf_id)
    if tray_id:
        conditions.append(Tray.id == tray_id)
    rows = await self.session.scalars(
        select(Tray)
        .join(Shelf, Shelf.id == Tray.shelf_id)
        .where(*conditions)
        .order_by(Tray.shelf_id.asc(), Tray.code.asc(), Tray.id.asc())
    )
    return rows.all()


async def list_positions_for_scope(
    self,
    *,
    area_id: UUID | None,
    shelf_id: UUID | None,
    tray_id: UUID | None,
) -> Sequence[Position]:
    conditions = []
    if area_id:
        conditions.append(Shelf.area_id == area_id)
    if shelf_id:
        conditions.append(Tray.shelf_id == shelf_id)
    if tray_id:
        conditions.append(Position.tray_id == tray_id)
    rows = await self.session.scalars(
        select(Position)
        .join(Tray, Tray.id == Position.tray_id)
        .join(Shelf, Shelf.id == Tray.shelf_id)
        .where(*conditions)
        .order_by(Tray.code.asc(), Position.code.asc(), Position.id.asc())
    )
    return rows.all()


async def list_boxes_for_positions(self, position_ids: Sequence[UUID]) -> Sequence[Box]:
    if not position_ids:
        return []
    rows = await self.session.scalars(
        select(Box).where(
            Box.current_position_id.in_(position_ids),
            Box.custody_status.in_(ACTIVE_LOCATION_CUSTODY_STATUSES),
        )
    )
    return rows.all()


async def get_box_at_position(self, position_id: UUID) -> Box | None:
    return await self.session.scalar(
        select(Box).where(
            Box.current_position_id == position_id,
            Box.custody_status.in_(ACTIVE_LOCATION_CUSTODY_STATUSES),
        )
    )


async def list_active_blocks(self, shelf_id: UUID) -> Sequence[PositionBlock]:
    rows = await self.session.scalars(
        select(PositionBlock)
        .where(
            PositionBlock.shelf_id == shelf_id,
            PositionBlock.cancelled_at.is_(None),
        )
        .order_by(
            PositionBlock.first_position_number.asc(),
            PositionBlock.id.asc(),
        )
    )
    return rows.all()


async def has_overlapping_block(
    self,
    shelf_id: UUID,
    first_number: int,
    last_number: int,
) -> bool:
    result = await self.session.scalar(
        select(func.count())
        .select_from(PositionBlock)
        .where(
            PositionBlock.shelf_id == shelf_id,
            PositionBlock.cancelled_at.is_(None),
            PositionBlock.first_position_number <= last_number,
            PositionBlock.last_position_number >= first_number,
        )
    )
    return bool(result)


async def list_position_occupancy(
    self,
    *,
    area_id: UUID | None,
    shelf_id: UUID | None,
    tray_id: UUID | None,
    state: str | None,
    q: str | None,
    offset: int,
    limit: int,
) -> tuple[Sequence[tuple[Position, Tray, Shelf, Area, Box | None]], int]:
    conditions = []
    if area_id:
        conditions.append(Area.id == area_id)
    if shelf_id:
        conditions.append(Shelf.id == shelf_id)
    if tray_id:
        conditions.append(Tray.id == tray_id)
    if q:
        pattern = f"%{escape_like(q.strip())}%"
        conditions.append(
            or_(
                Position.code.ilike(pattern, escape="\\"),
                Position.label.ilike(pattern, escape="\\"),
                Tray.code.ilike(pattern, escape="\\"),
                Shelf.code.ilike(pattern, escape="\\"),
                Area.code.ilike(pattern, escape="\\"),
            )
        )
    if state == "OCCUPIED":
        conditions.append(Box.id.is_not(None))
    elif state == "EMPTY":
        conditions.append(Box.id.is_(None))
        conditions.append(Position.status == "AVAILABLE")
    elif state == "BLOCKED":
        conditions.append(Position.status == "BLOCKED")
    elif state == "RETIRED":
        conditions.append(Position.status == "RETIRED")

    base = (
        select(Position, Tray, Shelf, Area, Box)
        .join(Tray, Tray.id == Position.tray_id)
        .join(Shelf, Shelf.id == Tray.shelf_id)
        .join(Area, Area.id == Shelf.area_id)
        .outerjoin(
            Box,
            and_(
                Box.current_position_id == Position.id,
                Box.custody_status.in_(ACTIVE_LOCATION_CUSTODY_STATUSES),
            ),
        )
        .where(*conditions)
    )
    total = await self.session.scalar(select(func.count()).select_from(base.subquery()))
    rows = await self.session.execute(
        base.order_by(
            Area.code.asc(),
            Shelf.code.asc(),
            Tray.code.asc(),
            Position.code.asc(),
            Position.id.asc(),
        )
        .offset(offset)
        .limit(limit)
    )
    return [tuple(row) for row in rows.all()], int(total or 0)
```

`list_position_occupancy` usa `escape_like` y `or_`, que ya estan importados en el archivo. Si no, agregarlos.

### 8.6 Paso 6 - Modulo puro de ocupacion

**Archivo:** `backend/src/judicial_archive/modules/locations/occupancy.py` (NUEVO)

```python
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from judicial_archive.core.enums import (
    CustodyStatus,
    LocationPrecision,
    LocationState,
    PositionOccupancyState,
    PositionStatus,
)
from judicial_archive.modules.boxes.constants import ACTIVE_LOCATION_CUSTODY_STATUSES
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.locations.models import Position, Shelf


@dataclass(frozen=True)
class CapacityMismatch:
    shelf_id: UUID
    shelf_code: str
    configured: int
    visible: int

    @property
    def delta(self) -> int:
        return self.visible - self.configured


@dataclass(frozen=True)
class OccupancyCounts:
    configured_capacity: int | None
    visible_capacity: int
    occupied_positions: int
    available_positions: int
    blocked_positions: int
    retired_positions: int
    occupancy_rate: float
    unlocated_boxes: int = 0
    pending_confirmation_boxes: int = 0
    in_transit_boxes: int = 0
    capacity_mismatches: tuple[CapacityMismatch, ...] = ()
    conflicts: tuple[str, ...] = ()

    @property
    def capacity_matches_configuration(self) -> bool:
        return not self.capacity_mismatches


def precision_for(custody_status: str, position_id: UUID | None) -> str:
    if position_id is None:
        return LocationPrecision.UNKNOWN.value
    if custody_status == CustodyStatus.IN_PLACE.value:
        return LocationPrecision.CONFIRMED.value
    return LocationPrecision.PENDING.value


def classify_location_state(box: Box) -> str:
    if box.custody_status == CustodyStatus.IN_PLACE.value:
        return LocationState.CONFIRMED.value
    if box.custody_status == CustodyStatus.PENDING_VERIFICATION.value:
        return LocationState.PENDING_CONFIRMATION.value
    if box.custody_status == CustodyStatus.IN_RECONCILIATION.value:
        return LocationState.IN_RECONCILIATION.value
    if box.custody_status == CustodyStatus.ON_LOAN.value:
        return LocationState.ON_LOAN.value
    if box.custody_status == CustodyStatus.IN_TRANSIT.value:
        return LocationState.IN_TRANSIT.value
    if box.custody_status == CustodyStatus.MISSING.value:
        return LocationState.MISSING.value
    return LocationState.UNASSIGNED.value


def is_operable(box: Box) -> bool:
    if box.lifecycle_status != "ACTIVE":
        return False
    return box.custody_status in {
        CustodyStatus.UNKNOWN.value,
        CustodyStatus.MISSING.value,
        CustodyStatus.IN_PLACE.value,
        CustodyStatus.PENDING_VERIFICATION.value,
    }


def position_occupancy_state(
    position: Position,
    box: Box | None,
) -> str:
    if position.status == PositionStatus.RETIRED.value:
        return PositionOccupancyState.RETIRED.value
    if position.status == PositionStatus.BLOCKED.value:
        return PositionOccupancyState.BLOCKED.value
    if box is not None:
        return PositionOccupancyState.OCCUPIED.value
    return PositionOccupancyState.EMPTY.value


def compute_shelf_occupancy(
    shelf: Shelf,
    positions: Sequence[Position],
    boxes_by_position: Mapping[UUID, Box],
) -> OccupancyCounts:
    visible = [position for position in positions if position.status != "RETIRED"]
    retired = len(positions) - len(visible)
    blocked = sum(
        1 for position in visible if position.status == PositionStatus.BLOCKED.value
    )
    occupied = 0
    conflicts: list[str] = []

    for position in visible:
        box = boxes_by_position.get(position.id)
        if box is None:
            continue
        if box.custody_status not in ACTIVE_LOCATION_CUSTODY_STATUSES:
            conflicts.append(
                f"La caja {box.visible_number} tiene posicion pero custodia "
                f"{box.custody_status}."
            )
            continue
        if position.status != PositionStatus.AVAILABLE.value:
            conflicts.append(
                f"La posicion {position.code} esta {position.status} y tiene caja."
            )
            continue
        occupied += 1

    available = max(0, len(visible) - occupied - blocked)
    configured = shelf.capacity_positions
    mismatches: list[CapacityMismatch] = []
    if configured is not None and configured != len(visible):
        mismatches.append(
            CapacityMismatch(
                shelf_id=shelf.id,
                shelf_code=shelf.code,
                configured=configured,
                visible=len(visible),
            )
        )

    return OccupancyCounts(
        configured_capacity=configured,
        visible_capacity=len(visible),
        occupied_positions=occupied,
        available_positions=available,
        blocked_positions=blocked,
        retired_positions=retired,
        occupancy_rate=round(occupied / len(visible), 4) if visible else 0.0,
        capacity_mismatches=tuple(mismatches),
        conflicts=tuple(conflicts),
    )


def merge_counts(items: Sequence[OccupancyCounts]) -> OccupancyCounts:
    configured_values = [
        item.configured_capacity
        for item in items
        if item.configured_capacity is not None
    ]
    visible = sum(item.visible_capacity for item in items)
    occupied = sum(item.occupied_positions for item in items)
    return OccupancyCounts(
        configured_capacity=sum(configured_values) if configured_values else None,
        visible_capacity=visible,
        occupied_positions=occupied,
        available_positions=sum(item.available_positions for item in items),
        blocked_positions=sum(item.blocked_positions for item in items),
        retired_positions=sum(item.retired_positions for item in items),
        occupancy_rate=round(occupied / visible, 4) if visible else 0.0,
        unlocated_boxes=sum(item.unlocated_boxes for item in items),
        pending_confirmation_boxes=sum(
            item.pending_confirmation_boxes for item in items
        ),
        in_transit_boxes=sum(item.in_transit_boxes for item in items),
        capacity_mismatches=tuple(
            mismatch for item in items for mismatch in item.capacity_mismatches
        ),
        conflicts=tuple(conflict for item in items for conflict in item.conflicts),
    )
```

### 8.7 Paso 7 - Servicio de bloqueos

**Archivo:** `backend/src/judicial_archive/modules/locations/blocks.py` (NUEVO)

```python
from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import (
    ConflictError,
    InvalidParameterError,
    NotFoundError,
)
from judicial_archive.core.pagination import Page, PageParams
from judicial_archive.core.text import clean_optional_text
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.locations import schemas
from judicial_archive.modules.locations.models import (
    Position,
    PositionBlock,
    Shelf,
    Tray,
)
from judicial_archive.modules.locations.repositories import LocationsRepository
from judicial_archive.modules.users.models import User


def _block_snapshot(block: PositionBlock) -> dict[str, object]:
    return {
        "shelf_id": str(block.shelf_id),
        "start_position_id": str(block.start_position_id),
        "end_position_id": str(block.end_position_id),
        "first_position_number": block.first_position_number,
        "last_position_number": block.last_position_number,
        "reason": block.reason,
        "cancelled_at": block.cancelled_at.isoformat() if block.cancelled_at else None,
        "cancellation_reason": block.cancellation_reason,
    }


def _path_out(
    row: tuple[Position, Tray, Shelf, "Area"],
) -> schemas.PositionPathOut:
    position, tray, shelf, area = row
    return schemas.PositionPathOut(
        position_id=position.id,
        position_code=position.code,
        label=position.label,
        position_status=position.status,
        tray=schemas.TrayPathOut(id=tray.id, code=tray.code, name=tray.name),
        shelf=schemas.ShelfPathOut(id=shelf.id, code=shelf.code, name=shelf.name),
        area=schemas.AreaPathOut(id=area.id, code=area.code, name=area.name),
    )


def _sorted_positions(
    trays: Sequence[Tray],
    positions: Sequence[Position],
) -> list[Position]:
    tray_codes = {tray.id: tray.code for tray in trays}
    return sorted(
        positions,
        key=lambda position: (
            tray_codes[position.tray_id],
            position.code,
            str(position.id),
        ),
    )


async def _block_out(
    session: AsyncSession,
    block: PositionBlock,
) -> schemas.PositionBlockOut:
    paths = await LocationsRepository(session).list_position_paths(
        [block.start_position_id, block.end_position_id]
    )
    start = paths.get(block.start_position_id)
    end = paths.get(block.end_position_id)
    if start is None or end is None:
        raise NotFoundError("No fue posible resolver las posiciones del bloqueo.")
    return schemas.PositionBlockOut(
        id=block.id,
        shelf_id=block.shelf_id,
        start_position=_path_out(start),
        end_position=_path_out(end),
        first_position_number=block.first_position_number,
        last_position_number=block.last_position_number,
        reason=block.reason,
        notes=block.notes,
        blocked_by=block.blocked_by,
        cancelled_at=block.cancelled_at,
        cancelled_by=block.cancelled_by,
        cancellation_reason=block.cancellation_reason,
        created_at=block.created_at,
    )


async def create_block(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.PositionBlockCreate,
) -> schemas.PositionBlockOut:
    repo = LocationsRepository(session)
    shelf, trays, positions = await repo.get_shelf_structure_for_update(body.shelf_id)
    if shelf is None:
        raise NotFoundError("Anaquel no encontrado.")
    if shelf.version != body.expected_version:
        raise ConflictError(
            "El anaquel fue modificado por otra operacion; recargue y reintente.",
            details={"reason": "stale_version", "current_version": shelf.version},
        )
    if shelf.status != "ACTIVE":
        raise InvalidParameterError("No se puede bloquear un anaquel inactivo.")

    ordered = _sorted_positions(trays, positions)
    index_by_id = {position.id: index for index, position in enumerate(ordered)}
    if (
        body.start_position_id not in index_by_id
        or body.end_position_id not in index_by_id
    ):
        raise InvalidParameterError(
            "Las posiciones de inicio y fin deben pertenecer al anaquel indicado."
        )
    start_index = index_by_id[body.start_position_id]
    end_index = index_by_id[body.end_position_id]
    if start_index > end_index:
        raise InvalidParameterError(
            "La posicion inicial no puede ser posterior a la final."
        )

    first_number = start_index + 1
    last_number = end_index + 1
    if await repo.has_overlapping_block(shelf.id, first_number, last_number):
        raise ConflictError(
            "El rango se superpone con un bloqueo activo.",
            details={"reason": "blocked_range_conflict"},
        )

    occupied = await repo.occupied_position_ids(
        [position.id for position in ordered[start_index : end_index + 1]]
    )
    for position in ordered[start_index : end_index + 1]:
        if position.status == "RETIRED":
            raise ConflictError(
                f"La posicion {position.code} esta retirada.",
                details={"reason": "position_retired", "position_id": str(position.id)},
            )
        if position.status == "BLOCKED":
            raise ConflictError(
                f"La posicion {position.code} ya esta bloqueada.",
                details={"reason": "position_blocked", "position_id": str(position.id)},
            )
        if position.id in occupied:
            raise ConflictError(
                f"La posicion {position.code} esta ocupada.",
                details={
                    "reason": "position_occupied",
                    "position_id": str(position.id),
                },
            )

    block = PositionBlock(
        shelf_id=shelf.id,
        start_position_id=body.start_position_id,
        end_position_id=body.end_position_id,
        first_position_number=first_number,
        last_position_number=last_number,
        reason=body.reason.strip(),
        blocked_by=actor.id,
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    session.add(block)
    for position in ordered[start_index : end_index + 1]:
        position.status = "BLOCKED"
    await session.flush()

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="position_block.created",
        entity_type="position_block",
        entity_id=block.id,
        after=_block_snapshot(block),
        metadata={
            "shelf_id": str(shelf.id),
            "first_position_number": first_number,
            "last_position_number": last_number,
        },
    )
    await session.commit()
    await session.refresh(block)
    return await _block_out(session, block)


async def cancel_block(
    request: Request,
    session: AsyncSession,
    actor: User,
    block_id: UUID,
    body: schemas.PositionBlockCancel,
) -> schemas.PositionBlockOut:
    block = await session.scalar(
        select(PositionBlock).where(PositionBlock.id == block_id).with_for_update()
    )
    if block is None:
        raise NotFoundError("Bloqueo no encontrado.")
    if block.cancelled_at is not None:
        raise ConflictError(
            "El bloqueo ya fue cancelado.",
            details={"reason": "block_already_cancelled"},
        )

    repo = LocationsRepository(session)
    shelf, trays, positions = await repo.get_shelf_structure_for_update(block.shelf_id)
    if shelf is None:
        raise NotFoundError("Anaquel no encontrado.")
    if shelf.version != body.expected_version:
        raise ConflictError(
            "El anaquel fue modificado por otra operacion; recargue y reintente.",
            details={"reason": "stale_version", "current_version": shelf.version},
        )

    ordered = _sorted_positions(trays, positions)
    selected = ordered[block.first_position_number - 1 : block.last_position_number]
    occupied = await repo.occupied_position_ids([position.id for position in selected])
    for position in selected:
        if position.id in occupied:
            raise ConflictError(
                f"La posicion {position.code} esta ocupada; no se puede desbloquear.",
                details={
                    "reason": "position_occupied",
                    "position_id": str(position.id),
                },
            )
        if position.status == "BLOCKED":
            position.status = "AVAILABLE"

    before = _block_snapshot(block)
    block.cancelled_at = datetime.now(UTC)
    block.cancelled_by = actor.id
    block.cancellation_reason = body.reason.strip()
    await session.flush()

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="position_block.cancelled",
        entity_type="position_block",
        entity_id=block.id,
        before=before,
        after=_block_snapshot(block),
        metadata={"shelf_id": str(shelf.id)},
    )
    await session.commit()
    await session.refresh(block)
    return await _block_out(session, block)


async def list_blocks(
    session: AsyncSession,
    *,
    params: PageParams,
    area_id: UUID | None,
    shelf_id: UUID | None,
    active: bool | None,
) -> Page[schemas.PositionBlockOut]:
    repo = LocationsRepository(session)
    conditions = []
    if area_id:
        conditions.append(Shelf.area_id == area_id)
    if shelf_id:
        conditions.append(PositionBlock.shelf_id == shelf_id)
    if active is True:
        conditions.append(PositionBlock.cancelled_at.is_(None))
    elif active is False:
        conditions.append(PositionBlock.cancelled_at.is_not(None))

    base = (
        select(PositionBlock)
        .join(Shelf, Shelf.id == PositionBlock.shelf_id)
        .where(*conditions)
    )
    total = await session.scalar(select(func.count()).select_from(base.subquery()))
    rows = await session.scalars(
        base.order_by(
            PositionBlock.created_at.desc(),
            PositionBlock.id.desc(),
        )
        .offset(params.offset)
        .limit(params.limit)
    )
    items = [await _block_out(session, block) for block in rows.all()]
    return Page[schemas.PositionBlockOut].build(
        items, total=int(total or 0), params=params
    )
```

Agregar `func` a imports de SQLAlchemy en `blocks.py`. Agregar `Area` al import de modelos para la anotacion `_path_out`.

### 8.8 Paso 8 - Servicio de movimientos y ubicacion de cajas

**Archivo:** `backend/src/judicial_archive/modules/movements/services.py` (NUEVO)

```python
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from judicial_archive.core.enums import (
    CustodyStatus,
    LocationHistorySource,
    MovementStatus,
    MovementType,
    TransferMode,
)
from judicial_archive.core.errors import (
    ConflictError,
    ForbiddenError,
    InvalidParameterError,
    NotFoundError,
)
from judicial_archive.core.pagination import Page, PageParams
from judicial_archive.core.text import clean_optional_text
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.boxes.models import Box, BoxLocationHistory, BoxMovement
from judicial_archive.modules.boxes.repositories import BoxRepository
from judicial_archive.modules.boxes.schemas import (
    BoxLocationHistoryOut,
    BoxSummaryOut,
)
from judicial_archive.modules.locations import schemas as location_schemas
from judicial_archive.modules.locations.models import Area, Position, Shelf, Tray
from judicial_archive.modules.locations.occupancy import (
    classify_location_state,
    is_operable,
    precision_for,
)
from judicial_archive.modules.locations.repositories import LocationsRepository
from judicial_archive.modules.movements import schemas
from judicial_archive.modules.movements.repositories import MovementsRepository
from judicial_archive.modules.users.models import User


def _box_snapshot(box: Box, *, precision: str | None = None) -> dict[str, object]:
    return {
        "current_position_id": str(box.current_position_id)
        if box.current_position_id
        else None,
        "custody_status": box.custody_status,
        "location_precision": precision or box.location_precision,
        "version": box.version,
    }


def _movement_snapshot(movement: BoxMovement) -> dict[str, object]:
    return {
        "box_id": str(movement.box_id),
        "movement_type": movement.movement_type,
        "movement_status": movement.movement_status,
        "from_position_id": str(movement.from_position_id)
        if movement.from_position_id
        else None,
        "to_position_id": str(movement.to_position_id)
        if movement.to_position_id
        else None,
        "occurred_at": movement.occurred_at.isoformat(),
        "completed_at": movement.completed_at.isoformat()
        if movement.completed_at
        else None,
        "cancelled_at": movement.cancelled_at.isoformat()
        if movement.cancelled_at
        else None,
        "reason": movement.reason,
    }


def _history_out(history: BoxLocationHistory) -> BoxLocationHistoryOut:
    return BoxLocationHistoryOut(
        id=history.id,
        box_id=history.box_id,
        movement_id=history.movement_id,
        from_position_id=history.from_position_id,
        to_position_id=history.to_position_id,
        from_custody_status=history.from_custody_status,
        to_custody_status=history.to_custody_status,
        from_location_precision=history.from_location_precision,
        to_location_precision=history.to_location_precision,
        reason=history.reason,
        source=history.source,
        changed_at=history.changed_at,
        changed_by=history.changed_by,
        notes=history.notes,
    )


def _path_out(
    row: tuple[Position, Tray, Shelf, Area],
) -> location_schemas.PositionPathOut:
    position, tray, shelf, area = row
    return location_schemas.PositionPathOut(
        position_id=position.id,
        position_code=position.code,
        label=position.label,
        position_status=position.status,
        tray=location_schemas.TrayPathOut(
            id=tray.id,
            code=tray.code,
            name=tray.name,
        ),
        shelf=location_schemas.ShelfPathOut(
            id=shelf.id,
            code=shelf.code,
            name=shelf.name,
        ),
        area=location_schemas.AreaPathOut(
            id=area.id,
            code=area.code,
            name=area.name,
        ),
    )


def _box_summary(box: Box) -> BoxSummaryOut:
    return BoxSummaryOut(
        box_id=box.id,
        visible_number=box.visible_number,
        box_type=box.box_type,
        year=box.year,
        court_id=box.court_id,
        lifecycle_status=box.lifecycle_status,
        custody_status=box.custody_status,
        location_precision=box.location_precision,
        location_state=classify_location_state(box),
    )


async def _movement_out(
    session: AsyncSession,
    movement: BoxMovement,
) -> schemas.MovementOut:
    repo = LocationsRepository(session)
    ids = [
        position_id
        for position_id in (movement.from_position_id, movement.to_position_id)
        if position_id is not None
    ]
    paths = await repo.list_position_paths(ids)
    from_position = (
        _path_out(paths[movement.from_position_id])
        if movement.from_position_id and movement.from_position_id in paths
        else None
    )
    to_position = (
        _path_out(paths[movement.to_position_id])
        if movement.to_position_id and movement.to_position_id in paths
        else None
    )
    return schemas.MovementOut(
        id=movement.id,
        box_id=movement.box_id,
        movement_type=movement.movement_type,
        movement_status=movement.movement_status,
        from_position=from_position,
        to_position=to_position,
        occurred_at=movement.occurred_at,
        completed_at=movement.completed_at,
        cancelled_at=movement.cancelled_at,
        reason=movement.reason,
        performed_by=movement.performed_by,
        notes=movement.notes,
        version=movement.version,
    )


async def _box_location_detail(
    session: AsyncSession,
    box: Box,
) -> schemas.BoxLocationDetailOut:
    repo = LocationsRepository(session)
    movements = MovementsRepository(session)
    current_path = (
        await repo.get_position_path(box.current_position_id)
        if box.current_position_id
        else None
    )
    open_movement = await movements.get_open_for_box(box.id)
    last_movement = await movements.get_last_for_box(box.id)
    history_count = await BoxRepository(session).count_history(box.id)
    return schemas.BoxLocationDetailOut(
        box=_box_summary(box),
        current_position=_path_out(current_path) if current_path else None,
        open_movement=(
            await _movement_out(session, open_movement) if open_movement else None
        ),
        last_movement=(
            await _movement_out(session, last_movement) if last_movement else None
        ),
        history_count=history_count,
        operable=is_operable(box),
        version=box.version,
    )


async def _get_box_for_update(
    session: AsyncSession,
    box_id: UUID,
) -> Box:
    box = await BoxRepository(session).get_for_update(box_id)
    if box is None:
        raise NotFoundError("Caja no encontrada.")
    if box.lifecycle_status != "ACTIVE":
        raise ForbiddenError(
            "La caja no esta activa para operaciones de ubicacion.",
            details={
                "reason": "box_not_active",
                "lifecycle_status": box.lifecycle_status,
            },
        )
    return box


def _check_version(box: Box, expected_version: int) -> None:
    if box.version != expected_version:
        raise ConflictError(
            "La caja fue modificada por otra operacion; recargue y reintente.",
            details={
                "reason": "stale_version",
                "current_version": box.version,
            },
        )


async def _ensure_no_open_movement(
    session: AsyncSession,
    box_id: UUID,
) -> None:
    movement = await MovementsRepository(session).get_open_for_box(box_id)
    if movement is not None:
        raise ConflictError(
            "La caja ya tiene un movimiento abierto.",
            details={
                "reason": "open_movement_exists",
                "movement_id": str(movement.id),
            },
        )


async def _lock_positions(
    session: AsyncSession,
    *position_ids: UUID | None,
) -> dict[UUID, Position]:
    ids = [position_id for position_id in position_ids if position_id is not None]
    positions = await LocationsRepository(session).get_positions_for_update(ids)
    return {position.id: position for position in positions}


async def _validate_target_position(
    session: AsyncSession,
    position: Position,
) -> None:
    path = await LocationsRepository(session).get_position_path(position.id)
    if path is None:
        raise NotFoundError("Posicion no encontrada.")
    _, tray, shelf, area = path
    if tray.status != "ACTIVE":
        raise ConflictError(
            "La bandeja destino esta inactiva.",
            details={"reason": "tray_inactive", "tray_id": str(tray.id)},
        )
    if shelf.status != "ACTIVE":
        raise ConflictError(
            "El anaquel destino esta inactivo.",
            details={"reason": "shelf_inactive", "shelf_id": str(shelf.id)},
        )
    if area.status != "ACTIVE":
        raise ConflictError(
            "El area destino esta inactiva.",
            details={"reason": "area_inactive", "area_id": str(area.id)},
        )
    if position.status == "RETIRED":
        raise ConflictError(
            "La posicion destino esta retirada.",
            details={"reason": "position_retired", "position_id": str(position.id)},
        )
    if position.status == "BLOCKED":
        raise ConflictError(
            "La posicion destino esta bloqueada.",
            details={"reason": "position_blocked", "position_id": str(position.id)},
        )


async def _assert_position_free(
    session: AsyncSession,
    position_id: UUID,
) -> None:
    occupied = await LocationsRepository(session).get_box_at_position(position_id)
    if occupied is not None:
        raise ConflictError(
            "La posicion destino ya esta ocupada.",
            details={
                "reason": "position_occupied",
                "position_id": str(position_id),
                "box_id": str(occupied.id),
            },
        )


def _new_movement(
    *,
    box_id: UUID,
    movement_type: str,
    movement_status: str,
    from_position_id: UUID | None,
    to_position_id: UUID | None,
    reason: str,
    actor: User,
    notes: str | None,
) -> BoxMovement:
    now = datetime.now(UTC)
    return BoxMovement(
        box_id=box_id,
        movement_type=movement_type,
        movement_status=movement_status,
        from_position_id=from_position_id,
        to_position_id=to_position_id,
        occurred_at=now,
        completed_at=now if movement_status == MovementStatus.COMPLETED.value else None,
        cancelled_at=None,
        reason=reason,
        performed_by=actor.id,
        notes=notes,
    )


async def _add_history(
    session: AsyncSession,
    *,
    box: Box,
    movement_id: UUID | None,
    from_position_id: UUID | None,
    from_custody_status: str | None,
    from_location_precision: str | None,
    to_position_id: UUID | None,
    to_custody_status: str,
    reason: str,
    actor: User,
    notes: str | None,
    source: str = LocationHistorySource.API.value,
) -> BoxLocationHistory:
    history = BoxLocationHistory(
        box_id=box.id,
        movement_id=movement_id,
        from_position_id=from_position_id,
        to_position_id=to_position_id,
        from_custody_status=from_custody_status,
        to_custody_status=to_custody_status,
        from_location_precision=from_location_precision,
        to_location_precision=precision_for(to_custody_status, to_position_id),
        reason=reason,
        source=source,
        changed_at=datetime.now(UTC),
        changed_by=actor.id,
        notes=notes,
    )
    session.add(history)
    await session.flush()
    return history


def _apply_location(
    box: Box,
    *,
    position_id: UUID | None,
    custody_status: str,
) -> None:
    box.current_position_id = position_id
    box.custody_status = custody_status


async def _commit_or_conflict(session: AsyncSession) -> None:
    try:
        await session.commit()
    except StaleDataError as exc:
        await session.rollback()
        raise ConflictError(
            "La operacion compitio con otra modificacion; recargue y reintente.",
            details={"reason": "stale_version"},
        ) from exc
    except IntegrityError as exc:
        await session.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == "uq_boxes_current_position_occupied":
            raise ConflictError(
                "La posicion destino ya esta ocupada.",
                details={"reason": "position_occupied"},
            ) from exc
        if constraint == "uq_box_movements_open_box":
            raise ConflictError(
                "La caja ya tiene un movimiento abierto.",
                details={"reason": "open_movement_exists"},
            ) from exc
        if constraint == "ck_boxes_custody_position":
            raise ConflictError(
                "La transicion de custodia no es valida.",
                details={"reason": "invalid_transition"},
            ) from exc
        raise


async def assign_box(
    request: Request,
    session: AsyncSession,
    actor: User,
    box_id: UUID,
    body: schemas.AssignRequest,
) -> schemas.LocationMutationOut:
    box = await _get_box_for_update(session, box_id)
    _check_version(box, body.expected_version)
    if box.current_position_id is not None:
        raise ConflictError(
            "La caja ya tiene una posicion; use un traslado.",
            details={"reason": "box_already_located"},
        )
    if box.custody_status not in {
        CustodyStatus.UNKNOWN.value,
        CustodyStatus.MISSING.value,
    }:
        raise ConflictError(
            "La caja no puede asignarse desde su estado actual.",
            details={
                "reason": "invalid_transition",
                "custody_status": box.custody_status,
            },
        )
    await _ensure_no_open_movement(session, box.id)

    positions = await _lock_positions(session, body.position_id)
    target = positions.get(body.position_id)
    if target is None:
        raise NotFoundError("Posicion no encontrada.")
    await _validate_target_position(session, target)
    await _assert_position_free(session, target.id)

    custody = (
        CustodyStatus.IN_PLACE.value
        if body.confirmed
        else CustodyStatus.PENDING_VERIFICATION.value
    )
    before = _box_snapshot(box)
    from_custody = box.custody_status
    from_precision = box.location_precision
    movement = _new_movement(
        box_id=box.id,
        movement_type=MovementType.ASSIGN.value,
        movement_status=MovementStatus.COMPLETED.value,
        from_position_id=None,
        to_position_id=target.id,
        reason=body.reason.strip(),
        actor=actor,
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    session.add(movement)
    await session.flush()

    _apply_location(box, position_id=target.id, custody_status=custody)
    history = await _add_history(
        session,
        box=box,
        movement_id=movement.id,
        from_position_id=None,
        from_custody_status=from_custody,
        from_location_precision=from_precision,
        to_position_id=target.id,
        to_custody_status=custody,
        reason=body.reason.strip(),
        actor=actor,
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    after = _box_snapshot(
        box,
        precision=precision_for(custody, target.id),
    )
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="box.location_assigned",
        entity_type="box",
        entity_id=box.id,
        before=before,
        after=after,
        metadata={
            "movement_id": str(movement.id),
            "history_id": str(history.id),
            "position_id": str(target.id),
            "confirmed": body.confirmed,
        },
    )
    await _commit_or_conflict(session)
    await session.refresh(box)
    await session.refresh(movement)
    return schemas.LocationMutationOut(
        box=await _box_location_detail(session, box),
        movement=await _movement_out(session, movement),
        history=_history_out(history),
    )


async def unassign_box(
    request: Request,
    session: AsyncSession,
    actor: User,
    box_id: UUID,
    body: schemas.UnassignRequest,
) -> schemas.LocationMutationOut:
    box = await _get_box_for_update(session, box_id)
    _check_version(box, body.expected_version)
    if box.current_position_id is None:
        raise ConflictError(
            "La caja no tiene ubicacion para retirar.",
            details={"reason": "box_without_location"},
        )
    if box.custody_status not in {
        CustodyStatus.IN_PLACE.value,
        CustodyStatus.PENDING_VERIFICATION.value,
    }:
        raise ConflictError(
            "La caja no puede desasignarse desde su estado actual.",
            details={
                "reason": "invalid_transition",
                "custody_status": box.custody_status,
            },
        )
    await _ensure_no_open_movement(session, box.id)

    from_position_id = box.current_position_id
    from_custody = box.custody_status
    from_precision = box.location_precision
    await _lock_positions(session, from_position_id)

    before = _box_snapshot(box)
    movement = _new_movement(
        box_id=box.id,
        movement_type=MovementType.UNASSIGN.value,
        movement_status=MovementStatus.COMPLETED.value,
        from_position_id=from_position_id,
        to_position_id=None,
        reason=body.reason.strip(),
        actor=actor,
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    session.add(movement)
    await session.flush()

    _apply_location(box, position_id=None, custody_status=CustodyStatus.UNKNOWN.value)
    history = await _add_history(
        session,
        box=box,
        movement_id=movement.id,
        from_position_id=from_position_id,
        from_custody_status=from_custody,
        from_location_precision=from_precision,
        to_position_id=None,
        to_custody_status=CustodyStatus.UNKNOWN.value,
        reason=body.reason.strip(),
        actor=actor,
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    after = _box_snapshot(box, precision="UNKNOWN")
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="box.location_unassigned",
        entity_type="box",
        entity_id=box.id,
        before=before,
        after=after,
        metadata={
            "movement_id": str(movement.id),
            "history_id": str(history.id),
            "from_position_id": str(from_position_id),
        },
    )
    await _commit_or_conflict(session)
    await session.refresh(box)
    await session.refresh(movement)
    return schemas.LocationMutationOut(
        box=await _box_location_detail(session, box),
        movement=await _movement_out(session, movement),
        history=_history_out(history),
    )


async def transfer_box(
    request: Request,
    session: AsyncSession,
    actor: User,
    box_id: UUID,
    body: schemas.TransferRequest,
) -> schemas.LocationMutationOut:
    box = await _get_box_for_update(session, box_id)
    _check_version(box, body.expected_version)
    if box.current_position_id is None:
        raise ConflictError(
            "La caja no tiene ubicacion de origen.",
            details={"reason": "box_without_location"},
        )
    if box.custody_status not in {
        CustodyStatus.IN_PLACE.value,
        CustodyStatus.PENDING_VERIFICATION.value,
    }:
        raise ConflictError(
            "La caja no puede trasladarse desde su estado actual.",
            details={
                "reason": "invalid_transition",
                "custody_status": box.custody_status,
            },
        )
    if body.to_position_id == box.current_position_id:
        raise InvalidParameterError(
            "La posicion destino debe ser distinta de la posicion actual."
        )
    await _ensure_no_open_movement(session, box.id)

    from_position_id = box.current_position_id
    from_custody = box.custody_status
    from_precision = box.location_precision
    positions = await _lock_positions(session, from_position_id, body.to_position_id)
    target = positions.get(body.to_position_id)
    if target is None:
        raise NotFoundError("Posicion destino no encontrada.")
    await _validate_target_position(session, target)
    await _assert_position_free(session, target.id)

    before = _box_snapshot(box)
    if body.mode == TransferMode.IN_TRANSIT:
        movement = _new_movement(
            box_id=box.id,
            movement_type=MovementType.TRANSFER.value,
            movement_status=MovementStatus.IN_TRANSIT.value,
            from_position_id=from_position_id,
            to_position_id=target.id,
            reason=body.reason.strip(),
            actor=actor,
            notes=clean_optional_text(body.notes, max_length=1000),
        )
        session.add(movement)
        await session.flush()
        _apply_location(
            box,
            position_id=None,
            custody_status=CustodyStatus.IN_TRANSIT.value,
        )
        history = await _add_history(
            session,
            box=box,
            movement_id=movement.id,
            from_position_id=from_position_id,
            from_custody_status=from_custody,
            from_location_precision=from_precision,
            to_position_id=None,
            to_custody_status=CustodyStatus.IN_TRANSIT.value,
            reason=body.reason.strip(),
            actor=actor,
            notes=clean_optional_text(body.notes, max_length=1000),
        )
        after = _box_snapshot(box, precision="UNKNOWN")
    else:
        custody = (
            CustodyStatus.IN_PLACE.value
            if body.confirmed
            else CustodyStatus.PENDING_VERIFICATION.value
        )
        movement = _new_movement(
            box_id=box.id,
            movement_type=MovementType.TRANSFER.value,
            movement_status=MovementStatus.COMPLETED.value,
            from_position_id=from_position_id,
            to_position_id=target.id,
            reason=body.reason.strip(),
            actor=actor,
            notes=clean_optional_text(body.notes, max_length=1000),
        )
        session.add(movement)
        await session.flush()
        _apply_location(box, position_id=target.id, custody_status=custody)
        history = await _add_history(
            session,
            box=box,
            movement_id=movement.id,
            from_position_id=from_position_id,
            from_custody_status=from_custody,
            from_location_precision=from_precision,
            to_position_id=target.id,
            to_custody_status=custody,
            reason=body.reason.strip(),
            actor=actor,
            notes=clean_optional_text(body.notes, max_length=1000),
        )
        after = _box_snapshot(box, precision=precision_for(custody, target.id))

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="box.location_transferred",
        entity_type="box",
        entity_id=box.id,
        before=before,
        after=after,
        metadata={
            "movement_id": str(movement.id),
            "history_id": str(history.id),
            "from_position_id": str(from_position_id),
            "to_position_id": str(target.id),
            "mode": body.mode.value,
            "confirmed": body.confirmed,
        },
    )
    await _commit_or_conflict(session)
    await session.refresh(box)
    await session.refresh(movement)
    return schemas.LocationMutationOut(
        box=await _box_location_detail(session, box),
        movement=await _movement_out(session, movement),
        history=_history_out(history),
    )


async def confirm_location(
    request: Request,
    session: AsyncSession,
    actor: User,
    box_id: UUID,
    body: schemas.ConfirmRequest,
) -> schemas.LocationMutationOut:
    box = await _get_box_for_update(session, box_id)
    _check_version(box, body.expected_version)
    if box.current_position_id is None:
        raise ConflictError(
            "La caja no tiene posicion para confirmar.",
            details={"reason": "box_without_location"},
        )
    if box.custody_status != CustodyStatus.PENDING_VERIFICATION.value:
        raise ConflictError(
            "La caja no esta pendiente de confirmacion.",
            details={
                "reason": "invalid_transition",
                "custody_status": box.custody_status,
            },
        )
    position_id = box.current_position_id
    positions = await _lock_positions(session, position_id)
    if position_id not in positions:
        raise NotFoundError("Posicion no encontrada.")

    before = _box_snapshot(box)
    _apply_location(
        box,
        position_id=position_id,
        custody_status=CustodyStatus.IN_PLACE.value,
    )
    history = await _add_history(
        session,
        box=box,
        movement_id=None,
        from_position_id=position_id,
        from_custody_status=CustodyStatus.PENDING_VERIFICATION.value,
        from_location_precision="PENDING",
        to_position_id=position_id,
        to_custody_status=CustodyStatus.IN_PLACE.value,
        reason=body.reason.strip(),
        actor=actor,
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    after = _box_snapshot(box, precision="CONFIRMED")
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="box.location_confirmed",
        entity_type="box",
        entity_id=box.id,
        before=before,
        after=after,
        metadata={
            "history_id": str(history.id),
            "position_id": str(position_id),
        },
    )
    await _commit_or_conflict(session)
    await session.refresh(box)
    return schemas.LocationMutationOut(
        box=await _box_location_detail(session, box),
        movement=None,
        history=_history_out(history),
    )


async def complete_movement(
    request: Request,
    session: AsyncSession,
    actor: User,
    movement_id: UUID,
    body: schemas.CompleteMovementRequest,
) -> schemas.LocationMutationOut:
    movement = await MovementsRepository(session).get_for_update(movement_id)
    if movement is None:
        raise NotFoundError("Movimiento no encontrado.")
    if movement.movement_type != MovementType.TRANSFER.value:
        raise ConflictError(
            "Solo los traslados pueden completarse en B6.",
            details={"reason": "unsupported_movement_type"},
        )
    if movement.movement_status != MovementStatus.IN_TRANSIT.value:
        raise ConflictError(
            "El movimiento no esta en transito.",
            details={
                "reason": "movement_not_in_transit",
                "movement_status": movement.movement_status,
            },
        )

    box = await _get_box_for_update(session, movement.box_id)
    _check_version(box, body.expected_version)
    if box.custody_status != CustodyStatus.IN_TRANSIT.value:
        raise ConflictError(
            "La caja no esta en transito.",
            details={
                "reason": "invalid_transition",
                "custody_status": box.custody_status,
            },
        )
    if movement.to_position_id is None:
        raise ConflictError(
            "El movimiento no tiene posicion destino.",
            details={"reason": "movement_without_target"},
        )

    positions = await _lock_positions(session, movement.to_position_id)
    target = positions.get(movement.to_position_id)
    if target is None:
        raise NotFoundError("Posicion destino no encontrada.")
    await _validate_target_position(session, target)
    await _assert_position_free(session, target.id)

    custody = (
        CustodyStatus.IN_PLACE.value
        if body.confirmed
        else CustodyStatus.PENDING_VERIFICATION.value
    )
    before = _box_snapshot(box)
    before_movement = _movement_snapshot(movement)
    movement.movement_status = MovementStatus.COMPLETED.value
    movement.completed_at = datetime.now(UTC)
    _apply_location(box, position_id=target.id, custody_status=custody)
    history = await _add_history(
        session,
        box=box,
        movement_id=movement.id,
        from_position_id=None,
        from_custody_status=CustodyStatus.IN_TRANSIT.value,
        from_location_precision="UNKNOWN",
        to_position_id=target.id,
        to_custody_status=custody,
        reason=body.reason.strip(),
        actor=actor,
        notes=clean_optional_text(body.notes, max_length=1000),
    )
    after = _box_snapshot(box, precision=precision_for(custody, target.id))
    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="box.location_transfer_completed",
        entity_type="box",
        entity_id=box.id,
        before=before,
        after=after,
        metadata={
            "movement_id": str(movement.id),
            "movement_before": before_movement,
            "history_id": str(history.id),
            "to_position_id": str(target.id),
            "confirmed": body.confirmed,
        },
    )
    await _commit_or_conflict(session)
    await session.refresh(box)
    await session.refresh(movement)
    return schemas.LocationMutationOut(
        box=await _box_location_detail(session, box),
        movement=await _movement_out(session, movement),
        history=_history_out(history),
    )


async def cancel_movement(
    request: Request,
    session: AsyncSession,
    actor: User,
    movement_id: UUID,
    body: schemas.CancelMovementRequest,
) -> schemas.LocationMutationOut:
    movement = await MovementsRepository(session).get_for_update(movement_id)
    if movement is None:
        raise NotFoundError("Movimiento no encontrado.")
    if movement.movement_type != MovementType.TRANSFER.value:
        raise ConflictError(
            "Solo los traslados pueden cancelarse en B6.",
            details={"reason": "unsupported_movement_type"},
        )
    if movement.movement_status != MovementStatus.IN_TRANSIT.value:
        raise ConflictError(
            "El movimiento no esta en transito.",
            details={
                "reason": "movement_not_in_transit",
                "movement_status": movement.movement_status,
            },
        )

    box = await _get_box_for_update(session, movement.box_id)
    _check_version(box, body.expected_version)
    if box.custody_status != CustodyStatus.IN_TRANSIT.value:
        raise ConflictError(
            "La caja no esta en transito.",
            details={
                "reason": "invalid_transition",
                "custody_status": box.custody_status,
            },
        )

    history_origin = await BoxRepository(session).get_last_history_for_movement(
        movement.id
    )
    if history_origin is None:
        raise ConflictError(
            "No existe historial de origen para restaurar el traslado.",
            details={"reason": "movement_without_origin_history"},
        )

    origin_position_id = history_origin.from_position_id
    origin_custody = history_origin.from_custody_status or CustodyStatus.UNKNOWN.value
    origin_precision = history_origin.from_location_precision or "UNKNOWN"
    if origin_position_id is not None:
        positions = await _lock_positions(session, origin_position_id)
        origin = positions.get(origin_position_id)
        if origin is None:
            raise NotFoundError("Posicion de origen no encontrada.")
        occupied = await LocationsRepository(session).get_box_at_position(
            origin_position_id
        )
        if occupied is not None and occupied.id != box.id:
            raise ConflictError(
                "La posicion de origen fue ocupada durante el transito.",
                details={
                    "reason": "origin_occupied",
                    "position_id": str(origin_position_id),
                    "box_id": str(occupied.id),
                },
            )
        if origin.status != "AVAILABLE":
            raise ConflictError(
                "La posicion de origen no esta disponible.",
                details={
                    "reason": "origin_unavailable",
                    "position_id": str(origin_position_id),
                    "position_status": origin.status,
                },
            )

    before = _box_snapshot(box)
    before_movement = _movement_snapshot(movement)
    movement.movement_status = MovementStatus.CANCELLED.value
    movement.cancelled_at = datetime.now(UTC)

    if origin_position_id is not None:
        _apply_location(
            box,
            position_id=origin_position_id,
            custody_status=origin_custody,
        )
        history = await _add_history(
            session,
            box=box,
            movement_id=movement.id,
            from_position_id=None,
            from_custody_status=CustodyStatus.IN_TRANSIT.value,
            from_location_precision="UNKNOWN",
            to_position_id=origin_position_id,
            to_custody_status=origin_custody,
            reason=body.reason.strip(),
            actor=actor,
            notes=clean_optional_text(body.notes, max_length=1000),
        )
        after = _box_snapshot(box, precision=origin_precision)
    else:
        _apply_location(
            box,
            position_id=None,
            custody_status=CustodyStatus.UNKNOWN.value,
        )
        history = await _add_history(
            session,
            box=box,
            movement_id=movement.id,
            from_position_id=None,
            from_custody_status=CustodyStatus.IN_TRANSIT.value,
            from_location_precision="UNKNOWN",
            to_position_id=None,
            to_custody_status=CustodyStatus.UNKNOWN.value,
            reason=body.reason.strip(),
            actor=actor,
            notes=clean_optional_text(body.notes, max_length=1000),
        )
        after = _box_snapshot(box, precision="UNKNOWN")

    await record_audit_event(
        session,
        request=request,
        actor=actor,
        action="box.location_transfer_cancelled",
        entity_type="box",
        entity_id=box.id,
        before=before,
        after=after,
        metadata={
            "movement_id": str(movement.id),
            "movement_before": before_movement,
            "history_id": str(history.id),
            "restored_position_id": str(origin_position_id)
            if origin_position_id
            else None,
        },
    )
    await _commit_or_conflict(session)
    await session.refresh(box)
    await session.refresh(movement)
    return schemas.LocationMutationOut(
        box=await _box_location_detail(session, box),
        movement=await _movement_out(session, movement),
        history=_history_out(history),
    )


async def get_box_location(
    session: AsyncSession,
    box_id: UUID,
) -> schemas.BoxLocationDetailOut:
    box = await BoxRepository(session).get(box_id)
    if box is None:
        raise NotFoundError("Caja no encontrada.")
    return await _box_location_detail(session, box)


async def list_box_history(
    session: AsyncSession,
    *,
    params: PageParams,
    box_id: UUID,
    from_date: datetime | None,
    to_date: datetime | None,
    source: str | None,
) -> Page[BoxLocationHistoryOut]:
    box = await BoxRepository(session).get(box_id)
    if box is None:
        raise NotFoundError("Caja no encontrada.")
    rows, total = await BoxRepository(session).list_history(
        box_id,
        from_date=from_date,
        to_date=to_date,
        source=source,
        offset=params.offset,
        limit=params.limit,
    )
    items = [_history_out(row) for row in rows]
    return Page[BoxLocationHistoryOut].build(items, total=total, params=params)


async def list_movements(
    session: AsyncSession,
    *,
    params: PageParams,
    box_id: UUID | None,
    movement_type: str | None,
    movement_status: str | None,
    from_date: datetime | None,
    to_date: datetime | None,
) -> Page[schemas.MovementOut]:
    rows, total = await MovementsRepository(session).list(
        box_id=box_id,
        movement_type=movement_type,
        movement_status=movement_status,
        from_date=from_date,
        to_date=to_date,
        offset=params.offset,
        limit=params.limit,
    )
    items = [await _movement_out(session, row) for row in rows]
    return Page[schemas.MovementOut].build(items, total=total, params=params)


async def get_movement(
    session: AsyncSession,
    movement_id: UUID,
) -> schemas.MovementOut:
    movement = await MovementsRepository(session).get(movement_id)
    if movement is None:
        raise NotFoundError("Movimiento no encontrado.")
    return await _movement_out(session, movement)
```

**Puntos criticos de este servicio:**

- No asignar `box.location_precision`; es columna calculada.
- `_commit_or_conflict` traduce `StaleDataError` y violaciones unicas conocidas.
- `assign_box` y `transfer_box` validan la jerarquia fisica activa.
- `complete_movement` y `cancel_movement` restauran custodia y precision desde el historial, no desde supuestos.
- `cancel_movement` falla con `origin_occupied` si otro proceso tomo la posicion de origen durante el transito. La resolucion es manual y auditada, no automatica.

### 8.9 Paso 9 - Servicios de ocupacion, plano, escaneo y reportes

**Archivo:** `backend/src/judicial_archive/modules/locations/services.py`

Agregar imports:

```python
from dataclasses import replace
from datetime import UTC, datetime
from sqlalchemy import func, select

from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.boxes.repositories import BoxRepository
from judicial_archive.modules.boxes.schemas import BoxSummaryOut
from judicial_archive.modules.locations import occupancy
from judicial_archive.modules.locations.models import Area
from judicial_archive.modules.movements.repositories import MovementsRepository
```

Agregar helpers y servicios al final del archivo:

```python
def _path_out(
    row: tuple[Position, Tray, Shelf, Area],
) -> schemas.PositionPathOut:
    position, tray, shelf, area = row
    return schemas.PositionPathOut(
        position_id=position.id,
        position_code=position.code,
        label=position.label,
        position_status=position.status,
        tray=schemas.TrayPathOut(id=tray.id, code=tray.code, name=tray.name),
        shelf=schemas.ShelfPathOut(id=shelf.id, code=shelf.code, name=shelf.name),
        area=schemas.AreaPathOut(id=area.id, code=area.code, name=area.name),
    )


def _box_summary(box: Box) -> BoxSummaryOut:
    return BoxSummaryOut(
        box_id=box.id,
        visible_number=box.visible_number,
        box_type=box.box_type,
        year=box.year,
        court_id=box.court_id,
        lifecycle_status=box.lifecycle_status,
        custody_status=box.custody_status,
        location_precision=box.location_precision,
        location_state=occupancy.classify_location_state(box),
    )


def _summary_out(
    scope: str,
    scope_id: UUID | None,
    counts: occupancy.OccupancyCounts,
) -> schemas.OccupancySummaryOut:
    return schemas.OccupancySummaryOut(
        scope=scope,
        scope_id=scope_id,
        configured_capacity=counts.configured_capacity,
        visible_capacity=counts.visible_capacity,
        occupied_positions=counts.occupied_positions,
        available_positions=counts.available_positions,
        blocked_positions=counts.blocked_positions,
        retired_positions=counts.retired_positions,
        occupancy_rate=counts.occupancy_rate,
        unlocated_boxes=counts.unlocated_boxes,
        pending_confirmation_boxes=counts.pending_confirmation_boxes,
        in_transit_boxes=counts.in_transit_boxes,
        capacity_matches_configuration=counts.capacity_matches_configuration,
        capacity_mismatches=[
            schemas.CapacityMismatchOut(
                shelf_id=mismatch.shelf_id,
                shelf_code=mismatch.shelf_code,
                configured=mismatch.configured,
                visible=mismatch.visible,
                delta=mismatch.delta,
            )
            for mismatch in counts.capacity_mismatches
        ],
        conflicts=list(counts.conflicts),
    )


def _boxes_by_position(boxes: Sequence[Box]) -> dict[UUID, Box]:
    return {
        box.current_position_id: box
        for box in boxes
        if box.current_position_id is not None
    }


def _tray_counts(
    positions: Sequence[Position],
    boxes_by_position: dict[UUID, Box],
) -> occupancy.OccupancyCounts:
    visible = [position for position in positions if position.status != "RETIRED"]
    retired = len(positions) - len(visible)
    blocked = sum(1 for position in visible if position.status == "BLOCKED")
    occupied = sum(
        1
        for position in visible
        if position.id in boxes_by_position
        and boxes_by_position[position.id].custody_status
        in occupancy.ACTIVE_LOCATION_CUSTODY_STATUSES
    )
    available = max(0, len(visible) - occupied - blocked)
    return occupancy.OccupancyCounts(
        configured_capacity=None,
        visible_capacity=len(visible),
        occupied_positions=occupied,
        available_positions=available,
        blocked_positions=blocked,
        retired_positions=retired,
        occupancy_rate=round(occupied / len(visible), 4) if visible else 0.0,
    )


async def _location_totals(
    session: AsyncSession,
) -> tuple[int, int, int]:
    unlocated = await session.scalar(
        select(func.count())
        .select_from(Box)
        .where(
            Box.current_position_id.is_(None),
            Box.custody_status.in_(["UNKNOWN", "MISSING"]),
        )
    )
    pending = await session.scalar(
        select(func.count())
        .select_from(Box)
        .where(Box.custody_status == "PENDING_VERIFICATION")
    )
    in_transit = await session.scalar(
        select(func.count()).select_from(Box).where(Box.custody_status == "IN_TRANSIT")
    )
    return int(unlocated or 0), int(pending or 0), int(in_transit or 0)


async def get_occupancy(
    session: AsyncSession,
    *,
    area_id: UUID | None,
    shelf_id: UUID | None,
    tray_id: UUID | None,
) -> schemas.OccupancySummaryOut:
    repo = LocationsRepository(session)
    scope = "GLOBAL"
    scope_id: UUID | None = None

    if tray_id is not None:
        tray = await repo.get_tray(tray_id)
        if tray is None:
            raise NotFoundError("Bandeja no encontrada.")
        positions = await repo.list_positions_for_scope(
            area_id=None,
            shelf_id=tray.shelf_id,
            tray_id=tray.id,
        )
        boxes = await repo.list_boxes_for_positions(
            [position.id for position in positions]
        )
        counts = _tray_counts(positions, _boxes_by_position(boxes))
        scope = "TRAY"
        scope_id = tray.id
    elif shelf_id is not None:
        shelf = await repo.get_shelf(shelf_id)
        if shelf is None:
            raise NotFoundError("Anaquel no encontrado.")
        positions = await repo.list_positions_for_scope(
            area_id=None,
            shelf_id=shelf.id,
            tray_id=None,
        )
        boxes = await repo.list_boxes_for_positions(
            [position.id for position in positions]
        )
        counts = occupancy.compute_shelf_occupancy(
            shelf,
            positions,
            _boxes_by_position(boxes),
        )
        scope = "SHELF"
        scope_id = shelf.id
    else:
        shelves = await repo.list_shelves_for_scope(
            area_id=area_id,
            shelf_id=None,
        )
        trays = await repo.list_trays_for_scope(
            area_id=area_id,
            shelf_id=None,
            tray_id=None,
        )
        tray_to_shelf = {tray.id: tray.shelf_id for tray in trays}
        positions = await repo.list_positions_for_scope(
            area_id=area_id,
            shelf_id=None,
            tray_id=None,
        )
        boxes = await repo.list_boxes_for_positions(
            [position.id for position in positions]
        )
        boxes_by_position = _boxes_by_position(boxes)
        counts_by_shelf = []
        for shelf in shelves:
            shelf_positions = [
                position
                for position in positions
                if tray_to_shelf.get(position.tray_id) == shelf.id
            ]
            counts_by_shelf.append(
                occupancy.compute_shelf_occupancy(
                    shelf,
                    shelf_positions,
                    boxes_by_position,
                )
            )
        counts = occupancy.merge_counts(counts_by_shelf)
        scope = "AREA" if area_id is not None else "GLOBAL"
        scope_id = area_id

    unlocated, pending, in_transit = await _location_totals(session)
    counts = replace(
        counts,
        unlocated_boxes=unlocated,
        pending_confirmation_boxes=pending,
        in_transit_boxes=in_transit,
    )
    return _summary_out(scope, scope_id, counts)


async def list_position_occupancy(
    session: AsyncSession,
    *,
    params: PageParams,
    area_id: UUID | None,
    shelf_id: UUID | None,
    tray_id: UUID | None,
    state: str | None,
    q: str | None,
) -> Page[schemas.PositionOccupancyOut]:
    rows, total = await LocationsRepository(session).list_position_occupancy(
        area_id=area_id,
        shelf_id=shelf_id,
        tray_id=tray_id,
        state=state,
        q=q,
        offset=params.offset,
        limit=params.limit,
    )
    items = []
    for position, tray, shelf, area, box in rows:
        items.append(
            schemas.PositionOccupancyOut(
                position=_path_out((position, tray, shelf, area)),
                state=occupancy.position_occupancy_state(position, box),
                box=_box_summary(box) if box is not None else None,
                block_id=None,
            )
        )
    return Page[schemas.PositionOccupancyOut].build(
        items,
        total=total,
        params=params,
    )


async def list_unlocated_boxes(
    session: AsyncSession,
    *,
    params: PageParams,
    state: str | None,
    q: str | None,
) -> Page[schemas.UnlocatedBoxOut]:
    rows, total = await BoxRepository(session).list_unlocated(
        state=state,
        q=q,
        offset=params.offset,
        limit=params.limit,
    )
    movements = MovementsRepository(session)
    items = []
    for box in rows:
        last = await movements.get_last_for_box(box.id)
        items.append(
            schemas.UnlocatedBoxOut(
                box=_box_summary(box),
                location_state=occupancy.classify_location_state(box),
                last_movement_at=last.occurred_at if last is not None else None,
            )
        )
    return Page[schemas.UnlocatedBoxOut].build(items, total=total, params=params)


async def get_location_plan(
    session: AsyncSession,
    *,
    area_id: UUID | None,
    shelf_id: UUID | None,
    include_positions: bool,
) -> schemas.LocationPlanOut:
    repo = LocationsRepository(session)
    area: Area | None = None
    if area_id is not None:
        area = await repo.get_area(area_id)
        if area is None:
            raise NotFoundError("Area no encontrada.")
    if shelf_id is not None:
        shelf = await repo.get_shelf(shelf_id)
        if shelf is None:
            raise NotFoundError("Anaquel no encontrado.")
        if area is not None and shelf.area_id != area.id:
            raise InvalidParameterError("El anaquel no pertenece al area indicada.")

    shelves = await repo.list_shelves_for_scope(area_id=area_id, shelf_id=shelf_id)
    area_cache: dict[UUID, Area] = {}
    if area is not None:
        area_cache[area.id] = area
    for shelf_row in shelves:
        if shelf_row.area_id not in area_cache:
            area_row = await repo.get_area(shelf_row.area_id)
            if area_row is not None:
                area_cache[area_row.id] = area_row
    trays = await repo.list_trays_for_scope(
        area_id=area_id,
        shelf_id=shelf_id,
        tray_id=None,
    )
    positions = await repo.list_positions_for_scope(
        area_id=area_id,
        shelf_id=shelf_id,
        tray_id=None,
    )
    if include_positions and len(positions) > 5000:
        raise InvalidParameterError(
            "El plano solicitado supera el maximo de 5000 posiciones.",
            details={"max_positions": 5000, "requested": len(positions)},
        )
    boxes = await repo.list_boxes_for_positions([position.id for position in positions])
    boxes_by_position = _boxes_by_position(boxes)
    tray_by_id = {tray.id: tray for tray in trays}
    trays_by_shelf: dict[UUID, list[Tray]] = defaultdict(list)
    for tray in trays:
        trays_by_shelf[tray.shelf_id].append(tray)
    positions_by_tray: dict[UUID, list[Position]] = defaultdict(list)
    for position in positions:
        positions_by_tray[position.tray_id].append(position)

    plan_shelves = []
    counts_by_shelf = []
    for shelf in shelves:
        shelf_positions = [
            position
            for position in positions
            if tray_by_id.get(position.tray_id, None) is not None
            and tray_by_id[position.tray_id].shelf_id == shelf.id
        ]
        counts = occupancy.compute_shelf_occupancy(
            shelf,
            shelf_positions,
            boxes_by_position,
        )
        counts_by_shelf.append(counts)
        plan_trays = []
        for tray in sorted(
            trays_by_shelf.get(shelf.id, []), key=lambda item: item.code
        ):
            tray_positions = positions_by_tray.get(tray.id, [])
            tray_counts = _tray_counts(tray_positions, boxes_by_position)
            plan_positions = None
            if include_positions:
                plan_positions = []
                for position in sorted(tray_positions, key=lambda item: item.code):
                    box = boxes_by_position.get(position.id)
                    path_area = area_cache.get(shelf.area_id)
                    if path_area is None:
                        continue
                    path = (position, tray, shelf, path_area)
                    plan_positions.append(
                        schemas.LocationPlanPositionOut(
                            position=_path_out(path),
                            state=occupancy.position_occupancy_state(position, box),
                            box=_box_summary(box) if box is not None else None,
                            block_id=None,
                        )
                    )
            plan_trays.append(
                schemas.LocationPlanTrayOut(
                    tray=schemas.TrayPathOut(
                        id=tray.id,
                        code=tray.code,
                        name=tray.name,
                    ),
                    visible_capacity=tray_counts.visible_capacity,
                    occupied_positions=tray_counts.occupied_positions,
                    positions=plan_positions,
                )
            )
        plan_shelves.append(
            schemas.LocationPlanShelfOut(
                shelf=schemas.ShelfPathOut(
                    id=shelf.id,
                    code=shelf.code,
                    name=shelf.name,
                ),
                configured_capacity=shelf.capacity_positions,
                visible_capacity=counts.visible_capacity,
                occupied_positions=counts.occupied_positions,
                available_positions=counts.available_positions,
                blocked_positions=counts.blocked_positions,
                trays=plan_trays,
            )
        )

    counts = occupancy.merge_counts(counts_by_shelf)
    unlocated, pending, in_transit = await _location_totals(session)
    counts = replace(
        counts,
        unlocated_boxes=unlocated,
        pending_confirmation_boxes=pending,
        in_transit_boxes=in_transit,
    )
    area_out = (
        schemas.AreaPathOut(id=area.id, code=area.code, name=area.name)
        if area is not None
        else None
    )
    return schemas.LocationPlanOut(
        area=area_out,
        shelves=plan_shelves,
        summary=_summary_out(
            "SHELF" if shelf_id is not None else ("AREA" if area_id else "GLOBAL"),
            shelf_id or area_id,
            counts,
        ),
    )


async def scan(
    session: AsyncSession,
    *,
    box_number: str | None,
    position_id: UUID | None,
) -> schemas.ScanResponse:
    if (box_number is None) == (position_id is None):
        raise InvalidParameterError(
            "Debe indicar exactamente box_number o position_id."
        )
    repo = LocationsRepository(session)

    if box_number is not None:
        cleaned = box_number.strip()
        if not cleaned:
            raise InvalidParameterError("El numero de caja no puede estar vacio.")
        box = await BoxRepository(session).get_by_visible_number(cleaned)
        if box is None:
            return schemas.ScanResponse(
                kind="UNREGISTERED_BOX",
                box_number=cleaned,
                operable=False,
                message="Caja no registrada en el sistema.",
            )
        current_path = (
            await repo.get_position_path(box.current_position_id)
            if box.current_position_id
            else None
        )
        state = occupancy.classify_location_state(box)
        messages = {
            "CONFIRMED": "Caja ubicada y confirmada.",
            "PENDING_CONFIRMATION": "Caja ubicada, pendiente de confirmacion.",
            "IN_RECONCILIATION": "Caja en conciliacion.",
            "ON_LOAN": "Caja prestada; no esta en su posicion habitual.",
            "IN_TRANSIT": "Caja en transito.",
            "MISSING": "Caja marcada como no localizada.",
            "UNASSIGNED": "Caja registrada sin ubicacion.",
        }
        return schemas.ScanResponse(
            kind="BOX",
            box=_box_summary(box),
            current_position=_path_out(current_path) if current_path else None,
            location_state=state,
            operable=occupancy.is_operable(box),
            message=messages.get(state, "Estado de ubicacion desconocido."),
        )

    path = await repo.get_position_path(position_id)
    if path is None:
        raise NotFoundError("Posicion no encontrada.")
    position = path[0]
    box = await repo.get_box_at_position(position.id)
    state = occupancy.position_occupancy_state(position, box)
    messages = {
        "EMPTY": "Posicion vacia y disponible.",
        "OCCUPIED": "Posicion ocupada.",
        "BLOCKED": "Posicion bloqueada.",
        "RETIRED": "Posicion retirada.",
    }
    return schemas.ScanResponse(
        kind="POSITION",
        position=_path_out(path),
        position_state=state,
        box=_box_summary(box) if box is not None else None,
        message=messages[state],
    )


async def occupancy_report(
    session: AsyncSession,
    *,
    area_id: UUID | None,
    shelf_id: UUID | None,
) -> schemas.OccupancyReportOut:
    repo = LocationsRepository(session)
    shelves = await repo.list_shelves_for_scope(area_id=area_id, shelf_id=shelf_id)
    area_cache: dict[UUID, Area] = {}
    rows: list[schemas.OccupancyReportRowOut] = []
    counts_by_shelf: list[occupancy.OccupancyCounts] = []

    for shelf in shelves:
        area = area_cache.get(shelf.area_id)
        if area is None:
            area = await repo.get_area(shelf.area_id)
            if area is None:
                continue
            area_cache[area.id] = area
        positions = await repo.list_positions_for_scope(
            area_id=None,
            shelf_id=shelf.id,
            tray_id=None,
        )
        boxes = await repo.list_boxes_for_positions(
            [position.id for position in positions]
        )
        counts = occupancy.compute_shelf_occupancy(
            shelf,
            positions,
            _boxes_by_position(boxes),
        )
        counts_by_shelf.append(counts)
        rows.append(
            schemas.OccupancyReportRowOut(
                area_code=area.code,
                area_name=area.name,
                shelf_code=shelf.code,
                shelf_name=shelf.name,
                configured_capacity=counts.configured_capacity,
                visible_capacity=counts.visible_capacity,
                occupied_positions=counts.occupied_positions,
                available_positions=counts.available_positions,
                blocked_positions=counts.blocked_positions,
                retired_positions=counts.retired_positions,
                occupancy_rate=counts.occupancy_rate,
                capacity_matches=counts.capacity_matches_configuration,
            )
        )

    totals = occupancy.merge_counts(counts_by_shelf)
    unlocated, pending, in_transit = await _location_totals(session)
    totals = replace(
        totals,
        unlocated_boxes=unlocated,
        pending_confirmation_boxes=pending,
        in_transit_boxes=in_transit,
    )
    return schemas.OccupancyReportOut(
        generated_at=datetime.now(UTC),
        area_id=area_id,
        shelf_id=shelf_id,
        totals=_summary_out(
            "SHELF" if shelf_id else ("AREA" if area_id else "GLOBAL"),
            shelf_id or area_id,
            totals,
        ),
        rows=rows,
    )
```

**Archivo:** `backend/src/judicial_archive/modules/locations/reports.py` (NUEVO)

```python
from __future__ import annotations

import csv
import io
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.modules.locations.services import occupancy_report


def _csv_safe(value: object) -> str:
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{text}"
    return text


async def occupancy_csv(
    session: AsyncSession,
    *,
    area_id: UUID | None,
    shelf_id: UUID | None,
) -> str:
    report = await occupancy_report(session, area_id=area_id, shelf_id=shelf_id)
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "area_code",
            "area_name",
            "shelf_code",
            "shelf_name",
            "configured_capacity",
            "visible_capacity",
            "occupied_positions",
            "available_positions",
            "blocked_positions",
            "retired_positions",
            "occupancy_rate",
            "capacity_matches",
        ]
    )
    for row in report.rows:
        writer.writerow(
            [
                _csv_safe(row.area_code),
                _csv_safe(row.area_name),
                _csv_safe(row.shelf_code),
                _csv_safe(row.shelf_name or ""),
                row.configured_capacity,
                row.visible_capacity,
                row.occupied_positions,
                row.available_positions,
                row.blocked_positions,
                row.retired_positions,
                row.occupancy_rate,
                "true" if row.capacity_matches else "false",
            ]
        )
    return output.getvalue()
```

**Correccion de esquema:** `UnlocatedBoxOut.location_state` debe aceptar `MISSING`:

```python
class UnlocatedBoxOut(BaseModel):
    box: BoxSummaryOut
    location_state: Literal["UNASSIGNED", "PENDING_CONFIRMATION", "MISSING"]
    last_movement_at: datetime | None
```

### 8.10 Paso 10 - Routers

#### 8.10.1 Completar `modules/locations/routers.py`

Agregar despues de `list_box_types`:

```python
@shelves_router.get("", response_model=Page[schemas.ShelfOut])
async def list_shelves(
    params: Annotated[PageParams, Depends(pagination_params)],
    area_id: UUID | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    shelf_status: Annotated[str | None, Query(alias="status")] = None,
    sort_by: str | None = None,
    order: SortOrder = SortOrder.ASC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.ShelfOut]:
    sort = build_sort_params(sort_by, order, allowed_fields=_SHELF_SORT)
    return await services.list_shelves(
        session,
        params=params,
        area_id=area_id,
        q=q,
        status=shelf_status,
        sort_by=sort.sort_by or "code",
        order=sort.order,
    )


@shelves_router.post(
    "",
    response_model=schemas.ShelfOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_shelf(
    request: Request,
    body: schemas.ShelfCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.ShelfOut:
    return await services.create_shelf(request, session, current_user, body)


@shelves_router.get("/{shelf_id}", response_model=schemas.ShelfOut)
async def get_shelf(
    shelf_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.ShelfOut:
    return await services.get_shelf(session, shelf_id)


@shelves_router.patch("/{shelf_id}", response_model=schemas.ShelfOut)
async def update_shelf(
    request: Request,
    shelf_id: UUID,
    body: schemas.ShelfUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.ShelfOut:
    return await services.update_shelf(request, session, current_user, shelf_id, body)


@shelves_router.post("/{shelf_id}/activate", response_model=schemas.ShelfOut)
async def activate_shelf(
    request: Request,
    shelf_id: UUID,
    body: schemas.ShelfStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.ShelfOut:
    return await services.set_shelf_status(
        request, session, current_user, shelf_id, "ACTIVE", body.reason
    )


@shelves_router.post("/{shelf_id}/deactivate", response_model=schemas.ShelfOut)
async def deactivate_shelf(
    request: Request,
    shelf_id: UUID,
    body: schemas.ShelfStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.ShelfOut:
    return await services.set_shelf_status(
        request, session, current_user, shelf_id, "INACTIVE", body.reason
    )


@shelves_router.post(
    "/{shelf_id}/capacity/preview",
    response_model=schemas.CapacityPlanOut,
)
async def preview_shelf_capacity(
    shelf_id: UUID,
    body: schemas.CapacityTarget,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.CapacityPlanOut:
    return await services.preview_capacity(session, shelf_id, body)


@shelves_router.post(
    "/{shelf_id}/capacity/apply",
    response_model=schemas.CapacityApplyOut,
)
async def apply_shelf_capacity(
    request: Request,
    shelf_id: UUID,
    body: schemas.CapacityApplyRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.CapacityApplyOut:
    return await services.apply_capacity(request, session, current_user, shelf_id, body)


@trays_router.get("", response_model=Page[schemas.TrayOut])
async def list_trays(
    params: Annotated[PageParams, Depends(pagination_params)],
    shelf_id: UUID | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    tray_status: Annotated[str | None, Query(alias="status")] = None,
    sort_by: str | None = None,
    order: SortOrder = SortOrder.ASC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.TrayOut]:
    sort = build_sort_params(sort_by, order, allowed_fields=_TRAY_SORT)
    return await services.list_trays(
        session,
        params=params,
        shelf_id=shelf_id,
        q=q,
        status=tray_status,
        sort_by=sort.sort_by or "code",
        order=sort.order,
    )


@trays_router.post(
    "",
    response_model=schemas.TrayOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_tray(
    request: Request,
    body: schemas.TrayCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.TrayOut:
    return await services.create_tray(request, session, current_user, body)


@trays_router.get("/{tray_id}", response_model=schemas.TrayOut)
async def get_tray(
    tray_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.TrayOut:
    return await services.get_tray(session, tray_id)


@trays_router.patch("/{tray_id}", response_model=schemas.TrayOut)
async def update_tray(
    request: Request,
    tray_id: UUID,
    body: schemas.TrayUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.TrayOut:
    return await services.update_tray(request, session, current_user, tray_id, body)


@trays_router.post("/{tray_id}/activate", response_model=schemas.TrayOut)
async def activate_tray(
    request: Request,
    tray_id: UUID,
    body: schemas.TrayStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.TrayOut:
    return await services.set_tray_status(
        request, session, current_user, tray_id, "ACTIVE", body.reason
    )


@trays_router.post("/{tray_id}/deactivate", response_model=schemas.TrayOut)
async def deactivate_tray(
    request: Request,
    tray_id: UUID,
    body: schemas.TrayStatusRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.TrayOut:
    return await services.set_tray_status(
        request, session, current_user, tray_id, "INACTIVE", body.reason
    )


@positions_router.get("", response_model=Page[schemas.PositionOut])
async def list_positions(
    params: Annotated[PageParams, Depends(pagination_params)],
    tray_id: UUID | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    position_status: Annotated[str | None, Query(alias="status")] = None,
    sort_by: str | None = None,
    order: SortOrder = SortOrder.ASC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.PositionOut]:
    sort = build_sort_params(sort_by, order, allowed_fields=_POSITION_SORT)
    return await services.list_positions(
        session,
        params=params,
        tray_id=tray_id,
        q=q,
        status=position_status,
        sort_by=sort.sort_by or "code",
        order=sort.order,
    )


@positions_router.post(
    "",
    response_model=schemas.PositionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_position(
    request: Request,
    body: schemas.PositionCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PositionOut:
    return await services.create_position(request, session, current_user, body)


@positions_router.get("/{position_id}", response_model=schemas.PositionOut)
async def get_position(
    position_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> schemas.PositionOut:
    return await services.get_position(session, position_id)


@positions_router.patch("/{position_id}", response_model=schemas.PositionOut)
async def update_position(
    request: Request,
    position_id: UUID,
    body: schemas.PositionUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PositionOut:
    return await services.update_position(
        request, session, current_user, position_id, body
    )


@positions_router.post("/{position_id}/retire", response_model=schemas.PositionOut)
async def retire_position(
    request: Request,
    position_id: UUID,
    body: schemas.PositionRetireRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PositionOut:
    return await services.retire_position(
        request, session, current_user, position_id, body
    )


@positions_router.post("/{position_id}/activate", response_model=schemas.PositionOut)
async def activate_position(
    request: Request,
    position_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PositionOut:
    return await services.activate_position(request, session, current_user, position_id)
```

#### 8.10.2 Archivo `modules/locations/occupancy_router.py` (NUEVO)

```python
from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import (
    Page,
    PageParams,
    pagination_params,
)
from judicial_archive.modules.locations import reports, schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/locations", tags=["Ubicaciones"])
reports_router = APIRouter(
    prefix="/locations/reports",
    tags=["Ubicaciones - Reportes"],
)


@router.get("/occupancy", response_model=schemas.OccupancySummaryOut)
async def get_occupancy(
    area_id: UUID | None = None,
    shelf_id: UUID | None = None,
    tray_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_READ)),
) -> schemas.OccupancySummaryOut:
    return await services.get_occupancy(
        session,
        area_id=area_id,
        shelf_id=shelf_id,
        tray_id=tray_id,
    )


@router.get("/plan", response_model=schemas.LocationPlanOut)
async def get_location_plan(
    area_id: UUID | None = None,
    shelf_id: UUID | None = None,
    include_positions: bool = False,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_READ)),
) -> schemas.LocationPlanOut:
    return await services.get_location_plan(
        session,
        area_id=area_id,
        shelf_id=shelf_id,
        include_positions=include_positions,
    )


@router.get("/positions", response_model=Page[schemas.PositionOccupancyOut])
async def list_position_occupancy(
    params: Annotated[PageParams, Depends(pagination_params)],
    area_id: UUID | None = None,
    shelf_id: UUID | None = None,
    tray_id: UUID | None = None,
    state: Literal["EMPTY", "OCCUPIED", "BLOCKED", "RETIRED"] | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_READ)),
) -> Page[schemas.PositionOccupancyOut]:
    return await services.list_position_occupancy(
        session,
        params=params,
        area_id=area_id,
        shelf_id=shelf_id,
        tray_id=tray_id,
        state=state,
        q=q,
    )


@router.get("/unlocated-boxes", response_model=Page[schemas.UnlocatedBoxOut])
async def list_unlocated_boxes(
    params: Annotated[PageParams, Depends(pagination_params)],
    state: Literal["UNASSIGNED", "PENDING_CONFIRMATION"] | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_READ)),
) -> Page[schemas.UnlocatedBoxOut]:
    return await services.list_unlocated_boxes(
        session,
        params=params,
        state=state,
        q=q,
    )


@router.get("/scan", response_model=schemas.ScanResponse)
async def scan_location(
    box_number: Annotated[str | None, Query(max_length=32)] = None,
    position_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_READ)),
) -> schemas.ScanResponse:
    return await services.scan(
        session,
        box_number=box_number,
        position_id=position_id,
    )


@reports_router.get("/occupancy", response_model=schemas.OccupancyReportOut)
async def get_occupancy_report(
    area_id: UUID | None = None,
    shelf_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.REPORTS_READ)),
) -> schemas.OccupancyReportOut:
    return await services.occupancy_report(
        session,
        area_id=area_id,
        shelf_id=shelf_id,
    )


@reports_router.get("/occupancy.csv")
async def export_occupancy_csv(
    area_id: UUID | None = None,
    shelf_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.REPORTS_EXPORT)),
) -> Response:
    content = await reports.occupancy_csv(
        session,
        area_id=area_id,
        shelf_id=shelf_id,
    )
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="ocupacion.csv"',
        },
    )
```

#### 8.10.3 Archivo `modules/locations/blocks_router.py` (NUEVO)

```python
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import (
    Page,
    PageParams,
    pagination_params,
)
from judicial_archive.modules.locations import blocks, schemas
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/position-blocks", tags=["Ubicaciones - Bloqueos"])


@router.get("", response_model=Page[schemas.PositionBlockOut])
async def list_position_blocks(
    params: Annotated[PageParams, Depends(pagination_params)],
    area_id: UUID | None = None,
    shelf_id: UUID | None = None,
    active: Annotated[bool | None, Query()] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_READ)),
) -> Page[schemas.PositionBlockOut]:
    return await blocks.list_blocks(
        session,
        params=params,
        area_id=area_id,
        shelf_id=shelf_id,
        active=active,
    )


@router.post(
    "",
    response_model=schemas.PositionBlockOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_position_block(
    request: Request,
    body: schemas.PositionBlockCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PositionBlockOut:
    return await blocks.create_block(request, session, current_user, body)


@router.post("/{block_id}/cancel", response_model=schemas.PositionBlockOut)
async def cancel_position_block(
    request: Request,
    block_id: UUID,
    body: schemas.PositionBlockCancel,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CATALOG_MANAGE)),
) -> schemas.PositionBlockOut:
    return await blocks.cancel_block(
        request,
        session,
        current_user,
        block_id,
        body,
    )
```

#### 8.10.4 Archivo `modules/movements/routers.py` (NUEVO)

```python
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import (
    Page,
    PageParams,
    pagination_params,
)
from judicial_archive.modules.boxes.schemas import BoxLocationHistoryOut
from judicial_archive.modules.movements import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

box_locations_router = APIRouter(
    prefix="/locations/boxes",
    tags=["Ubicaciones - Cajas"],
)
movements_router = APIRouter(prefix="/movements", tags=["Movimientos"])


@box_locations_router.get("/{box_id}", response_model=schemas.BoxLocationDetailOut)
async def get_box_location(
    box_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_READ)),
) -> schemas.BoxLocationDetailOut:
    return await services.get_box_location(session, box_id)


@box_locations_router.get(
    "/{box_id}/history",
    response_model=Page[BoxLocationHistoryOut],
)
async def list_box_location_history(
    params: Annotated[PageParams, Depends(pagination_params)],
    box_id: UUID,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    source: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_READ)),
) -> Page[BoxLocationHistoryOut]:
    return await services.list_box_history(
        session,
        params=params,
        box_id=box_id,
        from_date=from_date,
        to_date=to_date,
        source=source,
    )


@box_locations_router.post(
    "/{box_id}/assign",
    response_model=schemas.LocationMutationOut,
)
async def assign_box_location(
    request: Request,
    box_id: UUID,
    body: schemas.AssignRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_MANAGE)),
) -> schemas.LocationMutationOut:
    return await services.assign_box(request, session, current_user, box_id, body)


@box_locations_router.post(
    "/{box_id}/unassign",
    response_model=schemas.LocationMutationOut,
)
async def unassign_box_location(
    request: Request,
    box_id: UUID,
    body: schemas.UnassignRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_MANAGE)),
) -> schemas.LocationMutationOut:
    return await services.unassign_box(request, session, current_user, box_id, body)


@box_locations_router.post(
    "/{box_id}/transfer",
    response_model=schemas.LocationMutationOut,
)
async def transfer_box_location(
    request: Request,
    box_id: UUID,
    body: schemas.TransferRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_MANAGE)),
) -> schemas.LocationMutationOut:
    return await services.transfer_box(request, session, current_user, box_id, body)


@box_locations_router.post(
    "/{box_id}/confirm",
    response_model=schemas.LocationMutationOut,
)
async def confirm_box_location(
    request: Request,
    box_id: UUID,
    body: schemas.ConfirmRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_MANAGE)),
) -> schemas.LocationMutationOut:
    return await services.confirm_location(request, session, current_user, box_id, body)


@movements_router.get("", response_model=Page[schemas.MovementOut])
async def list_movements(
    params: Annotated[PageParams, Depends(pagination_params)],
    box_id: UUID | None = None,
    movement_type: str | None = None,
    movement_status: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_READ)),
) -> Page[schemas.MovementOut]:
    return await services.list_movements(
        session,
        params=params,
        box_id=box_id,
        movement_type=movement_type,
        movement_status=movement_status,
        from_date=from_date,
        to_date=to_date,
    )


@movements_router.get("/{movement_id}", response_model=schemas.MovementOut)
async def get_movement(
    movement_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_READ)),
) -> schemas.MovementOut:
    return await services.get_movement(session, movement_id)


@movements_router.post(
    "/{movement_id}/complete",
    response_model=schemas.LocationMutationOut,
)
async def complete_movement(
    request: Request,
    movement_id: UUID,
    body: schemas.CompleteMovementRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_MANAGE)),
) -> schemas.LocationMutationOut:
    return await services.complete_movement(
        request, session, current_user, movement_id, body
    )


@movements_router.post(
    "/{movement_id}/cancel",
    response_model=schemas.LocationMutationOut,
)
async def cancel_movement(
    request: Request,
    movement_id: UUID,
    body: schemas.CancelMovementRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.MOVEMENTS_MANAGE)),
) -> schemas.LocationMutationOut:
    return await services.cancel_movement(
        request, session, current_user, movement_id, body
    )
```

#### 8.10.5 Registrar routers en `api/v1/router.py`

```python
from judicial_archive.modules.locations.blocks_router import (
    router as position_blocks_router,
)
from judicial_archive.modules.locations.occupancy_router import (
    reports_router as location_reports_router,
    router as locations_router,
)
from judicial_archive.modules.movements.routers import (
    box_locations_router,
    movements_router,
)
```

Y dentro de `api_router`:

```python
api_router.include_router(locations_router)
api_router.include_router(location_reports_router)
api_router.include_router(position_blocks_router)
api_router.include_router(box_locations_router)
api_router.include_router(movements_router)
```

Mantener el orden de inclusion existente para no cambiar rutas ya publicadas.

## 9. Pruebas

### 9.1 Estrategia

La fase B6 se valida en cuatro capas:

| Capa | Alcance | Base de datos | Objetivo |
|---|---|---|---|
| Unitaria | Funciones puras de ocupacion, estados y transiciones | No | Rapidez y cobertura de formulas |
| Integracion | Servicios, repositorios, constraints, triggers y concurrencia | PostgreSQL real | Verdad transaccional |
| API | Contratos HTTP, permisos, CSRF, paginacion y errores | PostgreSQL real | Compatibilidad con frontend |
| Migracion | Upgrade, downgrade y metadata | PostgreSQL real | Despliegue seguro |

Reglas:

- No usar SQLite para pruebas de integracion; los constraints parciales, `JSONB`, triggers y `FOR UPDATE` no se comportan igual.
- No mockear la sesion SQLAlchemy en pruebas de servicios con locks.
- No comparar timestamps exactos; usar `is not None`, orden relativo o rangos.
- Cada prueba debe limpiar datos mediante las fixtures existentes.
- Las pruebas de concurrencia usan dos sesiones y `asyncio.gather`.
- Las pruebas de API usan `seeded_api_client` y `csrf_headers`.
- Los tests unitarios no importan routers ni levantan la app.

### 9.2 Fixtures y limpieza

#### 9.2.1 Actualizar `backend/tests/integration/conftest.py`

El truncate de limpieza debe deshabilitar tambien el trigger append-only del historial:

```python
async with db_engine.begin() as connection:
    await connection.execute(
        text("ALTER TABLE audit_events DISABLE TRIGGER trg_audit_events_no_truncate")
    )
    await connection.execute(
        text(
            "ALTER TABLE box_location_history "
            "DISABLE TRIGGER trg_box_location_history_no_truncate"
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
                "ALTER TABLE box_location_history "
                "ENABLE TRIGGER trg_box_location_history_no_truncate"
            )
        )
        await connection.execute(
            text("ALTER TABLE audit_events ENABLE TRIGGER trg_audit_events_no_truncate")
        )
```

No usar `TRUNCATE ... CASCADE` sin deshabilitar el trigger: la prueba fallara con `box_location_history es append-only`.

#### 9.2.2 Fixture de estructura de ubicaciones

Crear `backend/tests/integration/location_fixtures.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from judicial_archive.core.enums import CustodyStatus
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.courts.models import Court
from judicial_archive.modules.locations.models import Area, Position, Shelf, Tray


@dataclass(frozen=True)
class LocationTree:
    area_id: UUID
    shelf_id: UUID
    tray_id: UUID
    position_ids: tuple[UUID, ...]
    box_ids: tuple[UUID, ...]


async def create_location_tree(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    positions: int = 3,
    boxes: int = 2,
) -> LocationTree:
    async with session_factory() as session:
        court = await session.scalar(select(Court).limit(1))
        if court is None:
            raise AssertionError("El seed debe crear al menos un juzgado")

        suffix = uuid4().hex[:8].upper()
        area = Area(code=f"A{suffix}", name="Area B6", status="ACTIVE")
        session.add(area)
        await session.flush()

        shelf = Shelf(
            area_id=area.id,
            code=f"S{suffix}",
            name="Anaquel B6",
            levels=1,
            positions_per_level=positions,
            status="ACTIVE",
        )
        session.add(shelf)
        await session.flush()

        tray = Tray(
            shelf_id=shelf.id,
            code=f"T{suffix}",
            name="Bandeja B6",
            status="ACTIVE",
        )
        session.add(tray)
        await session.flush()

        position_rows = [
            Position(
                tray_id=tray.id,
                code=f"P{index:02d}",
                label=f"Posicion {index}",
                status="AVAILABLE",
            )
            for index in range(1, positions + 1)
        ]
        session.add_all(position_rows)
        await session.flush()

        box_rows = [
            Box(
                court_id=court.id,
                year=2026,
                box_type="EXPEDIENTES",
                visible_number=f"B6-{suffix}-{index}",
                lifecycle_status="ACTIVE",
                custody_status=CustodyStatus.UNKNOWN.value,
                confidentiality="INTERNAL",
                created_by=None,
            )
            for index in range(1, boxes + 1)
        ]
        session.add_all(box_rows)
        await session.commit()

        return LocationTree(
            area_id=area.id,
            shelf_id=shelf.id,
            tray_id=tray.id,
            position_ids=tuple(row.id for row in position_rows),
            box_ids=tuple(row.id for row in box_rows),
        )


@pytest_asyncio.fixture
async def location_tree(session_factory) -> LocationTree:
    return await create_location_tree(session_factory)
```

### 9.3 Pruebas unitarias de ocupacion

Archivo `backend/tests/unit/test_occupancy.py`:

```python
from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from judicial_archive.modules.locations.occupancy import (
    compute_shelf_occupancy,
    merge_counts,
)


def _shelf(*, capacity: int | None = None):
    return SimpleNamespace(
        id=uuid4(),
        code="S1",
        capacity_positions=capacity,
    )


def _position(*, status: str = "AVAILABLE", code: str = "P1"):
    return SimpleNamespace(id=uuid4(), status=status, code=code)


def _box(*, custody: str = "IN_PLACE", number: str = "B-1"):
    return SimpleNamespace(custody_status=custody, visible_number=number)


def test_empty_shelf_has_zero_occupancy() -> None:
    shelf = _shelf(capacity=3)
    positions = [_position(code=f"P{i}") for i in range(1, 4)]

    counts = compute_shelf_occupancy(shelf, positions, {})

    assert counts.configured_capacity == 3
    assert counts.visible_capacity == 3
    assert counts.occupied_positions == 0
    assert counts.available_positions == 3
    assert counts.occupancy_rate == 0.0
    assert counts.capacity_matches_configuration is True


def test_occupied_and_blocked_positions_are_counted_once() -> None:
    shelf = _shelf(capacity=3)
    occupied = _position(code="P1")
    blocked = _position(status="BLOCKED", code="P2")
    empty = _position(code="P3")

    counts = compute_shelf_occupancy(
        shelf,
        [occupied, blocked, empty],
        {occupied.id: _box()},
    )

    assert counts.occupied_positions == 1
    assert counts.blocked_positions == 1
    assert counts.available_positions == 1
    assert counts.occupancy_rate == 0.3333


def test_retired_positions_are_not_visible_capacity() -> None:
    shelf = _shelf(capacity=3)
    positions = [
        _position(code="P1"),
        _position(code="P2"),
        _position(status="RETIRED", code="P3"),
    ]

    counts = compute_shelf_occupancy(shelf, positions, {})

    assert counts.visible_capacity == 2
    assert counts.retired_positions == 1
    assert counts.capacity_mismatches[0].delta == -1


def test_box_in_blocked_position_is_a_conflict_not_occupied() -> None:
    shelf = _shelf(capacity=1)
    position = _position(status="BLOCKED", code="P1")

    counts = compute_shelf_occupancy(
        shelf,
        [position],
        {position.id: _box(number="B-9")},
    )

    assert counts.occupied_positions == 0
    assert counts.blocked_positions == 1
    assert counts.conflicts
    assert "B-9" in counts.conflicts[0]


def test_box_with_invalid_custody_is_a_conflict() -> None:
    shelf = _shelf(capacity=1)
    position = _position(code="P1")

    counts = compute_shelf_occupancy(
        shelf,
        [position],
        {position.id: _box(custody="ON_LOAN")},
    )

    assert counts.occupied_positions == 0
    assert counts.conflicts
    assert "ON_LOAN" in counts.conflicts[0]


def test_merge_counts_keeps_global_rate_and_mismatches() -> None:
    first = compute_shelf_occupancy(
        _shelf(capacity=2),
        [_position(code="P1"), _position(code="P2")],
        {},
    )
    second = compute_shelf_occupancy(
        _shelf(capacity=3),
        [_position(code="P1")],
        {},
    )

    merged = merge_counts([first, second])

    assert merged.configured_capacity == 5
    assert merged.visible_capacity == 3
    assert merged.available_positions == 3
    assert len(merged.capacity_mismatches) == 1
```

### 9.4 Pruebas unitarias de estado de ubicacion

Archivo `backend/tests/unit/test_location_state.py`:

```python
from __future__ import annotations

from types import SimpleNamespace

import pytest

from judicial_archive.modules.locations.occupancy import (
    classify_location_state,
    is_operable,
    position_occupancy_state,
)


@pytest.mark.parametrize(
    ("custody", "expected"),
    [
        ("IN_PLACE", "CONFIRMED"),
        ("PENDING_VERIFICATION", "PENDING_CONFIRMATION"),
        ("IN_RECONCILIATION", "IN_RECONCILIATION"),
        ("ON_LOAN", "ON_LOAN"),
        ("IN_TRANSIT", "IN_TRANSIT"),
        ("MISSING", "MISSING"),
        ("UNKNOWN", "UNASSIGNED"),
    ],
)
def test_classify_location_state(custody: str, expected: str) -> None:
    box = SimpleNamespace(custody_status=custody)
    assert classify_location_state(box) == expected


@pytest.mark.parametrize(
    ("lifecycle", "custody", "expected"),
    [
        ("ACTIVE", "UNKNOWN", True),
        ("ACTIVE", "MISSING", True),
        ("ACTIVE", "IN_PLACE", True),
        ("ACTIVE", "PENDING_VERIFICATION", True),
        ("ACTIVE", "ON_LOAN", False),
        ("ARCHIVED", "UNKNOWN", False),
    ],
)
def test_is_operable(lifecycle: str, custody: str, expected: bool) -> None:
    box = SimpleNamespace(lifecycle_status=lifecycle, custody_status=custody)
    assert is_operable(box) is expected


@pytest.mark.parametrize(
    ("position_status", "has_box", "expected"),
    [
        ("AVAILABLE", False, "EMPTY"),
        ("AVAILABLE", True, "OCCUPIED"),
        ("BLOCKED", False, "BLOCKED"),
        ("BLOCKED", True, "BLOCKED"),
        ("RETIRED", False, "RETIRED"),
    ],
)
def test_position_occupancy_state(
    position_status: str,
    has_box: bool,
    expected: str,
) -> None:
    position = SimpleNamespace(status=position_status)
    box = SimpleNamespace() if has_box else None
    assert position_occupancy_state(position, box) == expected
```

### 9.5 Pruebas de integracion de movimientos

Archivo `backend/tests/integration/test_location_movements.py`:

```python
from __future__ import annotations

import pytest
from sqlalchemy import select

from judicial_archive.core.enums import CustodyStatus, MovementStatus
from judicial_archive.core.errors import ConflictError
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.movements import services
from judicial_archive.modules.movements.schemas import (
    AssignRequest,
    CancelMovementRequest,
    CompleteMovementRequest,
    TransferRequest,
)
from judicial_archive.modules.users.models import User
from tests.integration.auth_helpers import ADMIN_USERNAME
from tests.integration.location_fixtures import create_location_tree

pytestmark = pytest.mark.integration


async def _actor(session):
    user = await session.scalar(select(User).where(User.username == ADMIN_USERNAME))
    assert user is not None
    return user


async def test_assign_creates_history_and_movement(db_session, session_factory) -> None:
    tree = await create_location_tree(session_factory)
    actor = await _actor(db_session)
    box = await db_session.get(Box, tree.box_ids[0])

    result = await services.assign_box(
        None,
        db_session,
        actor,
        box.id,
        AssignRequest(
            position_id=tree.position_ids[0],
            confirmed=True,
            reason="Asignacion inicial",
            expected_version=box.version,
        ),
    )

    assert result.box.box.custody_status == CustodyStatus.IN_PLACE.value
    assert result.box.current_position is not None
    assert result.movement is not None
    assert result.movement.movement_type == "ASSIGN"
    assert result.history.to_position_id == tree.position_ids[0]
    assert result.history.from_custody_status == CustodyStatus.UNKNOWN.value


async def test_assign_requires_pending_verification_when_not_confirmed(
    db_session,
    session_factory,
) -> None:
    tree = await create_location_tree(session_factory)
    actor = await _actor(db_session)
    box = await db_session.get(Box, tree.box_ids[0])

    result = await services.assign_box(
        None,
        db_session,
        actor,
        box.id,
        AssignRequest(
            position_id=tree.position_ids[0],
            confirmed=False,
            reason="Ubicacion sin verificar",
            expected_version=box.version,
        ),
    )

    assert result.box.box.custody_status == CustodyStatus.PENDING_VERIFICATION.value
    assert result.box.box.location_state == "PENDING_CONFIRMATION"


async def test_assign_rejects_occupied_position(db_session, session_factory) -> None:
    tree = await create_location_tree(session_factory)
    actor = await _actor(db_session)
    first = await db_session.get(Box, tree.box_ids[0])
    second = await db_session.get(Box, tree.box_ids[1])

    await services.assign_box(
        None,
        db_session,
        actor,
        first.id,
        AssignRequest(
            position_id=tree.position_ids[0],
            confirmed=True,
            reason="Primera caja",
            expected_version=first.version,
        ),
    )
    second = await db_session.get(Box, second.id)

    with pytest.raises(ConflictError) as exc:
        await services.assign_box(
            None,
            db_session,
            actor,
            second.id,
            AssignRequest(
                position_id=tree.position_ids[0],
                confirmed=True,
                reason="Segunda caja",
                expected_version=second.version,
            ),
        )

    assert exc.value.details["reason"] == "position_occupied"


async def test_transfer_immediate_updates_location(db_session, session_factory) -> None:
    tree = await create_location_tree(session_factory)
    actor = await _actor(db_session)
    box = await db_session.get(Box, tree.box_ids[0])
    assigned = await services.assign_box(
        None,
        db_session,
        actor,
        box.id,
        AssignRequest(
            position_id=tree.position_ids[0],
            confirmed=True,
            reason="Origen",
            expected_version=box.version,
        ),
    )

    result = await services.transfer_box(
        None,
        db_session,
        actor,
        box.id,
        TransferRequest(
            to_position_id=tree.position_ids[1],
            mode="IMMEDIATE",
            confirmed=True,
            reason="Traslado directo",
            expected_version=assigned.box.version,
        ),
    )

    assert result.box.current_position is not None
    assert result.box.current_position.position_id == tree.position_ids[1]
    assert result.movement is not None
    assert result.movement.movement_type == "TRANSFER"
    assert result.movement.movement_status == MovementStatus.COMPLETED.value


async def test_transfer_in_transit_then_complete(db_session, session_factory) -> None:
    tree = await create_location_tree(session_factory)
    actor = await _actor(db_session)
    box = await db_session.get(Box, tree.box_ids[0])
    assigned = await services.assign_box(
        None,
        db_session,
        actor,
        box.id,
        AssignRequest(
            position_id=tree.position_ids[0],
            confirmed=True,
            reason="Origen",
            expected_version=box.version,
        ),
    )

    in_transit = await services.transfer_box(
        None,
        db_session,
        actor,
        box.id,
        TransferRequest(
            to_position_id=tree.position_ids[1],
            mode="IN_TRANSIT",
            confirmed=False,
            reason="Traslado en dos fases",
            expected_version=assigned.box.version,
        ),
    )
    assert in_transit.box.box.custody_status == CustodyStatus.IN_TRANSIT.value
    assert in_transit.box.current_position is None
    assert in_transit.box.open_movement is not None

    completed = await services.complete_movement(
        None,
        db_session,
        actor,
        in_transit.movement.id,
        CompleteMovementRequest(
            confirmed=True,
            reason="Recepcion confirmada",
            expected_version=in_transit.box.version,
        ),
    )
    assert completed.box.box.custody_status == CustodyStatus.IN_PLACE.value
    assert completed.box.current_position.position_id == tree.position_ids[1]


async def test_cancel_in_transit_restores_origin(db_session, session_factory) -> None:
    tree = await create_location_tree(session_factory)
    actor = await _actor(db_session)
    box = await db_session.get(Box, tree.box_ids[0])
    assigned = await services.assign_box(
        None,
        db_session,
        actor,
        box.id,
        AssignRequest(
            position_id=tree.position_ids[0],
            confirmed=True,
            reason="Origen",
            expected_version=box.version,
        ),
    )

    in_transit = await services.transfer_box(
        None,
        db_session,
        actor,
        box.id,
        TransferRequest(
            to_position_id=tree.position_ids[1],
            mode="IN_TRANSIT",
            confirmed=False,
            reason="Traslado",
            expected_version=assigned.box.version,
        ),
    )
    cancelled = await services.cancel_movement(
        None,
        db_session,
        actor,
        in_transit.movement.id,
        CancelMovementRequest(
            reason="Se cancela el traslado",
            expected_version=in_transit.box.version,
        ),
    )

    assert cancelled.box.box.custody_status == CustodyStatus.IN_PLACE.value
    assert cancelled.box.current_position.position_id == tree.position_ids[0]
    assert cancelled.box.open_movement is None
```

**Nota:** cuando el servicio se invoca directamente, `request=None` solo es aceptable si `record_audit_event` tolera ausencia de request. Si no lo tolera, usar un `Request` minimo de Starlette o probar por API. No relajar la auditoria para acomodar pruebas.

### 9.6 Pruebas de API

Archivo `backend/tests/integration/test_location_api.py`:

```python
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.integration.auth_helpers import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    csrf_headers,
    login,
)
from tests.integration.location_fixtures import location_tree  # noqa: F401

pytestmark = pytest.mark.integration


def _assign(
    client: TestClient,
    box_id,
    position_id,
    *,
    version: int = 1,
    confirmed: bool = True,
):
    return client.post(
        f"/api/v1/locations/boxes/{box_id}/assign",
        json={
            "position_id": str(position_id),
            "confirmed": confirmed,
            "reason": "Prueba de asignacion",
            "expected_version": version,
        },
        headers=csrf_headers(client),
    )


def test_assign_and_get_box_location(seeded_api_client, location_tree) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    response = _assign(client, location_tree.box_ids[0], location_tree.position_ids[0])

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["box"]["box"]["custody_status"] == "IN_PLACE"
    assert payload["box"]["current_position"]["position_id"] == str(
        location_tree.position_ids[0]
    )
    assert payload["box"]["version"] == 2

    detail = client.get(f"/api/v1/locations/boxes/{location_tree.box_ids[0]}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["version"] == 2
    assert detail.json()["history_count"] == 1


def test_assign_rejects_stale_version(seeded_api_client, location_tree) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    response = _assign(
        client,
        location_tree.box_ids[0],
        location_tree.position_ids[0],
        version=99,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["details"]["reason"] == "stale_version"


def test_transfer_in_transit_and_complete(seeded_api_client, location_tree) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    assigned = _assign(
        client,
        location_tree.box_ids[0],
        location_tree.position_ids[0],
    )
    assert assigned.status_code == 200, assigned.text
    version = assigned.json()["box"]["version"]

    response = client.post(
        f"/api/v1/locations/boxes/{location_tree.box_ids[0]}/transfer",
        json={
            "to_position_id": str(location_tree.position_ids[1]),
            "mode": "IN_TRANSIT",
            "confirmed": False,
            "reason": "Traslado en transito",
            "expected_version": version,
        },
        headers=csrf_headers(client),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["box"]["box"]["custody_status"] == "IN_TRANSIT"
    assert payload["box"]["current_position"] is None
    movement_id = payload["movement"]["id"]
    box_version = payload["box"]["version"]

    completed = client.post(
        f"/api/v1/movements/{movement_id}/complete",
        json={
            "confirmed": True,
            "reason": "Recepcion",
            "expected_version": box_version,
        },
        headers=csrf_headers(client),
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["box"]["box"]["custody_status"] == "IN_PLACE"
    assert completed.json()["box"]["current_position"]["position_id"] == str(
        location_tree.position_ids[1]
    )


def test_scan_by_box_and_position(seeded_api_client, location_tree) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    _assign(client, location_tree.box_ids[0], location_tree.position_ids[0])

    by_position = client.get(
        "/api/v1/locations/scan",
        params={"position_id": str(location_tree.position_ids[0])},
    )
    assert by_position.status_code == 200, by_position.text
    assert by_position.json()["kind"] == "POSITION"
    assert by_position.json()["position_state"] == "OCCUPIED"

    box_number = by_position.json()["box"]["visible_number"]
    by_box = client.get("/api/v1/locations/scan", params={"box_number": box_number})
    assert by_box.status_code == 200, by_box.text
    assert by_box.json()["kind"] == "BOX"
    assert by_box.json()["location_state"] == "CONFIRMED"


def test_scan_unknown_box_returns_unregistered(seeded_api_client) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    response = client.get("/api/v1/locations/scan", params={"box_number": "NO-EXISTE"})

    assert response.status_code == 200, response.text
    assert response.json()["kind"] == "UNREGISTERED_BOX"
    assert response.json()["operable"] is False


def test_occupancy_and_report(seeded_api_client, location_tree) -> None:
    client = seeded_api_client
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    occupancy = client.get(
        "/api/v1/locations/occupancy",
        params={"shelf_id": str(location_tree.shelf_id)},
    )
    assert occupancy.status_code == 200, occupancy.text
    assert occupancy.json()["visible_capacity"] == 3

    report = client.get(
        "/api/v1/locations/reports/occupancy",
        params={"shelf_id": str(location_tree.shelf_id)},
    )
    assert report.status_code == 200, report.text
    assert report.json()["rows"]

    csv_response = client.get(
        "/api/v1/locations/reports/occupancy.csv",
        params={"shelf_id": str(location_tree.shelf_id)},
    )
    assert csv_response.status_code == 200, csv_response.text
    assert "shelf_code" in csv_response.text
```

### 9.7 Pruebas de concurrencia

Archivo `backend/tests/integration/test_location_concurrency.py`:

```python
from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select

from judicial_archive.core.errors import ConflictError
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.movements import services
from judicial_archive.modules.movements.schemas import AssignRequest
from judicial_archive.modules.users.models import User
from tests.integration.auth_helpers import ADMIN_USERNAME
from tests.integration.location_fixtures import create_location_tree

pytestmark = pytest.mark.integration


async def _assign_once(session_factory, box_id, position_id):
    async with session_factory() as session:
        actor = await session.scalar(
            select(User).where(User.username == ADMIN_USERNAME)
        )
        box = await session.get(Box, box_id)
        return await services.assign_box(
            None,
            session,
            actor,
            box.id,
            AssignRequest(
                position_id=position_id,
                confirmed=True,
                reason="Concurrencia",
                expected_version=box.version,
            ),
        )


async def test_two_assignments_only_one_wins(session_factory) -> None:
    tree = await create_location_tree(session_factory)

    results = await asyncio.gather(
        _assign_once(session_factory, tree.box_ids[0], tree.position_ids[0]),
        _assign_once(session_factory, tree.box_ids[1], tree.position_ids[0]),
        return_exceptions=True,
    )

    successes = [item for item in results if not isinstance(item, Exception)]
    conflicts = [item for item in results if isinstance(item, ConflictError)]

    assert len(successes) == 1
    assert len(conflicts) == 1
    assert conflicts[0].details["reason"] in {
        "position_occupied",
        "stale_version",
        "open_movement_exists",
    }
```

**Nota:** si `record_audit_event` exige `Request`, construir un request minimo compartido. No cambiar la firma del servicio solo para la prueba.

### 9.8 Pruebas de historial append-only

Archivo `backend/tests/integration/test_location_history.py`:

```python
from __future__ import annotations

import pytest
from sqlalchemy import delete, text, update
from sqlalchemy.exc import DBAPIError

from judicial_archive.modules.boxes.models import BoxLocationHistory
from tests.integration.location_fixtures import location_tree  # noqa: F401

pytestmark = pytest.mark.integration


async def _seed_history(db_session, tree):
    row = BoxLocationHistory(
        box_id=tree.box_ids[0],
        to_custody_status="UNKNOWN",
        to_location_precision="UNKNOWN",
        reason="Historial de prueba",
    )
    db_session.add(row)
    await db_session.commit()
    return row


async def test_history_rejects_update(db_session, location_tree) -> None:
    row = await _seed_history(db_session, location_tree)

    with pytest.raises(DBAPIError):
        await db_session.execute(
            update(BoxLocationHistory)
            .where(BoxLocationHistory.id == row.id)
            .values(reason="alterado")
        )
        await db_session.commit()
    await db_session.rollback()


async def test_history_rejects_delete(db_session, location_tree) -> None:
    row = await _seed_history(db_session, location_tree)

    with pytest.raises(DBAPIError):
        await db_session.execute(
            delete(BoxLocationHistory).where(BoxLocationHistory.id == row.id)
        )
        await db_session.commit()
    await db_session.rollback()


async def test_history_rejects_truncate(db_session) -> None:
    with pytest.raises(DBAPIError):
        await db_session.execute(text("TRUNCATE TABLE box_location_history"))
        await db_session.commit()
    await db_session.rollback()
```

`_seed_history` inserta un registro valido directamente; el trigger solo bloquea `UPDATE`, `DELETE` y `TRUNCATE`, no `INSERT`. No se debe reutilizar una fila creada por otra prueba porque cada prueba tiene su propia limpieza.

### 9.9 Pruebas de esquema y migracion

Actualizar:

- `backend/tests/integration/test_schema_metadata.py`
  - incluir `box_location_history`;
  - incluir `uq_box_movements_open_box`;
  - incluir `cancellation_reason`;
  - verificar `PENDING_VERIFICATION` en `ck_boxes_custody_status`;
  - verificar `UNASSIGN` en `ck_box_movements_type`.

- `backend/tests/integration/test_schema_constraints.py`
  - insertar dos movimientos abiertos para la misma caja y esperar `IntegrityError`;
  - insertar dos cajas en la misma posicion con custodia `PENDING_VERIFICATION` y esperar `IntegrityError`;
  - insertar caja `PENDING_VERIFICATION` sin posicion y esperar `IntegrityError`;
  - intentar `UPDATE`, `DELETE` y `TRUNCATE` sobre historial.

- `backend/tests/integration/test_migrations.py`
  - `alembic upgrade head` crea tabla, indices, triggers y constraints;
  - `alembic downgrade -1` elimina los objetos B6;
  - `alembic upgrade head` vuelve a aplicar sin errores;
  - el downgrade falla de forma controlada si existen datos incompatibles.

### 9.10 Matriz de cobertura funcional

| Requisito | Unitarias | Integracion | API |
|---|---|---|---|
| Ocupacion por anaquel | Si | Si | Si |
| Ocupacion por area/global | Si | Si | Si |
| Plano con posiciones | No | Si | Si |
| Asignacion confirmada | No | Si | Si |
| Asignacion pendiente | No | Si | Si |
| Desasignacion | No | Si | Si |
| Traslado inmediato | No | Si | Si |
| Traslado en transito | No | Si | Si |
| Cancelacion de traslado | No | Si | Si |
| Escaneo por caja | No | Si | Si |
| Escaneo por posicion | No | Si | Si |
| Caja no registrada | No | Si | Si |
| Bloqueo de rango | No | Si | Si |
| Historial append-only | No | Si | No |
| CSV seguro | No | Si | Si |
| Permisos | No | Si | Si |
| Concurrencia | No | Si | No |
| Migracion/rollback | No | Si | No |

### 9.11 Comandos de prueba

```powershell
Set-Location backend
$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:Santi.15@localhost:5432/sga_test"
$env:TEST_REDIS_URL = "redis://localhost:6379/15"

uv run pytest tests/unit -q --no-cov
uv run pytest tests/integration -q --no-cov -n 0
uv run pytest -q
```

Resultado esperado:

- Unitarias: todas pasan.
- Integracion: todas pasan, sin `xfail`.
- Suite completa: `>= 269` pruebas, `0 failed`, `0 xfailed`.
- Cobertura minima B6: 90% en `locations/occupancy.py`, 85% en `movements/services.py`, 85% en `locations/services.py`.

## 10. Documentacion

### 10.1 `docs/api.md`

Agregar:

- tabla de endpoints B6 con metodo, ruta, permiso y descripcion;
- ejemplos de asignacion, traslado, escaneo y ocupacion;
- codigos de error: `400`, `403`, `404`, `409`, `422`;
- explicacion de `expected_version`;
- ejemplo de `409` con `details.reason`;
- nota de que `GET /locations/scan` no modifica datos.

### 10.2 `docs/modelo-de-datos.md`

Agregar:

- `box_location_history` con columnas, indices y triggers;
- `cancellation_reason` en `position_blocks`;
- nuevos valores de enums;
- constraints actualizados;
- diagrama de relaciones caja-posicion-movimiento-historial;
- nota de que el historial es inmutable.

### 10.3 `docs/reglas-de-negocio.md`

Agregar reglas numeradas:

- `BR-B6-001`: una caja solo puede tener una ubicacion actual;
- `BR-B6-002`: una posicion solo puede tener una caja activa;
- `BR-B6-003`: `PENDING_VERIFICATION` ocupa posicion pero no confirma ubicacion;
- `BR-B6-004`: `IN_TRANSIT` no ocupa posicion;
- `BR-B6-005`: no se puede trasladar a posicion ocupada, bloqueada o retirada;
- `BR-B6-006`: no se puede desasignar una caja en prestito o en transito;
- `BR-B6-007`: todo cambio de ubicacion genera historial y auditoria;
- `BR-B6-008`: cancelar un traslado restaura el origen solo si sigue libre;
- `BR-B6-009`: el historial no se actualiza ni se elimina;
- `BR-B6-010`: la capacidad configurada no bloquea operaciones, solo advierte.

### 10.4 `docs/inventario-fisico.md`

Agregar flujo operativo:

1. escanear caja o posicion;
2. verificar estado;
3. asignar, desasignar o trasladar;
4. confirmar recepcion;
5. registrar discrepancia;
6. consultar historial y reporte.

Incluir ejemplos de uso en mostrador y en deposito.

### 10.5 `docs/pruebas.md`

Agregar:

- comandos B6;
- variables de entorno;
- fixtures;
- pruebas de concurrencia;
- pruebas de migracion;
- criterio de "sin xfail".

### 10.6 `docs/seguridad.md`

Agregar:

- permisos por endpoint;
- CSRF en mutaciones;
- proteccion CSV injection;
- no exponer datos de cajas en reportes sin permiso;
- auditoria de actor, motivo y metadata.

### 10.7 `docs/roles-y-permisos.md`

Agregar matriz:

| Endpoint | Permiso |
|---|---|
| `GET /locations/occupancy` | `MOVEMENTS_READ` |
| `GET /locations/plan` | `MOVEMENTS_READ` |
| `GET /locations/positions` | `MOVEMENTS_READ` |
| `GET /locations/unlocated-boxes` | `MOVEMENTS_READ` |
| `GET /locations/scan` | `BOXES_READ` |
| `POST /locations/boxes/{id}/assign` | `MOVEMENTS_MANAGE` |
| `POST /locations/boxes/{id}/unassign` | `MOVEMENTS_MANAGE` |
| `POST /locations/boxes/{id}/transfer` | `MOVEMENTS_MANAGE` |
| `POST /locations/boxes/{id}/confirm` | `MOVEMENTS_MANAGE` |
| `GET /locations/boxes/{id}` | `BOXES_READ` |
| `GET /locations/boxes/{id}/history` | `MOVEMENTS_READ` |
| `GET /movements` | `MOVEMENTS_READ` |
| `POST /movements/{id}/complete` | `MOVEMENTS_MANAGE` |
| `POST /movements/{id}/cancel` | `MOVEMENTS_MANAGE` |
| `GET /locations/reports/occupancy` | `REPORTS_READ` |
| `GET /locations/reports/occupancy.csv` | `REPORTS_EXPORT` |
| `GET /position-blocks` | `CATALOG_READ` |
| `POST /position-blocks` | `CATALOG_MANAGE` |
| `POST /position-blocks/{id}/cancel` | `CATALOG_MANAGE` |

### 10.8 ADR de numeracion

Crear `docs/decisiones/ADR-0002-numeracion-fases-b6-b7.md` con:

- contexto del conflicto;
- decision B6=ubicaciones, B7=cajas;
- consecuencias;
- referencia a `GUIA_DESARROLLO_FASES_SGA.md`;
- fecha y estado `Aceptada`.

## 11. Calidad, comandos y validacion

### 11.1 Comandos obligatorios

```powershell
Set-Location backend

uv run ruff format src tests
uv run ruff check src tests
uv run mypy src
uv run pytest tests/unit -q --no-cov
```

Con integracion:

```powershell
$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:Santi.15@localhost:5432/sga_test"
$env:TEST_REDIS_URL = "redis://localhost:6379/15"

uv run alembic upgrade head
uv run pytest tests/integration -q --no-cov -n 0
uv run pytest -q
```

### 11.2 Validacion de migracion

```powershell
uv run alembic current
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
uv run alembic current
```

Debe terminar en `20261102_0002 (head)`.

### 11.3 Validacion de OpenAPI

```powershell
uv run python -c "from judicial_archive.main import create_app; from judicial_archive.core.config import Settings; app=create_app(Settings(), configure_logs=False); schema=app.openapi(); print(len(schema['paths']))"
```

Verificar manualmente que las rutas B6 aparecen y que no hay conflictos de path.

### 11.4 Criterios de calidad

- `ruff format --check` sin cambios.
- `ruff check` sin errores.
- `mypy src` sin errores nuevos.
- Sin `xfail` en la suite.
- Sin `TODO` sin issue asociado.
- Sin imports no usados.
- Sin `except Exception` generico en servicios nuevos.
- Sin logs con datos personales.
- Sin consultas N+1 en listados paginados.
- Sin `SELECT *` en repositorios.

## 12. Criterios de aceptacion

### 12.1 Funcionales

- [ ] Se puede listar, crear, editar y cambiar estado de anaqueles.
- [ ] Se puede listar, crear, editar y cambiar estado de bandejas.
- [ ] Se puede listar, crear, editar, retirar y reactivar posiciones.
- [ ] Se puede previsualizar y aplicar capacidad.
- [ ] Se puede consultar ocupacion por area, anaquel y bandeja.
- [ ] Se puede consultar el plano con y sin posiciones.
- [ ] Se puede listar posiciones con estado derivado.
- [ ] Se puede listar cajas no ubicadas.
- [ ] Se puede escanear por numero de caja.
- [ ] Se puede escanear por posicion.
- [ ] Se puede asignar una caja con confirmacion o pendiente.
- [ ] Se puede desasignar una caja.
- [ ] Se puede trasladar de forma inmediata.
- [ ] Se puede trasladar en dos fases.
- [ ] Se puede confirmar la recepcion de un traslado.
- [ ] Se puede cancelar un traslado y restaurar el origen.
- [ ] Se puede consultar el historial de ubicacion.
- [ ] Se puede bloquear y desbloquear un rango de posiciones.
- [ ] Se puede exportar ocupacion a CSV.

### 12.2 Datos e integridad

- [ ] `box_location_history` es append-only.
- [ ] Una caja no puede estar en dos posiciones.
- [ ] Una posicion no puede tener dos cajas activas.
- [ ] `PENDING_VERIFICATION` ocupa posicion.
- [ ] `IN_TRANSIT` no ocupa posicion.
- [ ] Un solo movimiento abierto por caja.
- [ ] El downgrade falla si hay datos incompatibles.
- [ ] La migracion es reversible en una base limpia.

### 12.3 Seguridad

- [ ] Todas las rutas requieren autenticacion.
- [ ] Todas las mutaciones requieren CSRF.
- [ ] Los permisos se aplican por endpoint.
- [ ] Los reportes no filtran cajas sin permiso.
- [ ] El CSV neutraliza formulas.
- [ ] La auditoria registra actor, motivo y metadata.

### 12.4 Calidad

- [ ] `ruff` y `mypy` pasan.
- [ ] Suite completa pasa sin `xfail`.
- [ ] Documentacion actualizada.
- [ ] OpenAPI sin conflictos.
- [ ] Sin N+1 en listados paginados.
- [ ] Sin cambios en B7.

## 13. Despliegue, migracion y rollback

### 13.1 Preflight

```sql
SELECT count(*) FROM boxes WHERE current_position_id IS NOT NULL
  AND custody_status NOT IN ('IN_PLACE', 'IN_RECONCILIATION', 'PENDING_VERIFICATION');

SELECT count(*) FROM boxes WHERE current_position_id IS NULL
  AND custody_status IN ('IN_PLACE', 'IN_RECONCILIATION', 'PENDING_VERIFICATION');

SELECT count(*) FROM box_movements
  WHERE movement_status IN ('PLANNED', 'IN_TRANSIT')
  GROUP BY box_id
  HAVING count(*) > 1;
```

Cualquier resultado mayor que cero requiere plan de datos antes de migrar.

### 13.2 Despliegue

1. Backup completo de PostgreSQL.
2. Ventana de mantenimiento o modo lectura.
3. `uv run alembic upgrade head`.
4. Verificar triggers y constraints.
5. Desplegar backend.
6. Ejecutar smoke tests de asignacion, escaneo y ocupacion.
7. Monitorear errores `409` y latencia de locks.

### 13.3 Postflight

```sql
SELECT tgname FROM pg_trigger
WHERE tgrelid = 'box_location_history'::regclass
  AND NOT tgisinternal;

SELECT indexname FROM pg_indexes
WHERE tablename = 'box_location_history';

SELECT conname FROM pg_constraint
WHERE conrelid = 'boxes'::regclass
  AND conname IN ('ck_boxes_custody_position');
```

### 13.4 Rollback

- Si falla el despliegue de aplicacion, revertir solo el backend; la migracion B6 es compatible con el codigo B5 en lectura.
- Si falla la migracion, restaurar backup.
- Si se requiere downgrade, verificar primero que no existan filas con `PENDING_VERIFICATION` ni movimientos `UNASSIGN`.
- `uv run alembic downgrade -1`.
- Restaurar backup si el downgrade no es suficiente.
- No borrar datos para forzar el downgrade.

## 14. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigacion |
|---|---|---|
| Lock contention en cajas | Latencia y timeouts | Lock corto, orden estable, reintentos en cliente |
| Deadlock entre caja y posiciones | Error 500 | Orden caja -> posiciones ordenadas por UUID |
| Version obsoleta | 409 frecuente | Devolver `version` en detalle y refrescar tras mutacion |
| N+1 en plano/reportes | Lentitud | Precargar paths y cajas por lote |
| CSV injection | Ejecucion en Excel | `_csv_safe` en campos de texto |
| Historial crece sin limite | Espacio | Particionado futuro, retencion documentada |
| Trigger bloquea tests | Suite roja | Deshabilitar trigger solo en limpieza |
| Migracion bloquea tabla | Downtime | Ventana, backup, preflight |
| Numeracion B6/B7 confusa | Retrabajo | ADR y actualizacion de docs |
| Permisos demasiado amplios | Exposicion | Matriz por endpoint y pruebas 403 |

## 15. Apendices

### 15.1 Apendice A - Enums B6

| Enum | Valores nuevos |
|---|---|
| `CustodyStatus` | `PENDING_VERIFICATION` |
| `MovementType` | `UNASSIGN` |
| `TransferMode` | `IMMEDIATE`, `IN_TRANSIT` |
| `LocationState` | `CONFIRMED`, `PENDING_CONFIRMATION`, `IN_RECONCILIATION`, `ON_LOAN`, `IN_TRANSIT`, `MISSING`, `UNASSIGNED` |
| `LocationHistorySource` | `API`, `IMPORT`, `RECONCILIATION`, `SYSTEM` |
| `PositionOccupancyState` | `EMPTY`, `OCCUPIED`, `BLOCKED`, `RETIRED` |
| `ScanKind` | `BOX`, `POSITION`, `UNREGISTERED_BOX` |

### 15.2 Apendice B - Endpoints B6

| Metodo | Ruta | Permiso |
|---|---|---|
| GET | `/api/v1/areas/{area_id}/shelves` | `CATALOG_READ` |
| POST | `/api/v1/areas/{area_id}/shelves` | `CATALOG_MANAGE` |
| GET | `/api/v1/shelves/{shelf_id}` | `CATALOG_READ` |
| PATCH | `/api/v1/shelves/{shelf_id}` | `CATALOG_MANAGE` |
| POST | `/api/v1/shelves/{shelf_id}/activate` | `CATALOG_MANAGE` |
| POST | `/api/v1/shelves/{shelf_id}/deactivate` | `CATALOG_MANAGE` |
| POST | `/api/v1/shelves/{shelf_id}/capacity/preview` | `CATALOG_READ` |
| POST | `/api/v1/shelves/{shelf_id}/capacity/apply` | `CATALOG_MANAGE` |
| GET | `/api/v1/trays` | `CATALOG_READ` |
| POST | `/api/v1/trays` | `CATALOG_MANAGE` |
| GET | `/api/v1/trays/{tray_id}` | `CATALOG_READ` |
| PATCH | `/api/v1/trays/{tray_id}` | `CATALOG_MANAGE` |
| POST | `/api/v1/trays/{tray_id}/activate` | `CATALOG_MANAGE` |
| POST | `/api/v1/trays/{tray_id}/deactivate` | `CATALOG_MANAGE` |
| GET | `/api/v1/positions` | `CATALOG_READ` |
| POST | `/api/v1/positions` | `CATALOG_MANAGE` |
| GET | `/api/v1/positions/{position_id}` | `CATALOG_READ` |
| PATCH | `/api/v1/positions/{position_id}` | `CATALOG_MANAGE` |
| POST | `/api/v1/positions/{position_id}/retire` | `CATALOG_MANAGE` |
| POST | `/api/v1/positions/{position_id}/activate` | `CATALOG_MANAGE` |
| GET | `/api/v1/locations/occupancy` | `MOVEMENTS_READ` |
| GET | `/api/v1/locations/plan` | `MOVEMENTS_READ` |
| GET | `/api/v1/locations/positions` | `MOVEMENTS_READ` |
| GET | `/api/v1/locations/unlocated-boxes` | `MOVEMENTS_READ` |
| GET | `/api/v1/locations/scan` | `BOXES_READ` |
| GET | `/api/v1/locations/reports/occupancy` | `REPORTS_READ` |
| GET | `/api/v1/locations/reports/occupancy.csv` | `REPORTS_EXPORT` |
| GET | `/api/v1/locations/boxes/{box_id}` | `BOXES_READ` |
| GET | `/api/v1/locations/boxes/{box_id}/history` | `MOVEMENTS_READ` |
| POST | `/api/v1/locations/boxes/{box_id}/assign` | `MOVEMENTS_MANAGE` |
| POST | `/api/v1/locations/boxes/{box_id}/unassign` | `MOVEMENTS_MANAGE` |
| POST | `/api/v1/locations/boxes/{box_id}/transfer` | `MOVEMENTS_MANAGE` |
| POST | `/api/v1/locations/boxes/{box_id}/confirm` | `MOVEMENTS_MANAGE` |
| GET | `/api/v1/movements` | `MOVEMENTS_READ` |
| GET | `/api/v1/movements/{movement_id}` | `MOVEMENTS_READ` |
| POST | `/api/v1/movements/{movement_id}/complete` | `MOVEMENTS_MANAGE` |
| POST | `/api/v1/movements/{movement_id}/cancel` | `MOVEMENTS_MANAGE` |
| GET | `/api/v1/position-blocks` | `CATALOG_READ` |
| POST | `/api/v1/position-blocks` | `CATALOG_MANAGE` |
| POST | `/api/v1/position-blocks/{block_id}/cancel` | `CATALOG_MANAGE` |

### 15.3 Apendice C - Errores de negocio

| `details.reason` | HTTP | Significado |
|---|---|---|
| `stale_version` | 409 | Version optimista desactualizada |
| `position_occupied` | 409 | Posicion ya ocupada |
| `position_blocked` | 409 | Posicion bloqueada |
| `position_retired` | 409 | Posicion retirada |
| `box_already_located` | 409 | Caja ya tiene ubicacion |
| `box_without_location` | 409 | Caja sin ubicacion |
| `open_movement_exists` | 409 | Movimiento abierto existente |
| `invalid_transition` | 409 | Transicion de custodia invalida |
| `tray_inactive` | 409 | Bandeja inactiva |
| `shelf_inactive` | 409 | Anaquel inactivo |
| `area_inactive` | 409 | Area inactiva |
| `origin_occupied` | 409 | Origen ocupado al cancelar traslado |
| `block_already_cancelled` | 409 | Bloqueo ya cancelado |
| `box_not_active` | 403 | Caja no operativa |
| `forbidden` | 403 | Permiso insuficiente |

### 15.4 Apendice D - Definition of Done B6

- [ ] Migracion aplicada y reversible.
- [ ] Enums, modelos, constraints y triggers completos.
- [ ] Repositorios sin N+1 en listados.
- [ ] Servicios de asignacion, desasignacion y traslado completos.
- [ ] Servicios de ocupacion, plano, escaneo y reportes completos.
- [ ] Routers registrados.
- [ ] Pruebas unitarias, integracion y API en verde.
- [ ] Sin `xfail`.
- [ ] Documentacion actualizada.
- [ ] ADR de numeracion aceptada.
- [ ] Smoke test manual en entorno de staging.
- [ ] Backup y rollback probados.

### 15.5 Apendice E - Checklist de revision de PR

- [ ] No hay cambios fuera de B6.
- [ ] No se implemento CRUD de cajas.
- [ ] No se modifico B7.
- [ ] No hay secretos en codigo.
- [ ] No hay `print`.
- [ ] No hay `TODO` sin issue.
- [ ] No hay migraciones destructivas.
- [ ] No hay `DROP` sin `IF EXISTS`.
- [ ] No hay indices duplicados.
- [ ] No hay `SELECT *`.
- [ ] No hay `except Exception`.
- [ ] No hay logs con datos personales.
- [ ] No hay endpoints sin permiso.
- [ ] No hay mutaciones sin CSRF.
- [ ] No hay tests con `sleep`.
- [ ] No hay tests dependientes de orden.
- [ ] No hay tests con datos reales.

---

**Fin de la guia B6.** La implementacion debe seguir el orden de la seccion 8. Si aparece una decision no cubierta, documentarla en `docs/decisiones/` antes de codificar.
