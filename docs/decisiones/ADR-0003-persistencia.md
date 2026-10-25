# ADR-0003 --- PostgreSQL, SQLAlchemy async y Alembic

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
La integridad, la concurrencia y la trazabilidad son requisitos. Se
necesitan transacciones, restricciones y migraciones revisables.

## Decisión
PostgreSQL 18 como fuente de verdad. SQLAlchemy 2.1 async con psycopg 3.
Alembic para todo cambio de esquema. Sesión por petición; el servicio
define la unidad de trabajo.

## Alternativas
- SQLAlchemy sync: válido, pero bloquea el event loop o exige hilos.
- asyncpg directo: rápido, pero pierde el ORM y la integración Alembic.
- DDL manual: prohibido por trazabilidad.

## Consecuencias
- Transacciones y restricciones sólidas.
- Mayor complejidad async en pruebas y sesiones.
- Toda migración se revisa y se prueba en base vacía y representativa.

## Referencias
`db/session.py`, `alembic/env.py`, `AGENTS.md` sección 12.2.
