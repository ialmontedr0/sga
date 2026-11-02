import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from judicial_archive.core.errors import InvalidParameterError

_SENSITIVE_KEY_PARTS = frozenset(
    {"secret", "password", "passwd", "token", "api_key", "apikey", "private_key", "credential"}
)

_MAX_JSON_BYTES = 16_384


def validate_setting_value(key: str, value: object, value_type: str) -> None:
    lowered = key.lower()
    if any(part in lowered for part in _SENSITIVE_KEY_PARTS):
        raise InvalidParameterError("La clave parece contener un secreto y no se admite.")

    if value_type == "STRING":
        if not isinstance(value, str):
            raise InvalidParameterError("El valor debe ser texto.")
        if any(part in value.lower() for part in ("password=", "token=", "secret=")):
            raise InvalidParameterError("El valor parece contener un secreto.")
    elif value_type == "INTEGER":
        if isinstance(value, bool) or not isinstance(value, int):
            raise InvalidParameterError("El valor debe ser un entero.")
    elif value_type == "BOOLEAN":
        if not isinstance(value, bool):
            raise InvalidParameterError("El valor debe ser un booleano")
    elif value_type == "JSON":
        if not isinstance(value, (dict, list)):
            raise InvalidParameterError("El valor JSON debe ser un objeto o arreglo.")
    else:
        raise InvalidParameterError("Tipo de configuracion invalida.")

    encoded = json.dumps(value, ensure_ascii=False).encode("utf-8")
    if len(encoded) > _MAX_JSON_BYTES:
        raise InvalidParameterError("El valor de configuracion supera 16 KiB.")

    if key == "system.timezone":
        if not isinstance(value, str):
            raise InvalidParameterError("La zona horaria debe ser texto.")
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise InvalidParameterError("La zona horaria no existe.") from exc
