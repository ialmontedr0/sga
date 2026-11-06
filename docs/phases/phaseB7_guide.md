# Fase B7 - Cajas, expedientes e inventario administrativo

**Version:** 1.0
**Fecha:** 2026-11-05
**Estado:** Guia de implementacion
**Depende de:** B6 - Inventario fisico y ubicaciones
**Habilita:** B8, B9, B10, B11, B12, B13 y B14
**Alcance:** Backend, PostgreSQL, Alembic, pruebas y documentacion
**Documento unico de la fase:** `docs/phases/phaseB7_guide.md`

---

## 0. Como usar esta guia

1. Leer completos `docs/AGENTS.md` y `docs/phases/GUIA_DESARROLLO_FASES_SGA.md` antes de escribir codigo.
2. Leer `docs/phases/phaseB5_guide.md` y `docs/phases/phaseB6_guide.md` para conservar convenciones de catalogos, auditoria, paginacion, permisos, errores, numeracion y ubicaciones.
3. Ejecutar los pasos en el orden indicado. No crear routers antes de la migracion, los modelos y los servicios.
4. No implementar busqueda global avanzada, prestamos, importaciones masivas, OCR, QR, conciliacion ni frontend en esta fase. Esos trabajos pertenecen a fases posteriores.
5. Toda mutacion debe registrarse en auditoria dentro de la misma transaccion que el cambio de negocio.
6. Toda correccion debe incluir una prueba de regresion. No se aceptan `xfail` nuevos ni `skip` para funcionalidad B7.
7. Los comandos se ejecutan desde `backend/` salvo que se indique otra ruta.
8. Mantener documentacion en espanol y sin datos reales, secretos ni credenciales.
9. No implementar codigo de produccion en esta guia. La guia describe exactamente que crear, donde crearlo, como probarlo y como documentarlo.

---

## 1. Resumen ejecutivo

B5 construyo los catalogos judiciales y la configuracion fisica. B6 convirtio esa configuracion en un sistema operativo de ubicaciones. B7 construye el nucleo documental:

- CRUD de cajas, expedientes, personas relacionadas, imputados y documentos administrativos.
- Alta de caja con tribunal, anio y tipo documental excluyente.
- Numeracion visible de caja mediante secuencia PostgreSQL, segura ante concurrencia.
- Creacion atomica de caja con contenido inicial.
- Validacion configurable de NUC y de identificadores de sentencia/resolucion por tribunal.
- Deteccion de duplicados y busqueda por NUC completo o por sus ultimos cinco digitos.
- Relacion de varios imputados por expediente, almacenados individualmente.
- Reglas estrictas de exclusion: una caja de expedientes no contiene documentos administrativos y una caja administrativa no contiene expedientes.
- Desactivacion, archivo, anulacion y correccion controlada con motivo, actor y valores anteriores/nuevos.
- Soporte de excepciones historicas justificadas y auditadas.
- Pruebas unitarias, API, integracion, concurrencia, migraciones y auditoria.
- Documentacion de endpoints, payloads, reglas e integridad.

B7 **no crea** una segunda tabla de cajas ni duplica la logica de ubicaciones de B6. Reutiliza `boxes`, `box_location_history`, `box_movements`, `numbering_policies`, `identifier_format_profiles`, `audit_events` y los servicios de ubicacion ya existentes.

---

## 2. Alcance y no alcance

### 2.1 Dentro de alcance

| Area | Incluido |
|---|---|
| Cajas | Listar, crear, consultar, editar metadatos, archivar, anular y corregir numero visible. |
| Contenido de caja | Crear caja con expedientes o documentos administrativos en una sola transaccion. |
| Expedientes | CRUD, busqueda por NUC, ultimos cinco digitos, tribunal, anio y caja. |
| Imputados | Personas individuales, busqueda, alta, relacion con expediente y roles. |
| Documentos administrativos | CRUD, archivo, anulacion y baja logica. |
| Numeracion | Politica configurable, secuencia PostgreSQL, `nextval`, numero visible unico y sin reutilizacion. |
| NUC | Normalizacion, perfil configurable por tribunal y periodo, excepciones auditadas. |
| Sentencia/resolucion | Validacion del identificador contra perfil `SENTENCE`, tipo de resolucion y fechas parciales. |
| Duplicados | Deteccion exacta y aproximada de NUC; deteccion de personas y relaciones duplicadas. |
| Integridad | Exposicion de tipos, FK compuesta, validacion de servicio y transacciones. |
| Correcciones | Numero de caja, NUC, sentencia, caja asociada, relaciones y datos historicos. |
| Auditoria | Eventos para altas, cambios, correcciones, archivos, anulaciones y bajas. |
| Pruebas | Unitarias, API, integracion, concurrencia, migraciones y regresion. |
| Documentacion | API, modelo de datos, reglas, pruebas, seguridad, permisos y procedimiento historico. |

### 2.2 Fuera de alcance

| Area | Fase responsable |
|---|---|
| Busqueda global combinada e indices avanzados | B8 |
| Prestamos, devoluciones y movimientos de prestamo | B9 |
| Importaciones masivas y archivos digitales | B10 |
| OCR de escaneos y manuscritos | B11 |
| Exportaciones, informes y panel de control | B12 |
| QR y codigos de barras imprimibles | B13 |
| Conciliacion de inventario fisico y digital | B14 |
| Endurecimiento final y rendimiento global | B15 |
| Frontend, plano 2D/3D y pantallas | Fases F |

B7 puede leer y actualizar `Box.current_position_id`, `Box.custody_status` solo a traves de los servicios de B6. No debe escribir directamente esos campos desde los servicios documentales.

---

## 3. Conflicto de numeracion B6/B7 y decision

Existe una inconsistencia documental real:

- `docs/AGENTS.md`, seccion 14, indica **B6 = Cajas y registros documentales** y **B7 = Ubicaciones y movimientos**.
- `docs/phases/GUIA_DESARROLLO_FASES_SGA.md` y la solicitud actual indican **B6 = Inventario fisico y ubicaciones** y **B7 = Cajas, expedientes e inventario administrativo**.

**Decision para esta guia:** se mantiene la nomenclatura de `GUIA_DESARROLLO_FASES_SGA.md`:

1. B6 es inventario fisico y ubicaciones.
2. B7 es cajas, expedientes e inventario administrativo.
3. No se renombran modulos, tablas ni rutas existentes solo por el numero de fase.
4. B7 reutiliza los servicios de ubicacion de B6 y no duplica sus reglas.
5. Registrar o actualizar una ADR de numeracion de fases. La guia B6 menciona `ADR-0002`, pero ese numero ya esta ocupado por `ADR-0002-arquitectura-modular.md`. Usar el siguiente numero disponible, por ejemplo `docs/decisiones/ADR-0012-numeracion-fases-b6-b7.md`.
6. Corregir la referencia de handoff en la documentacion de cierre sin reescribir la historia de las fases.

---

## 4. Estado de partida y brechas B7

### 4.1 Lo que ya existe

| Archivo | Estado actual |
|---|---|
| `modules/boxes/models.py` | `Box`, `BoxNumberHistory`, `BoxLocationHistory`, `BoxMovement`; tipo, numero visible, custodia, historial y movimientos. |
| `modules/boxes/schemas.py` | Solo esquemas de resumen e historial de ubicacion. |
| `modules/boxes/repositories.py` | Consultas de caja, no ubicadas e historial; no hay CRUD documental. |
| `modules/case_files/models.py` | `CaseFile`, `CaseFileIdentifierHistory`, `Person`, `CaseParty`; NUC, fechas parciales, partes e historial. |
| `modules/administrative_documents/models.py` | `AdministrativeDocument`; titulo, fecha parcial, tipo, estado y baja logica. |
| `modules/numbering/` | Politicas, creacion de secuencias, preview y activacion/desactivacion. |
| `modules/identifier_profiles/` | Perfiles de formato por tribunal, tipo y vigencia; validacion de patrones. |
| `modules/courts/` | Tribunales, tipos de resolucion, roles de parte y politicas. |
| `modules/audit/` | `record_audit_event`, modelo e inmutabilidad. |
| `modules/movements/` | Servicios de ubicacion de cajas que B7 debe reutilizar. |
| `api/v1/router.py` | Registro de routers existentes; aun no registra B7. |
| `alembic/versions/20261026_0001_initial_schema.py` | Tablas, FK compuestas, checks e indices iniciales. |
| `tests/integration/test_schema_constraints.py` | Pruebas de exclusion de tipos documentales a nivel de esquema. |
| `tests/integration/test_numbering_sequence.py` | Pruebas de politicas y secuencias B5. |

### 4.2 Brechas que B7 debe cerrar

1. No existen servicios ni routers CRUD de cajas.
2. No existe asignacion de numero visible al crear una caja.
3. No existe endpoint para crear caja y contenido en una sola transaccion.
4. No existen servicios ni routers CRUD de expedientes.
5. No existen servicios ni routers CRUD de personas y partes.
6. No existen servicios ni routers CRUD de documentos administrativos.
7. No existe validacion de NUC contra perfiles activos por tribunal y fecha.
8. No existe validacion de sentencia/resolucion contra perfiles `SENTENCE`.
9. No existe deteccion de duplicados exactos ni aproximados.
10. No existe correccion controlada de numero visible, NUC o sentencia.
11. No existe baja logica ni archivo/anulacion con motivo y auditoria.
12. No existe restriccion unica de relacion `case_file_id + person_id + party_role_id`.
13. No existen pruebas de concurrencia de numeracion de cajas.
14. No existe procedimiento documentado de correccion de datos historicos.
15. No existe documentacion de endpoints y payloads B7.

### 4.3 Baseline esperado antes de B7

Con PostgreSQL y Redis activos:

```powershell
Set-Location backend
$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:Santi.15@localhost:5432/sga_test"
$env:TEST_REDIS_URL = "redis://localhost:6379/15"
uv run pytest -q -n 0 --no-cov --tb=short
```

Referencia de cierre B6: `331 passed`. Antes de iniciar B7, el comando `uv run mypy src tests` debe devolver `Success: no issues found`. No iniciar B7 con deuda de tipado o pruebas rojas.

---

## 5. Requisitos y criterios de aceptacion

| Criterio de aceptacion | Implementacion | Prueba obligatoria |
|---|---|---|
| Un expediente no puede insertarse en una caja administrativa | FK compuesta `(box_id, box_type)` + validacion de servicio + `box_type = EXPEDIENTES` | Crear expediente con caja administrativa devuelve 422/409 y no deja fila |
| Un documento administrativo no puede insertarse en una caja de expedientes | FK compuesta + validacion de servicio + `box_type = DOCUMENTOS_ADMINISTRATIVOS` | Crear documento con caja de expedientes devuelve 422/409 y no deja fila |
| La numeracion es unica con altas concurrentes | `nextval` de PostgreSQL + `uq_boxes_visible_number` + reintento controlado | Dos o mas altas concurrentes obtienen numeros distintos |
| No se reutiliza un numero visible | Secuencia PostgreSQL y `BoxNumberHistory`; no usar `MAX + 1` | Verificar que un fallo posterior al `nextval` deja un hueco y no reutiliza el valor |
| Los imputados se buscan individualmente | `Person` + `CaseParty`; busqueda por nombre e identificacion | Crear expediente con dos imputados y buscarlos por separado |
| Las reglas de identificadores son configurables | `IdentifierFormatProfile` por tribunal, tipo y vigencia | Perfil estricto rechaza; perfil no estricto advierte; excepcion justificada se audita |
| Las excepciones historicas quedan auditadas | `verification_status = CONFLICT`, `source`, motivo y evento de auditoria | Crear NUC fuera de patron con `historical_exception=true` y verificar auditoria |
| Las operaciones parciales no dejan datos inconsistentes | Un solo `commit` por caso de uso; rollback ante cualquier fallo | Forzar fallo en contenido y verificar que no queda caja ni expediente |
| La caja no mezcla tipos documentales | Tipo inmutable y FK compuesta | Intentar cambiar tipo o insertar contenido incompatible |
| Las correcciones conservan historia | `BoxNumberHistory`, `CaseFileIdentifierHistory` y auditoria | Corregir numero/NUC y verificar historial y auditoria |
| No se borra fisicamente contenido con historia | Archivo, anulacion o baja logica | `DELETE` no ejecuta `DELETE FROM`; verificar `deleted_at` o estado |
| Los permisos se respetan | `require_permissions` por ruta | 403 para rol sin permiso y 200/201 para autorizado |
| Toda mutacion requiere CSRF | Middleware existente | Mutacion sin `X-CSRF-Token` devuelve 403 |

Ademas, B7 debe cumplir:

- toda mutacion registra actor, fecha, entidad, antes/despues y metadata cuando aplique;
- ninguna ruta devuelve modelos ORM sin esquema Pydantic;
- los errores usan el sobre `{"error": {...}}`;
- las fechas son timezone-aware en UTC para timestamps; las fechas parciales usan precision explicita;
- no se exponen datos personales innecesarios en listados;
- los identificadores NUC, sentencia y proceso se guardan como texto, nunca como entero;
- no se usan datos de produccion en pruebas.

---

## 6. Modelo de dominio

### 6.1 Entidades y responsabilidades

| Entidad | Tabla | Responsabilidad B7 |
|---|---|---|
| `Box` | `boxes` | Unidad fisica; numero visible, tribunal, anio, tipo, ciclo de vida y custodia B6. |
| `BoxNumberHistory` | `box_number_history` | Historial de cambios de numero visible. |
| `CaseFile` | `case_files` | Expediente judicial; NUC, tribunal, caja, fechas parciales, sentencia y estado. |
| `CaseFileIdentifierHistory` | `case_file_identifier_history` | Historial de valores de identificadores corregidos. |
| `Person` | `persons` | Persona individual; nombre normalizado, alias e identificacion. |
| `CaseParty` | `case_parties` | Relacion entre expediente, persona y rol de parte. |
| `AdministrativeDocument` | `administrative_documents` | Documento administrativo dentro de una caja administrativa. |
| `NumberingPolicy` | `numbering_policies` | Politica de numeracion y secuencia PostgreSQL asociada. |
| `IdentifierFormatProfile` | `identifier_format_profiles` | Patron configurable por tribunal, tipo y vigencia. |
| `AuditEvent` | `audit_events` | Trazabilidad de todas las mutaciones. |

`Person` y `CaseParty` viven actualmente en `modules/case_files/models.py`. No moverlos en B7 salvo que exista una razon tecnica comprobada. Para mantener el cambio pequeno, B7 puede exponer un router `/persons` desde el modulo `case_files` sin mover el modelo.

### 6.2 Invariantes obligatorios

1. Cada caja tiene un UUID interno estable y un `visible_number` unico.
2. `visible_number` no se reutiliza nunca, aunque una transaccion falle despues de consumir la secuencia.
3. `box_type` es excluyente: `EXPEDIENTES` o `DOCUMENTOS_ADMINISTRATIVOS`.
4. Una caja de expedientes solo puede contener `CaseFile`.
5. Una caja administrativa solo puede contener `AdministrativeDocument`.
6. Un `CaseFile` puede existir sin caja (`box_id IS NULL`), pero si tiene caja debe ser de tipo `EXPEDIENTES`.
7. Un `AdministrativeDocument` siempre pertenece a una caja de tipo `DOCUMENTOS_ADMINISTRATIVOS`.
8. `court_id`, `year`, `box_type` y `visible_number` son inmutables despues de crear contenido. Cualquier cambio exige un flujo de correccion con motivo.
9. El NUC es texto; se conserva el valor original en `nuc_raw` y la forma normalizada en `nuc_normalized`.
10. `nuc_suffix5` es una columna calculada por PostgreSQL; no se asigna desde Python.
11. Los imputados son filas individuales de `CaseParty`; no se guarda una lista separada por comas.
12. No se permite duplicar la relacion `(case_file_id, person_id, party_role_id)`.
13. Las fechas parciales usan `*_precision`; no se inventa dia o mes cuando solo se conoce el anio.
14. No se elimina fisicamente una caja con contenido, movimientos o auditoria. Se archiva o anula.
15. Expedientes y documentos usan baja logica (`deleted_at`, `deleted_by`); no se borran fisicamente.
16. Toda mutacion y toda correccion genera auditoria en la misma transaccion.
17. La creacion de caja con contenido es atomica: o se crean caja y contenido, o no se crea nada.
18. La numeracion no depende de Redis ni de un contador en memoria.
19. La validacion de servidor es autoritativa; el frontend puede advertir, pero no decide.
20. Los errores de negocio no exponen detalles internos de SQL ni rutas del servidor.

### 6.3 Exclusion de tipos documentales

La proteccion tiene tres capas:

1. **Base de datos:** `boxes` tiene `UNIQUE (id, box_type)`. `case_files` y `administrative_documents` tienen FK compuesta `(box_id, box_type) -> boxes(id, box_type)`. Ademas, `case_files` exige `box_type = 'EXPEDIENTES'` y `administrative_documents` exige `box_type = 'DOCUMENTOS_ADMINISTRATIVOS'`.
2. **Servicio:** antes de insertar, B7 carga la caja y valida `box.box_type`, `box.lifecycle_status` y que la caja no este anulada/destruida.
3. **Esquema Pydantic:** el tipo de contenido solicitado debe coincidir con el tipo de caja. La API no acepta un payload ambiguo.

Respuestas esperadas:

- caja inexistente: `404 not_found`;
- caja de tipo incorrecto: `422 validation_error` con `details.reason = "box_type_mismatch"`;
- caja archivada/anulada/destruida: `409 conflict` con `details.reason = "box_not_active"`;
- violacion de FK por carrera: `409 conflict` con `details.reason = "box_type_conflict"`.

### 6.4 Modelo de numeracion

La secuencia PostgreSQL es la fuente de verdad del proximo numero. No usar `SELECT MAX(visible_number) + 1`, no usar un contador en Redis y no bloquear toda la tabla `boxes`.

Resolucion de politica:

1. Si el payload incluye `numbering_policy_id`, usar esa politica.
2. Si no se incluye, buscar politicas activas y vigentes que apliquen al tribunal, tipo de caja y anio.
3. Elegir por especificidad: `COURT` > `BOX_TYPE` > `YEAR` > `GLOBAL`.
4. Si hay varias del mismo alcance, elegir la de `effective_from` mas reciente.
5. Si no hay politica aplicable, devolver `409 conflict` con `details.reason = "numbering_policy_not_found"`.

La asignacion se hace con:

```sql
SELECT nextval(CAST(:name AS regclass))
```

`nextval` no participa del rollback transaccional. Por eso:

- un fallo posterior puede dejar un hueco en la numeracion;
- el hueco es aceptable y no se rellena;
- nunca se reutiliza un numero;
- la unicidad se refuerza con `uq_boxes_visible_number`.

### 6.5 Validacion configurable de NUC

El NUC se normaliza sin perder el valor original:

- `nuc_raw`: texto enviado por el usuario, recortado;
- `nuc_normalized`: mayusculas, sin espacios internos, conservando guiones y ceros iniciales;
- `nuc_suffix5`: ultimos cinco caracteres de `nuc_normalized`, calculado por PostgreSQL.

Reglas:

1. Sin perfil activo: se acepta, se normaliza y queda `verification_status = PENDING`.
2. Perfil no estricto y valor que no coincide: se acepta con `verification_status = CONFLICT` y advertencia en la respuesta.
3. Perfil estricto y valor que no coincide: se rechaza con `422 validation_error`, salvo que el payload incluya una excepcion historica justificada.
4. Excepcion historica: requiere `historical_exception = true` y `exception_reason` no vacio; deja `verification_status = CONFLICT` y se audita.
5. Un perfil estricto debe tener patron y al menos tres ejemplos; B5 ya lo valida.
6. No se rechaza un expediente historico solo porque no coincide con el patron moderno. La excepcion existe precisamente para eso.
7. Los perfiles son versionados por tribunal y tipo; B5 ya impide dos perfiles activos para el mismo tribunal y tipo.

### 6.6 Validacion de sentencia o resolucion

- `resolution_number` es texto.
- Si se envia `resolution_number`, se valida contra el perfil activo `SENTENCE` del tribunal.
- Si se envia `resolution_type_id`, debe existir y estar `ACTIVE`.
- Si se conoce la fecha de sentencia (`sentence_precision != UNKNOWN`), se recomienda enviar `resolution_number`; si no se envia, el servicio registra una advertencia en la respuesta y deja `verification_status = PENDING` o `CONFLICT` segun la politica de revision.
- Las fechas parciales deben cumplir la forma declarada: `YEAR` exige anio; `MONTH` exige anio y mes; `DAY` exige anio, mes y dia; `UNKNOWN` no admite componentes.
- La validacion de formato no sustituye la revision humana. `verification_status` expresa revision, no solo formato.

### 6.7 Deteccion de duplicados

Duplicados de expediente:

- **Exacto:** mismo `court_id` y mismo `nuc_normalized`, con `deleted_at IS NULL`. Se rechaza por defecto con `409 conflict` y `details.reason = "duplicate_nuc"`.
- **Aproximado:** mismo `court_id`, mismo `year` o mismo `nuc_suffix5`. Se devuelve como candidato, no se bloquea automaticamente.
- **Override:** solo con `duplicate_override = true` y `duplicate_override_reason`; deja `verification_status = CONFLICT` y se audita.
- **Busqueda:** `GET /case-files/duplicates?nuc=...&court_id=...&year=...` devuelve coincidencias exactas y candidatos.

Duplicados de persona:

- Se detectan por `identification_number` exacto o por `normalized_name` igual.
- No se deduplica globalmente por nombre sin identificacion confiable.
- `GET /persons/duplicates?display_name=...&identification_number=...` devuelve candidatos para revision humana.

Duplicados de documento administrativo:

- Se detectan por `box_id`, `document_year` y titulo normalizado.
- Un mismo titulo y anio dentro de la misma caja se rechaza por defecto con `409` y `details.reason = "duplicate_administrative_document"`.
- B7 no implementa override para documentos administrativos; el usuario debe corregir el titulo o el anio.
- `GET /administrative-documents/duplicates?box_id=...&title=...&document_year=...` devuelve la coincidencia exacta.

### 6.8 Ciclo de vida y correcciones

Cajas:

- `ACTIVE -> ARCHIVED`: requiere motivo; no borra contenido.
- `ACTIVE -> VOIDED`: requiere motivo; no permite nuevas altas de contenido.
- `DESTROYED`: no se implementa en B7 salvo que exista un flujo legal aprobado en una fase posterior.
- No se permite archivar o anular una caja con movimientos abiertos; B6 debe validar esa condicion.
- El numero visible se corrige con `POST /boxes/{id}/number-corrections`, que escribe `BoxNumberHistory` y auditoria.
- El tipo, tribunal y anio no se corrigen por `PATCH`; si se requiere, se documenta un procedimiento excepcional con auditoria y aprobacion.

Expedientes y documentos:

- `DELETE` es baja logica: `deleted_at`, `deleted_by`, motivo en auditoria.
- `ARCHIVED` y `VOIDED` usan `lifecycle_status`, `archived_at`/`voided_at` y motivo.
- No se permite modificar un registro con `deleted_at` no nulo.
- Las correcciones de NUC o sentencia usan endpoints especificos y dejan historial.
- El cambio de caja de un expediente usa `POST /case-files/{id}/relocate`, con motivo y validacion de tipo.
- La reubicacion de documentos administrativos queda fuera de B7; no se permite cambiar `box_id` por `PATCH`.

### 6.9 Auditoria

Acciones minimas:

| Accion | Entidad |
|---|---|
| `box.created` | `box` |
| `box.updated` | `box` |
| `box.number_corrected` | `box` |
| `box.archived` | `box` |
| `box.voided` | `box` |
| `box.created_with_content` | `box` |
| `case_file.created` | `case_file` |
| `case_file.updated` | `case_file` |
| `case_file.identifier_corrected` | `case_file` |
| `case_file.relocated` | `case_file` |
| `case_file.archived` | `case_file` |
| `case_file.voided` | `case_file` |
| `case_file.deleted` | `case_file` |
| `case_party.added` | `case_party` |
| `case_party.removed` | `case_party` |
| `person.created` | `person` |
| `administrative_document.created` | `administrative_document` |
| `administrative_document.updated` | `administrative_document` |
| `administrative_document.archived` | `administrative_document` |
| `administrative_document.voided` | `administrative_document` |
| `administrative_document.deleted` | `administrative_document` |

Los snapshots de auditoria deben incluir los campos relevantes, no el objeto ORM completo. Nunca incluir tokens, contrasenas, contenido documental ni datos personales innecesarios.

### 6.10 Concurrencia y transacciones

- Numeracion: `nextval` + unique constraint. No usar locks de tabla.
- Creacion de caja con contenido: una transaccion y un solo `commit`.
- Alta de contenido en caja existente: `SELECT ... FOR UPDATE` sobre la caja para evitar archivarla/anularla mientras se agrega contenido.
- Actualizacion de caja/expediente/documento: version optimista con `expected_version` y `StaleDataError` -> `409 conflict`.
- Correcciones: lock de fila, validacion, historial y auditoria en la misma transaccion.
- Relacion de partes: lock del expediente y constraint unico para evitar duplicados concurrentes.
- Si cualquier paso falla, ejecutar `await session.rollback()` y relanzar el error de negocio.
- No llamar `commit()` desde routers, repositorios ni validadores.

---

## 7. Arquitectura y arbol de archivos

### 7.1 Principios

- Mantener la arquitectura modular de `ADR-0002`: `models/schemas/repositories/services/routers`.
- El dominio no importa FastAPI. Los servicios reciben `Request` solo para auditoria, igual que B5/B6.
- La API no contiene reglas de negocio.
- Los repositorios encapsulan SQL y locks; los servicios orquestan transacciones.
- Los validadores puros no acceden a base de datos. Las consultas de perfiles y duplicados viven en repositorios.
- No crear utilidades globales nuevas si `core/text.py`, `core/errors.py` o `core/pagination.py` ya resuelven el caso.

### 7.2 Arbol objetivo

```text
backend/
  alembic/versions/
    20261105_0002_b7_case_party_uniqueness.py        NUEVO
  src/judicial_archive/modules/
    boxes/
      schemas.py                                      AMPLIAR
      repositories.py                                 AMPLIAR
      services.py                                     NUEVO
      routers.py                                      NUEVO
    case_files/
      schemas.py                                      NUEVO
      repositories.py                                 NUEVO
      validators.py                                   NUEVO
      services.py                                     NUEVO
      routers.py                                      NUEVO
    administrative_documents/
      schemas.py                                      NUEVO
      repositories.py                                 NUEVO
      services.py                                     NUEVO
      routers.py                                      NUEVO
    numbering/
      repositores.py                                  AMPLIAR (nombre existente con typo)
      services.py                                     AMPLIAR
    api/v1/
      router.py                                       AMPLIAR
  tests/unit/
    test_nuc_normalization.py                         NUEVO
    test_identifier_validation.py                     NUEVO
    test_b7_payload_validation.py                     NUEVO
  tests/api/
    test_boxes_api.py                                 NUEVO
    test_case_files_api.py                            NUEVO
    test_administrative_documents_api.py              NUEVO
  tests/integration/
    test_b7_boxes.py                                  NUEVO
    test_b7_numbering_concurrency.py                  NUEVO
    test_b7_case_files.py                             NUEVO
    test_b7_case_parties.py                           NUEVO
    test_b7_administrative_documents.py               NUEVO
    test_b7_atomic_creation.py                        NUEVO
    test_b7_corrections_audit.py                      NUEVO
    test_b7_schema_constraints.py                     AMPLIAR O NUEVO
  docs/
    api.md                                            ACTUALIZAR
    modelo-de-datos.md                                ACTUALIZAR
    reglas-de-negocio.md                              ACTUALIZAR
    pruebas.md                                        ACTUALIZAR
    seguridad.md                                      ACTUALIZAR
    roles-y-permisos.md                               ACTUALIZAR
    decisiones/ADR-0012-numeracion-fases-b6-b7.md     NUEVO
```

No crear `modules/persons/` en B7 salvo que se decida mover `Person` y `CaseParty`. Si se mueven, actualizar todos los imports, la metadata de SQLAlchemy y las pruebas en un cambio separado. Para esta fase se recomienda no moverlos.

### 7.3 Regla de dependencias

```text
core <- db <- modules <- api
```

Dependencias permitidas:

- `boxes.services` puede importar `case_files.services` y `administrative_documents.services` para la creacion atomica.
- `case_files.services` puede importar `boxes.repositories` para validar la caja.
- `administrative_documents.services` puede importar `boxes.repositories`.
- `boxes.services` importa `numbering.services` para asignar el numero.
- Ningun modulo importa `api`.
- Los routers importan servicios y permisos, no modelos para mutar.

---

## 8. Implementacion paso a paso

### 8.1 Paso 1 - Constantes y enums

No se requieren enums nuevos. Reutilizar:

- `BoxType`
- `BoxLifecycleStatus`
- `LifecycleStatus`
- `Confidentiality`
- `VerificationStatus`
- `IdentifierKind`

Agregar en `backend/src/judicial_archive/modules/boxes/constants.py`:

```python
from __future__ import annotations

from judicial_archive.core.enums import BoxType

CONTENT_TYPE_BY_BOX_TYPE = {
    BoxType.EXPEDIENTES.value: "CASE_FILE",
    BoxType.DOCUMENTOS_ADMINISTRATIVOS.value: "ADMINISTRATIVE_DOCUMENT",
}

BOX_MUTABLE_FIELDS = frozenset({"description", "confidentiality"})
BOX_IMMUTABLE_FIELDS = frozenset({"court_id", "year", "box_type", "visible_number"})
```

No agregar `notes` a `Box` si la columna no existe. El modelo actual no tiene `notes`; usar solo `description` y `confidentiality` en B7, o agregar una migracion separada si se decide.

### 8.2 Paso 2 - Migracion Alembic

Crear una revision:

```powershell
Set-Location backend
uv run alembic heads
uv run alembic revision -m "b7 case party uniqueness"
```

Renombrar el archivo generado a:

```text
backend/alembic/versions/20261105_0002_b7_case_party_uniqueness.py
```

Usar el `down_revision` que devuelva `alembic heads`. No inventar la cadena.

Contenido de referencia:

```python
"""B7: unicidad de relaciones de partes e indices de consulta.

Revision ID: 20261105_0002
Revises: <revision_head_actual>
Create Date: 2026-11-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20261105_0002"
down_revision: str | Sequence[str] | None = "<revision_head_actual>"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_case_parties_case_person_role",
        "case_parties",
        ["case_file_id", "person_id", "party_role_id"],
        unique=True,
    )
    op.create_index(
        "ix_admin_documents_box_year",
        "administrative_documents",
        ["box_id", "document_year"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_admin_documents_box_year", table_name="administrative_documents")
    op.drop_index("uq_case_parties_case_person_role", table_name="case_parties")
```

Preflight obligatorio antes de aplicar en una base con datos:

```sql
SELECT case_file_id, person_id, party_role_id, count(*) AS total
FROM case_parties
GROUP BY case_file_id, person_id, party_role_id
HAVING count(*) > 1
ORDER BY total DESC;
```

Si hay duplicados, resolverlos antes de crear el indice. No borrar relaciones sin auditoria y sin conservar la persona/rol correcto.

No agregar en esta migracion una restriccion unica global de NUC. La deteccion exacta se hace en servicio para permitir excepciones historicas auditadas. Si en el futuro se decide una restriccion, debe ser un cambio de fase con preflight de duplicados y una politica clara para datos historicos.

Comandos:

```powershell
Set-Location backend
uv run alembic upgrade head
uv run alembic check
```

Validacion de downgrade en base de prueba:

```powershell
uv run alembic downgrade -1
uv run alembic upgrade head
```

### 8.3 Paso 3 - Esquemas Pydantic de cajas

Editar `backend/src/judicial_archive/modules/boxes/schemas.py` y agregar:

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

BoxTypeValue = Literal["EXPEDIENTES", "DOCUMENTOS_ADMINISTRATIVOS"]
ConfidentialityValue = Literal["INTERNAL", "RESTRICTED", "CONFIDENTIAL"]


class BoxCreate(BaseModel):
    court_id: UUID
    year: int = Field(ge=1, le=9999)
    box_type: BoxTypeValue
    description: str | None = Field(default=None, max_length=500)
    confidentiality: ConfidentialityValue = "INTERNAL"
    numbering_policy_id: UUID | None = None
    visible_number: str | None = Field(default=None, max_length=32)
    historical_exception: bool = False
    exception_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_historical_number(self) -> "BoxCreate":
        if self.visible_number is not None and not self.historical_exception:
            raise ValueError(
                "Un numero visible manual requiere historical_exception=true."
            )
        if self.historical_exception and not (self.exception_reason or "").strip():
            raise ValueError("La excepcion historica requiere exception_reason.")
        if self.visible_number is not None and not self.visible_number.strip():
            raise ValueError("El numero visible no puede estar vacio.")
        return self


class BoxUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=500)
    confidentiality: ConfidentialityValue | None = None
    expected_version: int = Field(ge=1)


class BoxNumberCorrection(BaseModel):
    visible_number: str = Field(min_length=1, max_length=32)
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=1)


class BoxLifecycleRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=1)


class BoxOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    visible_number: str
    court_id: UUID
    year: int
    box_type: str
    numbering_policy_id: UUID | None
    description: str | None
    confidentiality: str
    lifecycle_status: str
    custody_status: str
    current_position_id: UUID | None
    location_precision: str
    version: int
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class BoxNumberHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    box_id: UUID
    previous_number: str | None
    new_number: str
    reason: str
    changed_at: datetime
    changed_by: UUID | None


class BoxContentSummaryOut(BaseModel):
    box_id: UUID
    box_type: str
    case_file_count: int
    administrative_document_count: int
    total_count: int


class BoxWithContentCreate(BaseModel):
    box: BoxCreate
    case_files: list["CaseFileInlineCreate"] = Field(default_factory=list)
    administrative_documents: list["AdministrativeDocumentInlineCreate"] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def _validate_content_types(self) -> "BoxWithContentCreate":
        has_cases = bool(self.case_files)
        has_docs = bool(self.administrative_documents)
        if has_cases and has_docs:
            raise ValueError(
                "Una caja no puede mezclar expedientes y documentos administrativos."
            )
        if self.box.box_type == "EXPEDIENTES" and has_docs:
            raise ValueError(
                "Una caja de expedientes no admite documentos administrativos."
            )
        if self.box.box_type == "DOCUMENTOS_ADMINISTRATIVOS" and has_cases:
            raise ValueError("Una caja administrativa no admite expedientes.")
        return self


from judicial_archive.modules.case_files.schemas import CaseFileInlineCreate  # noqa: E402
from judicial_archive.modules.administrative_documents.schemas import (  # noqa: E402
    AdministrativeDocumentInlineCreate,
)

BoxWithContentCreate.model_rebuild()
```

Notas:

- Los imports al final existen para evitar ciclos de Pydantic; si se prefiere, definir los esquemas inline en `case_files/schemas.py` y `administrative_documents/schemas.py` y usar `TYPE_CHECKING`/`model_rebuild`.
- `BoxUpdate` no permite cambiar `court_id`, `year`, `box_type` ni `visible_number`.
- `expected_version` es obligatorio en mutaciones de actualizacion para evitar perdidas por concurrencia.

### 8.4 Paso 4 - Repositorio de cajas

Ampliar `backend/src/judicial_archive/modules/boxes/repositories.py`:

```python
from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.enums import MovementStatus
from judicial_archive.core.pagination import SortOrder
from judicial_archive.core.text import escape_like
from judicial_archive.modules.administrative_documents.models import (
    AdministrativeDocument,
)
from judicial_archive.modules.boxes.models import Box, BoxMovement, BoxNumberHistory
from judicial_archive.modules.case_files.models import CaseFile


class BoxRepository:
    # ... metodos existentes ...

    async def get_for_update(self, box_id: UUID) -> Box | None:
        return await self.session.scalar(
            select(Box).where(Box.id == box_id).with_for_update()
        )

    async def list_items(
        self,
        *,
        q: str | None,
        court_id: UUID | None,
        year: int | None,
        box_type: str | None,
        lifecycle_status: str | None,
        custody_status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Box], int]:
        allowed = {"visible_number", "year", "created_at", "updated_at"}
        if sort_by not in allowed:
            raise ValueError("Campo de ordenamiento no permitido.")
        conditions = []
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(Box.visible_number.ilike(pattern, escape="\\"))
        if court_id is not None:
            conditions.append(Box.court_id == court_id)
        if year is not None:
            conditions.append(Box.year == year)
        if box_type:
            conditions.append(Box.box_type == box_type)
        if lifecycle_status:
            conditions.append(Box.lifecycle_status == lifecycle_status)
        if custody_status:
            conditions.append(Box.custody_status == custody_status)

        base = select(Box).where(*conditions)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        column = getattr(Box, sort_by)
        ordering = column.asc() if order == SortOrder.ASC else column.desc()
        rows = (
            await self.session.scalars(
                base.order_by(ordering, Box.id).offset(offset).limit(limit)
            )
        ).all()
        return rows, int(total or 0)

    async def count_contents(self, box_id: UUID) -> tuple[int, int]:
        case_count = await self.session.scalar(
            select(func.count())
            .select_from(CaseFile)
            .where(CaseFile.box_id == box_id, CaseFile.deleted_at.is_(None))
        )
        doc_count = await self.session.scalar(
            select(func.count())
            .select_from(AdministrativeDocument)
            .where(
                AdministrativeDocument.box_id == box_id,
                AdministrativeDocument.deleted_at.is_(None),
            )
        )
        return int(case_count or 0), int(doc_count or 0)

    async def list_number_history(
        self, box_id: UUID, *, offset: int, limit: int
    ) -> tuple[Sequence[BoxNumberHistory], int]:
        base = select(BoxNumberHistory).where(BoxNumberHistory.box_id == box_id)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        rows = (
            await self.session.scalars(
                base.order_by(
                    BoxNumberHistory.changed_at.desc(), BoxNumberHistory.id.desc()
                )
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return rows, int(total or 0)

    async def has_open_movement(self, box_id: UUID) -> bool:
        exists = await self.session.scalar(
            select(BoxMovement.id)
            .where(
                BoxMovement.box_id == box_id,
                BoxMovement.movement_status.in_(
                    [MovementStatus.PLANNED.value, MovementStatus.IN_TRANSIT.value]
                ),
            )
            .limit(1)
        )
        return exists is not None
```

No duplicar el metodo `get_for_update` si ya existe; en el archivo actual existe y se usa para ubicaciones. Si ya esta, conservarlo y solo agregar los metodos nuevos.

### 8.5 Paso 5 - Servicio de numeracion

Ampliar `backend/src/judicial_archive/modules/numbering/repositores.py`:

```python
from datetime import date

from sqlalchemy import or_, select


class NumberingPoliciesRepository:
    # ... metodos existentes ...

    async def list_active_candidates(
        self,
        *,
        court_id: UUID,
        box_type: str,
        year: int,
        on_date: date,
    ) -> Sequence[NumberingPolicy]:
        rows = await self.session.scalars(
            select(NumberingPolicy).where(
                NumberingPolicy.is_active.is_(True),
                NumberingPolicy.effective_from <= on_date,
                or_(
                    NumberingPolicy.effective_to.is_(None),
                    NumberingPolicy.effective_to >= on_date,
                ),
                or_(
                    NumberingPolicy.scope == "GLOBAL",
                    (NumberingPolicy.scope == "COURT")
                    & (NumberingPolicy.court_id == court_id),
                    (NumberingPolicy.scope == "BOX_TYPE")
                    & (NumberingPolicy.box_type == box_type),
                    (NumberingPolicy.scope == "YEAR") & (NumberingPolicy.year == year),
                ),
            )
        )
        return rows.all()
```

Ampliar `backend/src/judicial_archive/modules/numbering/services.py`:

```python
from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import ConflictError
from judicial_archive.modules.courts.models import NumberingPolicy
from judicial_archive.modules.numbering.repositores import NumberingPoliciesRepository

_SPECIFICITY = {"COURT": 0, "BOX_TYPE": 1, "YEAR": 2, "GLOBAL": 3}


def policy_applies_to_box(
    policy: NumberingPolicy,
    *,
    court_id: UUID,
    box_type: str,
    year: int,
) -> bool:
    if policy.scope == "GLOBAL":
        return True
    if policy.scope == "COURT":
        return policy.court_id == court_id
    if policy.scope == "BOX_TYPE":
        return policy.box_type == box_type
    if policy.scope == "YEAR":
        return policy.year == year
    return False


async def resolve_numbering_policy(
    session: AsyncSession,
    *,
    court_id: UUID,
    box_type: str,
    year: int,
    policy_id: UUID | None = None,
) -> NumberingPolicy:
    repo = NumberingPoliciesRepository(session)
    today = date.today()  # noqa: DTZ011
    if policy_id is not None:
        policy = await repo.get_by_id(policy_id)
        if policy is None:
            raise ConflictError(
                "Politica de numeracion no encontrada.",
                details={"reason": "numbering_policy_not_found"},
            )
        if not policy.is_active:
            raise ConflictError(
                "La politica de numeracion esta inactiva.",
                details={"reason": "numbering_policy_inactive"},
            )
        if policy.effective_from > today or (
            policy.effective_to is not None and policy.effective_to < today
        ):
            raise ConflictError(
                "La politica de numeracion no esta vigente.",
                details={"reason": "numbering_policy_not_effective"},
            )
        if not policy_applies_to_box(
            policy, court_id=court_id, box_type=box_type, year=year
        ):
            raise ConflictError(
                "La politica de numeracion no aplica a la caja.",
                details={"reason": "numbering_policy_scope_mismatch"},
            )
        return policy

    candidates = await repo.list_active_candidates(
        court_id=court_id,
        box_type=box_type,
        year=year,
        on_date=today,
    )
    if not candidates:
        raise ConflictError(
            "No hay una politica de numeracion activa para la caja.",
            details={"reason": "numbering_policy_not_found"},
        )
    return sorted(
        candidates,
        key=lambda item: (_SPECIFICITY[item.scope], -item.effective_from.toordinal()),
    )[0]


async def allocate_visible_number(
    session: AsyncSession,
    *,
    court_id: UUID,
    box_type: str,
    year: int,
    policy_id: UUID | None = None,
) -> tuple[str, NumberingPolicy]:
    policy = await resolve_numbering_policy(
        session,
        court_id=court_id,
        box_type=box_type,
        year=year,
        policy_id=policy_id,
    )
    value = await session.scalar(
        text("SELECT nextval(CAST(:name AS regclass))"),
        {"name": policy.sequence_name},
    )
    if value is None:
        raise ConflictError(
            "No se pudo obtener el siguiente numero de caja.",
            details={"reason": "sequence_unavailable"},
        )
    return format_visible_number(policy, int(value)), policy
```

No usar `session.execute(text(...))` sin parametros. No interpolar `sequence_name` en el SQL; ya esta validado por B5, pero se mantiene el parametro para evitar inyeccion.

### 8.6 Paso 6 - Servicio de cajas

Crear `backend/src/judicial_archive/modules/boxes/services.py`. La estructura minima es:

```python
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from judicial_archive.core.enums import BoxLifecycleStatus, CourtStatus
from judicial_archive.core.errors import (
    ConflictError,
    InvalidParameterError,
    NotFoundError,
)
from judicial_archive.core.pagination import Page, PageParams, SortOrder
from judicial_archive.core.text import clean_optional_text
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.boxes import schemas
from judicial_archive.modules.boxes.models import Box, BoxNumberHistory
from judicial_archive.modules.boxes.repositories import BoxRepository
from judicial_archive.modules.courts.models import Court
from judicial_archive.modules.numbering.services import allocate_visible_number
from judicial_archive.modules.users.models import User


def _snapshot(box: Box) -> dict[str, object]:
    return {
        "visible_number": box.visible_number,
        "court_id": str(box.court_id),
        "year": box.year,
        "box_type": box.box_type,
        "description": box.description,
        "confidentiality": box.confidentiality,
        "lifecycle_status": box.lifecycle_status,
        "custody_status": box.custody_status,
        "version": box.version,
    }


async def _active_court(session: AsyncSession, court_id: UUID) -> Court:
    court = await session.get(Court, court_id)
    if court is None:
        raise NotFoundError("Tribunal no encontrado.")
    if court.status != CourtStatus.ACTIVE.value:
        raise InvalidParameterError("El tribunal esta inactivo.")
    return court


async def _insert_box(
    session: AsyncSession,
    *,
    actor: User,
    body: schemas.BoxCreate,
) -> Box:
    await _active_court(session, body.court_id)

    if body.visible_number is not None:
        visible_number = body.visible_number.strip()
        policy_id = body.numbering_policy_id
    else:
        visible_number, policy = await allocate_visible_number(
            session,
            court_id=body.court_id,
            box_type=body.box_type,
            year=body.year,
            policy_id=body.numbering_policy_id,
        )
        policy_id = policy.id

    box = Box(
        court_id=body.court_id,
        year=body.year,
        box_type=body.box_type,
        visible_number=visible_number,
        numbering_policy_id=policy_id,
        description=clean_optional_text(body.description, max_length=500),
        confidentiality=body.confidentiality,
        lifecycle_status=BoxLifecycleStatus.ACTIVE.value,
        created_by=actor.id,
    )
    session.add(box)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError(
            "Ya existe una caja con ese numero visible.",
            details={"reason": "duplicate_visible_number"},
        ) from exc
    return box


async def create_box(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.BoxCreate,
) -> schemas.BoxOut:
    try:
        box = await _insert_box(session, actor=actor, body=body)
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="box.created",
            entity_type="box",
            entity_id=box.id,
            after=_snapshot(box),
            metadata=(
                {"historical_exception": True, "reason": body.exception_reason}
                if body.historical_exception
                else None
            ),
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(box)
    return schemas.BoxOut.model_validate(box)


async def list_boxes(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    court_id: UUID | None,
    year: int | None,
    box_type: str | None,
    lifecycle_status: str | None,
    custody_status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.BoxOut]:
    rows, total = await BoxRepository(session).list_items(
        q=q,
        court_id=court_id,
        year=year,
        box_type=box_type,
        lifecycle_status=lifecycle_status,
        custody_status=custody_status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.BoxOut.model_validate(row) for row in rows]
    return Page[schemas.BoxOut].build(items, total=total, params=params)


async def get_box(session: AsyncSession, box_id: UUID) -> schemas.BoxOut:
    box = await BoxRepository(session).get(box_id)
    if box is None:
        raise NotFoundError("Caja no encontrada.")
    return schemas.BoxOut.model_validate(box)


async def update_box(
    request: Request,
    session: AsyncSession,
    actor: User,
    box_id: UUID,
    body: schemas.BoxUpdate,
) -> schemas.BoxOut:
    repo = BoxRepository(session)
    try:
        box = await repo.get_for_update(box_id)
        if box is None:
            raise NotFoundError("Caja no encontrada.")
        if box.version != body.expected_version:
            raise ConflictError(
                "La caja fue modificada por otro usuario.",
                details={"reason": "stale_version", "current_version": box.version},
            )
        before = _snapshot(box)
        changes = body.model_dump(exclude_unset=True)
        if "description" in changes:
            box.description = clean_optional_text(
                changes["description"], max_length=500
            )
        if "confidentiality" in changes and changes["confidentiality"] is not None:
            box.confidentiality = changes["confidentiality"]
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="box.updated",
            entity_type="box",
            entity_id=box.id,
            before=before,
            after=_snapshot(box),
        )
        await session.commit()
    except StaleDataError as exc:
        await session.rollback()
        raise ConflictError(
            "La caja fue modificada por otro usuario.",
            details={"reason": "stale_version"},
        ) from exc
    except Exception:
        await session.rollback()
        raise
    await session.refresh(box)
    return schemas.BoxOut.model_validate(box)


async def correct_box_number(
    request: Request,
    session: AsyncSession,
    actor: User,
    box_id: UUID,
    body: schemas.BoxNumberCorrection,
) -> schemas.BoxOut:
    repo = BoxRepository(session)
    try:
        box = await repo.get_for_update(box_id)
        if box is None:
            raise NotFoundError("Caja no encontrada.")
        if box.version != body.expected_version:
            raise ConflictError(
                "La caja fue modificada por otro usuario.",
                details={"reason": "stale_version", "current_version": box.version},
            )
        new_number = body.visible_number.strip()
        if not new_number:
            raise InvalidParameterError("El numero visible no puede estar vacio.")
        if new_number == box.visible_number:
            raise InvalidParameterError("El nuevo numero debe ser diferente al actual.")
        before = _snapshot(box)
        previous = box.visible_number
        box.visible_number = new_number
        session.add(
            BoxNumberHistory(
                box_id=box.id,
                previous_number=previous,
                new_number=new_number,
                reason=body.reason.strip(),
                changed_by=actor.id,
            )
        )
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="box.number_corrected",
            entity_type="box",
            entity_id=box.id,
            before=before,
            after=_snapshot(box),
            metadata={"reason": body.reason.strip()},
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "Ya existe una caja con ese numero visible.",
            details={"reason": "duplicate_visible_number"},
        ) from exc
    except Exception:
        await session.rollback()
        raise
    await session.refresh(box)
    return schemas.BoxOut.model_validate(box)


async def set_box_lifecycle(
    request: Request,
    session: AsyncSession,
    actor: User,
    box_id: UUID,
    *,
    target: str,
    body: schemas.BoxLifecycleRequest,
) -> schemas.BoxOut:
    if target not in {
        BoxLifecycleStatus.ARCHIVED.value,
        BoxLifecycleStatus.VOIDED.value,
    }:
        raise InvalidParameterError("Transicion de caja no permitida.")
    repo = BoxRepository(session)
    try:
        box = await repo.get_for_update(box_id)
        if box is None:
            raise NotFoundError("Caja no encontrada.")
        if box.version != body.expected_version:
            raise ConflictError(
                "La caja fue modificada por otro usuario.",
                details={"reason": "stale_version", "current_version": box.version},
            )
        if box.lifecycle_status != BoxLifecycleStatus.ACTIVE.value:
            raise ConflictError(
                "Solo una caja activa puede archivarse o anularse.",
                details={"reason": "box_not_active"},
            )
        if await repo.has_open_movement(box.id):
            raise ConflictError(
                "La caja tiene un movimiento abierto.",
                details={"reason": "open_movement_exists"},
            )
        before = _snapshot(box)
        now = datetime.now(UTC)
        if target == BoxLifecycleStatus.ARCHIVED.value:
            box.lifecycle_status = target
            box.archived_at = now
            box.archived_by = actor.id
            box.archive_reason = body.reason.strip()
            action = "box.archived"
        else:
            box.lifecycle_status = target
            box.voided_at = now
            box.voided_by = actor.id
            box.void_reason = body.reason.strip()
            action = "box.voided"
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action=action,
            entity_type="box",
            entity_id=box.id,
            before=before,
            after=_snapshot(box),
            metadata={"reason": body.reason.strip()},
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(box)
    return schemas.BoxOut.model_validate(box)
```

Notas:

- `create_box` no crea contenido. Para contenido atomico usar el paso 8.11.
- No permitir `DELETE /boxes/{id}`. La API solo expone archivo/anulacion.
- Si se implementa `notes` en `Box`, agregar la columna con migracion; no asignarla sin existir.

### 8.7 Paso 7 - Validadores de identificadores

Crear `backend/src/judicial_archive/modules/case_files/validators.py`:

```python
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.enums import IdentifierKind, VerificationStatus
from judicial_archive.core.errors import InvalidParameterError
from judicial_archive.modules.courts.models import IdentifierFormatProfile

_WHITESPACE = re.compile(r"\s+")


def normalize_identifier(value: str) -> str:
    cleaned = value.strip().upper()
    if not cleaned:
        raise InvalidParameterError("El identificador no puede estar vacio.")
    return _WHITESPACE.sub("", cleaned)


def normalize_person_name(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise InvalidParameterError("El nombre no puede estar vacio.")
    decomposed = unicodedata.normalize("NFKD", cleaned)
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return without_accents.upper()


@dataclass(frozen=True)
class IdentifierValidation:
    raw: str
    normalized: str
    verification_status: str
    profile_id: UUID | None
    warning: str | None = None


async def get_active_identifier_profile(
    session: AsyncSession,
    *,
    court_id: UUID,
    kind: str,
    on_date: date,
) -> IdentifierFormatProfile | None:
    return await session.scalar(
        select(IdentifierFormatProfile)
        .where(
            IdentifierFormatProfile.court_id == court_id,
            IdentifierFormatProfile.identifier_kind == kind,
            IdentifierFormatProfile.is_active.is_(True),
            IdentifierFormatProfile.effective_from <= on_date,
            or_(
                IdentifierFormatProfile.effective_to.is_(None),
                IdentifierFormatProfile.effective_to >= on_date,
            ),
        )
        .order_by(IdentifierFormatProfile.effective_from.desc())
        .limit(1)
    )


async def validate_identifier(
    session: AsyncSession,
    *,
    court_id: UUID,
    kind: str,
    raw_value: str,
    allow_exception: bool = False,
    exception_reason: str | None = None,
    on_date: date | None = None,
) -> IdentifierValidation:
    raw = raw_value.strip()
    normalized = normalize_identifier(raw)
    profile = await get_active_identifier_profile(
        session,
        court_id=court_id,
        kind=kind,
        on_date=on_date or date.today(),  # noqa: DTZ011
    )
    if profile is None:
        return IdentifierValidation(
            raw=raw,
            normalized=normalized,
            verification_status=VerificationStatus.PENDING.value,
            profile_id=None,
            warning="No hay perfil de identificador activo para el tribunal.",
        )

    if not profile.pattern:
        return IdentifierValidation(
            raw=raw,
            normalized=normalized,
            verification_status=VerificationStatus.PENDING.value,
            profile_id=profile.id,
            warning="El perfil activo no define patron.",
        )

    try:
        matches = re.fullmatch(profile.pattern, normalized) is not None
    except re.error as exc:
        raise InvalidParameterError(
            "El perfil de identificador contiene un patron invalido.",
            details={"profile_id": str(profile.id)},
        ) from exc

    if matches:
        return IdentifierValidation(
            raw=raw,
            normalized=normalized,
            verification_status=VerificationStatus.PENDING.value,
            profile_id=profile.id,
        )

    if profile.strict and not allow_exception:
        raise InvalidParameterError(
            "El identificador no cumple el patron configurado para el tribunal.",
            details={
                "reason": "identifier_pattern_mismatch",
                "profile_id": str(profile.id),
                "kind": kind,
                "normalized": normalized,
            },
        )

    if allow_exception and not (exception_reason or "").strip():
        raise InvalidParameterError(
            "La excepcion de identificador requiere un motivo.",
            details={"reason": "exception_reason_required"},
        )

    return IdentifierValidation(
        raw=raw,
        normalized=normalized,
        verification_status=VerificationStatus.CONFLICT.value,
        profile_id=profile.id,
        warning="El identificador no cumple el patron; se registro como excepcion.",
    )


def validate_partial_date(
    *,
    precision: str,
    year: int | None,
    month: int | None,
    day: int | None,
    field: str,
) -> None:
    valid = {"UNKNOWN", "YEAR", "MONTH", "DAY"}
    if precision not in valid:
        raise InvalidParameterError(f"Precision invalida para {field}.")
    if precision == "UNKNOWN":
        if year is not None or month is not None or day is not None:
            raise InvalidParameterError(f"{field} UNKNOWN no admite componentes.")
        return
    if year is None:
        raise InvalidParameterError(f"{field} requiere anio.")
    if precision == "YEAR":
        if month is not None or day is not None:
            raise InvalidParameterError(f"{field} YEAR no admite mes ni dia.")
        return
    if month is None:
        raise InvalidParameterError(f"{field} requiere mes.")
    if precision == "MONTH":
        if day is not None:
            raise InvalidParameterError(f"{field} MONTH no admite dia.")
        return
    if day is None:
        raise InvalidParameterError(f"{field} requiere dia.")


def identifier_kind_for_resolution() -> str:
    return IdentifierKind.SENTENCE.value
```

### 8.8 Paso 8 - Esquemas de expedientes, personas y partes

Crear `backend/src/judicial_archive/modules/case_files/schemas.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ConfidentialityValue = Literal["INTERNAL", "RESTRICTED", "CONFIDENTIAL"]
PrecisionValue = Literal["UNKNOWN", "YEAR", "MONTH", "DAY"]


class PersonCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=300)
    aliases: list[str] | None = None
    identification_type: str | None = Field(default=None, max_length=32)
    identification_number: str | None = Field(default=None, max_length=64)
    birth_year: int | None = Field(default=None, ge=1, le=9999)
    birth_month: int | None = Field(default=None, ge=1, le=12)
    birth_day: int | None = Field(default=None, ge=1, le=31)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _validate_birth_date(self) -> "PersonCreate":
        if self.birth_month is not None and self.birth_year is None:
            raise ValueError("El mes de nacimiento requiere anio.")
        if self.birth_day is not None and self.birth_month is None:
            raise ValueError("El dia de nacimiento requiere mes.")
        return self


class PersonUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=300)
    aliases: list[str] | None = None
    identification_type: str | None = Field(default=None, max_length=32)
    identification_number: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=2000)
    expected_version: int = Field(ge=1)


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    normalized_name: str
    aliases: list[str] | None
    identification_type: str | None
    identification_number: str | None
    birth_year: int | None
    birth_month: int | None
    birth_day: int | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class CasePartyCreate(BaseModel):
    person_id: UUID
    party_role_id: UUID
    is_primary: bool = False
    notes: str | None = Field(default=None, max_length=1000)


class CasePartyWithPersonCreate(BaseModel):
    person: PersonCreate
    party_role_id: UUID
    is_primary: bool = False
    notes: str | None = Field(default=None, max_length=1000)


class CasePartyUpdate(BaseModel):
    is_primary: bool | None = None
    notes: str | None = Field(default=None, max_length=1000)


class CasePartyOut(BaseModel):
    id: UUID
    case_file_id: UUID
    person: PersonOut
    party_role_id: UUID
    party_role_code: str
    party_role_name: str
    is_primary: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CaseFileInlineCreate(BaseModel):
    nuc: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=1, le=9999)
    entry_precision: PrecisionValue = "UNKNOWN"
    entry_year: int | None = Field(default=None, ge=1, le=9999)
    entry_month: int | None = Field(default=None, ge=1, le=12)
    entry_day: int | None = Field(default=None, ge=1, le=31)
    sentence_precision: PrecisionValue = "UNKNOWN"
    sentence_year: int | None = Field(default=None, ge=1, le=9999)
    sentence_month: int | None = Field(default=None, ge=1, le=12)
    sentence_day: int | None = Field(default=None, ge=1, le=31)
    resolution_type_id: UUID | None = None
    resolution_number: str | None = Field(default=None, max_length=100)
    judge_name: str | None = Field(default=None, max_length=200)
    court_name_raw: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    confidentiality: ConfidentialityValue = "INTERNAL"
    source: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=2000)
    historical_exception: bool = False
    exception_reason: str | None = Field(default=None, max_length=500)
    duplicate_override: bool = False
    duplicate_override_reason: str | None = Field(default=None, max_length=500)
    parties: list[CasePartyCreate] = Field(default_factory=list)


class CaseFileCreate(CaseFileInlineCreate):
    court_id: UUID
    box_id: UUID | None = None


class CaseFileUpdate(BaseModel):
    box_id: UUID | None = None
    change_reason: str | None = Field(default=None, max_length=500)
    entry_precision: PrecisionValue | None = None
    entry_year: int | None = Field(default=None, ge=1, le=9999)
    entry_month: int | None = Field(default=None, ge=1, le=12)
    entry_day: int | None = Field(default=None, ge=1, le=31)
    sentence_precision: PrecisionValue | None = None
    sentence_year: int | None = Field(default=None, ge=1, le=9999)
    sentence_month: int | None = Field(default=None, ge=1, le=12)
    sentence_day: int | None = Field(default=None, ge=1, le=31)
    resolution_type_id: UUID | None = None
    resolution_number: str | None = Field(default=None, max_length=100)
    judge_name: str | None = Field(default=None, max_length=200)
    court_name_raw: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    confidentiality: ConfidentialityValue | None = None
    notes: str | None = Field(default=None, max_length=2000)
    expected_version: int = Field(ge=1)


class CaseFileIdentifierCorrection(BaseModel):
    identifier_kind: Literal["NUC", "SENTENCE"]
    value: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=500)
    historical_exception: bool = False
    exception_reason: str | None = Field(default=None, max_length=500)
    expected_version: int = Field(ge=1)


class CaseFileRelocate(BaseModel):
    box_id: UUID
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=1)


class CaseFileLifecycleRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=1)


class CaseFileDeleteRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=1)


class CaseFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    court_id: UUID
    box_id: UUID | None
    box_type: str
    nuc_raw: str
    nuc_normalized: str
    nuc_suffix5: str
    year: int
    entry_precision: str
    entry_year: int | None
    entry_month: int | None
    entry_day: int | None
    sentence_precision: str
    sentence_year: int | None
    sentence_month: int | None
    sentence_day: int | None
    resolution_type_id: UUID | None
    resolution_number: str | None
    judge_name: str | None
    court_name_raw: str | None
    description: str | None
    verification_status: str
    confidentiality: str
    lifecycle_status: str
    source: str | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class CaseFileDetailOut(CaseFileOut):
    parties: list[CasePartyOut]
    warnings: list[str] = Field(default_factory=list)


class DuplicateCaseFileOut(BaseModel):
    id: UUID
    nuc_raw: str
    nuc_normalized: str
    nuc_suffix5: str
    court_id: UUID
    year: int
    box_id: UUID | None
    match_type: Literal["EXACT", "SUFFIX5", "SAME_YEAR"]
    verification_status: str


class DuplicatePersonOut(BaseModel):
    id: UUID
    display_name: str
    normalized_name: str
    identification_number: str | None
    match_type: Literal["IDENTIFICATION", "NAME"]
```

Notas:

- `CaseFileUpdate` no permite cambiar `nuc_raw`, `nuc_normalized`, `court_id` ni `year`.
- `CaseFileUpdate.box_id` se acepta, pero si cambia debe exigir `change_reason`.
- `expected_version` es obligatorio.
- `CaseFileInlineCreate` no incluye `court_id` ni `box_id` porque se toman del contenedor.
- `parties` en el alta usa `CasePartyCreate`; para crear personas nuevas en el mismo payload se puede usar un endpoint separado o `CasePartyWithPersonCreate` en la ruta de partes.

### 8.9 Paso 9 - Repositorio de expedientes, personas y partes

Crear `backend/src/judicial_archive/modules/case_files/repositories.py`:

```python
from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.pagination import SortOrder
from judicial_archive.core.text import escape_like
from judicial_archive.modules.case_files.models import CaseFile, CaseParty, Person
from judicial_archive.modules.courts.models import PartyRole


class CaseFileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, case_file_id: UUID) -> CaseFile | None:
        return await self.session.get(CaseFile, case_file_id)

    async def get_for_update(self, case_file_id: UUID) -> CaseFile | None:
        return await self.session.scalar(
            select(CaseFile)
            .where(CaseFile.id == case_file_id, CaseFile.deleted_at.is_(None))
            .with_for_update()
        )

    async def find_exact_nuc(
        self,
        *,
        court_id: UUID,
        nuc_normalized: str,
        exclude_id: UUID | None = None,
    ) -> CaseFile | None:
        conditions = [
            CaseFile.court_id == court_id,
            CaseFile.nuc_normalized == nuc_normalized,
            CaseFile.deleted_at.is_(None),
        ]
        if exclude_id is not None:
            conditions.append(CaseFile.id != exclude_id)
        return await self.session.scalar(select(CaseFile).where(*conditions).limit(1))

    async def list_duplicates(
        self,
        *,
        court_id: UUID,
        nuc_normalized: str,
        year: int,
        limit: int = 20,
    ) -> Sequence[tuple[CaseFile, str]]:
        suffix5 = nuc_normalized[-5:]
        rows = await self.session.execute(
            select(CaseFile)
            .where(
                CaseFile.court_id == court_id,
                CaseFile.deleted_at.is_(None),
                or_(
                    CaseFile.nuc_normalized == nuc_normalized,
                    CaseFile.nuc_suffix5 == suffix5,
                    CaseFile.year == year,
                ),
            )
            .order_by(CaseFile.year.desc(), CaseFile.created_at.desc())
            .limit(limit)
        )
        result: list[tuple[CaseFile, str]] = []
        for row in rows.scalars().all():
            if row.nuc_normalized == nuc_normalized:
                match_type = "EXACT"
            elif row.nuc_suffix5 == suffix5:
                match_type = "SUFFIX5"
            else:
                match_type = "SAME_YEAR"
            result.append((row, match_type))
        return result

    async def list_items(
        self,
        *,
        q: str | None,
        court_id: UUID | None,
        box_id: UUID | None,
        year: int | None,
        lifecycle_status: str | None,
        verification_status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[CaseFile], int]:
        allowed = {"year", "nuc_normalized", "created_at", "updated_at"}
        if sort_by not in allowed:
            raise ValueError("Campo de ordenamiento no permitido.")
        conditions = [CaseFile.deleted_at.is_(None)]
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(
                or_(
                    CaseFile.nuc_normalized.ilike(pattern, escape="\\"),
                    CaseFile.nuc_suffix5.ilike(pattern, escape="\\"),
                    CaseFile.resolution_number.ilike(pattern, escape="\\"),
                )
            )
        if court_id is not None:
            conditions.append(CaseFile.court_id == court_id)
        if box_id is not None:
            conditions.append(CaseFile.box_id == box_id)
        if year is not None:
            conditions.append(CaseFile.year == year)
        if lifecycle_status:
            conditions.append(CaseFile.lifecycle_status == lifecycle_status)
        if verification_status:
            conditions.append(CaseFile.verification_status == verification_status)

        base = select(CaseFile).where(*conditions)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        column = getattr(CaseFile, sort_by)
        ordering = column.asc() if order == SortOrder.ASC else column.desc()
        rows = (
            await self.session.scalars(
                base.order_by(ordering, CaseFile.id).offset(offset).limit(limit)
            )
        ).all()
        return rows, int(total or 0)


class PersonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, person_id: UUID) -> Person | None:
        return await self.session.get(Person, person_id)

    async def get_for_update(self, person_id: UUID) -> Person | None:
        return await self.session.scalar(
            select(Person)
            .where(Person.id == person_id, Person.deleted_at.is_(None))
            .with_for_update()
        )

    async def find_exact_identification(
        self, identification_number: str
    ) -> Person | None:
        return await self.session.scalar(
            select(Person)
            .where(
                Person.identification_number == identification_number,
                Person.deleted_at.is_(None),
            )
            .limit(1)
        )

    async def list_items(
        self,
        *,
        q: str | None,
        identification_number: str | None,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Person], int]:
        conditions = [Person.deleted_at.is_(None)]
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(Person.normalized_name.ilike(pattern, escape="\\"))
        if identification_number:
            conditions.append(
                Person.identification_number == identification_number.strip()
            )
        base = select(Person).where(*conditions)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        rows = (
            await self.session.scalars(
                base.order_by(Person.normalized_name.asc(), Person.id.asc())
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return rows, int(total or 0)

    async def list_duplicates(
        self,
        *,
        normalized_name: str,
        identification_number: str | None,
        limit: int = 20,
    ) -> Sequence[tuple[Person, str]]:
        conditions = [Person.deleted_at.is_(None)]
        if identification_number:
            conditions.append(
                or_(
                    Person.identification_number == identification_number,
                    Person.normalized_name == normalized_name,
                )
            )
        else:
            conditions.append(Person.normalized_name == normalized_name)
        rows = (
            await self.session.scalars(
                select(Person)
                .where(*conditions)
                .order_by(Person.created_at.desc())
                .limit(limit)
            )
        ).all()
        result: list[tuple[Person, str]] = []
        for person in rows:
            if (
                identification_number
                and person.identification_number == identification_number
            ):
                result.append((person, "IDENTIFICATION"))
            else:
                result.append((person, "NAME"))
        return result


class CasePartyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, party_id: UUID) -> CaseParty | None:
        return await self.session.get(CaseParty, party_id)

    async def find_relation(
        self,
        *,
        case_file_id: UUID,
        person_id: UUID,
        party_role_id: UUID,
    ) -> CaseParty | None:
        return await self.session.scalar(
            select(CaseParty).where(
                CaseParty.case_file_id == case_file_id,
                CaseParty.person_id == person_id,
                CaseParty.party_role_id == party_role_id,
            )
        )

    async def list_for_case(
        self, case_file_id: UUID
    ) -> Sequence[tuple[CaseParty, Person, PartyRole]]:
        rows = await self.session.execute(
            select(CaseParty, Person, PartyRole)
            .join(Person, Person.id == CaseParty.person_id)
            .join(PartyRole, PartyRole.id == CaseParty.party_role_id)
            .where(CaseParty.case_file_id == case_file_id)
            .order_by(CaseParty.is_primary.desc(), Person.normalized_name.asc())
        )
        return rows.all()

    async def count_primary_for_case(self, case_file_id: UUID) -> int:
        total = await self.session.scalar(
            select(func.count())
            .select_from(CaseParty)
            .where(
                CaseParty.case_file_id == case_file_id, CaseParty.is_primary.is_(True)
            )
        )
        return int(total or 0)
```

### 8.10 Paso 10 - Servicio de expedientes, personas y partes

Crear `backend/src/judicial_archive/modules/case_files/services.py`. La implementacion debe separar:

- `prepare_case_file`: valida y devuelve un `CaseFile` sin `commit`.
- `create_case_file`: llama a `prepare_case_file`, registra auditoria y hace `commit`.
- `create_case_file_in_box`: variante usada por la creacion atomica de caja.
- `add_party` / `add_party_with_person`.
- `correct_identifier`, `relocate`, `archive`, `void`, `soft_delete`.

Fragmento de referencia:

```python
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from judicial_archive.core.enums import (
    BoxLifecycleStatus,
    BoxType,
    LifecycleStatus,
    VerificationStatus,
)
from judicial_archive.core.errors import (
    ConflictError,
    InvalidParameterError,
    NotFoundError,
)
from judicial_archive.core.pagination import Page, PageParams, SortOrder
from judicial_archive.core.text import clean_optional_text
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.boxes.repositories import BoxRepository
from judicial_archive.modules.case_files import schemas
from judicial_archive.modules.case_files.models import (
    CaseFile,
    CaseFileIdentifierHistory,
    CaseParty,
    Person,
)
from judicial_archive.modules.case_files.repositories import (
    CaseFileRepository,
    CasePartyRepository,
    PersonRepository,
)
from judicial_archive.modules.case_files.validators import (
    normalize_person_name,
    validate_identifier,
    validate_partial_date,
)
from judicial_archive.modules.courts.models import PartyRole, ResolutionType
from judicial_archive.modules.users.models import User


def _case_snapshot(case_file: CaseFile) -> dict[str, object]:
    return {
        "court_id": str(case_file.court_id),
        "box_id": str(case_file.box_id) if case_file.box_id else None,
        "nuc_raw": case_file.nuc_raw,
        "nuc_normalized": case_file.nuc_normalized,
        "year": case_file.year,
        "resolution_number": case_file.resolution_number,
        "verification_status": case_file.verification_status,
        "lifecycle_status": case_file.lifecycle_status,
        "version": case_file.version,
    }


async def _validate_box_for_content(
    session: AsyncSession,
    *,
    box_id: UUID,
    expected_type: str,
    lock: bool = True,
) -> Box:
    repo = BoxRepository(session)
    box = await repo.get_for_update(box_id) if lock else await repo.get(box_id)
    if box is None:
        raise NotFoundError("Caja no encontrada.")
    if box.lifecycle_status != BoxLifecycleStatus.ACTIVE.value:
        raise ConflictError(
            "La caja no esta activa.",
            details={"reason": "box_not_active"},
        )
    if box.box_type != expected_type:
        raise InvalidParameterError(
            "El tipo de caja no coincide con el contenido.",
            details={"reason": "box_type_mismatch"},
        )
    return box


async def _validate_resolution(
    session: AsyncSession,
    *,
    court_id: UUID,
    body: schemas.CaseFileInlineCreate,
) -> None:
    if body.resolution_type_id is not None:
        resolution = await session.get(ResolutionType, body.resolution_type_id)
        if resolution is None:
            raise NotFoundError("Tipo de resolucion no encontrado.")
        if resolution.status != "ACTIVE":
            raise InvalidParameterError("El tipo de resolucion esta inactivo.")

    if body.resolution_number:
        await validate_identifier(
            session,
            court_id=court_id,
            kind="SENTENCE",
            raw_value=body.resolution_number,
            allow_exception=body.historical_exception,
            exception_reason=body.exception_reason,
        )

    validate_partial_date(
        precision=body.entry_precision,
        year=body.entry_year,
        month=body.entry_month,
        day=body.entry_day,
        field="entry",
    )
    validate_partial_date(
        precision=body.sentence_precision,
        year=body.sentence_year,
        month=body.sentence_month,
        day=body.sentence_day,
        field="sentence",
    )


async def prepare_case_file(
    session: AsyncSession,
    *,
    actor: User,
    court_id: UUID,
    box_id: UUID | None,
    body: schemas.CaseFileInlineCreate,
    box: Box | None = None,
) -> tuple[CaseFile, list[str]]:
    warnings: list[str] = []
    if box is not None:
        if box.id != box_id:
            raise InvalidParameterError("La caja no coincide con el contenido.")
        if box.lifecycle_status != BoxLifecycleStatus.ACTIVE.value:
            raise ConflictError(
                "La caja no esta activa.", details={"reason": "box_not_active"}
            )
        if box.box_type != BoxType.EXPEDIENTES.value:
            raise InvalidParameterError(
                "Un expediente solo puede pertenecer a una caja de expedientes.",
                details={"reason": "box_type_mismatch"},
            )
    elif box_id is not None:
        await _validate_box_for_content(
            session,
            box_id=box_id,
            expected_type=BoxType.EXPEDIENTES.value,
        )

    await _validate_resolution(session, court_id=court_id, body=body)

    nuc = await validate_identifier(
        session,
        court_id=court_id,
        kind="NUC",
        raw_value=body.nuc,
        allow_exception=body.historical_exception,
        exception_reason=body.exception_reason,
    )
    if nuc.warning:
        warnings.append(nuc.warning)

    repo = CaseFileRepository(session)
    duplicate = await repo.find_exact_nuc(
        court_id=court_id,
        nuc_normalized=nuc.normalized,
    )
    if duplicate is not None:
        if not body.duplicate_override:
            raise ConflictError(
                "Ya existe un expediente con el mismo NUC en el tribunal.",
                details={
                    "reason": "duplicate_nuc",
                    "case_file_id": str(duplicate.id),
                },
            )
        if not (body.duplicate_override_reason or "").strip():
            raise InvalidParameterError(
                "La excepcion de duplicado requiere motivo.",
                details={"reason": "duplicate_override_reason_required"},
            )
        warnings.append("Se registro un NUC duplicado como excepcion auditada.")

    verification_status = nuc.verification_status
    if duplicate is not None:
        verification_status = VerificationStatus.CONFLICT.value

    case_file = CaseFile(
        court_id=court_id,
        box_id=box_id,
        box_type=BoxType.EXPEDIENTES.value,
        nuc_raw=nuc.raw,
        nuc_normalized=nuc.normalized,
        year=body.year,
        entry_precision=body.entry_precision,
        entry_year=body.entry_year,
        entry_month=body.entry_month,
        entry_day=body.entry_day,
        sentence_precision=body.sentence_precision,
        sentence_year=body.sentence_year,
        sentence_month=body.sentence_month,
        sentence_day=body.sentence_day,
        resolution_type_id=body.resolution_type_id,
        resolution_number=clean_optional_text(body.resolution_number, max_length=100),
        judge_name=clean_optional_text(body.judge_name, max_length=200),
        court_name_raw=clean_optional_text(body.court_name_raw, max_length=200),
        description=clean_optional_text(body.description, max_length=1000),
        verification_status=verification_status,
        confidentiality=body.confidentiality,
        lifecycle_status=LifecycleStatus.ACTIVE.value,
        source=clean_optional_text(body.source, max_length=32),
        notes=clean_optional_text(body.notes, max_length=2000),
        created_by=actor.id,
    )
    session.add(case_file)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError(
            "No se pudo crear el expediente por una restriccion de integridad.",
            details={"reason": "case_file_integrity_conflict"},
        ) from exc

    session.add(
        CaseFileIdentifierHistory(
            case_file_id=case_file.id,
            identifier_kind="NUC",
            value_raw=nuc.raw,
            value_normalized=nuc.normalized,
            is_primary=True,
            reason="Alta inicial del expediente.",
            changed_by=actor.id,
        )
    )

    for party in body.parties:
        await _prepare_party(
            session,
            case_file_id=case_file.id,
            body=party,
            actor=actor,
        )

    return case_file, warnings
```

La funcion `_prepare_party` debe validar persona, rol activo y duplicado de relacion:

```python
async def _prepare_party(
    session: AsyncSession,
    *,
    case_file_id: UUID,
    body: schemas.CasePartyCreate,
    actor: User,
) -> CaseParty:
    person = await PersonRepository(session).get(body.person_id)
    if person is None or person.deleted_at is not None:
        raise NotFoundError("Persona no encontrada.")
    role = await session.get(PartyRole, body.party_role_id)
    if role is None:
        raise NotFoundError("Rol de parte no encontrado.")
    if role.status != "ACTIVE":
        raise InvalidParameterError("El rol de parte esta inactivo.")

    repo = CasePartyRepository(session)
    existing = await repo.find_relation(
        case_file_id=case_file_id,
        person_id=body.person_id,
        party_role_id=body.party_role_id,
    )
    if existing is not None:
        raise ConflictError(
            "La persona ya esta relacionada con ese rol en el expediente.",
            details={"reason": "duplicate_case_party"},
        )
    if body.is_primary and await repo.count_primary_for_case(case_file_id) > 0:
        raise ConflictError(
            "El expediente ya tiene una parte principal.",
            details={"reason": "primary_party_exists"},
        )

    party = CaseParty(
        case_file_id=case_file_id,
        person_id=body.person_id,
        party_role_id=body.party_role_id,
        is_primary=body.is_primary,
        notes=clean_optional_text(body.notes, max_length=1000),
        created_by=actor.id,
    )
    session.add(party)
    await session.flush()
    return party
```

`create_case_file` publico:

```python
async def create_case_file(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.CaseFileCreate,
) -> schemas.CaseFileDetailOut:
    try:
        case_file, warnings = await prepare_case_file(
            session,
            actor=actor,
            court_id=body.court_id,
            box_id=body.box_id,
            body=body,
        )
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="case_file.created",
            entity_type="case_file",
            entity_id=case_file.id,
            after=_case_snapshot(case_file),
            metadata={
                "warnings": warnings,
                "historical_exception": body.historical_exception,
                "exception_reason": body.exception_reason,
                "duplicate_override": body.duplicate_override,
                "duplicate_override_reason": body.duplicate_override_reason,
            },
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(case_file)
    return await get_case_file_detail(session, case_file.id, warnings=warnings)
```

La creacion atomica de caja usara `prepare_case_file(..., box=box, body=inline)` y no llamara a `create_case_file` para evitar commits intermedios.

Continuacion de `services.py`:

```python
def _party_out(
    party: CaseParty,
    person: Person,
    role: PartyRole,
) -> schemas.CasePartyOut:
    return schemas.CasePartyOut(
        id=party.id,
        case_file_id=party.case_file_id,
        person=schemas.PersonOut.model_validate(person),
        party_role_id=role.id,
        party_role_code=role.code,
        party_role_name=role.name,
        is_primary=party.is_primary,
        notes=party.notes,
        created_at=party.created_at,
        updated_at=party.updated_at,
    )


async def get_case_file_detail(
    session: AsyncSession,
    case_file_id: UUID,
    *,
    warnings: list[str] | None = None,
) -> schemas.CaseFileDetailOut:
    case_file = await CaseFileRepository(session).get(case_file_id)
    if case_file is None or case_file.deleted_at is not None:
        raise NotFoundError("Expediente no encontrado.")
    rows = await CasePartyRepository(session).list_for_case(case_file.id)
    base = schemas.CaseFileOut.model_validate(case_file)
    return schemas.CaseFileDetailOut(
        **base.model_dump(),
        parties=[_party_out(party, person, role) for party, person, role in rows],
        warnings=warnings or [],
    )


async def list_case_files(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    court_id: UUID | None,
    box_id: UUID | None,
    year: int | None,
    lifecycle_status: str | None,
    verification_status: str | None,
    sort_by: str,
    order: SortOrder,
) -> Page[schemas.CaseFileOut]:
    rows, total = await CaseFileRepository(session).list_items(
        q=q,
        court_id=court_id,
        box_id=box_id,
        year=year,
        lifecycle_status=lifecycle_status,
        verification_status=verification_status,
        sort_by=sort_by,
        order=order,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.CaseFileOut.model_validate(row) for row in rows]
    return Page[schemas.CaseFileOut].build(items, total=total, params=params)


async def get_case_file(
    session: AsyncSession,
    case_file_id: UUID,
) -> schemas.CaseFileDetailOut:
    return await get_case_file_detail(session, case_file_id)


async def update_case_file(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CaseFileUpdate,
) -> schemas.CaseFileDetailOut:
    repo = CaseFileRepository(session)
    try:
        case_file = await repo.get_for_update(case_file_id)
        if case_file is None:
            raise NotFoundError("Expediente no encontrado.")
        if case_file.version != body.expected_version:
            raise ConflictError(
                "El expediente fue modificado por otro usuario.",
                details={
                    "reason": "stale_version",
                    "current_version": case_file.version,
                },
            )
        if case_file.lifecycle_status == LifecycleStatus.VOIDED.value:
            raise ConflictError(
                "Un expediente anulado no puede modificarse.",
                details={"reason": "case_file_voided"},
            )

        before = _case_snapshot(case_file)
        changes = body.model_dump(exclude_unset=True)
        changes.pop("expected_version", None)

        if "box_id" in changes:
            new_box_id = changes["box_id"]
            if new_box_id != case_file.box_id:
                if not (body.change_reason or "").strip():
                    raise InvalidParameterError(
                        "El cambio de caja requiere motivo.",
                        details={"reason": "change_reason_required"},
                    )
                if new_box_id is not None:
                    await _validate_box_for_content(
                        session,
                        box_id=new_box_id,
                        expected_type=BoxType.EXPEDIENTES.value,
                    )
                case_file.box_id = new_box_id
                case_file.box_type = BoxType.EXPEDIENTES.value

        if (
            "resolution_type_id" in changes
            and changes["resolution_type_id"] is not None
        ):
            resolution = await session.get(
                ResolutionType, changes["resolution_type_id"]
            )
            if resolution is None:
                raise NotFoundError("Tipo de resolucion no encontrado.")
            if resolution.status != "ACTIVE":
                raise InvalidParameterError("El tipo de resolucion esta inactivo.")

        if "resolution_number" in changes:
            raw_resolution = changes["resolution_number"]
            previous_resolution = case_file.resolution_number
            if raw_resolution:
                sentence = await validate_identifier(
                    session,
                    court_id=case_file.court_id,
                    kind="SENTENCE",
                    raw_value=raw_resolution,
                )
                case_file.resolution_number = sentence.normalized
                if previous_resolution != sentence.normalized:
                    session.add(
                        CaseFileIdentifierHistory(
                            case_file_id=case_file.id,
                            identifier_kind="SENTENCE",
                            value_raw=sentence.raw,
                            value_normalized=sentence.normalized,
                            is_primary=False,
                            reason=(
                                body.change_reason or "Actualizacion de resolucion"
                            ).strip(),
                            changed_by=actor.id,
                        )
                    )
            else:
                case_file.resolution_number = None

        for field in (
            "entry_precision",
            "entry_year",
            "entry_month",
            "entry_day",
            "sentence_precision",
            "sentence_year",
            "sentence_month",
            "sentence_day",
        ):
            if field in changes:
                setattr(case_file, field, changes[field])

        for field in ("resolution_type_id", "judge_name", "court_name_raw", "notes"):
            if field in changes:
                setattr(
                    case_file,
                    field,
                    clean_optional_text(changes[field])
                    if field != "resolution_type_id"
                    else changes[field],
                )
        if "description" in changes:
            case_file.description = clean_optional_text(
                changes["description"], max_length=1000
            )
        if "confidentiality" in changes and changes["confidentiality"] is not None:
            case_file.confidentiality = changes["confidentiality"]

        validate_partial_date(
            precision=case_file.entry_precision,
            year=case_file.entry_year,
            month=case_file.entry_month,
            day=case_file.entry_day,
            field="entry",
        )
        validate_partial_date(
            precision=case_file.sentence_precision,
            year=case_file.sentence_year,
            month=case_file.sentence_month,
            day=case_file.sentence_day,
            field="sentence",
        )
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="case_file.updated",
            entity_type="case_file",
            entity_id=case_file.id,
            before=before,
            after=_case_snapshot(case_file),
            metadata={"change_reason": body.change_reason},
        )
        await session.commit()
    except StaleDataError as exc:
        await session.rollback()
        raise ConflictError(
            "El expediente fue modificado por otro usuario.",
            details={"reason": "stale_version"},
        ) from exc
    except Exception:
        await session.rollback()
        raise
    await session.refresh(case_file)
    return await get_case_file_detail(session, case_file.id)


async def add_party(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CasePartyCreate,
) -> schemas.CasePartyOut:
    try:
        case_file = await CaseFileRepository(session).get_for_update(case_file_id)
        if case_file is None:
            raise NotFoundError("Expediente no encontrado.")
        if case_file.lifecycle_status == LifecycleStatus.VOIDED.value:
            raise ConflictError("Un expediente anulado no admite partes.")
        party = await _prepare_party(
            session,
            case_file_id=case_file.id,
            body=body,
            actor=actor,
        )
        party_id = party.id
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="case_party.added",
            entity_type="case_party",
            entity_id=party.id,
            after={
                "case_file_id": str(case_file_id),
                "person_id": str(party.person_id),
                "party_role_id": str(party.party_role_id),
                "is_primary": party.is_primary,
            },
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    rows = await CasePartyRepository(session).list_for_case(case_file_id)
    for party, person, role in rows:
        if party.id == party_id:
            return _party_out(party, person, role)
    raise NotFoundError("Parte no encontrada.")


async def add_party_with_person(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CasePartyWithPersonCreate,
) -> schemas.CasePartyOut:
    person_repo = PersonRepository(session)
    try:
        case_file = await CaseFileRepository(session).get_for_update(case_file_id)
        if case_file is None:
            raise NotFoundError("Expediente no encontrado.")
        if case_file.lifecycle_status == LifecycleStatus.VOIDED.value:
            raise ConflictError("Un expediente anulado no admite partes.")

        normalized_name = normalize_person_name(body.person.display_name)
        identification = clean_optional_text(
            body.person.identification_number, max_length=64
        )
        if identification:
            identification = identification.strip().upper()
            existing = await person_repo.find_exact_identification(identification)
            if existing is not None:
                raise ConflictError(
                    "Ya existe una persona con ese numero de identificacion.",
                    details={
                        "reason": "duplicate_person",
                        "person_id": str(existing.id),
                    },
                )

        person = Person(
            display_name=" ".join(body.person.display_name.strip().split()),
            normalized_name=normalized_name,
            aliases=body.person.aliases,
            identification_type=clean_optional_text(body.person.identification_type),
            identification_number=identification,
            birth_year=body.person.birth_year,
            birth_month=body.person.birth_month,
            birth_day=body.person.birth_day,
            notes=clean_optional_text(body.person.notes, max_length=2000),
            created_by=actor.id,
        )
        session.add(person)
        await session.flush()

        party_body = schemas.CasePartyCreate(
            person_id=person.id,
            party_role_id=body.party_role_id,
            is_primary=body.is_primary,
            notes=body.notes,
        )
        party = await _prepare_party(
            session,
            case_file_id=case_file.id,
            body=party_body,
            actor=actor,
        )
        person_id = person.id
        party_id = party.id
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="person.created",
            entity_type="person",
            entity_id=person.id,
            after={
                "display_name": person.display_name,
                "normalized_name": person.normalized_name,
            },
        )
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="case_party.added",
            entity_type="case_party",
            entity_id=party.id,
            after={
                "case_file_id": str(case_file.id),
                "person_id": str(person.id),
                "party_role_id": str(party.party_role_id),
            },
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    rows = await CasePartyRepository(session).list_for_case(case_file_id)
    for party, person, role in rows:
        if party.id == party_id and party.person_id == person_id:
            return _party_out(party, person, role)
    raise NotFoundError("Parte no encontrada.")


async def remove_party(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    party_id: UUID,
) -> None:
    repo = CasePartyRepository(session)
    try:
        case_file = await CaseFileRepository(session).get_for_update(case_file_id)
        if case_file is None:
            raise NotFoundError("Expediente no encontrado.")
        if case_file.lifecycle_status == LifecycleStatus.VOIDED.value:
            raise ConflictError("Un expediente anulado no admite cambios de partes.")
        party = await repo.get(party_id)
        if party is None or party.case_file_id != case_file_id:
            raise NotFoundError("Parte no encontrada.")
        before = {
            "person_id": str(party.person_id),
            "party_role_id": str(party.party_role_id),
            "is_primary": party.is_primary,
        }
        await session.delete(party)
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="case_party.removed",
            entity_type="case_party",
            entity_id=party_id,
            before=before,
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
```

`correct_identifier`:

```python
async def correct_identifier(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CaseFileIdentifierCorrection,
) -> schemas.CaseFileDetailOut:
    repo = CaseFileRepository(session)
    try:
        case_file = await repo.get_for_update(case_file_id)
        if case_file is None:
            raise NotFoundError("Expediente no encontrado.")
        if case_file.version != body.expected_version:
            raise ConflictError(
                "El expediente fue modificado por otro usuario.",
                details={
                    "reason": "stale_version",
                    "current_version": case_file.version,
                },
            )
        if case_file.lifecycle_status == LifecycleStatus.VOIDED.value:
            raise ConflictError(
                "Un expediente anulado no admite correcciones.",
                details={"reason": "case_file_voided"},
            )
        before = _case_snapshot(case_file)
        if body.identifier_kind == "NUC":
            validation = await validate_identifier(
                session,
                court_id=case_file.court_id,
                kind="NUC",
                raw_value=body.value,
                allow_exception=body.historical_exception,
                exception_reason=body.exception_reason,
            )
            duplicate = await repo.find_exact_nuc(
                court_id=case_file.court_id,
                nuc_normalized=validation.normalized,
                exclude_id=case_file.id,
            )
            if duplicate is not None:
                raise ConflictError(
                    "Ya existe otro expediente con ese NUC.",
                    details={
                        "reason": "duplicate_nuc",
                        "case_file_id": str(duplicate.id),
                    },
                )
            previous = case_file.nuc_raw
            case_file.nuc_raw = validation.raw
            case_file.nuc_normalized = validation.normalized
            case_file.verification_status = validation.verification_status
        else:
            validation = await validate_identifier(
                session,
                court_id=case_file.court_id,
                kind="SENTENCE",
                raw_value=body.value,
                allow_exception=body.historical_exception,
                exception_reason=body.exception_reason,
            )
            previous = case_file.resolution_number
            case_file.resolution_number = validation.normalized
            if validation.verification_status == VerificationStatus.CONFLICT.value:
                case_file.verification_status = validation.verification_status

        session.add(
            CaseFileIdentifierHistory(
                case_file_id=case_file.id,
                identifier_kind=body.identifier_kind,
                value_raw=validation.raw,
                value_normalized=validation.normalized,
                is_primary=body.identifier_kind == "NUC",
                reason=body.reason.strip(),
                changed_by=actor.id,
            )
        )
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="case_file.identifier_corrected",
            entity_type="case_file",
            entity_id=case_file.id,
            before=before,
            after=_case_snapshot(case_file),
            metadata={
                "identifier_kind": body.identifier_kind,
                "previous_value": previous,
                "new_value": validation.normalized,
                "reason": body.reason.strip(),
                "historical_exception": body.historical_exception,
            },
        )
        await session.commit()
    except StaleDataError as exc:
        await session.rollback()
        raise ConflictError(
            "El expediente fue modificado por otro usuario.",
            details={"reason": "stale_version"},
        ) from exc
    except Exception:
        await session.rollback()
        raise
    await session.refresh(case_file)
    return await get_case_file_detail(session, case_file.id)
```

`relocate`, archivo, anulacion y baja logica:

```python
async def relocate_case_file(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CaseFileRelocate,
) -> schemas.CaseFileDetailOut:
    repo = CaseFileRepository(session)
    try:
        case_file = await repo.get_for_update(case_file_id)
        if case_file is None:
            raise NotFoundError("Expediente no encontrado.")
        if case_file.version != body.expected_version:
            raise ConflictError(
                "El expediente fue modificado por otro usuario.",
                details={
                    "reason": "stale_version",
                    "current_version": case_file.version,
                },
            )
        if case_file.lifecycle_status == LifecycleStatus.VOIDED.value:
            raise ConflictError("Un expediente anulado no puede reubicarse.")
        await _validate_box_for_content(
            session,
            box_id=body.box_id,
            expected_type=BoxType.EXPEDIENTES.value,
        )
        before = _case_snapshot(case_file)
        case_file.box_id = body.box_id
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="case_file.relocated",
            entity_type="case_file",
            entity_id=case_file.id,
            before=before,
            after=_case_snapshot(case_file),
            metadata={"reason": body.reason.strip()},
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(case_file)
    return await get_case_file_detail(session, case_file.id)


async def archive_case_file(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CaseFileLifecycleRequest,
) -> schemas.CaseFileDetailOut:
    return await _change_case_lifecycle(
        request,
        session,
        actor,
        case_file_id,
        body,
        target=LifecycleStatus.ARCHIVED.value,
        action="case_file.archived",
    )


async def void_case_file(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CaseFileLifecycleRequest,
) -> schemas.CaseFileDetailOut:
    return await _change_case_lifecycle(
        request,
        session,
        actor,
        case_file_id,
        body,
        target=LifecycleStatus.VOIDED.value,
        action="case_file.voided",
    )


async def _change_case_lifecycle(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CaseFileLifecycleRequest,
    *,
    target: str,
    action: str,
) -> schemas.CaseFileDetailOut:
    repo = CaseFileRepository(session)
    try:
        case_file = await repo.get_for_update(case_file_id)
        if case_file is None:
            raise NotFoundError("Expediente no encontrado.")
        if case_file.version != body.expected_version:
            raise ConflictError(
                "El expediente fue modificado por otro usuario.",
                details={
                    "reason": "stale_version",
                    "current_version": case_file.version,
                },
            )
        before = _case_snapshot(case_file)
        if target == LifecycleStatus.ARCHIVED.value:
            if case_file.lifecycle_status != LifecycleStatus.ACTIVE.value:
                raise ConflictError(
                    "Solo un expediente activo puede archivarse.",
                    details={"reason": "case_file_not_active"},
                )
            case_file.lifecycle_status = target
            case_file.archived_at = datetime.now(UTC)
            case_file.archived_by = actor.id
            case_file.archive_reason = body.reason.strip()
        else:
            if case_file.lifecycle_status == LifecycleStatus.VOIDED.value:
                raise ConflictError("El expediente ya esta anulado.")
            case_file.lifecycle_status = target
            case_file.voided_at = datetime.now(UTC)
            case_file.voided_by = actor.id
            case_file.void_reason = body.reason.strip()
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action=action,
            entity_type="case_file",
            entity_id=case_file.id,
            before=before,
            after=_case_snapshot(case_file),
            metadata={"reason": body.reason.strip()},
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(case_file)
    return await get_case_file_detail(session, case_file.id)


async def soft_delete_case_file(
    request: Request,
    session: AsyncSession,
    actor: User,
    case_file_id: UUID,
    body: schemas.CaseFileDeleteRequest,
) -> None:
    repo = CaseFileRepository(session)
    try:
        case_file = await repo.get_for_update(case_file_id)
        if case_file is None:
            raise NotFoundError("Expediente no encontrado.")
        if case_file.version != body.expected_version:
            raise ConflictError(
                "El expediente fue modificado por otro usuario.",
                details={
                    "reason": "stale_version",
                    "current_version": case_file.version,
                },
            )
        if case_file.lifecycle_status == LifecycleStatus.VOIDED.value:
            raise ConflictError(
                "Un expediente anulado no puede darse de baja.",
                details={"reason": "case_file_voided"},
            )
        before = _case_snapshot(case_file)
        case_file.deleted_at = datetime.now(UTC)
        case_file.deleted_by = actor.id
        await session.flush()
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="case_file.deleted",
            entity_type="case_file",
            entity_id=case_file.id,
            before=before,
            metadata={"reason": body.reason.strip()},
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
```

Notas:

- En `update_case_file` no se debe permitir cambiar `court_id`, `nuc_raw`, `nuc_normalized` ni `year`; esas modificaciones usan `correct_identifier` o un procedimiento administrativo.
- La reubicacion desde `PATCH /case-files/{id}` y desde `/case-files/{id}/relocate` debe compartir validacion.
- El borrado de partes es fisico porque `case_parties` no tiene borrado logico; queda auditado.
- Corregir un identificador no reutiliza numeracion de cajas ni cambia `nuc_suffix5` manualmente: es una columna calculada.

### 8.11 Paso 11 - Creacion atomica de caja con contenido

Agregar a `backend/src/judicial_archive/modules/boxes/schemas.py`:

```python
class BoxWithContentOut(BaseModel):
    box: BoxOut
    case_file_ids: list[UUID] = Field(default_factory=list)
    administrative_document_ids: list[UUID] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
```

Agregar a `backend/src/judicial_archive/modules/boxes/services.py`:

```python
from judicial_archive.modules.administrative_documents.services import (
    prepare_administrative_document,
)
from judicial_archive.modules.case_files.services import prepare_case_file


async def create_box_with_content(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.BoxWithContentCreate,
) -> schemas.BoxWithContentOut:
    case_file_ids: list[UUID] = []
    administrative_document_ids: list[UUID] = []
    warnings: list[str] = []
    try:
        box = await _insert_box(session, actor=actor, body=body.box)

        if box.box_type == BoxType.EXPEDIENTES.value:
            for inline in body.case_files:
                case_file, case_warnings = await prepare_case_file(
                    session,
                    actor=actor,
                    court_id=box.court_id,
                    box_id=box.id,
                    body=inline,
                    box=box,
                )
                case_file_ids.append(case_file.id)
                warnings.extend(case_warnings)
                await record_audit_event(
                    session,
                    request=request,
                    actor=actor,
                    action="case_file.created",
                    entity_type="case_file",
                    entity_id=case_file.id,
                    after={
                        "court_id": str(case_file.court_id),
                        "box_id": str(case_file.box_id) if case_file.box_id else None,
                        "nuc_raw": case_file.nuc_raw,
                        "nuc_normalized": case_file.nuc_normalized,
                        "year": case_file.year,
                        "verification_status": case_file.verification_status,
                    },
                    metadata={
                        "box_id": str(box.id),
                        "atomic_box_creation": True,
                        "warnings": case_warnings,
                    },
                )
        else:
            for inline in body.administrative_documents:
                document, doc_warnings = await prepare_administrative_document(
                    session,
                    actor=actor,
                    box=box,
                    body=inline,
                )
                administrative_document_ids.append(document.id)
                warnings.extend(doc_warnings)
                await record_audit_event(
                    session,
                    request=request,
                    actor=actor,
                    action="administrative_document.created",
                    entity_type="administrative_document",
                    entity_id=document.id,
                    after={
                        "box_id": str(document.box_id),
                        "title": document.title,
                        "document_type": document.document_type,
                        "document_year": document.document_year,
                        "verification_status": document.verification_status,
                    },
                    metadata={
                        "box_id": str(box.id),
                        "atomic_box_creation": True,
                        "warnings": doc_warnings,
                    },
                )

        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="box.created_with_content",
            entity_type="box",
            entity_id=box.id,
            after=_snapshot(box),
            metadata={
                "case_file_ids": [str(item) for item in case_file_ids],
                "administrative_document_ids": [
                    str(item) for item in administrative_document_ids
                ],
                "warnings": warnings,
            },
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(box)
    return schemas.BoxWithContentOut(
        box=schemas.BoxOut.model_validate(box),
        case_file_ids=case_file_ids,
        administrative_document_ids=administrative_document_ids,
        warnings=warnings,
    )
```

Agregar `BoxType` al import de `judicial_archive.core.enums` en `boxes/services.py`.

Reglas:

- `_insert_box` ya valida tribunal, numeracion y duplicado de numero visible.
- `prepare_case_file` y `prepare_administrative_document` solo hacen `flush`; no hacen `commit`.
- Un error en cualquier contenido debe ejecutar `rollback` y no dejar caja ni contenido.
- El limite maximo de contenido por caja debe configurarse en `core/config.py` y validarse antes del primer `flush`; si no existe configuracion, usar `1000` como valor documentado.
- El payload debe rechazar simultaneamente `case_files` y `administrative_documents`; ya lo valida `BoxWithContentCreate`.
- Si `box.box_type` es `EXPEDIENTES`, `administrative_documents` debe estar vacio; si es `DOCUMENTOS_ADMINISTRATIVOS`, `case_files` debe estar vacio.

### 8.12 Paso 12 - Documentos administrativos

Crear `backend/src/judicial_archive/modules/administrative_documents/schemas.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ConfidentialityValue = Literal["INTERNAL", "RESTRICTED", "CONFIDENTIAL"]


class AdministrativeDocumentInlineCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    document_type: str | None = Field(default=None, max_length=80)
    document_year: int = Field(ge=1, le=9999)
    document_month: int | None = Field(default=None, ge=1, le=12)
    document_day: int | None = Field(default=None, ge=1, le=31)
    description: str | None = Field(default=None, max_length=1000)
    confidentiality: ConfidentialityValue = "INTERNAL"
    source: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=2000)


class AdministrativeDocumentCreate(AdministrativeDocumentInlineCreate):
    box_id: UUID


class AdministrativeDocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    document_type: str | None = Field(default=None, max_length=80)
    document_year: int | None = Field(default=None, ge=1, le=9999)
    document_month: int | None = Field(default=None, ge=1, le=12)
    document_day: int | None = Field(default=None, ge=1, le=31)
    description: str | None = Field(default=None, max_length=1000)
    confidentiality: ConfidentialityValue | None = None
    source: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=2000)
    expected_version: int = Field(ge=1)


class AdministrativeDocumentLifecycleRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=1)


class AdministrativeDocumentDeleteRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
    expected_version: int = Field(ge=1)


class AdministrativeDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    box_id: UUID
    box_type: str
    title: str
    document_type: str | None
    document_year: int
    document_month: int | None
    document_day: int | None
    description: str | None
    verification_status: str
    confidentiality: str
    lifecycle_status: str
    source: str | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class DuplicateAdministrativeDocumentOut(BaseModel):
    id: UUID
    box_id: UUID
    title: str
    document_year: int
    match_type: Literal["EXACT"]
```

Crear `backend/src/judicial_archive/modules/administrative_documents/repositories.py`:

```python
from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.pagination import SortOrder
from judicial_archive.core.text import escape_like
from judicial_archive.modules.administrative_documents.models import (
    AdministrativeDocument,
)


class AdministrativeDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, document_id: UUID) -> AdministrativeDocument | None:
        return await self.session.get(AdministrativeDocument, document_id)

    async def get_for_update(self, document_id: UUID) -> AdministrativeDocument | None:
        return await self.session.scalar(
            select(AdministrativeDocument)
            .where(
                AdministrativeDocument.id == document_id,
                AdministrativeDocument.deleted_at.is_(None),
            )
            .with_for_update()
        )

    async def find_duplicate(
        self,
        *,
        box_id: UUID,
        title: str,
        document_year: int,
        exclude_id: UUID | None = None,
    ) -> AdministrativeDocument | None:
        conditions = [
            AdministrativeDocument.box_id == box_id,
            AdministrativeDocument.document_year == document_year,
            func.lower(AdministrativeDocument.title) == title.strip().lower(),
            AdministrativeDocument.deleted_at.is_(None),
        ]
        if exclude_id is not None:
            conditions.append(AdministrativeDocument.id != exclude_id)
        return await self.session.scalar(
            select(AdministrativeDocument).where(*conditions).limit(1)
        )

    async def list_items(
        self,
        *,
        q: str | None,
        box_id: UUID | None,
        document_year: int | None,
        lifecycle_status: str | None,
        sort_by: str,
        order: SortOrder,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[AdministrativeDocument], int]:
        allowed = {"document_year", "title", "created_at", "updated_at"}
        if sort_by not in allowed:
            raise ValueError("Campo de ordenamiento no permitido.")
        conditions = [AdministrativeDocument.deleted_at.is_(None)]
        if q:
            pattern = f"%{escape_like(q.strip())}%"
            conditions.append(
                or_(
                    AdministrativeDocument.title.ilike(pattern, escape="\\"),
                    AdministrativeDocument.description.ilike(pattern, escape="\\"),
                )
            )
        if box_id is not None:
            conditions.append(AdministrativeDocument.box_id == box_id)
        if document_year is not None:
            conditions.append(AdministrativeDocument.document_year == document_year)
        if lifecycle_status:
            conditions.append(
                AdministrativeDocument.lifecycle_status == lifecycle_status
            )
        base = select(AdministrativeDocument).where(*conditions)
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        column = getattr(AdministrativeDocument, sort_by)
        ordering = column.asc() if order == SortOrder.ASC else column.desc()
        rows = (
            await self.session.scalars(
                base.order_by(ordering, AdministrativeDocument.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return rows, int(total or 0)
```

Crear `backend/src/judicial_archive/modules/administrative_documents/services.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from judicial_archive.core.enums import BoxLifecycleStatus, BoxType, LifecycleStatus
from judicial_archive.core.errors import (
    ConflictError,
    InvalidParameterError,
    NotFoundError,
)
from judicial_archive.core.pagination import Page, PageParams, SortOrder
from judicial_archive.core.text import clean_optional_text
from judicial_archive.modules.administrative_documents import schemas
from judicial_archive.modules.administrative_documents.models import (
    AdministrativeDocument,
)
from judicial_archive.modules.administrative_documents.repositories import (
    AdministrativeDocumentRepository,
)
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.boxes.repositories import BoxRepository
from judicial_archive.modules.case_files.validators import validate_partial_date
from judicial_archive.modules.users.models import User


def _snapshot(document: AdministrativeDocument) -> dict[str, object]:
    return {
        "box_id": str(document.box_id),
        "title": document.title,
        "document_type": document.document_type,
        "document_year": document.document_year,
        "document_month": document.document_month,
        "document_day": document.document_day,
        "confidentiality": document.confidentiality,
        "lifecycle_status": document.lifecycle_status,
        "version": document.version,
    }


async def _active_admin_box(
    session: AsyncSession,
    box_id: UUID,
    *,
    lock: bool = True,
) -> Box:
    repo = BoxRepository(session)
    box = await repo.get_for_update(box_id) if lock else await repo.get(box_id)
    if box is None:
        raise NotFoundError("Caja no encontrada.")
    if box.lifecycle_status != BoxLifecycleStatus.ACTIVE.value:
        raise ConflictError(
            "La caja no esta activa.", details={"reason": "box_not_active"}
        )
    if box.box_type != BoxType.DOCUMENTOS_ADMINISTRATIVOS.value:
        raise InvalidParameterError(
            "Un documento administrativo solo puede pertenecer a una caja administrativa.",
            details={"reason": "box_type_mismatch"},
        )
    return box


async def prepare_administrative_document(
    session: AsyncSession,
    *,
    actor: User,
    box: Box,
    body: schemas.AdministrativeDocumentInlineCreate,
) -> tuple[AdministrativeDocument, list[str]]:
    if box.lifecycle_status != BoxLifecycleStatus.ACTIVE.value:
        raise ConflictError(
            "La caja no esta activa.", details={"reason": "box_not_active"}
        )
    if box.box_type != BoxType.DOCUMENTOS_ADMINISTRATIVOS.value:
        raise InvalidParameterError(
            "La caja no admite documentos administrativos.",
            details={"reason": "box_type_mismatch"},
        )
    validate_partial_date(
        precision="DAY"
        if body.document_day
        else ("MONTH" if body.document_month else "YEAR"),
        year=body.document_year,
        month=body.document_month,
        day=body.document_day,
        field="document",
    )
    repo = AdministrativeDocumentRepository(session)
    duplicate = await repo.find_duplicate(
        box_id=box.id,
        title=body.title,
        document_year=body.document_year,
    )
    if duplicate is not None:
        raise ConflictError(
            "Ya existe un documento con el mismo titulo y anio en la caja.",
            details={
                "reason": "duplicate_administrative_document",
                "document_id": str(duplicate.id),
            },
        )
    document = AdministrativeDocument(
        box_id=box.id,
        box_type=BoxType.DOCUMENTOS_ADMINISTRATIVOS.value,
        title=" ".join(body.title.strip().split()),
        document_type=clean_optional_text(body.document_type, max_length=80),
        document_year=body.document_year,
        document_month=body.document_month,
        document_day=body.document_day,
        description=clean_optional_text(body.description, max_length=1000),
        confidentiality=body.confidentiality,
        lifecycle_status=LifecycleStatus.ACTIVE.value,
        source=clean_optional_text(body.source, max_length=32),
        notes=clean_optional_text(body.notes, max_length=2000),
        created_by=actor.id,
    )
    session.add(document)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError(
            "No se pudo crear el documento administrativo.",
            details={"reason": "administrative_document_integrity_conflict"},
        ) from exc
    return document, []


async def create_administrative_document(
    request: Request,
    session: AsyncSession,
    actor: User,
    body: schemas.AdministrativeDocumentCreate,
) -> schemas.AdministrativeDocumentOut:
    try:
        box = await _active_admin_box(session, body.box_id)
        document, warnings = await prepare_administrative_document(
            session,
            actor=actor,
            box=box,
            body=body,
        )
        await record_audit_event(
            session,
            request=request,
            actor=actor,
            action="administrative_document.created",
            entity_type="administrative_document",
            entity_id=document.id,
            after=_snapshot(document),
            metadata={"warnings": warnings},
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(document)
    return schemas.AdministrativeDocumentOut.model_validate(document)
```

Agregar a `administrative_documents/services.py`:

```python
async def list_administrative_document_duplicates(
    session: AsyncSession,
    *,
    box_id: UUID,
    title: str,
    document_year: int,
) -> list[schemas.DuplicateAdministrativeDocumentOut]:
    duplicate = await AdministrativeDocumentRepository(session).find_duplicate(
        box_id=box_id,
        title=title,
        document_year=document_year,
    )
    if duplicate is None:
        return []
    return [
        schemas.DuplicateAdministrativeDocumentOut(
            id=duplicate.id,
            box_id=duplicate.box_id,
            title=duplicate.title,
            document_year=duplicate.document_year,
            match_type="EXACT",
        )
    ]
```

Implementar exactamente estas funciones con el mismo patron que cajas y expedientes:

- `list_administrative_documents`
- `get_administrative_document`
- `update_administrative_document`
- `set_administrative_document_lifecycle`
- `soft_delete_administrative_document`
- `list_administrative_document_duplicates`

Reglas:

- Listado paginado con `Page` y `SortOrder`.
- `update` bloquea con `get_for_update`, exige `expected_version`, valida fechas y duplicado si cambia `title` o `document_year`.
- `archive` solo desde `ACTIVE`.
- `void` desde `ACTIVE` o `ARCHIVED`.
- `soft_delete` no permitido desde `VOIDED`.
- Todas las mutaciones registran `before`/`after` y `reason` cuando aplica.
- No se permite cambiar `box_id` por `PATCH`; la reubicacion de documentos administrativos queda fuera de B7.
- Un documento administrativo nunca puede quedar en una caja de expedientes.

### 8.13 Paso 13 - Routers

Antes de los routers, agregar a `boxes/services.py`:

```python
async def get_box_content_summary(
    session: AsyncSession,
    box_id: UUID,
) -> schemas.BoxContentSummaryOut:
    box = await BoxRepository(session).get(box_id)
    if box is None:
        raise NotFoundError("Caja no encontrada.")
    case_count, doc_count = await BoxRepository(session).count_contents(box.id)
    return schemas.BoxContentSummaryOut(
        box_id=box.id,
        box_type=box.box_type,
        case_file_count=case_count,
        administrative_document_count=doc_count,
        total_count=case_count + doc_count,
    )


async def list_box_number_history(
    session: AsyncSession,
    *,
    box_id: UUID,
    params: PageParams,
) -> Page[schemas.BoxNumberHistoryOut]:
    box = await BoxRepository(session).get(box_id)
    if box is None:
        raise NotFoundError("Caja no encontrada.")
    rows, total = await BoxRepository(session).list_number_history(
        box_id,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.BoxNumberHistoryOut.model_validate(row) for row in rows]
    return Page[schemas.BoxNumberHistoryOut].build(items, total=total, params=params)
```

Agregar a `case_files/services.py`:

```python
from judicial_archive.modules.case_files.validators import normalize_identifier


async def list_case_file_duplicates(
    session: AsyncSession,
    *,
    court_id: UUID,
    nuc: str,
    year: int,
    limit: int = 20,
) -> list[schemas.DuplicateCaseFileOut]:
    normalized = normalize_identifier(nuc)
    rows = await CaseFileRepository(session).list_duplicates(
        court_id=court_id,
        nuc_normalized=normalized,
        year=year,
        limit=limit,
    )
    return [
        schemas.DuplicateCaseFileOut(
            id=case_file.id,
            nuc_raw=case_file.nuc_raw,
            nuc_normalized=case_file.nuc_normalized,
            nuc_suffix5=case_file.nuc_suffix5,
            court_id=case_file.court_id,
            year=case_file.year,
            box_id=case_file.box_id,
            match_type=match_type,
            verification_status=case_file.verification_status,
        )
        for case_file, match_type in rows
    ]


async def list_persons(
    session: AsyncSession,
    *,
    params: PageParams,
    q: str | None,
    identification_number: str | None,
) -> Page[schemas.PersonOut]:
    rows, total = await PersonRepository(session).list_items(
        q=q,
        identification_number=identification_number,
        offset=params.offset,
        limit=params.limit,
    )
    items = [schemas.PersonOut.model_validate(row) for row in rows]
    return Page[schemas.PersonOut].build(items, total=total, params=params)


async def get_person(session: AsyncSession, person_id: UUID) -> schemas.PersonOut:
    person = await PersonRepository(session).get(person_id)
    if person is None or person.deleted_at is not None:
        raise NotFoundError("Persona no encontrada.")
    return schemas.PersonOut.model_validate(person)


async def list_person_duplicates(
    session: AsyncSession,
    *,
    display_name: str,
    identification_number: str | None,
    limit: int = 20,
) -> list[schemas.DuplicatePersonOut]:
    rows = await PersonRepository(session).list_duplicates(
        normalized_name=normalize_person_name(display_name),
        identification_number=clean_optional_text(identification_number, max_length=64),
        limit=limit,
    )
    return [
        schemas.DuplicatePersonOut(
            id=person.id,
            display_name=person.display_name,
            normalized_name=person.normalized_name,
            identification_number=person.identification_number,
            match_type=match_type,
        )
        for person, match_type in rows
    ]
```

Crear `backend/src/judicial_archive/modules/boxes/routers.py`:

```python
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import (
    Page,
    PageParams,
    SortOrder,
    pagination_params,
)
from judicial_archive.modules.boxes import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/boxes", tags=["Cajas"])


@router.get("", response_model=Page[schemas.BoxOut])
async def list_boxes(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=120)] = None,
    court_id: UUID | None = None,
    year: int | None = None,
    box_type: str | None = None,
    lifecycle_status: str | None = None,
    custody_status: str | None = None,
    sort_by: str = "created_at",
    order: SortOrder = SortOrder.DESC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_READ)),
) -> Page[schemas.BoxOut]:
    return await services.list_boxes(
        session,
        params=params,
        q=q,
        court_id=court_id,
        year=year,
        box_type=box_type,
        lifecycle_status=lifecycle_status,
        custody_status=custody_status,
        sort_by=sort_by,
        order=order,
    )


@router.get("/{box_id}", response_model=schemas.BoxOut)
async def get_box(
    box_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_READ)),
) -> schemas.BoxOut:
    return await services.get_box(session, box_id)


@router.get("/{box_id}/content-summary", response_model=schemas.BoxContentSummaryOut)
async def get_box_content_summary(
    box_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_READ)),
) -> schemas.BoxContentSummaryOut:
    return await services.get_box_content_summary(session, box_id)


@router.get(
    "/{box_id}/number-history", response_model=Page[schemas.BoxNumberHistoryOut]
)
async def list_box_number_history(
    params: Annotated[PageParams, Depends(pagination_params)],
    box_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_READ)),
) -> Page[schemas.BoxNumberHistoryOut]:
    return await services.list_box_number_history(session, box_id=box_id, params=params)


@router.post("", response_model=schemas.BoxOut)
async def create_box(
    request: Request,
    body: schemas.BoxCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_CREATE)),
) -> schemas.BoxOut:
    return await services.create_box(request, session, current_user, body)


@router.post("/with-content", response_model=schemas.BoxWithContentOut)
async def create_box_with_content(
    request: Request,
    body: schemas.BoxWithContentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_CREATE)),
) -> schemas.BoxWithContentOut:
    return await services.create_box_with_content(request, session, current_user, body)


@router.patch("/{box_id}", response_model=schemas.BoxOut)
async def update_box(
    request: Request,
    box_id: UUID,
    body: schemas.BoxUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_UPDATE)),
) -> schemas.BoxOut:
    return await services.update_box(request, session, current_user, box_id, body)


@router.post("/{box_id}/number-corrections", response_model=schemas.BoxOut)
async def correct_box_number(
    request: Request,
    box_id: UUID,
    body: schemas.BoxNumberCorrection,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_UPDATE)),
) -> schemas.BoxOut:
    return await services.correct_box_number(
        request, session, current_user, box_id, body
    )


@router.post("/{box_id}/archive", response_model=schemas.BoxOut)
async def archive_box(
    request: Request,
    box_id: UUID,
    body: schemas.BoxLifecycleRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_UPDATE)),
) -> schemas.BoxOut:
    return await services.set_box_lifecycle(
        request,
        session,
        current_user,
        box_id,
        target="ARCHIVED",
        body=body,
    )


@router.post("/{box_id}/void", response_model=schemas.BoxOut)
async def void_box(
    request: Request,
    box_id: UUID,
    body: schemas.BoxLifecycleRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.BOXES_UPDATE)),
) -> schemas.BoxOut:
    return await services.set_box_lifecycle(
        request,
        session,
        current_user,
        box_id,
        target="VOIDED",
        body=body,
    )
```

Crear `backend/src/judicial_archive/modules/case_files/routers.py`:

```python
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import (
    Page,
    PageParams,
    SortOrder,
    pagination_params,
)
from judicial_archive.modules.case_files import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/case-files", tags=["Expedientes"])
persons_router = APIRouter(prefix="/persons", tags=["Personas"])


@router.get("/duplicates", response_model=list[schemas.DuplicateCaseFileOut])
async def list_case_file_duplicates(
    court_id: UUID,
    nuc: Annotated[str, Query(min_length=1, max_length=100)],
    year: int,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_READ)),
) -> list[schemas.DuplicateCaseFileOut]:
    return await services.list_case_file_duplicates(
        session,
        court_id=court_id,
        nuc=nuc,
        year=year,
        limit=limit,
    )


@router.get("", response_model=Page[schemas.CaseFileOut])
async def list_case_files(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=120)] = None,
    court_id: UUID | None = None,
    box_id: UUID | None = None,
    year: int | None = None,
    lifecycle_status: str | None = None,
    verification_status: str | None = None,
    sort_by: str = "created_at",
    order: SortOrder = SortOrder.DESC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_READ)),
) -> Page[schemas.CaseFileOut]:
    return await services.list_case_files(
        session,
        params=params,
        q=q,
        court_id=court_id,
        box_id=box_id,
        year=year,
        lifecycle_status=lifecycle_status,
        verification_status=verification_status,
        sort_by=sort_by,
        order=order,
    )


@router.post("", response_model=schemas.CaseFileDetailOut)
async def create_case_file(
    request: Request,
    body: schemas.CaseFileCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_CREATE)),
) -> schemas.CaseFileDetailOut:
    return await services.create_case_file(request, session, current_user, body)


@router.get("/{case_file_id}", response_model=schemas.CaseFileDetailOut)
async def get_case_file(
    case_file_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_READ)),
) -> schemas.CaseFileDetailOut:
    return await services.get_case_file(session, case_file_id)


@router.patch("/{case_file_id}", response_model=schemas.CaseFileDetailOut)
async def update_case_file(
    request: Request,
    case_file_id: UUID,
    body: schemas.CaseFileUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> schemas.CaseFileDetailOut:
    return await services.update_case_file(
        request, session, current_user, case_file_id, body
    )


@router.post("/{case_file_id}/relocate", response_model=schemas.CaseFileDetailOut)
async def relocate_case_file(
    request: Request,
    case_file_id: UUID,
    body: schemas.CaseFileRelocate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> schemas.CaseFileDetailOut:
    return await services.relocate_case_file(
        request, session, current_user, case_file_id, body
    )


@router.post(
    "/{case_file_id}/identifiers/correct",
    response_model=schemas.CaseFileDetailOut,
)
async def correct_case_identifier(
    request: Request,
    case_file_id: UUID,
    body: schemas.CaseFileIdentifierCorrection,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> schemas.CaseFileDetailOut:
    return await services.correct_identifier(
        request, session, current_user, case_file_id, body
    )


@router.post("/{case_file_id}/archive", response_model=schemas.CaseFileDetailOut)
async def archive_case_file(
    request: Request,
    case_file_id: UUID,
    body: schemas.CaseFileLifecycleRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> schemas.CaseFileDetailOut:
    return await services.archive_case_file(
        request, session, current_user, case_file_id, body
    )


@router.post("/{case_file_id}/void", response_model=schemas.CaseFileDetailOut)
async def void_case_file(
    request: Request,
    case_file_id: UUID,
    body: schemas.CaseFileLifecycleRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> schemas.CaseFileDetailOut:
    return await services.void_case_file(
        request, session, current_user, case_file_id, body
    )


@router.delete("/{case_file_id}", status_code=204)
async def delete_case_file(
    request: Request,
    case_file_id: UUID,
    body: schemas.CaseFileDeleteRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> Response:
    await services.soft_delete_case_file(
        request, session, current_user, case_file_id, body
    )
    return Response(status_code=204)


@router.get("/{case_file_id}/parties", response_model=list[schemas.CasePartyOut])
async def list_case_parties(
    case_file_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_READ)),
) -> list[schemas.CasePartyOut]:
    detail = await services.get_case_file_detail(session, case_file_id)
    return detail.parties


@router.post("/{case_file_id}/parties", response_model=schemas.CasePartyOut)
async def add_case_party(
    request: Request,
    case_file_id: UUID,
    body: schemas.CasePartyCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> schemas.CasePartyOut:
    return await services.add_party(request, session, current_user, case_file_id, body)


@router.post(
    "/{case_file_id}/parties/with-person",
    response_model=schemas.CasePartyOut,
)
async def add_case_party_with_person(
    request: Request,
    case_file_id: UUID,
    body: schemas.CasePartyWithPersonCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> schemas.CasePartyOut:
    return await services.add_party_with_person(
        request, session, current_user, case_file_id, body
    )


@router.delete("/{case_file_id}/parties/{party_id}", status_code=204)
async def remove_case_party(
    request: Request,
    case_file_id: UUID,
    party_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_UPDATE)),
) -> Response:
    await services.remove_party(request, session, current_user, case_file_id, party_id)
    return Response(status_code=204)


@persons_router.get("/duplicates", response_model=list[schemas.DuplicatePersonOut])
async def list_person_duplicates(
    display_name: Annotated[str, Query(min_length=1, max_length=300)],
    identification_number: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_READ)),
) -> list[schemas.DuplicatePersonOut]:
    return await services.list_person_duplicates(
        session,
        display_name=display_name,
        identification_number=identification_number,
        limit=limit,
    )


@persons_router.get("", response_model=Page[schemas.PersonOut])
async def list_persons(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=120)] = None,
    identification_number: Annotated[str | None, Query(max_length=64)] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_READ)),
) -> Page[schemas.PersonOut]:
    return await services.list_persons(
        session,
        params=params,
        q=q,
        identification_number=identification_number,
    )


@persons_router.get("/{person_id}", response_model=schemas.PersonOut)
async def get_person(
    person_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.CASES_READ)),
) -> schemas.PersonOut:
    return await services.get_person(session, person_id)
```

Crear `backend/src/judicial_archive/modules/administrative_documents/routers.py`:

```python
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.api.deps import get_session, require_permissions
from judicial_archive.core.pagination import (
    Page,
    PageParams,
    SortOrder,
    pagination_params,
)
from judicial_archive.modules.administrative_documents import schemas, services
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(
    prefix="/administrative-documents",
    tags=["Documentos administrativos"],
)


@router.get(
    "/duplicates", response_model=list[schemas.DuplicateAdministrativeDocumentOut]
)
async def list_document_duplicates(
    box_id: UUID,
    title: Annotated[str, Query(min_length=1, max_length=300)],
    document_year: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.DOCUMENTS_READ)),
) -> list[schemas.DuplicateAdministrativeDocumentOut]:
    return await services.list_administrative_document_duplicates(
        session,
        box_id=box_id,
        title=title,
        document_year=document_year,
    )


@router.get("", response_model=Page[schemas.AdministrativeDocumentOut])
async def list_administrative_documents(
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=120)] = None,
    box_id: UUID | None = None,
    document_year: int | None = None,
    lifecycle_status: str | None = None,
    sort_by: str = "created_at",
    order: SortOrder = SortOrder.DESC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.DOCUMENTS_READ)),
) -> Page[schemas.AdministrativeDocumentOut]:
    return await services.list_administrative_documents(
        session,
        params=params,
        q=q,
        box_id=box_id,
        document_year=document_year,
        lifecycle_status=lifecycle_status,
        sort_by=sort_by,
        order=order,
    )


@router.post("", response_model=schemas.AdministrativeDocumentOut)
async def create_administrative_document(
    request: Request,
    body: schemas.AdministrativeDocumentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.DOCUMENTS_MANAGE)),
) -> schemas.AdministrativeDocumentOut:
    return await services.create_administrative_document(
        request, session, current_user, body
    )


@router.get("/{document_id}", response_model=schemas.AdministrativeDocumentOut)
async def get_administrative_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.DOCUMENTS_READ)),
) -> schemas.AdministrativeDocumentOut:
    return await services.get_administrative_document(session, document_id)


@router.patch("/{document_id}", response_model=schemas.AdministrativeDocumentOut)
async def update_administrative_document(
    request: Request,
    document_id: UUID,
    body: schemas.AdministrativeDocumentUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.DOCUMENTS_MANAGE)),
) -> schemas.AdministrativeDocumentOut:
    return await services.update_administrative_document(
        request, session, current_user, document_id, body
    )


@router.post(
    "/{document_id}/archive",
    response_model=schemas.AdministrativeDocumentOut,
)
async def archive_administrative_document(
    request: Request,
    document_id: UUID,
    body: schemas.AdministrativeDocumentLifecycleRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.DOCUMENTS_MANAGE)),
) -> schemas.AdministrativeDocumentOut:
    return await services.set_administrative_document_lifecycle(
        request,
        session,
        current_user,
        document_id,
        target="ARCHIVED",
        body=body,
    )


@router.post(
    "/{document_id}/void",
    response_model=schemas.AdministrativeDocumentOut,
)
async def void_administrative_document(
    request: Request,
    document_id: UUID,
    body: schemas.AdministrativeDocumentLifecycleRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.DOCUMENTS_MANAGE)),
) -> schemas.AdministrativeDocumentOut:
    return await services.set_administrative_document_lifecycle(
        request,
        session,
        current_user,
        document_id,
        target="VOIDED",
        body=body,
    )


@router.delete("/{document_id}", status_code=204)
async def delete_administrative_document(
    request: Request,
    document_id: UUID,
    body: schemas.AdministrativeDocumentDeleteRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.DOCUMENTS_MANAGE)),
) -> Response:
    await services.soft_delete_administrative_document(
        request, session, current_user, document_id, body
    )
    return Response(status_code=204)
```

Notas de orden de rutas:

- `/case-files/duplicates` debe declararse antes de `/case-files/{case_file_id}`.
- `/persons/duplicates` debe declararse antes de `/persons/{person_id}`.
- `/administrative-documents/duplicates` debe declararse antes de `/administrative-documents/{document_id}`.
- Si se agrega `GET /boxes/with-content`, debe declararse antes de `GET /boxes/{box_id}`.
- Las rutas `POST /boxes/with-content` y `POST /case-files/{id}/parties/with-person` no colisionan con rutas dinamicas `GET`, pero se mantiene el orden estatico por claridad.

### 8.14 Paso 14 - Registrar routers

Editar `backend/src/judicial_archive/api/v1/router.py`:

```python
from judicial_archive.modules.administrative_documents.routers import (
    router as administrative_documents_router,
)
from judicial_archive.modules.boxes.routers import router as boxes_router
from judicial_archive.modules.case_files.routers import (
    persons_router,
    router as case_files_router,
)

api_router.include_router(boxes_router)
api_router.include_router(case_files_router)
api_router.include_router(persons_router)
api_router.include_router(administrative_documents_router)
```

Orden recomendado en `router.py`: despues de `locations`/`movements` y antes de rutas de reportes. No crear prefijos duplicados: los routers ya incluyen `/boxes`, `/case-files`, `/persons` y `/administrative-documents`.

## 9. Pruebas

### 9.1 Unitarias

Crear `backend/tests/unit/test_case_file_validators.py`:

- `normalize_identifier("  abc 123 ")` devuelve `"ABC123"`.
- `normalize_identifier("   ")` lanza `InvalidParameterError`.
- `normalize_person_name("  Jose  Angel  ")` devuelve `"JOSE ANGEL"`.
- `normalize_person_name("Jose Angel")` y `normalize_person_name("JOSÉ ÁNGEL")` producen el mismo valor.
- Perfil estricto con patron `^[0-9]{13}$`:
  - acepta `"1234567890123"`;
  - rechaza `"ABC"` con `identifier_pattern_mismatch`;
  - con `allow_exception=True` y motivo devuelve `verification_status=CONFLICT`;
  - con `allow_exception=True` sin motivo lanza `exception_reason_required`.
- Perfil no estricto con patron que no coincide devuelve `CONFLICT` sin lanzar.
- Sin perfil activo devuelve `PENDING` y warning.
- `validate_partial_date`:
  - `UNKNOWN` con componentes lanza error;
  - `YEAR` con mes lanza error;
  - `MONTH` sin mes lanza error;
  - `DAY` sin dia lanza error;
  - combinaciones validas no lanzan.

Crear `backend/tests/unit/test_case_file_schemas.py`:

- `PersonCreate` rechaza mes sin anio y dia sin mes.
- `CaseFileUpdate` acepta campos opcionales y exige `expected_version`.
- `BoxWithContentCreate` rechaza mezcla de expedientes y documentos.
- `BoxWithContentCreate` rechaza documentos en caja de expedientes y expedientes en caja administrativa.
- `BoxCreate` exige `historical_exception=true` cuando se envia `visible_number`.
- `BoxCreate` exige `exception_reason` cuando `historical_exception=true`.

### 9.2 API

Crear `backend/tests/api/test_boxes_api.py`:

- `GET /api/v1/boxes` sin autenticacion devuelve `401`.
- `POST /api/v1/boxes` sin `boxes.create` devuelve `403`.
- `POST /api/v1/boxes` con datos validos crea caja y asigna numero visible.
- Crear dos cajas concurrentes en la misma politica no repite numero visible.
- `POST /api/v1/boxes` con `visible_number` sin `historical_exception` devuelve `422`.
- `POST /api/v1/boxes` con numero visible duplicado devuelve `409` con `reason=duplicate_visible_number`.
- `PATCH /api/v1/boxes/{id}` con `expected_version` desactualizado devuelve `409` con `reason=stale_version`.
- `POST /api/v1/boxes/{id}/archive` archiva solo cajas activas y sin movimiento abierto.
- `POST /api/v1/boxes/{id}/void` anula y conserva historia.
- `DELETE /api/v1/boxes/{id}` devuelve `405` o no existe en el router.
- `GET /api/v1/boxes/{id}/content-summary` devuelve conteos correctos.
- `GET /api/v1/boxes/{id}/number-history` devuelve historial paginado.
- `POST /api/v1/boxes/with-content` crea caja y expedientes en una sola transaccion.
- Si un expediente del payload falla, no queda caja creada.

Crear `backend/tests/api/test_case_files_api.py`:

- `POST /api/v1/case-files` en caja `EXPEDIENTES` crea expediente.
- `POST /api/v1/case-files` con caja `DOCUMENTOS_ADMINISTRATIVOS` devuelve `422` o `409` con `reason=box_type_mismatch`.
- `POST /api/v1/case-files` con caja archivada o anulada devuelve `409` con `reason=box_not_active`.
- `POST /api/v1/case-files` con NUC duplicado exacto devuelve `409` con `reason=duplicate_nuc`.
- `POST /api/v1/case-files` con `duplicate_override=true` y motivo crea el expediente con `verification_status=CONFLICT` y auditoria.
- `POST /api/v1/case-files` con NUC que no cumple perfil estricto devuelve `422` con `identifier_pattern_mismatch`.
- `POST /api/v1/case-files` con `historical_exception=true` y motivo registra `CONFLICT`.
- `POST /api/v1/case-files` con multiples imputados crea todas las relaciones.
- Repetir persona y rol en el mismo expediente devuelve `409` con `reason=duplicate_case_party`.
- Intentar dos partes principales devuelve `409` con `reason=primary_party_exists`.
- `GET /api/v1/case-files/duplicates` devuelve coincidencias exactas, por sufijo y por anio.
- `GET /api/v1/persons?q=` busca por nombre normalizado.
- `GET /api/v1/persons/duplicates` detecta identificacion exacta y nombre exacto.
- `POST /api/v1/case-files/{id}/identifiers/correct` actualiza NUC y agrega historia.
- Corregir NUC a uno ya existente devuelve `409`.
- `POST /api/v1/case-files/{id}/relocate` mueve a caja de expedientes y audita motivo.
- `POST /api/v1/case-files/{id}/archive` archiva expediente activo.
- `POST /api/v1/case-files/{id}/void` anula expediente.
- `DELETE /api/v1/case-files/{id}` hace baja logica y no borra filas.
- Un expediente anulado no admite partes, reubicacion ni edicion.

Crear `backend/tests/api/test_administrative_documents_api.py`:

- `POST /api/v1/administrative-documents` en caja administrativa crea documento.
- En caja de expedientes devuelve `422` o `409` con `reason=box_type_mismatch`.
- Documento con mismo titulo y anio en la misma caja devuelve `409` con `reason=duplicate_administrative_document`.
- `GET /api/v1/administrative-documents/duplicates` devuelve coincidencias exactas.
- `PATCH` con `expected_version` desactualizado devuelve `409`.
- `POST /{id}/archive`, `POST /{id}/void` y `DELETE /{id}` respetan transiciones.
- Un documento anulado no se modifica.
- Sin `documents.manage` las mutaciones devuelven `403`.

### 9.3 Integracion

Crear `backend/tests/integration/test_case_party_uniqueness.py`:

- Verifica que `uq_case_parties_case_person_role` exista.
- Inserta dos relaciones iguales y espera `IntegrityError`.
- Inserta la misma persona con otro rol y espera exito.
- Inserta la misma persona y rol en otro expediente y espera exito.

Crear `backend/tests/integration/test_box_numbering_concurrency.py`:

- Crea 20 cajas concurrentes con `asyncio.gather` y sesiones independientes.
- Verifica que todos los `visible_number` sean distintos.
- Verifica que todos sean mayores o iguales al `start_value` de la politica.
- Verifica que no existan numeros duplicados en `boxes`.
- Repite con `box_type` distinto para validar la especificidad de politica.
- Documenta que los huecos son aceptables; no se exige secuencia continua.

Crear `backend/tests/integration/test_atomic_box_creation.py`:

- Payload con caja valida y un expediente invalido: no queda caja ni expediente.
- Payload con caja valida y NUC duplicado: no queda caja nueva.
- Payload con documento en caja de expedientes: no queda caja.
- Payload con expediente en caja administrativa: no queda caja.
- Verifica que la auditoria no tenga eventos de entidades no confirmadas.

Extender `backend/tests/integration/test_schema_constraints.py`:

- Insertar `case_files` con `box_type=DOCUMENTOS_ADMINISTRATIVOS` falla por `ck_case_files_box_type_expedientes`.
- Insertar `administrative_documents` con `box_type=EXPEDIENTES` falla por `ck_admin_documents_box_type_admin`.
- Insertar `case_files` con `box_id` de caja administrativa falla por FK compuesta.
- Insertar `administrative_documents` con `box_id` de caja de expedientes falla por FK compuesta.
- Verificar que `uq_boxes_visible_number` siga existiendo.
- Verificar que no exista una restriccion unica global de NUC.

### 9.4 Matriz de cobertura

| Criterio de aceptacion | Pruebas principales |
|---|---|
| Expediente no puede insertarse en caja administrativa | API `test_case_files_api.py`; integracion `test_schema_constraints.py` |
| Documento administrativo no puede insertarse en caja de expedientes | API `test_administrative_documents_api.py`; integracion `test_schema_constraints.py` |
| Numeracion unica bajo concurrencia | Integracion `test_box_numbering_concurrency.py` |
| Imputados buscables individualmente | API `test_case_files_api.py`; unit `test_case_file_validators.py` |
| Reglas de identificador configurables y excepciones auditadas | Unit `test_case_file_validators.py`; API `test_case_files_api.py` |
| Operacion parcial no deja datos inconsistentes | Integracion `test_atomic_box_creation.py` |
| Relacion persona-rol unica por expediente | Integracion `test_case_party_uniqueness.py`; API `test_case_files_api.py` |
| Correccion y baja controladas | API `test_case_files_api.py`; API `test_boxes_api.py` |

### 9.5 Comandos

Unitarias y API:

```powershell
Set-Location backend
uv run pytest tests/unit -q --no-cov -n 0
uv run pytest tests/api -q --no-cov -n 0
```

Integracion:

```powershell
Set-Location backend
$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://usuario:clave@localhost:5432/sga_test"
uv run pytest tests/integration -q --no-cov -n 0
Remove-Item Env:RUN_INTEGRATION, Env:TEST_DATABASE_URL
```

Suite completa:

```powershell
Set-Location backend
uv run pytest -q -n 0
```

Cobertura:

```powershell
Set-Location backend
uv run pytest --cov=judicial_archive --cov-report=html -n 0
```

## 10. Documentacion a actualizar

### 10.1 `docs/AGENTS.md`

Corregir la numeracion de fases para que coincida con `GUIA_DESARROLLO_FASES_SGA.md`:

- B6: inventario fisico, areas, estantes, bandejas, posiciones y movimientos.
- B7: cajas, expedientes, personas/partes e inventario administrativo.

Agregar reglas B7:

- Un expediente solo puede estar en caja `EXPEDIENTES`.
- Un documento administrativo solo puede estar en caja `DOCUMENTOS_ADMINISTRATIVOS`.
- La numeracion de cajas usa politicas y secuencias; no `MAX()+1`.
- Las excepciones historicas requieren motivo y auditoria.
- No crear una restriccion unica global de NUC.
- No exponer `DELETE /boxes/{id}`.

No cambiar el significado historico de fases ya cerradas sin ADR. El ADR debe explicar la correccion documental.

### 10.2 `docs/modelo-de-datos.md`

Agregar:

- Indice unico `uq_case_parties_case_person_role` sobre `case_parties(case_file_id, person_id, party_role_id)`.
- Indice no unico `ix_admin_documents_box_year` sobre `administrative_documents(box_id, document_year)`.
- Nota: `case_files.nuc_normalized` no tiene restriccion unica global; la deteccion de duplicados es de servicio y admite excepcion auditada.
- Nota: `case_files.box_type` siempre es `EXPEDIENTES`; `administrative_documents.box_type` siempre es `DOCUMENTOS_ADMINISTRATIVOS`.
- Nota: las FK compuestas `(box_id, box_type)` impiden mezclar tipos.
- Nota: `case_files.nuc_suffix5` es columna calculada.
- Nota: `case_parties` no tiene borrado logico; su eliminacion es fisica y auditada.

### 10.3 `docs/reglas-de-negocio.md`

Agregar secciones:

- Politica de numeracion de cajas:
  - seleccionar politica activa por especificidad `COURT > BOX_TYPE > YEAR > GLOBAL`;
  - desempate por `effective_from` mas reciente;
  - asignar con `nextval`;
  - no reutilizar numeros;
  - aceptar huecos;
  - numero manual solo como excepcion historica auditada.
- Tipos de caja:
  - caja de expedientes solo admite expedientes;
  - caja administrativa solo admite documentos administrativos;
  - una caja no puede mezclar tipos.
- NUC:
  - normalizar a mayusculas y sin espacios;
  - validar contra perfil activo del tribunal;
  - duplicado exacto dentro del mismo tribunal;
  - sufijo de 5 caracteres para busqueda;
  - excepcion historica con `CONFLICT` y motivo;
  - no restriccion unica global.
- Personas y partes:
  - nombre normalizado para busqueda;
  - identificacion exacta para duplicados;
  - relacion unica por expediente, persona y rol;
  - una sola parte principal por expediente.
- Ciclo de vida:
  - caja: `ACTIVE -> ARCHIVED` o `ACTIVE -> VOIDED`; no se reactiva;
  - expediente: `ACTIVE -> ARCHIVED`; `ACTIVE` o `ARCHIVED -> VOIDED`; baja logica separada;
  - documento administrativo: `ACTIVE -> ARCHIVED`; `ACTIVE` o `ARCHIVED -> VOIDED`; baja logica separada;
  - entidades anuladas no se editan.
- Correcciones:
  - corregir NUC o resolucion no borra historia;
  - cada correccion agrega `case_file_identifier_history`;
  - cambio de caja requiere motivo;
  - toda excepcion queda auditada.

### 10.4 `docs/api.md`

Documentar:

- `GET/POST /api/v1/boxes`
- `GET/PATCH /api/v1/boxes/{id}`
- `POST /api/v1/boxes/with-content`
- `POST /api/v1/boxes/{id}/number-corrections`
- `POST /api/v1/boxes/{id}/archive`
- `POST /api/v1/boxes/{id}/void`
- `GET /api/v1/boxes/{id}/content-summary`
- `GET /api/v1/boxes/{id}/number-history`
- `GET/POST /api/v1/case-files`
- `GET/PATCH/DELETE /api/v1/case-files/{id}`
- `GET /api/v1/case-files/duplicates`
- `POST /api/v1/case-files/{id}/relocate`
- `POST /api/v1/case-files/{id}/identifiers/correct`
- `POST /api/v1/case-files/{id}/archive`
- `POST /api/v1/case-files/{id}/void`
- `GET/POST /api/v1/case-files/{id}/parties`
- `POST /api/v1/case-files/{id}/parties/with-person`
- `DELETE /api/v1/case-files/{id}/parties/{party_id}`
- `GET /api/v1/persons`
- `GET /api/v1/persons/duplicates`
- `GET /api/v1/persons/{id}`
- `GET/POST /api/v1/administrative-documents`
- `GET/PATCH/DELETE /api/v1/administrative-documents/{id}`
- `GET /api/v1/administrative-documents/duplicates`
- `POST /api/v1/administrative-documents/{id}/archive`
- `POST /api/v1/administrative-documents/{id}/void`

Para cada endpoint documentar permisos, query params, payload, respuesta, errores y ejemplo. Usar el sobre de error existente en `docs/api.md`.

### 10.5 `docs/pruebas.md`

Agregar:

- Archivos de prueba B7.
- Comandos unitarios, API e integracion.
- Variables `RUN_INTEGRATION` y `TEST_DATABASE_URL`.
- Advertencia de no usar base de produccion.
- Pruebas de concurrencia y su dependencia de PostgreSQL real.
- Criterio de huecos aceptables en numeracion.

### 10.6 `docs/roles-y-permisos.md`

Agregar matriz B7 sin crear permisos nuevos:

| Recurso | Lectura | Creacion | Actualizacion | Baja/anulacion |
|---|---|---|---|---|
| Cajas | `boxes.read` | `boxes.create` | `boxes.update` | `boxes.update` |
| Expedientes | `cases.read` | `cases.create` | `cases.update` | `cases.update` |
| Personas/partes | `cases.read` | `cases.update` | `cases.update` | `cases.update` |
| Documentos administrativos | `documents.read` | `documents.manage` | `documents.manage` | `documents.manage` |

No usar `boxes.delete` en B7; queda reservado para una fase posterior si se decide.

### 10.7 ADR

Crear `docs/decisiones/ADR-0012-numeracion-fases-b6-b7.md`:

- Contexto: conflicto entre `docs/AGENTS.md` y `GUIA_DESARROLLO_FASES_SGA.md`.
- Decision: B6 es inventario fisico/ubicaciones; B7 es cajas/expedientes/inventario administrativo.
- Decision: no se reutiliza `ADR-0002` porque ya esta ocupado por arquitectura modular.
- Consecuencias: actualizar `AGENTS.md`, mantener el plan de fases y no renumerar ADR existentes.

## 11. Puertas de calidad

Ejecutar antes de cerrar B7:

```powershell
Set-Location backend
uv run ruff format --check src tests
uv run ruff check src tests
uv run mypy src tests
uv run pytest -q -n 0 --no-cov --tb=short
```

Si el repositorio tiene `pre-commit` configurado:

```powershell
Set-Location backend
uv run pre-commit run --all-files
```

Migraciones:

```powershell
Set-Location backend
uv run alembic heads
uv run alembic upgrade head
uv run alembic check
uv run alembic downgrade -1
uv run alembic upgrade head
```

Criterios de bloqueo:

- Cualquier fallo de `ruff`, `mypy` o pruebas.
- Cualquier `visible_number` duplicado en prueba de concurrencia.
- Cualquier operacion atomica que deje caja o contenido parcial.
- Cualquier endpoint que permita mezclar tipos de caja.
- Cualquier correccion sin historia o sin auditoria.
- Cualquier `DELETE /boxes/{id}` expuesto.
- Cualquier migracion que agregue unicidad global de NUC.

## 12. Checklist de aceptacion

- [ ] La migracion B7 tiene `down_revision` correcto y `alembic check` limpio.
- [ ] Existe `uq_case_parties_case_person_role`.
- [ ] Existe `ix_admin_documents_box_year`.
- [ ] No existe restriccion unica global de NUC.
- [ ] `GET/POST/PATCH /boxes` funcionan con permisos correctos.
- [ ] `POST /boxes/with-content` es atomico.
- [ ] La numeracion concurrente no duplica `visible_number`.
- [ ] La politica de numeracion respeta especificidad y vigencia.
- [ ] Un expediente no puede crearse en caja administrativa.
- [ ] Un documento administrativo no puede crearse en caja de expedientes.
- [ ] Un expediente puede tener multiples imputados.
- [ ] La relacion persona-rol-expediente es unica.
- [ ] Solo hay una parte principal por expediente.
- [ ] La busqueda de personas por nombre funciona.
- [ ] La deteccion de duplicados de NUC funciona por exacto, sufijo y anio.
- [ ] Las excepciones de identificador requieren motivo y quedan en `CONFLICT`.
- [ ] Las excepciones de duplicado requieren motivo y quedan auditadas.
- [ ] La correccion de NUC agrega historia y no borra la anterior.
- [ ] La reubicacion de expediente valida tipo de caja y audita motivo.
- [ ] Archivo, anulacion y baja logica respetan transiciones.
- [ ] Una entidad anulada no se puede editar.
- [ ] Las cajas no exponen borrado fisico.
- [ ] Los routers estan registrados sin prefijos duplicados.
- [ ] Las rutas estaticas estan antes de las dinamicas.
- [ ] `docs/AGENTS.md` usa la numeracion correcta de fases.
- [ ] `docs/modelo-de-datos.md` refleja indices y restricciones.
- [ ] `docs/reglas-de-negocio.md` documenta B7.
- [ ] `docs/api.md` documenta endpoints y errores.
- [ ] `docs/pruebas.md` documenta comandos y pruebas B7.
- [ ] `docs/roles-y-permisos.md` refleja que no hay permisos nuevos.
- [ ] `ADR-0012` existe y no reutiliza `ADR-0002`.
- [ ] `uv run ruff format --check src tests` pasa.
- [ ] `uv run ruff check src tests` pasa.
- [ ] `uv run mypy src tests` pasa.
- [ ] `uv run pytest -q -n 0 --no-cov --tb=short` pasa.
- [ ] La suite de integracion pasa con PostgreSQL real.

## 13. Despliegue, migracion y rollback

### 13.1 Preflight de datos

Antes de aplicar la migracion en una base con datos:

```sql
SELECT case_file_id, person_id, party_role_id, count(*) AS total
FROM case_parties
GROUP BY case_file_id, person_id, party_role_id
HAVING count(*) > 1
ORDER BY total DESC;
```

Si hay filas:

1. Identificar la relacion correcta.
2. Decidir si se conserva una fila y se eliminan las duplicadas, o si se requiere merge manual.
3. Registrar la decision en un ticket y en auditoria.
4. No ejecutar la migracion hasta que el preflight devuelva cero filas.

Preflight de numeros visibles duplicados:

```sql
SELECT visible_number, count(*) AS total
FROM boxes
GROUP BY visible_number
HAVING count(*) > 1;
```

No deberia devolver filas por `uq_boxes_visible_number`, pero se verifica antes de desplegar.

Preflight de NUC duplicados informativos:

```sql
SELECT court_id, nuc_normalized, count(*) AS total
FROM case_files
WHERE deleted_at IS NULL
GROUP BY court_id, nuc_normalized
HAVING count(*) > 1
ORDER BY total DESC;
```

Este preflight no bloquea la migracion porque B7 no agrega unicidad global de NUC. Sirve para decidir si se necesita limpieza o marcacion como `CONFLICT`.

### 13.2 Respaldo

Antes de migrar:

- Respaldo completo de la base.
- Respaldo de `boxes`, `case_files`, `case_parties`, `persons`, `administrative_documents` y tablas de auditoria.
- Verificar restauracion en un entorno de prueba.
- Confirmar que `TEST_DATABASE_URL` no apunta a produccion.

### 13.3 Orden de despliegue

1. Detener escrituras de la aplicacion o poner el sistema en modo mantenimiento.
2. Ejecutar preflight.
3. Crear respaldo.
4. Ejecutar `uv run alembic upgrade head`.
5. Verificar indices y constraints.
6. Desplegar la version B7 de la aplicacion.
7. Reactivar escrituras.
8. Ejecutar smoke tests.

La migracion B7 no mueve datos ni crea entidades; solo agrega indices. Si se detectan duplicados de `case_parties`, la migracion fallara y la aplicacion anterior debe seguir operativa.

### 13.4 Bloqueo de indices

`CREATE UNIQUE INDEX` dentro de una transaccion puede bloquear escrituras en `case_parties`. Para bases grandes:

- Preferir una ventana de mantenimiento.
- O usar `CREATE UNIQUE INDEX CONCURRENTLY` fuera de transaccion y luego reflejar el indice en Alembic con `op.execute`/`autocommit_block`.
- Si se usa `CONCURRENTLY`, no ejecutar la sentencia dentro de una transaccion normal.
- Verificar que el indice quede valido con `pg_index.indisvalid`.

Ejemplo de verificacion:

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('case_parties', 'administrative_documents')
  AND indexname IN ('uq_case_parties_case_person_role', 'ix_admin_documents_box_year');
```

### 13.5 Smoke tests posteriores

```powershell
$base = "http://localhost:8000/api/v1"
Invoke-RestMethod "$base/health"
Invoke-RestMethod "$base/boxes" -Headers $headers
Invoke-RestMethod "$base/case-files" -Headers $headers
Invoke-RestMethod "$base/administrative-documents" -Headers $headers
```

Verificar:

- `GET /health` responde correctamente.
- Los listados paginan.
- Crear una caja de prueba asigna numero.
- Crear un expediente en caja de expedientes funciona.
- Crear un documento en caja administrativa funciona.
- Intentar mezclar tipos devuelve error controlado.
- El evento de auditoria aparece en la consulta de auditoria.

Eliminar o anular los datos de smoke test con el flujo auditado; no borrar filas directamente.

### 13.6 Rollback

Si falla el despliegue:

1. Detener escrituras.
2. Volver a la version anterior de la aplicacion.
3. Ejecutar `uv run alembic downgrade -1` solo si es seguro.
4. Verificar que los indices B7 hayan sido eliminados.
5. Restaurar respaldo si la migracion dejo datos inconsistentes.
6. Reactivar escrituras.
7. Registrar incidente y causa.

`downgrade` elimina los indices, no los datos. Si se agrego una columna en una migracion futura, el rollback debe revisarse contra esa revision, no contra esta guia.

### 13.7 Post-despliegue

- Verificar que no haya errores 500 en logs.
- Verificar que las rutas nuevas no colisionen con las existentes.
- Verificar que los permisos devuelvan 403 correctamente.
- Verificar que las excepciones historicas queden en `CONFLICT`.
- Verificar que no se hayan creado cajas sin contenido por un fallo atomico.
- Revisar que el numero visible asignado no se repita.
- Revisar que la auditoria tenga `before`/`after` en mutaciones.

## 14. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigacion |
|---|---|---|
| Concurrencia en numeracion | Numeros duplicados | `nextval`, indice unico, prueba concurrente |
| Huecos en numeracion | Numeros faltantes | Aceptar y documentar; no reutilizar |
| Politica de numeracion ambigua | Numero inesperado | Orden de especificidad y vigencia documentado |
| NUC con formatos historicos | Rechazo de datos validos | Perfil configurable y excepcion auditada |
| Duplicado de NUC no detectado | Expedientes repetidos | Deteccion exacta por tribunal y sufijo5 |
| Duplicado de persona | Registros fragmentados | Busqueda por identificacion y nombre normalizado |
| Relacion parte duplicada | Datos inconsistentes | Indice unico y validacion de servicio |
| Dos partes principales | Ambiguedad procesal | Validacion en servicio y prueba API |
| Mezcla de tipos de caja | Datos invalidos | FK compuesta, checks y validacion de servicio |
| Operacion atomica parcial | Caja huerfana | Una transaccion, `flush` sin `commit`, rollback |
| Indice unico bloquea tabla | Downtime | Ventana de mantenimiento o `CONCURRENTLY` |
| Borrado fisico accidental | Perdida de datos | Baja logica y auditoria; no `DELETE` de cajas |
| Permisos insuficientes | Funcionalidad inaccesible | Matriz B7 y pruebas 403 |
| Import circular entre modulos | Error de arranque | Servicios importan repositorios/modelos, no routers |
| Ruta dinamica captura ruta estatica | Endpoint inaccesible | Declarar rutas estaticas primero |
| `Box.notes` inexistente | Error de atributo | No usar `notes` en cajas; usar `description` |
| Fechas parciales invalidas | Datos inconsistentes | `validate_partial_date` y checks SQL |
| Baja logica no excluida en consultas | Datos borrados visibles | Filtrar `deleted_at IS NULL` en repositorios |
| Version desactualizada | Sobrescritura de cambios | `expected_version` y `StaleDataError` |
| Auditoria incompleta | Falta de trazabilidad | Registrar `before`/`after` y motivos |
| Documentacion de fases contradictoria | Implementacion incorrecta | ADR-0012 y actualizacion de `AGENTS.md` |

## 15. Anexos

### 15.1 Tabla de endpoints

| Metodo | Ruta | Permiso | Descripcion |
|---|---|---|---|
| GET | `/api/v1/boxes` | `boxes.read` | Listar cajas con filtros y paginacion |
| POST | `/api/v1/boxes` | `boxes.create` | Crear caja |
| POST | `/api/v1/boxes/with-content` | `boxes.create` | Crear caja y contenido en una transaccion |
| GET | `/api/v1/boxes/{id}` | `boxes.read` | Obtener caja |
| PATCH | `/api/v1/boxes/{id}` | `boxes.update` | Actualizar descripcion/confidencialidad |
| POST | `/api/v1/boxes/{id}/number-corrections` | `boxes.update` | Corregir numero visible con historia |
| POST | `/api/v1/boxes/{id}/archive` | `boxes.update` | Archivar caja |
| POST | `/api/v1/boxes/{id}/void` | `boxes.update` | Anular caja |
| GET | `/api/v1/boxes/{id}/content-summary` | `boxes.read` | Resumen de contenido |
| GET | `/api/v1/boxes/{id}/number-history` | `boxes.read` | Historia de numeros |
| GET | `/api/v1/case-files` | `cases.read` | Listar expedientes |
| POST | `/api/v1/case-files` | `cases.create` | Crear expediente |
| GET | `/api/v1/case-files/duplicates` | `cases.read` | Buscar posibles duplicados |
| GET | `/api/v1/case-files/{id}` | `cases.read` | Obtener expediente con partes |
| PATCH | `/api/v1/case-files/{id}` | `cases.update` | Actualizar expediente |
| POST | `/api/v1/case-files/{id}/relocate` | `cases.update` | Reubicar expediente |
| POST | `/api/v1/case-files/{id}/identifiers/correct` | `cases.update` | Corregir NUC o resolucion |
| POST | `/api/v1/case-files/{id}/archive` | `cases.update` | Archivar expediente |
| POST | `/api/v1/case-files/{id}/void` | `cases.update` | Anular expediente |
| DELETE | `/api/v1/case-files/{id}` | `cases.update` | Baja logica |
| GET | `/api/v1/case-files/{id}/parties` | `cases.read` | Listar partes |
| POST | `/api/v1/case-files/{id}/parties` | `cases.update` | Agregar parte existente |
| POST | `/api/v1/case-files/{id}/parties/with-person` | `cases.update` | Crear persona y parte |
| DELETE | `/api/v1/case-files/{id}/parties/{party_id}` | `cases.update` | Quitar parte |
| GET | `/api/v1/persons` | `cases.read` | Buscar personas |
| GET | `/api/v1/persons/duplicates` | `cases.read` | Buscar duplicados de persona |
| GET | `/api/v1/persons/{id}` | `cases.read` | Obtener persona |
| GET | `/api/v1/administrative-documents` | `documents.read` | Listar documentos |
| POST | `/api/v1/administrative-documents` | `documents.manage` | Crear documento |
| GET | `/api/v1/administrative-documents/duplicates` | `documents.read` | Buscar duplicados |
| GET | `/api/v1/administrative-documents/{id}` | `documents.read` | Obtener documento |
| PATCH | `/api/v1/administrative-documents/{id}` | `documents.manage` | Actualizar documento |
| POST | `/api/v1/administrative-documents/{id}/archive` | `documents.manage` | Archivar documento |
| POST | `/api/v1/administrative-documents/{id}/void` | `documents.manage` | Anular documento |
| DELETE | `/api/v1/administrative-documents/{id}` | `documents.manage` | Baja logica |

### 15.2 Payloads de referencia

Crear caja:

```json
{
  "court_id": "6f0f6a3e-2d4a-4b8e-9f0e-1a2b3c4d5e6f",
  "year": 2026,
  "box_type": "EXPEDIENTES",
  "description": "Caja de expedientes 2026",
  "confidentiality": "INTERNAL"
}
```

Crear caja con contenido atomico:

```json
{
  "box": {
    "court_id": "6f0f6a3e-2d4a-4b8e-9f0e-1a2b3c4d5e6f",
    "year": 2026,
    "box_type": "EXPEDIENTES",
    "description": "Caja con expedientes iniciales",
    "confidentiality": "INTERNAL"
  },
  "case_files": [
    {
      "nuc": "2026-000123",
      "year": 2026,
      "entry_precision": "DAY",
      "entry_year": 2026,
      "entry_month": 1,
      "entry_day": 15,
      "sentence_precision": "UNKNOWN",
      "resolution_type_id": "8c1f0a3e-1b2c-4d5e-8f90-1234567890ab",
      "resolution_number": "SENT-2026-0001",
      "judge_name": "Juez de prueba",
      "description": "Expediente de prueba",
      "confidentiality": "INTERNAL",
      "parties": [
        {
          "person_id": "0a1b2c3d-4e5f-6789-abcd-ef0123456789",
          "party_role_id": "1a2b3c4d-5e6f-7890-abcd-ef1234567890",
          "is_primary": true,
          "notes": "Imputado principal"
        }
      ]
    }
  ],
  "administrative_documents": []
}
```

Crear expediente con excepcion historica:

```json
{
  "court_id": "6f0f6a3e-2d4a-4b8e-9f0e-1a2b3c4d5e6f",
  "box_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
  "nuc": "NUC-HISTORICO-001",
  "year": 1998,
  "entry_precision": "YEAR",
  "entry_year": 1998,
  "sentence_precision": "UNKNOWN",
  "historical_exception": true,
  "exception_reason": "NUC anterior al formato vigente"
}
```

Crear expediente con duplicado autorizado:

```json
{
  "court_id": "6f0f6a3e-2d4a-4b8e-9f0e-1a2b3c4d5e6f",
  "box_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
  "nuc": "2026-000123",
  "year": 2026,
  "entry_precision": "UNKNOWN",
  "sentence_precision": "UNKNOWN",
  "duplicate_override": true,
  "duplicate_override_reason": "Expediente reingresado por error administrativo documentado"
}
```

Corregir NUC:

```json
{
  "identifier_kind": "NUC",
  "value": "2026-000124",
  "reason": "Error de digitacion en el alta",
  "historical_exception": false,
  "expected_version": 3
}
```

Reubicar expediente:

```json
{
  "box_id": "8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
  "reason": "Reorganizacion de cajas 2026",
  "expected_version": 4
}
```

Crear documento administrativo:

```json
{
  "box_id": "9c0d1e2f-3a4b-5c6d-7e8f-9a0b1c2d3e4f",
  "title": "Oficio de remision",
  "document_type": "OFICIO",
  "document_year": 2026,
  "document_month": 2,
  "document_day": 10,
  "description": "Oficio de remision de expedientes",
  "confidentiality": "INTERNAL"
}
```

### 15.3 Errores y motivos

| `reason` | HTTP | Causa |
|---|---|---|
| `box_type_mismatch` | 422 o 409 | Tipo de caja incompatible con el contenido |
| `box_not_active` | 409 | Caja archivada, anulada o inactiva |
| `duplicate_visible_number` | 409 | Numero visible ya existente |
| `stale_version` | 409 | `expected_version` desactualizado |
| `duplicate_nuc` | 409 | NUC exacto ya existente en el tribunal |
| `duplicate_override_reason_required` | 422 | Override de duplicado sin motivo |
| `identifier_pattern_mismatch` | 422 | Identificador no cumple perfil estricto |
| `exception_reason_required` | 422 | Excepcion sin motivo |
| `duplicate_case_party` | 409 | Persona y rol ya relacionados al expediente |
| `primary_party_exists` | 409 | Ya existe parte principal |
| `duplicate_person` | 409 | Identificacion exacta ya registrada |
| `duplicate_administrative_document` | 409 | Titulo y anio repetidos en la caja |
| `case_file_voided` | 409 | Expediente anulado no editable |
| `case_file_not_active` | 409 | Transicion no permitida |
| `open_movement_exists` | 409 | Caja con movimiento abierto |
| `change_reason_required` | 422 | Cambio de caja sin motivo |
| `invalid_identifier_profile_pattern` | 422 | Patron de perfil invalido |
| `case_file_integrity_conflict` | 409 | Conflicto de integridad no clasificado |
| `administrative_document_integrity_conflict` | 409 | Conflicto de integridad no clasificado |

Usar el sobre de error existente. No devolver detalles internos de SQL ni nombres de constraints al cliente.

### 15.4 Acciones de auditoria

| Accion | Entidad |
|---|---|
| `box.created` | `box` |
| `box.created_with_content` | `box` |
| `box.updated` | `box` |
| `box.number_corrected` | `box` |
| `box.archived` | `box` |
| `box.voided` | `box` |
| `case_file.created` | `case_file` |
| `case_file.updated` | `case_file` |
| `case_file.relocated` | `case_file` |
| `case_file.identifier_corrected` | `case_file` |
| `case_file.archived` | `case_file` |
| `case_file.voided` | `case_file` |
| `case_file.deleted` | `case_file` |
| `case_party.added` | `case_party` |
| `case_party.removed` | `case_party` |
| `person.created` | `person` |
| `administrative_document.created` | `administrative_document` |
| `administrative_document.updated` | `administrative_document` |
| `administrative_document.archived` | `administrative_document` |
| `administrative_document.voided` | `administrative_document` |
| `administrative_document.deleted` | `administrative_document` |

Las excepciones historicas deben incluir en `metadata`:

- `historical_exception`
- `exception_reason`
- `duplicate_override`
- `duplicate_override_reason`
- `warnings`

### 15.5 Procedimiento de correccion historica

1. Detectar el dato problematico con el endpoint de duplicados o una consulta controlada.
2. No modificar la base directamente.
3. Si el NUC no cumple el formato vigente:
   - usar `POST /case-files/{id}/identifiers/correct`;
   - enviar `historical_exception=true`;
   - enviar `exception_reason` claro y verificable;
   - confirmar que quede `verification_status=CONFLICT`.
4. Si el NUC ya existe en otro expediente:
   - no forzar la correccion desde el endpoint de correccion;
   - documentar el caso;
   - resolver mediante el procedimiento administrativo definido por el area;
   - si se autoriza un duplicado, hacerlo en el alta con `duplicate_override` y motivo, no con SQL manual.
5. Si hay relaciones de parte duplicadas:
   - ejecutar el preflight SQL;
   - conservar la relacion correcta;
   - eliminar las relaciones sobrantes con `DELETE /case-files/{id}/parties/{party_id}` para que quede auditoria;
   - no borrar personas ni expedientes.
6. Si hay una caja con contenido mezclado:
   - no intentar corregir con `PATCH`;
   - mover el contenido al contenedor correcto con el flujo de reubicacion o alta;
   - documentar y auditar.
7. Verificar auditoria:
   - accion;
   - actor;
   - fecha;
   - `before`/`after`;
   - motivo;
   - resultado.

### 15.6 Notas finales

- B7 no implementa codigo de produccion en esta guia; las secciones de codigo son referencias para la fase de implementacion.
- No usar `MAX(visible_number) + 1` en ningun caso.
- No agregar una restriccion unica global de NUC en B7.
- No crear permisos nuevos; reutilizar `boxes.*`, `cases.*` y `documents.*`.
- No exponer `DELETE /boxes/{id}`.
- No usar `notes` en `Box` mientras la columna no exista.
- Mantener las rutas estaticas antes de las dinamicas.
- Mantener la documentacion en espanol y sin emojis.
- Ejecutar todas las puertas de calidad antes de cerrar la fase.
