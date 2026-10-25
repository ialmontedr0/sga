# AGENTS.md --- Sistema de Gestión Documental Judicial

**Versión:** 1.0\
**Idioma de trabajo y documentación:** español\
**Estado:** instrucciones maestras para agentes de programación y
colaboradores\
**Proyecto:** sistema web para administrar el archivo central judicial,
sus cajas, expedientes, documentos administrativos, ubicaciones físicas,
digitalización, movimientos, auditoría e inventario.

> Este archivo es la fuente de instrucciones operativas para cualquier
> agente que trabaje en el repositorio. Léelo completo antes de
> modificar código. Si una decisión técnica contradice una regla de
> negocio de este documento, prevalece la regla de negocio. Si un
> requisito no está confirmado, no lo inventes: registra la
> incertidumbre, implementa una solución configurable cuando sea seguro
> y documenta qué decisión requiere validación humana.

------------------------------------------------------------------------

## 1. Misión del proyecto

Construir un sistema de gestión documental judicial confiable,
auditable, seguro y mantenible para el archivo central. Debe relacionar
el inventario físico con el inventario digital, permitir localizar
expedientes y documentos, apoyar la incorporación de datos históricos
mediante OCR/importaciones revisables y mostrar las ubicaciones en un
plano 2D y un modelo 3D interactivo.

La solución debe poder utilizarse por Internet. Por eso, autenticación,
autorización, protección de documentos, registros de auditoría, manejo
de secretos, copias de seguridad y controles de despliegue son
requisitos fundamentales, no tareas opcionales de última hora.

### Orden de implementación obligatorio

1.  **Backend completo primero:** dominio, base de datos, migraciones,
    autenticación, autorización, servicios, API, validaciones, búsqueda,
    auditoría, importaciones/OCR, movimientos, préstamos, reportes,
    tareas asíncronas, pruebas y documentación.
2.  **Frontend después:** React + TypeScript + Vite + Tailwind CSS,
    arquitectura modular y diseño atómico, consumiendo contratos de API
    definidos y probados.
3.  **Integración final:** experiencia completa, plano 2D, modelo 3D,
    validación de flujos y preparación para producción.

No se debe comenzar construyendo pantallas desconectadas del dominio ni
saltar las fases de diseño de datos y reglas de negocio. Una función no
se considera completa por tener solamente una pantalla o un endpoint.

------------------------------------------------------------------------

## 2. Stack y restricciones técnicas

### 2.1 Tecnologías confirmadas

**Backend** - Python. - FastAPI como framework HTTP. - Uvicorn como
servidor ASGI. - PostgreSQL como base de datos relacional. - SQLAlchemy
para persistencia y mapeo objeto-relacional. - Alembic para todas las
migraciones del esquema. - `uv` para gestionar entorno, dependencias y
comandos Python. - Redis, ya instalado, para los usos que se definan:
colas, coordinación, caché o estado temporal. No utilizar Redis como
fuente de verdad de los registros judiciales.

**Frontend** - React. - TypeScript. - Vite. - Tailwind CSS. -
Componentes reutilizables con enfoque de diseño atómico. - Interfaz
administrativa moderna, responsive y en español. - Tema claro y
oscuro. - Barra lateral de navegación.

**Infraestructura** - PostgreSQL y Redis ya están instalados en el
entorno destino. - Despliegue previsto a través de Internet. - No asumir
Docker como requisito; no es parte del stack confirmado para este
proyecto. - Configurar el servidor y los servicios según el entorno
real, sin incluir secretos en el repositorio.

### 2.2 Principios de implementación

-   Mantener Python y TypeScript con tipado estricto y contratos
    explícitos.
-   Preferir soluciones sencillas, mantenibles y comprobables antes que
    abstracciones innecesarias.
-   Separar dominio, infraestructura, API, tareas asíncronas y
    presentación.
-   Usar operaciones de base de datos transaccionales cuando una acción
    afecte varias entidades.
-   No duplicar reglas de negocio en múltiples capas; la validación del
    servidor es autoritativa.
-   No guardar fechas, NUC, identificadores de sentencia o códigos
    judiciales como números si pueden contener ceros iniciales, guiones
    o formatos históricos. Usar cadenas de texto cuando el identificador
    sea semántico.
-   No introducir dependencias nuevas sin explicar su necesidad y
    comprobar compatibilidad, licencia, mantenimiento y superficie de
    riesgo.
-   No crear endpoints o tablas ficticias para simular funcionalidades
    todavía no implementadas.
-   Evitar lógica de negocio en componentes React.
-   No usar datos de producción en pruebas.
-   No registrar en logs contraseñas, tokens, contenido documental
    sensible ni datos personales innecesarios.

### 2.3 Idioma y convenciones

-   Toda la documentación, manuales, comentarios explicativos, mensajes
    de validación e interfaz de usuario deben estar en español.
-   Los identificadores de código (variables, clases, funciones,
    módulos, tablas y columnas) pueden y preferiblemente deben usar
    inglés consistente.
-   Los nombres de dominio visibles al usuario deben respetar la
    terminología judicial y archivística en español: caja, expediente,
    imputado, tribunal, anaquel, bandeja, posición, préstamo, traslado,
    devolución, conciliación e inventario.
-   Fechas visibles: formato `DD/MM/AAAA` cuando se muestre una fecha
    completa. La API y la base de datos deben usar tipos y formatos
    inequívocos (ISO 8601 en intercambio; `DATE`/`TIMESTAMP` en base de
    datos).
-   No convertir automáticamente una cadena de identificador a número ni
    eliminar ceros iniciales.

------------------------------------------------------------------------

## 3. Contexto operativo confirmado

### 3.1 Usuarios y roles

Se espera un grupo inicial de **10 usuarios**:

-   2 administradores.
-   1 supervisor de archivo.
-   1 archivista.
-   1 digitalizador.
-   5 usuarios de consulta.

Implementar autorización por roles y permisos granulares cuando sea
útil. Los nombres de roles no deben sustituir a la verificación de
permisos en el servidor.

Matriz funcional inicial recomendada, sujeta a validación en la fase de
permisos:

  ----------------------------------------------------------------------------------------
  Capacidad           Administrador   Supervisor   Archivista   Digitalizador     Consulta
  ----------------- --------------- ------------ ------------ --------------- ------------
  Gestionar                      Sí    No, salvo           No              No           No
  usuarios, roles y                      permiso
  configuración                        explícito

  Gestionar áreas,               Sí           Sí        Según              No           No
  anaqueles y                                         permiso
  capacidades

  Crear/editar                   Sí           Sí           Sí   Según permiso           No
  cajas y metadatos
  archivísticos

  Buscar y                       Sí           Sí           Sí              Sí           Sí
  consultar
  registros
  autorizados

  Revisar/aprobar                Sí           Sí        Según  No por defecto           No
  importaciones OCR                                   permiso

  Ejecutar                       Sí           Sí        Según              Sí           No
  importaciones y                                     permiso
  digitalización

  Registrar                      Sí           Sí           Sí   Según permiso           No
  préstamos,
  traslados y
  devoluciones

  Conciliar                      Sí           Sí           Sí    Apoyo, según           No
  inventario                                                          permiso

  Ver auditoría                  Sí    Sí, según    Limitado,              No           No
  completa                              política        según
                                                      permiso

  Configurar reglas              Sí         Solo           No              No           No
  globales                              permisos
                                        expresos
  ----------------------------------------------------------------------------------------

Esta matriz es una base de diseño, no una autorización para conceder
acceso indiscriminado. Definir permisos explícitos, aplicar mínimo
privilegio y probar cada rol. Las acciones sensibles deben requerir
usuario autenticado y quedar auditadas.

### 3.2 Inventario actual

El inventario declarado llega a **4.401 cajas**. La numeración global
siguiente es **4.402**, pero debe existir una política configurable para
la numeración futura. No codificar el número 4402 como constante
inmutable ni reutilizar números borrados.

El inventario está parcialmente registrado en formato digital y
parcialmente en inventarios físicos. Por ello: - Debe ser posible
importar y revisar lotes. - Debe distinguirse dato confirmado de dato
pendiente de verificación. - No se deben inventar datos ausentes. - Debe
poder registrarse una caja aunque su ubicación física no esté
confirmada. - La migración inicial debe conservar referencias y
numeración histórica. - Antes de cargar registros históricos se debe
detectar duplicados, formatos anómalos y conflictos de ubicación.

### 3.3 Áreas y anaqueles iniciales

Configuración física inicial indicada por el usuario:

  Área                Anaqueles iniciales     Cantidad
  ------------------- --------------------- ----------
  Zona A              A1--A9                         9
  Zona B              B1--B8                         8
  Zona C              C1--C6                         6
  Zona D              D1--D13                       13
  Zona O              O1--O3                         3
  **Total inicial**                             **39**

Las áreas y los anaqueles deben poder crearse, editarse, desactivarse y
reorganizarse por usuarios autorizados. Esta lista es la configuración
inicial conocida, no una limitación fija del sistema.

Cada anaquel tendrá una capacidad configurable que puede incluir: -
Número de bandejas/niveles. - Número de posiciones por bandeja. -
Identificación/etiqueta de cada posición. - Estado de cada posición. -
Capacidad total derivada y ocupación real.

Ejemplos de configuraciones indicadas: - 7 bandejas × 9 cajas por
bandeja. - 7 bandejas × 8 cajas por bandeja. - 7 bandejas × 7 cajas por
bandeja. - Otras configuraciones definidas posteriormente.

No asumir que todos los anaqueles comparten la misma capacidad. Separar
capacidad teórica, ocupación real y disponibilidad. Una posición no
puede alojar dos cajas activas a la vez. La asignación debe protegerse
contra concurrencia mediante restricciones/operaciones transaccionales.

### 3.4 Ubicación física y trazabilidad

Una caja puede tener: - Ubicación confirmada. - Ubicación pendiente de
verificación. - Ubicación desconocida/no asignada. - Estado de préstamo
o salida temporal. - Historial de ubicaciones anteriores.

No representar una ubicación desconocida como si fuera una posición
física válida. Las cajas sin ubicación deben aparecer en listas de
pendientes de localización y conciliación. Cada traslado debe conservar
origen, destino, fecha, usuario, motivo y referencia del movimiento.

------------------------------------------------------------------------

## 4. Entidades y reglas de dominio

El modelo definitivo se documentará antes de crear las migraciones
iniciales. Los nombres aquí descritos son conceptos de dominio; los
nombres técnicos concretos pueden ajustarse si se mantiene el
comportamiento y se documenta el motivo.

### 4.1 Entidades mínimas esperadas

-   Usuario, rol y permiso.
-   Tribunal.
-   Área.
-   Anaquel.
-   Bandeja/nivel o representación equivalente.
-   Posición física.
-   Caja.
-   Expediente.
-   Imputado/persona relacionada con expediente.
-   Documento administrativo.
-   Archivo digital/documento original.
-   Lote de importación.
-   Fila/registro extraído durante la importación.
-   Resultado de OCR y advertencias de validación.
-   Préstamo.
-   Movimiento/traslado.
-   Devolución.
-   Etiqueta/código QR.
-   Sesión o evento de conciliación de inventario.
-   Evento de auditoría.
-   Configuración/política de numeración.
-   Tarea asíncrona y estado de procesamiento, si se utiliza una cola.
-   Reporte/exportación, si requiere seguimiento persistente.

Evitar una tabla genérica opaca que elimine integridad referencial. Las
relaciones deben expresar las reglas del dominio.

### 4.2 Cajas

Reglas obligatorias: 1. Cada caja tiene identificador interno estable,
independiente del número visible. 2. El número visible de caja pertenece
a una secuencia global y no debe reutilizarse una vez asignado. 3. La
próxima numeración se obtiene de una política/configuración
transaccional, no de `MAX(number) + 1` sin protección contra
concurrencia. 4. Cada caja tiene un tipo documental excluyente: -
`EXPEDIENTES` - `DOCUMENTOS_ADMINISTRATIVOS` 5. Una caja no puede
mezclar expedientes judiciales y documentos administrativos. 6. Una caja
se relaciona con un tribunal y un año de referencia conforme al tipo de
caja y reglas validadas. 7. Una caja puede existir sin ubicación física
confirmada. 8. Una caja puede estar vacía, ocupada, temporalmente
prestada, pendiente de localizar, en conciliación o en otro estado
documentado. No crear estados redundantes ni permitir transiciones
arbitrarias. 9. Los cambios de ubicación se realizan mediante
movimientos; no sobrescribir la ubicación sin conservar el historial.
10. No eliminar físicamente una caja que tenga expedientes, documentos,
movimientos o auditoría vinculada. Usar baja lógica o estado
archivístico apropiado, manteniendo trazabilidad. 11. Si se cambia un
atributo que las reglas declaren inmutable (por ejemplo, tipo, tribunal
o año una vez que contiene contenido), exigir un flujo explícito de
corrección/traslado y registrar motivo, usuario y valores
previos/nuevos. Validar la inmutabilidad exacta con las reglas
archivísticas antes de habilitar edición. 12. No permitir asignar una
caja a una posición ocupada ni exceder la capacidad configurada del
anaquel.

### 4.3 Expedientes judiciales

Campos iniciales: - NUC. - Tribunal. - Año de referencia, si no se
deriva de una regla de negocio explícita. - Uno o varios imputados,
almacenados individualmente. - Fecha de entrada. - Identificador de
sentencia/resolución. - Fecha de sentencia/resolución. - Caja
asociada. - Metadatos de procedencia, estado de revisión y auditoría.

El NUC es un **identificador de texto**, no un entero. Debe admitir
formatos históricos y configurables. Ejemplos confirmados: - `00001`
(cinco dígitos). - `2022-102-00001` (`YYYY-CODIGOTRIBUNAL-NUMPROCESO`).

También se debe permitir configurar validadores o perfiles de formato
por tribunal/periodo cuando el inventario real lo requiera. No rechazar
un expediente histórico únicamente porque no coincide con el patrón
moderno. Los formatos desconocidos deben poder registrarse con una
advertencia y revisión, según los permisos establecidos.

La búsqueda debe poder localizar por NUC completo y por sus últimos
cinco dígitos. La búsqueda parcial no debe reemplazar la identificación
exacta y debe advertir si existen varios resultados.

Los imputados se guardan en registros relacionados individuales; no
almacenar la lista completa únicamente en una cadena separada por comas.
Evitar duplicados de relación dentro del mismo expediente, sin imponer
deduplicación global de personas por nombre sin un identificador
confiable.

Las fechas ausentes o de precisión limitada deben representarse con un
estado explícito de "desconocida/no registrada" en lugar de fabricar una
fecha.

### 4.4 Sentencias y resoluciones

El identificador de sentencia es texto. Los patrones deben ser
configurables por tribunal, categoría o periodo, por ejemplo: -
`000-0000-SSSS-0000`.

También se mencionaron identificadores o sistemas como `SADM`, `SPEN`,
`RPE` y otros. No asumir que son prefijos intercambiables ni imponer un
único patrón global. Mantener configuraciones de formato, validadores y
reglas de normalización claramente documentados. Preservar el valor
original cuando se normalice una representación para búsqueda.

Los campos mínimos de expediente incluyen el identificador de
sentencia/resolución y su fecha, cuando existan. El sistema debe poder
buscar por sentencia completa o fragmento de acuerdo con permisos y
estrategia de indexación.

### 4.5 Documentos administrativos

Una caja de documentos administrativos contiene documentos
administrativos, no expedientes judiciales. Cada documento
administrativo puede incluir: - Nombre/título del documento. - Tribunal
relacionado. - Año. - Mes opcional, porque el dato puede estar
disponible solo con precisión anual. - Caja. - Archivo digital asociado,
si existe. - Estado de revisión y procedencia.

Representar el mes como opcional y no inventar `01/01` cuando solo se
conoce el año. Definir cómo se representan los documentos con fecha
parcial en consultas, reportes y filtros.

### 4.6 Tribunales iniciales

Precargar estos registros iniciales como catálogo editable:

  -----------------------------------------------------------------------
  Nombre                  Código                  Estado indicado
  ----------------------- ----------------------- -----------------------
  Juzgado de Instrucción  589                     Por confirmar

  Juzgado de Instrucción  589                     Por confirmar
  en Atención Permanente

  Corte de Apelación      102                     Activo, según
                                                  información inicial

  Primera Cámara Penal    106                     Inactivo
  del Juzgado de Primera
  Instancia

  Segunda Cámara Penal    107                     Inactivo
  del Juzgado de Primera
  Instancia

  Juzgado de Primera      107                     Por confirmar
  Instancia Unipersonal

  Tribunal Ejecución de   107-01                  Por confirmar
  la Pena

  Tribunal Colegiado de   107-02                  Por confirmar
  Primera Instancia
  -----------------------------------------------------------------------

**Importante:** existen códigos repetidos indicados deliberadamente o
pendientes de aclaración (589 y 107). No imponer unicidad global del
código como restricción sin confirmar el significado del catálogo.
Diseñar el código con contexto suficiente (por ejemplo, código +
tipo/periodo/tribunal o una clave interna), conservar los datos
recibidos y crear una tarea de revisión de conflictos. Los códigos no
deben usarse como clave primaria.

El estado activo/inactivo debe ser explícito y administrable. Desactivar
un tribunal no debe borrar expedientes, cajas ni relaciones históricas.

------------------------------------------------------------------------

## 5. Búsqueda global

La búsqueda global es una función central. Debe poder filtrar y
localizar por: - NUC completo. - Últimos cinco dígitos del NUC. -
Imputado(s). - Tribunal y código. - Año. - Identificador de
sentencia/resolución. - Fecha de entrada. - Fecha de sentencia. - Nombre
del documento administrativo. - Número de caja. - Área. - Anaquel. -
Bandeja/nivel. - Posición física. - Estado de ubicación (confirmada,
pendiente, desconocida). - Tipo de caja. - Estado del préstamo o
movimiento, cuando corresponda.

Requisitos: - Combinar filtros cuando tenga sentido. - Paginación,
ordenamiento estable y límites de resultados. - Índices PostgreSQL
adecuados a los patrones reales. - Búsqueda de texto sin sacrificar
exactitud de identificadores. - No convertir coincidencias parciales en
una única coincidencia si hay varias. - Mostrar los campos que explican
por qué se encontró un resultado. - Respetar permisos y ocultar
información no autorizada. - Permitir abrir el detalle y visualizar la
caja en plano 2D/3D cuando tenga una ubicación confirmada. - Si no tiene
ubicación confirmada, mostrar el estado y ofrecer un flujo de
localización/conciliación a los roles autorizados. - Probar NUC con
ceros iniciales, guiones, formatos históricos, valores duplicados y
búsqueda por últimos cinco dígitos.

Sugerencias funcionales adicionales que se pueden incorporar si no
desvían el alcance: - Búsquedas guardadas por usuario. - Historial de
consultas recientes sin guardar información sensible innecesaria. -
Indicadores de resultados con datos incompletos. - Filtros rápidos por
ubicación desconocida, préstamos vencidos, importaciones pendientes y
discrepancias de inventario.

------------------------------------------------------------------------

## 6. OCR, digitalización e importaciones

### 6.1 Formatos de entrada

La solución debe contemplar: - PDF digital con texto seleccionable. -
PDF escaneado como imagen. - DOCX. - Documentos antiguos manuscritos,
con expectativas realistas de precisión.

No afirmar que el OCR manuscrito será perfecto. La calidad depende de la
escritura, resolución, inclinación, manchas, calidad de escaneo y
complejidad de tablas. Todo resultado extraído debe ser revisable por
una persona antes de incorporarse como dato definitivo.

### 6.2 Flujo obligatorio de importación

1.  Usuario autorizado crea un lote y carga uno o varios archivos.
2.  Validar extensión, MIME real, tamaño, cantidad de páginas, nombre y
    seguridad del archivo.
3.  Conservar el original sin alterarlo y registrar hash criptográfico,
    tamaño, tipo, usuario, fecha y lote.
4.  Procesar extracción de texto/OCR en tarea controlada; no bloquear
    innecesariamente la petición HTTP.
5.  Identificar metadatos de cabecera, como número de caja, tribunal,
    código y año, si aparecen.
6.  Extraer tabla de expedientes con NUC, imputados, sentencia y fecha
    de sentencia, según el formato del documento.
7.  Mostrar una vista previa editable con filas, campos, nivel de
    confianza si está disponible, alertas y errores.
8.  Validar contra catálogos, formatos configurados, duplicados,
    relaciones caja/tribunal/año y tipo de caja.
9.  Marcar explícitamente errores, advertencias y campos no reconocidos.
10. Permitir corrección manual de los campos extraídos.
11. Exigir aprobación explícita por un usuario autorizado antes de
    guardar registros definitivos.
12. Guardar de forma transaccional las filas aprobadas, la procedencia y
    el vínculo al original.
13. Generar resumen de insertados, actualizados, omitidos, duplicados y
    errores.
14. Mantener registro de quién procesó, revisó, aprobó y aplicó el lote.
15. Permitir reintento controlado sin duplicar registros ya aplicados.

No ejecutar una importación definitiva automáticamente tras OCR. No
actualizar registros existentes por coincidencia aproximada sin decisión
explícita del usuario. Una corrección manual debe conservarse en la
trazabilidad del lote.

### 6.3 Archivos originales y seguridad

-   Guardar originales en almacenamiento privado, fuera del directorio
    público estático.
-   No confiar en el nombre, extensión o MIME declarados por el cliente.
-   Aplicar límites de tamaño y procesamiento, validación de contenido y
    protección frente a archivos maliciosos.
-   No exponer enlaces públicos permanentes a documentos judiciales.
-   Descargar o visualizar mediante endpoint autorizado con comprobación
    de permisos.
-   Configurar retención, respaldos y recuperación de los archivos.
-   No registrar contenido íntegro de documentos en logs.
-   Definir, documentar y probar la estrategia de almacenamiento antes
    de producción.

### 6.4 Calidad y observabilidad OCR

-   Registrar versión/configuración del motor y fecha de procesamiento.
-   Separar texto extraído del dato aceptado.
-   Mantener advertencias y correcciones.
-   Mostrar incertidumbre de forma entendible.
-   Permitir que un lote falle parcialmente sin dejar relaciones
    corruptas.
-   Añadir pruebas con PDF de texto, PDF escaneado, DOCX, tablas
    partidas, NUC con ceros iniciales, manuscritos difíciles y archivos
    inválidos.
-   La selección de motores OCR y sus dependencias es una decisión
    técnica que debe documentarse y comprobarse en el entorno objetivo.
    No afirmar que un motor reconoce manuscritos con precisión
    garantizada.

------------------------------------------------------------------------

## 7. Plano 2D y modelo 3D

La aplicación debe ofrecer una representación interactiva del espacio
físico: - Plano 2D de la sala/archivo, áreas y anaqueles. - Modelo 3D
interactivo de la configuración física. - Selección de área, anaquel,
bandeja y posición. - Selección de una caja desde la representación. -
Vista de ocupación, capacidad y posiciones libres. - Visualización de
los resultados de búsqueda sobre la ubicación física correspondiente. -
Indicación visual clara para ubicación desconocida, pendiente, ocupada,
libre, en préstamo o en conflicto. - Posibilidad de configurar
capacidades por anaquel sin recompilar el frontend. - Accesibilidad
alternativa mediante tablas/listas; la localización no puede depender
exclusivamente de gráficos.

Las coordenadas y la geometría visual deben derivarse de los datos
configurados. No mantener capacidades o anaqueles codificados de forma
independiente en el frontend. Los cambios en la configuración física
deben reflejarse en las vistas 2D y 3D.

Antes de elegir bibliotecas 2D/3D, evaluar compatibilidad con
React/Vite, accesibilidad, rendimiento, licencias y mantenimiento.
Cargar el modelo 3D de manera diferida si es necesario para no penalizar
la búsqueda y el panel administrativo. Debe existir un estado
alternativo útil si la visualización 3D no puede cargarse.

------------------------------------------------------------------------

## 8. Préstamos, traslados, devoluciones, QR e inventario

### 8.1 Préstamos y devoluciones

Implementar un ciclo de préstamo con: - Caja/expediente o unidad
prestada, conforme a las reglas aprobadas. - Solicitante y
responsable. - Fecha de salida. - Fecha de vencimiento, si aplica. -
Motivo y referencia autorizante. - Estado (solicitado, aprobado,
entregado, devuelto, vencido, cancelado u otro conjunto mínimo
aprobado). - Fecha real de devolución. - Usuario que ejecutó cada
transición. - Evidencia/observaciones permitidas. - Alertas de
vencimiento y préstamos pendientes.

No permitir transiciones inválidas ni registrar una devolución si no
existe un préstamo abierto válido. Definir si se presta una caja
completa o unidades documentales individuales; no asumirlo
silenciosamente. Mientras esté prestada, la visualización física debe
indicar que la caja no está disponible en su posición habitual, sin
perder su ubicación de origen.

### 8.2 Traslados

Cada traslado debe incluir: - Caja. - Origen y destino. - Fecha/hora. -
Usuario responsable. - Motivo. - Estado de operación. - Aprobación
cuando la política lo requiera. - Registro de auditoría.

La actualización de ubicación y el registro del movimiento deben ocurrir
en una transacción. Si la transacción falla, no debe quedar la caja
movida sin historial ni historial sin movimiento real. Proteger el
destino contra ocupación concurrente.

### 8.3 Códigos QR

-   Generar QR con un identificador opaco o URL interna protegida, no
    con datos personales o judiciales completos.
-   El QR no debe conceder acceso por sí solo a documentos restringidos.
-   Al escanearlo, validar autenticación y permisos.
-   Permitir imprimir etiquetas y regenerar un código revocado.
-   Registrar emisión, reimpresión y sustitución cuando sea relevante.
-   Probar que un QR antiguo o revocado no exponga datos.
-   El número visible de caja puede mostrarse junto al QR en la
    etiqueta, de acuerdo con la política de impresión.

### 8.4 Conciliación de inventario

Crear sesiones de conciliación con: - Alcance (área, anaquel, bandeja,
cajas específicas o inventario general). - Fecha de inicio y cierre. -
Responsable y participantes. - Cajas esperadas. - Cajas encontradas. -
Cajas no localizadas. - Cajas encontradas en ubicación inesperada. -
Cajas físicas sin registro digital. - Duplicados/conflictos. -
Diferencias y resolución. - Evidencia/observaciones permitidas. -
Aprobación y auditoría.

No modificar automáticamente el inventario para eliminar discrepancias.
Presentar diferencias y requerir resolución autorizada. El historial de
la conciliación debe conservar los resultados previos y finales.

------------------------------------------------------------------------

## 9. Auditoría e historial

La auditoría es obligatoria para las operaciones sensibles y las
modificaciones de datos de negocio. Registrar como mínimo: -
Usuario/actor (incluyendo identidad del sistema para tareas
automatizadas). - Fecha/hora. - Tipo de entidad e identificador. -
Acción. - Valores anteriores y nuevos, cuando sea pertinente. - Motivo,
cuando la acción lo requiera. - Identificador de correlación de
petición/tarea si existe. - Resultado de la operación. - Origen de
datos: interfaz, importación, OCR, tarea automática u otro.

Reglas: - No permitir que usuarios ordinarios alteren o borren eventos
de auditoría. - No guardar contraseñas, tokens, secretos ni contenido
sensible innecesario en la auditoría. - Redactar o excluir datos
personales que no sean necesarios para explicar el cambio. - Las
eliminaciones de registros de negocio deben ser lógicas o sujetas a
política de retención; nunca deben borrar el historial asociado. - Las
importaciones deben registrar origen y quién aprobó. - Los cambios de
ubicación, préstamo, devolución, cambio de rol, configuración de
numeración y correcciones de registros deben quedar auditados. - Los
eventos de auditoría deben insertarse de forma consistente con la
operación de negocio o mediante un mecanismo transaccional fiable. -
Definir retención, acceso, exportación y protección de auditoría.

------------------------------------------------------------------------

## 10. Exportaciones y reportes

Formatos requeridos: - Excel (`.xlsx`). - CSV. - PDF.

Los reportes deben poder filtrarse por: - Tribunal. - Año. - Área. -
Anaquel. - Tipo de caja. - Y, cuando aplique, ubicación, estado,
importación, préstamo o conciliación.

Requisitos: - La exportación debe respetar los filtros visibles y los
permisos del usuario. - Incluir encabezados legibles, fecha de
generación y criterios aplicados. - No perder ceros iniciales ni
convertir NUC/códigos/sentencias en números. - Prevenir inyección de
fórmulas en CSV/Excel para valores que comiencen con caracteres
interpretables como fórmulas. - Gestionar exportaciones grandes mediante
tareas en segundo plano si es necesario. - Proteger descargas y
establecer expiración para archivos temporales. - Probar con caracteres
españoles, datos vacíos, filas numerosas y formatos históricos.

------------------------------------------------------------------------

## 11. Seguridad para una aplicación accesible por Internet

Implementar seguridad desde el principio: - Autenticación robusta y
gestión segura de sesiones/tokens. - Hash de contraseñas con un
algoritmo moderno recomendado por la biblioteca elegida; nunca almacenar
contraseñas en texto plano. - Autorización por rol/permisos en el
servidor para cada operación. - Validación de entrada en API y límites
de longitud/tamaño. - Protección frente a SQL injection mediante
ORM/consultas parametrizadas. - Protección frente a XSS, CSRF cuando
aplique, abuso de sesión y ataques de fuerza bruta. - CORS restringido a
orígenes conocidos; no usar comodines con credenciales. - HTTPS en
producción. - Cookies seguras si se usan cookies: `HttpOnly`, `Secure`,
`SameSite` apropiado. - Rotación y almacenamiento externo de secretos
mediante variables de entorno o gestor seguro. - Rate limiting para
autenticación, OCR, búsquedas costosas y descarga de documentos. -
Límites de paginación y recursos. - Validación del contenido real de
archivos, límites de páginas y tiempos de procesamiento. - Protección de
endpoints de archivos y QR. - No exponer errores internos, stack traces,
configuración ni secretos a clientes. - Logs estructurados sin datos
judiciales sensibles innecesarios. - Dependencias fijadas y revisadas;
no instalar paquetes abandonados o de procedencia dudosa. - Copias de
seguridad cifradas cuando corresponda y pruebas periódicas de
restauración. - Política de retención de datos y revisión de permisos. -
Cuentas iniciales con credenciales temporales seguras y obligación de
cambio; nunca incluir contraseñas por defecto en Git. - Documentar
procedimientos de respuesta ante incidentes.

La aplicación gestiona información judicial potencialmente sensible. No
implementar rutas de descarga pública, índices de archivos accesibles
sin autenticación ni búsquedas que permitan eludir los permisos.

------------------------------------------------------------------------

## 12. Arquitectura de backend

Mantener una arquitectura modular. Una estructura inicial sugerida
---ajustable durante la fase de preparación, sin mezclar
responsabilidades--- es:

``` text
backend/
├── pyproject.toml
├── uv.lock
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── permissions.py
│   │   ├── logging.py
│   │   ├── errors.py
│   │   └── pagination.py
│   ├── db/
│   │   ├── session.py
│   │   ├── base.py
│   │   └── health.py
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   ├── api/
│   │   ├── deps.py
│   │   └── v1/
│   ├── modules/
│   │   ├── auth/
│   │   ├── users/
│   │   ├── courts/
│   │   ├── locations/
│   │   ├── boxes/
│   │   ├── cases/
│   │   ├── administrative_documents/
│   │   ├── search/
│   │   ├── files/
│   │   ├── imports/
│   │   ├── ocr/
│   │   ├── loans/
│   │   ├── movements/
│   │   ├── qr/
│   │   ├── inventory/
│   │   ├── audit/
│   │   └── reports/
│   ├── tasks/
│   └── utils/
└── tests/
    ├── unit/
    ├── integration/
    ├── api/
    ├── security/
    └── fixtures/
```

La estructura es orientativa, no una orden de crear módulos vacíos.
Crear cada módulo cuando exista funcionalidad real. Evitar dependencias
circulares y modelos que importen la aplicación HTTP. Mantener los
esquemas de entrada/salida separados de los modelos ORM.

### 12.1 Contratos API

-   Versionar endpoints (por ejemplo, `/api/v1`).
-   Mantener documentación OpenAPI.
-   Usar esquemas de petición y respuesta explícitos.
-   Usar códigos HTTP semánticos y errores consistentes.
-   Definir paginación, filtros, ordenamiento y formato de fechas de
    forma uniforme.
-   No exponer campos internos ni propiedades ORM sin filtrado.
-   Verificar permisos en todas las rutas de lectura y escritura.
-   Añadir pruebas de contrato para los flujos críticos.
-   El frontend debe consumir los contratos públicos, no acceder
    directamente a la base de datos ni replicar sus reglas.

### 12.2 Persistencia y transacciones

-   Usar PostgreSQL como fuente de verdad.
-   Definir claves foráneas, restricciones, índices y reglas `CHECK`
    cuando correspondan.
-   Añadir restricciones únicas solo después de validar la semántica
    real de los datos históricos.
-   Usar transacciones para operaciones que modifican caja, ubicación,
    préstamos, movimientos, importaciones o auditoría.
-   Controlar concurrencia en asignación de número de caja y posición
    física.
-   No depender de Redis para mantener la integridad de negocio.
-   No ejecutar DDL manual sin una migración Alembic equivalente.
-   Evitar migraciones destructivas; cuando haya que cambiar datos,
    diseñar migraciones revisables, respaldos y estrategia de reversión.
-   Probar migraciones desde una base vacía y desde el esquema anterior
    representativo.

### 12.3 Alembic: reglas obligatorias

-   Toda modificación del esquema se realiza mediante migraciones
    versionadas.
-   Revisar manualmente el contenido de cada migración autogenerada.
-   No asumir que `--autogenerate` detecta todos los cambios semánticos,
    restricciones o renombres.
-   No editar migraciones ya aplicadas en ambientes compartidos; crear
    una nueva migración correctiva.
-   Documentar cualquier migración de datos.
-   Mantener consistencia entre modelos SQLAlchemy y esquema de base de
    datos.
-   Probar `upgrade` y, cuando sea viable, `downgrade` en una base de
    pruebas.
-   No borrar información histórica para hacer pasar una migración.
-   Verificar el estado de Alembic antes de desplegar.

### 12.4 Redis y tareas de fondo

Redis puede apoyar tareas costosas o diferidas, como OCR, importaciones
y exportaciones grandes. Definir un sistema de ejecución de tareas que
sea observable, idempotente y recuperable.

-   Las tareas deben tener estado, progreso cuando sea posible,
    resultado y error controlado.
-   Evitar duplicar efectos si una tarea se reintenta.
-   Aplicar límites de concurrencia, tamaño y tiempo.
-   No colocar documentos judiciales completos en claves de Redis si no
    es necesario.
-   Configurar expiración para datos temporales y proteger Redis en la
    red.
-   Si una tarea falla, permitir reintento seguro y conservar
    diagnóstico útil.
-   La base de datos mantiene el estado durable de negocio.

------------------------------------------------------------------------

## 13. Arquitectura de frontend

Estructura sugerida:

``` text
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── src/
│   ├── app/
│   │   ├── router/
│   │   ├── providers/
│   │   └── layouts/
│   ├── assets/
│   ├── components/
│   │   ├── atoms/
│   │   ├── molecules/
│   │   ├── organisms/
│   │   └── templates/
│   ├── features/
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── users/
│   │   ├── courts/
│   │   ├── locations/
│   │   ├── boxes/
│   │   ├── cases/
│   │   ├── administrative-documents/
│   │   ├── search/
│   │   ├── imports/
│   │   ├── loans/
│   │   ├── movements/
│   │   ├── inventory/
│   │   ├── audit/
│   │   └── reports/
│   ├── services/
│   │   ├── api-client.ts
│   │   └── generated-or-manual-contracts/
│   ├── hooks/
│   ├── utils/
│   ├── styles/
│   └── main.tsx
└── tests/
```

### 13.1 Diseño y experiencia de usuario

-   Panel administrativo moderno, claro y usable.
-   Tema claro y oscuro.
-   Sidebar adaptable a pantallas pequeñas.
-   Responsive en escritorio, tableta y móvil.
-   Navegación y textos en español.
-   Estados de carga, vacío, error, permiso insuficiente y éxito.
-   Formularios con validación, mensajes útiles y confirmación para
    acciones destructivas/sensibles.
-   Tablas con filtros, paginación y ordenamiento accesibles.
-   Etiquetas visuales para estados de caja, ubicación, préstamo e
    importación.
-   Evitar que el color sea el único medio para comunicar estados.
-   Soporte de teclado y etiquetas accesibles.
-   No perder el trabajo del usuario al producirse un error evitable.
-   Mostrar claramente cuándo un dato procede de OCR y requiere
    revisión.

### 13.2 Diseño atómico

Usar átomos para controles simples, moléculas para agrupaciones,
organismos para componentes funcionales y plantillas para estructura de
página. No convertir cada `div` en un componente ni crear una jerarquía
excesiva. Los componentes compartidos deben ser coherentes, accesibles y
documentados.

### 13.3 Estado y comunicación con API

-   Mantener la lógica de negocio autoritativa en backend.
-   Centralizar cliente HTTP, autenticación, manejo de errores y tipos.
-   No repetir llamadas API en múltiples componentes sin necesidad.
-   Cancelar o ignorar respuestas obsoletas en búsquedas cambiantes.
-   No guardar tokens sensibles en lugares inseguros.
-   Respetar permisos que indique el servidor, pero no depender de
    ocultar botones como mecanismo de seguridad.
-   Añadir pruebas de componentes, formularios y flujos de usuario.
-   Usar carga diferida para módulos pesados, especialmente
    visualización 3D y documentos.

------------------------------------------------------------------------

## 14. Fases y orden de trabajo

La guía maestra de fases
(`guia_fases_sistema_gestion_documental_judicial.md`) desarrolla
objetivos, dependencias, requisitos, impacto, entregables, riesgos y
criterios de aceptación. Debe mantenerse alineada con estas
instrucciones. La secuencia acordada es **backend antes de frontend**.

### Backend: fases B0--B15

-   **B0 --- Preparación del proyecto:** repositorio, entornos,
    convenciones, configuración, `.env.example`, herramientas de calidad
    y estructura inicial.
-   **B1 --- Dominio y reglas de negocio:** catálogo de entidades,
    estados, transiciones, invariantes y preguntas pendientes.
-   **B2 --- Base de datos y migraciones:** SQLAlchemy, PostgreSQL,
    Alembic, claves, restricciones e índices iniciales.
-   **B3 --- Configuración, logging y errores:** settings, validación de
    entorno, logs estructurados y respuestas de error.
-   **B4 --- Autenticación, usuarios y permisos:** cuentas, roles,
    sesiones/tokens y autorización.
-   **B5 --- Catálogos judiciales y configuración física:** tribunales,
    áreas, anaqueles, bandejas, posiciones y capacidades.
-   **B6 --- Cajas y registros documentales:** numeración, expedientes,
    imputados, documentos administrativos y reglas de exclusión.
-   **B7 --- Ubicaciones y movimientos:** asignación de posición,
    traslados, historial y concurrencia.
-   **B8 --- Búsqueda global:** filtros combinados, últimos cinco
    dígitos del NUC, índices, paginación y permisos.
-   **B9 --- Archivos y digitalización:** almacenamiento privado,
    metadatos, descarga autorizada y conservación de originales.
-   **B10 --- OCR e importación revisable:** extracción, validación,
    tabla previa, corrección, aprobación y aplicación transaccional.
-   **B11 --- Préstamos, devoluciones y QR:** ciclo de préstamo, alertas
    y etiquetas seguras.
-   **B12 --- Conciliación de inventario:** sesiones, discrepancias,
    resolución y cierre.
-   **B13 --- Auditoría completa:** valores anteriores/nuevos, actores,
    motivos, procedencia y consultas autorizadas.
-   **B14 --- Reportes y exportaciones:** Excel, CSV, PDF y filtros.
-   **B15 --- Pruebas integrales, endurecimiento, documentación y
    despliegue del backend:** pruebas de regresión, rendimiento,
    seguridad, recuperación y operación.

### Frontend: fases F0--F10

-   **F0 --- Preparación y sistema visual:** React/TS/Vite/Tailwind,
    rutas, tema, layouts y cliente API.
-   **F1 --- Autenticación y shell administrativo:** login, sesión,
    sidebar y navegación por permisos.
-   **F2 --- Dashboard:** métricas útiles y alertas operativas.
-   **F3 --- Catálogos y configuración física:** tribunales, áreas,
    anaqueles y capacidades.
-   **F4 --- Cajas y registros:** expedientes, imputados, documentos
    administrativos y formularios validados.
-   **F5 --- Búsqueda global y detalle:** filtros, resultados y
    navegación a ubicación.
-   **F6 --- Plano 2D y modelo 3D:** selección de caja/posición,
    ocupación y visualización de resultados.
-   **F7 --- Importaciones, digitalización y OCR:** carga, progreso,
    revisión de tabla, errores y aprobación.
-   **F8 --- Préstamos, movimientos, QR y conciliación:** flujos
    operativos completos.
-   **F9 --- Auditoría, reportes y exportaciones:** filtros, vista
    previa y descargas autorizadas.
-   **F10 --- Accesibilidad, responsive, pruebas E2E y preparación de
    producción:** validación integral.

No avanzar a una fase si las dependencias funcionales o migraciones
críticas de la fase anterior no están aprobadas. Se pueden realizar
tareas de investigación en paralelo, pero no desarrollar frontend
definitivo contra endpoints inventados.

------------------------------------------------------------------------

## 15. Pruebas y calidad

Cada módulo nuevo debe incluir pruebas apropiadas antes de integrarse.

### 15.1 Backend

-   Pruebas unitarias de reglas de dominio.
-   Pruebas de integración con PostgreSQL real o entorno de prueba
    equivalente.
-   Pruebas de endpoints, autenticación y permisos.
-   Pruebas de migraciones.
-   Pruebas de concurrencia para numeración y posiciones.
-   Pruebas de importación idempotente y fallos parciales.
-   Pruebas de préstamos, devoluciones y transiciones inválidas.
-   Pruebas de auditoría y preservación del historial.
-   Pruebas de autorización de archivos.
-   Pruebas de exportación segura.
-   Pruebas de rendimiento de búsquedas con volumen representativo.

### 15.2 Frontend

-   Pruebas unitarias de componentes y utilidades.
-   Pruebas de formularios y validaciones.
-   Pruebas de flujos críticos.
-   Pruebas de permisos visibles y manejo de `403`.
-   Pruebas de estados de carga, vacío y error.
-   Pruebas responsive y accesibilidad.
-   Pruebas de búsqueda y navegación desde resultados a la ubicación.
-   Pruebas de revisión/aprobación de importaciones.
-   Pruebas de recuperación ante errores de red.

### 15.3 Datos y casos de prueba obligatorios

Incluir: - NUC `00001`. - NUC `2022-102-00001`. - NUC con guiones, ceros
iniciales y formato histórico no reconocido. - Sentencias con el patrón
`000-0000-SSSS-0000`. - Códigos judiciales repetidos 589 y 107. -
Tribunal inactivo con registros históricos. - Caja sin ubicación. - Caja
con ubicación pendiente de confirmar. - Intento de ocupar dos veces una
posición. - Intento de mezclar expedientes y documentos
administrativos. - Anaqueles con capacidades diferentes. - Imputados
múltiples por expediente. - Documento administrativo con año conocido y
mes desconocido. - PDF digital, escaneado, DOCX y documento
manuscrito. - OCR con baja confianza, campos faltantes y duplicados. -
Importación reintentada. - Préstamo vencido, devolución válida e intento
de devolución inválida. - Traslado hacia posición ocupada. - Usuario sin
permiso que intenta consultar o descargar un documento. - Exportación
con valores que podrían interpretarse como fórmulas. - Eliminación
lógica con conservación de auditoría.

### 15.4 Calidad mínima antes de fusionar

-   Formateador y linter pasan.
-   Tipos/validaciones pasan.
-   Pruebas relevantes pasan.
-   No quedan secretos ni archivos de datos reales en el diff.
-   Migraciones revisadas y probadas.
-   Documentación actualizada.
-   Cambios de API documentados.
-   Ningún error se oculta mediante `except` genérico o conversión
    silenciosa.
-   La implementación tiene un criterio de aceptación verificable.

------------------------------------------------------------------------

## 16. Comandos y flujo de trabajo

Los comandos exactos pueden variar con los scripts configurados en
`pyproject.toml` y `package.json`; mantenerlos actualizados en el
README. Como base para el backend con `uv` y Alembic:

``` bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
uv run alembic current
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "descripcion_del_cambio"
```

No ejecutar una migración en producción sin revisar el diff, respaldo,
plan de despliegue y validación de reversión/recuperación. La generación
automática no sustituye la revisión manual.

Para el frontend, una vez definidos los scripts del proyecto:

``` bash
cd frontend
pnpm install
pnpm dev
pnpm build
pnpm test
pnpm lint
```

Si un comando no existe, definirlo en el manifiesto correspondiente o
documentar el equivalente real; no afirmar que pasó una tarea que no se
ejecutó. No introducir scripts ficticios.

### 16.1 Variables de entorno

-   Mantener `.env.example` con nombres y valores ficticios seguros.
-   Ignorar `.env` y archivos de secretos en Git.
-   Validar al inicio las variables requeridas y mostrar errores sin
    revelar secretos.
-   Separar configuración de desarrollo, pruebas y producción.
-   No codificar contraseñas de PostgreSQL/Redis, claves de firma ni
    credenciales iniciales.
-   Documentar cómo crear el primer administrador de manera segura.

------------------------------------------------------------------------

## 17. Documentación obligatoria

Mantener documentación en español y alineada con el código. Como mínimo:

``` text
docs/
├── arquitectura.md
├── reglas-de-negocio.md
├── modelo-de-datos.md
├── api.md
├── seguridad.md
├── instalacion-desarrollo.md
├── despliegue-produccion.md
├── operaciones-y-mantenimiento.md
├── copias-de-seguridad-y-restauracion.md
├── importacion-y-ocr.md
├── inventario-fisico.md
├── roles-y-permisos.md
├── pruebas.md
├── decisiones/
│   └── ADR-*.md
└── pendientes-de-validacion.md
```

El README raíz debe explicar el propósito, arquitectura, prerequisitos,
estructura, configuración, comandos de desarrollo, migraciones, pruebas,
despliegue y enlaces a documentos. Mantener una lista explícita de
preguntas pendientes, especialmente sobre formatos históricos y reglas
archivísticas. Cuando se tome una decisión arquitectónica relevante,
registrar una ADR con contexto, opciones, decisión, consecuencias y
fecha.

------------------------------------------------------------------------

## 18. Gestión de incertidumbres y decisiones pendientes

No convertir los puntos siguientes en reglas rígidas sin revisión
humana:

1.  **Códigos de tribunales repetidos:** código 589 para dos nombres y
    código 107 para dos tribunales. Confirmar si son colisiones válidas,
    códigos reutilizados históricamente o datos que deben corregirse.
2.  **Formatos NUC:** validar patrones por tribunal y época; admitir
    formatos históricos y preservar valores originales.
3.  **Sentencias/resoluciones:** precisar la semántica del patrón
    `000-0000-SSSS-0000`, y el uso de SADM, SPEN, RPE y otros
    identificadores.
4.  **Inmutabilidad de caja:** confirmar las condiciones exactas bajo
    las cuales tribunal, año y tipo quedan fijados; diseñar un flujo de
    corrección auditable para errores históricos.
5.  **Préstamos:** definir si se presta una caja completa, un expediente
    individual o ambos; establecer aprobaciones, vencimientos y
    notificaciones.
6.  **Almacenamiento de originales:** elegir el sistema de archivos o
    almacenamiento privado, límites, política de retención y estrategia
    de respaldo.
7.  **OCR manuscrito:** establecer expectativas de precisión, motor y
    proceso de revisión según muestras reales.
8.  **Modelo físico:** confirmar si hay datos geométricos, dimensiones y
    orientación suficientes para representar fielmente el espacio en
    2D/3D.
9.  **Fechas parciales:** establecer reglas uniformes para fechas con
    solo año o año/mes.
10. **Eliminación/retención:** definir política institucional de
    conservación, baja lógica, acceso y eventual purga autorizada.
11. **Alertas:** definir canales, periodicidad, destinatarios y
    condiciones de vencimiento para préstamos y conciliaciones.
12. **Identidad de usuarios:** definir alta, recuperación de contraseña,
    cierre de sesión, caducidad y posibles requisitos de segundo factor.
13. **Política de numeración:** confirmar si los números se asignan al
    crear una caja, al aprobarla o en otro momento, y cómo tratar cajas
    anuladas.

Si falta una decisión necesaria, documentarla en
`docs/pendientes-de-validacion.md`, proponer alternativas con
ventajas/riesgos y evitar bloquear decisiones reversibles que no
comprometan integridad ni seguridad.

------------------------------------------------------------------------

## 19. Reglas de Git y colaboración

-   Realizar cambios pequeños y enfocados.
-   Usar mensajes de commit descriptivos, preferiblemente en español o
    en inglés consistente.
-   No mezclar refactorizaciones grandes con cambios funcionales no
    relacionados.
-   No incluir `.env`, claves, documentos judiciales reales, volcados de
    base de datos ni archivos privados.
-   No reformatear archivos completos sin necesidad.
-   Revisar el diff antes de finalizar.
-   Si se cambia un contrato de API, actualizar pruebas, tipos del
    frontend y documentación.
-   No descartar trabajo ajeno ni sobrescribir cambios sin entenderlos.
-   Ante una migración o operación destructiva, detenerse y solicitar
    confirmación/plan de respaldo.
-   Si no se puede ejecutar una prueba, decirlo claramente y describir
    la limitación; no inventar resultados.
-   No declarar completada una fase hasta cumplir sus criterios de
    aceptación.

------------------------------------------------------------------------

## 20. Definition of Done

Una funcionalidad solo se considera terminada cuando corresponda todo lo
siguiente:

-   [ ] Requisito y regla de negocio documentados.
-   [ ] Modelo de datos y migración Alembic revisados, cuando aplique.
-   [ ] Validación en backend implementada.
-   [ ] Permisos verificados en el servidor.
-   [ ] Manejo de errores y estados límite.
-   [ ] Auditoría añadida para acciones sensibles.
-   [ ] Pruebas unitarias/integración/API pertinentes.
-   [ ] Interfaz accesible y responsive, cuando aplique.
-   [ ] Contrato de API documentado.
-   [ ] Logs no exponen secretos ni datos sensibles innecesarios.
-   [ ] Copias/restauración consideradas si afecta datos o archivos.
-   [ ] README/documentación actualizados.
-   [ ] Linter, formato, tipos y pruebas ejecutados o limitaciones
    declaradas.
-   [ ] Diff revisado; no hay secretos ni datos reales.
-   [ ] Criterios de aceptación demostrados.

------------------------------------------------------------------------

## 21. Instrucciones finales para agentes

Antes de cada tarea:

1.  Lee este archivo y la fase correspondiente de
    `guia_fases_sistema_gestion_documental_judicial.md`.
2.  Inspecciona la estructura real del repositorio y el estado de Git
    antes de asumir que algo existe.
3.  Identifica dependencias, modelos, endpoints, migraciones y pruebas
    afectadas.
4.  Verifica si la tarea depende de una regla no confirmada.
5.  Explica brevemente el plan, realiza cambios concretos y ejecuta las
    comprobaciones disponibles.
6.  Resume archivos modificados, decisiones tomadas, comandos ejecutados
    y resultados.
7.  Declara claramente las pruebas no ejecutadas, riesgos restantes y
    decisiones que requieren intervención humana.

**Nunca:** inventes datos históricos, descartes trazabilidad, omitas
permisos, cambies el esquema sin Alembic, permitas que OCR escriba
registros definitivos sin aprobación, expongas archivos judiciales
públicamente, borres auditoría, asumas que todas las cajas tienen
ubicación confirmada o desarrolles el frontend definitivo contra una API
ficticia.

**Prioridad de decisión:** seguridad y confidencialidad → integridad y
trazabilidad de datos → reglas archivísticas confirmadas →
compatibilidad con datos históricos → mantenibilidad → experiencia
visual y optimización.
