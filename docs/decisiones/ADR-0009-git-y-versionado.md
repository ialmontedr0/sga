# ADR-0009 --- Trunk-based y Conventional Commits

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
Se necesita historial legible, integración frecuente y trazabilidad de
fases sin sobrecarga de ramas.

## Decisión
Rama principal `main` protegida. Ramas cortas `feat/`, `fix/`, `docs/`,
`chore/`, `refactor/`, `test/`. Commits convencionales en español.
Etiquetas `v0.x.y` al cerrar hitos. Sin `--no-verify`, sin reescribir
historial compartido.

## Alternativas
- Git Flow: demasiadas ramas para un equipo pequeño.
- Commits libres: historial difícil de auditar.

## Consecuencias
- Historial claro y PR pequeños.
- Requiere disciplina de mensajes y revisión.
- Los cambios grandes se dividen.

## Referencias
`AGENTS.md` sección 19.
