# Roles y permisos

## Principios

- La autorización se verifica siempre en el servidor por permiso, no solo por rol.
- Mínimo privilegio y denegación por defecto.
- Los roles de sistema no se eliminan ni se desactivan.
- El rol `ADMINISTRADOR` conserva el catálogo completo de permisos.
- Todo cambio de roles o permisos se audita en `security_events`.

## Roles iniciales

| Código | Nombre | Uso |
|---|---|---|
| `ADMINISTRADOR` | Administrador | Control total |
| `SUPERVISOR` | Supervisor | Operación y supervisión, sin gestión de usuarios |
| `ARCHIVISTA` | Archivista | Cajas, expedientes, movimientos, préstamos |
| `DIGITALIZADOR` | Digitalizador | Carga y OCR |
| `CONSULTA` | Usuario de consulta | Solo lectura autorizada |

## Catálogo de permisos

Formato: `modulo.accion` (`^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$`).

- Usuarios: `users.read`, `users.create`, `users.update`, `users.delete`, `users.lock`,
  `users.reset_password`.
- Roles/permisos: `roles.read`, `roles.manage`, `permissions.read`, `permissions.manage`.
- Sesiones/auditoría: `sessions.read`, `sessions.manage`, `audit.read`.
- Catálogos/búsqueda: `catalog.read`, `catalog.manage`, `search.read`.
- Cajas/expedientes: `boxes.read/create/update/delete`, `cases.read/create/update`.
- Documentos/archivos: `documents.read`, `documents.manage`, `files.read`, `files.upload`,
  `files.download`.
- Operación: `imports.read/create/approve`, `ocr.review`, `loans.read/manage`,
  `movements.read/manage`, `inventory.read/manage`.
- Reportes/configuración: `reports.read`, `reports.export`, `settings.read`, `settings.manage`.

La fuente de verdad del catálogo y de la matriz es `src/judicial_archive/db/seed_rbac.py`.

## Matriz resumida

| Capacidad | ADMINISTRADOR | SUPERVISOR | ARCHIVISTA | DIGITALIZADOR | CONSULTA |
|---|:---:|:---:|:---:|:---:|:---:|
| Gestionar usuarios/roles/permisos | Sí | No | No | No | No |
| Ver usuarios, roles y sesiones | Sí | Sí | No | No | No |
| Revocar sesiones | Sí | Sí | No | No | No |
| Ver auditoría | Sí | Sí | No | No | No |
| Catálogos físicos | Sí | Gestionar | Consultar | Consultar | Consultar |
| Cajas y expedientes | Sí | Crear/editar | Crear/editar | Consultar | Consultar |
| Documentos y archivos | Sí | Gestionar | Gestionar | Consultar/subir | Consultar/descargar |
| Importaciones/OCR | Sí | Aprobar | Crear | Crear/revisar | No |
| Préstamos/movimientos/inventario | Sí | Gestionar | Gestionar | No | No |
| Reportes | Sí | Exportar | Consultar | No | Consultar |
| Configuración global | Sí | Consultar | No | No | No |

## Cómo se aplica

1. `get_current_user` valida la cookie `sga_session` y la sesión en `auth_sessions`.
2. `require_permissions("modulo.accion")` consulta `role_permissions` en cada petición.
3. Un usuario sin el permiso recibe `403` con `error.code = "forbidden"`.
4. `GET /auth/me` devuelve los roles y permisos efectivos para que el frontend muestre
   u oculte acciones; ocultar un botón no sustituye la validación del servidor.

## Administración

- Alta inicial: `uv run python scripts/create_admin.py` (interactivo, sin contraseña por defecto).
- Seed: `uv run python -m judicial_archive.db.seed_rbac` (idempotente).
- Roles/permisos por API: `GET/POST /roles/`, `POST /roles/{id}/permissions`,
  `GET/POST /permissions/`.
- El rol `ADMINISTRADOR` no se puede restringir por API.

## Cuentas iniciales

No crear usuarios por migración ni con contraseñas en el repositorio. Las cuentas se crean
con el script o por API y deben cambiar la contraseña en el primer acceso cuando corresponda.
