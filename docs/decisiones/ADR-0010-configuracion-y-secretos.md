# ADR-0010 --- Configuración por entorno con prefijo SGA_

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
Desarrollo, pruebas y producción difieren en credenciales, hosts y
seguridad. Los secretos no pueden estar en el código.

## Decisión
pydantic-settings con prefijo `SGA_`, `.env` local ignorado,
`.env.example` versionado, validación al inicio y reglas que rechazan
configuración insegura en producción. Secretos en variables del sistema
o gestor institucional.

## Alternativas
- Archivos YAML por entorno: riesgo de versionar secretos.
- Variables sin validación: fallos tardíos y silenciosos.

## Consecuencias
- Arranque seguro y errores claros.
- Cambios de configuración requieren reinicio.
- La documentación debe mantenerse sincronizada.

## Referencias
`core/config.py`, `backend/.env.example`.
