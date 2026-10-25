# Fase B0 --- Preparación del proyecto y decisiones técnicas

**Proyecto:** SGA --- Sistema de Gestión Documental Judicial
**Fase:** B0
**Versión de la guía:** 1.0
**Fecha:** 23/10/2026
**Estado:** Guía de implementación completa, lista para ejecutar
**Documentos rectores:** `docs/AGENTS.md` y `docs/phases/GUIA_DESARROLLO_FASES_SGA.md`

---

## 0. Cómo usar esta guía

Esta guía contiene **todo** lo necesario para ejecutar la fase B0 de principio a fin:

- decisiones técnicas y su justificación;
- estructura exacta de carpetas y archivos;
- contenido completo de cada archivo a crear;
- comandos verificables para Windows PowerShell y equivalentes para Linux/macOS;
- configuración de calidad, pruebas, seguridad y documentación;
- criterios de aceptación y checklist de cierre.

Reglas de lectura:

1. Los comandos se ejecutan desde la raíz del repositorio (`C:\Users\Tony\Documents\sga`) salvo que se indique expresamente otra carpeta.
2. Cuando se indique `cd backend`, todos los comandos posteriores de esa sección se ejecutan desde `backend/`.
3. Todos los archivos se crean con codificación **UTF-8 sin BOM** y finales de línea **LF**, salvo los scripts `.ps1`, que usan **CRLF**.
4. Los valores marcados como `CAMBIAR_...` son obligatorios y **nunca** deben quedar en Git.
5. Esta fase **no implementa funcionalidades de negocio**. Solo prepara la base técnica, la infraestructura mínima y las decisiones.

### 0.1 Aclaración sobre la numeración de fases

Existe una diferencia entre `AGENTS.md` (sección 14) y la guía maestra:

- `AGENTS.md` describe backend **B0--B15** y frontend **F0--F10**.
- `GUIA_DESARROLLO_FASES_SGA.md` describe backend **B0--B16** y frontend **F1--F11**.

Para la ejecución se adopta como autoritativa la **guía maestra**, porque contiene el detalle de actividades, entregables y criterios de aceptación. Esto no afecta a B0: la fase B0 es idéntica en ambos documentos. La divergencia empieza en las fases posteriores y debe reconciliarse documentalmente antes de B9/B10. Se registra como deuda documental en `docs/pendientes-de-validacion.md`.

---

## 1. Objetivo, alcance y límites de B0

### 1.1 Objetivo

Convertir los requisitos en una base técnica verificable antes de desarrollar funcionalidades de negocio, de modo que cualquier persona pueda:

- clonar el repositorio;
- crear el entorno desde cero;
- levantar el servicio;
- ejecutar lint, formato, tipado y pruebas;
- entender las decisiones arquitectónicas;
- continuar con B1 y B2 sin rehacer la base.

### 1.2 Incluido en B0

- Repositorio Git, ramas, convenciones de commits y versionado.
- Python 3.12 fijado y gestionado con `uv`.
- `pyproject.toml` completo, dependencias y grupos de desarrollo.
- Estructura modular inicial del backend.
- Configuración tipada por entorno y gestión de secretos.
- `.env.example` sin secretos reales.
- Logging estructurado, identificador de petición, errores uniformes y paginación.
- Preparación de SQLAlchemy 2.1 asíncrono, PostgreSQL y Alembic (sin modelos de negocio ni migraciones todavía).
- Seguridad base: utilidades de hash de contraseña y tokens; decisión de autenticación por sesiones opacas.
- Decisión y esqueleto de tareas en segundo plano con ARQ + Redis.
- Decisión y contrato de almacenamiento privado local con abstracción futura.
- API mínima de salud (`/api/v1/health/live` y `/api/v1/health/ready`).
- Configuración de Ruff, mypy, pytest, cobertura, pre-commit y CI.
- Documentación: README, arquitectura, API, instalación, pruebas, seguridad, pendientes y ADR.
- Scripts de desarrollo y verificación.

### 1.3 Fuera de B0

No se implementa en esta fase:

- modelos de dominio, tablas, migraciones ni datos semilla de negocio (B1/B2);
- autenticación funcional, login, usuarios, roles ni permisos (B4);
- catálogos de tribunales, áreas, anaqueles o cajas (B5);
- endpoints de negocio, búsqueda, OCR, importaciones, préstamos, QR, conciliación, reportes (B6--B14);
- frontend (F1--F11);
- despliegue real en producción (fase de integración).

Los esqueletos incluidos existen solo para evitar retrabajo y para que el servicio arranque con infraestructura sana.

### 1.4 Criterios de aceptación de B0

| Criterio | Evidencia verificable |
|---|---|
| Entorno reproducible desde cero | README + `uv sync --frozen` + servicio arrancando |
| Servicio arranca sin secretos incrustados | `SGA_SECRET_KEY` externa + `.env` ignorado por Git |
| Lint, formato, tipos y pruebas ejecutables | `scripts/check.ps1` y comandos documentados |
| Sin secretos en el repositorio | `.gitignore`, `.env.example`, gitleaks en pre-commit |
| Decisiones documentadas | ADR-0001 a ADR-0011 |
| Estructura modular clara | Árbol de carpetas y `docs/arquitectura.md` |
| Infraestructura mínima verificable | `/health/live` y `/health/ready` |
| Base preparada para B1/B2 | Config, DB, Alembic y convenciones listas |

---

## 2. Requisitos previos y verificación del entorno

### 2.1 Software requerido

| Herramienta | Versión mínima | Uso |
|---|---|---|
| Git | 2.40+ | Control de versiones |
| uv | 0.11+ | Python, dependencias y ejecución |
| Python | 3.12.x (gestionado por uv) | Backend |
| PostgreSQL | 16+ (probado con 18.4) | Base de datos |
| Redis | 7+ (probado con 7.4.2) | Cola, caché y coordinación |
| PowerShell | 5.1+ o PowerShell 7+ | Scripts en Windows |
| Node.js | 22+ (solo futuro frontend) | No se usa en B0 |

No se requiere Docker. PostgreSQL y Redis ya están instalados en el entorno destino. Docker solo aparece, opcionalmente, en CI.

### 2.2 Verificación del entorno en Windows

Ejecutar desde la raíz del repositorio:

```powershell
git --version
uv --version
psql --version
redis-cli ping
node --version
```

Resultado esperado (las versiones pueden ser superiores):

```text
git version 2.49.0.windows.1
uv 0.11.21
psql (PostgreSQL) 18.4
PONG
v22.14.0
```

Si `redis-cli` no está en el `PATH`, localizarlo con:

```powershell
Get-Command redis-cli -ErrorAction SilentlyContinue
Get-Service | Where-Object { $_.Name -match 'redis' }
```

Si Redis no responde, iniciar el servicio correspondiente o ejecutar el binario instalado. No continuar hasta obtener `PONG`.

### 2.3 Verificación de PostgreSQL

```powershell
psql -U postgres -h localhost -c "SELECT version();"
```

Si la autenticación falla, revisar `pg_hba.conf` o usar el usuario administrador configurado durante la instalación. No se deben usar credenciales de producción en desarrollo.

### 2.4 Creación de base de datos y usuario de desarrollo

Se necesitan dos bases: una de desarrollo y una de pruebas. Ejecutar como administrador de PostgreSQL:

```powershell
psql -U postgres -h localhost
```

Dentro de `psql`:

```sql
CREATE ROLE sga_dev LOGIN PASSWORD 'CAMBIAR_CONTRASENA_DEV';
CREATE ROLE sga_test LOGIN PASSWORD 'CAMBIAR_CONTRASENA_TEST';
CREATE DATABASE sga_dev
    OWNER sga_dev
    ENCODING 'UTF8'
    TEMPLATE template0;
CREATE DATABASE sga_test
    OWNER sga_test
    ENCODING 'UTF8'
    TEMPLATE template0;
\q
```

Alternativa no interactiva en PowerShell:

```powershell
psql -U postgres -h localhost -c "CREATE ROLE sga_dev LOGIN PASSWORD 'CAMBIAR_CONTRASENA_DEV';"
psql -U postgres -h localhost -c "CREATE ROLE sga_test LOGIN PASSWORD 'CAMBIAR_CONTRASENA_TEST';"
psql -U postgres -h localhost -c "CREATE DATABASE sga_dev OWNER sga_dev ENCODING 'UTF8' TEMPLATE template0;"
psql -U postgres -h localhost -c "CREATE DATABASE sga_test OWNER sga_test ENCODING 'UTF8' TEMPLATE template0;"
```

Verificación:

```powershell
psql -U sga_dev -h localhost -d sga_dev -c "SELECT current_database(), current_user;"
psql -U sga_test -h localhost -d sga_test -c "SELECT current_database(), current_user;"
```

Notas:

- Si la contraseña contiene caracteres especiales (`@`, `:`, `/`, `#`, `%`), deben codificarse en la URL de conexión. Para evitar problemas, usar una contraseña alfanumérica larga.
- No reutilizar la contraseña de producción.
- La base `sga_test` se usará en pruebas de integración de B2 en adelante.
- `sga_test` no debe tener acceso a `sga_dev` ni a datos reales.
- Para ejecutar integración en local, definir `TEST_DATABASE_URL` y `TEST_REDIS_URL` con credenciales reales de prueba; los valores por defecto de las pruebas son solo marcadores para CI. No usar el prefijo `SGA_` para estas variables, porque pydantic-settings las interpretaría como configuración de la aplicación y `extra="forbid"` las rechazaría.

### 2.5 Verificación de Redis

```powershell
redis-cli ping
redis-cli INFO server
```

Resultado esperado: `PONG` y datos del servidor.

En desarrollo local se puede usar la base `0`; las pruebas usan la base `15` para no contaminar datos de desarrollo. En producción se debe configurar autenticación y aislamiento de red.

### 2.6 Variables que deben quedar claras antes de empezar

| Variable | Valor provisional |
|---|---|
| Sistema operativo de desarrollo | Windows 10/11 |
| Sistema operativo de producción | Linux (Ubuntu LTS) --- pendiente de confirmación institucional |
| Proxy inverso | Nginx --- pendiente de confirmación |
| Servicio de aplicación | systemd --- pendiente de confirmación |
| Almacenamiento privado | Sistema de archivos local con abstracción --- pendiente de confirmación |
| Proveedor de OCR externo | No autorizado por defecto; se decide en B11 |
| Docker | No es requisito del proyecto |

---

## 3. Resumen de decisiones técnicas

| Área | Decisión | ADR |
|---|---|---|
| Lenguaje y dependencias | Python 3.12 + `uv` + layout `src/` | ADR-0001 |
| Arquitectura | Monolito modular por dominio y capas | ADR-0002 |
| Persistencia | SQLAlchemy 2.1 async + psycopg 3 + Alembic | ADR-0003 |
| Autenticación | Sesiones opacas en PostgreSQL + cookie segura + CSRF | ADR-0004 |
| Tareas en segundo plano | ARQ sobre Redis | ADR-0005 |
| Archivos | Almacenamiento privado local tras interfaz de almacenamiento | ADR-0006 |
| Observabilidad | structlog JSON + request-id + errores uniformes + paginación | ADR-0007 |
| Calidad | Ruff + mypy + pytest + pre-commit + GitHub Actions | ADR-0008 |
| Git | Trunk-based con ramas cortas y Conventional Commits | ADR-0009 |
| Configuración | pydantic-settings + variables `SGA_*` + secretos externos | ADR-0010 |
| Despliegue | Linux + Nginx + systemd, sin Docker como requisito | ADR-0011 |

Estas decisiones son revisables mediante un ADR nuevo. No se cambian por conveniencia puntual sin registrar el motivo.

---

## 4. Repositorio y estrategia de ramas

### 4.1 Inicialización del repositorio

Desde `C:\Users\Tony\Documents\sga`:

```powershell
git init -b main
git config user.name "Nombre Apellido"
git config user.email "correo@institucion.gob"
```

No configurar credenciales ni claves en el repositorio. Si ya existe un remoto institucional:

```powershell
git remote add origin <URL_DEL_REPOSITORIO>
```

No ejecutar `git push` hasta revisar el diff y confirmar que no hay secretos.

### 4.2 Modelo de ramas

Se adopta **trunk-based development** con ramas cortas:

- `main`: rama estable, protegida, siempre ejecutable.
- `feat/<fase>-<descripcion>`: nueva funcionalidad.
- `fix/<descripcion>`: corrección.
- `docs/<descripcion>`: documentación.
- `chore/<descripcion>`: mantenimiento, dependencias, configuración.
- `refactor/<descripcion>`: refactorización sin cambio funcional.

Ejemplos:

```text
feat/b0-base-backend
docs/b0-decisiones
chore/b0-calidad
fix/health-readiness-timeout
```

Reglas:

- Ramas de vida corta (idealmente menos de 3 días).
- Integración mediante Pull Request.
- Squash merge para mantener historial legible.
- No hacer push directo a `main`.
- No reescribir historia compartida.
- No mezclar cambios de varias fases en una rama.

### 4.3 Convención de commits

Formato:

```text
<tipo>(<alcance>): <descripción en imperativo>
```

Tipos permitidos: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `build`, `ci`, `perf`, `security`.

Ejemplos:

```text
chore(b0): inicializar estructura del backend
docs(b0): registrar ADR de autenticacion por sesiones
test(b0): cubrir validacion de configuracion
ci(b0): ejecutar lint tipado y pruebas
```

Reglas:

- Descripción en español o inglés consistente, nunca mezclada en el mismo repositorio.
- Máximo 72 caracteres en la primera línea.
- Cuerpo opcional explicando el qué y el porqué, no el cómo línea por línea.
- Referenciar incidencias cuando existan.

### 4.4 Versionado y etiquetas

- Versionado semántico `MAYOR.MENOR.PARCHE` para el backend.
- Etiquetas de fase: `phase-b0`, `phase-b1`, etc.
- Etiquetas de release: `v0.1.0`, `v0.2.0`.
- Una etiqueta de fase solo se crea cuando se cumplen los criterios de aceptación.

Comandos:

```powershell
git tag -a phase-b0 -m "Fase B0 completada"
git tag -a v0.1.0 -m "Base tecnica del backend"
```

No crear etiquetas sobre commits que no hayan pasado CI.

### 4.5 Archivos de configuración del repositorio

#### Archivo: `.gitignore` (raíz)

```gitignore
# ============================================================
# Secretos y configuracion local
# ============================================================
.env
.env.*
!.env.example
*.pem
*.key
*.p12
*.pfx
*.jks
secrets/
secret/
*.secret

# ============================================================
# Python
# ============================================================
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.eggs/
.venv/
venv/
env/
.python-version.bak

# ============================================================
# Herramientas
# ============================================================
.mypy_cache/
.dmypy.json
.ruff_cache/
.pytest_cache/
.coverage
.coverage.*
coverage.xml
htmlcov/
.hypothesis/
.tox/
.nox/
.cache/
.pre-commit-cache/

# ============================================================
# Datos, archivos y respaldos
# ============================================================
backend/var/
backend/storage/
backend/media/
backend/private/
backend/backups/
*.log
*.sqlite
*.sqlite3
*.dump
*.sql.gz
!docs/**/*.sql

# ============================================================
# Documentos judiciales y datos reales
# ============================================================
*.pdf
*.docx
*.doc
*.xlsx
*.xls
*.tif
*.tiff
!docs/**/*.pdf
!docs/**/*.docx
!docs/**/*.xlsx

# ============================================================
# Sistema operativo y editores
# ============================================================
.DS_Store
Thumbs.db
Desktop.ini
.idea/
*.swp
*.swo
*~
.vscode/
!.vscode/settings.json
!.vscode/extensions.json

# ============================================================
# Otros
# ============================================================
node_modules/
frontend/dist/
```

Notas:

- La regla de PDF/DOCX/XLSX evita subir documentos reales por accidente. Las excepciones permiten documentación técnica con ejemplos sintéticos.
- `backend/var/` contiene archivos temporales y almacenamiento privado de desarrollo.
- Nunca agregar `!.env` ni excepciones para archivos de secretos.

#### Archivo: `.gitattributes` (raíz)

```gitattributes
* text=auto eol=lf

*.ps1 text eol=crlf
*.bat text eol=crlf
*.cmd text eol=crlf

*.png binary
*.jpg binary
*.jpeg binary
*.gif binary
*.ico binary
*.pdf binary
*.docx binary
*.xlsx binary
*.zip binary
*.gz binary
*.7z binary

uv.lock text eol=lf linguist-generated=true
alembic.ini text eol=lf
```

#### Archivo: `.editorconfig` (raíz)

```editorconfig
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.{yml,yaml,json,jsonc,toml,md}]
indent_size = 2

[*.md]
trim_trailing_whitespace = false

[*.ps1]
end_of_line = crlf
indent_size = 4

[Makefile]
indent_style = tab
```

#### Archivo opcional: `.vscode/settings.json` (raíz)

```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.ruff": "explicit",
    "source.organizeImports.ruff": "explicit"
  },
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/Scripts/python.exe",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["backend/tests"],
  "python.analysis.typeCheckingMode": "strict",
  "files.eol": "\n",
  "files.insertFinalNewline": true,
  "files.trimTrailingWhitespace": true,
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.tabSize": 4
  },
  "[markdown]": {
    "editor.tabSize": 2
  }
}
```

#### Archivo opcional: `.vscode/extensions.json` (raíz)

```json
{
  "recommendations": [
    "charliermarsh.ruff",
    "ms-python.python",
    "ms-python.mypy-type-checker",
    "redhat.vscode-yaml",
    "tamasfe.even-better-toml",
    "bierner.markdown-mermaid"
  ]
}
```

---

## 5. Estructura de carpetas de B0

La estructura adopta el layout `src/` dentro de `backend/`. Se desvía del ejemplo de `AGENTS.md` (`backend/app/...`) porque `AGENTS.md` indica expresamente que la estructura es orientativa y ajustable durante B0. El layout `src/` evita importaciones accidentales del directorio de trabajo y es el recomendado para paquetes instalables.

```text
sga/
├── .editorconfig
├── .gitattributes
├── .gitleaks.toml
├── .gitignore
├── .pre-commit-config.yaml
├── README.md
├── .github/
│   └── workflows/
│       └── ci.yml
├── .vscode/
│   ├── extensions.json
│   └── settings.json
├── backend/
│   ├── .env.example
│   ├── .python-version
│   ├── alembic.ini
│   ├── README.md                    # breve, requerido por pyproject
│   ├── pyproject.toml
│   ├── uv.lock                      # generado por uv, se versiona
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako           # generado por alembic init
│   │   └── versions/
│   │       └── .gitkeep
│   ├── scripts/
│   │   ├── check.ps1
│   │   ├── dev.ps1
│   │   └── worker.ps1
│   ├── src/
│   │   └── judicial_archive/
│   │       ├── __init__.py
│   │       ├── asgi.py
│   │       ├── main.py
│   │       ├── api/
│   │       │   ├── __init__.py
│   │       │   ├── deps.py
│   │       │   └── v1/
│   │       │       ├── __init__.py
│   │       │       ├── health.py
│   │       │       └── router.py
│   │       ├── core/
│   │       │   ├── __init__.py
│   │       │   ├── config.py
│   │       │   ├── errors.py
│   │       │   ├── logging.py
│   │       │   ├── middleware.py
│   │       │   ├── pagination.py
│   │       │   ├── runtime.py
│   │       │   └── security.py
│   │       ├── db/
│   │       │   ├── __init__.py
│   │       │   ├── base.py
│   │       │   ├── health.py
│   │       │   └── session.py
│   │       ├── modules/
│   │       │   └── __init__.py
│   │       └── tasks/
│   │           ├── __init__.py
│   │           └── worker.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── helpers.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── test_errors.py
│   │   │   └── test_health.py
│   │   ├── integration/
│   │   │   ├── __init__.py
│   │   │   └── test_dependencies.py
│   │   └── unit/
│   │       ├── __init__.py
│   │       ├── test_config.py
│   │       ├── test_db_health.py
│   │       ├── test_pagination.py
│   │       ├── test_security.py
│   │       └── test_session.py
│   └── var/                         # no se versiona; se crea al usar almacenamiento
├── docs/
│   ├── AGENTS.md
│   ├── api.md
│   ├── arquitectura.md
│   ├── decisiones/
│   │   ├── ADR-0001-python-y-uv.md
│   │   ├── ADR-0002-arquitectura-modular.md
│   │   ├── ADR-0003-persistencia.md
│   │   ├── ADR-0004-autenticacion.md
│   │   ├── ADR-0005-tareas-segundo-plano.md
│   │   ├── ADR-0006-almacenamiento-privado.md
│   │   ├── ADR-0007-observabilidad-y-errores.md
│   │   ├── ADR-0008-calidad-y-ci.md
│   │   ├── ADR-0009-git-y-versionado.md
│   │   ├── ADR-0010-configuracion-y-secretos.md
│   │   └── ADR-0011-despliegue.md
│   ├── instalacion-desarrollo.md
│   ├── pendientes-de-validacion.md
│   ├── pruebas.md
│   ├── seguridad.md
│   └── phases/
│       ├── GUIA_DESARROLLO_FASES_SGA.md
│       └── phaseB0_guide.md
```

Reglas de estructura:

- `core/`: configuración, seguridad, errores, logging, middleware y paginación. No contiene lógica de negocio.
- `db/`: motor, sesiones, base declarativa y comprobaciones de salud.
- `api/`: dependencias HTTP, routers versionados y endpoints. No contiene lógica de negocio.
- `modules/`: módulos de dominio. Cada módulo se crea **cuando exista funcionalidad real** en su fase.
- `tasks/`: trabajador ARQ y, más adelante, tareas concretas.
- `tests/`: unitarias, API e integración. Las pruebas de integración requieren PostgreSQL/Redis reales.
- No se crean carpetas vacías ni módulos ficticios para cumplir una plantilla.

### 5.1 Estructura interna de cada módulo de dominio (para fases posteriores)

Cuando se cree un módulo, por ejemplo `modules/case_files/`, usará esta separación solo si aporta valor:

```text
case_files/
├── __init__.py
├── models.py          # SQLAlchemy
├── schemas.py         # Pydantic de entrada/salida
├── repository.py      # acceso a datos
├── service.py         # reglas de negocio y transacciones
├── router.py          # endpoints
├── validators.py      # validaciones de dominio
├── permissions.py     # permisos del módulo
└── tests/
```

No todos los módulos necesitan todos los archivos. Evitar abstracciones vacías.

---

## 6. Python, uv y pyproject.toml

### 6.1 Instalación de Python 3.12 con uv

Desde la raíz del repositorio:

```powershell
uv python install 3.12
New-Item -ItemType Directory -Force backend | Out-Null
Set-Location backend
uv python pin 3.12
```

Esto crea `backend/.python-version` con el contenido:

```text
3.12
```

Verificación:

```powershell
uv python find 3.12
uv python list --only-installed
```

### 6.2 Creación manual de `pyproject.toml`

No usar `uv init` para evitar archivos de ejemplo y nombres incorrectos. Crear el archivo con el contenido completo de la sección 6.3.

#### Archivo: `backend/pyproject.toml`

```toml
[project]
name = "sga-backend"
version = "0.1.0"
description = "Backend del Sistema de Gestion Documental Judicial (SGA)"
readme = "README.md"
requires-python = ">=3.12,<3.13"
license = "LicenseRef-Proprietary"
authors = [
  { name = "Equipo SGA" },
]
keywords = ["judicial", "archivo", "gestion-documental", "fastapi"]
classifiers = [
  "Development Status :: 3 - Alpha",
  "Environment :: Web Environment",
  "Framework :: FastAPI",
  "Intended Audience :: Legal Industry",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.12",
  "Typing :: Typed",
]
dependencies = [
  "alembic>=1.20,<2",
  "arq>=0.28,<0.29",
  "fastapi>=0.161,<1",
  "psycopg[binary]>=3.3,<4",
  "pydantic>=2.14,<3",
  "pydantic-settings>=2.16,<3",
  "pwdlib[argon2]>=0.3,<1",
  "redis[hiredis]>=5.2,<6",
  "sqlalchemy[asyncio]>=2.1,<3",
  "structlog>=26.1,<27",
  "uvicorn[standard]>=0.54,<1",
]

[dependency-groups]
dev = [
  "httpx>=0.28,<1",
  "mypy>=2.4,<3",
  "pre-commit>=4.7,<5",
  "pytest>=9.1,<10",
  "pytest-asyncio>=1.4,<2",
  "pytest-cov>=7.1,<8",
  "ruff>=0.17,<1",
]

[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/judicial_archive"]

[tool.hatch.build.targets.sdist]
include = [
  "src/judicial_archive",
  "tests",
  "alembic",
  "alembic.ini",
  "README.md",
]

[tool.uv]
package = true
python-preference = "managed"

# ============================================================
# Ruff
# ============================================================
[tool.ruff]
target-version = "py312"
line-length = 100
src = ["src", "tests"]
extend-exclude = [
  ".venv",
  "alembic/versions",
]

[tool.ruff.lint]
select = [
  "E4",   # errores de importacion
  "E7",   # errores de estructura
  "E9",   # errores de ejecucion
  "F",    # pyflakes
  "I",    # isort
  "N",    # pep8-naming
  "UP",   # pyupgrade
  "B",    # bugbear
  "SIM",  # simplificaciones
  "ASYNC",# errores de async
  "C4",   # comprehensions
  "DTZ",  # fechas con zona horaria
  "PT",   # pytest-style
  "RUF",  # reglas propias de ruff
  "S",    # bandit
  "LOG",  # logging
  "G",    # formato de logging
  "PTH",  # pathlib
  "T20",  # prohibir print
]
ignore = [
  "B008",  # FastAPI usa Depends() en defaults
  "UP046", # se usa Generic[T] por claridad y compatibilidad con Pydantic
  "RUF001",# caracteres unicode en mensajes en espanol
  "RUF002",
  "RUF003",
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "S105", "S106", "S107"]
"alembic/versions/**/*.py" = ["E501"]
"src/judicial_archive/tasks/worker.py" = ["ARG"]

[tool.ruff.lint.isort]
known-first-party = ["judicial_archive", "tests"]
combine-as-imports = true

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "lf"

# ============================================================
# mypy
# ============================================================
[tool.mypy]
python_version = "3.12"
strict = true
warn_unreachable = true
warn_unused_ignores = true
show_error_codes = true
show_column_numbers = true
pretty = true
plugins = [
  "pydantic.mypy",
]
exclude = [
  "^\\.venv/",
  "alembic/versions/",
]

[[tool.mypy.overrides]]
module = ["alembic.*"]
ignore_errors = true

[[tool.mypy.overrides]]
module = ["arq", "arq.*"]
ignore_missing_imports = true

# ============================================================
# pytest
# ============================================================
[tool.pytest.ini_options]
minversion = "9.0"
testpaths = ["tests"]
addopts = [
  "-ra",
  "--strict-markers",
  "--strict-config",
  "--cov=judicial_archive",
  "--cov-report=term-missing",
  "--cov-report=xml",
]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
markers = [
  "integration: requiere PostgreSQL y Redis reales",
  "security: comprobaciones de seguridad",
  "slow: prueba lenta",
]
filterwarnings = [
  "error",
]

# ============================================================
# cobertura
# ============================================================
[tool.coverage.run]
branch = true
source = ["src/judicial_archive"]
omit = [
  "src/judicial_archive/asgi.py",
  "src/judicial_archive/__main__.py",
]

[tool.coverage.report]
show_missing = true
skip_covered = true
fail_under = 60
exclude_lines = [
  "pragma: no cover",
  "if TYPE_CHECKING:",
  "raise NotImplementedError",
  "\\.\\.\\.",
]
```

#### Archivo: `backend/README.md`

`pyproject.toml` declara `readme = "README.md"`, por lo que el archivo debe existir dentro de `backend/`. Mantenerlo breve y remitir al README raíz:

````markdown
# SGA Backend

Backend del Sistema de Gestión Documental Judicial.

La documentación principal está en el README raíz y en `../docs/`.
Comandos básicos:

```powershell
uv sync
uv run uvicorn judicial_archive.asgi:app --reload
uv run pytest
```
````

No duplicar aquí la documentación completa; este archivo solo satisface el metadato del paquete y orienta a la documentación central.

Notas importantes sobre dependencias:

- **Redis se fija en `<6`** porque ARQ 0.28 declara `redis>=4.2,<6`. Instalar redis-py 8 provocaría un conflicto de resolución. redis-py 5.3 funciona correctamente con servidores Redis 7 y 8.
- **`orjson` no se usa**: FastAPI 0.161 deprecó `ORJSONResponse`; los errores usan `JSONResponse` y las respuestas normales se serializan con Pydantic.
- **SQLAlchemy 2.1 no incluye `sqlalchemy.ext.mypy.plugin`**: no se declara ese plugin; SQLAlchemy 2.1 trae tipado nativo y mypy falla al importar el módulo inexistente.
- **Python 3.12** se elige por compatibilidad con el ecosistema de OCR, visión y procesamiento documental que se evaluará en B11. No se usa 3.13/3.14 en B0.
- **`arq` se fija `<0.29`** porque es una versión 0.x; una actualización menor puede introducir cambios incompatibles. Se revisará en B10/B11.
- **No se incluyen dependencias de OCR, imágenes, PDF ni frontend** en B0. Se agregarán cuando la fase correspondiente las requiera.
- `uv.lock` es la fuente de reproducibilidad. Se versiona y no se edita a mano.

### 6.3 Sincronización e inspección

Desde `backend/`:

```powershell
uv sync
uv lock --check
uv tree
```

`uv sync`:

- crea `.venv`;
- instala Python 3.12 si hace falta;
- instala dependencias y el proyecto en modo editable;
- genera/actualiza `uv.lock`.

`uv lock --check` verifica que el lock está actualizado. En CI se usa `uv sync --frozen` para no modificar el lock.

### 6.4 Política de dependencias

- Toda dependencia nueva se agrega con `uv add <paquete>` o `uv add --dev <paquete>`, nunca con `pip install`.
- Cada dependencia nueva requiere justificación en el PR: necesidad, licencia, mantenimiento, seguridad y alternativa considerada.
- No se agregan dos librerías que resuelvan lo mismo.
- Actualizaciones de dependencias en PR separados y con pruebas.
- Actualización de seguridad urgente puede ir en PR propio, documentando el CVE.
- No se usan paquetes abandonados, sin licencia clara o de procedencia dudosa.
- Producción instala sin grupo `dev`: `uv sync --frozen --no-dev`.

Comandos útiles:

```powershell
uv add httpx
uv add --dev pytest-xdist
uv remove httpx
uv lock --upgrade
uv lock --upgrade-package fastapi
uv sync --frozen
uv sync --frozen --no-dev
```

### 6.5 Verificación de Python y del entorno virtual

```powershell
uv run python --version
uv run python -c "import fastapi, sqlalchemy, pydantic, arq, structlog; print('dependencias ok')"
```

Resultado esperado: `Python 3.12.x` y `dependencias ok`.

---

## 7. Configuración de entornos y secretos

### 7.1 Principios

- Toda configuración se lee de variables de entorno con prefijo `SGA_`.
- Los valores se validan al arrancar; si falta algo obligatorio, el proceso falla con un mensaje claro y sin revelar secretos.
- `.env` es solo para desarrollo local y **nunca** se versiona.
- `.env.example` contiene nombres y valores ficticios, nunca credenciales reales.
- Producción, staging, pruebas y desarrollo usan archivos y secretos separados.
- No se permite configuración insegura silenciosa en producción.
- La configuración es inmutable en tiempo de ejecución y se inyecta en `app.state.settings`.

### 7.2 Archivo: `backend/.env.example`

```dotenv
# ============================================================
# SGA - Configuracion de ejemplo
# Copiar a .env y completar los valores.
# NUNCA versionar .env ni secretos reales.
# ============================================================

# Entorno: development | testing | staging | production
SGA_ENVIRONMENT=development
SGA_DEBUG=true

# Clave secreta de al menos 32 caracteres.
# Generar con:
#   uv run python -c "import secrets; print(secrets.token_urlsafe(64))"
SGA_SECRET_KEY=

# API
SGA_API_V1_PREFIX=/api/v1
SGA_DOCS_ENABLED=true
SGA_LOG_LEVEL=INFO
SGA_LOG_JSON=false

# Base de datos PostgreSQL (driver psycopg 3)
SGA_DATABASE_URL=postgresql+psycopg://sga_dev:CAMBIAR_CONTRASENA_DEV@localhost:5432/sga_dev
SGA_DB_POOL_SIZE=10
SGA_DB_MAX_OVERFLOW=20
SGA_DB_ECHO=false
SGA_DB_POOL_PRE_PING=true
SGA_DB_POOL_RECYCLE_SECONDS=1800

# Redis
SGA_REDIS_URL=redis://localhost:6379/0
SGA_REDIS_SOCKET_TIMEOUT_SECONDS=3

# CORS y hosts permitidos (listas separadas por coma)
SGA_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
SGA_TRUSTED_HOSTS=localhost,127.0.0.1,testserver

# Sesiones y CSRF (la implementacion funcional llega en B4)
SGA_SESSION_COOKIE_NAME=sga_session
SGA_SESSION_COOKIE_SECURE=false
SGA_SESSION_IDLE_MINUTES=30
SGA_SESSION_ABSOLUTE_HOURS=12
SGA_CSRF_COOKIE_NAME=sga_csrf
SGA_CSRF_HEADER_NAME=X-CSRF-Token

# Tareas en segundo plano (ARQ)
SGA_TASK_QUEUE_NAME=sga
SGA_TASK_MAX_JOBS=4
SGA_TASK_JOB_TIMEOUT_SECONDS=900

# Almacenamiento privado
SGA_STORAGE_BACKEND=local
SGA_STORAGE_ROOT=var/storage

# Salud y observabilidad
SGA_REQUEST_ID_HEADER=X-Request-ID
SGA_READINESS_TIMEOUT_SECONDS=3
```

Reglas:

- Copiar con `Copy-Item .env.example .env`.
- Completar `SGA_SECRET_KEY` y la contraseña de PostgreSQL.
- No usar el archivo `.env.example` como `.env` en producción.
- En producción, `SGA_SESSION_COOKIE_SECURE=true`, `SGA_LOG_JSON=true`, `SGA_DOCS_ENABLED=false` y `SGA_TRUSTED_HOSTS` con dominios reales.

### 7.3 Archivo: `backend/src/judicial_archive/core/config.py`

```python
from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    Field,
    PostgresDsn,
    RedisDsn,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
StorageBackend = Literal["local"]


class Settings(BaseSettings):
    """Configuracion tipada de la aplicacion, validada al arrancar."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SGA_",
        case_sensitive=False,
        extra="forbid",
        validate_default=True,
    )

    # Obligatorios: no tienen valor por defecto seguro.
    secret_key: SecretStr
    database_url: PostgresDsn
    redis_url: RedisDsn

    # Aplicacion
    app_name: str = "SGA - Sistema de Gestion Documental Judicial"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    docs_enabled: bool = False
    log_level: LogLevel = "INFO"
    log_json: bool = True

    # HTTP
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    trusted_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    request_id_header: str = Field(
        default="X-Request-ID",
        pattern=r"^[A-Za-z0-9-]{3,64}$",
    )

    # Base de datos
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=100)
    db_echo: bool = False
    db_pool_pre_ping: bool = True
    db_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)

    # Redis
    redis_socket_timeout_seconds: float = Field(default=3.0, gt=0, le=60)

    # Sesiones y CSRF (se implementan en B4)
    session_cookie_name: str = "sga_session"
    session_cookie_secure: bool = True
    session_idle_minutes: int = Field(default=30, ge=5, le=1440)
    session_absolute_hours: int = Field(default=12, ge=1, le=720)
    csrf_cookie_name: str = "sga_csrf"
    csrf_header_name: str = "X-CSRF-Token"

    # Tareas en segundo plano
    task_queue_name: str = "sga"
    task_max_jobs: int = Field(default=4, ge=1, le=64)
    task_job_timeout_seconds: int = Field(default=900, ge=10, le=86400)

    # Almacenamiento privado
    storage_backend: StorageBackend = "local"
    storage_root: Path = Path("var/storage")

    # Salud
    readiness_timeout_seconds: float = Field(default=3.0, gt=0, le=30)

    @field_validator("secret_key")
    @classmethod
    def _validate_secret_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            msg = "SGA_SECRET_KEY debe tener al menos 32 caracteres."
            raise ValueError(msg)
        return value

    @field_validator("api_v1_prefix")
    @classmethod
    def _validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/"):
            msg = "SGA_API_V1_PREFIX debe comenzar con '/' y no terminar con '/'."
            raise ValueError(msg)
        return value

    @field_validator("cors_origins", "trusted_hosts", mode="before")
    @classmethod
    def _split_comma_separated(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _validate_cors_credentials(self) -> Self:
        if any(origin.strip() == "*" for origin in self.cors_origins):
            msg = "SGA_CORS_ORIGINS no puede contener '*' porque se usan credenciales"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def _validate_production_rules(self) -> Self:
        if self.environment is not Environment.PRODUCTION:
            return self

        problems: list[str] = []
        if self.debug:
            problems.append("SGA_DEBUG debe ser false en produccion")
        if self.docs_enabled:
            problems.append("SGA_DOCS_ENABLED debe ser false en produccion")
        if not self.log_json:
            problems.append("SGA_LOG_JSON debe ser true en produccion")
        if not self.session_cookie_secure:
            problems.append("SGA_SESSION_COOKIE_SECURE debe ser true en produccion")
        if "testserver" in self.trusted_hosts:
            problems.append(
                "SGA_TRUSTED_HOSTS no puede contener 'testserver' en produccion"
            )
        if "*" in self.trusted_hosts:
            problems.append("SGA_TRUSTED_HOSTS no puede contener '*' en produccion")

        if problems:
            msg = "Configuracion de produccion invalida: " + "; ".join(problems)
            raise ValueError(msg)
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la configuracion validada, cacheada por proceso."""
    return Settings()  # pyright: ignore[reportCallIssue]
```

Notas:

- `NoDecode` evita que pydantic-settings intente interpretar las listas como JSON; así se admite `a,b,c`.
- `secret_key` es `SecretStr`; nunca se imprime su valor.
- `extra="forbid"` detecta nombres de variables mal escritos, una causa frecuente de fallos silenciosos.
- La caché de `get_settings` se limpia en pruebas con `get_settings.cache_clear()`.
- El plugin de Pydantic para mypy reconoce los campos obligatorios, pero Pylance strict no: se usa `# pyright: ignore[reportCallIssue]`. `# type: ignore` no sirve porque mypy lo marcaria como ignore sin uso.

### 7.4 Reglas de secretos

| Secreto | Dónde vive | Rotación |
|---|---|---|
| `SGA_SECRET_KEY` | `.env` local / gestor de secretos en producción | Al menos anual y ante incidente |
| Contraseña PostgreSQL | `.env` local / gestor de secretos | Según política institucional |
| Contraseña Redis | `.env` local / gestor de secretos | Según política institucional |
| Credenciales de OCR externo | No se usan por defecto | Se evalúa en B11 |

Reglas obligatorias:

- No incluir secretos en código, tests, documentación, capturas ni logs.
- No imprimir `settings` completos ni usar `model_dump()` sobre `Settings` en logs.
- No enviar `.env` por correo ni chat.
- Generar claves con `secrets`, no con `random`.
- En producción usar variables del servicio o un gestor de secretos; no archivos dentro del repositorio.
- Si un secreto se expone, rotarlo de inmediato y registrar el incidente.

Generar una clave:

```powershell
cd backend
uv run python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## 8. Logging estructurado e identificador de petición

### 8.1 Política

- Logs estructurados en JSON en producción y legibles en desarrollo.
- Todo log HTTP incluye `request_id`.
- Se registran eventos, no frases libres concatenadas.
- No se registran contraseñas, tokens, cookies, cuerpos de documentos ni datos personales innecesarios.
- Los errores 5xx se registran con traza en el servidor, pero el cliente recibe un mensaje genérico.
- Los errores 4xx esperados se registran como advertencia, no como error.
- `X-Request-ID` se acepta del cliente solo si cumple un formato seguro; en caso contrario se genera uno nuevo.
- El identificador se devuelve siempre en la respuesta.

### 8.2 Archivo: `backend/src/judicial_archive/core/logging.py`

```python
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from judicial_archive.core.config import Settings

_SENSITIVE_KEY_MARKERS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "authorization",
        "cookie",
        "api_key",
        "apikey",
        "session",
    }
)


def _redact_sensitive_values(
    _logger: Any,
    _method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Reemplaza valores de claves sensibles antes de emitir el log."""
    for key in list(event_dict):
        if any(marker in key.lower() for marker in _SENSITIVE_KEY_MARKERS):
            event_dict[key] = "***"
    return event_dict


def _shared_processors() -> list[Processor]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _redact_sensitive_values,
    ]


def configure_logging(settings: Settings) -> None:
    """Configura structlog y el logging estandar de forma unificada."""
    shared_processors = _shared_processors()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    renderer: Processor
    if settings.log_json:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(logger_name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True
```

Notas:

- `cache_logger_on_first_use=True` mejora rendimiento; no se cambia la configuración en caliente.
- `_redact_sensitive_values` es una defensa adicional, no sustituye la disciplina de no registrar datos sensibles.
- En producción, `SGA_LOG_JSON=true` es obligatorio por validación.
- No se registra el contenido de los documentos ni el cuerpo completo de las peticiones.

### 8.3 Archivo: `backend/src/judicial_archive/core/middleware.py`

```python
from __future__ import annotations

import re
from uuid import uuid4

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


class RequestContextMiddleware:
    """Middleware ASGI puro que asigna y propaga un request-id seguro."""

    def __init__(self, app: ASGIApp, *, header_name: str = "X-Request-ID") -> None:
        self.app = app
        self.header_name = header_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        incoming = headers.get(self.header_name)
        request_id = (
            incoming
            if incoming and _REQUEST_ID_PATTERN.fullmatch(incoming)
            else uuid4().hex
        )

        state = scope.setdefault("state", {})
        state["request_id"] = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers[self.header_name] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            structlog.contextvars.clear_contextvars()
```

Notas:

- Se implementa como middleware ASGI puro para evitar problemas de `BaseHTTPMiddleware` con streaming y contextvars.
- Si el cliente envía un `X-Request-ID` válido, se conserva para correlación con proxy/APM.
- Si no es válido, se genera uno nuevo y no se refleja entrada arbitraria en cabeceras.
- El identificador queda en `request.state.request_id` y en el contexto de structlog.

### 8.4 Uso en código

En cualquier módulo:

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("box_created", box_id=str(box.id), box_number=box.number)
```

No usar `print` (Ruff `T20` lo prohíbe). No usar `f"..."` como mensaje de log; usar eventos y campos (`G` lo detecta).

---

## 9. Errores uniformes

### 9.1 Formato de error

Todas las respuestas de error usan el mismo sobre:

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

Reglas:

- `code` es estable y apto para lógica de cliente.
- `message` es legible en español y no revela información interna.
- `details` solo incluye datos seguros y accionables.
- `request_id` permite correlacionar con logs.
- Nunca se devuelven trazas, rutas del servidor, DSN, SQL ni secretos.
- Los errores de validación no devuelven el valor de entrada (`input`), para evitar filtrar datos sensibles.

### 9.2 Archivo: `backend/src/judicial_archive/core/errors.py`

```python
from __future__ import annotations

from enum import StrEnum
from typing import Any, cast

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "validation_error"
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    CONFLICT = "conflict"
    RATE_LIMITED = "rate_limited"
    SERVICE_UNAVAILABLE = "service_unavailable"
    INTERNAL_ERROR = "internal_error"


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AppError(Exception):
    """Error de aplicacion con codigo estable y estado HTTP asociado."""

    status_code: int = 400
    code: ErrorCode = ErrorCode.BAD_REQUEST

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class UnauthorizedError(AppError):
    status_code = 401
    code = ErrorCode.UNAUTHORIZED


class ForbiddenError(AppError):
    status_code = 403
    code = ErrorCode.FORBIDDEN


class NotFoundError(AppError):
    status_code = 404
    code = ErrorCode.NOT_FOUND


class ConflictError(AppError):
    status_code = 409
    code = ErrorCode.CONFLICT


class InvalidParameterError(AppError):
    status_code = 422
    code = ErrorCode.VALIDATION_ERROR


class RateLimitedError(AppError):
    status_code = 429
    code = ErrorCode.RATE_LIMITED


class ServiceUnavailableError(AppError):
    status_code = 503
    code = ErrorCode.SERVICE_UNAVAILABLE


class InternalError(AppError):
    status_code = 500
    code = ErrorCode.INTERNAL_ERROR


logger = structlog.get_logger(__name__)

_HTTP_STATUS_TO_CODE: dict[int, ErrorCode] = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMITED,
    503: ErrorCode.SERVICE_UNAVAILABLE,
}


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else None


def _error_response(
    *,
    status_code: int,
    code: ErrorCode,
    message: str,
    request_id: str | None,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetail(
            code=code.value,
            message=message,
            details=details,
            request_id=request_id,
        )
    ).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=payload)


def _serialize_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for error in exc.errors():
        serialized.append(
            {
                "location": list(error.get("loc", ())),
                "message": error.get("msg", "Valor invalido."),
                "type": error.get("type", "value_error"),
            }
        )
    return serialized


async def app_error_handler(request: Request, exc: Exception) -> Response:
    app_error = cast(AppError, exc)
    if app_error.status_code >= 500:
        logger.error(
            "application_error",
            status_code=app_error.status_code,
            error_code=app_error.code.value,
            path=request.url.path,
            method=request.method,
        )
    else:
        logger.warning(
            "application_error",
            status_code=app_error.status_code,
            error_code=app_error.code.value,
            path=request.url.path,
            method=request.method,
        )
    return _error_response(
        status_code=app_error.status_code,
        code=app_error.code,
        message=app_error.message,
        request_id=_request_id(request),
        details=app_error.details,
    )


async def validation_exception_handler(request: Request, exc: Exception) -> Response:
    validation_error = cast(RequestValidationError, exc)
    return _error_response(
        status_code=422,
        code=ErrorCode.VALIDATION_ERROR,
        message="Los datos enviados no son validos.",
        request_id=_request_id(request),
        details={"errors": _serialize_validation_errors(validation_error)},
    )


async def http_exception_handler(request: Request, exc: Exception) -> Response:
    http_error = cast(StarletteHTTPException, exc)
    detail = cast(object, http_error.detail)
    if http_error.status_code >= 500:
        message = "Error interno del servidor."
    elif isinstance(detail, str):
        message = detail
    else:
        message = "Error en la solicitud."
    default_code = (
        ErrorCode.INTERNAL_ERROR
        if http_error.status_code >= 500
        else ErrorCode.BAD_REQUEST
    )
    code = _HTTP_STATUS_TO_CODE.get(http_error.status_code, default_code)
    return _error_response(
        status_code=http_error.status_code,
        code=code,
        message=message,
        request_id=_request_id(request),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
        exc_info=exc,
    )
    return _error_response(
        status_code=500,
        code=ErrorCode.INTERNAL_ERROR,
        message="Error interno del servidor.",
        request_id=_request_id(request),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
```

Notas:

- Se usa `JSONResponse` en lugar de `ORJSONResponse`: FastAPI 0.161 marca `ORJSONResponse` como deprecado y serializa directamente con Pydantic cuando existe `response_model`.
- `cast(...)` estrecha el tipo para mypy dentro de los handlers; los handlers se registran para esa clase exacta. No se usan `assert` en código de producción porque Ruff (bandit) los prohíbe y pueden desaparecer con `-O`.
- Los errores de validación se serializan sin `input` ni `ctx`.
- `AppError` permite lanzar errores de negocio desde servicios sin acoplar a FastAPI, aunque los códigos HTTP viven en la capa de aplicación.
- En B3/B4 se agregarán códigos específicos (por ejemplo, `invalid_credentials`, `position_occupied`) manteniendo el mismo sobre.

### 9.3 Catálogo inicial de códigos

| Código | HTTP | Uso |
|---|---|---|
| `validation_error` | 422 | Entrada inválida |
| `bad_request` | 400 | Solicitud incorrecta |
| `unauthorized` | 401 | Falta autenticación o expiró |
| `forbidden` | 403 | Sin permiso |
| `not_found` | 404 | Recurso inexistente |
| `method_not_allowed` | 405 | Método HTTP no permitido |
| `conflict` | 409 | Conflicto de estado o concurrencia |
| `rate_limited` | 429 | Límite de tasa excedido |
| `service_unavailable` | 503 | Dependencia no disponible |
| `internal_error` | 500 | Error no controlado |

---

## 10. Paginación y ordenamiento

### 10.1 Política

- Paginación por página, no por cursor, en B0. Se evaluará cursor para búsquedas masivas en B8.
- `page` empieza en 1.
- `page_size` por defecto 25 y máximo 100.
- La respuesta incluye `total`, `pages`, `has_next` y `has_previous`.
- El ordenamiento se permite solo por campos explícitos de una lista blanca por endpoint.
- Nunca se interpola un campo de ordenamiento directamente en SQL; se mapea a columnas conocidas.
- Los resultados deben tener un orden estable; si el campo elegido no es único, se añade un desempate por identificador en la consulta.

### 10.2 Archivo: `backend/src/judicial_archive/core/pagination.py`

```python
from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from math import ceil
from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

from judicial_archive.core.errors import InvalidParameterError

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class PageParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def pagination_params(
    page: Annotated[
        int, Query(ge=1, description="Numero de pagina (empieza en 1).")
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_SIZE, description="Elementos por pagina."),
    ] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


class SortParams(BaseModel):
    sort_by: str | None = None
    order: SortOrder = SortOrder.ASC


def build_sort_params(
    sort_by: str | None,
    order: SortOrder,
    *,
    allowed_fields: frozenset[str],
) -> SortParams:
    if sort_by is not None and sort_by not in allowed_fields:
        raise InvalidParameterError(
            "El campo de ordenamiento no esta permitido.",
            details={"allowed_fields": sorted(allowed_fields)},
        )
    return SortParams(sort_by=sort_by, order=order)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0)
    has_next: bool
    has_previous: bool

    @classmethod
    def build(cls, items: Sequence[T], *, total: int, params: PageParams) -> Page[T]:
        pages = ceil(total / params.page_size) if total > 0 else 0
        return cls(
            items=list(items),
            total=total,
            page=params.page,
            page_size=params.page_size,
            pages=pages,
            has_next=params.page < pages,
            has_previous=params.page > 1 and total > 0,
        )
```

Ejemplo de uso futuro en un endpoint:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from judicial_archive.core.pagination import (
    Page,
    PageParams,
    SortOrder,
    build_sort_params,
    pagination_params,
)

router = APIRouter()

_ALLOWED_SORT_FIELDS = frozenset({"number", "created_at"})


@router.get("/boxes", response_model=Page[dict[str, object]])
async def list_boxes(
    params: Annotated[PageParams, Depends(pagination_params)],
    sort_by: Annotated[str | None, Query()] = None,
    order: Annotated[SortOrder, Query()] = SortOrder.ASC,
) -> Page[dict[str, object]]:
    build_sort_params(sort_by, order, allowed_fields=_ALLOWED_SORT_FIELDS)
    # La consulta real se implementa en B6/B8.
    return Page[dict[str, object]].build([], total=0, params=params)
```

Este ejemplo es ilustrativo y **no debe crearse todavía**; los endpoints de negocio pertenecen a fases posteriores.

---

## 11. Base de datos, sesiones y Alembic

### 11.1 Política

- PostgreSQL es la fuente de verdad.
- SQLAlchemy 2.1 en modo asíncrono con driver `psycopg` 3.
- Alembic es el único mecanismo para modificar el esquema.
- En B0 no se crean tablas de negocio ni migraciones. Solo se prepara la base declarativa, el motor, la sesión y la configuración de Alembic.
- Las migraciones se crearán en B2 tras aprobar el modelo de dominio de B1.
- No se ejecuta DDL manual en desarrollo que no esté respaldado por una migración.
- Las sesiones no hacen `commit` automático; el servicio de aplicación define la unidad de trabajo.
- Las operaciones que afectan varias entidades se ejecutan en una transacción.
- Se prohíbe `SELECT ... FOR UPDATE` sin justificación y sin control de timeout.

### 11.2 Archivo: `backend/src/judicial_archive/db/base.py`

```python
from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base declarativa comun. Los modelos de dominio se agregan en B2."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
```

La convención de nombres es obligatoria para que Alembic genere nombres estables de índices, claves y restricciones. Sin ella, las migraciones autogeneradas producen nombres aleatorios y difíciles de revertir.

### 11.3 Archivo: `backend/src/judicial_archive/db/session.py`

```python
from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from judicial_archive.core.config import Settings


class Database:
    """Contenedor del motor y la fabrica de sesiones asincronas."""

    def __init__(self, settings: Settings) -> None:
        self._engine: AsyncEngine = create_async_engine(
            str(settings.database_url),
            echo=settings.db_echo,
            pool_pre_ping=settings.db_pool_pre_ping,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_recycle=settings.db_pool_recycle_seconds,
        )
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    def session(self) -> AsyncSession:
        return self._session_factory()

    async def dispose(self) -> None:
        await self._engine.dispose()
```

### 11.4 Archivo: `backend/src/judicial_archive/db/health.py`

```python
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Literal, Protocol

import structlog
from sqlalchemy import text

from judicial_archive.db.session import Database

HealthState = Literal["ok", "error"]


class RedisPing(Protocol):
    """Contrato minimo de Redis usado por salud; facilita pruebas."""

    def ping(self, **kwargs: Any) -> Any: ...


@dataclass(frozen=True, slots=True)
class DependencyHealth:
    status: HealthState
    latency_ms: float


logger = structlog.get_logger(__name__)


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 2)


async def check_database(
    database: Database | None,
    timeout_seconds: float,
) -> DependencyHealth:
    started = perf_counter()
    if database is None:
        logger.warning("database_health_check_unavailable")
        return DependencyHealth(status="error", latency_ms=0.0)
    try:
        async with asyncio.timeout(timeout_seconds):
            async with database.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning(
            "database_health_check_failed",
            error_type=type(exc).__name__,
        )
        return DependencyHealth(status="error", latency_ms=_elapsed_ms(started))
    return DependencyHealth(status="ok", latency_ms=_elapsed_ms(started))


async def check_redis(
    redis: RedisPing | None,
    timeout_seconds: float,
) -> DependencyHealth:
    started = perf_counter()
    if redis is None:
        logger.warning("redis_health_check_unavailable")
        return DependencyHealth(status="error", latency_ms=0.0)
    try:
        async with asyncio.timeout(timeout_seconds):
            await redis.ping()
    except Exception as exc:
        logger.warning(
            "redis_health_check_failed",
            error_type=type(exc).__name__,
        )
        return DependencyHealth(status="error", latency_ms=_elapsed_ms(started))
    return DependencyHealth(status="ok", latency_ms=_elapsed_ms(started))
```

### 11.5 Archivo: `backend/alembic.ini`

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
path_separator = os
sqlalchemy.url =

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

La URL no se escribe en `alembic.ini`; se inyecta desde `Settings` en `env.py`. Así no hay credenciales en archivos versionados.

### 11.6 Creación del esqueleto de Alembic

Ejecutar una sola vez desde `backend/`:

```powershell
uv run alembic init -t async alembic
```

Esto crea `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/` y `alembic.ini`. Luego:

1. Reemplazar `alembic.ini` por el contenido de la sección 11.5.
2. Reemplazar `alembic/env.py` por el contenido de la sección 11.7.
3. Crear `alembic/versions/.gitkeep` vacío para versionar la carpeta.
4. No generar ninguna migración todavía.

### 11.7 Archivo: `backend/alembic/env.py`

```python
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

from judicial_archive.core.config import get_settings
from judicial_archive.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

_settings = get_settings()
config.set_main_option("sqlalchemy.url", str(_settings.database_url).replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Nota: Alembic usa el engine síncrono de SQLAlchemy con `psycopg`, no el engine async. Así se evita el `ProactorEventLoop` de Windows y las migraciones funcionan igual en CI (Linux) y desarrollo local.

### 11.8 Comandos de Alembic para B0

```powershell
uv run alembic current
uv run alembic history
```

En B0 no debe haber revisiones. `alembic current` no debe fallar por configuración. Si falla la conexión, el mensaje indicará el problema de base de datos; no se debe continuar con migraciones hasta resolverlo.

A partir de B2:

```powershell
uv run alembic revision --autogenerate -m "descripcion_del_cambio"
uv run alembic upgrade head
uv run alembic downgrade -1
```

Reglas obligatorias:

- Revisar manualmente toda migración autogenerada.
- No editar migraciones ya aplicadas en un entorno compartido.
- Probar `upgrade` y `downgrade` en `sga_test`.
- Nunca borrar datos históricos para hacer pasar una migración.
- Verificar `alembic current` antes de desplegar.

---

## 12. Seguridad base y decisión de autenticación

### 12.1 Decisión

Se implementará autenticación mediante **sesiones opacas del lado del servidor**:

- El cliente recibe una cookie `HttpOnly`, `Secure` en producción y `SameSite=Lax` con el identificador de sesión.
- El identificador es un token aleatorio de al menos 256 bits.
- En PostgreSQL se guarda **solo el hash SHA-256** del token, nunca el token en claro.
- La sesión tiene expiración por inactividad y expiración absoluta.
- Las operaciones de escritura usan protección CSRF de doble envío: cookie CSRF legible por JavaScript + cabecera `X-CSRF-Token`.
- Los tokens no se guardan en `localStorage` ni en `sessionStorage`.
- La revocación es inmediata al eliminar la sesión en base de datos.
- Las sesiones y eventos de autenticación se implementan en B4; B0 solo deja las utilidades y la decisión.

Esta estrategia cumple los requisitos de `AGENTS.md` y evita las desventajas de JWT de larga vida en una aplicación administrativa con información judicial.

### 12.2 Archivo: `backend/src/judicial_archive/core/security.py`

```python
from __future__ import annotations

import hashlib
import hmac
import secrets

import structlog
from pwdlib import PasswordHash

_MIN_TOKEN_BYTES = 32
_MAX_PASSWORD_LENGTH = 1024

_hasher = PasswordHash.recommended()

logger = structlog.get_logger(__name__)


def hash_password(password: str) -> str:
    """Genera un hash Argon2id de la contrasena."""
    if not password:
        msg = "La contrasena no puede estar vacia."
        raise ValueError(msg)
    if len(password) > _MAX_PASSWORD_LENGTH:
        msg = f"La contrasena supera el maximo de {_MAX_PASSWORD_LENGTH} caracteres."
        raise ValueError(msg)
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica una contrasena sin propagar errores de formato del hash."""
    if not password or not password_hash:
        return False
    if len(password) > _MAX_PASSWORD_LENGTH:
        return False
    try:
        return _hasher.verify(password, password_hash)
    except Exception as exc:
        logger.warning("password_verification_failed", error_type=type(exc).__name__)
        return False


def generate_opaque_token(nbytes: int = _MIN_TOKEN_BYTES) -> str:
    """Genera un token opaco criptograficamente seguro."""
    if nbytes < _MIN_TOKEN_BYTES:
        msg = f"El token debe tener al menos {_MIN_TOKEN_BYTES} bytes de entropia."
        raise ValueError(msg)
    return secrets.token_urlsafe(nbytes)


def hash_opaque_token(token: str) -> str:
    """Devuelve el hash SHA-256 hexadecimal de un token de alta entropia."""
    if not token:
        msg = "El token no puede estar vacio."
        raise ValueError(msg)
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_opaque_token(token: str, token_hash: str) -> bool:
    """Compara un token con su hash en tiempo constante."""
    if not token or not token_hash:
        return False
    return hmac.compare_digest(hash_opaque_token(token), token_hash)
```

Notas:

- `PasswordHash.recommended()` usa Argon2id, algoritmo recomendado por OWASP.
- SHA-256 es adecuado para tokens aleatorios de alta entropía; no se usa para contraseñas.
- La comparación de tokens usa `hmac.compare_digest` para evitar comparaciones dependientes del tiempo.
- El límite de 1024 caracteres evita abuso de CPU con contraseñas enormes.
- La implementación de cookies, CSRF, sesiones y bloqueo por intentos pertenece a B4.

### 12.3 Reglas de seguridad que B0 deja preparadas

- CORS explícito, sin comodines con credenciales.
- `TrustedHostMiddleware` con hosts explícitos.
- Validación de configuración insegura en producción.
- Logs con redacción de claves sensibles.
- Errores sin trazas ni datos internos.
- Secretos fuera del repositorio y escaneo con gitleaks.
- Dependencias fijadas con `uv.lock` y CI.
- HTTPS obligatorio en producción (fase de despliegue).
- Cookies seguras cuando se implementen.
- Contraseñas con Argon2id.
- Almacenamiento privado fuera del directorio estático.
- Rate limiting y bloqueo de fuerza bruta en B4/B15.

---

## 13. Tareas en segundo plano: ARQ + Redis

### 13.1 Decisión

Se usa **ARQ** como cola de tareas:

- Es asíncrono y encaja con FastAPI/SQLAlchemy async.
- Es multiplataforma (funciona en Windows sin el problema de `fork` de otras colas).
- Usa Redis, ya disponible.
- Tiene reintentos, timeouts, cron, resultados y observabilidad básica.
- Requiere menos infraestructura y configuración que Celery.

Alternativas descartadas:

| Alternativa | Motivo de descarte |
|---|---|
| Celery | Complejo, problemas en Windows, prefork no ideal para el entorno de desarrollo |
| RQ | Depende de `fork` en el worker; problemático en Windows |
| Dramatiq | Sólido, pero workers síncronos y menos natural con SQLAlchemy async |
| Taskiq | Moderno, pero su plugin Redis exige redis-py 8, incompatible con ARQ y menos maduro |
| Hilos/`BackgroundTasks` de FastAPI | No sobreviven reinicios, no son observables ni idempotentes |

### 13.2 Archivo: `backend/src/judicial_archive/tasks/worker.py`

```python
from __future__ import annotations

from typing import Any, ClassVar

import structlog
from arq.connections import RedisSettings

from judicial_archive.core.config import get_settings
from judicial_archive.core.runtime import configure_event_loop_policy

configure_event_loop_policy()

logger = structlog.get_logger(__name__)
_settings = get_settings()


async def startup(ctx: dict[Any, Any]) -> None:
    logger.info(
        "worker_started",
        queue=_settings.task_queue_name,
        max_jobs=_settings.task_max_jobs,
    )


async def shutdown(ctx: dict[Any, Any]) -> None:
    logger.info("worker_stopped")


async def healthcheck(ctx: dict[Any, Any]) -> dict[str, str]:
    """Tarea minima de diagnostico para que ARQ pueda arrancar en B0."""
    logger.info("worker_healthcheck")
    return {"status": "ok"}


class WorkerSettings:
    """Configuracion de ARQ. Las tareas de negocio se agregan en B10-B14."""

    functions: ClassVar[list[Any]] = [healthcheck]
    on_startup: Any = startup
    on_shutdown: Any = shutdown
    redis_settings: RedisSettings = RedisSettings.from_dsn(str(_settings.redis_url))
    queue_name: str = _settings.task_queue_name
    max_jobs: int = _settings.task_max_jobs
    job_timeout: int = _settings.task_job_timeout_seconds
```

### 13.3 Ejecución del trabajador

Desde `backend/`:

```powershell
uv run arq judicial_archive.tasks.worker.WorkerSettings
```

En desarrollo se puede usar `scripts/worker.ps1`. En producción se ejecutará como servicio systemd separado y con un usuario del sistema sin privilegios.

### 13.4 Reglas para tareas futuras

- Cada tarea debe ser **idempotente** o protegerse contra ejecución duplicada.
- El estado durable del negocio vive en PostgreSQL, no en Redis.
- Redis solo contiene colas, estados temporales, caché y coordinación.
- Los trabajos deben tener timeout, reintentos limitados y registro de error.
- No se guardan documentos judiciales completos en claves Redis.
- Los datos temporales deben tener expiración.
- Redis debe estar protegido por red y autenticación en producción.
- Un fallo de Redis no debe corromper datos de negocio.
- Las tareas registran `job_id`, actor cuando aplique y resultados sin datos sensibles.
- El worker no debe ejecutar código no confiable.

ARQ 0.28 rechaza un worker sin funciones registradas. Por eso B0 registra solo `healthcheck`, una tarea minima de diagnostico que devuelve `{"status": "ok"}`; no se crean tareas de negocio ficticias. Para validar el arranque sin dejar el proceso vivo: `uv run arq judicial_archive.tasks.worker.WorkerSettings --burst`.

---

## 14. Almacenamiento privado de archivos

### 14.1 Decisión

Se usará **almacenamiento privado en el sistema de archivos local**, accedido exclusivamente a través de una interfaz de almacenamiento (`StorageBackend`) que permita sustituirlo por S3/MinIO en el futuro sin cambiar el dominio.

Razones:

- No se requiere un proveedor externo ni coste adicional.
- Los originales no deben estar en el directorio público estático.
- La institución aún no ha definido un proveedor S3.
- La abstracción evita acoplar el dominio al sistema de archivos.
- El volumen inicial (4.401 cajas y documentos asociados) es manejable localmente, sujeto a estimación en B10.

Configuración:

```text
SGA_STORAGE_BACKEND=local
SGA_STORAGE_ROOT=var/storage
```

Reglas:

- `var/storage` vive fuera de `src/`, `static/` y cualquier carpeta servida por el proxy.
- El nombre original del archivo nunca se usa como ruta.
- Se usa un identificador opaco y una estructura por prefijo (por ejemplo, `ab/cd/<uuid>`).
- Se calcula SHA-256 al guardar.
- La escritura es atómica: archivo temporal + `os.replace`.
- La descarga se hace por endpoint autorizado, nunca por URL pública directa.
- Se guardan metadatos en PostgreSQL: hash, tamaño, MIME real, propietario, lote, fecha y referencia.
- Se aplican límites de tamaño y validación de contenido en B9/B10.
- Los respaldos de archivos se coordinan con los de PostgreSQL.
- No se registran contenidos de documentos en logs.

### 14.2 Contrato previsto (se implementa en B9)

El módulo de archivos expondrá una interfaz equivalente a:

```python
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class StoredObject:
    key: str
    size: int
    sha256: str


class StorageBackend(Protocol):
    async def save(self, key: str, source: AsyncIterator[bytes]) -> StoredObject: ...
    async def open(self, key: str) -> AsyncIterator[bytes]: ...
    async def delete(self, key: str) -> None: ...
    def path_for(self, key: str) -> Path: ...
```

No se crea este archivo en B0. Se documenta el contrato para que B9 lo implemente con pruebas de escritura atómica, path traversal, hash y limpieza.

### 14.3 Preparación del directorio

El directorio no se versiona. Se crea cuando B9 implemente el almacenamiento. En B0 solo se verifica que `backend/var/` esté ignorado por Git:

```powershell
git check-ignore -v backend/var/storage
```

Si el comando no devuelve una regla, revisar `.gitignore`.

---

## 15. Infraestructura mínima de API

### 15.1 Archivo: `backend/src/judicial_archive/__init__.py`

```python
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("sga-backend")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["__version__"]
```

### 15.2 Archivo: `backend/src/judicial_archive/api/deps.py`

```python
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.config import Settings
from judicial_archive.db.session import Database


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_database(request: Request) -> Database:
    return cast(Database, request.app.state.database)


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Entrega una sesion por peticion. El servicio define commit/rollback."""
    database = get_database(request)
    async with database.session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
```

Nota: redis-py 5.x no parametriza `Redis`; se usa `Redis` sin `[str]` en anotaciones y `cast`.

Regla de transacciones:

- El repositorio no hace `commit`.
- El servicio de aplicación abre la unidad de trabajo, ejecuta cambios y hace `commit` una sola vez.
- Si algo falla, se hace `rollback` y se propaga el error.
- No se comparte una sesión entre peticiones ni entre tareas.

### 15.3 Archivo: `backend/src/judicial_archive/api/v1/router.py`

```python
from __future__ import annotations

from fastapi import APIRouter

from judicial_archive.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["Salud"])
```

### 15.4 Archivo: `backend/src/judicial_archive/api/v1/health.py`

```python
from __future__ import annotations

import asyncio
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from judicial_archive import __version__
from judicial_archive.api.deps import get_app_settings
from judicial_archive.core.config import Settings
from judicial_archive.db.health import check_database, check_redis
from judicial_archive.db.session import Database

router = APIRouter()


class LivenessStatus(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str
    environment: str


class ComponentHealth(BaseModel):
    status: Literal["ok", "error"]
    latency_ms: float = Field(ge=0)


class ReadinessStatus(BaseModel):
    status: Literal["ok", "error"]
    version: str
    components: dict[str, ComponentHealth]


@router.get(
    "/live",
    response_model=LivenessStatus,
    summary="Verificar que el proceso responde",
)
async def liveness(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> LivenessStatus:
    return LivenessStatus(
        service=settings.app_name,
        version=__version__,
        environment=settings.environment.value,
    )


@router.get(
    "/ready",
    response_model=ReadinessStatus,
    responses={503: {"model": ReadinessStatus}},
    summary="Verificar disponibilidad de dependencias",
)
async def readiness(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ReadinessStatus:
    database: Database | None = getattr(request.app.state, "database", None)
    redis: Redis | None = getattr(request.app.state, "redis", None)
    db_health, redis_health = await asyncio.gather(
        check_database(database, settings.readiness_timeout_seconds),
        check_redis(redis, settings.readiness_timeout_seconds),
    )
    components = {
        "database": ComponentHealth(
            status=db_health.status,
            latency_ms=db_health.latency_ms,
        ),
        "redis": ComponentHealth(
            status=redis_health.status,
            latency_ms=redis_health.latency_ms,
        ),
    }
    is_ready = all(component.status == "ok" for component in components.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessStatus(
        status="ok" if is_ready else "error",
        version=__version__,
        components=components,
    )
```

Diferencias:

- `/live` no consulta dependencias: responde si el proceso está vivo.
- `/ready` consulta PostgreSQL y Redis con timeout y devuelve 503 si alguno falla.
- No se expone el DSN ni el mensaje interno del error.
- Los health checks no requieren autenticación, pero no revelan información sensible.

### 15.5 Archivo: `backend/src/judicial_archive/core/runtime.py`

```python
from __future__ import annotations

import asyncio
import sys


def configure_event_loop_policy() -> None:
    """Usa SelectorEventLoop en Windows para compatibilidad con psycopg async."""
    if sys.platform != "win32":
        return

    from asyncio.windows_events import WindowsSelectorEventLoopPolicy

    asyncio.set_event_loop_policy(  # pyright: ignore[reportDeprecated]
        WindowsSelectorEventLoopPolicy()
    )
```

Nota: psycopg 3 async no funciona con el `ProactorEventLoop` que Windows usa por defecto. Esta función se ejecuta al importar `main.py` y `worker.py`, antes de crear los loops de Uvicorn, pytest-asyncio o ARQ.

### 15.6 Archivo: `backend/src/judicial_archive/main.py`

```python
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import cast

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from starlette.middleware.trustedhost import TrustedHostMiddleware

from judicial_archive import __version__
from judicial_archive.api.v1.router import api_router
from judicial_archive.core.config import Environment, Settings, get_settings
from judicial_archive.core.errors import register_exception_handlers
from judicial_archive.core.logging import configure_logging
from judicial_archive.core.middleware import RequestContextMiddleware
from judicial_archive.core.runtime import configure_event_loop_policy
from judicial_archive.db.session import Database

configure_event_loop_policy()

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = cast(Settings, app.state.settings)
    database = Database(settings)
    redis: Redis = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
        str(settings.redis_url),
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=settings.redis_socket_timeout_seconds,
        socket_timeout=settings.redis_socket_timeout_seconds,
    )
    app.state.database = database
    app.state.redis = redis

    logger.info(
        "application_starting",
        environment=settings.environment.value,
        version=__version__,
    )
    try:
        yield
    finally:
        await redis.aclose()
        await database.dispose()
        logger.info("application_stopped")


def create_app(
    settings: Settings | None = None, *, configure_logs: bool = True
) -> FastAPI:
    resolved_settings = settings or get_settings()
    if configure_logs:
        configure_logging(resolved_settings)

    docs_enabled = resolved_settings.docs_enabled
    app = FastAPI(
        title=resolved_settings.app_name,
        description="API del Sistema de Gestion Documental Judicial.",
        version=__version__,
        debug=(
            resolved_settings.debug
            and resolved_settings.environment is Environment.DEVELOPMENT
        ),
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings

    register_exception_handlers(app)
    app.include_router(api_router, prefix=resolved_settings.api_v1_prefix)

    # El ultimo middleware agregado es el mas externo.
    app.add_middleware(
        RequestContextMiddleware,
        header_name=resolved_settings.request_id_header,
    )
    if resolved_settings.trusted_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=resolved_settings.trusted_hosts,
        )
    if resolved_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                resolved_settings.csrf_header_name,
                resolved_settings.request_id_header,
            ],
            expose_headers=[resolved_settings.request_id_header],
            max_age=600,
        )

    return app
```

Orden de middleware (de interior a exterior):

1. `RequestContextMiddleware`: asigna `request_id`.
2. `TrustedHostMiddleware`: rechaza hosts no permitidos.
3. `CORSMiddleware`: aplica CORS y responde preflight.

El último agregado es el más externo, por eso CORS se agrega al final. Así las respuestas de error también reciben cabeceras CORS.

### 15.7 Archivo: `backend/src/judicial_archive/asgi.py`

```python
from __future__ import annotations

from judicial_archive.main import create_app

app = create_app()
```

Uso:

```powershell
uv run uvicorn judicial_archive.asgi:app --reload --host 127.0.0.1 --port 8000
```

La fábrica `create_app` permite pruebas con configuración inyectada sin depender de variables globales.

### 15.8 Archivos `__init__.py` de paquetes

Todos los paquetes llevan `__init__.py` con docstring breve en español:

```python
"""Paquete de la API HTTP versionada."""
```

Crear en:

- `src/judicial_archive/api/__init__.py`
- `src/judicial_archive/api/v1/__init__.py`
- `src/judicial_archive/core/__init__.py`
- `src/judicial_archive/db/__init__.py`
- `src/judicial_archive/modules/__init__.py`
- `src/judicial_archive/tasks/__init__.py`
- `tests/__init__.py`
- `tests/api/__init__.py`
- `tests/integration/__init__.py`
- `tests/unit/__init__.py`

No dejar `__init__.py` vacíos con lógica de negocio. Solo docstring y, si aplica, exports explícitos.

### 15.9 Contrato inicial de API

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/api/v1/health/live` | No | Proceso vivo |
| GET | `/api/v1/health/ready` | No | PostgreSQL y Redis disponibles |
| GET | `/docs` | No | Swagger UI (solo si `SGA_DOCS_ENABLED=true`) |
| GET | `/openapi.json` | No | Contrato OpenAPI (solo si habilitado) |

No se crean endpoints de negocio en B0. Cualquier ruta adicional debe corresponder a una fase y tener contrato, permisos y pruebas.

---

## 16. Pruebas

### 16.1 Estrategia

- **Unitarias:** configuración, seguridad, paginación, utilidades.
- **API:** health, request-id, formato de errores.
- **Integración:** PostgreSQL y Redis reales, marcadas y desactivadas por defecto.
- **Seguridad:** validaciones de configuración insegura y hash de contraseñas.
- No se usan datos de producción.
- No se usan mocks de la base de datos para probar reglas de persistencia reales en fases posteriores.
- Las pruebas deben ser deterministas y no depender del orden de ejecución.

### 16.2 Archivo: `backend/tests/helpers.py`

```python
from __future__ import annotations

from typing import Any

from judicial_archive.core.config import Environment, Settings


def build_test_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "environment": Environment.TESTING,
        "debug": False,
        "secret_key": "x" * 48,
        "database_url": "postgresql+psycopg://sga_test:sga_test@localhost:5432/sga_test",
        "redis_url": "redis://localhost:6379/15",
        "cors_origins": ["http://localhost:5173"],
        "trusted_hosts": ["testserver", "localhost", "127.0.0.1"],
        "docs_enabled": True,
        "log_json": False,
        "session_cookie_secure": False,
        "storage_root": "var/storage",
    }
    values.update(overrides)
    return Settings.model_validate(values)
```

### 16.3 Archivo: `backend/tests/conftest.py`

```python
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from judicial_archive.main import create_app
from tests.helpers import build_test_settings


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app(build_test_settings(), configure_logs=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as http_client:
        yield http_client
```

### 16.4 Archivo: `backend/tests/unit/test_config.py`

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from judicial_archive.core.config import Environment, Settings
from tests.helpers import build_test_settings


def test_valid_settings() -> None:
    settings = build_test_settings()
    assert settings.environment is Environment.TESTING
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.cors_origins == ["http://localhost:5173"]


def test_short_secret_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        build_test_settings(secret_key="corto")


def test_api_prefix_must_start_with_slash() -> None:
    with pytest.raises(ValidationError):
        build_test_settings(api_v1_prefix="api/v1")


def test_api_prefix_must_not_end_with_slash() -> None:
    with pytest.raises(ValidationError):
        build_test_settings(api_v1_prefix="/api/v1/")


def test_production_accepts_secure_configuration() -> None:
    settings = build_test_settings(
        environment=Environment.PRODUCTION,
        debug=False,
        docs_enabled=False,
        log_json=True,
        session_cookie_secure=True,
        cors_origins=["https://sga.institucion.gob"],
        trusted_hosts=["sga.institucion.gob"],
    )
    assert settings.environment is Environment.PRODUCTION


@pytest.mark.parametrize(
    "overrides",
    [
        {"debug": True},
        {"docs_enabled": True},
        {"log_json": False},
        {"session_cookie_secure": False},
        {"cors_origins": ["*"]},
        {"trusted_hosts": ["testserver"]},
    ],
)
def test_production_rejects_insecure_configuration(
    overrides: dict[str, object],
) -> None:
    base: dict[str, object] = {
        "environment": Environment.PRODUCTION,
        "debug": False,
        "docs_enabled": False,
        "log_json": True,
        "session_cookie_secure": True,
        "cors_origins": ["https://sga.institucion.gob"],
        "trusted_hosts": ["sga.institucion.gob"],
    }
    base.update(overrides)
    with pytest.raises(ValidationError):
        build_test_settings(**base)


def test_comma_separated_environment_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SGA_ENVIRONMENT", "testing")
    monkeypatch.setenv("SGA_SECRET_KEY", "y" * 48)
    monkeypatch.setenv(
        "SGA_DATABASE_URL",
        "postgresql+psycopg://sga_test:sga_test@localhost:5432/sga_test",
    )
    monkeypatch.setenv("SGA_REDIS_URL", "redis://localhost:6379/15")
    monkeypatch.setenv(
        "SGA_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )
    monkeypatch.setenv("SGA_TRUSTED_HOSTS", "localhost,127.0.0.1,testserver")
    monkeypatch.setenv("SGA_DOCS_ENABLED", "true")
    monkeypatch.setenv("SGA_LOG_JSON", "false")
    monkeypatch.setenv("SGA_SESSION_COOKIE_SECURE", "false")

    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]

    assert settings.cors_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    assert settings.trusted_hosts == ["localhost", "127.0.0.1", "testserver"]
```

Nota: `Settings(_env_file=None)` desactiva la lectura del archivo `.env` durante la prueba. Las variables se inyectan con `monkeypatch` y se limpian automáticamente. En Pylance strict se usa `# pyright: ignore[reportCallIssue]`.

### 16.5 Archivo: `backend/tests/unit/test_security.py`

```python
from __future__ import annotations

import pytest

from judicial_archive.core.security import (
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_opaque_token,
    verify_password,
)


def test_password_hash_and_verify() -> None:
    password = "Contrasena-Segura-2026"
    password_hash = hash_password(password)

    assert password_hash != password
    assert password not in password_hash
    assert verify_password(password, password_hash) is True
    assert verify_password("otra-contrasena", password_hash) is False


def test_empty_password_is_rejected() -> None:
    with pytest.raises(ValueError, match="no puede estar vacia"):
        hash_password("")


def test_verify_password_with_invalid_hash_returns_false() -> None:
    assert verify_password("cualquiera", "hash-invalido") is False


def test_opaque_token_generation_and_hash() -> None:
    token = generate_opaque_token()
    other = generate_opaque_token()

    assert token != other
    assert len(token) >= 43
    assert hash_opaque_token(token) == hash_opaque_token(token)
    assert hash_opaque_token(token) != hash_opaque_token(other)
    assert verify_opaque_token(token, hash_opaque_token(token)) is True
    assert verify_opaque_token(other, hash_opaque_token(token)) is False


def test_token_requires_minimum_entropy() -> None:
    with pytest.raises(ValueError, match="al menos 32 bytes"):
        generate_opaque_token(16)
```

### 16.6 Archivo: `backend/tests/unit/test_pagination.py`

```python
from __future__ import annotations

import pytest

from judicial_archive.core.errors import InvalidParameterError
from judicial_archive.core.pagination import (
    MAX_PAGE_SIZE,
    Page,
    PageParams,
    SortOrder,
    build_sort_params,
)


def test_page_params_offset_and_limit() -> None:
    params = PageParams(page=3, page_size=25)

    assert params.offset == 50
    assert params.limit == 25


def test_page_build_with_results() -> None:
    params = PageParams(page=2, page_size=10)

    page = Page[int].build([1, 2, 3], total=23, params=params)

    assert page.items == [1, 2, 3]
    assert page.total == 23
    assert page.pages == 3
    assert page.has_next is True
    assert page.has_previous is True


def test_page_build_empty() -> None:
    params = PageParams(page=1, page_size=MAX_PAGE_SIZE)

    page = Page[int].build([], total=0, params=params)

    assert page.pages == 0
    assert page.has_next is False
    assert page.has_previous is False


def test_sort_field_must_be_allowed() -> None:
    with pytest.raises(InvalidParameterError):
        build_sort_params(
            "password", SortOrder.ASC, allowed_fields=frozenset({"number"})
        )


def test_sort_field_allowed() -> None:
    params = build_sort_params(
        "number", SortOrder.DESC, allowed_fields=frozenset({"number"})
    )

    assert params.sort_by == "number"
    assert params.order is SortOrder.DESC
```

### 16.7 Archivo: `backend/tests/unit/test_db_health.py`

```python
from __future__ import annotations

from typing import Any, cast

from judicial_archive.db.health import check_database, check_redis
from judicial_archive.db.session import Database


class _FakeConnection:
    async def __aenter__(self) -> _FakeConnection:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def execute(self, statement: object) -> None:
        return None


class _FakeEngine:
    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    def connect(self) -> _FakeConnection:
        if self._fail:
            raise RuntimeError("conexion simulada fallida")
        return _FakeConnection()


class _FakeDatabase:
    def __init__(self, *, fail: bool = False) -> None:
        self.engine = _FakeEngine(fail=fail)


class _FakeRedis:
    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    async def ping(self, **kwargs: Any) -> bool:
        if self._fail:
            raise RuntimeError("redis simulado fallido")
        return True


async def test_database_health_ok() -> None:
    health = await check_database(cast(Database, _FakeDatabase()), 1.0)

    assert health.status == "ok"
    assert health.latency_ms >= 0


async def test_database_health_failure() -> None:
    health = await check_database(cast(Database, _FakeDatabase(fail=True)), 1.0)

    assert health.status == "error"
    assert health.latency_ms >= 0


async def test_redis_health_ok() -> None:
    health = await check_redis(_FakeRedis(), 1.0)

    assert health.status == "ok"


async def test_redis_health_failure() -> None:
    health = await check_redis(_FakeRedis(fail=True), 1.0)

    assert health.status == "error"
```

### 16.8 Archivo: `backend/tests/unit/test_session.py`

```python
from __future__ import annotations

from judicial_archive.db.session import Database
from tests.helpers import build_test_settings


async def test_database_is_created_and_disposed_without_connecting() -> None:
    database = Database(build_test_settings())

    assert database.engine is not None
    async with database.session() as session:
        assert session is not None

    await database.dispose()
```

### 16.9 Archivo: `backend/tests/api/test_health.py`

```python
from __future__ import annotations

from httpx import AsyncClient


async def test_liveness_returns_ok(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health/live",
        headers={"X-Request-ID": "req-12345678"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["environment"] == "testing"
    assert response.headers["X-Request-ID"] == "req-12345678"


async def test_request_id_is_generated_when_missing(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert len(response.headers["X-Request-ID"]) == 32


async def test_unsafe_request_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health/live",
        headers={"X-Request-ID": "<script>alert(1)</script>"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "<script>alert(1)</script>"
    assert len(response.headers["X-Request-ID"]) == 32


async def test_readiness_without_dependencies_returns_503(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["components"]["database"]["status"] == "error"
    assert body["components"]["redis"]["status"] == "error"
```

### 16.10 Archivo: `backend/tests/api/test_errors.py`

```python
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from judicial_archive.core.errors import NotFoundError
from judicial_archive.main import create_app
from tests.helpers import build_test_settings


@pytest_asyncio.fixture
async def error_client() -> AsyncIterator[AsyncClient]:
    app = create_app(build_test_settings(), configure_logs=False)

    @app.get("/_test/not-found")
    async def _raise_not_found() -> None:
        raise NotFoundError("La caja solicitada no existe.")

    @app.get("/_test/validation")
    async def _validate(value: int) -> dict[str, int]:
        return {"value": value}

    @app.get("/_test/unhandled")
    async def _raise_unhandled() -> None:
        raise RuntimeError("detalle interno que no debe salir")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as http_client:
        yield http_client


async def test_app_error_uses_standard_envelope(error_client: AsyncClient) -> None:
    response = await error_client.get("/_test/not-found")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["message"] == "La caja solicitada no existe."
    assert body["error"]["request_id"]


async def test_validation_error_does_not_echo_input(error_client: AsyncClient) -> None:
    response = await error_client.get("/_test/validation", params={"value": "secreto"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "secreto" not in response.text
    assert body["error"]["details"]["errors"]


async def test_unhandled_error_hides_internal_detail(error_client: AsyncClient) -> None:
    response = await error_client.get("/_test/unhandled")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "Error interno del servidor."
    assert "detalle interno" not in response.text
```

Nota: `ASGITransport(..., raise_app_exceptions=False)` es necesario para probar el sobre de error 500. Starlette vuelve a lanzar la excepción después de enviar la respuesta para que el servidor la registre; sin esa opción, `httpx` propagaría la excepción y la prueba fallaría.

### 16.11 Archivo: `backend/tests/integration/test_dependencies.py`

```python
from __future__ import annotations

import os

import pytest
from redis.asyncio import Redis
from sqlalchemy import text

from judicial_archive.db.session import Database
from tests.helpers import build_test_settings

_RUN_INTEGRATION = os.getenv("RUN_INTEGRATION") == "1"
_INTEGRATION_REASON = "Definir RUN_INTEGRATION=1 y disponer de PostgreSQL/Redis."


@pytest.mark.integration
@pytest.mark.skipif(not _RUN_INTEGRATION, reason=_INTEGRATION_REASON)
async def test_postgresql_connection() -> None:
    settings = build_test_settings(
        database_url=os.getenv("TEST_DATABASE_URL")
        or os.getenv(
            "SGA_DATABASE_URL",
            "postgresql+psycopg://sga_test:sga_test@localhost:5432/sga_test",
        )
    )
    database = Database(settings)
    try:
        async with database.engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
    finally:
        await database.dispose()


@pytest.mark.integration
@pytest.mark.skipif(not _RUN_INTEGRATION, reason=_INTEGRATION_REASON)
async def test_redis_connection() -> None:
    settings = build_test_settings(
        redis_url=os.getenv("TEST_REDIS_URL")
        or os.getenv("SGA_REDIS_URL", "redis://localhost:6379/15")
    )
    redis: Redis = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
        str(settings.redis_url),
        encoding="utf-8",
        decode_responses=True,
    )
    try:
        assert await redis.ping() is True  # pyright: ignore[reportUnknownMemberType]
    finally:
        await redis.aclose()
```

Ejecución:

```powershell
$env:RUN_INTEGRATION = "1"
uv run pytest -m integration
Remove-Item Env:RUN_INTEGRATION
```

### 16.12 Comandos de prueba

Desde `backend/`:

```powershell
uv run pytest
uv run pytest tests/unit
uv run pytest tests/api
uv run pytest -m integration
uv run pytest --cov=judicial_archive --cov-report=html
```

Cobertura inicial mínima: 60 % en B0, porque el esqueleto incluye módulos que se prueban en fases posteriores. El objetivo es 75 % al cierre de B2 y 85 % al cierre de B16. No se persiguen porcentajes con pruebas triviales; se priorizan reglas y flujos.

### 16.13 Reglas de pruebas

- Cada defecto corregido debe tener una prueba que lo reproduzca.
- Las pruebas no debe depender del orden de ejecución.
- No se usan fechas actuales sin control; cuando se necesiten, se inyecta un reloj.
- No se usan datos personales reales.
- Los archivos de prueba deben ser sintéticos y pequeños.
- Las pruebas de integración requieren servicios reales y se marcan.
- No se silencian errores con `except` genéricos en producción ni en pruebas.
- Las pruebas de seguridad se marcan con `@pytest.mark.security` cuando correspondan.

---

## 17. Calidad: Ruff, mypy, pre-commit y CI

### 17.1 Ruff

Ruff hace linting y formato. Configuración en `pyproject.toml` (sección 6.2).

Comandos:

```powershell
uv run ruff check .
uv run ruff check --fix .
uv run ruff format .
uv run ruff format --check .
```

Reglas:

- No deshabilitar reglas globalmente sin justificación en el PR.
- Los ignores puntuales usan `# noqa: <codigo>` con explicación cuando no es obvio.
- El formato no se discute en revisión; lo aplica Ruff.
- No reformatear archivos completos sin necesidad en un PR funcional.

### 17.2 mypy

Configuración estricta en `pyproject.toml` (sección 6.2).

Comandos:

```powershell
uv run mypy src tests
```

Reglas:

- No usar `Any` sin justificación.
- No usar `# type: ignore` sin código de error y motivo.
- Los modelos SQLAlchemy y Pydantic se escriben con tipos explícitos.
- Los esquemas de entrada/salida no se mezclan con modelos ORM.
- Los módulos nuevos deben pasar mypy desde su creación.

### 17.3 Archivo: `.pre-commit-config.yaml` (raíz)

```yaml
default_stages: [pre-commit]
fail_fast: false

repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: check-yaml
      - id: check-toml
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-merge-conflict
      - id: check-added-large-files
        args: [--maxkb=1024]
      - id: debug-statements
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.17.2
    hooks:
      - id: ruff-check
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1
    hooks:
      - id: gitleaks

  - repo: local
    hooks:
      - id: mypy
        name: mypy (backend)
        entry: uv run --directory backend mypy src tests
        language: system
        pass_filenames: false
        files: ^backend/.*\.py$
        stages: [pre-commit]
```

Instalación:

```powershell
uv tool install pre-commit
pre-commit install
pre-commit run --all-files
```

Alternativa sin instalar globalmente:

```powershell
cd backend
uv run pre-commit install --config ../.pre-commit-config.yaml
uv run pre-commit run --all-files --config ../.pre-commit-config.yaml
```

Notas:

- `gitleaks` bloquea commits con secretos detectados.
- mypy se ejecuta sobre todo el backend, no solo archivos modificados, para evitar falsos negativos por dependencias.
- Si un hook falla, corregir y volver a ejecutar; no usar `--no-verify`.

### 17.4 Archivo: `.gitleaks.toml` (raíz)

```toml
[extend]
useDefault = true

[allowlist]
description = "Excepciones controladas para ejemplos sin secretos reales"
paths = [
  '''^docs/.*\.md$''',
  '''^backend/\.env\.example$''',
  '''^backend/tests/.*''',
]
regexes = [
  '''CAMBIAR_CONTRASENA_DEV''',
  '''SGA_SECRET_KEY=\s*$''',
]
```

Justificación:

- `docs/` puede contener ejemplos de configuración.
- `.env.example` contiene marcadores, no secretos.
- Las pruebas usan valores sintéticos.
- Cualquier excepción adicional requiere revisión y justificación; no ampliar la allowlist sin motivo.

### 17.5 Archivo: `.github/workflows/ci.yml` (raíz)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  backend:
    name: Backend (Python 3.12)
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:18-alpine
        env:
          POSTGRES_USER: sga
          POSTGRES_PASSWORD: sga_ci
          POSTGRES_DB: sga_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U sga -d sga_test"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:8-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    defaults:
      run:
        working-directory: backend

    env:
      SGA_ENVIRONMENT: testing
      SGA_DEBUG: "false"
      SGA_SECRET_KEY: ci-secret-key-with-at-least-thirty-two-characters
      SGA_DATABASE_URL: postgresql+psycopg://sga:sga_ci@localhost:5432/sga_test
      SGA_REDIS_URL: redis://localhost:6379/15
      SGA_CORS_ORIGINS: http://localhost:5173
      SGA_TRUSTED_HOSTS: localhost,127.0.0.1,testserver
      SGA_DOCS_ENABLED: "true"
      SGA_LOG_JSON: "false"
      SGA_SESSION_COOKIE_SECURE: "false"
      RUN_INTEGRATION: "1"

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Instalar uv
        uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true

      - name: Instalar Python 3.12
        run: uv python install 3.12

      - name: Instalar dependencias
        run: uv sync --frozen

      - name: Verificar formato
        run: uv run ruff format --check .

      - name: Lint
        run: uv run ruff check .

      - name: Tipado
        run: uv run mypy src tests

      - name: Pruebas
        run: uv run pytest
```

Notas:

- `astral-sh/setup-uv@v7` es la etiqueta mayor existente verificada en el remoto; no usar `@v10`, que no existe.
- Docker solo se usa en el runner de CI; el proyecto no lo requiere.
- El lock debe estar actualizado; `uv sync --frozen` falla si no coincide.
- El secreto de CI es ficticio y no sirve fuera del runner.
- Si el repositorio no está en GitHub, replicar los mismos comandos en el CI institucional.

### 17.6 Scripts de verificación

#### Archivo: `backend/scripts/check.ps1`

```powershell
$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][scriptblock] $Command
    )

    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo en '$Name' con codigo $LASTEXITCODE."
    }
}

$backendRoot = Split-Path -Parent $PSScriptRoot
Push-Location $backendRoot
try {
    Invoke-Step "Formato" { uv run ruff format --check . }
    Invoke-Step "Lint" { uv run ruff check . }
    Invoke-Step "Tipos" { uv run mypy src tests }
    Invoke-Step "Pruebas" { uv run pytest }
    Write-Host "Todas las comprobaciones pasaron." -ForegroundColor Green
}
finally {
    Pop-Location
}
```

Uso:

```powershell
cd backend
.\scripts\check.ps1
```

Si PowerShell bloquea scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

#### Archivo: `backend/scripts/dev.ps1`

```powershell
$ErrorActionPreference = "Stop"
$backendRoot = Split-Path -Parent $PSScriptRoot
Push-Location $backendRoot
try {
    uv run uvicorn judicial_archive.asgi:app --reload --host 127.0.0.1 --port 8000
}
finally {
    Pop-Location
}
```

#### Archivo: `backend/scripts/worker.ps1`

```powershell
$ErrorActionPreference = "Stop"
$backendRoot = Split-Path -Parent $PSScriptRoot
Push-Location $backendRoot
try {
    uv run arq judicial_archive.tasks.worker.WorkerSettings
}
finally {
    Pop-Location
}
```

---

## 18. Documentación del repositorio

### 18.1 Archivo: `README.md` (raíz)

Contenido recomendado completo:

````markdown
# SGA --- Sistema de Gestión Documental Judicial

Sistema web para administrar el archivo central judicial: cajas,
expedientes, documentos administrativos, ubicaciones físicas,
digitalización, movimientos, préstamos, auditoría e inventario.

El backend se construye primero. El frontend se incorpora cuando existan
contratos de API probados.

## Estado

Fase actual: **B0 --- Preparación del proyecto**.

El repositorio contiene la base técnica del backend: configuración,
calidad, pruebas, salud y documentación de decisiones. No contiene aún
modelos de negocio ni endpoints funcionales.

## Stack

- Python 3.12, uv.
- FastAPI, Uvicorn, Pydantic v2.
- PostgreSQL 18, SQLAlchemy 2.1 async, psycopg 3, Alembic.
- Redis 7.4+, ARQ.
- Ruff, mypy, pytest, pre-commit, GitHub Actions.
- Frontend previsto: React, TypeScript, Vite, Tailwind CSS.

## Requisitos

- Windows 10/11, Linux o macOS.
- Python 3.12 gestionado por uv.
- PostgreSQL 18 con las bases `sga_dev` y `sga_test`.
- Redis 7.4 o superior.
- Git.

Ver `docs/instalacion-desarrollo.md` para el procedimiento detallado.

## Inicio rápido

```powershell
git clone <URL_DEL_REPOSITORIO> sga
Set-Location sga
uv python install 3.12
Set-Location backend
uv sync
Copy-Item .env.example .env
# Editar .env con credenciales locales reales.
uv run alembic upgrade head
uv run uvicorn judicial_archive.asgi:app --reload
```

Abrir `http://127.0.0.1:8000/docs`.

## Comandos

```powershell
cd backend
uv sync
uv run uvicorn judicial_archive.asgi:app --reload
uv run arq judicial_archive.tasks.worker.WorkerSettings
uv run alembic current
uv run alembic upgrade head
uv run ruff format .
uv run ruff check .
uv run mypy src tests
uv run pytest
.\scripts\check.ps1
```

## Estructura

```text
backend/
├── src/judicial_archive/   Código del backend
│   ├── core/               Configuración, errores, logging, seguridad
│   ├── db/                 Motor, sesiones y salud
│   ├── api/                Dependencias y rutas versionadas
│   ├── modules/            Dominio (se crea por fase)
│   └── tasks/              Worker ARQ
├── tests/                  Unitarias, API e integración
├── alembic/                Migraciones
└── scripts/                Utilidades de desarrollo
docs/                       Documentación y ADR
```

## Documentación

- `docs/arquitectura.md`
- `docs/api.md`
- `docs/instalacion-desarrollo.md`
- `docs/pruebas.md`
- `docs/seguridad.md`
- `docs/pendientes-de-validacion.md`
- `docs/decisiones/ADR-*.md`
- `docs/AGENTS.md` (reglas maestras)
- `docs/phases/GUIA_DESARROLLO_FASES_SGA.md`

## Seguridad

No se aceptan secretos, documentos judiciales reales, volcados de base de
datos ni datos personales en el repositorio. Los documentos se almacenan
en un volumen privado y se sirven mediante endpoints autorizados.

## Licencia

Uso institucional. Pendiente de definición formal.
````

### 18.2 Archivo: `docs/arquitectura.md`

Estructura mínima:

````markdown
# Arquitectura del backend

## 1. Principios
- Backend primero, contratos antes que pantallas.
- Reglas de negocio independientes de FastAPI; los modelos ORM se aíslan
  dentro de cada módulo.
- Una sola fuente de verdad: PostgreSQL.
- Redis no almacena verdad de negocio.
- Seguridad y auditoría desde el diseño.
- Módulos por capacidad de negocio, no por tipo técnico.

## 2. Capas
HTTP (api/) -> servicio (modules/*/service.py) -> repositorio
(modules/*/repository.py) -> modelos (modules/*/models.py) -> PostgreSQL.

- `api/`: valida transporte, aplica dependencias, traduce errores.
- `service/`: reglas, transacciones, permisos y auditoría.
- `repository/`: consultas y persistencia; no decide reglas.
- `models/`: mapeo ORM; sin lógica HTTP.
- `schemas/`: contratos Pydantic; no se exponen modelos ORM.

## 3. Dependencias permitidas
- `api` puede importar `core`, `db` y `modules`.
- `modules` puede importar `core` y `db`, nunca `api`.
- `db` puede importar `core`, nunca `modules`.
- `core` no importa `api`, `db` ni `modules`.
- `tasks` puede importar `core`, `db` y servicios de módulos.
- Evitar dependencias circulares entre módulos.

## 4. Flujo de una petición
1. Middleware asigna `request_id` y valida host.
2. CORS responde preflight.
3. Router resuelve endpoint y dependencias.
4. Se valida entrada con Pydantic.
5. Servicio verifica permisos y reglas.
6. Repositorio consulta o persiste.
7. Servicio confirma la transacción.
8. Se devuelve el esquema de respuesta.
9. Un error se traduce al sobre uniforme con `request_id`.

## 5. Transacciones
- Una sesión por petición.
- El servicio define la unidad de trabajo.
- `commit` único al finalizar; `rollback` ante error.
- Operaciones que afectan caja, ubicación, préstamo, importación o
  auditoría son atómicas.
- No se comparte sesión entre peticiones ni tareas.

## 6. Módulos previstos
auth, users, courts, locations, boxes, case_files,
administrative_documents, search, files, imports, ocr, loans, movements,
qr, inventory, audit, reports.

Cada módulo se crea en su fase, con modelos, migración, permisos y
pruebas. No se crean carpetas vacías.

## 7. Tareas asíncronas
ARQ + Redis para OCR, importaciones y exportaciones. Las tareas son
idempotentes, observables y con timeout. El estado durable vive en
PostgreSQL.

## 8. Almacenamiento
Interfaz `StorageBackend`; implementación local privada en B0/B9 y
posible S3/MinIO futuro. El nombre original no se usa como ruta. Hash
SHA-256 y escritura atómica.

## 9. Observabilidad
Logs JSON con `request_id`, nivel, evento y duración. Redacción de
secretos. Errores uniformes sin trazas en producción. `/live` y `/ready`.

## 10. Decisiones
Ver `docs/decisiones/ADR-0001` a `ADR-0011`.
````

### 18.3 Archivo: `docs/instalacion-desarrollo.md`

Contenido mínimo:

````markdown
# Instalación y desarrollo

## 1. Requisitos
- Windows 10/11 con PowerShell 5.1 o superior.
- Git 2.40+.
- PostgreSQL 18 con `psql` en PATH.
- Redis 7.4+ (servicio o contenedor local).
- uv 0.8+.

## 2. Clonar
git clone <URL> sga
cd sga

## 3. Python y dependencias
uv python install 3.12
cd backend
uv python pin 3.12
uv sync

## 4. Bases de datos
Abrir psql como administrador:
psql -U postgres

CREATE ROLE sga_dev LOGIN PASSWORD 'CAMBIAR_CONTRASENA_DEV';
CREATE DATABASE sga_dev OWNER sga_dev ENCODING 'UTF8';
CREATE ROLE sga_test LOGIN PASSWORD 'CAMBIAR_CONTRASENA_TEST';
CREATE DATABASE sga_test OWNER sga_test ENCODING 'UTF8';

Verificar:
psql -U sga_dev -d sga_dev -c "SELECT current_database(), current_user;"
psql -U sga_test -d sga_test -c "SELECT current_database(), current_user;"

## 5. Redis
redis-cli ping
# Esperado: PONG

En Windows, si Redis corre como servicio:
Get-Service *redis*

## 6. Configuración
Copy-Item .env.example .env
Editar .env. Generar secreto:
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"

No versionar .env.

## 7. Migraciones
uv run alembic upgrade head
uv run alembic current

## 8. Ejecutar
uv run uvicorn judicial_archive.asgi:app --reload
# http://127.0.0.1:8000/api/v1/health/live
# http://127.0.0.1:8000/api/v1/health/ready
# http://127.0.0.1:8000/docs

## 9. Worker
uv run arq judicial_archive.tasks.worker.WorkerSettings

## 10. Calidad
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
.\scripts\check.ps1

## 11. Problemas frecuentes
- `password authentication failed`: revisar usuario, base y `pg_hba.conf`.
- `database does not exist`: crear la base y ejecutar migraciones.
- `Connection refused` en Redis: iniciar el servicio y verificar el puerto.
- `port already in use`: detener el proceso anterior o cambiar el puerto.
- `UnicodeDecodeError`: guardar archivos en UTF-8 sin BOM.
- `ruff` no encontrado: ejecutar con `uv run` desde `backend/`.
- mypy no encuentra el paquete: `uv sync` y ejecutar dentro de `backend/`.
- Pylance marca `is unknown import symbol`: eliminar stubs viejos en `typings/` (Pylance los usa antes que el paquete real) y seleccionar `backend/.venv`.
- Pylance marca `Expected no type arguments for class "Redis"`: redis-py 5.x no es genérico; usar `Redis`, no `Redis[str]`.
- Pylance marca `ORJSONResponse is deprecated`: usar `JSONResponse`; FastAPI 0.161 serializa con Pydantic.
- Pylance marca `Settings()` con argumentos faltantes: usar `# pyright: ignore[reportCallIssue]`, no `# type: ignore`.
- Alembic falla con `ProactorEventLoop`: usar el engine síncrono de `env.py` o `configure_event_loop_policy()` en Windows.
- ARQ falla con `at least one function or cron_job must be registered`: registrar al menos `healthcheck`.
- PowerShell bloquea scripts: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## 12. Flujo diario
1. git switch -c feat/<tema>
2. Implementar con pruebas.
3. .\scripts\check.ps1
4. Revisar `git diff`.
5. Commit convencional.
6. Push y PR.
````

### 18.4 Archivo: `docs/pruebas.md`

Contenido mínimo:

````markdown
# Pruebas

## Pirámide
- Unitarias: reglas, configuración, seguridad, paginación.
- API: contratos, errores, cabeceras, autenticación.
- Integración: PostgreSQL y Redis reales.
- Seguridad: permisos, CSRF, fuerza bruta, archivos (fases posteriores).
- E2E: frontend y flujos completos (fases F).

## Comandos
cd backend
uv run pytest
uv run pytest tests/unit
uv run pytest tests/api
uv run pytest -m integration
uv run pytest --cov=judicial_archive --cov-report=html

## Integración
$env:RUN_INTEGRATION = "1"
uv run pytest -m integration
Remove-Item Env:RUN_INTEGRATION

Requiere PostgreSQL y Redis. Usa `sga_test` y la base Redis 15.

## Datos
- Sintéticos.
- NUC `00001` y `2022-102-00001`.
- Códigos 589 y 107 repetidos.
- Fechas parciales y desconocidas.
- Documentos sin ubicación.
- Archivos pequeños de prueba.

## Reglas
- Toda corrección incluye prueba de regresión.
- Sin dependencia del orden.
- Sin fechas reales no controladas.
- Sin secretos ni datos personales.
- Sin mocks de PostgreSQL para reglas de persistencia.
- Cobertura objetivo: 60 % en B0, 75 % al cierre de B2 y 85 % al cierre de B16.

## Criterio de aceptación
Todas las pruebas pasan en local y CI; las de integración se ejecutan en
CI con servicios reales.
````

### 18.5 Archivo: `docs/seguridad.md`

Contenido mínimo:

````markdown
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
````

### 18.6 Archivo: `docs/pendientes-de-validacion.md`

````markdown
# Pendientes de validación

Cada punto requiere decisión humana antes de convertirse en regla rígida.

| # | Tema | Pregunta | Impacto | Fase | Estado |
|---|---|---|---|---|---|
| 1 | Códigos de tribunales | ¿589 y 107 son colisiones válidas o datos a corregir? | Catálogo y unicidad | B5 | Pendiente |
| 2 | Formatos NUC | ¿Qué patrones aplican por tribunal y época? | Validación y búsqueda | B1/B8 | Pendiente |
| 3 | Sentencias | ¿Semántica de `000-0000-SSSS-0000`, SADM, SPEN, RPE? | Validación y búsqueda | B1/B8 | Pendiente |
| 4 | Inmutabilidad de caja | ¿Cuándo quedan fijos tipo, tribunal y año? | Edición y corrección | B1/B6 | Pendiente |
| 5 | Préstamos | ¿Caja completa, expediente o ambos? | Modelo y flujo | B1/B11 | Pendiente |
| 6 | Almacenamiento | ¿Volumen, retención y respaldo de originales? | B9 y operación | B9 | Pendiente |
| 7 | OCR manuscrito | ¿Motor, precisión esperada y revisión? | B10 | B10 | Pendiente |
| 8 | Modelo físico | ¿Dimensiones y orientación para 2D/3D? | F6 | F6 | Pendiente |
| 9 | Fechas parciales | ¿Representación uniforme de año/mes? | Modelo y reportes | B1 | Pendiente |
| 10 | Retención | ¿Baja lógica, conservación y purga? | Auditoría y datos | B13 | Pendiente |
| 11 | Alertas | ¿Canales, periodicidad y destinatarios? | B11/B12 | Pendiente |
| 12 | Identidad | ¿Alta, recuperación, caducidad, 2FA? | B4 | Pendiente |
| 13 | Numeración | ¿Cuándo se asigna el número y cómo se anula? | B6 | Pendiente |
| 14 | Numeración de fases | `AGENTS.md` usa B0-B15/F0-F10; la guía maestra B0-B16/F1-F11 | Trazabilidad documental | B0 | Resuelto: prevalece la guía maestra; corregir `AGENTS.md` |
| 15 | Licencia | ¿Licencia institucional o privada? | Publicación | B0 | Pendiente |

## Nota sobre la numeración de fases

La fase B0 es idéntica en ambos documentos. A partir de B1, la guía
maestra agrega una fase y desplaza los números. Este documento y el
código usarán la guía maestra. La discrepancia debe corregirse en
`AGENTS.md` mediante una tarea documental separada, sin alterar el
contenido de negocio.
````

### 18.7 ADR-0001 a ADR-0011

Cada ADR usa la plantilla: estado, fecha, contexto, decisión,
alternativas, consecuencias y referencias. Crear los once archivos.

#### `docs/decisiones/ADR-0001-python-y-uv.md`

```markdown
# ADR-0001 --- Python 3.12, uv y layout src

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
El backend requiere tipado estricto, dependencias reproducibles y
compatibilidad con Windows y Linux. El entorno tiene Python 3.10.8, pero
FastAPI, SQLAlchemy y las herramientas modernas se benefician de 3.12.

## Decisión
Usar Python 3.12 gestionado por uv, layout `src/`, paquete
`judicial_archive` y distribución `sga-backend`. Versionar `uv.lock`.

## Alternativas
- Python 3.10 del sistema: menor vida útil y sin ventajas.
- Poetry: válido, pero uv es más rápido y ya está instalado.
- Layout plano: expone el directorio de trabajo en importaciones.

## Consecuencias
- Reproducibilidad y velocidad.
- Requiere instalar 3.12 con uv en cada entorno.
- El paquete debe instalarse con `uv sync`.

## Referencias
`pyproject.toml`, `docs/instalacion-desarrollo.md`.
```

#### `docs/decisiones/ADR-0002-arquitectura-modular.md`

```markdown
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
```

#### `docs/decisiones/ADR-0003-persistencia.md`

```markdown
# ADR-0003 --- PostgreSQL, SQLAlchemy async y Alembic

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
La integridad, la concurrencia y la trazabilidad son requisitos. Se
necesitan transacciones, restricciones y migraciones revisables.

## Decisión
PostgreSQL 18 como fuente de verdad. SQLAlchemy 2.1 async con psycopg 3.
Alembic para todo cambio de esquema. Sesión por petición; el servicio
define la unidad de trabajo.

## Alternativas
- SQLAlchemy sync: válido, pero bloquea el event loop o exige hilos.
- asyncpg directo: rápido, pero pierde el ORM y la integración Alembic.
- DDL manual: prohibido por trazabilidad.

## Consecuencias
- Transacciones y restricciones sólidas.
- Mayor complejidad async en pruebas y sesiones.
- Toda migración se revisa y se prueba en base vacía y representativa.

## Referencias
`db/session.py`, `alembic/env.py`, `AGENTS.md` sección 12.2.
```

#### `docs/decisiones/ADR-0004-autenticacion.md`

```markdown
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
```

#### `docs/decisiones/ADR-0005-tareas-segundo-plano.md`

```markdown
# ADR-0005 --- ARQ sobre Redis para tareas asíncronas

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
OCR, importaciones y exportaciones no deben bloquear HTTP ni depender de
hilos del proceso web. El entorno es Windows y Linux, con Redis ya
instalado.

## Decisión
ARQ 0.28 con Redis 5.2-6. Worker separado, tareas idempotentes,
timeout y reintentos limitados. Estado durable en PostgreSQL.

## Alternativas
- Celery: potente pero pesado y problemático en Windows.
- RQ: depende de fork.
- Taskiq Redis: exige redis-py 8, incompatible con ARQ.
- BackgroundTasks: no sobrevive reinicios.

## Consecuencias
- Worker simple y asíncrono.
- Restricción de versión de redis-py.
- Requiere monitoreo de cola y limpieza de estados.

## Referencias
`tasks/worker.py`, `pyproject.toml`.
```

#### `docs/decisiones/ADR-0006-almacenamiento-privado.md`

```markdown
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
```

#### `docs/decisiones/ADR-0007-observabilidad-y-errores.md`

```markdown
# ADR-0007 --- Logs estructurados y errores uniformes

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
Se necesita diagnosticar fallos sin exponer datos judiciales ni
secretos, y correlacionar peticiones y tareas.

## Decisión
structlog con salida JSON en producción y consola legible en desarrollo.
`request_id` en cada petición, respuesta y log. Sobre de error
`error.code/message/details/request_id`. Sin trazas en producción.

## Alternativas
- Logging estándar: difícil de consultar y correlacionar.
- Errores ad hoc por endpoint: inconsistentes para el frontend.

## Consecuencias
- Consultas y alertas más simples.
- Requiere disciplina de eventos y redacción.
- El cliente recibe mensajes estables y seguros.

## Referencias
`core/logging.py`, `core/errors.py`, `core/middleware.py`.
```

#### `docs/decisiones/ADR-0008-calidad-y-ci.md`

```markdown
# ADR-0008 --- Ruff, mypy, pytest y CI obligatorio

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
El proyecto tendrá un solo equipo pequeño y debe mantener calidad sin
revisiones manuales repetitivas.

## Decisión
Ruff para formato y lint, mypy estricto, pytest con cobertura, pre-commit
con gitleaks y CI en GitHub Actions con PostgreSQL y Redis reales.
`uv sync --frozen` garantiza el lock.

## Alternativas
- Black + isort + flake8: más herramientas y más lento.
- Solo revisión manual: no escala ni es reproducible.

## Consecuencias
- Comprobaciones automáticas y consistentes.
- El CI requiere servicios y lock actualizado.
- Los hooks locales pueden ralentizar commits grandes.

## Referencias
`.pre-commit-config.yaml`, `.github/workflows/ci.yml`.
```

#### `docs/decisiones/ADR-0009-git-y-versionado.md`

```markdown
# ADR-0009 --- Trunk-based y Conventional Commits

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
Se necesita historial legible, integración frecuente y trazabilidad de
fases sin sobrecarga de ramas.

## Decisión
Rama principal `main` protegida. Ramas cortas `feat/`, `fix/`, `docs/`,
`chore/`, `refactor/`, `test/`. Commits convencionales en español.
Etiquetas `v0.x.y` al cerrar hitos. Sin `--no-verify`, sin reescribir
historial compartido.

## Alternativas
- Git Flow: demasiadas ramas para un equipo pequeño.
- Commits libres: historial difícil de auditar.

## Consecuencias
- Historial claro y PR pequeños.
- Requiere disciplina de mensajes y revisión.
- Los cambios grandes se dividen.

## Referencias
`AGENTS.md` sección 19.
```

#### `docs/decisiones/ADR-0010-configuracion-y-secretos.md`

```markdown
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
```

#### `docs/decisiones/ADR-0011-despliegue.md`

```markdown
# ADR-0011 --- Despliegue Linux con Nginx y systemd

- Estado: provisional
- Fecha: 2026-10-23

## Contexto
El sistema se accederá por Internet. Docker no es requisito confirmado.
El entorno destino exacto aún no está definido.

## Decisión
Desplegar el backend con Uvicorn detrás de Nginx y systemd en Linux.
PostgreSQL y Redis locales o administrados. HTTPS obligatorio. Worker
ARQ como servicio separado. Variables de entorno fuera del repositorio.

## Alternativas
- Docker Compose: útil, pero no confirmado ni obligatorio.
- Windows Server: posible, pero menos habitual para este stack.

## Consecuencias
- Proceso operable y comprensible sin contenedores.
- Requiere endurecimiento del sistema y gestión de servicios.
- La decisión se revisará cuando se conozca el entorno institucional.

## Referencias
`AGENTS.md` secciones 2.1 y 11.
```

---

### 18.8 Archivo: `docs/api.md`

````markdown
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
````

---

## 19. Runbook de ejecución de B0

Este runbook describe el orden exacto para materializar la fase. **Fue ejecutado y verificado localmente al cerrar B0**; cada paso incluye verificación. El remoto `origin/main`, el CI de GitHub Actions y la etiqueta `v0.1.0` están publicados. La etiqueta existente apunta al commit inicial `c5b53d6`; la documentación se incorpora después y requiere una decisión explícita sobre el etiquetado final.

### Paso 0. Confirmar estado del repositorio

```powershell
Set-Location C:\Users\Tony\Documents\sga
git status
git log --oneline -5
```

Esperado: repositorio inicializado, sin cambios ajenos. Si no hay repositorio:

```powershell
git init -b main
```

### Paso 1. Crear archivos raíz

Crear:

- `.gitignore`
- `.gitattributes`
- `.editorconfig`
- `.pre-commit-config.yaml`
- `.gitleaks.toml`
- `.github/workflows/ci.yml`
- `README.md`

Verificar que `.env` no se versiona:

```powershell
git check-ignore -v backend/.env
```

### Paso 2. Crear backend y fijar Python

```powershell
uv python install 3.12
New-Item -ItemType Directory -Force backend | Out-Null
Set-Location backend
uv python pin 3.12
```

Verificar:

```powershell
Get-Content .python-version
uv python find 3.12
```

Esperado: `3.12` y una ruta al intérprete.

### Paso 3. Crear `pyproject.toml`

Copiar el contenido de la sección 6.3 y ejecutar:

```powershell
uv lock
uv sync
uv run python -c "import fastapi, sqlalchemy, arq, pydantic; print('ok')"
```

Esperado: `ok`. Si falla, revisar la salida de `uv sync` y la versión de Python.

### Paso 4. Crear configuración

```powershell
Copy-Item .env.example .env
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Reemplazar `CAMBIAR_SECRETO_DEV` en `.env` con el valor generado. Verificar que `.env` está ignorado.

### Paso 5. Crear paquetes y código base

Crear en el orden de las secciones 8 a 15:

1. `core/config.py`
2. `core/logging.py`
3. `core/middleware.py`
4. `core/errors.py`
5. `core/pagination.py`
6. `core/runtime.py`
7. `core/security.py`
8. `db/base.py`
9. `db/session.py`
10. `db/health.py`
11. `tasks/worker.py`
12. `api/deps.py`
13. `api/v1/health.py`
14. `api/v1/router.py`
15. `main.py`
16. `asgi.py`
17. `__init__.py` de cada paquete

Verificar importación:

```powershell
uv run python -c "from judicial_archive.main import create_app; print(create_app)"
```

### Paso 6. Configurar Alembic

```powershell
uv run alembic init alembic
```

Reemplazar `alembic.ini` y `alembic/env.py` con el contenido de las secciones 11.1 y 11.2. Conservar `alembic/script.py.mako` generado. Verificar:

```powershell
uv run alembic current
uv run alembic heads
```

Esperado: sin errores; sin revisiones al inicio. No crear una migración ficticia.

### Paso 7. Verificar bases de datos

```powershell
psql -U sga_dev -d sga_dev -c "SELECT current_database(), current_user;"
psql -U sga_test -d sga_test -c "SELECT current_database(), current_user;"
redis-cli ping
```

Esperado: dos filas correctas y `PONG`.

### Paso 8. Ejecutar pruebas

```powershell
uv run pytest
```

Esperado: todas las pruebas unitarias y de API pasan; las de integración se omiten sin `RUN_INTEGRATION=1`.

```powershell
$env:RUN_INTEGRATION = "1"
uv run pytest -m integration
Remove-Item Env:RUN_INTEGRATION
```

Esperado: integración pasa si los servicios están disponibles.

### Paso 9. Ejecutar calidad

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
```

Esperado: sin errores. Si Pylance marca `Settings()` por argumentos requeridos, usar `# pyright: ignore[reportCallIssue]` solo en la llamada y documentar el motivo. No silenciar otros errores.

### Paso 10. Ejecutar servidor

Terminal 1:

```powershell
uv run uvicorn judicial_archive.asgi:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/live | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready | ConvertTo-Json
```

Esperado: `status: ok` y componentes `database` y `redis` en `ok`. Abrir `/docs` y comprobar los dos endpoints.

### Paso 11. Ejecutar worker

```powershell
uv run arq judicial_archive.tasks.worker.WorkerSettings
```

Esperado: arranque sin errores y log `worker_started`. Detener con `Ctrl+C` y comprobar `worker_stopped`.

### Paso 12. Pre-commit

```powershell
uv tool install pre-commit
pre-commit install
pre-commit run --all-files
```

Esperado: todos los hooks pasan. Si gitleaks detecta un falso positivo, revisar antes de ampliar la allowlist.

### Paso 13. Primer commit

```powershell
Set-Location C:\Users\Tony\Documents\sga
git add .
git status
git diff --cached --stat
git commit -m "chore(backend): preparar estructura y calidad de la fase B0"
git tag -a v0.1.0 -m "Fase B0: preparacion del backend"
```

Antes de confirmar, verificar que no hay `.env`, documentos reales, volcados ni secretos.

### Paso 14. Publicar y CI

```powershell
git remote add origin <URL>
git push -u origin main
git push origin v0.1.0
```

Verificar en CI: formato, lint, tipos y pruebas pasan. Si el CI falla, corregir y hacer un nuevo commit; no forzar el push.

---

## 20. Criterios de aceptación de B0

| # | Criterio | Verificación | Evidencia |
|---|---|---|---|
| 1 | Python 3.12 fijado | `uv python find 3.12` | `.python-version` |
| 2 | Dependencias reproducibles | `uv sync --frozen` | `uv.lock` |
| 3 | Configuración validada | pruebas de `Settings` | `test_config.py` |
| 4 | Secretos fuera del repo | `git check-ignore` + gitleaks | `.gitignore`, `.gitleaks.toml` |
| 5 | Logs estructurados con request-id | petición a `/live` | cabecera `X-Request-ID`, logs |
| 6 | Errores uniformes | pruebas de errores | `test_errors.py` |
| 7 | Salud operativa | `/live` y `/ready` | respuestas 200/503 |
| 8 | PostgreSQL conecta | `/ready` e integración | `test_dependencies.py` |
| 9 | Redis conecta | `/ready` e integración | `test_dependencies.py` |
| 10 | Alembic operativo | `alembic current`, `alembic heads` | salida de consola |
| 11 | Worker ARQ arranca | `arq ...WorkerSettings` | log `worker_started` |
| 12 | Calidad pasa | `check.ps1` | salida local y CI |
| 13 | CI verde | ejecución en GitHub Actions | enlace al run |
| 14 | Documentación completa | revisión de `docs/` | ADR, guías |
| 15 | Sin datos reales | revisión del diff | `git status` |
| 16 | Fase documentada | este archivo | `phaseB0_guide.md` |

B0 se considera cerrada solo cuando los 16 criterios están verificados. Las pruebas de integración pueden posponerse únicamente si se documenta la causa y se ejecutan antes de iniciar B2.

---

## 21. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Incompatibilidad ARQ/redis-py | Alta si se ignora | Alto | Fijar `redis>=5.2,<6`; no instalar redis-py 8 |
| mypy estricto bloquea el avance | Media | Medio | Corregir tipos; ignores puntuales justificados |
| Configuración insegura llega a producción | Media | Muy alto | Validadores y CI; revisión de variables |
| Secretos en Git | Media | Muy alto | gitleaks, `.gitignore`, rotación inmediata |
| PostgreSQL/Redis no disponibles | Media | Medio | `/ready`, integración, documentación |
| Diferencias Windows/Linux | Media | Medio | CI Linux, rutas relativas, UTF-8, LF |
| Alembic autogenerate incompleto | Alta | Alto | Revisión manual; probar upgrade/downgrade |
| Cambio de versión de dependencias | Media | Medio | `uv.lock`, actualizaciones controladas |
| Numeración de fases inconsistente | Alta | Bajo | Guía maestra como fuente; corregir AGENTS.md |
| Almacenamiento local sin respaldo | Media | Alto | Definir respaldo antes de B9 |
| Crecimiento de documentos | Media | Alto | Medir volumen en B9/B10; interfaz reemplazable |
| Fuga de datos en logs/errores | Media | Muy alto | Redacción, pruebas, revisión de diff |
| Deuda por saltar B1 | Alta | Alto | No implementar modelos sin reglas aprobadas |

Riesgos críticos requieren decisión humana antes de continuar. No se acepta un riesgo de seguridad alto como deuda técnica.

---

## 22. Definition of Done de B0 y traspaso a B1

### 22.1 Checklist de B0

- [x] Archivos raíz creados y versionados.
- [x] `backend/pyproject.toml` con dependencias y configuración completas.
- [x] `uv.lock` generado y reproducible.
- [x] `.env.example` completo y `.env` ignorado.
- [x] Todos los módulos base creados con `__init__.py`.
- [x] Configuración validada con pruebas.
- [x] Logging, request-id, errores y paginación implementados.
- [x] Seguridad base implementada y probada.
- [x] Alembic configurado sin migraciones ficticias.
- [x] `/live` y `/ready` funcionando.
- [x] Worker ARQ arranca.
- [x] Pruebas unitarias, API e integración definidas y ejecutadas.
- [x] Ruff, mypy y pytest pasan.
- [x] pre-commit y gitleaks activos.
- [x] CI configurado y verde en GitHub Actions (run `40203857497`).
- [x] README y documentación creados.
- [x] ADR-0001 a ADR-0011 creados.
- [x] Pendientes de validación registrados.
- [x] Sin secretos, datos reales ni artefactos.
- [x] Primer commit `c5b53d6` y remoto `origin/main` publicados.
- [ ] Etiqueta final verificada: `v0.1.0` existe, pero apunta a `c5b53d6` y no incluye la documentación posterior.

### 22.2 Traspaso a B1

Antes de iniciar B1, el equipo debe tener:

- La guía B1 leída y aprobada.
- El catálogo de entidades y reglas de negocio en revisión.
- Respuestas o decisiones provisionales para los pendientes 1 a 5, 9 y 13.
- Confirmación de que B0 está cerrada y el CI está verde.
- Un responsable de validar los códigos de tribunales y formatos históricos.

B1 **no debe** crear tablas ni migraciones. Su entregable es el modelo conceptual, las reglas, los estados, las transiciones y las preguntas resueltas o explícitamente pendientes.

---

## 23. Qué NO hace B0

Para evitar confusiones y trabajo prematuro:

- No crea tablas de negocio.
- No crea migraciones iniciales.
- No implementa autenticación, usuarios ni permisos.
- No implementa CRUD de cajas, expedientes, tribunales ni ubicaciones.
- No implementa OCR, importaciones, préstamos, movimientos ni reportes.
- No crea endpoints ficticios.
- No crea el frontend.
- No configura producción ni certificados.
- No define reglas archivísticas no confirmadas.
- No carga datos reales.
- No elige un motor OCR definitivo.
- No implementa 2D/3D.

Cualquier intento de adelantar estas tareas debe registrarse como fuera de alcance y evaluarse en su fase.

---

## Apéndice A. Variables de entorno

| Variable | Tipo | Ejemplo | Obligatoria | Notas |
|---|---|---|---|---|
| `SGA_APP_NAME` | texto | `SGA - Sistema de Gestion Documental Judicial` | No | Nombre visible |
| `SGA_ENVIRONMENT` | enum | `development` | No | `development`, `testing`, `staging`, `production` |
| `SGA_DEBUG` | booleano | `false` | No | Prohibido en producción |
| `SGA_SECRET_KEY` | secreto | 48+ caracteres | Sí | Rotable; nunca en Git |
| `SGA_API_V1_PREFIX` | texto | `/api/v1` | No | Debe iniciar con `/` y no terminar en `/` |
| `SGA_DATABASE_URL` | URL | `postgresql+psycopg://...` | Sí | Driver `psycopg` |
| `SGA_DB_ECHO` | booleano | `false` | No | Solo desarrollo |
| `SGA_DB_POOL_SIZE` | entero | `10` | No | 1-100 |
| `SGA_DB_MAX_OVERFLOW` | entero | `20` | No | 0-100 |
| `SGA_DB_POOL_PRE_PING` | booleano | `true` | No | Recomendado |
| `SGA_DB_POOL_RECYCLE_SECONDS` | entero | `1800` | No | 60-86400 |
| `SGA_REDIS_URL` | URL | `redis://localhost:6379/0` | Sí | Redis 7.4+ |
| `SGA_REDIS_SOCKET_TIMEOUT_SECONDS` | decimal | `3` | No | 1-60 |
| `SGA_CORS_ORIGINS` | lista | `http://localhost:5173` | No | Separada por comas; sin `*` con credenciales |
| `SGA_TRUSTED_HOSTS` | lista | `localhost,127.0.0.1` | No | Separada por comas; por defecto incluye `testserver` para pruebas |
| `SGA_REQUEST_ID_HEADER` | texto | `X-Request-ID` | No | Cabecera de correlación |
| `SGA_DOCS_ENABLED` | booleano | `true` | No | `false` en producción |
| `SGA_LOG_LEVEL` | enum | `INFO` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `SGA_LOG_JSON` | booleano | `true` | No | `true` en producción |
| `SGA_SESSION_COOKIE_NAME` | texto | `sga_session` | No | Sin espacios |
| `SGA_SESSION_COOKIE_SECURE` | booleano | `true` | No | `true` en producción |
| `SGA_SESSION_IDLE_MINUTES` | entero | `30` | No | 5-1440 |
| `SGA_SESSION_ABSOLUTE_HOURS` | entero | `12` | No | 1-720 |
| `SGA_CSRF_COOKIE_NAME` | texto | `sga_csrf` | No | Se implementa en B4 |
| `SGA_CSRF_HEADER_NAME` | texto | `X-CSRF-Token` | No | Se implementa en B4 |
| `SGA_TASK_QUEUE_NAME` | texto | `sga` | No | Cola ARQ |
| `SGA_TASK_MAX_JOBS` | entero | `4` | No | 1-64 |
| `SGA_TASK_JOB_TIMEOUT_SECONDS` | entero | `900` | No | 10-86400 |
| `SGA_STORAGE_BACKEND` | enum | `local` | No | Solo `local` en B0; S3 se evaluará en B9 |
| `SGA_STORAGE_ROOT` | ruta | `var/storage` | No | Fuera de estáticos |
| `SGA_READINESS_TIMEOUT_SECONDS` | decimal | `3.0` | No | 0 < valor <= 30 |

Reglas:

- No agregar variables sin documentarlas aquí y en `.env.example`.
- No usar prefijos distintos para evitar colisiones.
- Las listas se separan por comas, sin comillas en el archivo `.env` salvo que contengan espacios.
- Los secretos no se registran ni se imprimen.

---

## Apéndice B. Comandos de referencia

### Backend

```powershell
cd backend
uv sync
uv run uvicorn judicial_archive.asgi:app --reload --host 127.0.0.1 --port 8000
uv run arq judicial_archive.tasks.worker.WorkerSettings
uv run alembic current
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "descripcion"
uv run ruff format .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv run pytest -m integration
```

### Base de datos

```powershell
psql -U postgres
psql -U sga_dev -d sga_dev
psql -U sga_test -d sga_test
```

### Git

```powershell
git status
git diff
git switch -c feat/tema
git add <archivos>
git commit -m "feat(scope): descripcion"
git push -u origin feat/tema
git tag -a v0.1.0 -m "Fase B0"
```

### Pre-commit

```powershell
pre-commit install
pre-commit run --all-files
pre-commit autoupdate
```

---

## Apéndice C. Matriz de versiones y compatibilidad

| Componente | Versión mínima | Versión fijada | Motivo |
|---|---|---|---|
| Python | 3.12 | 3.12 | Tipado y soporte |
| FastAPI | 0.115 | 0.161.1 | Framework |
| Uvicorn | 0.30 | 0.54.0 | ASGI |
| Pydantic | 2.7 | 2.14.1 | Validación |
| pydantic-settings | 2.3 | 2.16.1 | Configuración |
| SQLAlchemy | 2.0.30 | 2.1.6 | ORM async |
| psycopg | 3.2 | 3.3.6 | Driver |
| Alembic | 1.13 | 1.20.1 | Migraciones |
| ARQ | 0.26 | 0.28.0 | Tareas |
| redis-py | 5.2 | >=5.2,<6 | Compatibilidad ARQ |
| structlog | 24.1 | 26.1.0 | Logs |
| pwdlib | 0.2 | 0.3.1 | Contraseñas |
| pytest | 8.2 | 9.1.1 | Pruebas |
| pytest-asyncio | 0.23 | 1.4.0 | Async |
| pytest-cov | 5.0 | 7.1.0 | Cobertura |
| httpx | 0.27 | 0.28.1 | Cliente de pruebas |
| Ruff | 0.5 | 0.17.2 | Lint/formato |
| mypy | 1.10 | 2.4.0 | Tipos |
| pre-commit | 3.7 | 4.7.0 | Hooks |
| PostgreSQL | 16 | 18 | Base de datos |
| Redis | 7.0 | 7.4+ | Cola/caché |

Compatibilidad crítica:

- ARQ 0.28 declara `redis>=4.2,<6`. No actualizar redis-py a 8 mientras se use esta versión de ARQ.
- `pytest-asyncio` 1.x requiere `asyncio_mode=auto` o marcas explícitas; la configuración ya lo define.
- SQLAlchemy 2.1 requiere psycopg 3.2+ y Python 3.10+; el proyecto usa 3.12.
- FastAPI 0.161 requiere Pydantic 2.7+; el rango lo garantiza.

Actualizaciones:

1. Cambiar la restricción en `pyproject.toml`.
2. `uv lock --upgrade-package <paquete>`.
3. Ejecutar `uv sync`, pruebas y CI.
4. Revisar compatibilidad y notas de versión.
5. Documentar el cambio si afecta arquitectura o seguridad.

---

## Apéndice D. Glosario

| Término | Significado |
|---|---|
| Anaquel | Estructura física que contiene bandejas y posiciones |
| Bandeja | Nivel o compartimento dentro de un anaquel |
| Caja | Unidad física que agrupa expedientes o documentos administrativos |
| Conciliación | Proceso de comparar inventario digital con físico |
| Expediente | Conjunto documental de un caso judicial |
| Lote de importación | Conjunto de archivos procesados y revisados juntos |
| Movimiento | Traslado registrado de una caja con origen y destino |
| NUC | Número Único de Caso; identificador de texto |
| Posición | Lugar concreto dentro de una bandeja |
| Préstamo | Salida temporal autorizada de una unidad |
| Sesión opaca | Sesión cuyo identificador no contiene datos y se valida en servidor |
| Sobre de error | Estructura uniforme de respuesta de error |
| `request_id` | Identificador de correlación de una petición |

---

## Apéndice E. Inventario de archivos de B0

Marcar al crear cada archivo. Ningún archivo debe quedar vacío salvo los `.gitkeep` justificados.

### Raíz

- [ ] `.editorconfig`
- [ ] `.gitattributes`
- [ ] `.gitignore`
- [ ] `.gitleaks.toml`
- [ ] `.pre-commit-config.yaml`
- [ ] `.github/workflows/ci.yml`
- [ ] `README.md`

### Backend

- [ ] `backend/.env.example`
- [ ] `backend/.python-version`
- [ ] `backend/README.md`
- [ ] `backend/alembic.ini`
- [ ] `backend/pyproject.toml`
- [ ] `backend/uv.lock`
- [ ] `backend/alembic/env.py`
- [ ] `backend/alembic/script.py.mako`
- [ ] `backend/alembic/versions/.gitkeep`
- [ ] `backend/scripts/check.ps1`
- [ ] `backend/scripts/dev.ps1`
- [ ] `backend/scripts/worker.ps1`

### Código

- [ ] `backend/src/judicial_archive/__init__.py`
- [ ] `backend/src/judicial_archive/asgi.py`
- [ ] `backend/src/judicial_archive/main.py`
- [ ] `backend/src/judicial_archive/api/__init__.py`
- [ ] `backend/src/judicial_archive/api/deps.py`
- [ ] `backend/src/judicial_archive/api/v1/__init__.py`
- [ ] `backend/src/judicial_archive/api/v1/health.py`
- [ ] `backend/src/judicial_archive/api/v1/router.py`
- [ ] `backend/src/judicial_archive/core/__init__.py`
- [ ] `backend/src/judicial_archive/core/config.py`
- [ ] `backend/src/judicial_archive/core/errors.py`
- [ ] `backend/src/judicial_archive/core/logging.py`
- [ ] `backend/src/judicial_archive/core/middleware.py`
- [ ] `backend/src/judicial_archive/core/pagination.py`
- [ ] `backend/src/judicial_archive/core/runtime.py`
- [ ] `backend/src/judicial_archive/core/security.py`
- [ ] `backend/src/judicial_archive/db/__init__.py`
- [ ] `backend/src/judicial_archive/db/base.py`
- [ ] `backend/src/judicial_archive/db/health.py`
- [ ] `backend/src/judicial_archive/db/session.py`
- [ ] `backend/src/judicial_archive/modules/__init__.py`
- [ ] `backend/src/judicial_archive/tasks/__init__.py`
- [ ] `backend/src/judicial_archive/tasks/worker.py`

### Pruebas

- [ ] `backend/tests/__init__.py`
- [ ] `backend/tests/conftest.py`
- [ ] `backend/tests/helpers.py`
- [ ] `backend/tests/api/__init__.py`
- [ ] `backend/tests/api/test_errors.py`
- [ ] `backend/tests/api/test_health.py`
- [ ] `backend/tests/integration/__init__.py`
- [ ] `backend/tests/integration/test_dependencies.py`
- [ ] `backend/tests/unit/__init__.py`
- [ ] `backend/tests/unit/test_config.py`
- [ ] `backend/tests/unit/test_db_health.py`
- [ ] `backend/tests/unit/test_pagination.py`
- [ ] `backend/tests/unit/test_security.py`
- [ ] `backend/tests/unit/test_session.py`

### Documentación

- [ ] `docs/api.md`
- [ ] `docs/arquitectura.md`
- [ ] `docs/instalacion-desarrollo.md`
- [ ] `docs/pruebas.md`
- [ ] `docs/seguridad.md`
- [ ] `docs/pendientes-de-validacion.md`
- [ ] `docs/decisiones/ADR-0001-python-y-uv.md`
- [ ] `docs/decisiones/ADR-0002-arquitectura-modular.md`
- [ ] `docs/decisiones/ADR-0003-persistencia.md`
- [ ] `docs/decisiones/ADR-0004-autenticacion.md`
- [ ] `docs/decisiones/ADR-0005-tareas-segundo-plano.md`
- [ ] `docs/decisiones/ADR-0006-almacenamiento-privado.md`
- [ ] `docs/decisiones/ADR-0007-observabilidad-y-errores.md`
- [ ] `docs/decisiones/ADR-0008-calidad-y-ci.md`
- [ ] `docs/decisiones/ADR-0009-git-y-versionado.md`
- [ ] `docs/decisiones/ADR-0010-configuracion-y-secretos.md`
- [ ] `docs/decisiones/ADR-0011-despliegue.md`

---

## Cierre de la guía

Esta guía cubre la fase B0 completa: decisiones, estructura, código de referencia, configuración, seguridad base, tareas, almacenamiento, API mínima, pruebas, calidad, CI, documentación, ADR, runbook, aceptación, riesgos y Definition of Done.

Estado de implementación: **documentación lista; código aún no ejecutado ni validado**. La ejecución debe seguir el runbook de la sección 19 y registrar los resultados reales. No declarar B0 cerrada sin cumplir la sección 20.

Siguiente fase: **B1 --- Dominio y reglas de negocio**, sin crear tablas ni migraciones hasta que las reglas estén revisadas.
