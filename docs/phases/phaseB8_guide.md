# Fase B8 - Busqueda avanzada e indices

**Version:** 1.0
**Fecha:** 2026-11-06
**Estado:** Guia de implementacion
**Depende de:** B7 - Cajas, expedientes e inventario administrativo
**Habilita:** B9, B10, B12, B13, B14 y B15
**Alcance:** Backend, PostgreSQL, Alembic, pruebas y documentacion
**Documento unico de la fase:** `docs/phases/phaseB8_guide.md`

---

## 0. Como usar esta guia

1. Leer completos `docs/AGENTS.md` y `docs/phases/GUIA_DESARROLLO_FASES_SGA.md` antes de escribir codigo.
2. Leer `docs/phases/phaseB1_guide.md` para el contrato funcional de busqueda global, `phaseB2_guide.md` para el modelo de datos e indices y `phaseB7_guide.md` para las convenciones de servicios, routers, permisos, auditoria y pruebas.
3. Ejecutar los pasos en el orden indicado. No crear routers antes de la migracion, los esquemas y el repositorio.
4. No implementar prestamos, importaciones masivas, OCR, QR, reportes, frontend ni conciliacion en esta fase. B8 solo lee datos existentes y crea indices y endpoints de consulta.
5. Toda busqueda debe respetar permisos, confidencialidad y alcance de grupo. No se acepta filtrar despues de consultar ni ocultar resultados en el frontend.
6. No se permite modificar datos desde endpoints de busqueda. B8 es estrictamente de lectura.
7. Toda correccion debe incluir una prueba de regresion. No se aceptan `xfail` nuevos ni `skip` para funcionalidad B8.
8. Los comandos se ejecutan desde `backend/` salvo que se indique otra ruta.
9. Mantener documentacion en espanol y sin datos reales, secretos ni credenciales.
10. No implementar codigo de produccion en esta guia. La guia describe exactamente que crear, donde crearlo, como probarlo y como documentarlo.

---

## 1. Resumen ejecutivo

B7 construyo el nucleo documental: cajas, expedientes, personas, partes, documentos administrativos, numeracion, correcciones y auditoria. B8 agrega la capacidad de localizar esos registros de forma rapida, combinable y segura.

B8 entrega:

- Un endpoint global agrupado `GET /api/v1/search`.
- Endpoints especializados con paginacion estable:
  - `GET /api/v1/search/boxes`
  - `GET /api/v1/search/case-files`
  - `GET /api/v1/search/administrative-documents`
  - `GET /api/v1/search/import-batches`
- Busqueda por NUC completo, ultimos cinco digitos, NUC parcial, nombre de imputado o parte, tribunal, anio, sentencia/resolucion y fechas.
- Busqueda por numero de caja, tipo, estado, area, anaquel, bandeja, posicion, ubicacion confirmada, pendiente o desconocida.
- Filtros de disponibilidad y prestamo, con proteccion por permisos.
- Filtros por lote de importacion y filas con incidencias.
- Normalizacion uniforme de acentos, mayusculas, espacios y ceros iniciales.
- Ranking determinista: exacto, prefijo y contiene. Sin busqueda difusa por defecto.
- Indices B-tree, GIN trigram y funciones inmutables de `unaccent` en PostgreSQL.
- Paginacion, ordenacion por lista blanca, limites de resultados y limite de tasa.
- Auditoria de cada busqueda sin almacenar el texto crudo de la consulta.
- Pruebas unitarias, API, integracion, permisos, auditoria, indices y rendimiento.

B8 **no crea** una segunda capa de datos ni duplica los modelos de B7. Reutiliza `boxes`, `case_files`, `persons`, `case_parties`, `administrative_documents`, `courts`, `areas`, `shelves`, `trays`, `positions`, `import_batches`, `import_rows`, `loans` y `loan_items`.

La regla central es:

> Una busqueda nunca debe revelar un registro que el usuario no puede ver en su endpoint de origen, ni debe devolver ubicacion fisica de un resultado no autorizado.

---

## 2. Alcance y no alcance

### 2.1 Dentro de alcance

| Area | Incluido |
|---|---|
| Busqueda global | Consulta agrupada por cajas, expedientes y documentos administrativos. |
| Busqueda especializada | Un endpoint por grupo con paginacion y ordenacion propias. |
| Identificadores | NUC exacto, `nuc_suffix5`, NUC parcial, resolucion/sentencia. |
| Personas | Nombre normalizado de imputados y partes, rol de parte. |
| Tribunales | Codigo normalizado y nombre del tribunal. |
| Fechas | Entrada, sentencia y documento con precision YEAR, MONTH o DAY. |
| Cajas | Numero visible, tipo, ciclo de vida, custodia, confidencialidad. |
| Ubicacion | Area, anaquel, bandeja, posicion, precision y ausencia de ubicacion. |
| Prestamos | Disponibilidad, prestamo abierto, estado y vencimiento. |
| Importaciones | Lote, estado de lote, fila y registros con incidencias. |
| Ranking | Exacto, prefijo, contiene y orden estable por relevancia o fecha. |
| Permisos | `search.read`, permisos de recurso y permisos de confidencialidad. |
| Indices | B-tree compuestos, GIN trigram, indices parciales y `EXPLAIN`. |
| Seguridad | Auditoria redactada, limite de tasa y ausencia de N+1. |
| Pruebas | Unitarias, API, integracion, precision, permisos, indices y rendimiento. |
| Documentacion | API, modelo de datos, reglas, permisos, seguridad, pruebas y ADR. |

### 2.2 Fuera de alcance

| Area | Fase responsable |
|---|---|
| Prestamos, devoluciones y solicitudes | B9 |
| Importaciones masivas, carga y aplicacion de lotes | B10 |
| OCR de escaneos y manuscritos | B11 |
| Exportaciones, reportes y panel de control | B12 |
| QR y codigos de barras | B13 |
| Conciliacion de inventario fisico y digital | B14 |
| Endurecimiento final y rendimiento global | B15 |
| Frontend, plano 2D/3D y pantallas | Fases F |
| Busqueda difusa, tolerante a errores o semantica | Fase posterior con decision expresa |
| Motor externo tipo Elasticsearch/OpenSearch | No aprobado en el stack actual |

B8 puede leer `import_batches`, `import_rows`, `loans` y `loan_items`, pero no crear, modificar ni aplicar esos registros. Los filtros de prestamo e importacion son de solo lectura.

---

## 3. Decisiones de diseno y conflictos

### 3.1 Decisiones obligatorias

| ID | Decision | Motivo |
|---|---|---|
| D-B8-01 | `q` es opcional si se envia al menos un filtro especifico. | Evita exigir texto libre para busquedas exactas por NUC, caja o lote. |
| D-B8-02 | Existe un endpoint global agrupado y endpoints especializados. | El global sirve a la barra de busqueda; los especializados permiten paginacion y filtros propios. |
| D-B8-03 | La confidencialidad se controla con `search.restricted` y `search.confidential`. | No existe hoy un permiso que diferencie niveles; usar roles seria fragil. |
| D-B8-04 | No hay busqueda difusa por defecto. | Un falso positivo judicial es mas costoso que un resultado faltante; la fuzzy se evalua en otra fase. |
| D-B8-05 | Se usan `pg_trgm` y `unaccent` con una funcion inmutable. | Permiten busqueda parcial con acentos sin cambiar el modelo ni agregar un motor externo. |
| D-B8-06 | Las fechas parciales se interpretan por precision declarada. | No se inventa dia o mes; una fecha YEAR no debe comportarse como DAY. |
| D-B8-07 | B8 no cambia los defaults de confidencialidad de B7. | La discrepancia D-33 se documenta y se resuelve en una fase legal separada. |
| D-B8-08 | Los filtros de prestamo e importacion son opcionales y requieren permiso. | B8 lee modulos que aun no tienen routers; no debe exponer datos sin control. |
| D-B8-09 | Las busquedas tienen limite de tasa por usuario. | Una busqueda trigram puede ser costosa; el limite protege la base y el servicio. |
| D-B8-10 | `nuc_suffix5` no es unico. | Varios expedientes pueden compartir los ultimos cinco caracteres. |

### 3.2 Conflicto de confidencialidad D-33

La decision D-33 registrada en la documentacion maestra indica que el valor por defecto de confidencialidad deberia ser `RESTRICTED`. La implementacion B7 usa `INTERNAL` como default en `Box`, `CaseFile` y `AdministrativeDocument`.

Decision para B8:

1. No cambiar defaults existentes en esta fase.
2. Aplicar visibilidad sobre los valores reales ya almacenados.
3. Registrar la discrepancia en `docs/pendientes-de-validacion.md`.
4. Si el area legal confirma que el default debe ser `RESTRICTED`, crear una fase o ADR separada con migracion de datos, comunicacion y pruebas.
5. B8 no debe introducir un cambio silencioso de visibilidad que afecte registros historicos.

### 3.3 Refinamiento del contrato B1

B1 exige `q` en la busqueda global. B8 lo refina:

- `q` sigue siendo el criterio principal.
- `q` puede omitirse si se envia un filtro especifico como `nuc`, `nuc_last5`, `name`, `sentence`, `title`, `number` o `import_batch_id`.
- Si no hay `q` ni filtros, devolver `422 validation_error` con `details.reason = "search_criteria_required"`.
- Si se envia `types` explicito con un filtro que no aplica a ese tipo, devolver `422` en lugar de ignorar el filtro. Esto cumple el criterio de no omitir filtros.

---

## 4. Estado de partida y brechas B8

### 4.1 Lo que ya existe

| Archivo | Estado actual |
|---|---|
| `modules/boxes/models.py` | `Box`, historial de numero y ubicacion, movimientos; indices de tribunal/anio/tipo, custodia y posicion. |
| `modules/case_files/models.py` | `CaseFile`, `Person`, `CaseParty`, historial de identificadores; `nuc_suffix5` generado e indices de NUC, anio, caja y verificacion. |
| `modules/administrative_documents/models.py` | Documento administrativo con titulo, fecha parcial, tipo, estado y baja logica. |
| `modules/locations/models.py` | `Area`, `Shelf`, `Tray`, `Position`; codigos y jerarquia. |
| `modules/courts/models.py` | `Court`, `ResolutionType`, `PartyRole`, perfiles de identificadores. |
| `modules/imports/models.py` | `ImportBatch`, `ImportFile`, `ImportRow` con vinculos a caja, expediente y documento. |
| `modules/loans/models.py` | `Loan`, `LoanItem` con indices parciales de prestamo abierto por caja y expediente. |
| `modules/audit/services.py` | `record_audit_event` para auditoria transaccional. |
| `modules/users/repositories.py` | `get_permission_codes(user_id)`. |
| `api/deps.py` | `get_session`, `get_redis`, `get_current_user`, `require_permissions`. |
| `core/pagination.py` | `Page`, `PageParams`, `SortOrder`, `build_sort_params`. |
| `core/text.py` | `escape_like`, normalizacion de codigos y utilidades de texto. |
| `modules/case_files/validators.py` | `normalize_identifier`, `normalize_person_name`. |
| `api/v1/router.py` | Registro de routers B7; no registra busqueda. |
| `alembic/versions/20261105_0002_b7_case_party_uniqueness.py` | Cabeza actual de migraciones. |
| `tests/integration/b7_helpers.py` | Helpers de creacion de cajas, expedientes, personas y documentos. |

### 4.2 Brechas que B8 debe cerrar

1. No existe modulo `modules/search/`.
2. No existe endpoint global ni endpoints especializados de busqueda.
3. No existe normalizacion unica para texto de busqueda con acentos y espacios.
4. No existe ranking determinista entre coincidencia exacta, prefijo y contiene.
5. No existe control de visibilidad por nivel de confidencialidad.
6. No existen permisos `search.restricted` ni `search.confidential`.
7. No existe busqueda por ubicacion fisica ni por ubicacion desconocida/pendiente.
8. No existe busqueda por prestamo abierto, vencimiento o disponibilidad.
9. No existe busqueda por lote de importacion ni por filas con incidencias.
10. No existen indices GIN trigram ni funcion inmutable de `unaccent`.
11. No existen indices parciales para vinculos de importacion ni para prestamos vencidos.
12. No existe limite de tasa para busqueda.
13. No existe auditoria de busqueda con metadatos redactados.
14. No existen pruebas de precision, permisos, indices ni rendimiento B8.
15. No existe documentacion de endpoints, filtros y semantica de fechas.

### 4.3 Baseline esperado antes de B8

Con PostgreSQL y Redis activos:

```powershell
Set-Location backend
$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:Santi.15@localhost:5432/sga_test"
$env:TEST_REDIS_URL = "redis://localhost:6379/15"
uv run pytest -q -n 0 --no-cov --tb=short
uv run mypy src tests
```

Referencia de cierre B7:

- 223 pruebas unitarias/API.
- 44 pruebas de integracion B7.
- `mypy` sin errores.
- `ruff` sin errores.

No iniciar B8 con pruebas rojas, deuda de tipado ni migraciones sin aplicar.

---

## 5. Requisitos y criterios de aceptacion

| Criterio de aceptacion | Implementacion | Prueba obligatoria |
|---|---|---|
| Buscar los ultimos cinco digitos devuelve todas las coincidencias | `nuc_suffix5` + filtro exacto + indice B-tree | Sembrar dos NUC con el mismo sufijo y verificar que aparecen ambos |
| Las busquedas combinadas no omiten filtros | Validacion de aplicabilidad por tipo + condiciones SQL obligatorias | Enviar `types=BOX&nuc=...` y recibir 422, no una lista de cajas sin filtro |
| La respuesta incluye caja y ubicacion cuando estan confirmadas | `SearchLocationOut` construido desde `Position/Tray/Shelf/Area` | Caja en posicion confirmada devuelve jerarquia completa |
| Los resultados respetan permisos | Filtro por `confidentiality` y permisos de grupo | Rol sin `search.restricted` no ve registros RESTRICTED |
| No se filtra ubicacion de resultados no autorizados | Ubicacion se incluye solo si el grupo y el registro son visibles | Usuario sin `boxes.read` no recibe grupo de cajas ni ubicaciones |
| No hay N+1 | Una consulta por grupo + subconsultas `EXISTS` y agregadas | Contar consultas con SQLAlchemy o `pg_stat_statements` |
| La paginacion es estable | Orden por relevancia/fecha y desempate por `id` | Dos paginas consecutivas no repiten ni omiten filas |
| La ordenacion es segura | Lista blanca por grupo | `sort_by=password` devuelve 422 |
| Las fechas parciales no se inventan | Condiciones por `*_precision` y componentes existentes | Fecha YEAR no coincide con rango de un dia concreto |
| Los indices se usan | `EXPLAIN (ANALYZE, BUFFERS)` sobre datos representativos | NUC exacto, sufijo y trigram usan indice |
| La busqueda queda auditada | `record_audit_event` con accion `search.executed` | Verificar evento sin `q` crudo ni nombres |
| El limite de tasa funciona | Redis `INCR` por usuario y ventana | Superar el limite devuelve 429 |
| No se exponen datos internos | Respuestas Pydantic, errores con sobre estandar | No hay stack traces ni SQL en respuestas |

Ademas, B8 debe cumplir:

- ninguna ruta devuelve modelos ORM sin esquema Pydantic;
- los errores usan el sobre `{"error": {...}}`;
- las busquedas no ejecutan `commit` de datos de negocio, solo el evento de auditoria;
- no se registran en logs el texto crudo de `q`, nombres, NUC ni ubicaciones;
- los identificadores NUC se tratan como texto, nunca como entero;
- no se usan datos de produccion en pruebas;
- los resultados no incluyen notas internas, contenido documental ni datos personales innecesarios.

---

## 6. Modelo de busqueda

### 6.1 Grupos y entidades

| Grupo | Tipo API | Entidad base | Permiso de recurso |
|---|---|---|---|
| Cajas | `BOX` | `Box` | `boxes.read` |
| Expedientes | `CASE_FILE` | `CaseFile` | `cases.read` |
| Documentos administrativos | `ADMINISTRATIVE_DOCUMENT` | `AdministrativeDocument` | `documents.read` |
| Lotes de importacion | `IMPORT_BATCH` | `ImportBatch` | `imports.read` |

El endpoint global busca en `BOX`, `CASE_FILE` y `ADMINISTRATIVE_DOCUMENT`. Los lotes de importacion tienen endpoint especializado y no se mezclan en el global para no exponer metadatos operativos en la barra de busqueda general.

### 6.2 Normalizacion

Se deben distinguir tres formas de normalizacion:

| Uso | Funcion | Resultado |
|---|---|---|
| Identificadores | `normalize_identifier` | Mayusculas, sin espacios, conserva guiones y ceros iniciales. |
| Nombres de personas | `normalize_person_name` | Mayusculas, sin espacios, sin acentos. |
| Texto libre | `normalize_search_text` | Minusculas, espacios colapsados, sin acentos, conserva separacion de palabras. |

Reglas:

1. El NUC se compara con `nuc_normalized`; nunca se convierte a entero.
2. El sufijo se compara con `nuc_suffix5`; no se recalcula en Python para el filtro exacto.
3. El nombre de persona se compara con `Person.normalized_name`; el texto de `q` se normaliza con `normalize_person_name` para esa condicion.
4. Titulos y descripciones se comparan con `lower(immutable_unaccent(...))` y patron `LIKE` escapado.
5. Los codigos de area, anaquel, bandeja, posicion y tribunal se comparan en mayusculas y sin espacios.
6. `escape_like` es obligatorio en todo patron que incluya entrada del usuario.
7. `q` debe tener al menos 3 caracteres despues de recortar espacios.
8. `nuc`, `nuc_last5` y `number` pueden ser mas cortos porque son exactos.
9. No se eliminan ceros iniciales de NUC ni de numeros de caja.
10. No se usa `unaccent` en Python para datos almacenados; se normaliza al escribir y se usa la funcion SQL solo en columnas que no tienen forma normalizada.

### 6.3 Ranking

Cada grupo calcula un `relevance` entero:

| Valor | Tipo | Significado |
|---|---|---|
| 0 | `EXACT` | Coincidencia exacta en un identificador o titulo. |
| 1 | `PREFIX` | El valor empieza por la consulta. |
| 2 | `CONTAINS` | El valor contiene la consulta. |
| 3 | `FILTER` | No hay `q`; el resultado coincide solo por filtros. |

Reglas:

1. Si no hay `q`, todos los resultados tienen `relevance = 3` y `match_type = FILTER`.
2. Si hay `q`, se evalua en este orden: NUC exacto, sufijo exacto, resolucion exacta, numero de caja exacto, codigo de tribunal exacto, luego prefijos, luego contiene.
3. `matched_fields` es una lista de campos donde hubo coincidencia. No es exhaustiva si el resultado coincide por filtros.
4. `relevance` se usa como primer criterio de orden cuando `sort_by = relevance`.
5. El desempate final siempre es `updated_at DESC, id ASC` o el campo de orden elegido con `id ASC`.
6. No se usa similitud trigram como ranking en B8; los trigramas solo aceleran `LIKE '%...%'`.
7. No se usa `ts_rank`, `similarity` ni puntuacion difusa en la respuesta.

### 6.4 Filtros

#### Filtros comunes

| Filtro | Tipo | Aplica a | Semantica |
|---|---|---|---|
| `q` | texto | todos | Texto libre normalizado, minimo 3 caracteres. |
| `types` | lista | global | Tipos solicitados; por defecto todos los permitidos. |
| `limit_per_type` | entero | global | 1 a 50; por defecto 20. |
| `court_id` | UUID | todos | Tribunal del expediente, caja o caja del documento. |
| `year` | entero | todos | Anio del expediente, caja o documento segun el grupo. |
| `box_id` | UUID | todos | Caja del registro; en cajas, la propia caja. |
| `box_type` | enum | todos | Tipo de caja asociada. |
| `number` | texto | todos | Numero visible de caja exacto. |
| `confidentiality` | enum | todos | Nivel solicitado; requiere permiso si no es INTERNAL. |
| `lifecycle_status` | enum | todos | Estado de ciclo de vida del registro del grupo. |
| `verification_status` | enum | expedientes y documentos | Estado de verificacion. |
| `custody_status` | enum | todos | Custodia de la caja asociada. |
| `location_precision` | enum | todos | Precision de ubicacion de la caja asociada. |
| `has_location` | booleano | todos | `true` exige posicion actual; `false` exige ausencia. |
| `area_id` / `area_code` | UUID / texto | todos | Area de la ubicacion actual. |
| `shelf_id` / `shelf_code` | UUID / texto | todos | Anaquel de la ubicacion actual. |
| `tray_id` / `tray_code` | UUID / texto | todos | Bandeja de la ubicacion actual. |
| `position_id` / `position_code` | UUID / texto | todos | Posicion actual. |
| `import_batch_id` | UUID | todos | Lote que tiene una fila vinculada al registro. |
| `import_row_status` | enum | todos | Estado de la fila de importacion vinculada. |
| `import_batch_status` | enum | todos | Estado del lote vinculado. |
| `has_import_incidents` | booleano | todos | Exige al menos una fila WARNING o ERROR vinculada. |
| `has_open_loan` | booleano | cajas y expedientes | Exige o excluye prestamo abierto. |
| `loan_status` | enum | cajas y expedientes | Estado del prestamo abierto. |
| `overdue` | booleano | cajas y expedientes | Prestamo abierto con `due_at < now()`. |
| `available` | booleano | cajas y expedientes | Sin prestamo abierto y caja en estado ACTIVE. |

#### Filtros de expediente

| Filtro | Tipo | Semantica |
|---|---|---|
| `nuc` | texto | NUC exacto normalizado. |
| `nuc_last5` | texto | Exactamente 5 digitos; compara `nuc_suffix5`. |
| `nuc_partial` | texto | Contiene en `nuc_normalized`; minimo 3 caracteres. |
| `name` | texto | Nombre de parte normalizado; contiene en `Person.normalized_name`. |
| `party_role_id` | UUID | Rol de parte exacto. |
| `party_role_code` | texto | Codigo de rol exacto. |
| `sentence` | texto | Numero de resolucion exacto normalizado. |
| `sentence_partial` | texto | Contiene en resolucion; minimo 3 caracteres. |
| `entry_date_from` / `entry_date_to` | fecha | Rango de fecha de entrada por precision. |
| `sentence_date_from` / `sentence_date_to` | fecha | Rango de fecha de sentencia por precision. |
| `has_box` | booleano | Expediente con o sin caja. |

#### Filtros de documento administrativo

| Filtro | Tipo | Semantica |
|---|---|---|
| `title` | texto | Titulo normalizado; contiene. |
| `document_type` | texto | Tipo exacto. |
| `document_month` | entero | Mes del documento, 1 a 12. |
| `document_date_from` / `document_date_to` | fecha | Rango por precision inferida. |

#### Filtros de caja

| Filtro | Tipo | Semantica |
|---|---|---|
| `number` | texto | Numero visible exacto. |
| `box_type` | enum | Tipo de caja. |
| `custody_status` | enum | Custodia. |
| `location_precision` | enum | Precision de ubicacion. |
| `has_location` | booleano | Con o sin posicion actual. |
| `has_open_loan` | booleano | Con o sin prestamo abierto. |
| `loan_status` | enum | Estado del prestamo abierto. |
| `overdue` | booleano | Prestamo vencido. |
| `available` | booleano | Disponible para prestamo. |

#### Filtros de lote de importacion

| Filtro | Tipo | Semantica |
|---|---|---|
| `q` | texto | Nombre de archivo o clave de idempotencia. |
| `import_kind` | enum | Tipo de importacion. |
| `import_status` | enum | Estado del lote. |
| `source_type` | enum | Formato de origen. |
| `created_by` | UUID | Usuario creador. |
| `created_from` / `created_to` | fecha | Rango de creacion. |
| `has_incidents` | booleano | `error_rows > 0` o `warning_rows > 0`. |

### 6.5 Reglas de aplicabilidad por tipo

Si `types` es explicito y un filtro no aplica a alguno de los tipos solicitados, devolver `422 validation_error` con:

```json
{
  "error": {
    "code": "validation_error",
    "message": "El filtro no aplica a todos los tipos solicitados.",
    "details": {
      "reason": "filter_not_applicable",
      "filter": "nuc",
      "applicable_types": ["CASE_FILE"]
    }
  }
}
```

Si `types` no se envia, B8 reduce automaticamente los grupos:

- `nuc`, `nuc_last5`, `nuc_partial`, `name`, `party_role_*`, `sentence*`, `entry_date_*`, `sentence_date_*`, `has_box` -> solo `CASE_FILE`.
- `title`, `document_type`, `document_month`, `document_date_*` -> solo `ADMINISTRATIVE_DOCUMENT`.
- `verification_status` -> `CASE_FILE` y `ADMINISTRATIVE_DOCUMENT`.
- `has_open_loan`, `loan_status`, `overdue`, `available` -> `BOX` y `CASE_FILE`.
- `import_batch_id`, `import_row_status`, `import_batch_status`, `has_import_incidents` -> grupos de entidad (`BOX`, `CASE_FILE`, `ADMINISTRATIVE_DOCUMENT`), no `IMPORT_BATCH`.
- `import_kind`, `import_status`, `source_type`, `created_by`, `created_from`, `created_to`, `has_incidents` -> solo `IMPORT_BATCH`.
- El resto de filtros -> todos los grupos permitidos.

Si la interseccion queda vacia, devolver `422` con `details.reason = "no_applicable_types"`.

### 6.6 Fechas parciales

#### Expedientes

`entry_precision` y `sentence_precision` indican la precision real:

- `YEAR`: solo `*_year` tiene valor.
- `MONTH`: `*_year` y `*_month` tienen valor.
- `DAY`: `*_year`, `*_month` y `*_day` tienen valor.
- `UNKNOWN`: ningun componente tiene valor.

Regla de interseccion:

1. Un registro `YEAR` coincide con un rango si su anio cae dentro del rango.
2. Un registro `MONTH` coincide si su par (anio, mes) intersecta el rango.
3. Un registro `DAY` coincide si su fecha completa intersecta el rango.
4. Un registro `UNKNOWN` nunca coincide con un rango de fecha.
5. No se rellena dia o mes faltante con `1` ni con el dia actual.
6. No se usa `make_date` para precision YEAR o MONTH.

#### Documentos administrativos

No existe columna de precision. Se infiere:

- si `document_day` no es nulo -> `DAY`;
- si `document_month` no es nulo y `document_day` es nulo -> `MONTH`;
- si solo `document_year` no es nulo -> `YEAR`.

Se aplican las mismas reglas de interseccion.

### 6.7 Visibilidad y permisos

#### Permisos nuevos

Agregar en `modules/users/permissions.py`:

```python
SEARCH_RESTRICTED = "search.restricted"
SEARCH_CONFIDENTIAL = "search.confidential"
```

Agregar en `db/seed_rbac.py`:

```python
(
    (
        "search.restricted",
        "Buscar registros restringidos",
        "Incluir resultados con confidencialidad RESTRICTED.",
    ),
)
(
    (
        "search.confidential",
        "Buscar registros confidenciales",
        "Incluir resultados con confidencialidad CONFIDENTIAL.",
    ),
)
```

Matriz inicial propuesta:

| Rol | `search.restricted` | `search.confidential` |
|---|---|---|
| ADMINISTRADOR | Si | Si |
| SUPERVISOR | Si | Si |
| ARCHIVISTA | Si | No |
| DIGITALIZADOR | No | No |
| CONSULTA | No | No |

Reglas:

1. Todo usuario necesita `search.read` para usar cualquier endpoint de busqueda.
2. El grupo de cajas requiere `boxes.read`.
3. El grupo de expedientes requiere `cases.read`.
4. El grupo de documentos requiere `documents.read`.
5. El endpoint de lotes requiere `imports.read`.
6. Los filtros de prestamo requieren `loans.read`.
7. Los filtros de importacion requieren `imports.read`.
8. `INTERNAL` siempre es visible si el usuario tiene el permiso del grupo.
9. `RESTRICTED` requiere `search.restricted`.
10. `CONFIDENTIAL` requiere `search.confidential`; este permiso implica tambien `RESTRICTED`.
11. Si `types` es explicito y el usuario no tiene permiso para uno de los tipos, devolver `403`.
12. Si `types` no se envia, omitir los grupos no permitidos y listarlos en `meta.omitted_types`.
13. Un filtro `confidentiality=RESTRICTED` sin `search.restricted` devuelve `403`.
14. Un filtro `confidentiality=CONFIDENTIAL` sin `search.confidential` devuelve `403`.
15. La ubicacion solo se incluye si el registro y su caja son visibles.
16. Si el registro es visible pero su caja es de mayor confidencialidad, no se incluye la caja ni la ubicacion.

#### Regla de caja asociada

Para expedientes y documentos:

- Si `box_id` es nulo, el registro puede ser visible por su propio nivel.
- Si `box_id` no es nulo, la caja debe ser visible por su nivel de confidencialidad.
- Si la caja no es visible, el registro se excluye del resultado. No se devuelve el registro con ubicacion vacia, porque eso revela su existencia y su relacion.

### 6.8 Prestamos e importaciones

#### Prestamos

Un prestamo esta abierto cuando existe un `LoanItem` con `released_at IS NULL`.

- `has_open_loan=true`: `EXISTS` de item abierto para la caja o el expediente.
- `has_open_loan=false`: `NOT EXISTS`.
- `loan_status`: estado del `Loan` asociado al item abierto.
- `overdue=true`: item abierto y `Loan.due_at < now()` con estado `APPROVED` o `DELIVERED`.
- `available=true`: sin item abierto y, para cajas, `Box.lifecycle_status = ACTIVE`.
- `available=false`: con item abierto o caja no activa.

No se devuelve el detalle del prestamo en B8; solo disponibilidad y estado. El detalle pertenece a B9.

#### Importaciones

- `import_batch_id`: existe una fila `ImportRow` vinculada al registro en ese lote.
- `import_row_status`: existe una fila vinculada con ese estado.
- `import_batch_status`: existe una fila vinculada cuyo lote tiene ese estado.
- `has_import_incidents=true`: existe una fila vinculada con estado `WARNING` o `ERROR`.
- `has_import_incidents=false`: no existe fila con esos estados.

No se devuelven `raw_data`, `normalized_data`, `errors` ni `warnings` en B8. Esos datos pertenecen a B10 y pueden contener informacion sensible.

### 6.9 Paginacion y ordenacion

#### Global

- `limit_per_type`: 1 a 50, por defecto 20.
- No hay pagina global; cada grupo tiene su propio limite.
- `sort_by` global permitido: `relevance`, `updated_at`, `created_at`.
- `order`: `asc` o `desc`; `relevance` siempre se ordena ascendente.

#### Especializados

- Usar `PageParams` con `page` y `page_size` (1 a 100, por defecto 25).
- Orden por defecto: `relevance` si hay `q`; `updated_at` descendente si no hay `q`.
- Desempate obligatorio por `id ASC`.
- Listas blancas:

| Endpoint | Campos permitidos |
|---|---|
| `/search/boxes` | `relevance`, `number`, `year`, `updated_at`, `created_at` |
| `/search/case-files` | `relevance`, `nuc`, `year`, `entry_date`, `sentence_date`, `updated_at`, `created_at` |
| `/search/administrative-documents` | `relevance`, `title`, `document_date`, `updated_at`, `created_at` |
| `/search/import-batches` | `relevance`, `created_at`, `completed_at`, `status`, `total_rows` |

### 6.10 Auditoria y limite de tasa

#### Auditoria

Accion: `search.executed`.
Entidad: `search`.
`entity_id`: `null`.

Metadata permitida:

```json
{
  "endpoint": "global",
  "query_length": 12,
  "types": ["BOX", "CASE_FILE"],
  "omitted_types": [],
  "applied_filters": ["q", "court_id", "year"],
  "limit_per_type": 20,
  "counts": {"BOX": 3, "CASE_FILE": 0, "ADMINISTRATIVE_DOCUMENT": 0},
  "partial": false,
  "duration_ms": 42
}
```

Prohibido en auditoria y logs:

- texto crudo de `q`;
- nombres de personas;
- NUC o numero de resolucion;
- numero de caja;
- ubicacion fisica;
- IDs de resultados;
- contenido de filas de importacion.

Si la auditoria falla, la busqueda debe fallar. No se acepta una busqueda exitosa sin evento de auditoria.

#### Limite de tasa

Configuracion:

```python
search_rate_limit_enabled: bool = True
search_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
search_rate_limit_requests: int = Field(default=60, ge=1, le=10000)
search_rate_limit_fail_open: bool = False
```

Reglas:

1. Clave Redis: `sga:search:rate:{user_id}:{window}`.
2. `INCR` y `EXPIRE` en la primera peticion de la ventana.
3. Si se supera el limite, `429 rate_limited` con `details.retry_after_seconds`.
4. Si Redis falla y `fail_open=false`, devolver `503 service_unavailable`.
5. Si Redis falla y `fail_open=true`, registrar advertencia y permitir la busqueda. Solo usar en desarrollo.
6. El limite se aplica a todos los endpoints de busqueda.
7. No se usa el limite para reemplazar permisos ni para proteger datos.

---

## 7. Arquitectura y arbol de archivos

### 7.1 Principios

- Mantener la arquitectura modular de `ADR-0002`: `models/schemas/repositories/services/routers`.
- El modulo `search` es de solo lectura y no define modelos ORM.
- El repositorio encapsula SQL, joins, subconsultas y ranking.
- El servicio valida permisos, aplicabilidad, auditoria y limite de tasa.
- El router solo declara parametros, dependencias y respuestas.
- No duplicar normalizacion: reutilizar `core/text.py` y `case_files/validators.py`.
- No duplicar paginacion: reutilizar `core/pagination.py`.
- No importar `api` desde modulos.
- No crear utilidades globales si una existente resuelve el caso.

### 7.2 Arbol objetivo

```text
backend/
  alembic/versions/
    20261106_0001_b8_search_indexes.py                NUEVO
  src/judicial_archive/modules/
    search/
      __init__.py                                      NUEVO
      access.py                                        NUEVO
      filters.py                                       NUEVO
      normalizers.py                                   NUEVO
      schemas.py                                       NUEVO
      repositories.py                                  NUEVO
      services.py                                      NUEVO
      rate_limit.py                                    NUEVO
      routers.py                                       NUEVO
    users/
      permissions.py                                   AMPLIAR
    api/v1/
      router.py                                        AMPLIAR
  src/judicial_archive/core/
    config.py                                          AMPLIAR
  src/judicial_archive/db/
    seed_rbac.py                                       AMPLIAR
  tests/unit/
    test_search_normalization.py                       NUEVO
    test_search_filters.py                             NUEVO
    test_search_access.py                              NUEVO
    test_search_schemas.py                             NUEVO
  tests/api/
    test_search_api.py                                 NUEVO
    test_search_specialized_api.py                     NUEVO
    test_search_rate_limit_api.py                      NUEVO
  tests/integration/
    test_b8_search_accuracy.py                         NUEVO
    test_b8_search_permissions.py                      NUEVO
    test_b8_search_indexes.py                          NUEVO
    test_b8_search_audit.py                            NUEVO
    test_b8_search_performance.py                      NUEVO (marcada slow)
  scripts/
    create_search_indexes_concurrently.sql             NUEVO (opcional para produccion)
    seed_search_benchmark.sql                          NUEVO (opcional)
  docs/
    api.md                                             ACTUALIZAR
    modelo-de-datos.md                                 ACTUALIZAR
    reglas-de-negocio.md                               ACTUALIZAR
    pruebas.md                                         ACTUALIZAR
    seguridad.md                                       ACTUALIZAR
    roles-y-permisos.md                                ACTUALIZAR
    pendientes-de-validacion.md                        ACTUALIZAR
    decisiones/ADR-0013-extensiones-y-politica-busqueda.md NUEVO
```

No crear `modules/search/models.py` en B8. No mover modelos existentes.

### 7.3 Regla de dependencias

```text
core <- db <- modules <- api
```

Dependencias permitidas:

- `search.repositories` importa modelos de `boxes`, `case_files`, `administrative_documents`, `locations`, `courts`, `imports`, `loans`.
- `search.services` importa `UsersRepository`, `record_audit_event` y `search.repositories`.
- `search.routers` importa `search.services`, `search.filters`, `search.schemas` y permisos.
- `search` no importa routers de otros modulos.
- `search` no modifica modelos ni escribe datos de negocio.
- `search` no importa `api`.

---

## 8. Implementacion paso a paso

### 8.1 Paso 1 - Permisos, configuracion y limite de tasa

Editar `backend/src/judicial_archive/modules/users/permissions.py`:

```python
# Catalogos y busqueda
CATALOG_READ = "catalog.read"
CATALOG_MANAGE = "catalog.manage"
SEARCH_READ = "search.read"
SEARCH_RESTRICTED = "search.restricted"
SEARCH_CONFIDENTIAL = "search.confidential"
```

Editar `backend/src/judicial_archive/db/seed_rbac.py` dentro de `PERMISSIONS`:

```python
(("search.read", "Busqueda global", "Ejecutar busquedas autorizadas."),)
(
    (
        "search.restricted",
        "Buscar registros restringidos",
        "Incluir resultados con confidencialidad RESTRICTED.",
    ),
)
(
    (
        "search.confidential",
        "Buscar registros confidenciales",
        "Incluir resultados con confidencialidad CONFIDENTIAL.",
    ),
)
```

Actualizar `ROLE_PERMISSIONS`:

```python
"SUPERVISOR": (
    # ...
    "search.read",
    "search.restricted",
    "search.confidential",
    # ...
),
"ARCHIVISTA": (
    # ...
    "search.read",
    "search.restricted",
    # ...
),
"DIGITALIZADOR": (
    # ...
    "search.read",
    # sin permisos de confidencialidad
),
"CONSULTA": (
    # ...
    "search.read",
    # sin permisos de confidencialidad
),
```

`ADMINISTRADOR` ya recibe todos los permisos con `tuple(code for code, _, _ in PERMISSIONS)`.

Editar `backend/src/judicial_archive/core/config.py`:

```python
# Busqueda
search_rate_limit_enabled: bool = True
search_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
search_rate_limit_requests: int = Field(default=60, ge=1, le=10000)
search_rate_limit_fail_open: bool = False
search_max_q_length: int = Field(default=120, ge=3, le=500)
search_min_q_length: int = Field(default=3, ge=1, le=10)
search_max_limit_per_type: int = Field(default=50, ge=1, le=200)
search_default_limit_per_type: int = Field(default=20, ge=1, le=200)
```

Agregar a `.env.example`:

```dotenv
SGA_SEARCH_RATE_LIMIT_ENABLED=true
SGA_SEARCH_RATE_LIMIT_WINDOW_SECONDS=60
SGA_SEARCH_RATE_LIMIT_REQUESTS=60
SGA_SEARCH_RATE_LIMIT_FAIL_OPEN=false
SGA_SEARCH_MAX_Q_LENGTH=120
SGA_SEARCH_MIN_Q_LENGTH=3
SGA_SEARCH_MAX_LIMIT_PER_TYPE=50
SGA_SEARCH_DEFAULT_LIMIT_PER_TYPE=20
```

Los limites de `q` y paginacion deben leerse de `Settings` o mantenerse sincronizados con los `Query` y las validaciones. B8 usa `120`, `3`, `50` y `20` como valores iniciales; si se cambian en configuracion, actualizar ambos lugares o inyectar `Settings` en el router.

Crear `backend/src/judicial_archive/modules/search/rate_limit.py`:

```python
from __future__ import annotations

import time

import structlog
from fastapi import Depends
from redis.asyncio import Redis

from judicial_archive.api.deps import get_app_settings, get_current_user, get_redis
from judicial_archive.core.config import Settings
from judicial_archive.core.errors import RateLimitedError, ServiceUnavailableError
from judicial_archive.modules.users.models import User

logger = structlog.get_logger(__name__)


async def enforce_search_rate_limit(
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_app_settings),
) -> None:
    if not settings.search_rate_limit_enabled:
        return

    now = int(time.time())
    window = now // settings.search_rate_limit_window_seconds
    retry_after = settings.search_rate_limit_window_seconds - (
        now % settings.search_rate_limit_window_seconds
    )
    key = f"sga:search:rate:{current_user.id}:{window}"

    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, settings.search_rate_limit_window_seconds)
    except Exception:
        logger.exception("search_rate_limit_unavailable")
        if settings.search_rate_limit_fail_open:
            return
        raise ServiceUnavailableError(
            "El servicio de busqueda no esta disponible temporalmente."
        ) from None

    if count > settings.search_rate_limit_requests:
        raise RateLimitedError(
            "Demasiadas busquedas. Intente de nuevo mas tarde.",
            details={"retry_after_seconds": retry_after},
        )
```

La dependencia no recibe `Request` porque el limite se aplica por usuario y ventana temporal. Si mas adelante se necesita `request_id`, agregarlo en ese momento.

### 8.2 Paso 2 - Migracion Alembic de extensiones e indices

Crear la revision:

```powershell
Set-Location backend
uv run alembic heads
uv run alembic revision -m "b8 search indexes"
```

Renombrar el archivo generado a:

```text
backend/alembic/versions/20261106_0001_b8_search_indexes.py
```

Usar el `down_revision` que devuelva `alembic heads`. Al cierre B7 la cabeza es `20261105_0002`, pero verificar antes de escribir.

Contenido de referencia:

```python
"""B8: extensiones, funcion inmutable e indices de busqueda.

Revision ID: 20261106_0001
Revises: 20261105_0002
Create Date: 2026-11-06
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20261106_0001"
down_revision: str | Sequence[str] | None = "20261105_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.immutable_unaccent(value text)
        RETURNS text
        LANGUAGE sql
        IMMUTABLE
        PARALLEL SAFE
        STRICT
        AS $$
            SELECT public.unaccent('public.unaccent'::regdictionary, value)
        $$
        """
    )

    # Trigramas para busqueda parcial.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_persons_normalized_name_trgm "
        "ON persons USING gin (normalized_name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_case_files_nuc_trgm "
        "ON case_files USING gin (nuc_normalized gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_case_files_resolution_trgm "
        "ON case_files USING gin "
        "(lower(public.immutable_unaccent(resolution_number)) gin_trgm_ops) "
        "WHERE resolution_number IS NOT NULL AND deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_boxes_visible_number_trgm "
        "ON boxes USING gin (visible_number gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_boxes_description_trgm "
        "ON boxes USING gin "
        "(lower(public.immutable_unaccent(description)) gin_trgm_ops) "
        "WHERE description IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_admin_documents_title_trgm "
        "ON administrative_documents USING gin "
        "(lower(public.immutable_unaccent(title)) gin_trgm_ops) "
        "WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_admin_documents_description_trgm "
        "ON administrative_documents USING gin "
        "(lower(public.immutable_unaccent(description)) gin_trgm_ops) "
        "WHERE description IS NOT NULL AND deleted_at IS NULL"
    )

    # Filtros combinados.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_case_files_search_filters "
        "ON case_files (court_id, year, lifecycle_status, confidentiality) "
        "WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_boxes_search_filters "
        "ON boxes (court_id, year, box_type, lifecycle_status, custody_status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_admin_documents_search_filters "
        "ON administrative_documents "
        "(document_year, lifecycle_status, verification_status, confidentiality, box_id) "
        "WHERE deleted_at IS NULL"
    )

    # Relaciones de partes y filtros por rol.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_case_parties_person_case "
        "ON case_parties (person_id, case_file_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_case_parties_case_role "
        "ON case_parties (case_file_id, party_role_id)"
    )

    # Vinculos de importacion.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_import_rows_target_box "
        "ON import_rows (target_box_id) WHERE target_box_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_import_rows_target_case "
        "ON import_rows (target_case_file_id) WHERE target_case_file_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_import_rows_target_admin "
        "ON import_rows (target_administrative_document_id) "
        "WHERE target_administrative_document_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_import_rows_batch_status "
        "ON import_rows (batch_id, status)"
    )

    # Prestamos vencidos.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_loans_overdue "
        "ON loans (due_at) "
        "WHERE status IN ('APPROVED', 'DELIVERED') AND due_at IS NOT NULL"
    )

    op.execute("ANALYZE persons")
    op.execute("ANALYZE case_files")
    op.execute("ANALYZE boxes")
    op.execute("ANALYZE administrative_documents")
    op.execute("ANALYZE case_parties")
    op.execute("ANALYZE import_rows")
    op.execute("ANALYZE loans")


def downgrade() -> None:
    for index_name in (
        "ix_loans_overdue",
        "ix_import_rows_batch_status",
        "ix_import_rows_target_admin",
        "ix_import_rows_target_case",
        "ix_import_rows_target_box",
        "ix_case_parties_case_role",
        "ix_case_parties_person_case",
        "ix_admin_documents_search_filters",
        "ix_boxes_search_filters",
        "ix_case_files_search_filters",
        "ix_admin_documents_description_trgm",
        "ix_admin_documents_title_trgm",
        "ix_boxes_description_trgm",
        "ix_boxes_visible_number_trgm",
        "ix_case_files_resolution_trgm",
        "ix_case_files_nuc_trgm",
        "ix_persons_normalized_name_trgm",
    ):
        op.execute(f"DROP INDEX IF EXISTS {index_name}")

    op.execute("DROP FUNCTION IF EXISTS public.immutable_unaccent(text)")
    # No eliminar pg_trgm ni unaccent: pueden ser usadas por otros objetos.
```

Preflight obligatorio:

```sql
SELECT name, default_version, installed_version
FROM pg_available_extensions
WHERE name IN ('pg_trgm', 'unaccent');

SELECT rolsuper
FROM pg_roles
WHERE rolname = current_user;

SELECT count(*) FROM case_files;
SELECT count(*) FROM boxes;
SELECT count(*) FROM administrative_documents;
SELECT count(*) FROM persons;
SELECT count(*) FROM import_rows;
```

Si el usuario de migracion no es superusuario, un DBA debe instalar las extensiones antes:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
```

No crear indices `CONCURRENTLY` dentro de una migracion Alembic normal. Si las tablas son grandes o estan en produccion con trafico, usar `scripts/create_search_indexes_concurrently.sql` fuera de transaccion y luego aplicar la migracion, que omitira los indices existentes por `IF NOT EXISTS`.

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

### 8.3 Paso 3 - Normalizadores, acceso y filtros

Crear `backend/src/judicial_archive/modules/search/normalizers.py`:

```python
from __future__ import annotations

import re
import unicodedata

from judicial_archive.core.errors import InvalidParameterError
from judicial_archive.core.text import escape_like
from judicial_archive.modules.case_files.validators import (
    normalize_identifier,
    normalize_person_name,
)

_SUFFIX5 = re.compile(r"^\d{5}$")


def normalize_search_text(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise InvalidParameterError("El texto de busqueda no puede estar vacio.")
    decomposed = unicodedata.normalize("NFKD", cleaned)
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return without_accents.casefold()


def normalize_name_search(value: str) -> str:
    return normalize_person_name(value)


def normalize_nuc_search(value: str) -> str:
    return normalize_identifier(value)


def normalize_suffix5(value: str) -> str:
    cleaned = value.strip()
    if not _SUFFIX5.fullmatch(cleaned):
        raise InvalidParameterError(
            "Los ultimos cinco digitos deben ser exactamente cinco digitos.",
            details={"field": "nuc_last5"},
        )
    return cleaned


def contains_pattern(value: str) -> str:
    return f"%{escape_like(value)}%"


def prefix_pattern(value: str) -> str:
    return f"{escape_like(value)}%"
```

Crear `backend/src/judicial_archive/modules/search/access.py`:

```python
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from judicial_archive.core.enums import Confidentiality
from judicial_archive.modules.users import permissions


@dataclass(frozen=True)
class SearchAccess:
    codes: frozenset[str]
    allowed_confidentiality: tuple[str, ...]
    can_boxes: bool
    can_cases: bool
    can_documents: bool
    can_imports: bool
    can_loans: bool


def build_access(codes: Sequence[str]) -> SearchAccess:
    code_set = frozenset(codes)
    if permissions.SEARCH_CONFIDENTIAL in code_set:
        allowed = (
            Confidentiality.INTERNAL.value,
            Confidentiality.RESTRICTED.value,
            Confidentiality.CONFIDENTIAL.value,
        )
    elif permissions.SEARCH_RESTRICTED in code_set:
        allowed = (
            Confidentiality.INTERNAL.value,
            Confidentiality.RESTRICTED.value,
        )
    else:
        allowed = (Confidentiality.INTERNAL.value,)

    return SearchAccess(
        codes=code_set,
        allowed_confidentiality=allowed,
        can_boxes=permissions.BOXES_READ in code_set,
        can_cases=permissions.CASES_READ in code_set,
        can_documents=permissions.DOCUMENTS_READ in code_set,
        can_imports=permissions.IMPORTS_READ in code_set,
        can_loans=permissions.LOANS_READ in code_set,
    )
```

Crear `backend/src/judicial_archive/modules/search/filters.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date
from typing import Any
from uuid import UUID

from judicial_archive.core.errors import ForbiddenError, InvalidParameterError
from judicial_archive.modules.search.access import SearchAccess

ALL_ENTITY_TYPES = ("BOX", "CASE_FILE", "ADMINISTRATIVE_DOCUMENT")
ALL_TYPES = (*ALL_ENTITY_TYPES, "IMPORT_BATCH")

CASE_ONLY_FILTERS = frozenset(
    {
        "nuc",
        "nuc_last5",
        "nuc_partial",
        "name",
        "party_role_id",
        "party_role_code",
        "sentence",
        "sentence_partial",
        "entry_date_from",
        "entry_date_to",
        "sentence_date_from",
        "sentence_date_to",
        "has_box",
    }
)
ADMIN_ONLY_FILTERS = frozenset(
    {
        "title",
        "document_type",
        "document_month",
        "document_date_from",
        "document_date_to",
    }
)
LOAN_FILTERS = frozenset({"has_open_loan", "loan_status", "overdue", "available"})
IMPORT_FILTERS = frozenset(
    {
        "import_batch_id",
        "import_row_status",
        "import_batch_status",
        "has_import_incidents",
    }
)
IMPORT_BATCH_ONLY_FILTERS = frozenset(
    {
        "import_kind",
        "import_status",
        "source_type",
        "created_by",
        "created_from",
        "created_to",
        "has_incidents",
    }
)
VERIFICATION_FILTERS = frozenset({"verification_status"})
CONTROL_FIELDS = frozenset({"types", "limit_per_type", "sort_by", "order"})


@dataclass(frozen=True, slots=True)
class SearchFilters:
    q: str | None = None
    types: tuple[str, ...] | None = None
    limit_per_type: int = 20
    court_id: UUID | None = None
    year: int | None = None
    box_id: UUID | None = None
    box_type: str | None = None
    number: str | None = None
    confidentiality: str | None = None
    lifecycle_status: str | None = None
    verification_status: str | None = None
    custody_status: str | None = None
    location_precision: str | None = None
    has_location: bool | None = None
    area_id: UUID | None = None
    area_code: str | None = None
    shelf_id: UUID | None = None
    shelf_code: str | None = None
    tray_id: UUID | None = None
    tray_code: str | None = None
    position_id: UUID | None = None
    position_code: str | None = None
    nuc: str | None = None
    nuc_last5: str | None = None
    nuc_partial: str | None = None
    name: str | None = None
    party_role_id: UUID | None = None
    party_role_code: str | None = None
    sentence: str | None = None
    sentence_partial: str | None = None
    entry_date_from: date | None = None
    entry_date_to: date | None = None
    sentence_date_from: date | None = None
    sentence_date_to: date | None = None
    has_box: bool | None = None
    title: str | None = None
    document_type: str | None = None
    document_month: int | None = None
    document_date_from: date | None = None
    document_date_to: date | None = None
    import_batch_id: UUID | None = None
    import_row_status: str | None = None
    import_batch_status: str | None = None
    has_import_incidents: bool | None = None
    has_open_loan: bool | None = None
    loan_status: str | None = None
    overdue: bool | None = None
    available: bool | None = None
    import_kind: str | None = None
    import_status: str | None = None
    source_type: str | None = None
    created_by: UUID | None = None
    created_from: date | None = None
    created_to: date | None = None
    has_incidents: bool | None = None
    sort_by: str = "relevance"
    order: str = "desc"

    def present_keys(self) -> list[str]:
        keys: list[str] = []
        for field in fields(self):
            if field.name in CONTROL_FIELDS:
                continue
            value: Any = getattr(self, field.name)
            if value is not None and value != "":
                keys.append(field.name)
        return sorted(keys)


def parse_types(value: str | None) -> tuple[str, ...] | None:
    if value is None or not value.strip():
        return None
    parsed = tuple(part.strip().upper() for part in value.split(",") if part.strip())
    invalid = sorted(set(parsed) - set(ALL_TYPES))
    if invalid:
        raise InvalidParameterError(
            "Se solicito un tipo de busqueda no valido.",
            details={"invalid_types": invalid, "allowed_types": list(ALL_TYPES)},
        )
    return parsed


def required_types_for_filters(filters: SearchFilters) -> set[str] | None:
    present = set(filters.present_keys())
    required: set[str] = set(ALL_TYPES)

    if present & CASE_ONLY_FILTERS:
        required &= {"CASE_FILE"}
    if present & ADMIN_ONLY_FILTERS:
        required &= {"ADMINISTRATIVE_DOCUMENT"}
    if present & LOAN_FILTERS:
        required &= {"BOX", "CASE_FILE"}
    if present & IMPORT_FILTERS:
        required &= set(ALL_ENTITY_TYPES)
    if present & IMPORT_BATCH_ONLY_FILTERS:
        required &= {"IMPORT_BATCH"}
    if present & VERIFICATION_FILTERS:
        required &= {"CASE_FILE", "ADMINISTRATIVE_DOCUMENT"}

    if required == set(ALL_TYPES):
        return None
    return required


def _validate_range(
    name_from: str, value_from: date | None, name_to: str, value_to: date | None
) -> None:
    if value_from is not None and value_to is not None and value_to < value_from:
        raise InvalidParameterError(
            "El rango de fechas es invalido.",
            details={"reason": "date_range_invalid", "from": name_from, "to": name_to},
        )


def _require_min_length(value: str | None, *, field: str, minimum: int = 3) -> None:
    if value is not None and len(value.strip()) < minimum:
        raise InvalidParameterError(
            "El filtro es demasiado corto.",
            details={
                "reason": "filter_too_short",
                "field": field,
                "min_length": minimum,
            },
        )


def validate_filters(
    filters: SearchFilters,
    *,
    access: SearchAccess,
    allowed_sort: frozenset[str],
) -> None:
    if filters.sort_by not in allowed_sort:
        raise InvalidParameterError(
            "El campo de ordenamiento no esta permitido.",
            details={
                "reason": "sort_not_allowed",
                "allowed_fields": sorted(allowed_sort),
            },
        )
    if filters.order not in {"asc", "desc"}:
        raise InvalidParameterError(
            "El orden debe ser asc o desc.",
            details={"field": "order"},
        )

    if filters.q is not None:
        q = filters.q.strip()
        if len(q) < 3:
            raise InvalidParameterError(
                "La busqueda debe tener al menos 3 caracteres.",
                details={"reason": "q_too_short", "min_length": 3},
            )
        if len(q) > 120:
            raise InvalidParameterError(
                "La busqueda supera el maximo permitido.",
                details={"reason": "q_too_long", "max_length": 120},
            )

    if not filters.present_keys():
        raise InvalidParameterError(
            "Debe enviar un texto de busqueda o al menos un filtro.",
            details={"reason": "search_criteria_required"},
        )

    if filters.confidentiality is not None and filters.confidentiality not in {
        "INTERNAL",
        "RESTRICTED",
        "CONFIDENTIAL",
    }:
        raise InvalidParameterError(
            "El nivel de confidencialidad no es valido.",
            details={"field": "confidentiality"},
        )
    if filters.location_precision is not None and filters.location_precision not in {
        "CONFIRMED",
        "PENDING",
        "UNKNOWN",
    }:
        raise InvalidParameterError(
            "La precision de ubicacion no es valida.",
            details={"field": "location_precision"},
        )
    if filters.verification_status is not None and filters.verification_status not in {
        "PENDING",
        "CONFIRMED",
        "CONFLICT",
    }:
        raise InvalidParameterError(
            "El estado de verificacion no es valido.",
            details={"field": "verification_status"},
        )

    for field, value in (
        ("nuc_partial", filters.nuc_partial),
        ("name", filters.name),
        ("sentence_partial", filters.sentence_partial),
        ("title", filters.title),
    ):
        _require_min_length(value, field=field)

    if filters.nuc_last5 is not None:
        from judicial_archive.modules.search.normalizers import normalize_suffix5

        normalize_suffix5(filters.nuc_last5)

    if filters.number is not None and not filters.number.strip():
        raise InvalidParameterError(
            "El numero de caja no puede estar vacio.",
            details={"field": "number"},
        )

    if filters.document_month is not None and not 1 <= filters.document_month <= 12:
        raise InvalidParameterError(
            "El mes del documento debe estar entre 1 y 12.",
            details={"field": "document_month"},
        )

    if filters.year is not None and not 1 <= filters.year <= 9999:
        raise InvalidParameterError(
            "El anio debe estar entre 1 y 9999.",
            details={"field": "year"},
        )

    _validate_range(
        "entry_date_from",
        filters.entry_date_from,
        "entry_date_to",
        filters.entry_date_to,
    )
    _validate_range(
        "sentence_date_from",
        filters.sentence_date_from,
        "sentence_date_to",
        filters.sentence_date_to,
    )
    _validate_range(
        "document_date_from",
        filters.document_date_from,
        "document_date_to",
        filters.document_date_to,
    )
    _validate_range(
        "created_from", filters.created_from, "created_to", filters.created_to
    )

    if not 1 <= filters.limit_per_type <= 50:
        raise InvalidParameterError(
            "limit_per_type debe estar entre 1 y 50.",
            details={"field": "limit_per_type"},
        )

    if filters.types is not None:
        invalid = sorted(set(filters.types) - set(ALL_TYPES))
        if invalid:
            raise InvalidParameterError(
                "Se solicito un tipo de busqueda no valido.",
                details={"invalid_types": invalid},
            )
        if not access.can_boxes and "BOX" in filters.types:
            raise ForbiddenError("No tiene permiso para buscar cajas.")
        if not access.can_cases and "CASE_FILE" in filters.types:
            raise ForbiddenError("No tiene permiso para buscar expedientes.")
        if not access.can_documents and "ADMINISTRATIVE_DOCUMENT" in filters.types:
            raise ForbiddenError(
                "No tiene permiso para buscar documentos administrativos."
            )
        if not access.can_imports and "IMPORT_BATCH" in filters.types:
            raise ForbiddenError("No tiene permiso para buscar lotes de importacion.")

        required = required_types_for_filters(filters)
        if required is not None and not required:
            raise InvalidParameterError(
                "La combinacion de filtros no tiene tipos aplicables.",
                details={
                    "reason": "no_applicable_types",
                    "filter": _first_applicable_filter(filters),
                },
            )
        if required is not None and not set(filters.types).issubset(required):
            applicable = sorted(required)
            raise InvalidParameterError(
                "El filtro no aplica a todos los tipos solicitados.",
                details={
                    "reason": "filter_not_applicable",
                    "filter": _first_applicable_filter(filters),
                    "applicable_types": applicable,
                },
            )

    if (
        filters.confidentiality == "RESTRICTED"
        and "search.restricted" not in access.codes
    ):
        raise ForbiddenError("No tiene permiso para buscar registros restringidos.")
    if (
        filters.confidentiality == "CONFIDENTIAL"
        and "search.confidential" not in access.codes
    ):
        raise ForbiddenError("No tiene permiso para buscar registros confidenciales.")

    if (
        filters.present_keys()
        and set(filters.present_keys()) & LOAN_FILTERS
        and not access.can_loans
    ):
        raise ForbiddenError("No tiene permiso para consultar prestamos.")
    if (
        filters.present_keys()
        and set(filters.present_keys()) & IMPORT_FILTERS
        and not access.can_imports
    ):
        raise ForbiddenError("No tiene permiso para consultar importaciones.")

    if filters.has_open_loan is False and (
        filters.loan_status is not None or filters.overdue is True
    ):
        raise InvalidParameterError(
            "has_open_loan=false no se puede combinar con estado o vencimiento de prestamo.",
            details={"reason": "loan_filter_conflict"},
        )
    if filters.available is True and (
        filters.has_open_loan is True
        or filters.loan_status is not None
        or filters.overdue is True
    ):
        raise InvalidParameterError(
            "available=true no se puede combinar con filtros de prestamo abierto.",
            details={"reason": "availability_filter_conflict"},
        )
    if filters.has_box is False and filters.box_id is not None:
        raise InvalidParameterError(
            "has_box=false no se puede combinar con box_id.",
            details={"reason": "box_filter_conflict"},
        )
    location_filters = (
        filters.area_id,
        filters.area_code,
        filters.shelf_id,
        filters.shelf_code,
        filters.tray_id,
        filters.tray_code,
        filters.position_id,
        filters.position_code,
    )
    if filters.has_location is False and any(
        value is not None for value in location_filters
    ):
        raise InvalidParameterError(
            "has_location=false no se puede combinar con filtros de ubicacion.",
            details={"reason": "location_filter_conflict"},
        )


def _first_applicable_filter(filters: SearchFilters) -> str:
    present = set(filters.present_keys())
    applicable = (
        CASE_ONLY_FILTERS
        | ADMIN_ONLY_FILTERS
        | LOAN_FILTERS
        | IMPORT_FILTERS
        | IMPORT_BATCH_ONLY_FILTERS
        | VERIFICATION_FILTERS
    )
    for field in sorted(present & applicable):
        return field
    return "unknown"
```

`required_types_for_filters` devuelve la interseccion de tipos que soportan todos los filtros. Si la interseccion queda vacia, la peticion es contradictoria. La intencion es que un filtro exclusivo de expediente no se combine con `types=BOX`.

### 8.4 Paso 4 - Esquemas Pydantic

Crear `backend/src/judicial_archive/modules/search/schemas.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

MatchType = Literal["EXACT", "PREFIX", "CONTAINS", "FILTER"]


class SearchCourtOut(BaseModel):
    id: UUID
    code: str
    name: str


class SearchLocationOut(BaseModel):
    area_id: UUID | None
    area_code: str | None
    area_name: str | None
    shelf_id: UUID | None
    shelf_code: str | None
    shelf_name: str | None
    tray_id: UUID | None
    tray_code: str | None
    tray_name: str | None
    position_id: UUID | None
    position_code: str | None
    position_label: str | None
    precision: str


class SearchBoxRefOut(BaseModel):
    id: UUID
    visible_number: str
    box_type: str
    lifecycle_status: str
    custody_status: str
    confidentiality: str


class PartialDateOut(BaseModel):
    precision: str
    year: int | None
    month: int | None
    day: int | None


class BoxSearchItem(BaseModel):
    id: UUID
    visible_number: str
    description: str | None
    box_type: str
    year: int
    court: SearchCourtOut
    lifecycle_status: str
    custody_status: str
    location_precision: str
    confidentiality: str
    location: SearchLocationOut | None
    has_open_loan: bool
    loan_status: str | None
    overdue: bool
    available: bool
    matched_fields: list[str] = Field(default_factory=list)
    match_type: MatchType
    relevance: int
    version: int
    updated_at: datetime


class CaseFileSearchItem(BaseModel):
    id: UUID
    nuc_raw: str
    nuc_normalized: str
    nuc_suffix5: str
    year: int
    court: SearchCourtOut
    resolution_number: str | None
    entry: PartialDateOut
    sentence: PartialDateOut
    lifecycle_status: str
    verification_status: str
    confidentiality: str
    box: SearchBoxRefOut | None
    location: SearchLocationOut | None
    party_count: int
    party_names: list[str]
    matched_fields: list[str] = Field(default_factory=list)
    match_type: MatchType
    relevance: int
    version: int
    updated_at: datetime


class AdministrativeDocumentSearchItem(BaseModel):
    id: UUID
    title: str
    document_type: str | None
    document_year: int
    document_month: int | None
    document_day: int | None
    lifecycle_status: str
    verification_status: str
    confidentiality: str
    box: SearchBoxRefOut
    location: SearchLocationOut | None
    matched_fields: list[str] = Field(default_factory=list)
    match_type: MatchType
    relevance: int
    version: int
    updated_at: datetime


class ImportBatchSearchItem(BaseModel):
    id: UUID
    import_kind: str
    source_type: str
    status: str
    original_filename: str | None
    total_files: int
    processed_files: int
    total_rows: int
    valid_rows: int
    warning_rows: int
    error_rows: int
    has_incidents: bool
    submitted_at: datetime | None
    applied_at: datetime | None
    completed_at: datetime | None
    matched_fields: list[str] = Field(default_factory=list)
    match_type: MatchType
    relevance: int
    created_at: datetime
    updated_at: datetime


class SearchGroupError(BaseModel):
    code: str
    message: str


class SearchGroupBox(BaseModel):
    total: int = 0
    items: list[BoxSearchItem] = Field(default_factory=list)
    error: SearchGroupError | None = None


class SearchGroupCaseFile(BaseModel):
    total: int = 0
    items: list[CaseFileSearchItem] = Field(default_factory=list)
    error: SearchGroupError | None = None


class SearchGroupAdminDocument(BaseModel):
    total: int = 0
    items: list[AdministrativeDocumentSearchItem] = Field(default_factory=list)
    error: SearchGroupError | None = None


class SearchGroups(BaseModel):
    boxes: SearchGroupBox | None = None
    case_files: SearchGroupCaseFile | None = None
    administrative_documents: SearchGroupAdminDocument | None = None


class SearchMeta(BaseModel):
    limit_per_type: int
    requested_types: list[str]
    searched_types: list[str]
    omitted_types: list[str]
    applied_filters: list[str]
    took_ms: int


class GlobalSearchResponse(BaseModel):
    query: str | None
    partial: bool
    groups: SearchGroups
    meta: SearchMeta
```

No incluir `notes`, `source`, `created_by` ni datos de importacion crudos. No incluir `judge_name` en la busqueda para reducir datos personales; si se necesita, agregarlo con justificacion y permiso.

### 8.5 Paso 5 - Repositorio de busqueda

Crear `backend/src/judicial_archive/modules/search/repositories.py`. El codigo de referencia se divide por grupo para mantenerlo legible.

#### 8.5.1 Utilidades comunes

```python
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import and_, case, exists, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.enums import (
    BoxLifecycleStatus,
    ImportRowStatus,
    LoanStatus,
)
from judicial_archive.modules.administrative_documents.models import (
    AdministrativeDocument,
)
from judicial_archive.modules.boxes.models import Box
from judicial_archive.modules.case_files.models import CaseFile, CaseParty, Person
from judicial_archive.modules.courts.models import Court, PartyRole
from judicial_archive.modules.imports.models import ImportBatch, ImportRow
from judicial_archive.modules.loans.models import Loan, LoanItem
from judicial_archive.modules.locations.models import Area, Position, Shelf, Tray
from judicial_archive.modules.search.access import SearchAccess
from judicial_archive.modules.search.filters import SearchFilters
from judicial_archive.modules.search.normalizers import (
    contains_pattern,
    normalize_identifier,
    normalize_name_search,
    normalize_search_text,
    prefix_pattern,
)


def _text_expr(column: Any) -> Any:
    return func.lower(func.immutable_unaccent(column))


LoanTarget = Literal["box", "case_file"]
ImportTarget = Literal["box", "case_file", "administrative_document"]


def _open_loan_exists(target: LoanTarget, filters: SearchFilters) -> Any:
    stmt = (
        select(1)
        .select_from(LoanItem)
        .join(Loan, Loan.id == LoanItem.loan_id)
        .where(LoanItem.released_at.is_(None))
    )
    if target == "box":
        stmt = stmt.where(LoanItem.box_id == Box.id)
    else:
        stmt = stmt.where(LoanItem.case_file_id == CaseFile.id)

    if filters.loan_status is not None:
        stmt = stmt.where(Loan.status == filters.loan_status)
    if filters.overdue is True:
        stmt = stmt.where(
            Loan.due_at.is_not(None),
            Loan.due_at < func.now(),
            Loan.status.in_((LoanStatus.APPROVED.value, LoanStatus.DELIVERED.value)),
        )
    return exists(stmt)


def _import_exists(target: ImportTarget, filters: SearchFilters) -> Any:
    if target == "box":
        stmt = (
            select(1)
            .select_from(ImportRow)
            .where(
                ImportRow.target_box_id.is_not(None),
                ImportRow.target_box_id == Box.id,
            )
        )
    elif target == "case_file":
        stmt = (
            select(1)
            .select_from(ImportRow)
            .where(
                ImportRow.target_case_file_id.is_not(None),
                ImportRow.target_case_file_id == CaseFile.id,
            )
        )
    else:
        stmt = (
            select(1)
            .select_from(ImportRow)
            .where(
                ImportRow.target_administrative_document_id.is_not(None),
                ImportRow.target_administrative_document_id
                == AdministrativeDocument.id,
            )
        )

    if filters.import_batch_id is not None:
        stmt = stmt.where(ImportRow.batch_id == filters.import_batch_id)
    if filters.import_row_status is not None:
        stmt = stmt.where(ImportRow.status == filters.import_row_status)
    if filters.has_import_incidents is True:
        stmt = stmt.where(
            ImportRow.status.in_(
                (ImportRowStatus.WARNING.value, ImportRowStatus.ERROR.value)
            )
        )
    if filters.import_batch_status is not None:
        stmt = stmt.join(ImportBatch, ImportBatch.id == ImportRow.batch_id).where(
            ImportBatch.status == filters.import_batch_status
        )
    return exists(stmt)


def _import_filter_condition(target: ImportTarget, filters: SearchFilters) -> Any:
    if filters.has_import_incidents is False:
        without_incident_flag = replace(filters, has_import_incidents=None)
        return ~_import_exists(target, without_incident_flag)
    return _import_exists(target, filters)


def _partial_date_condition(
    model: Any,
    prefix: str,
    date_from: date | None,
    date_to: date | None,
) -> Any | None:
    if date_from is None and date_to is None:
        return None

    year = getattr(model, f"{prefix}_year")
    month = getattr(model, f"{prefix}_month")
    day = getattr(model, f"{prefix}_day")
    precision = getattr(model, f"{prefix}_precision")

    branches: list[Any] = []

    year_branch = and_(precision == "YEAR", year.is_not(None))
    if date_from is not None:
        year_branch = and_(year_branch, year >= date_from.year)
    if date_to is not None:
        year_branch = and_(year_branch, year <= date_to.year)
    branches.append(year_branch)

    month_branch = and_(precision == "MONTH", year.is_not(None), month.is_not(None))
    if date_from is not None:
        month_branch = and_(
            month_branch,
            or_(
                year > date_from.year,
                and_(year == date_from.year, month >= date_from.month),
            ),
        )
    if date_to is not None:
        month_branch = and_(
            month_branch,
            or_(
                year < date_to.year,
                and_(year == date_to.year, month <= date_to.month),
            ),
        )
    branches.append(month_branch)

    day_branch = and_(
        precision == "DAY",
        year.is_not(None),
        month.is_not(None),
        day.is_not(None),
    )
    if date_from is not None:
        day_branch = and_(day_branch, func.make_date(year, month, day) >= date_from)
    if date_to is not None:
        day_branch = and_(day_branch, func.make_date(year, month, day) <= date_to)
    branches.append(day_branch)

    return or_(*branches)


def _document_date_condition(
    date_from: date | None,
    date_to: date | None,
) -> Any | None:
    if date_from is None and date_to is None:
        return None

    year = AdministrativeDocument.document_year
    month = AdministrativeDocument.document_month
    day = AdministrativeDocument.document_day

    branches: list[Any] = []

    year_branch = and_(month.is_(None), year.is_not(None))
    if date_from is not None:
        year_branch = and_(year_branch, year >= date_from.year)
    if date_to is not None:
        year_branch = and_(year_branch, year <= date_to.year)
    branches.append(year_branch)

    month_branch = and_(month.is_not(None), day.is_(None))
    if date_from is not None:
        month_branch = and_(
            month_branch,
            or_(
                year > date_from.year,
                and_(year == date_from.year, month >= date_from.month),
            ),
        )
    if date_to is not None:
        month_branch = and_(
            month_branch,
            or_(
                year < date_to.year,
                and_(year == date_to.year, month <= date_to.month),
            ),
        )
    branches.append(month_branch)

    day_branch = day.is_not(None)
    if date_from is not None:
        day_branch = and_(day_branch, func.make_date(year, month, day) >= date_from)
    if date_to is not None:
        day_branch = and_(day_branch, func.make_date(year, month, day) <= date_to)
    branches.append(day_branch)

    return or_(*branches)
```

#### 8.5.2 Filtros comunes de caja y ubicacion

```python
def _box_location_conditions(filters: SearchFilters) -> list[Any]:
    conditions: list[Any] = []
    if filters.box_id is not None:
        conditions.append(Box.id == filters.box_id)
    if filters.box_type is not None:
        conditions.append(Box.box_type == filters.box_type)
    if filters.number is not None:
        conditions.append(Box.visible_number == filters.number.strip())
    if filters.custody_status is not None:
        conditions.append(Box.custody_status == filters.custody_status)
    if filters.location_precision is not None:
        conditions.append(Box.location_precision == filters.location_precision)
    if filters.has_location is True:
        conditions.append(Box.current_position_id.is_not(None))
    elif filters.has_location is False:
        conditions.append(Box.current_position_id.is_(None))
    if filters.area_id is not None:
        conditions.append(Area.id == filters.area_id)
    if filters.area_code is not None:
        conditions.append(Area.code == normalize_identifier(filters.area_code))
    if filters.shelf_id is not None:
        conditions.append(Shelf.id == filters.shelf_id)
    if filters.shelf_code is not None:
        conditions.append(Shelf.code == normalize_identifier(filters.shelf_code))
    if filters.tray_id is not None:
        conditions.append(Tray.id == filters.tray_id)
    if filters.tray_code is not None:
        conditions.append(Tray.code == normalize_identifier(filters.tray_code))
    if filters.position_id is not None:
        conditions.append(Position.id == filters.position_id)
    if filters.position_code is not None:
        conditions.append(Position.code == normalize_identifier(filters.position_code))
    return conditions


def _box_search_conditions(filters: SearchFilters, access: SearchAccess) -> list[Any]:
    conditions: list[Any] = [Box.confidentiality.in_(access.allowed_confidentiality)]
    if filters.court_id is not None:
        conditions.append(Box.court_id == filters.court_id)
    if filters.year is not None:
        conditions.append(Box.year == filters.year)
    if filters.lifecycle_status is not None:
        conditions.append(Box.lifecycle_status == filters.lifecycle_status)
    if filters.confidentiality is not None:
        conditions.append(Box.confidentiality == filters.confidentiality)
    conditions.extend(_box_location_conditions(filters))

    if filters.has_open_loan is True:
        conditions.append(_open_loan_exists("box", filters))
    elif filters.has_open_loan is False:
        conditions.append(~_open_loan_exists("box", filters))
    if filters.loan_status is not None or filters.overdue is True:
        conditions.append(_open_loan_exists("box", filters))
    if filters.available is True:
        conditions.append(~_open_loan_exists("box", SearchFilters()))
        conditions.append(Box.lifecycle_status == BoxLifecycleStatus.ACTIVE.value)
    elif filters.available is False:
        conditions.append(
            or_(
                _open_loan_exists("box", SearchFilters()),
                Box.lifecycle_status != BoxLifecycleStatus.ACTIVE.value,
            )
        )

    if filters.present_keys() and set(filters.present_keys()) & {
        "import_batch_id",
        "import_row_status",
        "import_batch_status",
        "has_import_incidents",
    }:
        conditions.append(_import_filter_condition("box", filters))
    return conditions
```

`SearchFilters()` vacio se usa solo para construir un `EXISTS` sin filtros de prestamo. Es valido porque no se llama a `validate_filters`. Si se prefiere evitar, crear una funcion `_open_loan_exists_raw(target_column)`.

#### 8.5.3 Busqueda de cajas

```python
class SearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search_boxes(
        self,
        *,
        filters: SearchFilters,
        access: SearchAccess,
        offset: int,
        limit: int,
        sort_by: str,
        order: str,
    ) -> tuple[Sequence[Any], int]:
        conditions = _box_search_conditions(filters, access)
        if filters.q is not None:
            q = filters.q.strip()
            q_ident = normalize_identifier(q)
            q_text = normalize_search_text(q)
            ident_like = contains_pattern(q_ident)
            text_like = contains_pattern(q_text)
            conditions.append(
                or_(
                    Box.visible_number.ilike(ident_like, escape="\\"),
                    _text_expr(Box.description).like(text_like, escape="\\"),
                    Court.code_normalized.ilike(ident_like, escape="\\"),
                    _text_expr(Court.name).like(text_like, escape="\\"),
                    Area.code.ilike(ident_like, escape="\\"),
                    _text_expr(Area.name).like(text_like, escape="\\"),
                    Shelf.code.ilike(ident_like, escape="\\"),
                    _text_expr(Shelf.name).like(text_like, escape="\\"),
                    Tray.code.ilike(ident_like, escape="\\"),
                    _text_expr(Tray.name).like(text_like, escape="\\"),
                    Position.code.ilike(ident_like, escape="\\"),
                    _text_expr(Position.label).like(text_like, escape="\\"),
                )
            )

        base = (
            select(Box, Court, Area, Shelf, Tray, Position)
            .select_from(Box)
            .join(Court, Court.id == Box.court_id)
            .outerjoin(Position, Position.id == Box.current_position_id)
            .outerjoin(Tray, Tray.id == Position.tray_id)
            .outerjoin(Shelf, Shelf.id == Tray.shelf_id)
            .outerjoin(Area, Area.id == Shelf.area_id)
            .where(*conditions)
        )

        total = await self.session.scalar(
            select(func.count()).select_from(base.order_by(None).subquery())
        )

        rank = self._box_rank(filters)
        order_by = self._box_order(filters, rank, sort_by, order)
        rows = await self.session.execute(
            base.order_by(*order_by).offset(offset).limit(limit)
        )
        return rows.all(), int(total or 0)

    def _box_rank(self, filters: SearchFilters) -> Any:
        if filters.q is None:
            return literal(3)
        q_ident = normalize_identifier(filters.q)
        prefix = prefix_pattern(q_ident)
        return case(
            (Box.visible_number == q_ident, 0),
            (Court.code_normalized == q_ident, 0),
            (Box.visible_number.ilike(prefix, escape="\\"), 1),
            (Court.code_normalized.ilike(prefix, escape="\\"), 1),
            else_=2,
        )

    def _box_order(
        self,
        filters: SearchFilters,
        rank: Any,
        sort_by: str,
        order: str,
    ) -> list[Any]:
        if sort_by == "relevance":
            return [rank.asc(), Box.updated_at.desc(), Box.id.asc()]
        column = {
            "number": Box.visible_number,
            "year": Box.year,
            "updated_at": Box.updated_at,
            "created_at": Box.created_at,
        }[sort_by]
        if order == "asc":
            return [column.asc(), Box.id.asc()]
        return [column.desc(), Box.id.asc()]
```

#### 8.5.4 Busqueda de expedientes

```python
async def search_case_files(
    self,
    *,
    filters: SearchFilters,
    access: SearchAccess,
    offset: int,
    limit: int,
    sort_by: str,
    order: str,
) -> tuple[Sequence[Any], int]:
    conditions: list[Any] = [
        CaseFile.deleted_at.is_(None),
        CaseFile.confidentiality.in_(access.allowed_confidentiality),
        or_(
            Box.id.is_(None),
            Box.confidentiality.in_(access.allowed_confidentiality),
        ),
    ]
    if filters.court_id is not None:
        conditions.append(CaseFile.court_id == filters.court_id)
    if filters.year is not None:
        conditions.append(CaseFile.year == filters.year)
    if filters.lifecycle_status is not None:
        conditions.append(CaseFile.lifecycle_status == filters.lifecycle_status)
    if filters.verification_status is not None:
        conditions.append(CaseFile.verification_status == filters.verification_status)
    if filters.confidentiality is not None:
        conditions.append(CaseFile.confidentiality == filters.confidentiality)
    if filters.has_box is True:
        conditions.append(CaseFile.box_id.is_not(None))
    elif filters.has_box is False:
        conditions.append(CaseFile.box_id.is_(None))
    if filters.box_id is not None:
        conditions.append(CaseFile.box_id == filters.box_id)
    conditions.extend(_box_location_conditions(filters))

    if filters.nuc is not None:
        conditions.append(CaseFile.nuc_normalized == normalize_identifier(filters.nuc))
    if filters.nuc_last5 is not None:
        from judicial_archive.modules.search.normalizers import normalize_suffix5

        conditions.append(CaseFile.nuc_suffix5 == normalize_suffix5(filters.nuc_last5))
    if filters.nuc_partial is not None:
        conditions.append(
            CaseFile.nuc_normalized.ilike(
                contains_pattern(normalize_identifier(filters.nuc_partial)),
                escape="\\",
            )
        )
    if filters.name is not None:
        conditions.append(self._party_exists(name=filters.name))
    if filters.party_role_id is not None:
        conditions.append(self._party_exists(party_role_id=filters.party_role_id))
    if filters.party_role_code is not None:
        conditions.append(self._party_exists(party_role_code=filters.party_role_code))
    if filters.sentence is not None:
        conditions.append(
            _text_expr(CaseFile.resolution_number)
            == normalize_search_text(filters.sentence)
        )
    if filters.sentence_partial is not None:
        conditions.append(
            _text_expr(CaseFile.resolution_number).like(
                contains_pattern(normalize_search_text(filters.sentence_partial)),
                escape="\\",
            )
        )

    entry_condition = _partial_date_condition(
        CaseFile, "entry", filters.entry_date_from, filters.entry_date_to
    )
    if entry_condition is not None:
        conditions.append(entry_condition)
    sentence_condition = _partial_date_condition(
        CaseFile, "sentence", filters.sentence_date_from, filters.sentence_date_to
    )
    if sentence_condition is not None:
        conditions.append(sentence_condition)

    if filters.has_open_loan is True:
        conditions.append(_open_loan_exists("case_file", filters))
    elif filters.has_open_loan is False:
        conditions.append(~_open_loan_exists("case_file", filters))
    if filters.loan_status is not None or filters.overdue is True:
        conditions.append(_open_loan_exists("case_file", filters))
    if filters.available is True:
        conditions.append(~_open_loan_exists("case_file", SearchFilters()))
    elif filters.available is False:
        conditions.append(_open_loan_exists("case_file", SearchFilters()))

    if filters.present_keys() and set(filters.present_keys()) & {
        "import_batch_id",
        "import_row_status",
        "import_batch_status",
        "has_import_incidents",
    }:
        conditions.append(_import_filter_condition("case_file", filters))

    if filters.q is not None:
        q = filters.q.strip()
        q_ident = normalize_identifier(q)
        q_text = normalize_search_text(q)
        q_name = normalize_name_search(q)
        ident_like = contains_pattern(q_ident)
        text_like = contains_pattern(q_text)
        name_like = contains_pattern(q_name)
        q_parts: list[Any] = [
            CaseFile.nuc_normalized == q_ident,
            CaseFile.nuc_normalized.ilike(ident_like, escape="\\"),
            CaseFile.nuc_suffix5 == q_ident[-5:]
            if len(q_ident) >= 5
            else literal(False),
            _text_expr(CaseFile.resolution_number) == q_text,
            _text_expr(CaseFile.resolution_number).like(text_like, escape="\\"),
            self._party_exists(
                normalized_name_like=name_like,
                display_name_like=text_like,
                identification_like=ident_like,
            ),
            Box.visible_number.ilike(ident_like, escape="\\"),
            Court.code_normalized.ilike(ident_like, escape="\\"),
            _text_expr(Court.name).like(text_like, escape="\\"),
            Area.code.ilike(ident_like, escape="\\"),
            _text_expr(Area.name).like(text_like, escape="\\"),
            Shelf.code.ilike(ident_like, escape="\\"),
            _text_expr(Shelf.name).like(text_like, escape="\\"),
            Tray.code.ilike(ident_like, escape="\\"),
            _text_expr(Tray.name).like(text_like, escape="\\"),
            Position.code.ilike(ident_like, escape="\\"),
            _text_expr(Position.label).like(text_like, escape="\\"),
        ]
        conditions.append(or_(*q_parts))

    party_count = (
        select(func.count(CaseParty.id))
        .where(CaseParty.case_file_id == CaseFile.id)
        .correlate(CaseFile)
        .scalar_subquery()
    )
    party_names_subq = (
        select(Person.display_name)
        .join(CaseParty, CaseParty.person_id == Person.id)
        .where(
            CaseParty.case_file_id == CaseFile.id,
            Person.deleted_at.is_(None),
        )
        .order_by(Person.display_name)
        .limit(5)
        .correlate(CaseFile)
        .subquery()
    )
    party_names = select(
        func.array_agg(party_names_subq.c.display_name)
    ).scalar_subquery()

    base = (
        select(
            CaseFile,
            Court,
            Box,
            Area,
            Shelf,
            Tray,
            Position,
            party_count.label("party_count"),
            party_names.label("party_names"),
        )
        .select_from(CaseFile)
        .join(Court, Court.id == CaseFile.court_id)
        .outerjoin(Box, Box.id == CaseFile.box_id)
        .outerjoin(Position, Position.id == Box.current_position_id)
        .outerjoin(Tray, Tray.id == Position.tray_id)
        .outerjoin(Shelf, Shelf.id == Tray.shelf_id)
        .outerjoin(Area, Area.id == Shelf.area_id)
        .where(*conditions)
    )

    total = await self.session.scalar(
        select(func.count()).select_from(base.order_by(None).subquery())
    )
    rank = self._case_file_rank(filters)
    order_by = self._case_file_order(filters, rank, sort_by, order)
    rows = await self.session.execute(
        base.order_by(*order_by).offset(offset).limit(limit)
    )
    return rows.all(), int(total or 0)


def _party_exists(
    self,
    *,
    name: str | None = None,
    party_role_id: UUID | None = None,
    party_role_code: str | None = None,
    normalized_name_like: str | None = None,
    display_name_like: str | None = None,
    identification_like: str | None = None,
) -> Any:
    stmt = (
        select(1)
        .select_from(CaseParty)
        .join(Person, Person.id == CaseParty.person_id)
        .where(
            CaseParty.case_file_id == CaseFile.id,
            Person.deleted_at.is_(None),
        )
    )
    if name is not None:
        stmt = stmt.where(
            Person.normalized_name.ilike(
                contains_pattern(normalize_name_search(name)), escape="\\"
            )
        )
    if party_role_id is not None:
        stmt = stmt.where(CaseParty.party_role_id == party_role_id)
    if party_role_code is not None:
        stmt = stmt.join(PartyRole, PartyRole.id == CaseParty.party_role_id).where(
            PartyRole.code == normalize_identifier(party_role_code)
        )
    if normalized_name_like is not None:
        stmt = stmt.where(
            Person.normalized_name.ilike(normalized_name_like, escape="\\")
        )
    if display_name_like is not None:
        stmt = stmt.where(
            _text_expr(Person.display_name).like(display_name_like, escape="\\")
        )
    if identification_like is not None:
        stmt = stmt.where(
            Person.identification_number.ilike(identification_like, escape="\\")
        )
    return exists(stmt)


def _case_file_rank(self, filters: SearchFilters) -> Any:
    if filters.q is None:
        return literal(3)
    q_ident = normalize_identifier(filters.q)
    q_text = normalize_search_text(filters.q)
    prefix = prefix_pattern(q_ident)
    return case(
        (CaseFile.nuc_normalized == q_ident, 0),
        (
            CaseFile.nuc_suffix5 == q_ident[-5:]
            if len(q_ident) >= 5
            else literal(False),
            0,
        ),
        (_text_expr(CaseFile.resolution_number) == q_text, 0),
        (Box.visible_number == q_ident, 0),
        (Court.code_normalized == q_ident, 0),
        (CaseFile.nuc_normalized.ilike(prefix, escape="\\"), 1),
        (Box.visible_number.ilike(prefix, escape="\\"), 1),
        (Court.code_normalized.ilike(prefix, escape="\\"), 1),
        else_=2,
    )


def _case_file_order(
    self,
    filters: SearchFilters,
    rank: Any,
    sort_by: str,
    order: str,
) -> list[Any]:
    if sort_by == "relevance":
        return [rank.asc(), CaseFile.updated_at.desc(), CaseFile.id.asc()]
    if sort_by == "entry_date":
        columns = [CaseFile.entry_year, CaseFile.entry_month, CaseFile.entry_day]
        return self._date_order(columns, order, CaseFile.id)
    if sort_by == "sentence_date":
        columns = [
            CaseFile.sentence_year,
            CaseFile.sentence_month,
            CaseFile.sentence_day,
        ]
        return self._date_order(columns, order, CaseFile.id)
    column = {
        "nuc": CaseFile.nuc_normalized,
        "year": CaseFile.year,
        "updated_at": CaseFile.updated_at,
        "created_at": CaseFile.created_at,
    }[sort_by]
    if order == "asc":
        return [column.asc(), CaseFile.id.asc()]
    return [column.desc(), CaseFile.id.asc()]


def _date_order(self, columns: list[Any], order: str, tie_breaker: Any) -> list[Any]:
    if order == "asc":
        return [column.asc().nullslast() for column in columns] + [tie_breaker.asc()]
    return [column.desc().nullslast() for column in columns] + [tie_breaker.asc()]
```

`_open_loan_exists` usa `CaseFile.id` para expedientes. La condicion `available=false` en expedientes no incluye estado de caja; B8 define disponibilidad de expediente como ausencia de prestamo abierto. Documentarlo.

#### 8.5.5 Busqueda de documentos administrativos

```python
async def search_administrative_documents(
    self,
    *,
    filters: SearchFilters,
    access: SearchAccess,
    offset: int,
    limit: int,
    sort_by: str,
    order: str,
) -> tuple[Sequence[Any], int]:
    conditions: list[Any] = [
        AdministrativeDocument.deleted_at.is_(None),
        AdministrativeDocument.confidentiality.in_(access.allowed_confidentiality),
        Box.confidentiality.in_(access.allowed_confidentiality),
    ]
    if filters.court_id is not None:
        conditions.append(Box.court_id == filters.court_id)
    if filters.year is not None:
        conditions.append(AdministrativeDocument.document_year == filters.year)
    if filters.box_id is not None:
        conditions.append(AdministrativeDocument.box_id == filters.box_id)
    if filters.lifecycle_status is not None:
        conditions.append(
            AdministrativeDocument.lifecycle_status == filters.lifecycle_status
        )
    if filters.verification_status is not None:
        conditions.append(
            AdministrativeDocument.verification_status == filters.verification_status
        )
    if filters.confidentiality is not None:
        conditions.append(
            AdministrativeDocument.confidentiality == filters.confidentiality
        )
    if filters.document_type is not None:
        conditions.append(AdministrativeDocument.document_type == filters.document_type)
    if filters.document_month is not None:
        conditions.append(
            AdministrativeDocument.document_month == filters.document_month
        )
    if filters.title is not None:
        conditions.append(
            _text_expr(AdministrativeDocument.title).like(
                contains_pattern(normalize_search_text(filters.title)), escape="\\"
            )
        )
    conditions.extend(_box_location_conditions(filters))

    document_date = _document_date_condition(
        filters.document_date_from, filters.document_date_to
    )
    if document_date is not None:
        conditions.append(document_date)

    if filters.present_keys() and set(filters.present_keys()) & {
        "import_batch_id",
        "import_row_status",
        "import_batch_status",
        "has_import_incidents",
    }:
        conditions.append(_import_filter_condition("administrative_document", filters))

    if filters.q is not None:
        q = filters.q.strip()
        q_ident = normalize_identifier(q)
        q_text = normalize_search_text(q)
        ident_like = contains_pattern(q_ident)
        text_like = contains_pattern(q_text)
        conditions.append(
            or_(
                _text_expr(AdministrativeDocument.title) == q_text,
                _text_expr(AdministrativeDocument.title).like(text_like, escape="\\"),
                _text_expr(AdministrativeDocument.description).like(
                    text_like, escape="\\"
                ),
                Box.visible_number.ilike(ident_like, escape="\\"),
                Court.code_normalized.ilike(ident_like, escape="\\"),
                _text_expr(Court.name).like(text_like, escape="\\"),
                Area.code.ilike(ident_like, escape="\\"),
                _text_expr(Area.name).like(text_like, escape="\\"),
                Shelf.code.ilike(ident_like, escape="\\"),
                _text_expr(Shelf.name).like(text_like, escape="\\"),
                Tray.code.ilike(ident_like, escape="\\"),
                _text_expr(Tray.name).like(text_like, escape="\\"),
                Position.code.ilike(ident_like, escape="\\"),
                _text_expr(Position.label).like(text_like, escape="\\"),
            )
        )

    base = (
        select(AdministrativeDocument, Box, Court, Area, Shelf, Tray, Position)
        .select_from(AdministrativeDocument)
        .join(Box, Box.id == AdministrativeDocument.box_id)
        .join(Court, Court.id == Box.court_id)
        .outerjoin(Position, Position.id == Box.current_position_id)
        .outerjoin(Tray, Tray.id == Position.tray_id)
        .outerjoin(Shelf, Shelf.id == Tray.shelf_id)
        .outerjoin(Area, Area.id == Shelf.area_id)
        .where(*conditions)
    )

    total = await self.session.scalar(
        select(func.count()).select_from(base.order_by(None).subquery())
    )
    rank = self._admin_document_rank(filters)
    order_by = self._admin_document_order(filters, rank, sort_by, order)
    rows = await self.session.execute(
        base.order_by(*order_by).offset(offset).limit(limit)
    )
    return rows.all(), int(total or 0)


def _admin_document_rank(self, filters: SearchFilters) -> Any:
    if filters.q is None:
        return literal(3)
    q_ident = normalize_identifier(filters.q)
    q_text = normalize_search_text(filters.q)
    prefix_text = prefix_pattern(q_text)
    prefix_ident = prefix_pattern(q_ident)
    return case(
        (_text_expr(AdministrativeDocument.title) == q_text, 0),
        (Box.visible_number == q_ident, 0),
        (Court.code_normalized == q_ident, 0),
        (_text_expr(AdministrativeDocument.title).like(prefix_text, escape="\\"), 1),
        (Box.visible_number.ilike(prefix_ident, escape="\\"), 1),
        (Court.code_normalized.ilike(prefix_ident, escape="\\"), 1),
        else_=2,
    )


def _admin_document_order(
    self,
    filters: SearchFilters,
    rank: Any,
    sort_by: str,
    order: str,
) -> list[Any]:
    if sort_by == "relevance":
        return [
            rank.asc(),
            AdministrativeDocument.updated_at.desc(),
            AdministrativeDocument.id.asc(),
        ]
    if sort_by == "document_date":
        columns = [
            AdministrativeDocument.document_year,
            AdministrativeDocument.document_month,
            AdministrativeDocument.document_day,
        ]
        return self._date_order(columns, order, AdministrativeDocument.id)
    column = {
        "title": _text_expr(AdministrativeDocument.title),
        "updated_at": AdministrativeDocument.updated_at,
        "created_at": AdministrativeDocument.created_at,
    }[sort_by]
    if order == "asc":
        return [column.asc(), AdministrativeDocument.id.asc()]
    return [column.desc(), AdministrativeDocument.id.asc()]
```

#### 8.5.6 Busqueda de lotes de importacion

```python
async def search_import_batches(
    self,
    *,
    filters: SearchFilters,
    offset: int,
    limit: int,
    sort_by: str,
    order: str,
) -> tuple[Sequence[Any], int]:
    conditions: list[Any] = []
    if filters.q is not None:
        q = filters.q.strip()
        like = contains_pattern(q)
        conditions.append(
            or_(
                ImportBatch.original_filename.ilike(like, escape="\\"),
                ImportBatch.idempotency_key.ilike(like, escape="\\"),
            )
        )
    if filters.import_kind is not None:
        conditions.append(ImportBatch.import_kind == filters.import_kind)
    if filters.import_status is not None:
        conditions.append(ImportBatch.status == filters.import_status)
    if filters.source_type is not None:
        conditions.append(ImportBatch.source_type == filters.source_type)
    if filters.created_by is not None:
        conditions.append(ImportBatch.created_by == filters.created_by)
    if filters.created_from is not None:
        conditions.append(
            ImportBatch.created_at
            >= datetime.combine(filters.created_from, time.min, tzinfo=UTC)
        )
    if filters.created_to is not None:
        conditions.append(
            ImportBatch.created_at
            < datetime.combine(
                filters.created_to + timedelta(days=1), time.min, tzinfo=UTC
            )
        )
    if filters.has_incidents is True:
        conditions.append(or_(ImportBatch.error_rows > 0, ImportBatch.warning_rows > 0))
    elif filters.has_incidents is False:
        conditions.append(
            and_(ImportBatch.error_rows == 0, ImportBatch.warning_rows == 0)
        )

    base = select(ImportBatch).where(*conditions)
    total = await self.session.scalar(
        select(func.count()).select_from(base.order_by(None).subquery())
    )
    rank = self._import_batch_rank(filters)
    order_by = self._import_batch_order(rank, sort_by, order)
    rows = await self.session.execute(
        base.order_by(*order_by).offset(offset).limit(limit)
    )
    return rows.all(), int(total or 0)


def _import_batch_rank(self, filters: SearchFilters) -> Any:
    if filters.q is None:
        return literal(3)
    q = filters.q.strip()
    prefix = prefix_pattern(q)
    return case(
        (ImportBatch.original_filename == q, 0),
        (ImportBatch.idempotency_key == q, 0),
        (ImportBatch.original_filename.ilike(prefix, escape="\\"), 1),
        (ImportBatch.idempotency_key.ilike(prefix, escape="\\"), 1),
        else_=2,
    )


def _import_batch_order(self, rank: Any, sort_by: str, order: str) -> list[Any]:
    if sort_by == "relevance":
        return [rank.asc(), ImportBatch.created_at.desc(), ImportBatch.id.asc()]
    column = {
        "created_at": ImportBatch.created_at,
        "completed_at": ImportBatch.completed_at,
        "status": ImportBatch.status,
        "total_rows": ImportBatch.total_rows,
    }[sort_by]
    if order == "asc":
        return [column.asc(), ImportBatch.id.asc()]
    return [column.desc(), ImportBatch.id.asc()]
```

No usar `filters.q` crudo en SQL sin `escape_like`. El unico caso que usa igualdad directa es `original_filename == q`, que es seguro porque no es patron.

---

#### 8.5.7 Subconsultas de prestamo para la respuesta

Agregar estas funciones y columnas a las consultas de cajas y expedientes. No hacer una consulta por resultado.

```python
def _box_open_loan_subqueries() -> tuple[Any, Any, Any]:
    base = (
        select(Loan.id, Loan.status, Loan.due_at)
        .select_from(Loan)
        .join(LoanItem, LoanItem.loan_id == Loan.id)
        .where(LoanItem.box_id == Box.id, LoanItem.released_at.is_(None))
        .order_by(Loan.created_at.desc())
        .limit(1)
        .correlate(Box)
    )
    subq = base.subquery()
    return (
        select(subq.c.id).scalar_subquery(),
        select(subq.c.status).scalar_subquery(),
        select(subq.c.due_at).scalar_subquery(),
    )


def _case_file_open_loan_subqueries() -> tuple[Any, Any, Any]:
    base = (
        select(Loan.id, Loan.status, Loan.due_at)
        .select_from(Loan)
        .join(LoanItem, LoanItem.loan_id == Loan.id)
        .where(LoanItem.case_file_id == CaseFile.id, LoanItem.released_at.is_(None))
        .order_by(Loan.created_at.desc())
        .limit(1)
        .correlate(CaseFile)
    )
    subq = base.subquery()
    return (
        select(subq.c.id).scalar_subquery(),
        select(subq.c.status).scalar_subquery(),
        select(subq.c.due_at).scalar_subquery(),
    )
```

En `search_boxes`, antes de construir `base`:

```python
open_loan_id, open_loan_status, open_loan_due_at = _box_open_loan_subqueries()
```

Y en el `select`:

```python
select(
    Box,
    Court,
    Area,
    Shelf,
    Tray,
    Position,
    open_loan_id.label("open_loan_id"),
    open_loan_status.label("open_loan_status"),
    open_loan_due_at.label("open_loan_due_at"),
)
```

En `search_case_files`:

```python
open_loan_id, open_loan_status, open_loan_due_at = _case_file_open_loan_subqueries()
```

Y agregar las tres columnas al `select` de expedientes.

El servicio calcula:

```python
has_open_loan = row.open_loan_id is not None
overdue = bool(
    row.open_loan_due_at is not None
    and row.open_loan_due_at < datetime.now(UTC)
    and row.open_loan_status in {"APPROVED", "DELIVERED"}
)
```

No se devuelve `open_loan_id` en la respuesta.

### 8.6 Paso 6 - Servicio de busqueda

Crear `backend/src/judicial_archive/modules/search/services.py`:

```python
from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.enums import AuditResult
from judicial_archive.core.errors import InvalidParameterError, ServiceUnavailableError
from judicial_archive.core.pagination import Page, PageParams
from judicial_archive.modules.audit.services import record_audit_event
from judicial_archive.modules.search import schemas
from judicial_archive.modules.search.access import SearchAccess, build_access
from judicial_archive.modules.search.filters import (
    ALL_ENTITY_TYPES,
    SearchFilters,
    required_types_for_filters,
    validate_filters,
)
from judicial_archive.modules.search.normalizers import (
    normalize_identifier,
    normalize_search_text,
)
from judicial_archive.modules.search.repositories import SearchRepository
from judicial_archive.modules.users.models import User
from judicial_archive.modules.users.repositories import UsersRepository

logger = structlog.get_logger(__name__)

GLOBAL_SORT_FIELDS = frozenset({"relevance", "updated_at", "created_at"})
BOX_SORT_FIELDS = frozenset({"relevance", "number", "year", "updated_at", "created_at"})
CASE_FILE_SORT_FIELDS = frozenset(
    {"relevance", "nuc", "year", "entry_date", "sentence_date", "updated_at", "created_at"}
)
ADMIN_DOCUMENT_SORT_FIELDS = frozenset(
    {"relevance", "title", "document_date", "updated_at", "created_at"}
)
IMPORT_BATCH_SORT_FIELDS = frozenset(
    {"relevance", "created_at", "completed_at", "status", "total_rows"}
)


def _resolve_types(
    filters: SearchFilters,
    access: SearchAccess,
) -> tuple[list[str], list[str], list[str]]:
    if filters.types is None:
        requested = set(ALL_ENTITY_TYPES)
        allowed = {
            group
            for group, can_read in (
                ("BOX", access.can_boxes),
                ("CASE_FILE", access.can_cases),
                ("ADMINISTRATIVE_DOCUMENT", access.can_documents),
            )
            if can_read
        }
        unauthorized = requested - allowed
        searched = requested & allowed
    else:
        requested = set(filters.types)
        if "IMPORT_BATCH" in requested:
            raise InvalidParameterError(
                "El endpoint global no busca lotes de importacion.",
                details={"reason": "type_not_supported", "supported_types": list(ALL_ENTITY_TYPES)},
            )
        unauthorized = set()
        searched = requested

    required = required_types_for_filters(filters)
    if required is not None:
        searched &= required

    if not searched:
        raise InvalidParameterError(
            "No hay grupos de busqueda aplicables a los filtros enviados.",
            details={"reason": "no_applicable_types"},
        )
    return sorted(requested), sorted(searched), sorted(unauthorized)


def _location_out(
    *,
    precision: str,
    area: Any,
    shelf: Any,
    tray: Any,
    position: Any,
) -> schemas.SearchLocationOut | None:
    if precision == "UNKNOWN":
        return None
    if area is None and shelf is None and tray is None and position is None:
        return None
    return schemas.SearchLocationOut(
        area_id=area.id if area is not None else None,
        area_code=area.code if area is not None else None,
        area_name=area.name if area is not None else None,
        shelf_id=shelf.id if shelf is not None else None,
        shelf_code=shelf.code if shelf is not None else None,
        shelf_name=shelf.name if shelf is not None else None,
        tray_id=tray.id if tray is not None else None,
        tray_code=tray.code if tray is not None else None,
        tray_name=tray.name if tray is not None else None,
        position_id=position.id if position is not None else None,
        position_code=position.code if position is not None else None,
        position_label=position.label if position is not None else None,
        precision=precision,
    )


def _box_ref(box: Any | None) -> schemas.SearchBoxRefOut | None:
    if box is None:
        return None
    return schemas.SearchBoxRefOut(
        id=box.id,
        visible_number=box.visible_number,
        box_type=box.box_type,
        lifecycle_status=box.lifecycle_status,
        custody_status=box.custody_status,
        confidentiality=box.confidentiality,
    )


def _partial_date(model: Any, prefix: str) -> schemas.PartialDateOut:
    return schemas.PartialDateOut(
        precision=getattr(model, f"{prefix}_precision"),
        year=getattr(model, f"{prefix}_year"),
        month=getattr(model, f"{prefix}_month"),
        day=getattr(model, f"{prefix}_day"),
    )


def _box_match(
    row: Any,
    filters: SearchFilters,
) -> tuple[list[str], str, int]:
    if filters.q is None:
        return [], "FILTER", 3
    box, court = row[0], row[1]
    q_ident = normalize_identifier(filters.q)
    q_text = normalize_search_text(filters.q)
    fields: list[str] = []
    exact = False
    prefix = False

    if box.visible_number == q_ident:
        fields.append("number")
        exact = True
    elif box.visible_number.lower().startswith(q_ident.lower()):
        fields.append("number_prefix")
        prefix = True
    elif q_ident.lower() in box.visible_number.lower():
        fields.append("number_partial")

    if court.code_normalized == q_ident:
        fields.append("court_code")
        exact = True
    elif court.code_normalized.startswith(q_ident):
        fields.append("court_code_prefix")
        prefix = True

    if box.description and q_text in _lower_unaccent(box.description):
        fields.append("description")

    if exact:
        return fields, "EXACT", 0
    if prefix:
        return fields, "PREFIX", 1
    return fields or ["location"], "CONTAINS", 2


def _case_file_match(
    row: Any,
    filters: SearchFilters,
) -> tuple[list[str], str, int]:
    if filters.q is None:
        return [], "FILTER", 3
    case_file, court, box = row[0], row[1], row[2]
    q_ident = normalize_identifier(filters.q)
    q_text = normalize_search_text(filters.q)
    fields: list[str] = []
    exact = False
    prefix = False

    if case_file.nuc_normalized == q_ident:
        fields.append("nuc")
        exact = True
    elif len(q_ident) >= 5 and case_file.nuc_suffix5 == q_ident[-5:]:
        fields.append("nuc_suffix5")
        exact = True
    elif case_file.nuc_normalized.startswith(q_ident):
        fields.append("nuc_prefix")
        prefix = True
    elif q_ident in case_file.nuc_normalized:
        fields.append("nuc_partial")

    if case_file.resolution_number:
        resolution = _lower_unaccent(case_file.resolution_number)
        if resolution == q_text:
            fields.append("resolution_number")
            exact = True
        elif resolution.startswith(q_text):
            fields.append("resolution_prefix")
            prefix = True
        elif q_text in resolution:
            fields.append("resolution_partial")

    if box is not None and box.visible_number == q_ident:
        fields.append("box_number")
        exact = True
    if court.code_normalized == q_ident:
        fields.append("court_code")
        exact = True
    elif court.code_normalized.startswith(q_ident):
        fields.append("court_code_prefix")
        prefix = True

    q_name = normalize_name_search(filters.q)
    for party_name in row.party_names or []:
        candidate = normalize_name_search(party_name)
        if candidate == q_name:
            fields.append("party_name")
            break
        if candidate.startswith(q_name):
            fields.append("party_name_prefix")
        elif q_name in candidate:
            fields.append("party_name_partial")

    if exact:
        return fields, "EXACT", 0
    if prefix:
        return fields, "PREFIX", 1
    return fields or ["location"], "CONTAINS", 2


def _admin_document_match(
    row: Any,
    filters: SearchFilters,
) -> tuple[list[str], str, int]:
    if filters.q is None:
        return [], "FILTER", 3
    document, box, court = row[0], row[1], row[2]
    q_ident = normalize_identifier(filters.q)
    q_text = normalize_search_text(filters.q)
    fields: list[str] = []
    exact = False
    prefix = False

    title = _lower_unaccent(document.title)
    if title == q_text:
        fields.append("title")
        exact = True
    elif title.startswith(q_text):
        fields.append("title_prefix")
        prefix = True
    elif q_text in title:
        fields.append("title_partial")

    if document.description and q_text in _lower_unaccent(document.description):
        fields.append("description")
    if box.visible_number == q_ident:
        fields.append("box_number")
        exact = True
    if court.code_normalized == q_ident:
        fields.append("court_code")
        exact = True
    elif court.code_normalized.startswith(q_ident):
        fields.append("court_code_prefix")
        prefix = True

    if exact:
        return fields, "EXACT", 0
    if prefix:
        return fields, "PREFIX", 1
    return fields or ["location"], "CONTAINS", 2


def _import_batch_match(row: Any, filters: SearchFilters) -> tuple[list[str], str, int]:
    if filters.q is None:
        return [], "FILTER", 3
    batch = row[0]
    q = filters.q.strip()
    fields: list[str] = []
    exact = False
    prefix = False
    if batch.original_filename == q:
        fields.append("original_filename")
        exact = True
    elif batch.original_filename and batch.original_filename.lower().startswith(q.lower()):
        fields.append("original_filename_prefix")
        prefix = True
    elif batch.original_filename and q.lower() in batch.original_filename.lower():
        fields.append("original_filename_partial")

    if batch.idempotency_key == q:
        fields.append("idempotency_key")
        exact = True
    elif batch.idempotency_key and batch.idempotency_key.lower().startswith(q.lower()):
        fields.append("idempotency_key_prefix")
        prefix = True

    if exact:
        return fields, "EXACT", 0
    if prefix:
        return fields, "PREFIX", 1
    return fields or ["filters"], "CONTAINS", 2


def _lower_unaccent(value: str) -> str:
    import unicodedata

    decomposed = unicodedata.normalize("NFKD", " ".join(value.strip().split()))
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = SearchRepository(session)
        self.users = UsersRepository(session)

    async def global_search(
        self,
        request: Request,
        actor: User,
        filters: SearchFilters,
    ) -> schemas.GlobalSearchResponse:
        started = time.perf_counter()
        access = build_access(await self.users.get_permission_codes(actor.id))
        validate_filters(filters, access=access, allowed_sort=GLOBAL_SORT_FIELDS)
        requested, searched, omitted = _resolve_types(filters, access)

        groups = schemas.SearchGroups()
        counts: dict[str, int] = {}
        failures = 0

        if "BOX" in searched:
            try:
                async with self.session.begin_nested():
                    rows, total = await self.repository.search_boxes(
                        filters=filters,
                        access=access,
                        offset=0,
                        limit=filters.limit_per_type,
                        sort_by=filters.sort_by,
                        order=filters.order,
                    )
                groups.boxes = schemas.SearchGroupBox(
                    total=total,
                    items=[self._box_item(row, filters) for row in rows],
                )
                counts["BOX"] = total
            except Exception:
                failures += 1
                counts["BOX"] = 0
                groups.boxes = schemas.SearchGroupBox(
                    error=schemas.SearchGroupError(
                        code="search_group_failed",
                        message="No se pudo completar la busqueda de cajas.",
                    )
                )
                logger.exception("search_group_failed", group="BOX")

        if "CASE_FILE" in searched:
            try:
                async with self.session.begin_nested():
                    rows, total = await self.repository.search_case_files(
                        filters=filters,
                        access=access,
                        offset=0,
                        limit=filters.limit_per_type,
                        sort_by=filters.sort_by,
                        order=filters.order,
                    )
                groups.case_files = schemas.SearchGroupCaseFile(
                    total=total,
                    items=[self._case_file_item(row, filters) for row in rows],
                )
                counts["CASE_FILE"] = total
            except Exception:
                failures += 1
                counts["CASE_FILE"] = 0
                groups.case_files = schemas.SearchGroupCaseFile(
                    error=schemas.SearchGroupError(
                        code="search_group_failed",
                        message="No se pudo completar la busqueda de expedientes.",
                    )
                )
                logger.exception("search_group_failed", group="CASE_FILE")

        if "ADMINISTRATIVE_DOCUMENT" in searched:
            try:
                async with self.session.begin_nested():
                    rows, total = await self.repository.search_administrative_documents(
                        filters=filters,
                        access=access,
                        offset=0,
                        limit=filters.limit_per_type,
                        sort_by=filters.sort_by,
                        order=filters.order,
                    )
                groups.administrative_documents = schemas.SearchGroupAdminDocument(
                    total=total,
                    items=[self._admin_document_item(row, filters) for row in rows],
                )
                counts["ADMINISTRATIVE_DOCUMENT"] = total
            except Exception:
                failures += 1
                counts["ADMINISTRATIVE_DOCUMENT"] = 0
                groups.administrative_documents = schemas.SearchGroupAdminDocument(
                    error=schemas.SearchGroupError(
                        code="search_group_failed",
                        message="No se pudo completar la busqueda de documentos administrativos.",
                    )
                )
                logger.exception("search_group_failed", group="ADMINISTRATIVE_DOCUMENT")

        duration_ms = int((time.perf_counter() - started) * 1000)
        partial = failures > 0

        if searched and failures == len(searched):
            await self._audit(
                request,
                actor,
                filters,
                endpoint="global",
                types=searched,
                omitted=omitted,
                counts=counts,
                partial=True,
                duration_ms=duration_ms,
                result=AuditResult.FAILURE,
            )
            await self.session.commit()
            raise ServiceUnavailableError(
                "No se pudo completar la busqueda en este momento."
            )

        await self._audit(
            request,
            actor,
            filters,
            endpoint="global",
            types=searched,
            omitted=omitted,
            counts=counts,
            partial=partial,
            duration_ms=duration_ms,
            result=AuditResult.SUCCESS,
        )
        await self.session.commit()

        return schemas.GlobalSearchResponse(
            query=filters.q,
            partial=partial,
            groups=groups,
            meta=schemas.SearchMeta(
                limit_per_type=filters.limit_per_type,
                requested_types=requested,
                searched_types=searched,
                omitted_types=omitted,
                applied_filters=filters.present_keys(),
                took_ms=duration_ms,
            ),
        )

    async def search_boxes_page(
        self,
        request: Request,
        actor: User,
        filters: SearchFilters,
        params: PageParams,
    ) -> Page[schemas.BoxSearchItem]:
        started = time.perf_counter()
        access = build_access(await self.users.get_permission_codes(actor.id))
        validate_filters(filters, access=access, allowed_sort=BOX_SORT_FIELDS)
        rows, total = await self.repository.search_boxes(
            filters=filters,
            access=access,
            offset=params.offset,
            limit=params.limit,
            sort_by=filters.sort_by,
            order=filters.order,
        )
        items = [self._box_item(row, filters) for row in rows]
        duration_ms = int((time.perf_counter() - started) * 1000)
        await self._audit_page(
            request, actor, filters, "boxes", "BOX", total, len(items), duration_ms
        )
        await self.session.commit()
        return Page[schemas.BoxSearchItem].build(items, total=total, params=params)

    async def search_case_files_page(
        self,
        request: Request,
        actor: User,
        filters: SearchFilters,
        params: PageParams,
    ) -> Page[schemas.CaseFileSearchItem]:
        started = time.perf_counter()
        access = build_access(await self.users.get_permission_codes(actor.id))
        validate_filters(filters, access=access, allowed_sort=CASE_FILE_SORT_FIELDS)
        rows, total = await self.repository.search_case_files(
            filters=filters,
            access=access,
            offset=params.offset,
            limit=params.limit,
            sort_by=filters.sort_by,
            order=filters.order,
        )
        items = [self._case_file_item(row, filters) for row in rows]
        duration_ms = int((time.perf_counter() - started) * 1000)
        await self._audit_page(
            request, actor, filters, "case-files", "CASE_FILE", total, len(items), duration_ms
        )
        await self.session.commit()
        return Page[schemas.CaseFileSearchItem].build(items, total=total, params=params)

    async def search_admin_documents_page(
        self,
        request: Request,
        actor: User,
        filters: SearchFilters,
        params: PageParams,
    ) -> Page[schemas.AdministrativeDocumentSearchItem]:
        started = time.perf_counter()
        access = build_access(await self.users.get_permission_codes(actor.id))
        validate_filters(
            filters, access=access, allowed_sort=ADMIN_DOCUMENT_SORT_FIELDS
        )
        rows, total = await self.repository.search_administrative_documents(
            filters=filters,
            access=access,
            offset=params.offset,
            limit=params.limit,
            sort_by=filters.sort_by,
            order=filters.order,
        )
        items = [self._admin_document_item(row, filters) for row in rows]
        duration_ms = int((time.perf_counter() - started) * 1000)
        await self._audit_page(
            request,
            actor,
            filters,
            "administrative-documents",
            "ADMINISTRATIVE_DOCUMENT",
            total,
            len(items),
            duration_ms,
        )
        await self.session.commit()
        return Page[schemas.AdministrativeDocumentSearchItem].build(
            items, total=total, params=params
        )

    async def search_import_batches_page(
        self,
        request: Request,
        actor: User,
        filters: SearchFilters,
        params: PageParams,
    ) -> Page[schemas.ImportBatchSearchItem]:
        started = time.perf_counter()
        access = build_access(await self.users.get_permission_codes(actor.id))
        validate_filters(
            filters, access=access, allowed_sort=IMPORT_BATCH_SORT_FIELDS
        )
        rows, total = await self.repository.search_import_batches(
            filters=filters,
            offset=params.offset,
            limit=params.limit,
            sort_by=filters.sort_by,
            order=filters.order,
        )
        items = [self._import_batch_item(row, filters) for row in rows]
        duration_ms = int((time.perf_counter() - started) * 1000)
        await self._audit_page(
            request,
            actor,
            filters,
            "import-batches",
            "IMPORT_BATCH",
            total,
            len(items),
            duration_ms,
        )
        await self.session.commit()
        return Page[schemas.ImportBatchSearchItem].build(
            items, total=total, params=params
        )

    def _box_item(
        self, row: Any, filters: SearchFilters
    ) -> schemas.BoxSearchItem:
        box, court, area, shelf, tray, position = (row[0], row[1], row[2], row[3], row[4], row[5])
        matched_fields, match_type, relevance = _box_match(row, filters)
        has_open_loan = row.open_loan_id is not None
        overdue = bool(
            row.open_loan_due_at is not None
            and row.open_loan_due_at < datetime.now(UTC)
            and row.open_loan_status in {"APPROVED", "DELIVERED"}
        )
        available = (not has_open_loan) and box.lifecycle_status == "ACTIVE"
        return schemas.BoxSearchItem(
            id=box.id,
            visible_number=box.visible_number,
            description=box.description,
            box_type=box.box_type,
            year=box.year,
            court=schemas.SearchCourtOut(
                id=court.id, code=court.code_normalized, name=court.name
            ),
            lifecycle_status=box.lifecycle_status,
            custody_status=box.custody_status,
            location_precision=box.location_precision,
            confidentiality=box.confidentiality,
            location=_location_out(
                precision=box.location_precision,
                area=area,
                shelf=shelf,
                tray=tray,
                position=position,
            ),
            has_open_loan=has_open_loan,
            loan_status=row.open_loan_status,
            overdue=overdue,
            available=available,
            matched_fields=matched_fields,
            match_type=match_type,
            relevance=relevance,
            version=box.version,
            updated_at=box.updated_at,
        )

    def _case_file_item(
        self, row: Any, filters: SearchFilters
    ) -> schemas.CaseFileSearchItem:
        case_file, court, box, area, shelf, tray, position = (\n            row[0], row[1], row[2], row[3], row[4], row[5], row[6]\n        )
        matched_fields, match_type, relevance = _case_file_match(row, filters)
        return schemas.CaseFileSearchItem(
            id=case_file.id,
            nuc_raw=case_file.nuc_raw,
            nuc_normalized=case_file.nuc_normalized,
            nuc_suffix5=case_file.nuc_suffix5,
            year=case_file.year,
            court=schemas.SearchCourtOut(
                id=court.id, code=court.code_normalized, name=court.name
            ),
            resolution_number=case_file.resolution_number,
            entry=_partial_date(case_file, "entry"),
            sentence=_partial_date(case_file, "sentence"),
            lifecycle_status=case_file.lifecycle_status,
            verification_status=case_file.verification_status,
            confidentiality=case_file.confidentiality,
            box=_box_ref(box),
            location=_location_out(
                precision=box.location_precision if box is not None else "UNKNOWN",
                area=area,
                shelf=shelf,
                tray=tray,
                position=position,
            ),
            party_count=int(row.party_count or 0),
            party_names=list(row.party_names or []),
            matched_fields=matched_fields,
            match_type=match_type,
            relevance=relevance,
            version=case_file.version,
            updated_at=case_file.updated_at,
        )

    def _admin_document_item(
        self, row: Any, filters: SearchFilters
    ) -> schemas.AdministrativeDocumentSearchItem:
        document, box, court, area, shelf, tray, position = (\n            row[0], row[1], row[2], row[3], row[4], row[5], row[6]\n        )
        matched_fields, match_type, relevance = _admin_document_match(row, filters)
        return schemas.AdministrativeDocumentSearchItem(
            id=document.id,
            title=document.title,
            document_type=document.document_type,
            document_year=document.document_year,
            document_month=document.document_month,
            document_day=document.document_day,
            lifecycle_status=document.lifecycle_status,
            verification_status=document.verification_status,
            confidentiality=document.confidentiality,
            box=_box_ref(box),
            location=_location_out(
                precision=box.location_precision,
                area=area,
                shelf=shelf,
                tray=tray,
                position=position,
            ),
            matched_fields=matched_fields,
            match_type=match_type,
            relevance=relevance,
            version=document.version,
            updated_at=document.updated_at,
        )

    def _import_batch_item(
        self, row: Any, filters: SearchFilters
    ) -> schemas.ImportBatchSearchItem:
        batch = row[0]
        matched_fields, match_type, relevance = _import_batch_match(row, filters)
        return schemas.ImportBatchSearchItem(
            id=batch.id,
            import_kind=batch.import_kind,
            source_type=batch.source_type,
            status=batch.status,
            original_filename=batch.original_filename,
            total_files=batch.total_files,
            processed_files=batch.processed_files,
            total_rows=batch.total_rows,
            valid_rows=batch.valid_rows,
            warning_rows=batch.warning_rows,
            error_rows=batch.error_rows,
            has_incidents=batch.error_rows > 0 or batch.warning_rows > 0,
            submitted_at=batch.submitted_at,
            applied_at=batch.applied_at,
            completed_at=batch.completed_at,
            matched_fields=matched_fields,
            match_type=match_type,
            relevance=relevance,
            created_at=batch.created_at,
            updated_at=batch.updated_at,
        )

    async def _audit(
        self,
        request: Request,
        actor: User,
        filters: SearchFilters,
        *,
        endpoint: str,
        types: list[str],
        omitted: list[str],
        counts: dict[str, int],
        partial: bool,
        duration_ms: int,
        result: AuditResult,
    ) -> None:
        await record_audit_event(
            self.session,
            request=request,
            actor=actor,
            action="search.executed",
            entity_type="search",
            entity_id=None,
            metadata={
                "endpoint": endpoint,
                "query_length": len(filters.q.strip()) if filters.q else 0,
                "types": types,
                "omitted_types": omitted,
                "applied_filters": filters.present_keys(),
                "limit_per_type": filters.limit_per_type,
                "counts": counts,
                "partial": partial,
                "duration_ms": duration_ms,
            },
            result=result,
        )

    async def _audit_page(
        self,
        request: Request,
        actor: User,
        filters: SearchFilters,
        endpoint: str,
        entity_type: str,
        total: int,
        returned: int,
        duration_ms: int,
    ) -> None:
        await self._audit(
            request,
            actor,
            filters,
            endpoint=endpoint,
            types=[entity_type],
            omitted=[],
            counts={"total": total, "returned": returned},
            partial=False,
            duration_ms=duration_ms,
            result=AuditResult.SUCCESS,
        )
```

Ajustes obligatorios antes de implementar:

- Medir `duration_ms` con `time.perf_counter()` en cada metodo especializado.
- `_box_match` y `_case_file_match` deben incluir coincidencias de ubicacion si se desea reportar `location`; la version minima puede devolver `CONTAINS` sin campo especifico.
- `_case_file_item` no debe calcular `has_open_loan` si el esquema no lo expone. Si se decide exponerlo, agregar los campos al esquema y a la respuesta.
- `SearchFilters()` vacio se usa solo para construir `EXISTS` de prestamo sin filtros; documentar o reemplazar por una funcion dedicada.
- El servicio especializado debe capturar errores de base de datos, auditar `FAILURE`, hacer `commit` de la auditoria y devolver `503`; no dejar una excepcion SQL cruda.

### 8.7 Paso 7 - Routers

Crear `backend/src/judicial_archive/modules/search/routers.py`:

```python
from __future__ import annotations

from datetime import date
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
from judicial_archive.modules.search import schemas, services
from judicial_archive.modules.search.filters import SearchFilters, parse_types
from judicial_archive.modules.search.rate_limit import enforce_search_rate_limit
from judicial_archive.modules.users import permissions
from judicial_archive.modules.users.models import User

router = APIRouter(prefix="/search", tags=["Busqueda"])


@router.get("", response_model=schemas.GlobalSearchResponse)
async def global_search(
    request: Request,
    q: Annotated[str | None, Query(max_length=120)] = None,
    types: Annotated[
        str | None, Query(description="BOX,CASE_FILE,ADMINISTRATIVE_DOCUMENT")
    ] = None,
    limit_per_type: Annotated[int, Query(ge=1, le=50)] = 20,
    court_id: UUID | None = None,
    year: Annotated[int | None, Query(ge=1, le=9999)] = None,
    box_id: UUID | None = None,
    box_type: str | None = None,
    number: str | None = None,
    confidentiality: str | None = None,
    lifecycle_status: str | None = None,
    verification_status: str | None = None,
    custody_status: str | None = None,
    location_precision: str | None = None,
    has_location: bool | None = None,
    area_id: UUID | None = None,
    area_code: str | None = None,
    shelf_id: UUID | None = None,
    shelf_code: str | None = None,
    tray_id: UUID | None = None,
    tray_code: str | None = None,
    position_id: UUID | None = None,
    position_code: str | None = None,
    nuc: str | None = None,
    nuc_last5: str | None = None,
    nuc_partial: str | None = None,
    name: str | None = None,
    party_role_id: UUID | None = None,
    party_role_code: str | None = None,
    sentence: str | None = None,
    sentence_partial: str | None = None,
    entry_date_from: date | None = None,
    entry_date_to: date | None = None,
    sentence_date_from: date | None = None,
    sentence_date_to: date | None = None,
    has_box: bool | None = None,
    title: str | None = None,
    document_type: str | None = None,
    document_month: Annotated[int | None, Query(ge=1, le=12)] = None,
    document_date_from: date | None = None,
    document_date_to: date | None = None,
    import_batch_id: UUID | None = None,
    import_row_status: str | None = None,
    import_batch_status: str | None = None,
    has_import_incidents: bool | None = None,
    has_open_loan: bool | None = None,
    loan_status: str | None = None,
    overdue: bool | None = None,
    available: bool | None = None,
    sort_by: str = "relevance",
    order: SortOrder = SortOrder.DESC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_permissions(permissions.SEARCH_READ)),
    _: None = Depends(enforce_search_rate_limit),
) -> schemas.GlobalSearchResponse:
    filters = SearchFilters(
        q=q,
        types=parse_types(types),
        limit_per_type=limit_per_type,
        court_id=court_id,
        year=year,
        box_id=box_id,
        box_type=box_type,
        number=number,
        confidentiality=confidentiality,
        lifecycle_status=lifecycle_status,
        verification_status=verification_status,
        custody_status=custody_status,
        location_precision=location_precision,
        has_location=has_location,
        area_id=area_id,
        area_code=area_code,
        shelf_id=shelf_id,
        shelf_code=shelf_code,
        tray_id=tray_id,
        tray_code=tray_code,
        position_id=position_id,
        position_code=position_code,
        nuc=nuc,
        nuc_last5=nuc_last5,
        nuc_partial=nuc_partial,
        name=name,
        party_role_id=party_role_id,
        party_role_code=party_role_code,
        sentence=sentence,
        sentence_partial=sentence_partial,
        entry_date_from=entry_date_from,
        entry_date_to=entry_date_to,
        sentence_date_from=sentence_date_from,
        sentence_date_to=sentence_date_to,
        has_box=has_box,
        title=title,
        document_type=document_type,
        document_month=document_month,
        document_date_from=document_date_from,
        document_date_to=document_date_to,
        import_batch_id=import_batch_id,
        import_row_status=import_row_status,
        import_batch_status=import_batch_status,
        has_import_incidents=has_import_incidents,
        has_open_loan=has_open_loan,
        loan_status=loan_status,
        overdue=overdue,
        available=available,
        sort_by=sort_by,
        order=order.value,
    )
    return await services.SearchService(session).global_search(
        request, current_user, filters
    )
```

Los endpoints especializados reutilizan los mismos parametros. Para evitar duplicacion excesiva, se puede crear una funcion `build_filters(...)` en `filters.py` que reciba un diccionario de parametros; no crear una dependencia Pydantic con `Query` si el equipo no la usa en el resto del proyecto.

Patron de endpoint especializado:

```python
@router.get("/boxes", response_model=Page[schemas.BoxSearchItem])
async def search_boxes(
    request: Request,
    params: Annotated[PageParams, Depends(pagination_params)],
    q: Annotated[str | None, Query(max_length=120)] = None,
    number: str | None = None,
    court_id: UUID | None = None,
    year: Annotated[int | None, Query(ge=1, le=9999)] = None,
    box_type: str | None = None,
    lifecycle_status: str | None = None,
    custody_status: str | None = None,
    location_precision: str | None = None,
    has_location: bool | None = None,
    has_open_loan: bool | None = None,
    loan_status: str | None = None,
    overdue: bool | None = None,
    available: bool | None = None,
    sort_by: str = "relevance",
    order: SortOrder = SortOrder.DESC,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(
        require_permissions(permissions.SEARCH_READ, permissions.BOXES_READ)
    ),
    _: None = Depends(enforce_search_rate_limit),
) -> Page[schemas.BoxSearchItem]:
    filters = SearchFilters(
        q=q,
        number=number,
        court_id=court_id,
        year=year,
        box_type=box_type,
        lifecycle_status=lifecycle_status,
        custody_status=custody_status,
        location_precision=location_precision,
        has_location=has_location,
        has_open_loan=has_open_loan,
        loan_status=loan_status,
        overdue=overdue,
        available=available,
        sort_by=sort_by,
        order=order.value,
    )
    return await services.SearchService(session).search_boxes_page(
        request, current_user, filters, params
    )
```

Crear los endpoints restantes con el mismo patron:

| Ruta | Permisos | Esquema |
|---|---|---|
| `GET /search/case-files` | `search.read`, `cases.read` | `Page[CaseFileSearchItem]` |
| `GET /search/administrative-documents` | `search.read`, `documents.read` | `Page[AdministrativeDocumentSearchItem]` |
| `GET /search/import-batches` | `search.read`, `imports.read` | `Page[ImportBatchSearchItem]` |

Para `case-files`, incluir todos los filtros de expediente y los comunes de caja/ubicacion. Para `administrative-documents`, incluir `title`, `document_type`, `document_month`, fechas y comunes. Para `import-batches`, incluir `import_kind`, `import_status`, `source_type`, `created_by`, `created_from`, `created_to`, `has_incidents`.

No crear rutas dinamicas como `/search/{type}` antes de las rutas estaticas. FastAPI evalua en orden; las rutas fijas deben declararse primero.

### 8.8 Paso 8 - Registrar router

Editar `backend/src/judicial_archive/api/v1/router.py`:

```python
from judicial_archive.modules.search.routers import router as search_router

# ...
api_router.include_router(search_router)
```

Agregar el import junto a los demas y registrar antes o despues de los routers B7; no hay conflicto de prefijos.

Verificar:

```powershell
Set-Location backend
uv run python -c "from judicial_archive.main import create_app; app=create_app(); print([r.path for r in app.routes if '/search' in r.path])"
```

Debe listar:

```text
/api/v1/search
/api/v1/search/boxes
/api/v1/search/case-files
/api/v1/search/administrative-documents
/api/v1/search/import-batches
```

---

## 9. Pruebas

### 9.1 Unitarias

Crear `backend/tests/unit/test_search_normalization.py`:

- `normalize_search_text("  Jose   Angel  ") == "jose angel"`.
- `normalize_search_text("JOSÉ ÁNGEL") == "jose angel"`.
- `normalize_name_search("  Jose   Angel ") == "JOSEANGEL"`.
- `normalize_nuc_search("  abc-001  ") == "ABC-001"`.
- `normalize_suffix5("00001") == "00001"`.
- `normalize_suffix5("1")`, `normalize_suffix5("0000A")` y `normalize_suffix5("000001")` lanzan `InvalidParameterError`.
- `contains_pattern("50%_")` escapa `%` y `_`.
- `prefix_pattern("ABC") == "ABC%"`.

Crear `backend/tests/unit/test_search_filters.py`:

- Sin `q` ni filtros -> `search_criteria_required`.
- `q="ab"` -> `q_too_short`.
- `nuc_last5="1234"` -> error.
- `nuc_last5="12345"` -> valido.
- `types=("BOX",)` con `nuc` -> `filter_not_applicable`.
- `types=("CASE_FILE",)` con `title` -> `filter_not_applicable`.
- `types=("ADMINISTRATIVE_DOCUMENT",)` con `has_open_loan` -> `filter_not_applicable`.
- `types=("BOX",)` con `has_open_loan` -> valido.
- `types=("BOX",)` con `verification_status` -> `filter_not_applicable`.
- `types=("CASE_FILE", "ADMINISTRATIVE_DOCUMENT")` con `verification_status` -> valido.
- `types=("BOX",)` con `import_kind` -> `filter_not_applicable`.
- `types=("IMPORT_BATCH",)` con `import_kind` -> valido.
- `types=("IMPORT_BATCH",)` con `import_batch_id` -> `filter_not_applicable` porque ese filtro es de fila.
- `entry_date_from > entry_date_to` -> `date_range_invalid`.
- `document_month=13` -> error.
- `has_open_loan=false` con `loan_status` -> `loan_filter_conflict`.
- `available=true` con `overdue=true` -> `availability_filter_conflict`.
- `has_box=false` con `box_id` -> `box_filter_conflict`.
- `has_location=false` con `area_id` -> `location_filter_conflict`.
- `sort_by` no permitido -> `allowed_fields`.
- `limit_per_type=51` -> error.
- `confidentiality=RESTRICTED` sin permiso -> `ForbiddenError`.
- `confidentiality=CONFIDENTIAL` sin permiso -> `ForbiddenError`.
- `has_open_loan` sin `loans.read` -> `ForbiddenError`.
- `import_batch_id` sin `imports.read` -> `ForbiddenError`.

Crear `backend/tests/unit/test_search_access.py`:

- Sin permisos de confidencialidad -> solo `INTERNAL`.
- Con `search.restricted` -> `INTERNAL` y `RESTRICTED`.
- Con `search.confidential` -> los tres niveles.
- `search.confidential` implica `RESTRICTED`.
- Flags de grupo correctos.

Crear `backend/tests/unit/test_search_schemas.py`:

- `PartialDateOut` conserva `precision` y componentes nulos.
- `GlobalSearchResponse` serializa grupos omitidos como `null`.
- `SearchMeta.omitted_types` no contiene grupos buscados.
- `SearchGroupError` no expone SQL ni rutas.

### 9.2 API

Crear `backend/tests/api/test_search_api.py`:

| Caso | Resultado esperado |
|---|---|
| Sin cookie de sesion | 401 |
| Usuario sin `search.read` | 403 |
| `q` vacio y sin filtros | 422 |
| `q` de 2 caracteres | 422 |
| `types` invalido | 422 |
| `types=BOX&nuc=...` | 422 `filter_not_applicable` |
| Global con caja y expediente | 200, ambos grupos |
| Global sin permiso de cajas | 200, grupo `boxes=null`, `omitted_types=["BOX"]` |
| Global con `types=BOX` sin `boxes.read` | 403 |
| `confidentiality=RESTRICTED` sin permiso | 403 |
| `has_open_loan=true` sin `loans.read` | 403 |
| `import_batch_id` sin `imports.read` | 403 |
| `sort_by=password` | 422 |
| `limit_per_type=0` y `=51` | 422 |
| Respuesta de error | sobre `{"error": {...}}` |

Crear `backend/tests/api/test_search_specialized_api.py`:

| Caso | Resultado esperado |
|---|---|
| `/search/boxes` con permiso | 200 `Page[BoxSearchItem]` |
| `/search/boxes` sin `boxes.read` | 403 |
| `/search/case-files` con permiso | 200 |
| `/search/administrative-documents` con permiso | 200 |
| `/search/import-batches` con permiso | 200 |
| `/search/import-batches` sin `imports.read` | 403 |
| Pagina 2 estable | sin duplicados ni omisiones |
| `sort_by=entry_date` en cajas | 422 |
| `page_size=101` | 422 |
| Ruta estatica no capturada por dinamica | 200/422, nunca 404 por orden de rutas |

Crear `backend/tests/api/test_search_rate_limit_api.py`:

- Con limite 2 por ventana, tercera peticion -> 429.
- `details.retry_after_seconds` presente y positivo.
- Usuarios distintos tienen cubos distintos.
- Redis caido y `fail_open=false` -> 503.
- Redis caido y `fail_open=true` -> 200.
- Limite desactivado -> sin 429.

### 9.3 Integracion

Crear `backend/tests/integration/test_b8_search_accuracy.py` con PostgreSQL real:

1. Sembrar dos expedientes con NUC `...00001` y `...00001` en distintos tribunales o cajas; `nuc_last5=00001` devuelve ambos.
2. NUC exacto devuelve solo el expediente correcto.
3. NUC parcial con acentos y espacios devuelve el esperado.
4. Nombre `JOSE ANGEL` coincide con `José Ángel` y con `JOSEANGEL`.
5. Dos personas con el mismo nombre devuelven expedientes distintos sin duplicar filas.
6. Filtro `name` + `court_id` + `year` no omite ninguno.
7. Prefijo de NUC ordena antes que contiene.
8. Coincidencia exacta ordena antes que prefijo.
9. Caja con ubicacion confirmada devuelve area, anaquel, bandeja y posicion.
10. Caja con `location_precision=PENDING` devuelve ubicacion con `precision=PENDING`.
11. Caja sin posicion devuelve `location=null` y `has_location=false`.
12. Filtro `has_location=false` no devuelve cajas con posicion.
13. Filtro por area/anaquel/bandeja/posicion devuelve solo la jerarquia correcta.
14. Expediente sin caja no se excluye cuando no se filtra por caja.
15. Expediente en caja restringida no se devuelve a usuario sin `search.restricted`.
16. Documento en caja confidencial no se devuelve a usuario sin `search.confidential`.
17. `confidentiality=INTERNAL` no devuelve niveles superiores.
18. Fechas YEAR, MONTH y DAY se comportan segun la precision.
19. `entry_date_from=2022-06-15&entry_date_to=2022-06-15` no inventa dia en registros YEAR.
20. Prestamo abierto cambia `available`, `has_open_loan` y `loan_status`.
21. Prestamo vencido devuelve `overdue=true`.
22. Importacion con fila WARNING devuelve `has_import_incidents=true`.
23. Importacion sin incidencias no aparece con `has_import_incidents=true`.
24. Busqueda global no hace N+1: contar consultas y verificar que no crece con el numero de resultados.
25. Paginacion por relevancia y fecha es estable con empates.

Crear `backend/tests/integration/test_b8_search_permissions.py`:

- Matriz de roles: ADMINISTRADOR, SUPERVISOR, ARCHIVISTA, DIGITALIZADOR y CONSULTA.
- Verificar visibilidad de `INTERNAL`, `RESTRICTED` y `CONFIDENTIAL`.
- Verificar que `search.confidential` implica `RESTRICTED`.
- Verificar que un usuario sin `boxes.read` no recibe ubicacion ni grupo de cajas.
- Verificar que un usuario sin `loans.read` no puede filtrar por prestamo.
- Verificar que un usuario sin `imports.read` no puede filtrar por importacion.
- Verificar que un filtro explicito a un tipo no permitido devuelve 403.
- Verificar que un grupo omitido no aparece en `groups`.

Crear `backend/tests/integration/test_b8_search_indexes.py`:

- `pg_trgm` y `unaccent` instaladas.
- `public.immutable_unaccent('José Ángel') == 'Jose Angel'`.
- Existen todos los indices de la migracion.
- `EXPLAIN` de NUC exacto usa `ix_case_files_court_nuc` o un indice equivalente.
- `EXPLAIN` de sufijo usa `ix_case_files_nuc_suffix5`.
- `EXPLAIN` de NUC parcial usa `ix_case_files_nuc_trgm`.
- `EXPLAIN` de nombre usa `ix_persons_normalized_name_trgm`.
- `EXPLAIN` de titulo usa `ix_admin_documents_title_trgm`.
- `EXPLAIN` de numero de caja usa `ix_boxes_visible_number_trgm`.
- No hay `Seq Scan` en tablas grandes para esas consultas.
- Downgrade elimina indices y funcion, pero conserva extensiones.

Crear `backend/tests/integration/test_b8_search_audit.py`:

- Cada busqueda crea un evento `search.executed`.
- El evento tiene `endpoint`, `query_length`, `types`, `applied_filters`, `counts`, `duration_ms`.
- El evento no contiene `q` crudo, nombres, NUC, numero de caja ni ubicacion.
- `entity_type="search"` y `entity_id=null`.
- Un fallo de grupo en global genera `partial=true` y auditoria exitosa.
- Un fallo total genera auditoria `FAILURE` y 503.
- Un fallo de auditoria no devuelve una busqueda exitosa.

Crear `backend/tests/integration/test_b8_search_performance.py` marcada `slow`:

- Sembrar datos de benchmark.
- Medir P50 y P95 de NUC exacto, sufijo, NUC parcial, nombre, titulo y global.
- Verificar umbrales de la seccion 15.6.
- Ejecutar `EXPLAIN (ANALYZE, BUFFERS)` y guardar el plan en el reporte de pruebas.
- No ejecutar en CI normal si no hay base de datos de rendimiento.

### 9.4 Matriz de cobertura

| Requisito B8 | Unitaria | API | Integracion |
|---|---|---|---|
| NUC completo | Si | Si | Si |
| Ultimos cinco digitos | Si | Si | Si |
| NUC parcial | Si | Si | Si |
| Nombre de imputado | Si | Si | Si |
| Tribunal/anio | Si | Si | Si |
| Sentencia/resolucion | Si | Si | Si |
| Fechas parciales | Si | Si | Si |
| Documento administrativo | Si | Si | Si |
| Numero de caja | Si | Si | Si |
| Area/anaquel/bandeja/posicion | Si | Si | Si |
| Ubicacion desconocida/pendiente | Si | Si | Si |
| Prestamo/disponibilidad | Si | Si | Si |
| Importacion/incidencias | Si | Si | Si |
| Permisos/confidencialidad | Si | Si | Si |
| Ranking | Si | Si | Si |
| Paginacion/orden | Si | Si | Si |
| Auditoria | Si | Si | Si |
| Limite de tasa | Si | Si | Si |
| Indices/EXPLAIN | No | No | Si |
| Rendimiento | No | No | Si |

### 9.5 Comandos

```powershell
Set-Location backend

uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src tests

uv run pytest -q tests/unit/test_search_normalization.py
uv run pytest -q tests/unit/test_search_filters.py
uv run pytest -q tests/unit/test_search_access.py
uv run pytest -q tests/unit/test_search_schemas.py

$env:RUN_INTEGRATION = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:Santi.15@localhost:5432/sga_test"
$env:TEST_REDIS_URL = "redis://localhost:6379/15"

uv run pytest -q -n 0 --no-cov --tb=short tests/api/test_search_api.py
uv run pytest -q -n 0 --no-cov --tb=short tests/api/test_search_specialized_api.py
uv run pytest -q -n 0 --no-cov --tb=short tests/api/test_search_rate_limit_api.py
uv run pytest -q -n 0 --no-cov --tb=short tests/integration/test_b8_search_accuracy.py
uv run pytest -q -n 0 --no-cov --tb=short tests/integration/test_b8_search_permissions.py
uv run pytest -q -n 0 --no-cov --tb=short tests/integration/test_b8_search_indexes.py
uv run pytest -q -n 0 --no-cov --tb=short tests/integration/test_b8_search_audit.py

uv run pytest -q -n 0 --no-cov --tb=short -m slow tests/integration/test_b8_search_performance.py
```

Si el marcador `slow` no existe, agregarlo en `backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "slow: pruebas de rendimiento que requieren datos de benchmark",
]
```

No usar `skip` para pruebas B8 en el comando de cierre. Las pruebas `slow` pueden excluirse del CI normal, pero deben ejecutarse antes de cerrar B8.

---

## 10. Documentacion a actualizar

### 10.1 `docs/AGENTS.md`

Agregar en la seccion de busqueda y reglas de negocio:

- B8 es solo lectura; no muta registros.
- Toda busqueda respeta permisos de grupo y confidencialidad.
- `nuc_suffix5` no es unico.
- `q` minimo 3 caracteres; no fuzzy por defecto.
- Los indices requieren `EXPLAIN` real.
- `pg_trgm` y `unaccent` estan aprobadas con funcion inmutable.
- No se registra `q` crudo ni datos personales en auditoria o logs.
- No se cambia el default de confidencialidad de B7 en B8.
- Los filtros de prestamo e importacion son de solo lectura.
- La busqueda tiene limite de tasa.

### 10.2 `docs/modelo-de-datos.md`

Documentar:

- `nuc_suffix5` generado y no unico.
- Indices B-tree, GIN trigram, parciales y compuestos.
- Extensiones `pg_trgm` y `unaccent`.
- Funcion `public.immutable_unaccent`.
- Indices de `import_rows` por objetivo y `loans` vencidos.
- Coste de indices GIN y necesidad de `ANALYZE`.

### 10.3 `docs/reglas-de-negocio.md`

Documentar:

- Semantica de NUC exacto, sufijo y parcial.
- Normalizacion de nombres y texto.
- Ranking exacto, prefijo, contiene y filtros.
- Fechas parciales por precision.
- Visibilidad por confidencialidad.
- Disponibilidad de cajas y expedientes.
- Incidencias de importacion.
- Regla de caja asociada visible.
- Prohibicion de fuzzy por defecto.

### 10.4 `docs/api.md`

Agregar tabla de endpoints, parametros comunes, ejemplos y errores:

| Metodo | Ruta | Permiso minimo | Descripcion |
|---|---|---|---|
| GET | `/api/v1/search` | `search.read` | Busqueda global agrupada. |
| GET | `/api/v1/search/boxes` | `search.read`, `boxes.read` | Busqueda paginada de cajas. |
| GET | `/api/v1/search/case-files` | `search.read`, `cases.read` | Busqueda paginada de expedientes. |
| GET | `/api/v1/search/administrative-documents` | `search.read`, `documents.read` | Busqueda paginada de documentos. |
| GET | `/api/v1/search/import-batches` | `search.read`, `imports.read` | Busqueda paginada de lotes. |

No documentar endpoints de escritura para busqueda.

### 10.5 `docs/pruebas.md`

Agregar:

- Comandos de pruebas B8.
- Dataset de benchmark.
- Umbrales P95.
- Consultas `EXPLAIN` de referencia.
- Procedimiento para ejecutar `slow`.
- Evidencia requerida antes de cerrar B8.

### 10.6 `docs/roles-y-permisos.md`

Agregar:

- `search.restricted`.
- `search.confidential`.
- Matriz inicial por rol.
- Regla de implicacion de `search.confidential`.
- Necesidad de validacion legal de la matriz.

### 10.7 `docs/seguridad.md`

Agregar:

- Auditoria de busqueda redactada.
- Limite de tasa por usuario.
- No exposicion de ubicacion de registros no autorizados.
- No logs de `q`, nombres, NUC ni ubicaciones.
- Riesgo de trigramas y mitigacion.
- Redis no es fuente de verdad.

### 10.8 `docs/pendientes-de-validacion.md`

Agregar:

- Discrepancia D-33: default `RESTRICTED` vs implementacion `INTERNAL`.
- Matriz de permisos de confidencialidad pendiente de aprobacion legal.
- Umbrales de rendimiento dependientes del hardware.
- Necesidad de decidir si `search.confidential` debe implicar `search.restricted` (B8 asume que si).
- Necesidad de decidir si se expone `judge_name` en busqueda (B8 no lo expone).

### 10.9 ADR

Crear `docs/decisiones/ADR-0013-extensiones-y-politica-busqueda.md` con:

- Contexto: busqueda parcial con acentos, datos judiciales y coste.
- Decision: `pg_trgm`, `unaccent`, funcion inmutable, ranking determinista y permisos de confidencialidad.
- Alternativas: solo `LIKE`, full-text `tsvector`, motor externo, fuzzy.
- Consecuencias: indices GIN, coste de escritura, necesidad de `ANALYZE`, extensiones administradas por DBA.
- Seguridad: no fuzzy, no filtrado posterior, auditoria redactada.
- Fecha y responsables.

---

## 11. Puertas de calidad

Antes de cerrar B8:

```powershell
Set-Location backend
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src tests
uv run alembic heads
uv run alembic check
```

Criterios:

1. `ruff` sin errores.
2. `ruff format --check` sin cambios pendientes.
3. `mypy` sin errores.
4. Una sola cabeza Alembic.
5. `alembic check` sin operaciones pendientes.
6. Pruebas unitarias y API B8 en verde.
7. Pruebas de integracion B8 en verde con PostgreSQL real.
8. Pruebas de rendimiento `slow` ejecutadas y documentadas.
9. `EXPLAIN` confirma uso de indices.
10. No hay `Seq Scan` en tablas grandes para NUC exacto, sufijo, trigram y titulo.
11. No hay N+1.
12. Auditoria redactada verificada.
13. Permisos y confidencialidad verificados por rol.
14. Documentacion actualizada.
15. ADR-0013 creada.

No se acepta cerrar B8 con:

- indices creados sin `EXPLAIN`;
- busquedas que filtran en Python despues de traer todos los registros;
- resultados restringidos ocultos solo en el frontend;
- `q` crudo en logs o auditoria;
- fuzzy no documentada;
- migracion sin downgrade probado;
- pruebas de rendimiento sin dataset representativo.

---

## 12. Checklist de aceptacion

- [ ] Modulo `modules/search/` creado.
- [ ] Permisos `search.restricted` y `search.confidential` agregados.
- [ ] Seed RBAC actualizado.
- [ ] Configuracion de busqueda y limite de tasa agregada.
- [ ] Migracion B8 creada con `down_revision` correcto.
- [ ] Extensiones `pg_trgm` y `unaccent` verificadas.
- [ ] Funcion `immutable_unaccent` creada.
- [ ] Indices GIN trigram creados.
- [ ] Indices compuestos y parciales creados.
- [ ] Normalizadores implementados.
- [ ] `SearchAccess` implementado.
- [ ] `SearchFilters` y validacion implementados.
- [ ] Esquemas Pydantic implementados.
- [ ] Repositorio con una consulta por grupo implementado.
- [ ] Subconsultas de prestamo implementadas.
- [ ] Servicio global implementado.
- [ ] Servicios especializados implementados.
- [ ] Routers global y especializados implementados.
- [ ] Router registrado en `api/v1/router.py`.
- [ ] Limite de tasa implementado.
- [ ] Auditoria `search.executed` implementada.
- [ ] NUC completo, sufijo y parcial probados.
- [ ] Nombre de imputado probado.
- [ ] Tribunal, anio y sentencia probados.
- [ ] Fechas parciales probadas.
- [ ] Documento administrativo probado.
- [ ] Numero de caja probado.
- [ ] Area, anaquel, bandeja y posicion probados.
- [ ] Ubicacion desconocida/pendiente probada.
- [ ] Prestamo y disponibilidad probados.
- [ ] Importacion e incidencias probadas.
- [ ] Permisos por rol probados.
- [ ] Confidencialidad probada.
- [ ] Ranking probado.
- [ ] Paginacion estable probada.
- [ ] Ordenacion por lista blanca probada.
- [ ] N+1 verificado.
- [ ] `EXPLAIN` verificado.
- [ ] Rendimiento P95 medido.
- [ ] Documentacion actualizada.
- [ ] ADR-0013 creada.
- [ ] `ruff`, `mypy` y `alembic check` en verde.

---

## 13. Despliegue, migracion y rollback

### 13.1 Preflight

```sql
SELECT version();
SELECT name, default_version, installed_version
FROM pg_available_extensions
WHERE name IN ('pg_trgm', 'unaccent');

SELECT count(*) FROM case_files;
SELECT count(*) FROM boxes;
SELECT count(*) FROM administrative_documents;
SELECT count(*) FROM persons;
SELECT count(*) FROM case_parties;
SELECT count(*) FROM import_rows;
SELECT count(*) FROM loans;
```

Verificar espacio en disco para indices GIN:

```sql
SELECT pg_size_pretty(pg_database_size(current_database()));
```

### 13.2 Respaldo

Antes de migrar:

```powershell
pg_dump --format=custom --file=sga_before_b8.dump $env:SGA_DATABASE_URL
```

No guardar el respaldo en el repositorio. Verificar restauracion en una base temporal.

### 13.3 Orden de despliegue

1. Aplicar migracion en base de prueba.
2. Ejecutar pruebas de integracion B8.
3. Ejecutar `EXPLAIN` y benchmark.
4. Aplicar migracion en staging.
5. Verificar smoke tests.
6. Aplicar en produccion en ventana de mantenimiento.
7. Ejecutar `ANALYZE`.
8. Verificar endpoints y auditoria.
9. Monitorear latencia y errores.

### 13.4 Indices en produccion

Si las tablas son grandes, no crear indices GIN dentro de la transaccion de Alembic. Usar `scripts/create_search_indexes_concurrently.sql` con `psql`:

```powershell
psql $env:SGA_DATABASE_URL -f backend/scripts/create_search_indexes_concurrently.sql
```

Luego:

```powershell
Set-Location backend
uv run alembic upgrade head
```

La migracion usa `IF NOT EXISTS`, por lo que no recrea los indices. Si se usa `CONCURRENTLY`, no ejecutar dentro de una transaccion explicita.

### 13.5 Smoke tests posteriores

```powershell
curl.exe -i "http://localhost:8000/api/v1/search?q=00001&types=CASE_FILE" `
  -H "Cookie: sga_session=..."
```

Verificar:

- 200 con grupos esperados;
- 401 sin cookie;
- 403 con usuario sin permisos;
- 422 con filtro invalido;
- 429 al superar limite;
- evento `search.executed` en auditoria;
- latencia aceptable.

### 13.6 Rollback

```powershell
Set-Location backend
uv run alembic downgrade -1
```

El downgrade elimina indices y la funcion, pero conserva extensiones. Si se crearon indices `CONCURRENTLY`, el downgrade los elimina igualmente.

No revertir la migracion si ya se desplegaron endpoints que dependen de los indices; primero deshabilitar busqueda o volver a la version anterior de la aplicacion.

### 13.7 Post-despliegue

- Ejecutar `ANALYZE` despues de cargas masivas.
- Revisar `pg_stat_user_indexes` para indices no usados.
- Revisar `pg_stat_statements` si esta disponible.
- Revisar latencia P95 y errores 429/503.
- Revisar crecimiento de indices GIN.
- Revisar que no se registren datos sensibles.

---

## 14. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigacion |
|---|---|---|
| Trigramas generan falsos positivos | Resultados poco precisos | Ranking determinista y filtros exactos; no fuzzy. |
| Indices GIN aumentan coste de escritura | Altas mas lentas | Crear solo indices justificados; medir con `EXPLAIN`; monitorear. |
| `unaccent` no es inmutable por defecto | No se puede indexar | Funcion `immutable_unaccent` con diccionario calificado. |
| Permisos de confidencialidad mal asignados | Fuga de datos | Matriz RBAC, pruebas por rol y validacion legal. |
| Filtro ignorado por tipo | Resultado enganoso | Validacion `filter_not_applicable` y pruebas. |
| N+1 en nombres o prestamos | Latencia alta | Subconsultas correlacionadas y una consulta por grupo. |
| `q` crudo en logs | Exposicion de datos personales | Auditoria con `query_length` y `applied_filters`, nunca `q`. |
| Redis caido | Busqueda no disponible o sin limite | `fail_open` configurable; default cerrado en produccion. |
| Indice creado con bloqueo | Downtime | `CONCURRENTLY` en produccion y ventana de mantenimiento. |
| Fechas parciales mal interpretadas | Resultados incorrectos | Condiciones por precision y pruebas dedicadas. |
| `search.confidential` sin `search.restricted` | Niveles inconsistentes | La implementacion trata confidential como implicito de restricted. |
| Default de confidencialidad contradictorio | Decision legal pendiente | No cambiar en B8; documentar D-33. |

---

## 15. Anexos

### 15.1 Tabla de endpoints

| Metodo | Ruta | Permiso | Paginacion | Respuesta |
|---|---|---|---|---|
| GET | `/api/v1/search` | `search.read` | `limit_per_type` | `GlobalSearchResponse` |
| GET | `/api/v1/search/boxes` | `search.read`, `boxes.read` | `page`, `page_size` | `Page[BoxSearchItem]` |
| GET | `/api/v1/search/case-files` | `search.read`, `cases.read` | `page`, `page_size` | `Page[CaseFileSearchItem]` |
| GET | `/api/v1/search/administrative-documents` | `search.read`, `documents.read` | `page`, `page_size` | `Page[AdministrativeDocumentSearchItem]` |
| GET | `/api/v1/search/import-batches` | `search.read`, `imports.read` | `page`, `page_size` | `Page[ImportBatchSearchItem]` |

### 15.2 Payloads de referencia

#### Busqueda global por sufijo

```http
GET /api/v1/search?q=00001&types=CASE_FILE&limit_per_type=20
```

Respuesta:

```json
{
  "query": "00001",
  "partial": false,
  "groups": {
    "boxes": null,
    "case_files": {
      "total": 2,
      "items": [
        {
          "id": "00000000-0000-0000-0000-000000000001",
          "nuc_raw": "EXP-2022-00001",
          "nuc_normalized": "EXP-2022-00001",
          "nuc_suffix5": "00001",
          "year": 2022,
          "court": {
            "id": "00000000-0000-0000-0000-000000000002",
            "code": "TRIBUNAL-1",
            "name": "Tribunal de ejemplo"
          },
          "resolution_number": "RES-001",
          "entry": {"precision": "DAY", "year": 2022, "month": 6, "day": 15},
          "sentence": {"precision": "UNKNOWN", "year": null, "month": null, "day": null},
          "lifecycle_status": "ACTIVE",
          "verification_status": "CONFIRMED",
          "confidentiality": "INTERNAL",
          "box": {
            "id": "00000000-0000-0000-0000-000000000003",
            "visible_number": "0004402",
            "box_type": "EXPEDIENTES",
            "lifecycle_status": "ACTIVE",
            "custody_status": "IN_PLACE",
            "confidentiality": "INTERNAL"
          },
          "location": {
            "area_id": "00000000-0000-0000-0000-000000000004",
            "area_code": "A1",
            "area_name": "Area 1",
            "shelf_id": "00000000-0000-0000-0000-000000000005",
            "shelf_code": "E1",
            "shelf_name": "Estante 1",
            "tray_id": "00000000-0000-0000-0000-000000000006",
            "tray_code": "B1",
            "tray_name": "Bandeja 1",
            "position_id": "00000000-0000-0000-0000-000000000007",
            "position_code": "P01",
            "position_label": "Posicion 1",
            "precision": "CONFIRMED"
          },
          "party_count": 2,
          "party_names": ["Persona Ejemplo"],
          "matched_fields": ["nuc_suffix5"],
          "match_type": "EXACT",
          "relevance": 0,
          "version": 1,
          "updated_at": "2026-11-06T12:00:00Z"
        }
      ],
      "error": null
    },
    "administrative_documents": null
  },
  "meta": {
    "limit_per_type": 20,
    "requested_types": ["CASE_FILE"],
    "searched_types": ["CASE_FILE"],
    "omitted_types": [],
    "applied_filters": ["q"],
    "took_ms": 12
  }
}
```

#### Busqueda de cajas por ubicacion

```http
GET /api/v1/search/boxes?area_code=A1&shelf_code=E1&has_location=true&sort_by=number&order=asc
```

#### Busqueda de documentos por titulo

```http
GET /api/v1/search/administrative-documents?title=resolucion&document_month=6&page=1&page_size=25
```

#### Busqueda de lotes con incidencias

```http
GET /api/v1/search/import-batches?has_incidents=true&import_status=REVIEW_REQUIRED&page=1&page_size=25
```

### 15.3 Errores y motivos

| HTTP | Codigo | `details.reason` | Caso |
|---|---|---|---|
| 401 | `unauthorized` | - | Sin sesion. |
| 403 | `forbidden` | - | Sin permiso de grupo, confidencialidad, prestamo o importacion. |
| 422 | `validation_error` | `q_too_short` | `q` menor a 3. |
| 422 | `validation_error` | `q_too_long` | `q` mayor a 120. |
| 422 | `validation_error` | `search_criteria_required` | Sin `q` ni filtros. |
| 422 | `validation_error` | `filter_not_applicable` | Filtro incompatible con `types`. |
| 422 | `validation_error` | `no_applicable_types` | Interseccion de tipos vacia. |
| 422 | `validation_error` | `loan_filter_conflict` | Filtros de prestamo contradictorios. |
| 422 | `validation_error` | `availability_filter_conflict` | `available=true` con prestamo abierto. |
| 422 | `validation_error` | `box_filter_conflict` | `has_box=false` con `box_id`. |
| 422 | `validation_error` | `location_filter_conflict` | `has_location=false` con componentes de ubicacion. |
| 422 | `validation_error` | `date_range_invalid` | Rango de fechas invertido. |
| 422 | `validation_error` | `filter_too_short` | Filtro parcial menor a 3. |
| 422 | `validation_error` | `sort_not_allowed` | `sort_by` fuera de lista blanca. |
| 422 | `validation_error` | `type_not_supported` | `IMPORT_BATCH` en global. |
| 429 | `rate_limited` | - | Limite de tasa superado. |
| 503 | `service_unavailable` | - | Redis o base no disponible. |

Todos los errores usan el sobre:

```json
{
  "error": {
    "code": "validation_error",
    "message": "La busqueda debe tener al menos 3 caracteres.",
    "details": {"reason": "q_too_short", "min_length": 3},
    "request_id": "req-..."
  }
}
```

### 15.4 Acciones de auditoria

| Accion | Entidad | Cuando |
|---|---|---|
| `search.executed` | `search` | Cada busqueda global o especializada. |

No crear acciones por resultado ni por grupo. Los conteos van en metadata.

### 15.5 Consultas `EXPLAIN` de referencia

Ejecutar con datos representativos y `ANALYZE` previo:

```sql
ANALYZE case_files;
ANALYZE persons;
ANALYZE boxes;
ANALYZE administrative_documents;
ANALYZE case_parties;

EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id
FROM case_files
WHERE court_id = :court_id
  AND nuc_normalized = '00012345'
  AND deleted_at IS NULL;

EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id
FROM case_files
WHERE nuc_suffix5 = '12345'
  AND deleted_at IS NULL;

EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id
FROM case_files
WHERE nuc_normalized LIKE '%12345%'
  AND deleted_at IS NULL;

EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id
FROM persons
WHERE normalized_name LIKE '%PERSONA123%'
  AND deleted_at IS NULL;

EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id
FROM administrative_documents
WHERE lower(public.immutable_unaccent(title)) LIKE '%resolucion%'
  AND deleted_at IS NULL;

EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id
FROM boxes
WHERE visible_number LIKE '%4402%';
```

Planes esperados:

- NUC exacto: `Index Scan` o `Bitmap Index Scan` con `ix_case_files_court_nuc`.
- Sufijo: `Index Scan` o `Bitmap Index Scan` con `ix_case_files_nuc_suffix5`.
- NUC parcial: `Bitmap Index Scan` con `ix_case_files_nuc_trgm`.
- Nombre: `Bitmap Index Scan` con `ix_persons_normalized_name_trgm`.
- Titulo: `Bitmap Index Scan` con `ix_admin_documents_title_trgm`.
- Numero de caja: `Bitmap Index Scan` con `ix_boxes_visible_number_trgm`.

Si el plan muestra `Seq Scan` en tablas grandes, revisar:

- estadisticas desactualizadas (`ANALYZE`);
- selectividad real;
- tipo de dato y colacion;
- expresion indexada vs expresion consultada;
- `enable_seqscan` no debe usarse como solucion permanente.

### 15.6 Dataset de benchmark

Crear `backend/scripts/seed_search_benchmark.sql` con parametros `:court_id` y `:party_role_id`:

```sql
-- Cajas de expedientes.
INSERT INTO boxes (
    id, court_id, year, box_type, visible_number, description,
    confidentiality, lifecycle_status, custody_status
)
SELECT
    gen_random_uuid(),
    :court_id,
    2000 + (g % 25),
    'EXPEDIENTES',
    'BENCH-' || lpad(g::text, 6, '0'),
    'Caja de benchmark ' || g,
    'INTERNAL',
    'ACTIVE',
    'UNKNOWN'
FROM generate_series(1, 20000) AS g;

-- Expedientes.
INSERT INTO case_files (
    id, court_id, nuc_raw, nuc_normalized, year,
    lifecycle_status, verification_status, confidentiality
)
SELECT
    gen_random_uuid(),
    :court_id,
    lpad(g::text, 8, '0'),
    lpad(g::text, 8, '0'),
    2000 + (g % 25),
    'ACTIVE',
    'PENDING',
    'INTERNAL'
FROM generate_series(1, 100000) AS g;

-- Personas.
INSERT INTO persons (id, display_name, normalized_name)
SELECT
    gen_random_uuid(),
    'Persona ' || g,
    'PERSONA' || g
FROM generate_series(1, 20000) AS g;

-- Partes: una persona por expediente.
INSERT INTO case_parties (
    id, case_file_id, person_id, party_role_id, is_primary
)
SELECT
    gen_random_uuid(),
    cf.id,
    p.id,
    :party_role_id,
    false
FROM (
    SELECT id, row_number() OVER (ORDER BY id) AS rn
    FROM case_files
    ORDER BY id
    LIMIT 20000
) AS cf
JOIN (
    SELECT id, row_number() OVER (ORDER BY id) AS rn
    FROM persons
    ORDER BY id
    LIMIT 20000
) AS p USING (rn);

-- Cajas administrativas.
WITH new_boxes AS (
    INSERT INTO boxes (
        id, court_id, year, box_type, visible_number, description,
        confidentiality, lifecycle_status, custody_status
    )
    SELECT
        gen_random_uuid(),
        :court_id,
        2000 + (g % 25),
        'DOCUMENTOS_ADMINISTRATIVOS',
        'BENCH-ADM-' || lpad(g::text, 6, '0'),
        'Caja administrativa de benchmark ' || g,
        'INTERNAL',
        'ACTIVE',
        'UNKNOWN'
    FROM generate_series(1, 10000) AS g
    RETURNING id, year
)
INSERT INTO administrative_documents (
    id, box_id, box_type, title, document_type, document_year,
    description, verification_status, confidentiality, lifecycle_status
)
SELECT
    gen_random_uuid(),
    id,
    'DOCUMENTOS_ADMINISTRATIVOS',
    'Documento benchmark ' || row_number() OVER (),
    'OFICIO',
    year,
    'Descripcion de prueba',
    'PENDING',
    'INTERNAL',
    'ACTIVE'
FROM new_boxes;

ANALYZE boxes;
ANALYZE case_files;
ANALYZE persons;
ANALYZE case_parties;
ANALYZE administrative_documents;
```

Umbrales de referencia (hardware de desarrollo, PostgreSQL local, datos sinteticos):

| Consulta | P95 objetivo |
|---|---|
| NUC exacto | < 100 ms |
| `nuc_suffix5` | < 150 ms |
| NUC parcial | < 500 ms |
| Nombre parcial | < 500 ms |
| Titulo parcial | < 500 ms |
| Global agrupada | < 800 ms |
| Pagina especializada | < 600 ms |

Los umbrales son una linea base, no una garantia. Ajustar con el hardware real y documentar la medicion.

### 15.7 Script de indices concurrentes

Crear `backend/scripts/create_search_indexes_concurrently.sql` con las mismas sentencias de la migracion, cambiando `CREATE INDEX` por `CREATE INDEX CONCURRENTLY`:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE OR REPLACE FUNCTION public.immutable_unaccent(value text)
RETURNS text
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
STRICT
AS $$
    SELECT public.unaccent('public.unaccent'::regdictionary, value)
$$;

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_persons_normalized_name_trgm
ON persons USING gin (normalized_name gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_case_files_nuc_trgm
ON case_files USING gin (nuc_normalized gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_case_files_resolution_trgm
ON case_files USING gin
(lower(public.immutable_unaccent(resolution_number)) gin_trgm_ops)
WHERE resolution_number IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_boxes_visible_number_trgm
ON boxes USING gin (visible_number gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_boxes_description_trgm
ON boxes USING gin
(lower(public.immutable_unaccent(description)) gin_trgm_ops)
WHERE description IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_admin_documents_title_trgm
ON administrative_documents USING gin
(lower(public.immutable_unaccent(title)) gin_trgm_ops)
WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_admin_documents_description_trgm
ON administrative_documents USING gin
(lower(public.immutable_unaccent(description)) gin_trgm_ops)
WHERE description IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_case_files_search_filters
ON case_files (court_id, year, lifecycle_status, confidentiality)
WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_boxes_search_filters
ON boxes (court_id, year, box_type, lifecycle_status, custody_status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_admin_documents_search_filters
ON administrative_documents
(document_year, lifecycle_status, verification_status, confidentiality, box_id)
WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_case_parties_person_case
ON case_parties (person_id, case_file_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_case_parties_case_role
ON case_parties (case_file_id, party_role_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_import_rows_target_box
ON import_rows (target_box_id) WHERE target_box_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_import_rows_target_case
ON import_rows (target_case_file_id) WHERE target_case_file_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_import_rows_target_admin
ON import_rows (target_administrative_document_id)
WHERE target_administrative_document_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_import_rows_batch_status
ON import_rows (batch_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_loans_overdue
ON loans (due_at)
WHERE status IN ('APPROVED', 'DELIVERED') AND due_at IS NOT NULL;

ANALYZE persons;
ANALYZE case_files;
ANALYZE boxes;
ANALYZE administrative_documents;
ANALYZE case_parties;
ANALYZE import_rows;
ANALYZE loans;
```

`CREATE INDEX CONCURRENTLY` no puede ejecutarse dentro de una transaccion. Ejecutar con `psql` y revisar `pg_stat_progress_create_index`.

### 15.8 Notas finales

- B8 no implementa busqueda difusa. Si se aprueba en el futuro, debe ser un parametro explicito y auditado, no el comportamiento por defecto.
- B8 no cambia la confidencialidad por defecto de B7.
- B8 no expone datos de prestamos ni filas de importacion; solo disponibilidad e incidencias.
- B8 no reemplaza los endpoints CRUD de B7; los complementa.
- B8 debe poder desplegarse sin frontend y probarse con OpenAPI y `curl`.
- La evidencia de cierre debe incluir planes `EXPLAIN`, resultados de pruebas y captura de los umbrales P95.
