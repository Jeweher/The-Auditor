"""
File: app/core/logging_config.py
Folder: backend/app/core
Purpose: Configure logging once at application startup. All modules then use
         `logging.getLogger(__name__)` — never print(). Formats as plain text
         in development for readability, JSON in production for log aggregation.
"""

import logging
import sys
import json
from datetime import datetime, timezone

from app.core.config import get_settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging() -> None:
    settings = get_settings()
    root_logger = logging.getLogger()

    # Avoid duplicate handlers on reload
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if settings.ENV == "production":
        handler.setFormatter(JsonFormatter())
        root_logger.setLevel(logging.INFO)
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    root_logger.addHandler(handler)

    # Quiet down noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
