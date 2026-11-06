# ADR-0012: Numeración de las fases B6 y B7

- Estado: aceptada
- Fecha: 2026-11-06

## Contexto

Existe una contradicción documental entre `docs/AGENTS.md` y
`docs/phases/GUIA_DESARROLLO_FASES_SGA.md`:

- `docs/AGENTS.md` indicaba B6 como cajas y registros documentales, y B7
  como ubicaciones y movimientos.
- `docs/phases/GUIA_DESARROLLO_FASES_SGA.md` y el alcance aprobado para el
  proyecto indican B6 como inventario físico y ubicaciones, y B7 como cajas,
  expedientes e inventario administrativo.

La guía B6 mencionaba `ADR-0002` para registrar esta decisión, pero ese
número ya está ocupado por `ADR-0002-arquitectura-modular.md`.

## Decisión

1. B6 corresponde a inventario físico y ubicaciones: áreas, estantes,
   bandejas, posiciones, capacidades, movimientos e historial de ubicación.
2. B7 corresponde a cajas, expedientes, personas/partes, documentos
   administrativos y numeración asociada.
3. No se reutiliza `ADR-0002`; esta decisión se registra como `ADR-0012`.
4. No se renumeran las ADR existentes ni se renombran módulos, tablas o rutas
   solo por el número de fase.
5. `docs/AGENTS.md` debe alinearse con `GUIA_DESARROLLO_FASES_SGA.md`.

## Consecuencias

- La documentación de fases y los criterios de aceptación quedan alineados.
- Las implementaciones B6 y B7 existentes conservan sus nombres y rutas.
- Los agentes deben leer la guía maestra de fases y esta ADR antes de
  planificar trabajo de B6 o B7.
- Cualquier cambio futuro en la numeración de fases requiere una nueva ADR y
  no debe reescribir la historia documental.
