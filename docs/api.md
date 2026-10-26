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
Pendiente de implementación en B4: sesiones opacas con cookie
`HttpOnly`, CSRF para escrituras y permisos verificados en servidor.
Los endpoints de salud no requieren autenticación.

## Versionado
Los cambios incompatibles crean una nueva versión de API. No se rompen
contratos existentes sin migración, aviso y pruebas.
