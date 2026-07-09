"""Configuracao de logging estruturado da aplicacao.

Correcao critica (auditoria item 4): o backend nao tinha nenhum logging
configurado -- qualquer excecao nao tratada virava um 500 generico e
desaparecia sem deixar rastro. Este modulo centraliza a configuracao de
logging para toda a aplicacao (chamado uma unica vez, no startup, a
partir de `app.main`).

Formato: JSON estruturado (um objeto por linha), incluindo timestamp,
nivel, logger, mensagem e, quando disponivel, o `request_id` de
correlacao (ver `app.middleware.request_context`). Isso permite
diagnosticar incidentes em producao (grep/parse por request_id,
integracao futura com ferramentas de log aggregation) sem depender de
nenhuma biblioteca externa alem da stdlib.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.middleware.request_context import get_request_id

_RESERVED_LOG_RECORD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """Formata cada registro de log como uma linha JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = get_request_id()
        if request_id is not None:
            payload["request_id"] = request_id

        # Campos extras passados via `logger.info(..., extra={...})`.
        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_RECORD_ATTRS and not key.startswith("_"):
                if key not in payload:
                    try:
                        json.dumps(value)
                        payload[key] = value
                    except TypeError:
                        payload[key] = str(value)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configure_logging(*, debug: bool = False) -> None:
    """Configura o logging raiz da aplicacao. Idempotente."""
    root_logger = logging.getLogger()

    # Evita duplicar handlers se configure_logging() for chamado mais
    # de uma vez (ex.: reload em desenvolvimento, testes).
    root_logger.handlers.clear()

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Bibliotecas de terceiros tendem a ser bem verbosas em INFO/DEBUG;
    # mantemos elas em WARNING para nao afogar o log da aplicacao,
    # exceto quando DEBUG estiver ligado explicitamente.
    if not debug:
        for noisy_logger in ("httpx", "httpcore", "apscheduler"):
            logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    logging.getLogger("uvicorn.access").setLevel(
        logging.DEBUG if debug else logging.INFO
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
