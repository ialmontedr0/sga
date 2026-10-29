# API

## Base

`/api/v1`

## Formato de error

```json
{
  "error": {
    "code": "not_found",
    "message": "La caja solicitada no existe.",
    "details": null,
    "request_id": "5f0f0e8c9a4b4f0e8f0a9b8c7d6e5f4a"
  }
}
```

## Cabeceras

- `X-Request-ID`: se conserva si es válido; si no, se genera uno nuevo.
- La respuesta siempre incluye `X-Request-ID`.
- CORS solo permite los orígenes configurados en `SGA_CORS_ORIGINS`.
- Los hosts no permitidos se rechazan con `400 bad_request` según
  `SGA_TRUSTED_HOSTS`, conservando CORS y `X-Request-ID`.

## Límites de petición

El cuerpo declarado por `Content-Length` no puede superar
`SGA_MAX_REQUEST_BODY_BYTES` (1 MiB por defecto, entre 1 KiB y 16 MiB).
Un cuerpo mayor devuelve `413` con el código `payload_too_large`.

## Códigos de error

`validation_error`, `bad_request`, `unauthorized`, `forbidden`,
`not_found`, `method_not_allowed`, `conflict`, `payload_too_large`,
`rate_limited`, `service_unavailable` e `internal_error`. Los `500` no
exponen trazas ni detalles internos.

## Salud

### GET `/api/v1/health/live`

No consulta dependencias. Respuesta 200:

```json
{
  "status": "ok",
  "service": "SGA - Sistema de Gestion Documental Judicial",
  "version": "0.1.0",
  "environment": "development"
}
```

### GET `/api/v1/health/ready`

Consulta PostgreSQL y Redis con timeout. Respuesta 200 si ambos están
`ok`; 503 si alguno falla. No revela DSN ni mensajes internos.

```json
{
  "status": "ok",
  "version": "0.1.0",
  "components": {
    "database": {"status": "ok", "latency_ms": 1.23},
    "redis": {"status": "ok", "latency_ms": 0.45}
  }
}
```

## Documentación interactiva

- `/docs` (Swagger UI) y `/openapi.json`, solo si `SGA_DOCS_ENABLED=true`.
- En producción se deshabilitan por defecto.

## Paginación

Parámetros `page` (desde 1) y `page_size` (1-100, por defecto 25).
La respuesta incluye `items`, `total`, `page`, `page_size`, `pages`,
`has_next` y `has_previous`. El ordenamiento se restringe a campos
permitidos por endpoint.

## Autenticación

Base: `http://127.0.0.1:8000/api/v1` (desarrollo).
Las respuestas de error usan el sobre `{"error": {"code", "message", "details", "request_id"}}`.

## Versionado

Los cambios incompatibles crean una nueva versión de API. No se rompen
contratos existentes sin migración, aviso y pruebas.

### Cookies

| Cookie | HttpOnly | Uso |
|---|---|---|
| `sga_session` | Sí | Token opaco de sesión (solo se guarda su SHA-256 en BD) |
| `sga_csrf` | No | Token CSRF double-submit |

En producción ambas cookies usan `Secure=true`; `SameSite` es configurable (`lax` por defecto).

### Flujo

1. `GET /auth/csrf` → devuelve `{"csrf_token": "..."}` y fija la cookie `sga_csrf`.
2. `POST /auth/login` con `{"username","password"}` y header `X-CSRF-Token`.
3. El servidor fija `sga_session` y vincula el hash del token CSRF a la sesión.
4. En todo `POST/PUT/PATCH/DELETE` enviar `X-CSRF-Token` con el valor de `sga_csrf`.
5. `POST /auth/logout` revoca la sesión actual; `POST /auth/logout-all` revoca todas.

### Endpoints

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| GET | `/auth/csrf` | — | Emite token CSRF |
| POST | `/auth/login` | — | Inicia sesión (requiere CSRF) |
| POST | `/auth/logout` | sesión | Cierra la sesión actual |
| POST | `/auth/logout-all` | sesión | Cierra todas las sesiones |
| GET | `/auth/me` | sesión | Usuario actual, roles y permisos |
| POST | `/auth/change-password` | sesión | Cambia contraseña y revoca otras sesiones |
| GET | `/users/` | `users.read` | Lista usuarios |
| POST | `/users/` | `users.create` | Crea usuario |
| GET | `/users/{id}` | `users.read` | Detalle con roles y permisos |
| PATCH | `/users/{id}` | `users.update` | Actualiza datos/estado |
| POST | `/users/{id}/lock` | `users.lock` | Bloquea cuenta |
| POST | `/users/{id}/unlock` | `users.lock` | Desbloquea cuenta |
| POST | `/users/{id}/roles` | `roles.manage` | Reemplaza roles |
| POST | `/users/{id}/reset-password` | `users.reset_password` | Contraseña temporal + revocación |
| GET | `/users/{id}/sessions` | `sessions.read` | Sesiones activas |
| POST | `/users/{id}/sessions/{sid}/revoke` | `sessions.manage` | Revoca una sesión |
| GET | `/roles/` | `roles.read` | Roles con sus permisos |
| POST | `/roles/` | `roles.manage` | Crea rol |
| PATCH | `/roles/{id}` | `roles.manage` | Edita rol |
| POST | `/roles/{id}/permissions` | `roles.manage` | Reemplaza permisos del rol |
| GET | `/permissions/` | `permissions.read` | Catálogo de permisos |
| POST | `/permissions/` | `permissions.manage` | Crea permiso |

### Ejemplos

```bash
# Obtener CSRF
curl -c cookies.txt http://127.0.0.1:8000/api/v1/auth/csrf

# Login (usar el valor devuelto por /auth/csrf)
curl -b cookies.txt -c cookies.txt \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <TOKEN>" \
  -d '{"username":"admin","password":"..."}' \
  http://127.0.0.1:8000/api/v1/auth/login

# Consultar usuario actual
curl -b cookies.txt http://127.0.0.1:8000/api/v1/auth/me
```

```javascript
async function api(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };

  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = document.cookie
      .split("; ")
      .find((row) => row.startsWith("sga_csrf="))
      ?.split("=")[1];
    if (!csrf) throw new Error("Falta el token CSRF");
    headers["X-CSRF-Token"] = decodeURIComponent(csrf);
  }

  const response = await fetch(`/api/v1${path}`, {
    ...options,
    method,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.error?.message || `HTTP ${response.status}`);
  }
  return response.status === 204 ? null : response.json();
}
```

### Códigos relevantes

| Estado | Significado |
|---|---|
| 401 | No autenticado, sesión expirada o cuenta bloqueada |
| 403 | Permisos insuficientes o CSRF ausente/inválido |
| 409 | Conflicto de unicidad (usuario, email, rol o permiso) |
| 422 | Datos inválidos |

`error.details.reason == "csrf"` indica problema de CSRF, no de permisos.
