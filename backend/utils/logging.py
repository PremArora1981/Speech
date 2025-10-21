"""Structured logging utilities."""

import logging
from typing import Any


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger


class RequestContextFilter(logging.Filter):
    def __init__(self, request_id: str) -> None:
        super().__init__()
        self.request_id = request_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = self.request_id
        return True


def log_with_context(logger: logging.Logger, request_id: str, level: int, msg: str, **kwargs: Any) -> None:
    ctx = RequestContextFilter(request_id)
    logger.addFilter(ctx)
    logger.log(level, msg, extra=kwargs)
    logger.removeFilter(ctx)

