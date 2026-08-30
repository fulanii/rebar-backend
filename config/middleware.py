"""Request logging and log colouring."""

import logging
import time

RESET = "\033[0m"

LEVEL_COLORS = {
    logging.DEBUG: "\033[37m",
    logging.INFO: "\033[32m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[41m\033[97m",
}

logger = logging.getLogger(__name__)


class ColoredFormatter(logging.Formatter):
    """Standard formatter with the level name wrapped in an ANSI colour."""

    def format(self, record):
        original = record.levelname
        color = LEVEL_COLORS.get(record.levelno, "")
        record.levelname = f"{color}{original}{RESET}"
        try:
            return super().format(record)
        finally:
            record.levelname = original


class RequestLoggingMiddleware:
    """Logs one line per request: method, path, status, duration."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - started) * 1000

        logger.info(
            "%s %s -> %s (%.0fms)",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )
        return response
