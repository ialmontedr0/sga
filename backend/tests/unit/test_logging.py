from __future__ import annotations

import json
import logging
from collections.abc import Iterator

import pytest
import structlog

from judicial_archive.core.logging import (
    _redact_sensitive_values,
    _shared_processors,
    configure_logging,
)
from tests.helpers import build_test_settings


def test_redacts_top_level_secret() -> None:
    event = {"password": "secret", "user": "admin"}
    result = _redact_sensitive_values(None, "info", dict(event))
    assert result["password"] == "***"
    assert result["user"] == "admin"


def test_redacts_nested_dict() -> None:
    event = {"payload": {"token": "abc", "name": "x"}}
    result = _redact_sensitive_values(None, "info", dict(event))
    nested = result["payload"]
    assert isinstance(nested, dict)
    assert nested["token"] == "***"
    assert nested["name"] == "x"


def test_redacts_list_and_tuple() -> None:
    event = {"items": [{"secret": "a"}, {"ok": "b"}]}
    result = _redact_sensitive_values(None, "info", dict(event))
    items = result["items"]
    assert isinstance(items, list)
    assert items[0]["secret"] == "***"
    assert items[1]["ok"] == "b"
    tuple_result = _redact_sensitive_values(
        None,
        "info",
        {"value": ({"password": "a"},)},
    )
    value = tuple_result["value"]
    assert isinstance(value, tuple)
    assert value[0]["password"] == "***"


def test_redacts_database_url() -> None:
    result = _redact_sensitive_values(
        None,
        "info",
        {"database_url": "postgresql+psycopg://u:secret@host/db"},
    )
    assert result["database_url"] == "***"


def test_redacts_redis_url_and_dsn() -> None:
    result = _redact_sensitive_values(
        None,
        "info",
        {"redis_url": "redis://:secret@host/0", "dsn": "postgresql://u:secret@host/db"},
    )
    assert result["redis_url"] == "***"
    assert result["dsn"] == "***"


def test_does_not_mutate_unrelated_keys() -> None:
    event = {"request_id": "abc", "count": 3, "ok": True}
    result = _redact_sensitive_values(None, "info", dict(event))
    assert result == event


def test_shared_processors_include_redaction() -> None:
    assert _redact_sensitive_values in _shared_processors()


@pytest.fixture
def restore_logging() -> Iterator[None]:
    root = logging.getLogger()
    handlers = list(root.handlers)
    level = root.level
    uvicorn = logging.getLogger("uvicorn")
    uvicorn_handlers = list(uvicorn.handlers)
    uvicorn_propagate = uvicorn.propagate
    yield
    root.handlers = handlers
    root.setLevel(level)
    uvicorn.handlers = uvicorn_handlers
    uvicorn.propagate = uvicorn_propagate


def test_json_logging_redacts_and_propagates_request_id(
    capsys: pytest.CaptureFixture[str],
    restore_logging: None,
) -> None:
    configure_logging(build_test_settings(log_json=True, log_level="INFO"))
    logger = structlog.get_logger("tests.logging.json")
    with structlog.contextvars.bound_contextvars(request_id="abc123"):
        logger.info("sensitive_event", password="secret", nested={"token": "abc"})
    output = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(output)
    assert payload["event"] == "sensitive_event"
    assert payload["request_id"] == "abc123"
    assert payload["password"] == "***"
    assert payload["nested"]["token"] == "***"


def test_console_logging_redacts(
    capsys: pytest.CaptureFixture[str],
    restore_logging: None,
) -> None:
    configure_logging(build_test_settings(log_json=False, log_level="INFO"))
    logger = structlog.get_logger("tests.logging.console")
    logger.info("sensitive_event", password="secret")
    output = capsys.readouterr().out
    assert "sensitive_event" in output
    assert "secret" not in output
    assert "***" in output


def test_configure_logging_avoids_duplicate_handlers(restore_logging: None) -> None:
    root = logging.getLogger()
    root.addHandler(logging.NullHandler())
    root.setLevel(logging.ERROR)
    uvicorn = logging.getLogger("uvicorn")
    uvicorn.addHandler(logging.NullHandler())
    uvicorn.propagate = False

    configure_logging(build_test_settings(log_level="DEBUG"))

    assert len(root.handlers) == 1
    assert root.level == logging.DEBUG
    assert uvicorn.handlers == []
    assert uvicorn.propagate is True
