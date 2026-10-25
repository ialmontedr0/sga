# ADR-0005 --- ARQ sobre Redis para tareas asíncronas

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
OCR, importaciones y exportaciones no deben bloquear HTTP ni depender de
hilos del proceso web. El entorno es Windows y Linux, con Redis ya
instalado.

## Decisión
ARQ 0.28 con Redis 5.2-6. Worker separado, tareas idempotentes,
timeout y reintentos limitados. Estado durable en PostgreSQL.

## Alternativas
- Celery: potente pero pesado y problemático en Windows.
- RQ: depende de fork.
- Taskiq Redis: exige redis-py 8, incompatible con ARQ.
- BackgroundTasks: no sobrevive reinicios.

## Consecuencias
- Worker simple y asíncrono.
- Restricción de versión de redis-py.
- Requiere monitoreo de cola y limpieza de estados.

## Referencias
`tasks/worker.py`, `pyproject.toml`.
