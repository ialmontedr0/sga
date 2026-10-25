# ADR-0007 --- Logs estructurados y errores uniformes

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
Se necesita diagnosticar fallos sin exponer datos judiciales ni
secretos, y correlacionar peticiones y tareas.

## Decisión
structlog con salida JSON en producción y consola legible en desarrollo.
`request_id` en cada petición, respuesta y log. Sobre de error
`error.code/message/details/request_id`. Sin trazas en producción.

## Alternativas
- Logging estándar: difícil de consultar y correlacionar.
- Errores ad hoc por endpoint: inconsistentes para el frontend.

## Consecuencias
- Consultas y alertas más simples.
- Requiere disciplina de eventos y redacción.
- El cliente recibe mensajes estables y seguros.

## Referencias
`core/logging.py`, `core/errors.py`, `core/middleware.py`.
