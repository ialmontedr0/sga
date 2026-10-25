# ADR-0002 --- Arquitectura modular por dominio

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
El sistema abarca autenticación, catálogos, cajas, expedientes,
búsqueda, archivos, OCR, préstamos, inventario y reportes. Una capa
única acoplaría reglas y dificultaría las pruebas.

## Decisión
Organizar por módulos de dominio con capas internas
`models/schemas/repository/service/router`. El dominio no importa
FastAPI. La API no contiene reglas de negocio. Las dependencias apuntan
hacia `core` y `db`, nunca desde `core` hacia módulos.

## Alternativas
- Capas globales (`models/`, `services/`, `repositories/`): más simple al
  inicio, pero propensa a archivos gigantes y acoplamiento.
- Microservicios: sobredimensionado para 10 usuarios y un solo equipo.

## Consecuencias
- Módulos probables y reemplazables.
- Requiere disciplina para no duplicar utilidades.
- Los módulos se crean solo cuando existe funcionalidad real.

## Referencias
`docs/arquitectura.md`, `AGENTS.md` sección 12.
