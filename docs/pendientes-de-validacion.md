# Pendientes de validación

Cada punto requiere decisión humana antes de convertirse en regla rígida.

| # | Tema | Pregunta | Impacto | Fase | Estado |
|---|---|---|---|---|---|
| 1 | Códigos de tribunales | ¿589 y 107 son colisiones válidas o datos a corregir? | Catálogo y unicidad | B5 | Pendiente |
| 2 | Formatos NUC | ¿Qué patrones aplican por tribunal y época? | Validación y búsqueda | B1/B8 | Pendiente |
| 3 | Sentencias | ¿Semántica de `000-0000-SSSS-0000`, SADM, SPEN, RPE? | Validación y búsqueda | B1/B8 | Pendiente |
| 4 | Inmutabilidad de caja | ¿Cuándo quedan fijos tipo, tribunal y año? | Edición y corrección | B1/B6 | Pendiente |
| 5 | Préstamos | ¿Caja completa, expediente o ambos? | Modelo y flujo | B1/B11 | Pendiente |
| 6 | Almacenamiento | ¿Volumen, retención y respaldo de originales? | B9 y operación | B9 | Pendiente |
| 7 | OCR manuscrito | ¿Motor, precisión esperada y revisión? | B10 | B10 | Pendiente |
| 8 | Modelo físico | ¿Dimensiones y orientación para 2D/3D? | F6 | F6 | Pendiente |
| 9 | Fechas parciales | ¿Representación uniforme de año/mes? | Modelo y reportes | B1 | Pendiente |
| 10 | Retención | ¿Baja lógica, conservación y purga? | Auditoría y datos | B13 | Pendiente |
| 11 | Alertas | ¿Canales, periodicidad y destinatarios? | B11/B12 | Pendiente |
| 12 | Identidad | ¿Alta, recuperación, caducidad, 2FA? | B4 | Pendiente |
| 13 | Numeración | ¿Cuándo se asigna el número y cómo se anula? | B6 | Pendiente |
| 14 | Numeración de fases | `AGENTS.md` usa B0-B15/F0-F10; la guía maestra B0-B16/F1-F11 | Trazabilidad documental | B0 | Resuelto: prevalece la guía maestra; corregir `AGENTS.md` |
| 15 | Licencia | ¿Licencia institucional o privada? | Publicación | B0 | Pendiente |

## Nota sobre la numeración de fases

La fase B0 es idéntica en ambos documentos. A partir de B1, la guía
maestra agrega una fase y desplaza los números. Este documento y el
código usarán la guía maestra. La discrepancia debe corregirse en
`AGENTS.md` mediante una tarea documental separada, sin alterar el
contenido de negocio.
