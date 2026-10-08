import datetime as dt
import json
import logging
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path

from bpa.report import RUN_ID_PATTERN

PACKAGE_LOGGER = "bpa"
LOG_FILE_NAME = "bpa.log"
MAX_LOG_BYTES = 1_000_000
BACKUP_COUNT = 5


def generate_run_id(now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now()
    return f"{now:%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"


class RunIdFilter(logging.Filter):
    def __init__(self, run_id: str) -> None:
        super().__init__()
        self.run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = self.run_id
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": dt.datetime.fromtimestamp(record.created).isoformat(timespec="seconds"),
            "level": record.levelname,
            "run_id": getattr(record, "run_id", "-"),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def teardown_logging() -> None:
    package_logger = logging.getLogger(PACKAGE_LOGGER)
    for handler in list(package_logger.handlers):
        handler.close()
        package_logger.removeHandler(handler)
    package_logger.propagate = True
    package_logger.setLevel(logging.NOTSET)


def setup_logging(run_id: str, log_dir: Path, level: int = logging.INFO) -> None:

    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError(f"Unsafe run id: {run_id!r}")

    teardown_logging()

    log_dir.mkdir(parents=True, exist_ok=True)
    run_filter = RunIdFilter(run_id)

    console = logging.StreamHandler()
    console.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-7s [%(run_id)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    console.addFilter(run_filter)

    file_handler = RotatingFileHandler(
        log_dir / LOG_FILE_NAME,
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(JsonFormatter())
    file_handler.addFilter(run_filter)

    package_logger = logging.getLogger(PACKAGE_LOGGER)
    package_logger.setLevel(level)
    package_logger.addHandler(console)
    package_logger.addHandler(file_handler)
    package_logger.propagate = False
