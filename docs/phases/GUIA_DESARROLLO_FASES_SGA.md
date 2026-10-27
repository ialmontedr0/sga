# Guía maestra de fases --- Sistema de Gestión Documental Judicial

**Documento:** Plan de implementación funcional y técnica\
**Versión:** 1.0\
**Estado:** Especificación inicial aprobada para planificación\
**Stack principal:** React + TypeScript + Vite + Tailwind CSS; Python +
FastAPI + Uvicorn + SQLAlchemy + Alembic + `uv`; PostgreSQL; Redis.\
**Idioma de la interfaz:** Español\
**Despliegue previsto:** Internet, con acceso autenticado y controles de
seguridad reforzados.

------------------------------------------------------------------------

## 1. Propósito del documento

Esta guía define el alcance, las dependencias, los objetivos, los
requisitos, los entregables, los criterios de aceptación y los riesgos
de las fases de desarrollo de un sistema para gestionar el inventario
documental de un archivo central judicial.

El proyecto se desarrollará en el orden acordado:

1.  **Completar el backend primero**, incluyendo dominio, base de datos,
    autenticación, permisos, reglas de negocio, búsqueda, importaciones,
    OCR, auditoría, reportes, tareas en segundo plano, pruebas,
    documentación y despliegue.
2.  **Desarrollar el frontend después**, consumiendo contratos de API ya
    definidos y probados, con arquitectura modular y diseño atómico de
    componentes React.
3.  Integrar y validar la solución completa, incluido el plano 2D y el
    modelo 3D.

No se considera terminado un módulo solo porque exista una pantalla o un
endpoint. Debe contar con validaciones, pruebas, manejo de errores,
permisos, documentación y criterios de aceptación verificables.

## 2. Contexto y alcance confirmado

### 2.1 Inventario físico

El archivo cuenta actualmente con cinco áreas y 39 anaqueles:

  Área                Anaqueles conocidos     Cantidad
  ------------------- --------------------- ----------
  Zona A              A1--A9                         9
  Zona B              B1--B8                         8
  Zona C              C1--C6                         6
  Zona D              D1--D13                       13
  Zona O              O1--O3                         3
  **Total inicial**                             **39**

Las áreas y los anaqueles deben ser administrables mediante operaciones
CRUD. Los números anteriores representan el inventario inicial
declarado, no una restricción fija del sistema.

La configuración física de cada anaquel debe admitir capacidades
variables, por ejemplo:

-   7 bandejas × 9 posiciones por bandeja.
-   7 bandejas × 8 posiciones por bandeja.
-   7 bandejas × 7 posiciones por bandeja.
-   Otras configuraciones creadas por usuarios autorizados.

El modelo debe separar la **capacidad física configurada** de la
**ocupación real**. Una posición no podrá tener dos cajas activas a la
vez.

### 2.2 Cajas

-   Existe una secuencia global histórica que llega hasta la caja 4401.
-   La numeración futura debe poder cambiar mediante una política de
    numeración configurable, sin perder la identidad interna de las
    cajas existentes.
-   Cada caja tiene un tipo documental excluyente: expedientes
    judiciales o documentos administrativos.
-   Cada caja debe tener un tribunal y un año de referencia, según las
    reglas del tipo de caja.
-   Las cajas pueden existir en el sistema sin una ubicación física
    confirmada.
-   El sistema debe distinguir entre ubicación desconocida, ubicación
    pendiente de verificación y ubicación confirmada.
-   Las cajas pueden trasladarse; sus movimientos deben conservarse en
    el historial.

### 2.3 Expedientes judiciales

Campos funcionales iniciales:

-   NUC, como texto, aceptando formatos históricos y configurables.
-   Uno o varios imputados, registrados individualmente.
-   Fecha de entrada.
-   Identificador de sentencia o resolución.
-   Fecha de sentencia o resolución.
-   Caja asociada.

Formatos iniciales indicados:

-   NUC de cinco dígitos, por ejemplo `00001`.
-   NUC con estructura `YYYY-CODIGOTRIBUNAL-NUMPROCESO`, por ejemplo
    `2022-102-00001`.
-   Identificador de sentencia con estructura orientativa
    `000-0000-SSSS-0000`, donde los prefijos como `SPEN`, `SADM` o `RPE`
    se administran según las reglas aplicables.

Los formatos reales deben validarse con ejemplos institucionales antes
de fijar expresiones regulares definitivas. Deben contemplarse registros
históricos que no cumplan el formato moderno, sin aceptar
silenciosamente datos incorrectos.

### 2.4 Documentos administrativos

Campos funcionales iniciales:

-   Nombre del documento.
-   Tribunal asociado.
-   Año del documento.
-   Mes opcional cuando se conozca y sea necesario.
-   Caja asociada.

El modelo debe almacenar el año como un valor de año, no como una
fecha-hora inventada. Si el mes es opcional, se almacenará por separado
o mediante un modelo de fecha parcial explícito.

### 2.5 Tribunales

Catálogo inicial suministrado:

  -----------------------------------------------------------------------
  Tribunal                Código informado        Estado inicial
  ----------------------- ----------------------- -----------------------
  Juzgado de Instrucción  589                     Por confirmar

  Juzgado de Instrucción  589                     Por confirmar
  en Atención Permanente

  Corte de Apelación      102                     Por confirmar

  Primera Cámara Penal    106                     Inactivo
  del Juzgado de Primera
  Instancia

  Segunda Cámara Penal    107                     Inactivo
  del Juzgado de Primera
  Instancia

  Juzgado de Primera      107                     Por confirmar
  Instancia Unipersonal

  Tribunal de Ejecución   107-01                  Por confirmar
  de la Pena

  Tribunal Colegiado de   107-02                  Por confirmar
  Primera Instancia
  -----------------------------------------------------------------------

Los códigos no deben ser claves primarias. Como existen códigos
compartidos o potencialmente reutilizados, cada tribunal tendrá un
identificador interno estable. El sistema permitirá gestionar nombres,
códigos, estado, reglas de identificadores y vigencia sin destruir
referencias históricas. Antes de cargar el catálogo definitivo, el
responsable del archivo debe confirmar si los códigos repetidos son
válidos, representan variantes, o requieren una distinción adicional.

### 2.6 Importación documental y OCR

El sistema debe admitir:

-   PDF con texto seleccionable.
-   PDF escaneado.
-   DOCX.
-   Imágenes comunes de inventarios, si se habilita el formato.
-   Documentos manuscritos antiguos.
-   Importación estructurada desde CSV y XLSX, recomendada para
    inventarios tabulares.
-   Futuras plantillas de importación específicas por origen.

Toda importación debe generar una vista previa, mostrar advertencias y
errores, permitir corregir valores y exigir aprobación antes de
incorporar los registros al inventario oficial. Los originales se
conservarán y se vincularán a su lote de importación.

El OCR manuscrito puede producir resultados inciertos. No se prometerá
exactitud perfecta: los resultados tendrán estado, confianza cuando el
motor la proporcione, evidencia de origen y revisión humana.

### 2.7 Usuarios y permisos

Distribución inicial:

-   2 administradores.
-   1 supervisor de archivo.
-   1 archivista.
-   1 digitalizador.
-   5 usuarios de consulta.

Los permisos deben aplicarse en el backend, no solamente ocultando
controles del frontend. La cantidad de usuarios podrá crecer sin cambios
estructurales.

### 2.8 Funciones solicitadas

-   Búsqueda avanzada.
-   Plano 2D y modelo 3D interactivo.
-   CRUD de áreas, anaqueles, tribunales, cajas, expedientes e
    inventarios administrativos.
-   Importación y OCR con revisión.
-   Historial de cambios y movimientos.
-   Préstamos, traslados y devoluciones.
-   Etiquetas QR o códigos de barras.
-   Alertas e incidencias.
-   Conciliación de inventario físico y digital.
-   Exportación a XLSX, CSV y PDF.
-   Panel de métricas.
-   Tema claro y oscuro.
-   Interfaz adaptable y componentes atómicos.
-   Conservación de archivos originales de importación.

------------------------------------------------------------------------

## 3. Principios arquitectónicos obligatorios

### 3.1 Fuente única de verdad

PostgreSQL será la fuente oficial de datos. El frontend 2D/3D, las
exportaciones, los reportes y los procesos OCR deberán consumir el mismo
modelo de dominio. No se mantendrán inventarios paralelos
independientes.

### 3.2 Identidad interna independiente de códigos visibles

Las entidades principales usarán identificadores internos estables,
preferiblemente UUID. Los números visibles de caja, códigos de tribunal
y códigos de ubicación serán atributos de negocio sujetos a reglas
explícitas.

La numeración global de cajas debe ser configurable y transaccional. No
se debe calcular con `MAX(numero) + 1` sin protección ante concurrencia.
Se recomienda una secuencia o servicio de numeración controlado, con una
política de reasignación documentada. No se reutilizará un número
retirado sin una decisión explícita y auditada.

### 3.3 Reglas de negocio en el backend

Las reglas críticas se implementarán en servicios de dominio y se
reforzarán con restricciones de base de datos cuando sea viable. La
interfaz podrá ayudar al usuario, pero nunca será la única barrera.

### 3.4 Modularidad con límites claros

Organizar el backend por dominios funcionales, no como una colección de
archivos genéricos gigantes. Cada módulo tendrá modelos, esquemas,
servicios, repositorios cuando aporten valor, endpoints, permisos y
pruebas propios.

### 3.5 Procesos largos fuera de las peticiones HTTP

OCR, importaciones masivas, generación de informes voluminosos y tareas
de conciliación se ejecutarán en segundo plano mediante una cola de
trabajos apoyada por Redis y un trabajador dedicado. El usuario podrá
consultar el estado de cada trabajo.

### 3.6 Seguridad por diseño

La aplicación estará expuesta a Internet y gestionará información
judicial. Por tanto, TLS, control de acceso, protección de
sesiones/tokens, validación de archivos, límites de tamaño, registros de
auditoría, copias de seguridad y políticas de retención son requisitos
esenciales, no mejoras opcionales.

### 3.7 Trazabilidad

Los cambios importantes deben poder reconstruirse: actor, fecha,
entidad, operación, motivo, valores anteriores y nuevos cuando
corresponda. Los registros de auditoría deben estar protegidos contra
modificación por usuarios normales.

### 3.8 Entregables reproducibles

Cada fase incluirá instrucciones de instalación, configuración de
entorno, migraciones, pruebas y criterios de aceptación. Se utilizarán
archivos de bloqueo y versiones controladas de dependencias.

------------------------------------------------------------------------

## 4. Arquitectura de referencia

### 4.1 Backend

Tecnologías recomendadas:

-   Python con `uv` para entorno y dependencias.
-   FastAPI para API REST.
-   Uvicorn como servidor ASGI.
-   Pydantic para validación de entrada y salida.
-   SQLAlchemy 2.x para persistencia.
-   Alembic para migraciones.
-   PostgreSQL como base de datos relacional.
-   Redis para colas, coordinación y caché selectiva.
-   Un trabajador de tareas en segundo plano compatible con Redis, por
    ejemplo RQ o Celery; la elección se fijará antes de la fase de
    procesamiento documental.
-   Pytest para pruebas.
-   Ruff para linting y formato.
-   Mypy o Pyright para comprobaciones de tipos, según la estrategia
    acordada.
-   OpenAPI generado desde FastAPI como contrato verificable.

### 4.2 Frontend (se implementará después de cerrar el backend)

-   React con TypeScript.
-   Vite.
-   Tailwind CSS.
-   React Router para navegación.
-   TanStack Query para estado remoto y caché de API.
-   React Hook Form y Zod para formularios y validación de interfaz.
-   Biblioteca de componentes accesibles, si se decide adoptar una, sin
    sustituir el sistema de diseño propio.
-   Three.js mediante React Three Fiber para la visualización 3D, sujeto
    a validación técnica.
-   Biblioteca de gráficos para métricas.
-   Pruebas con Vitest y Testing Library; pruebas de navegador con
    Playwright.

La elección final de librerías debe quedar fijada en archivos de
dependencias y documentada. No se introducirán varias librerías que
resuelvan la misma necesidad sin una razón clara.

### 4.3 Almacenamiento de archivos

Los PDF, DOCX e imágenes originales no deben guardarse como grandes
blobs en las tablas principales. Se recomienda almacenamiento de objetos
privado, con una interfaz de servicio que permita usar almacenamiento
compatible con S3 o almacenamiento privado del servidor. La base de
datos conservará metadatos, hash de integridad, tamaño, tipo MIME,
propietario, permisos, lote de importación y referencia al objeto.

El acceso a los archivos será autorizado. No se expondrán rutas físicas
del servidor ni enlaces públicos permanentes.

### 4.4 Entornos

Como mínimo:

-   Desarrollo local.
-   Pruebas automatizadas.
-   Preproducción o staging.
-   Producción.

Cada entorno tendrá configuración y secretos separados. No se copiarán
datos judiciales reales a desarrollo sin autorización, anonimización y
controles adecuados.

------------------------------------------------------------------------

## 5. Modelo de dominio propuesto

Las entidades siguientes son una base inicial que se deberá refinar
durante la fase de análisis y modelado.

### 5.1 Organización física

-   `Area`: nombre, código, descripción, orden, estado.
-   `Shelf` o `Anaquel`: área, código visible, dimensiones opcionales,
    capacidad configurada, estado.
-   `ShelfLevel` o `Bandeja`: anaquel, número/etiqueta, orden,
    capacidad.
-   `ShelfPosition` o `PosicionCaja`: bandeja, índice de posición,
    estado.
-   `LocationAssignment`: caja, posición, fecha inicial/final, usuario,
    motivo y estado de verificación.
-   `PhysicalInventorySession`: sesión de inspección, alcance,
    responsable, fecha y estado.
-   `InventoryDiscrepancy`: tipo de discrepancia, evidencia, resolución
    y responsable.

Debe decidirse si la posición se materializa como registro independiente
o se deriva de una configuración del anaquel. Para facilitar
restricciones de ocupación, conciliación e historial, se recomienda una
representación explícita de posiciones o un modelo equivalente que
garantice unicidad.

### 5.2 Inventario documental

-   `Box`: UUID, número visible, tribunal, año, tipo, estado, notas,
    ubicación verificada y metadatos de creación.
-   `CaseFile` o `Expediente`: UUID, NUC, fechas, identificador de
    sentencia/resolución, caja y estado.
-   `Defendant` o `Imputado`: identidad textual normalizada, nombre
    original y campos de búsqueda necesarios.
-   `CaseDefendant`: relación entre expediente e imputado.
-   `AdministrativeDocument`: nombre, tribunal, año, mes opcional, caja
    y metadatos.
-   `Court`: UUID, nombre, código, estado, vigencia y observaciones.
-   `CourtIdentifierRule`: tribunal, tipo de identificador, prefijo,
    patrón, vigencia y reglas de validación.
-   `BoxType`: catálogo controlado o enumeración gestionada, según
    necesidades de configuración.

Se recomienda conservar los valores originales introducidos/importados
además de sus versiones normalizadas cuando esto sea importante para la
trazabilidad.

### 5.3 Sentencias y resoluciones

En lugar de codificar permanentemente `SPEN`, `SADM` y `RPE` en el
código fuente, crear un catálogo administrable de tipos de resolución
asociado al tribunal o a un ámbito global. Cada regla deberá definir:

-   Código/prefijo.
-   Descripción.
-   Tribunal o ámbito aplicable.
-   Patrón del identificador.
-   Estado activo/inactivo.
-   Vigencia, si procede.
-   Reglas de unicidad.

Antes de implementar el validador definitivo debe confirmarse el formato
real. El ejemplo `000-0000-SSSS-0000` y la descripción de códigos deben
reconciliarse: los ejemplos proporcionados usan prefijos alfanuméricos
como `SPEN`, no cuatro dígitos.

### 5.4 Usuarios, permisos y auditoría

-   `User`.
-   `Role`.
-   `Permission`.
-   `UserRole` y, si procede, asignaciones de alcance.
-   `AuditEvent`.
-   `AuthenticationSession` o mecanismo equivalente según el sistema de
    autenticación.
-   `LoginEvent` o eventos de seguridad relevantes.

Los eventos de auditoría deben evitar almacenar contraseñas, tokens o
información sensible innecesaria. Para valores anteriores/nuevos se
aplicará una política de exclusión y minimización de datos.

### 5.5 Importaciones y archivos

-   `ImportBatch`: creador, tipo de origen, estado, fecha, archivo
    original, resumen de resultados.
-   `ImportRow`: número de fila/página/segmento, datos extraídos,
    estado, errores y advertencias.
-   `StoredFile`: metadatos del archivo, hash, ubicación privada,
    tamaño, tipo, retención y permisos.
-   `OCRJob`: estado, motor, configuración, fecha, resultado y errores.
-   `ImportMappingProfile`: plantilla o mapeo de columnas por formato de
    inventario.
-   `ImportDecision`: aprobación, rechazo, correcciones y actor
    responsable.

Estados sugeridos para un lote: `uploaded`, `queued`, `processing`,
`needs_review`, `approved`, `importing`, `completed`,
`completed_with_errors`, `failed`, `cancelled`.

### 5.6 Préstamos y movimientos

-   `BoxMovement`: caja, ubicación origen/destino, actor, fecha, motivo
    y evidencia.
-   `Loan`: objeto prestado, solicitante autorizado, responsable, fecha
    de salida, fecha prevista de devolución, estado y autorización.
-   `LoanEvent`: entrega, renovación, devolución, incidencia y actor.
-   `Alert`: tipo, destinatario o grupo, fecha, estado y entidad
    asociada.

Debe confirmarse si se prestarán cajas completas, expedientes
individuales o ambos. El modelo debe admitir el alcance autorizado sin
permitir que una caja prestada parezca disponible en su posición física
habitual.

### 5.7 Configuración y reportes

-   `SystemSetting` para configuración no secreta y controlada.
-   `NumberingPolicy` para la numeración de cajas.
-   `ReportJob` para informes pesados generados en segundo plano.
-   `ExportArtifact` para archivos de exportación con vencimiento y
    permisos.

------------------------------------------------------------------------

## 6. Reglas de negocio críticas

1.  Una caja tendrá exactamente un tipo documental activo.
2.  Una caja de expedientes no aceptará documentos administrativos; una
    caja administrativa no aceptará expedientes.
3.  La caja debe cumplir las reglas de tribunal y año aplicables a su
    tipo.
4.  La ubicación física no será obligatoria al crear una caja, pero el
    estado de ubicación debe ser explícito.
5.  Una posición física no podrá asignarse a dos cajas activas
    simultáneamente.
6.  Una caja no podrá tener dos ubicaciones físicas activas
    simultáneamente.
7.  Los movimientos conservarán origen, destino, actor, fecha y motivo.
8.  El número global visible de caja será único según la política
    configurada.
9.  El sistema conservará el UUID interno aunque cambie el número
    visible por una operación autorizada.
10. Las cajas históricas no se eliminarán físicamente de manera
    ordinaria si tienen expedientes, movimientos, préstamos o auditoría
    asociados.
11. Los tribunales inactivos permanecerán referenciables en datos
    históricos.
12. La desactivación de un tribunal no cambiará retroactivamente los
    expedientes ya registrados.
13. Los formatos NUC y de sentencia se validarán según reglas
    configurables, con un mecanismo explícito para datos históricos
    excepcionales.
14. La búsqueda por los últimos cinco dígitos del NUC no debe asumirse
    como identificador único. Debe devolver coincidencias y pedir
    desambiguación cuando existan varias.
15. Los nombres de imputados se normalizarán para buscar, pero se
    conservará el texto original.
16. Las importaciones masivas serán transaccionales por lotes o por
    unidades controladas, con estrategia de reanudación y registro de
    fallos.
17. Una importación no sobrescribirá datos existentes de forma
    silenciosa.
18. Los duplicados probables se señalarán para revisión, diferenciando
    coincidencia exacta de posible coincidencia.
19. El OCR no guardará directamente en el inventario oficial sin
    aprobación humana.
20. Las operaciones sensibles deben verificar autorización en el backend
    y dejar auditoría.
21. Las exportaciones respetarán los permisos del usuario y no expondrán
    más información de la autorizada.
22. Las tareas en segundo plano serán idempotentes o contarán con
    protección frente a ejecuciones duplicadas.
23. Los borrados, cambios de código, reasignaciones de numeración y
    movimientos deberán confirmar dependencias y producir eventos de
    auditoría.
24. Las fechas se almacenarán en tipos adecuados; las fechas de entrada
    y sentencia serán fechas completas y el año/mes administrativo se
    modelará como fecha parcial.
25. La configuración de capacidad de un anaquel no podrá reducirse por
    debajo de las posiciones ocupadas sin un proceso de resolución de
    conflictos.

------------------------------------------------------------------------

## 7. Plan de fases del backend

# Fase B0 --- Preparación del proyecto y decisiones técnicas

### Objetivo

Convertir los requisitos en una base técnica verificable antes de
desarrollar funcionalidades de negocio.

### Actividades

-   Crear repositorio y estrategia de ramas.
-   Fijar versión de Python y política de dependencias con `uv`.
-   Establecer configuración de entornos.
-   Definir formato de código, tipado, pruebas y convenciones.
-   Crear configuración de Ruff, pytest y análisis de tipos.
-   Definir manejo de variables de entorno y secretos.
-   Elegir estrategia de autenticación y biblioteca de tareas en segundo
    plano.
-   Elegir almacenamiento privado de archivos.
-   Crear estructura modular inicial.
-   Definir política de errores, logging, identificadores de petición y
    paginación.
-   Documentar decisiones arquitectónicas (ADR).

### Requisitos previos

-   Acceso al repositorio y entorno de desarrollo.
-   Versiones y credenciales de desarrollo de PostgreSQL y Redis.
-   Decisión sobre el entorno de despliegue y proveedor de
    almacenamiento.

### Entregables

-   Repositorio inicial.
-   `pyproject.toml` y archivo de bloqueo de `uv`.
-   `.env.example` sin secretos.
-   Configuración de linting, pruebas y tipado.
-   Estructura inicial de paquetes.
-   Documento de arquitectura y registro ADR.
-   Instrucciones para ejecutar el servicio localmente.

### Criterios de aceptación

-   Una persona desarrolladora puede crear el entorno desde cero
    siguiendo el README.
-   El servicio arranca sin depender de configuración secreta
    incrustada.
-   Las comprobaciones de formato, lint y pruebas se ejecutan mediante
    comandos documentados.
-   Ningún secreto está comprometido en el repositorio.


## Estado de la fase: Completada
------------------------------------------------------------------------

# Fase B1 --- Análisis funcional, modelo de dominio y contratos

### Objetivo

Cerrar las ambigüedades del negocio y establecer contratos estables para
la futura interfaz.

### Actividades

-   Definir glosario: caja, expediente, imputado, tribunal, bandeja,
    posición, lote, préstamo y ubicación.
-   Confirmar formatos reales de NUC y sentencia/resolución.
-   Definir qué significa exactamente el número de proceso y la unicidad
    del NUC.
-   Resolver la duplicidad de códigos de tribunales.
-   Definir políticas de numeración y cambios de número visible.
-   Especificar estados de cajas, ubicaciones, préstamos, lotes y
    archivos.
-   Definir matriz de roles y permisos.
-   Definir reglas de borrado, archivo histórico y retención.
-   Diseñar esquemas de API y convenciones de errores.
-   Documentar filtros, ordenación, paginación y búsquedas.
-   Definir límites de carga y retención de documentos originales.

### Entregables

-   Especificación funcional.
-   Diagrama entidad-relación.
-   Diagrama de estados de las entidades críticas.
-   Matriz de roles y permisos.
-   Catálogo inicial de tribunales y tipos de resolución.
-   Contratos OpenAPI preliminares.
-   Lista de decisiones pendientes con responsable.

### Criterios de aceptación

-   No hay ambigüedades críticas en la separación de tipos de caja.
-   Están documentados los formatos de identificadores y sus excepciones
    históricas.
-   Los roles pueden describirse mediante permisos concretos.
-   Los contratos cubren los flujos principales y los errores esperados.

## Estado de la fase: Completada
------------------------------------------------------------------------

# Fase B2 --- Base de datos, modelos SQLAlchemy y migraciones Alembic

### Objetivo

Construir una base de datos consistente y migrable.

### Actividades

-   Configurar SQLAlchemy 2.x y sesiones transaccionales.
-   Crear modelos y relaciones.
-   Crear restricciones `UNIQUE`, `CHECK`, claves foráneas e índices.
-   Definir borrado lógico donde proceda.
-   Crear migración inicial con Alembic.
-   Configurar migraciones posteriores incrementales.
-   Preparar datos semilla para roles y configuración esencial.
-   Preparar carga inicial de áreas, anaqueles y tribunales confirmados.
-   Definir estrategia de actualización y reversión de migraciones.
-   Añadir pruebas de integridad y concurrencia.

### Entidades principales

-   Organización física y posiciones.
-   Tribunales y reglas de identificadores.
-   Cajas, expedientes, imputados y documentos administrativos.
-   Usuarios, roles, permisos y auditoría.
-   Archivos, lotes de importación, tareas, préstamos y movimientos.

### Entregables

-   Modelos SQLAlchemy.
-   Migraciones Alembic.
-   Semillas idempotentes.
-   Diagrama ER actualizado.
-   Pruebas de integridad relacional.
-   Guía de migración y restauración de esquema.

### Criterios de aceptación

-   Una base vacía puede llegar al esquema actual con las migraciones
    documentadas.
-   Las migraciones no dependen de cambios manuales invisibles.
-   Las claves foráneas y restricciones rechazan combinaciones
    inválidas.
-   Se prueban conflictos de concurrencia relevantes.
-   Las migraciones se verifican en una base de pruebas antes de
    producción.

### Evidencia de cierre

-   Fecha y entorno: 2026-10-26; Windows; PostgreSQL 18.4; Python
    3.12.13 con `uv`.
-   Esquema: 41 tablas; migración inicial `20261026_0001`; `sga_test`
    recreada desde esquema vacío.
-   `uv run ruff check .`: sin errores.
-   `uv run ruff format --check .`: 82 archivos formateados.
-   `uv run mypy src`: sin errores en 59 archivos.
-   `uv run pytest tests/unit`: 34 passed.
-   `uv run pytest tests/integration -m integration -n 0`: 46 passed.
-   `uv run alembic check`: sin operaciones nuevas detectadas.
-   Suite completa: 87 passed; cobertura 92.54 % (umbral 75).
-   Limitaciones: render Mermaid no ejecutado (`mmdc` ausente); no se
    realizó ensayo de restauración completo.
-   Commit: `7d6aa4f chore(backend): Base de datos, modelos SQLAlchemy y
    migraciones Alembic`.

## Estado de la fase: Completada
------------------------------------------------------------------------

# Fase B3 --- Configuración de la API y capa común

### Objetivo

Crear la infraestructura común de FastAPI para todos los módulos.

### Actividades

-   Configurar aplicación, routers y ciclo de vida.
-   Crear prefijo versionado, por ejemplo `/api/v1`.
-   Añadir validación de configuración.
-   Implementar manejo centralizado de excepciones.
-   Establecer formato uniforme de errores.
-   Configurar CORS con orígenes permitidos explícitos.
-   Añadir middleware de identificador de petición y logging.
-   Implementar health checks para aplicación y dependencias.
-   Añadir paginación, ordenación y filtros comunes.
-   Configurar documentación OpenAPI.
-   Añadir límites razonables de petición y protección de endpoints.
-   Evitar devolver trazas internas al cliente en producción.

### Entregables

-   Aplicación FastAPI ejecutable.
-   Router versionado.
-   Esquemas de error y respuesta.
-   Health checks.
-   Logging estructurado.
-   OpenAPI inicial.
-   Pruebas de API común.

### Criterios de aceptación

-   Los errores de validación y de negocio tienen respuestas coherentes.
-   La API no revela secretos ni trazas internas.
-   Los health checks distinguen disponibilidad de la API y
    disponibilidad de dependencias.
-   OpenAPI representa los contratos reales.

## Estado de la fase: Completada

Evidencia (2026-10-26): 130 pruebas aprobadas (52 unitarias, 32 de API y
46 de integración), cobertura global 95,03 % y 95 % en `core`; Ruff,
formato y mypy sin errores; `alembic check` sin operaciones nuevas; smoke
local con PostgreSQL y Redis en `ok` y rechazo de host no permitido con
`400 bad_request`. Detalle completo en `docs/phases/phaseB3_guide.md`,
sección 20.

## Estado de la fase: Completada
------------------------------------------------------------------------

# Fase B4 --- Autenticación, autorización y administración de usuarios

### Objetivo

Asegurar el acceso al sistema y aplicar permisos en el servidor.

### Actividades

-   Implementar autenticación segura.
-   Seleccionar estrategia de sesión o token según despliegue y
    clientes.
-   Proteger contraseñas con un algoritmo de hash adecuado.
-   Implementar inicio y cierre de sesión, expiración y revocación.
-   Implementar recuperación de acceso mediante flujo seguro si se
    habilita.
-   Crear usuarios y asignar roles.
-   Implementar permisos por operación y recurso.
-   Añadir limitación de intentos y eventos de seguridad.
-   Proteger cuentas administrativas.
-   Aplicar validación de permisos a todas las rutas sensibles.
-   Documentar alta, baja, bloqueo y recuperación de usuarios.

### Roles iniciales

-   Administrador.
-   Supervisor de archivo.
-   Archivista.
-   Digitalizador.
-   Consulta.

Los dos administradores iniciales serán cuentas creadas mediante un
procedimiento seguro; no se incluirán contraseñas predeterminadas en
código ni semillas.

### Entregables

-   Endpoints de autenticación.
-   CRUD de usuarios, roles y permisos.
-   Dependencias de autorización.
-   Matriz de permisos ejecutable.
-   Pruebas de acceso permitido y denegado.
-   Guía de administración de usuarios.

### Criterios de aceptación

-   Un usuario sin permiso no puede realizar la operación llamando
    directamente a la API.
-   Las sesiones/token expirados o revocados dejan de funcionar.
-   Las contraseñas nunca se almacenan en texto plano.
-   Los eventos de autenticación relevantes quedan registrados sin
    guardar secretos.

## Estado de la fase: Pendiente
------------------------------------------------------------------------

# Fase B5 --- Catálogos y configuración administrativa

### Objetivo

Hacer configurables los datos institucionales sin modificar el código
fuente.

### Actividades

-   CRUD de tribunales.
-   Gestión de códigos compartidos, estado y vigencia.
-   CRUD de tipos de resolución y reglas de prefijos.
-   CRUD de tipos de caja si se decide permitir extensiones.
-   CRUD de áreas y anaqueles.
-   Configuración de bandejas, posiciones y capacidad.
-   Configuración de política de numeración de cajas.
-   Validar cambios que afecten entidades existentes.
-   Añadir filtros, búsqueda, paginación y auditoría.
-   Definir reglas de desactivación y no de borrado físico cuando
    existan dependencias.

### Entregables

-   Endpoints y servicios de catálogos.
-   Validadores configurables.
-   Datos iniciales confirmados.
-   Pruebas CRUD y de dependencias.
-   Documentación de configuración.

### Criterios de aceptación

-   Un administrador autorizado puede mantener los catálogos.
-   Desactivar un tribunal no rompe datos históricos.
-   Un cambio de capacidad no elimina posiciones ocupadas de forma
    silenciosa.
-   Los códigos visibles no sustituyen las claves internas.

## Estado de la fase: Pendiente
------------------------------------------------------------------------

Avancemos con en el desarrollo, implementacion y documentacion de la siguiente fase de forma profesional, avanzada, completa, funcional, sin omisiones y abarcando todo lo relativo a esta. Continuaremos con:

Fase B5 --- Catálogos y configuración administrativa

### Objetivo

Hacer configurables los datos institucionales sin modificar el código
fuente.

### Actividades

-   CRUD de tribunales.
-   Gestión de códigos compartidos, estado y vigencia.
-   CRUD de tipos de resolución y reglas de prefijos.
-   CRUD de tipos de caja si se decide permitir extensiones.
-   CRUD de áreas y anaqueles.
-   Configuración de bandejas, posiciones y capacidad.
-   Configuración de política de numeración de cajas.
-   Validar cambios que afecten entidades existentes.
-   Añadir filtros, búsqueda, paginación y auditoría.
-   Definir reglas de desactivación y no de borrado físico cuando
    existan dependencias.

### Entregables

-   Endpoints y servicios de catálogos.
-   Validadores configurables.
-   Datos iniciales confirmados.
-   Pruebas CRUD y de dependencias.
-   Documentación de configuración.

### Criterios de aceptación

-   Un administrador autorizado puede mantener los catálogos.
-   Desactivar un tribunal no rompe datos históricos.
-   Un cambio de capacidad no elimina posiciones ocupadas de forma
    silenciosa.
-   Los códigos visibles no sustituyen las claves internas.

En este desarrollo de esta fase, quiero que me proporciones toda la informacion de implementacion, codigo, comandos, instrucciones completas y detalladas y todo lo indicado en esta fase, pero una escala completa, sin saltarte nada, todo lo que indica sin omisiones, de forma avanzada, moderna, profesional, correcta, completa y siempre tomando las mejores opciones, arquitecturas, patrones de diseño, todo que sea gratis para mi. No implementes por tu cuenta, solo indicame las instrucciones y documenta todo. Recuerda siempre leer el docs/AGENTS.md y el docs/phases/GUIA_DESARROLLO_FASES_SGA.md para mantenerte retroalimentado siempre y no perder el hilo y, cualquier informacion de otra de las fases ya implementadas puedes leerla en su respectivo archivo .md. Y toda la guia y documentacion de implementacion de la fase actual la escribiras en el archivo relativo a ella que sera phases/phaseB5_guide.md, asi queda todo documentado de una vez.

Nota: las indicaciones deben ser bien claras, no omitas donde debo crear archivos, donde debo escribir codigo, no te saltes nada, debes ser bien detallado por favor, sigue el mismo patron de guia como el phaseB1_guide.md.


# Fase B6 --- Inventario físico y ubicaciones

### Objetivo

Representar de manera fiable las áreas, anaqueles, bandejas, posiciones
y ubicación de cada caja.

### Actividades

-   CRUD de áreas y anaqueles.
-   Definición de capacidad configurable por anaquel.
-   Generación y mantenimiento de bandejas y posiciones.
-   Asignación y desasignación de cajas.
-   Estados de ubicación: desconocida, pendiente de verificar,
    confirmada, en tránsito u otros aprobados.
-   Historial de ubicación.
-   Validaciones de capacidad y unicidad.
-   Operaciones de traslado con origen, destino, motivo y usuario.
-   Soporte para cajas sin ubicación conocida.
-   Consultas de ocupación y capacidad disponible.
-   Diseño de operaciones de inventario físico y conciliación.

### Entregables

-   Modelos y servicios de ubicación.
-   Endpoints para plano y posiciones.
-   Endpoints de movimientos.
-   Reportes de ocupación.
-   Pruebas de concurrencia de asignación.
-   Documentación de estados de ubicación.

### Criterios de aceptación

-   No se puede ocupar dos veces una misma posición.
-   Una caja no puede estar en dos posiciones activas.
-   Los movimientos mantienen historial completo.
-   El sistema diferencia caja no registrada, caja sin ubicación
    confirmada y posición vacía.
-   La capacidad visible coincide con la configuración física.

## Estado de la fase: Pendiente
------------------------------------------------------------------------

Avancemos con en el desarrollo, implementacion y documentacion de la siguiente fase de forma profesional, avanzada, completa, funcional, sin omisiones y abarcando todo lo relativo a esta. Continuaremos con:

Fase B6 --- Inventario físico y ubicaciones

### Objetivo

Representar de manera fiable las áreas, anaqueles, bandejas, posiciones
y ubicación de cada caja.

### Actividades

-   CRUD de áreas y anaqueles.
-   Definición de capacidad configurable por anaquel.
-   Generación y mantenimiento de bandejas y posiciones.
-   Asignación y desasignación de cajas.
-   Estados de ubicación: desconocida, pendiente de verificar,
    confirmada, en tránsito u otros aprobados.
-   Historial de ubicación.
-   Validaciones de capacidad y unicidad.
-   Operaciones de traslado con origen, destino, motivo y usuario.
-   Soporte para cajas sin ubicación conocida.
-   Consultas de ocupación y capacidad disponible.
-   Diseño de operaciones de inventario físico y conciliación.

### Entregables

-   Modelos y servicios de ubicación.
-   Endpoints para plano y posiciones.
-   Endpoints de movimientos.
-   Reportes de ocupación.
-   Pruebas de concurrencia de asignación.
-   Documentación de estados de ubicación.

### Criterios de aceptación

-   No se puede ocupar dos veces una misma posición.
-   Una caja no puede estar en dos posiciones activas.
-   Los movimientos mantienen historial completo.
-   El sistema diferencia caja no registrada, caja sin ubicación
    confirmada y posición vacía.
-   La capacidad visible coincide con la configuración física.

En este desarrollo de esta fase, quiero que me proporciones toda la informacion de implementacion, codigo, comandos, instrucciones completas y detalladas y todo lo indicado en esta fase, pero una escala completa, sin saltarte nada, todo lo que indica sin omisiones, de forma avanzada, moderna, profesional, correcta, completa y siempre tomando las mejores opciones, arquitecturas, patrones de diseño, todo que sea gratis para mi. No implementes por tu cuenta, solo indicame las instrucciones y documenta todo. Recuerda siempre leer el docs/AGENTS.md y el docs/phases/GUIA_DESARROLLO_FASES_SGA.md para mantenerte retroalimentado siempre y no perder el hilo y, cualquier informacion de otra de las fases ya implementadas puedes leerla en su respectivo archivo .md. Y toda la guia y documentacion de implementacion de la fase actual la escribiras en el archivo relativo a ella que sera phases/phaseB6_guide.md, asi queda todo documentado de una vez.

Nota: las indicaciones deben ser bien claras, no omitas donde debo crear archivos, donde debo escribir codigo, no te saltes nada, debes ser bien detallado por favor.

# Fase B7 --- Cajas, expedientes e inventario administrativo

### Objetivo

Implementar el núcleo de gestión documental.

### Actividades

-   CRUD de cajas.
-   Numeración global mediante mecanismo seguro ante concurrencia.
-   Alta de caja con tribunal, año y tipo.
-   CRUD de expedientes.
-   Relación de varios imputados con un expediente.
-   CRUD de documentos administrativos.
-   Validación configurable de NUC.
-   Validación de sentencia/resolución según tribunal.
-   Búsqueda y detección de duplicados.
-   Transacciones para creación de caja y contenido.
-   Reglas estrictas de exclusión de tipos documentales.
-   Desactivación y corrección controlada de registros.
-   Soporte para excepciones históricas justificadas.
-   Auditoría de operaciones.

### Entregables

-   Servicios y endpoints CRUD.
-   Validadores configurables.
-   Reglas de integridad.
-   Pruebas unitarias e integración.
-   Documentación de endpoints y ejemplos de payload.
-   Procedimiento de corrección de datos históricos.

### Criterios de aceptación

-   No es posible insertar expedientes en una caja administrativa ni
    documentos administrativos en una caja de expedientes.
-   La numeración es única incluso con altas concurrentes.
-   Los imputados se buscan individualmente.
-   Las reglas de identificadores permiten configuración y excepciones
    auditadas.
-   Las operaciones parciales fallidas no dejan datos inconsistentes.

------------------------------------------------------------------------

# Fase B8 --- Búsqueda avanzada e índices

### Objetivo

Encontrar rápidamente expedientes, documentos, cajas y ubicaciones en el
archivo completo.

### Criterios de búsqueda

-   NUC completo.
-   Últimos cinco dígitos del NUC.
-   Coincidencia parcial de NUC.
-   Nombre de imputado, con coincidencia parcial y normalización.
-   Tribunal y código.
-   Año.
-   Identificador de sentencia/resolución.
-   Fecha de entrada y fecha de sentencia.
-   Nombre de documento administrativo.
-   Número de caja.
-   Área, anaquel, bandeja y posición.
-   Tipo y estado de caja.
-   Ubicación desconocida o pendiente de verificación.
-   Estado de préstamo y disponibilidad, según permisos.
-   Búsqueda por lote de importación y registros con incidencias.

### Actividades

-   Definir semántica exacta de coincidencia, acentos, mayúsculas y
    espacios.
-   Crear índices B-tree y otros índices adecuados según consultas.
-   Evaluar búsqueda de texto completo y trigramas de PostgreSQL.
-   Construir filtros combinables.
-   Implementar paginación estable.
-   Añadir ordenación permitida por lista blanca.
-   Devolver ubicación física en resultados autorizados.
-   Preparar consultas de explicación y pruebas de rendimiento.
-   Evitar consultas N+1 y carga innecesaria de relaciones.

### Entregables

-   Endpoints de búsqueda.
-   Índices y migraciones.
-   Contratos de filtros.
-   Pruebas de precisión y rendimiento.
-   Documentación de búsqueda.

### Criterios de aceptación

-   Buscar los últimos cinco dígitos devuelve todas las coincidencias,
    sin asumir unicidad.
-   Las búsquedas combinadas no omiten filtros.
-   La respuesta incluye caja y ubicación cuando estén confirmadas.
-   Se miden tiempos con datos de prueba representativos.
-   Los resultados respetan permisos y no filtran datos restringidos.

------------------------------------------------------------------------

# Fase B9 --- Auditoría, movimientos, préstamos y devoluciones

### Objetivo

Asegurar trazabilidad operativa de las cajas y los documentos.

### Actividades

-   Registro de cambios con actor, fecha, entidad, operación, motivo y
    valores permitidos.
-   Historial de movimiento de cajas.
-   Solicitud, autorización, entrega, renovación y devolución de
    préstamos.
-   Definición de si se prestan cajas, expedientes o ambos.
-   Validación de disponibilidad y conflictos.
-   Registro de incidentes: retraso, pérdida, daño o discrepancia.
-   Alertas de vencimiento y movimientos pendientes.
-   Permisos para consulta de auditoría.
-   Protección de la integridad de eventos.
-   Exportación autorizada de historial.

### Entregables

-   Módulo de auditoría.
-   Módulo de préstamos y movimientos.
-   Catálogo de estados y transiciones.
-   Alertas.
-   Pruebas de transiciones y permisos.
-   Manual operativo.

### Criterios de aceptación

-   Una devolución no borra el historial del préstamo.
-   Las operaciones críticas exigen permisos.
-   Los movimientos tienen origen, destino, actor, fecha y motivo.
-   Los registros de auditoría no pueden alterarse mediante operaciones
    CRUD normales.
-   Los conflictos de préstamo se detectan antes de confirmar la
    operación.

------------------------------------------------------------------------

# Fase B10 --- Archivos, importaciones masivas y revisión

### Objetivo

Importar inventarios existentes desde documentos digitales y hojas de
cálculo, conservando trazabilidad y control humano.

### Formatos

-   PDF con texto.
-   DOCX.
-   CSV.
-   XLSX.
-   PDF escaneado.
-   JPG, PNG o TIFF, si se habilitan.
-   Otros formatos aprobados tras evaluar seguridad y complejidad.

### Actividades

-   Crear almacenamiento privado de archivos.
-   Validar extensión, MIME real, tamaño y límites.
-   Calcular hash para integridad y detección de duplicados.
-   Registrar el archivo original y el lote.
-   Extraer texto de PDF y DOCX.
-   Detectar tablas y encabezados.
-   Configurar perfiles de mapeo de columnas.
-   Normalizar NUC, nombres, códigos, años y fechas.
-   Presentar vista previa editable.
-   Clasificar filas: válidas, advertencias, errores y duplicados
    probables.
-   Permitir corregir y aprobar/rechazar.
-   Ejecutar importación en transacciones controladas.
-   Registrar usuario, fecha, archivo, mapeo, decisiones y resultados.
-   Ofrecer reanudación o repetición segura de lotes fallidos.
-   Generar resumen descargable de resultados.

### Entregables

-   Servicio de almacenamiento.
-   CRUD de lotes.
-   Procesadores para PDF/DOCX/CSV/XLSX.
-   Vista de revisión disponible mediante API.
-   Endpoints de aprobación y ejecución.
-   Informe de importación.
-   Pruebas con archivos válidos, malformados, duplicados y de gran
    tamaño.

### Criterios de aceptación

-   El archivo original queda vinculado al lote.
-   Ningún registro se incorpora oficialmente antes de la aprobación.
-   Las filas con errores se identifican y no se importan
    silenciosamente.
-   Una repetición no duplica registros sin advertencia.
-   Los archivos no autorizados o malformados son rechazados de forma
    segura.
-   Los fallos quedan registrados con información útil y sin filtrar
    detalles internos.

------------------------------------------------------------------------

# Fase B11 --- OCR de escaneos y manuscritos

### Objetivo

Extraer datos de inventarios antiguos, incluidos documentos manuscritos,
con revisión humana.

### Actividades

-   Evaluar motores OCR para texto impreso y manuscrito.
-   Separar OCR de texto impreso de reconocimiento de escritura
    manuscrita.
-   Implementar preprocesamiento: rotación, contraste, eliminación de
    ruido y segmentación cuando sea viable.
-   Detectar páginas, tablas, columnas y filas.
-   Extraer campos objetivo: caja, tribunal, código, año, NUC,
    imputados, sentencia y fecha.
-   Guardar resultados crudos y normalizados.
-   Registrar motor, versión, configuración y errores.
-   Asociar resultados con página y región de origen cuando el motor lo
    permita.
-   Mostrar confianza cuando esté disponible, sin tratarla como
    garantía.
-   Crear reglas de revisión para campos críticos y baja confianza.
-   Permitir corrección humana y conservar los valores detectados
    originalmente.
-   Crear conjunto de evaluación con muestras autorizadas y anonimizadas
    cuando sea posible.
-   Medir precisión por campo y tipo de documento.
-   Establecer estrategia para motores locales o servicios externos
    según privacidad, coste y calidad.

### Entregables

-   Pipeline OCR en segundo plano.
-   Adaptadores de motores OCR.
-   Normalización y validación.
-   Resultados con procedencia.
-   Herramientas de revisión.
-   Informe de evaluación de calidad.
-   Política de datos para servicios externos, si se contemplan.

### Criterios de aceptación

-   El OCR no incorpora datos directamente al inventario oficial sin
    aprobación.
-   Los campos dudosos se destacan.
-   Es posible rastrear un valor hasta el documento y la página de
    origen cuando se disponga de esa información.
-   Se mide la precisión con una muestra representativa antes de aprobar
    el despliegue.
-   Si un motor externo se utiliza, su uso y tratamiento de datos están
    aprobados institucionalmente.

------------------------------------------------------------------------

# Fase B12 --- Exportaciones, informes y panel de control

### Objetivo

Producir informes fiables y útiles para supervisión e inventarios.

### Actividades

-   Exportar XLSX, CSV y PDF.
-   Informes por tribunal, año, área, anaquel, bandeja, tipo y estado.
-   Reporte de cajas sin ubicación confirmada.
-   Reporte de capacidad y ocupación.
-   Reporte de préstamos vencidos y movimientos pendientes.
-   Reporte de discrepancias del inventario físico.
-   Reporte de importaciones y errores OCR.
-   Resumen de expedientes y documentos administrativos.
-   Aplicar permisos y filtros a todas las exportaciones.
-   Ejecutar exportaciones pesadas en segundo plano.
-   Añadir expiración y autorización de descarga de archivos generados.

### Entregables

-   Servicios de informes.
-   Plantillas de exportación.
-   Endpoints y estados de trabajos.
-   Métricas iniciales.
-   Pruebas de consistencia entre informe y consultas de base de datos.

### Criterios de aceptación

-   Los totales exportados coinciden con los filtros de la API.
-   Los archivos respetan permisos.
-   Los trabajos grandes no bloquean la API.
-   Las exportaciones incluyen fecha de generación y criterios
    aplicados.

------------------------------------------------------------------------

# Fase B13 --- Códigos QR y códigos de barras

### Objetivo

Facilitar la identificación física de cajas y la verificación de
ubicación.

### Actividades

-   Definir contenido del código: identificador opaco o URL protegida,
    evitando datos sensibles legibles.
-   Generar etiquetas imprimibles.
-   Asociar etiqueta a UUID interno y número visible.
-   Permitir escanear para abrir ficha autorizada.
-   Registrar verificación de presencia física.
-   Gestionar reimpresión, deterioro y sustitución de etiquetas.
-   Evitar que un QR funcione como autorización por sí solo.

### Entregables

-   Servicio de etiquetas.
-   Plantillas imprimibles.
-   Endpoints de validación.
-   Registro de escaneos o verificaciones, según política.
-   Pruebas de correspondencia entre etiqueta y caja.

### Criterios de aceptación

-   Cada etiqueta identifica una sola entidad.
-   La etiqueta no expone información sensible.
-   El acceso exige autenticación y autorización.
-   Reimprimir una etiqueta no crea una caja nueva.

------------------------------------------------------------------------

# Fase B14 --- Conciliación de inventario físico y digital

### Objetivo

Comparar el registro del sistema con una inspección física real y
resolver discrepancias.

### Actividades

-   Crear sesiones de inventario por área, anaquel o selección de cajas.
-   Capturar escaneo o confirmación manual.
-   Comparar caja esperada con caja observada.
-   Detectar caja ausente, caja inesperada, posición incorrecta,
    etiqueta no válida y contenido no coincidente.
-   Registrar evidencia, observación, responsable y fecha.
-   Definir flujo de resolución y aprobación.
-   Corregir ubicación o inventario mediante operaciones auditadas.
-   Generar informe de conciliación.
-   Permitir sesiones parciales y reanudables.

### Entregables

-   Módulo de sesiones de inventario.
-   Registro de discrepancias.
-   Flujo de resolución.
-   Informes de conciliación.
-   Pruebas con escenarios correctos y discrepantes.

### Criterios de aceptación

-   Una discrepancia no modifica automáticamente el inventario oficial.
-   Las correcciones tienen responsable y motivo.
-   Se puede comparar el resultado final con la situación inicial.
-   Las sesiones pueden ejecutarse por área o anaquel sin bloquear todo
    el sistema.

------------------------------------------------------------------------

# Fase B15 --- Seguridad, rendimiento, resiliencia y endurecimiento

### Objetivo

Preparar el backend para operar en Internet con datos sensibles y carga
real.

### Actividades

-   Revisar OWASP ASVS y riesgos web relevantes.
-   Forzar HTTPS mediante la infraestructura de despliegue.
-   Configurar cookies seguras si se usa autenticación por cookies.
-   Proteger contra CSRF cuando corresponda, XSS, inyección y abuso de
    API.
-   Configurar CORS restrictivo, límites de tasa y tamaño.
-   Validar y escanear archivos subidos.
-   Revisar autorización a nivel de objeto para prevenir IDOR.
-   Aplicar límites de paginación y consultas costosas.
-   Añadir timeout, reintentos limitados y manejo de fallos de
    Redis/almacenamiento.
-   Probar restauración de PostgreSQL y archivos.
-   Definir copias de seguridad cifradas, retención y objetivos RPO/RTO.
-   Añadir métricas, logs y alertas operativas.
-   Revisar dependencias vulnerables.
-   Ejecutar pruebas de carga, seguridad y recuperación.
-   Establecer políticas de retención y borrado seguro.

### Entregables

-   Informe de seguridad.
-   Plan de copias de seguridad y recuperación.
-   Pruebas de carga.
-   Paneles o métricas operativas.
-   Lista de riesgos y remediaciones.
-   Checklist de producción.

### Criterios de aceptación

-   Las operaciones críticas están protegidas en el servidor.
-   Se ha probado una restauración completa.
-   No se registran secretos ni datos sensibles innecesarios en logs.
-   Se han probado límites de carga, errores de dependencias y
    reintentos.
-   Los riesgos críticos identificados están resueltos o formalmente
    aceptados.

------------------------------------------------------------------------

# Fase B16 --- Pruebas integrales, documentación y cierre del backend

### Objetivo

Declarar el backend estable y listo para ser consumido por el frontend.

### Actividades

-   Pruebas unitarias de dominio.
-   Pruebas de integración con PostgreSQL y Redis.
-   Pruebas de API con usuarios y permisos diferentes.
-   Pruebas de migraciones desde una base limpia y desde una versión
    anterior.
-   Pruebas de importación y OCR con fixtures.
-   Pruebas de concurrencia para numeración y asignación de posiciones.
-   Pruebas de búsqueda y exportación.
-   Pruebas de seguridad y regresión.
-   Revisión de OpenAPI.
-   Preparar datos de demostración sintéticos.
-   Completar manual de instalación, operación, respaldo y recuperación.
-   Congelar contratos de API para iniciar el frontend.

### Entregables

-   Suite automatizada de pruebas.
-   Informe de cobertura y riesgos residuales.
-   OpenAPI validado.
-   Manual técnico y operativo.
-   Guía de despliegue.
-   Guía de actualización de versiones.
-   Contratos API listos para frontend.
-   Versión etiquetada del backend.

### Criterios de aceptación

-   Los flujos principales están cubiertos por pruebas automatizadas.
-   No quedan defectos críticos abiertos.
-   Las migraciones y la recuperación están documentadas.
-   El frontend puede desarrollarse contra contratos estables y datos de
    prueba.
-   Se conoce qué funciones requieren servicios externos o configuración
    adicional.

------------------------------------------------------------------------

## 8. Plan de fases del frontend

El frontend comienza **después del cierre del backend** y consume su API
versionada. No replicará reglas de negocio críticas como única
validación.

# Fase F1 --- Base de React, Vite y arquitectura modular

### Objetivo

Crear una base mantenible para una aplicación administrativa de largo
plazo.

### Actividades

-   Crear proyecto con Vite y React TypeScript.
-   Configurar Tailwind CSS según la versión seleccionada.
-   Configurar alias, lint, formato, pruebas y variables de entorno.
-   Configurar React Router.
-   Configurar cliente HTTP tipado.
-   Generar tipos desde OpenAPI o mantener una estrategia de tipos
    sincronizados.
-   Configurar TanStack Query.
-   Crear manejo global de errores y notificaciones.
-   Definir límites entre módulos.
-   Crear documentación de arquitectura frontend.

### Entregables

-   Proyecto base.
-   Scripts reproducibles.
-   Cliente API.
-   Rutas iniciales.
-   Configuración de pruebas.
-   Guía de desarrollo frontend.

### Criterios de aceptación

-   El proyecto se instala y ejecuta desde cero con instrucciones
    documentadas.
-   No se incluyen secretos en el bundle.
-   Los tipos de API coinciden con el contrato del backend.
-   Las pruebas y el lint se ejecutan en CI.

------------------------------------------------------------------------

# Fase F2 --- Sistema de diseño y arquitectura atómica

### Objetivo

Construir componentes reutilizables y accesibles antes de crear páginas
complejas.

### Niveles de diseño atómico

-   **Tokens:** colores, tipografía, espaciado, radios, sombras, capas y
    puntos de ruptura.
-   **Átomos:** botón, campo, etiqueta, icono, checkbox, selector,
    tooltip, spinner y avatar.
-   **Moléculas:** campo con etiqueta y error, barra de búsqueda,
    filtro, selector de tribunal, paginador.
-   **Organismos:** tabla de inventario, formulario de caja, panel de
    filtros, diálogo de confirmación.
-   **Plantillas:** diseño de listado, detalle, formulario, revisión de
    importación y panel de control.
-   **Páginas:** composiciones conectadas a datos reales.

### Actividades

-   Definir tema claro y oscuro.
-   Crear variables y tokens de diseño.
-   Definir estados hover, focus, disabled, loading, error y success.
-   Establecer accesibilidad por teclado y lectores de pantalla.
-   Crear documentación visual de componentes.
-   Definir convenciones de carpetas y nombres.
-   Evitar componentes monolíticos y duplicación de lógica.

### Entregables

-   Design tokens.
-   Biblioteca atómica.
-   Plantillas de página.
-   Catálogo de componentes.
-   Pruebas de accesibilidad básicas.
-   Guía de contribución.

### Criterios de aceptación

-   Los componentes tienen API tipada y estados coherentes.
-   Tema claro/oscuro funciona en todas las plantillas.
-   Los formularios muestran etiquetas y errores accesibles.
-   Los componentes se reutilizan sin acoplarse a una única página.

------------------------------------------------------------------------

# Fase F3 --- Autenticación, navegación y permisos de interfaz

### Objetivo

Implementar el acceso y la estructura general de navegación.

### Actividades

-   Inicio y cierre de sesión.
-   Manejo seguro del estado de autenticación.
-   Renovación o expiración según el método seleccionado.
-   Protección de rutas.
-   Menú lateral adaptable.
-   Cabecera, perfil y selector de tema.
-   Navegación filtrada por permisos como ayuda de interfaz.
-   Pantallas de acceso denegado, sesión expirada y error.
-   Manejo de estados de carga.

### Entregables

-   Layout principal.
-   Flujos de autenticación.
-   Navegación por módulos.
-   Componentes de permisos.
-   Pruebas de rutas.

### Criterios de aceptación

-   Una ruta protegida no se muestra como disponible a usuarios no
    autenticados.
-   Los permisos del frontend no sustituyen los controles del backend.
-   La interfaz se adapta a resoluciones habituales.
-   La expiración se comunica de manera comprensible.

------------------------------------------------------------------------

# Fase F4 --- Panel de control

### Objetivo

Ofrecer una visión general del estado del archivo.

### Contenido previsto

-   Total de cajas.
-   Cajas con ubicación confirmada y pendiente.
-   Capacidad configurada y ocupación.
-   Distribución por área y tipo.
-   Expedientes y documentos administrativos.
-   Préstamos vencidos.
-   Importaciones pendientes de revisión.
-   Discrepancias abiertas.
-   Accesos rápidos a tareas permitidas.

### Entregables

-   Dashboard conectado a endpoints de métricas.
-   Gráficos y tablas.
-   Estados vacíos, carga y error.
-   Pruebas de permisos y datos.

### Criterios de aceptación

-   Las métricas coinciden con los datos de backend.
-   Los gráficos tienen alternativas textuales o tabulares cuando
    corresponda.
-   No se muestran métricas a las que el usuario no tiene permiso de
    acceso.

------------------------------------------------------------------------

# Fase F5 --- CRUD de catálogos e inventario

### Objetivo

Crear interfaces para mantener tribunales, áreas, anaqueles, cajas,
expedientes e inventario administrativo.

### Actividades

-   Listados con búsqueda, filtros, paginación y ordenación.
-   Formularios con validación de cliente.
-   Selectores dependientes de tribunal, año, tipo y caja.
-   Alta y edición de cajas.
-   Formularios de expedientes con varios imputados.
-   Formularios de documentos administrativos con año y mes opcional.
-   Manejo de duplicados y errores de negocio.
-   Confirmación de operaciones sensibles.
-   Vistas de detalle e historial.
-   Estados vacíos, errores y reintentos.

### Entregables

-   Páginas CRUD.
-   Formularios tipados.
-   Tablas reutilizables.
-   Pruebas unitarias y de integración de interfaz.
-   Guía de uso.

### Criterios de aceptación

-   La interfaz no permite enviar formularios obviamente inválidos.
-   Los errores del backend se presentan de manera comprensible.
-   Los usuarios no autorizados no ven acciones de escritura y el
    backend las rechaza igualmente.
-   Los formularios largos conservan entradas cuando ocurre un error
    recuperable.

------------------------------------------------------------------------

# Fase F6 --- Búsqueda global y resultados

### Objetivo

Permitir encontrar un expediente o documento y llegar rápidamente a su
ubicación física.

### Actividades

-   Barra de búsqueda global.
-   Búsqueda por NUC completo o últimos cinco dígitos.
-   Filtros combinables.
-   Búsqueda por imputado, tribunal, año, sentencia, fecha y nombre.
-   Resultados diferenciados por tipo documental.
-   Resaltado de coincidencias cuando resulte útil.
-   Ficha de caja y ubicación.
-   Acciones permitidas: abrir, exportar, registrar movimiento o iniciar
    préstamo.
-   Manejo de múltiples coincidencias.

### Entregables

-   Página de búsqueda avanzada.
-   Componentes de filtro.
-   Tabla y vista de resultados.
-   Enlaces a caja y ubicación.
-   Pruebas con resultados ambiguos y vacíos.

### Criterios de aceptación

-   La búsqueda por sufijo no asume que el resultado sea único.
-   El usuario puede identificar tribunal, año y ubicación de cada
    coincidencia.
-   Los filtros aplicados son visibles y se pueden limpiar.
-   La paginación conserva los criterios de búsqueda.

------------------------------------------------------------------------

# Fase F7 --- Editor de plano 2D

### Objetivo

Representar las áreas y colocar los anaqueles de manera editable.

### Actividades

-   Crear un plano por área.
-   Añadir, mover, rotar y seleccionar anaqueles.
-   Mostrar código, estado y ocupación.
-   Ajustar escala, zoom y desplazamiento.
-   Selección de anaquel para ver bandejas y posiciones.
-   Validar cambios de diseño.
-   Guardar coordenadas y orientación mediante API.
-   Evitar que el plano sea la única fuente de ubicación lógica.
-   Añadir leyenda y accesibilidad complementaria.

### Entregables

-   Editor 2D.
-   Modelo persistido de coordenadas.
-   Panel de propiedades.
-   Estados de edición y confirmación.
-   Pruebas de persistencia y permisos.

### Criterios de aceptación

-   El diseño guardado se conserva al recargar.
-   Los cambios requieren permisos.
-   La posición gráfica se vincula al anaquel real.
-   Mover un icono en el plano no cambia automáticamente la ubicación de
    cajas sin una operación explícita.

------------------------------------------------------------------------

# Fase F8 --- Modelo 3D interactivo

### Objetivo

Explorar visualmente el archivo, seleccionar anaqueles, bandejas y cajas
y enlazar la vista con el inventario.

### Actividades

-   Implementar escena 3D mediante Three.js/React Three Fiber o
    tecnología aprobada.
-   Construir geometría a partir de las dimensiones configuradas.
-   Representar áreas y anaqueles.
-   Renderizar bandejas y posiciones según capacidad.
-   Diferenciar posiciones ocupadas, vacías y no verificadas.
-   Selección y resaltado de elementos.
-   Panel de detalle sincronizado con la selección.
-   Navegación de cámara, zoom y controles accesibles.
-   Enlace desde resultados de búsqueda a la posición correspondiente.
-   Carga progresiva y optimización para escenas grandes.
-   Alternativa 2D/lista para dispositivos modestos o accesibilidad.
-   Separar la representación visual de las reglas de negocio.

### Entregables

-   Visor 3D.
-   Selección de anaqueles, bandejas y cajas.
-   Enlace búsqueda--ubicación.
-   Leyenda de estados.
-   Pruebas de selección y consistencia.
-   Guía de rendimiento y compatibilidad.

### Criterios de aceptación

-   Una caja localizada desde búsqueda se resalta en la escena correcta.
-   La escena refleja la ubicación persistida por el backend.
-   La visualización no asigna ni mueve cajas por sí sola.
-   La interfaz sigue siendo utilizable cuando el modelo 3D no está
    disponible.
-   Se mide el rendimiento con una configuración representativa del
    archivo.

------------------------------------------------------------------------

# Fase F9 --- Importación y revisión OCR en interfaz

### Objetivo

Permitir a digitalizadores cargar documentos, revisar la extracción y
aprobar lotes.

### Actividades

-   Carga de archivo con límites y progreso.
-   Selección de tipo de inventario y perfil de importación.
-   Seguimiento del estado del trabajo.
-   Vista de tabla extraída y datos de origen.
-   Resaltado de errores, advertencias y confianza.
-   Edición de campos.
-   Detección visual de duplicados.
-   Aprobación o rechazo con motivo.
-   Resumen del resultado y descarga del informe.
-   Acceso al archivo original según permisos.

### Entregables

-   Flujo de importación.
-   Vista de revisión.
-   Seguimiento de trabajos.
-   Informe de errores.
-   Pruebas de carga, revisión y aprobación.

### Criterios de aceptación

-   El usuario puede distinguir datos reconocidos de datos confirmados.
-   No se aprueba un lote sin resolver los errores bloqueantes.
-   El proceso puede recuperarse tras recargar la página.
-   El estado mostrado proviene del backend.

------------------------------------------------------------------------

# Fase F10 --- Préstamos, traslados, alertas y conciliación

### Objetivo

Dar soporte visual a las operaciones físicas y su trazabilidad.

### Actividades

-   Flujos de préstamo y devolución.
-   Registro de traslado y confirmación de llegada.
-   Alertas por vencimiento o discrepancia.
-   Sesiones de inventario físico.
-   Registro de caja observada mediante QR o búsqueda.
-   Resolución de incidencias.
-   Vista de historial por caja.
-   Confirmaciones para operaciones irreversibles o sensibles.

### Entregables

-   Páginas de préstamos y movimientos.
-   Centro de alertas.
-   Flujo de conciliación.
-   Historial de caja.
-   Pruebas de transiciones y permisos.

### Criterios de aceptación

-   Cada operación muestra su estado y responsable.
-   Los cambios de ubicación no ocurren únicamente por arrastrar
    elementos visuales.
-   Las alertas enlazan con la entidad y acción correspondiente.
-   Las incidencias resueltas conservan su historial.

------------------------------------------------------------------------

# Fase F11 --- Exportaciones, informes y experiencia final

### Objetivo

Completar la experiencia operativa y facilitar la adopción.

### Actividades

-   Selección de columnas y filtros autorizados.
-   Solicitud de exportaciones y seguimiento del trabajo.
-   Descarga protegida.
-   Vista previa de informes.
-   Diseño adaptable y accesible.
-   Optimización de tablas grandes.
-   Atajos de teclado y estados de foco.
-   Mensajes de éxito/error y confirmaciones.
-   Revisión de tema claro/oscuro.
-   Pruebas de navegador en resoluciones representativas.

### Entregables

-   Interfaz de exportaciones.
-   Catálogo de informes.
-   Revisión de accesibilidad.
-   Pruebas E2E.
-   Manual de usuario inicial.

### Criterios de aceptación

-   Las descargas respetan filtros y permisos.
-   Los informes se pueden localizar y descargar solo mientras estén
    autorizados.
-   La aplicación funciona en los navegadores objetivo acordados.
-   Las pantallas principales tienen estados de carga, vacío, error y
    éxito.

------------------------------------------------------------------------

## 9. Fase de integración y puesta en producción

Esta fase se ejecutará después de completar los módulos necesarios del
backend y frontend.

### Actividades

-   Desplegar en staging con configuración equivalente a producción.
-   Configurar DNS, TLS y proxy inverso.
-   Separar secretos y permisos del sistema operativo.
-   Configurar PostgreSQL, Redis y almacenamiento privado.
-   Configurar servicio API y trabajador de tareas.
-   Configurar copias de seguridad y monitoreo.
-   Ejecutar migraciones con procedimiento controlado.
-   Cargar inventario inicial mediante lotes de prueba.
-   Validar una muestra de cajas y ubicaciones físicamente.
-   Ejecutar pruebas de aceptación con usuarios de cada rol.
-   Corregir incidencias y aprobar salida a producción.
-   Preparar procedimiento de reversión y recuperación.
-   Definir soporte, mantenimiento y gestión de versiones.

### Entregables

-   Despliegue de staging.
-   Despliegue de producción.
-   Runbook de operación.
-   Plan de respaldo y recuperación probado.
-   Informe de aceptación.
-   Registro de riesgos residuales.
-   Procedimiento de actualización.

### Criterios de aceptación

-   TLS activo y configuración de seguridad revisada.
-   Restauración de base de datos y archivos probada.
-   Trabajadores y API se reinician de forma controlada.
-   Las tareas fallidas se pueden detectar y gestionar.
-   Usuarios clave aprueban los flujos principales.
-   Existe un plan de soporte y respuesta a incidentes.

------------------------------------------------------------------------

## 10. Estructura de carpetas de referencia

La estructura exacta se podrá ajustar durante B0/B1, pero se recomienda
mantener módulos por dominio.

``` text
backend/
├── pyproject.toml
├── uv.lock
├── alembic.ini
├── .env.example
├── README.md
├── alembic/
│   ├── env.py
│   └── versions/
├── src/
│   └── judicial_archive/
│       ├── __init__.py
│       ├── main.py
│       ├── core/
│       │   ├── config.py
│       │   ├── database.py
│       │   ├── security.py
│       │   ├── errors.py
│       │   ├── logging.py
│       │   └── permissions.py
│       ├── api/
│       │   └── v1/
│       │       ├── router.py
│       │       └── dependencies.py
│       ├── modules/
│       │   ├── identity/
│       │   ├── courts/
│       │   ├── physical_layout/
│       │   ├── boxes/
│       │   ├── case_files/
│       │   ├── administrative_documents/
│       │   ├── search/
│       │   ├── audit/
│       │   ├── loans/
│       │   ├── files/
│       │   ├── imports/
│       │   ├── ocr/
│       │   ├── reports/
│       │   ├── labels/
│       │   └── reconciliation/
│       ├── workers/
│       └── shared/
└── tests/
    ├── unit/
    ├── integration/
    ├── api/
    ├── security/
    └── fixtures/
```

Dentro de cada módulo, usar una separación coherente según su
complejidad, por ejemplo:

``` text
case_files/
├── models.py
├── schemas.py
├── repository.py
├── service.py
├── router.py
├── validators.py
├── permissions.py
└── tests/
```

No todos los módulos necesitan todos los archivos. Evitar abstracciones
vacías creadas solo para cumplir una plantilla.

Estructura frontend de referencia para las fases posteriores:

``` text
frontend/
├── src/
│   ├── app/
│   │   ├── router/
│   │   ├── providers/
│   │   └── layouts/
│   ├── shared/
│   │   ├── api/
│   │   ├── ui/
│   │   │   ├── atoms/
│   │   │   ├── molecules/
│   │   │   ├── organisms/
│   │   │   └── templates/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── types/
│   │   └── utils/
│   ├── modules/
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── courts/
│   │   ├── physical-layout/
│   │   ├── boxes/
│   │   ├── case-files/
│   │   ├── administrative-documents/
│   │   ├── search/
│   │   ├── imports/
│   │   ├── ocr-review/
│   │   ├── loans/
│   │   ├── reconciliation/
│   │   ├── reports/
│   │   └── settings/
│   ├── styles/
│   └── main.tsx
└── tests/
```

------------------------------------------------------------------------

## 11. Estrategia de pruebas

### 11.1 Backend

-   Unitarias para validadores, servicios y transiciones.
-   Integración con PostgreSQL real de pruebas.
-   Integración con Redis para tareas y estados.
-   Pruebas de API con diferentes roles.
-   Pruebas de migraciones.
-   Pruebas de concurrencia para numeración y posiciones.
-   Pruebas de importación y reintento.
-   Pruebas de seguridad de archivos.
-   Pruebas de búsqueda con acentos, mayúsculas, sufijos y resultados
    ambiguos.
-   Pruebas de auditoría.
-   Pruebas de generación de exportaciones.
-   Pruebas de restauración de copias de seguridad.

### 11.2 Frontend

-   Pruebas unitarias de funciones y componentes.
-   Pruebas de formularios.
-   Pruebas de permisos de interfaz.
-   Pruebas de búsqueda y filtros.
-   Pruebas de estados de carga, error y vacío.
-   Pruebas de accesibilidad.
-   Pruebas E2E con roles diferentes.
-   Pruebas de sincronización de búsqueda con el plano 2D/3D.

### 11.3 Pruebas de aceptación críticas

1.  Crear una caja de expedientes y agregar varios expedientes e
    imputados.
2.  Intentar añadir un documento administrativo a esa caja y comprobar
    el rechazo.
3.  Crear una caja administrativa y comprobar el rechazo de expedientes.
4.  Asignar una caja a una posición y bloquear una segunda asignación
    concurrente.
5.  Buscar por NUC completo y por últimos cinco dígitos.
6.  Encontrar una caja sin ubicación confirmada.
7.  Importar un inventario, corregir errores, aprobarlo e importar sin
    duplicados silenciosos.
8.  Verificar que un OCR dudoso exige revisión.
9.  Mover una caja y conservar el historial.
10. Prestar y devolver un objeto según los permisos configurados.
11. Conciliar una caja ausente y resolver la discrepancia.
12. Exportar resultados filtrados y comparar sus totales.
13. Denegar acciones administrativas a un usuario de consulta, incluso
    llamando directamente a la API.
14. Restaurar una copia de seguridad de base de datos y archivos en un
    entorno aislado.
15. Buscar un expediente y resaltar la caja correcta en el plano y
    modelo 3D.

------------------------------------------------------------------------

## 12. Seguridad, privacidad y operación

Como el sistema se expondrá a Internet, se deben definir y aplicar al
menos estas medidas:

-   HTTPS obligatorio.
-   Contraseñas con hash seguro y política de recuperación.
-   Autorización en servidor para cada operación y recurso.
-   CORS restrictivo.
-   Limitación de tasa en autenticación y endpoints sensibles.
-   Validación de archivos por extensión, MIME y contenido.
-   Límites de tamaño, tiempo de procesamiento y páginas.
-   Protección contra archivos maliciosos y contenido activo.
-   Almacenamiento privado y enlaces de descarga autorizados.
-   Secretos fuera del repositorio.
-   Logs sin contraseñas, tokens ni contenido judicial innecesario.
-   Auditoría protegida.
-   Copias de seguridad cifradas y restauración probada.
-   Retención y eliminación conforme a políticas institucionales.
-   Revisión de dependencias y actualizaciones de seguridad.
-   Monitorización de fallos de API, base de datos, Redis y
    trabajadores.
-   Separación entre desarrollo, pruebas y producción.
-   Política de acceso para proveedores OCR externos.
-   Procedimiento para incidentes y exposición accidental de datos.

La institución debe determinar qué información puede enviarse a
servicios externos de OCR o IA. Si no existe autorización expresa, el
diseño debe permitir procesar documentos con herramientas locales o con
un proveedor aprobado.

------------------------------------------------------------------------

## 13. Migración del inventario existente

El inventario actual es parcial y está repartido entre datos digitales y
documentos físicos. No debe intentarse una importación masiva
irreversible en un solo paso.

### Procedimiento recomendado

1.  Reunir los archivos digitales existentes y clasificarlos por formato
    y procedencia.
2.  Conservar copias originales inalteradas.
3.  Calcular hashes y registrar un catálogo de archivos fuente.
4.  Identificar qué fuentes describen cajas, expedientes, documentos
    administrativos y ubicaciones.
5.  Crear perfiles de importación por estructura.
6.  Importar primero a un área de preparación, no al inventario oficial.
7.  Normalizar códigos de tribunal, años, NUC y sentencias.
8.  Detectar duplicados exactos y probables.
9.  Revisar muestras con el supervisor y el archivista.
10. Ejecutar un piloto con un área o conjunto acotado de anaqueles.
11. Conciliar físicamente las cajas del piloto.
12. Corregir reglas y repetir la importación de prueba.
13. Aprobar lotes de forma controlada.
14. Importar el resto en lotes trazables.
15. Registrar cajas cuya ubicación no se haya confirmado.
16. Mantener un informe de origen para poder reconstruir cómo llegó cada
    registro.

### Datos que deben preservarse

-   Archivo original.
-   Nombre de origen.
-   Número de página, fila o segmento cuando esté disponible.
-   Texto original reconocido.
-   Valor normalizado.
-   Usuario que revisó.
-   Fecha de aprobación.
-   Errores y decisiones tomadas.

------------------------------------------------------------------------

## 14. Riesgos principales y mitigaciones

  -----------------------------------------------------------------------
  Riesgo                  Impacto                 Mitigación
  ----------------------- ----------------------- -----------------------
  Formatos históricos     Registros rechazados o  Reglas configurables,
  inconsistentes          mal normalizados        excepciones auditadas y
                                                  revisión

  Códigos de tribunal     Asociación errónea      UUID interno,
  duplicados                                      confirmación del
                                                  catálogo y reglas de
                                                  vigencia

  OCR manuscrito          Datos judiciales        Revisión humana
  impreciso               incorrectos             obligatoria y
                                                  evaluación por campo

  Inventario físico       Ubicaciones falsas      Estado explícito de
  incompleto                                      ubicación y
                                                  conciliación gradual

  Importación con         Conteos y búsquedas     Lotes, hashes,
  duplicados              incorrectos             detección de duplicados
                                                  y aprobación

  Acceso por Internet     Exposición de           HTTPS, autorización,
                          información sensible    auditoría, límites y
                                                  pruebas de seguridad

  Concurrencia al asignar Posiciones duplicadas   Restricciones de base
  cajas                                           de datos y
                                                  transacciones

  Cambios de capacidad    Posiciones ocupadas     Validación y proceso de
                          inválidas               resolución antes de
                                                  aplicar cambios

  Modelo 3D pesado        Mala experiencia en     Carga progresiva,
                          equipos modestos        optimización y
                                                  alternativa 2D/lista

  Dependencia de OCR      Coste o exposición de   Evaluación previa,
  externo                 datos                   procesamiento local y
                                                  control de proveedor

  Migraciones defectuosas Interrupción o pérdida  Pruebas, copias de
                          de datos                seguridad y despliegue
                                                  controlado

  Exportaciones no        Fuga de información     Permisos, archivos
  autorizadas                                     privados y enlaces de
                                                  descarga con
                                                  vencimiento
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 15. Indicadores de éxito

Los objetivos numéricos definitivos deben fijarse con una muestra real,
pero se medirán al menos:

-   Porcentaje de cajas con ubicación confirmada.
-   Porcentaje de cajas conciliadas físicamente.
-   Número de cajas con discrepancias abiertas.
-   Tiempo de respuesta de búsqueda por NUC.
-   Tiempo de respuesta de búsqueda por imputado.
-   Tasa de duplicados detectados durante importación.
-   Precisión de extracción por campo y tipo de documento.
-   Porcentaje de filas OCR corregidas manualmente.
-   Porcentaje de lotes importados sin errores bloqueantes.
-   Préstamos vencidos y tiempo medio de devolución.
-   Porcentaje de operaciones críticas con auditoría completa.
-   Éxito de copias de seguridad y restauraciones.
-   Errores de API y fallos de tareas en segundo plano.
-   Rendimiento del plano 2D/3D con el volumen objetivo.

------------------------------------------------------------------------

## 16. Orden de ejecución y dependencias

La secuencia recomendada del backend es:

1.  B0 Preparación.
2.  B1 Análisis y contratos.
3.  B2 Base de datos y migraciones.
4.  B3 Infraestructura de API.
5.  B4 Autenticación y permisos.
6.  B5 Catálogos.
7.  B6 Inventario físico.
8.  B7 Cajas y contenido documental.
9.  B8 Búsqueda.
10. B9 Auditoría, préstamos y movimientos.
11. B10 Archivos e importaciones.
12. B11 OCR.
13. B12 Informes y exportaciones.
14. B13 Etiquetas.
15. B14 Conciliación.
16. B15 Seguridad y rendimiento.
17. B16 Pruebas integrales y cierre del backend.

Algunas actividades internas pueden avanzar en paralelo cuando sus
contratos estén definidos, pero no se debe adelantar el frontend
completo mientras el modelo de datos y los contratos de API sigan
cambiando sin control.

La secuencia del frontend será:

1.  F1 Base del proyecto.
2.  F2 Sistema de diseño atómico.
3.  F3 Autenticación y navegación.
4.  F4 Panel de control.
5.  F5 CRUD.
6.  F6 Búsqueda.
7.  F7 Plano 2D.
8.  F8 Modelo 3D.
9.  F9 Revisión OCR.
10. F10 Préstamos, traslados y conciliación.
11. F11 Exportaciones y acabado.
12. Integración y despliegue.

------------------------------------------------------------------------

## 17. Definition of Done --- definición de terminado

Una fase o módulo solo se considerará terminado cuando:

-   Cumpla los requisitos documentados.
-   Incluya validaciones de entrada y reglas de negocio.
-   Aplique autenticación y autorización cuando corresponda.
-   Tenga pruebas automatizadas apropiadas.
-   Maneje errores, carga, ausencia de datos y fallos de dependencias.
-   Actualice migraciones y contratos cuando corresponda.
-   Registre auditoría en operaciones críticas.
-   Tenga documentación y comandos reproducibles.
-   Pase lint, tipado y pruebas.
-   No deje secretos en el repositorio.
-   Incluya los riesgos o limitaciones pendientes.
-   Haya sido revisado contra sus criterios de aceptación.

------------------------------------------------------------------------

## 18. Decisiones pendientes antes de fijar la implementación

Estas cuestiones no impiden redactar el plan, pero deben resolverse
antes de desarrollar las partes afectadas:

1.  **Servidor:** sistema operativo, proveedor, dominio, proxy inverso y
    estrategia de despliegue.
2.  **Autenticación:** sesiones con cookies seguras o tokens,
    recuperación de cuentas y posible MFA.
3.  **Formato de sentencia:** confirmar la estructura exacta y los
    segmentos numéricos/alfanuméricos.
4.  **NUC histórico:** confirmar si `00000` y
    `YYYY-CODIGOTRIBUNAL-NUMPROCESO` son los únicos formatos o existen
    otros.
5.  **Códigos de tribunales:** aclarar códigos repetidos y relaciones
    institucionales.
6.  **Caja:** confirmar si el año y el tribunal son obligatorios para
    todos los tipos y si el contenido debe coincidir siempre con ambos.
7.  **Préstamos:** determinar si se prestan cajas completas, expedientes
    individuales o ambos.
8.  **Archivos:** elegir almacenamiento privado local o compatible con
    S3 y política de retención.
9.  **OCR:** decidir si se permiten proveedores externos y qué
    presupuesto existe.
10. **Volumen de archivos:** estimar cantidad, tamaño medio, páginas y
    frecuencia de importaciones.
11. **Modelo físico:** determinar si se necesitan dimensiones métricas
    reales, escala, orientación y obstáculos del local.
12. **Numeración:** definir si cambiar la política solo afecta cajas
    nuevas o si se permitirá renumerar cajas existentes mediante
    operación auditada.

Estas decisiones deben quedar registradas en el documento de
arquitectura y actualizarse cuando se aprueben cambios.

------------------------------------------------------------------------

## 19. Resultado esperado

Al completar el proyecto, la institución dispondrá de un sistema modular
que:

-   Mantiene un inventario único de cajas, expedientes y documentos
    administrativos.
-   Representa la estructura real de áreas, anaqueles, bandejas y
    posiciones.
-   Localiza expedientes mediante búsqueda y visualización 2D/3D.
-   Conserva los originales de los inventarios importados.
-   Automatiza extracción documental con revisión humana.
-   Gestiona movimientos, préstamos, devoluciones y discrepancias.
-   Produce exportaciones y reportes controlados.
-   Conserva auditoría de operaciones críticas.
-   Permite configurar tribunales, reglas de identificadores y
    capacidades físicas.
-   Puede desplegarse en Internet con controles de seguridad apropiados.
-   Mantiene una base técnica preparada para crecer sin acoplar el
    dominio a la interfaz gráfica.

**Regla de ejecución:** primero se cierra el backend de manera modular,
probado y documentado; después se construye el frontend sobre contratos
estables; finalmente se ejecutan la integración, la migración del
inventario real, la validación física y la puesta en producción.
