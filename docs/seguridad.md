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

- Hash Argon2id con `pwdlib.PasswordHash.recommended()`.
- Longitud mínima configurable (`SGA_AUTH_PASSWORD_MIN_LENGTH`, 12 por defecto).
- Nunca se registran contraseñas, hashes ni tokens en logs/auditoría.

## Autorización

Permisos verificados en cada endpoint. Ocultar un botón no es control de acceso. Roles iniciales: administrador, supervisor, archivista,
digitalizador, consulta.

## Configuración

Prefijo SGA_, validación al inicio, CORS explícito, TrustedHost,
documentación deshabilitada en producción, cookies seguras y logs JSON.

## Archivos

Almacenamiento privado, nombre opaco, hash SHA-256, validación de MIME
real, límites de tamaño, descarga autorizada, sin enlaces públicos.

## Errores y logs

Sobre uniforme, sin trazas en producción, redacción de secretos, `request_id` para correlación.

## Dependencias

uv.lock versionado, CI, revisión de licencias y mantenimiento, gitleaks.

## Producción

HTTPS, proxy inverso, firewall, Redis autenticado y no expuesto, backups cifrados, restauración probada, cuentas temporales con cambio obligatorio, rate limiting y monitoreo.

- `SGA_AUTH_SESSION_COOKIE_SECURE=true`.
- `SGA_AUTH_CSRF_COOKIE_SECURE=true` y `SGA_AUTH_CSRF_ENABLED=true`.
- HTTPS obligatorio; no exponer la API por HTTP.
- CORS restringido a orígenes conocidos.
- Secretos en variables de entorno o gestor de secretos, nunca en Git.
- Revisar y rotar `SGA_SECRET_KEY` según política institucional.
- Restringir el acceso a PostgreSQL y Redis por red.
- Ejecutar el seed RBAC en cada despliegue y verificar el catálogo.
- Probar restauración de copias y plan de revocación de sesiones ante incidentes.

## Incidentes

1. Revocar sesiones del usuario afectado (`POST /users/{id}/sessions/{sid}/revoke` o
   `logout-all`).
2. Resetear contraseña (`POST /users/{id}/reset-password`).
3. Revisar `security_events` y `login_attempts`.
4. Si hay sospecha de escalado, revisar `user_roles` y `role_permissions`.
5. Documentar el incidente y las acciones en `docs/decisiones/`.

### Sesiones

- Token opaco de alta entropía; en BD solo se almacena `sha256(token)`.
- Expiración por inactividad (`SGA_AUTH_SESSION_IDLE_MINUTES`) y absoluta (`SGA_AUTH_SESSION_ABSOLUTE_HOURS`).
- Revocación en logout, logout-all, cambio de contraseña, reset por administrador y   revocación individual.
- Cookies `HttpOnly`, `Secure` en producción y `SameSite` configurable.

### CSRF

- Double-submit cookie + header `X-CSRF-Token`.
- Validación en todos los métodos no idempotentes, incluido el login.
- El token se vincula a la sesión mediante `auth_sessions.csrf_token_hash`.
- Comparación en tiempo constante.
- `GET /auth/csrf` es la única ruta exenta (método seguro).

### Fuerza bruta

- Intentos fallidos en `login_attempts` y `users.failed_login_count`.
- Bloqueo temporal tras `SGA_AUTH_LOGIN_MAX_ATTEMPTS` en la ventana configurada.
- Mensaje genérico «Credenciales inválidas»: no revelar si el usuario existe.

### Auditoría

- `security_events` registra login correcto/fallido, logout, revocaciones, cambios de contraseña, altas/bajas de usuarios y cambios de roles/permisos.
- Nunca se guardan secretos, tokens, hashes de sesión ni contraseñas.
- El detalle se limita a identificadores y códigos necesarios.
