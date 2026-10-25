# ADR-0004 --- Sesiones opacas con cookie y CSRF

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
La aplicación será accesible por Internet y maneja información judicial.
Se requiere revocación inmediata, protección XSS/CSRF y baja complejidad
operativa.

## Decisión
Sesiones opacas en PostgreSQL. Cookie HttpOnly, Secure en producción,
SameSite=Lax. Token aleatorio de 256 bits; se guarda solo SHA-256.
Expiración por inactividad y absoluta. CSRF de doble envío para
escrituras. Contraseñas con Argon2id. Implementación en B4.

## Alternativas
- JWT en localStorage: expuesto a XSS y difícil de revocar.
- JWT en cookie: requiere rotación y listas de revocación.
- Basic Auth: sin sesión ni cierre seguro.

## Consecuencias
- Revocación inmediata y auditoría de sesiones.
- Una consulta adicional por petición autenticada (mitigable con caché).
- Requiere limpieza periódica de sesiones expiradas.

## Referencias
`core/security.py`, `AGENTS.md` sección 11.
