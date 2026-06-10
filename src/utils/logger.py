"""
Yapılandırılmış logging sistemi.
Production ortamında izlenebilirlik için structlog kullanır.
"""

import logging
import sys

import structlog

from src.config import LOG_LEVEL, LOGS_DIR


def setup_logging(name: str = "ecommerce_analytics") -> structlog.stdlib.BoundLogger:
    """
    Uygulama genelinde kullanılacak logger'ı yapılandırır.

    Args:
        name: Logger adı (modül bazlı ayrım için)

    Returns:
        Yapılandırılmış structlog logger instance'ı
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "app.log"

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        force=True,
    )

    root_logger = logging.getLogger()
    if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
        root_logger.addHandler(file_handler)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger(name)


logger = setup_logging()
