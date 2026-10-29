"""Codigos de permiso del sistema.

Formato obligatorio (CHECK en base de datos):
    ^[a-z][a-z0-9_]*([a-z][a-z0-9_]*)+$

Los permisos de modulos futuros se declaran aqui para que el seed RBAC sea estable. No implica que sus endpoints existan.

"""

# Usuarios
USERS_READ = "users.read"
USERS_CREATE = "users.create"
USERS_UPDATE = "users.update"
USERS_DELETE = "users.delete"
USERS_LOCK = "users.lock"
USERS_RESET_PASSWORD = "users.reset_password"  # noqa: S105

# Roles y permisos
ROLES_READ = "roles.read"
ROLES_MANAGE = "roles.manage"
PERMISSIONS_READ = "permissions.read"
PERMISSIONS_MANAGE = "permissions.manage"

# Sesiones y auditoria
SESSIONS_READ = "sessions.read"
SESSIONS_MANAGE = "sessions.manage"
AUDIT_READ = "audit.read"

# Catalogos y busqueda
CATALOG_READ = "catalog.read"
CATALOG_MANAGE = "catalog.manage"
SEARCH_READ = "search.read"

# Cajas y expedientes
BOXES_READ = "boxes.read"
BOXES_CREATE = "boxes.create"
BOXES_UPDATE = "boxes.update"
BOXES_DELETE = "boxes.delete"
CASES_READ = "cases.read"
CASES_CREATE = "cases.create"
CASES_UPDATE = "cases.update"

# Documentos y archivos
DOCUMENTS_READ = "documents.read"
DOCUMENTS_MANAGE = "documents.manage"
FILES_READ = "files.read"
FILES_UPLOAD = "files.upload"
FILES_DOWNLOAD = "files.download"

# Importaciones, OCR y pretamos
IMPORTS_READ = "imports.read"
IMPORTS_CREATE = "imports.create"
IMPORTS_APPROVE = "imports.approve"
OCR_REVIEW = "ocr.review"
LOANS_READ = "loans.read"
LOANS_MANAGE = "loans.manage"
MOVEMENTS_READ = "movements.read"
MOVEMENTS_MANAGE = "movements.manage"
INVENTORY_READ = "inventory.read"
INVENTORY_MANAGE = "inventory.manage"

# Reportes y configuracion
REPORTS_READ = "reports.read"
REPORTS_EXPORT = "reports.export"
SETTINGS_READ = "settings.read"
SETTINGS_MANAGE = "settings.manage"
