# Seguridad

## Principios
- Mínimo privilegio.
- Defensa en profundidad.
- Validación autoritativa en servidor.
- Secretos fuera del repositorio.
- Auditoría de acciones sensibles.
- HTTPS en producción.

## Autenticación
Sesiones opacas en PostgreSQL, cookie HttpOnly/Secure/SameSite=Lax,
hash SHA-256 del token, expiración por inactividad y absoluta, CSRF de
doble envío. Implementación en B4.

## Contraseñas
Argon2id mediante pwdlib. Longitud máxima 1024. Nunca se registran ni se
devuelven.

## Autorización
Permisos verificados en cada endpoint. Ocultar un botón no es control de
acceso. Roles iniciales: administrador, supervisor, archivista,
digitalizador, consulta.

## Configuración
Prefijo SGA_, validación al inicio, CORS explícito, TrustedHost,
documentación deshabilitada en producción, cookies seguras y logs JSON.

## Archivos
Almacenamiento privado, nombre opaco, hash SHA-256, validación de MIME
real, límites de tamaño, descarga autorizada, sin enlaces públicos.

## Errores y logs
Sobre uniforme, sin trazas en producción, redacción de secretos,
`request_id` para correlación.

## Dependencias
uv.lock versionado, CI, revisión de licencias y mantenimiento, gitleaks.

## Producción
HTTPS, proxy inverso, firewall, Redis autenticado y no expuesto, backups
cifrados, restauración probada, cuentas temporales con cambio obligatorio,
rate limiting y monitoreo.

## Incidentes
Registrar, contener, preservar evidencia, rotar secretos, notificar según
política institucional y documentar lecciones aprendidas.
