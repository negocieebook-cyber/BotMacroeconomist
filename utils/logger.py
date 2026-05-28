"""
Configuração de logging com saída colorida no console.
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def _ansi_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("COLORTERM") or os.environ.get("WT_SESSION"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


class _ColorFormatter(logging.Formatter):
    _LEVEL_COLORS = {
        "DEBUG":    "\033[36m",
        "INFO":     "\033[32m",
        "WARNING":  "\033[33m",
        "ERROR":    "\033[31m",
        "CRITICAL": "\033[35;1m",
    }
    _RESET = "\033[0m"
    _DIM   = "\033[2m"

    def format(self, record: logging.LogRecord) -> str:
        rec = logging.makeLogRecord(record.__dict__)
        color = self._LEVEL_COLORS.get(rec.levelname, "")
        rec.levelname = f"{color}{rec.levelname:<8}{self._RESET}"
        rec.name = f"{self._DIM}{rec.name}{self._RESET}"
        return super().format(rec)


_CONSOLE_FMT = "%(asctime)s %(levelname)s %(message)s"
_FILE_FMT    = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_DATE_SHORT  = "%H:%M:%S"
_DATE_FULL   = "%Y-%m-%d %H:%M:%S"


def setup_logger(level: str = "INFO", log_file: str = "./logs/macroeconomist.log") -> logging.Logger:
    os.makedirs(os.path.dirname(log_file) or "logs", exist_ok=True)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    if _ansi_enabled():
        console_fmt = _ColorFormatter(_CONSOLE_FMT, datefmt=_DATE_SHORT)
    else:
        console_fmt = logging.Formatter(_CONSOLE_FMT, datefmt=_DATE_SHORT)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(getattr(logging, level.upper(), logging.INFO))
    console.setFormatter(console_fmt)
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    file_handler.setFormatter(logging.Formatter(_FILE_FMT, datefmt=_DATE_FULL))
    logger.addHandler(file_handler)

    return logger
