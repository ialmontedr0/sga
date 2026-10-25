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
