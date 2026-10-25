# ADR-0006 --- Almacenamiento privado local tras interfaz

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
Los originales judiciales no pueden servirse desde un directorio
público. Aún no hay proveedor S3 definido ni presupuesto confirmado.

## Decisión
Almacenamiento local privado en `backend/var/storage`, detrás de una
interfaz `StorageBackend`. Nombres opacos, SHA-256, escritura atómica y
descarga autorizada. Posible migración futura a S3/MinIO sin cambiar el
dominio.

## Alternativas
- Directorio estático: inaceptable por seguridad.
- S3 desde el inicio: dependencia y costo no confirmados.
- Base de datos como blob: degrada respaldos y rendimiento.

## Consecuencias
- Control total y bajo costo inicial.
- Responsabilidad de respaldo, cifrado y capacidad del volumen.
- La interfaz debe probarse antes de cambiar de backend.

## Referencias
`AGENTS.md` sección 6.3, fase B9.
