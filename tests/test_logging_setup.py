import json
import logging

import pytest

from bpa.logging_setup import generate_run_id, setup_logging, teardown_logging
from bpa.report import RUN_ID_PATTERN

LOGGER = logging.getLogger("bpa.test")


@pytest.fixture(autouse=True)
def clean_logging():
    yield
    teardown_logging()


def read_log(tmp_path):

    teardown_logging()
    lines = (tmp_path / "bpa.log").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_generated_run_id_is_safe_for_file_names():
    assert RUN_ID_PATTERN.fullmatch(generate_run_id())


def test_generated_run_ids_are_unique():
    assert len({generate_run_id() for _ in range(100)}) == 100


def test_file_receives_json_lines_with_run_id(tmp_path):
    setup_logging("run-1", tmp_path)

    LOGGER.info("processed %d rows", 12)

    entries = read_log(tmp_path)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["run_id"] == "run-1"
    assert entry["level"] == "INFO"
    assert entry["logger"] == "bpa.test"
    assert entry["message"] == "processed 12 rows"
    assert "time" in entry


def test_console_line_contains_run_id_and_message(tmp_path, capsys):
    setup_logging("run-2", tmp_path)

    LOGGER.warning("something odd")

    err = capsys.readouterr().err
    assert "run-2" in err
    assert "WARNING" in err
    assert "something odd" in err


def test_newline_in_message_cannot_forge_a_log_line(tmp_path):
    setup_logging("run-3", tmp_path)

    LOGGER.info("first\nFAKE LINE")

    entries = read_log(tmp_path)
    assert len(entries) == 1
    assert entries[0]["message"] == "first\nFAKE LINE"


def test_exception_traceback_is_logged(tmp_path):
    setup_logging("run-4", tmp_path)

    try:
        raise ValueError("boom")
    except ValueError:
        LOGGER.exception("step failed")

    entry = read_log(tmp_path)[0]
    assert entry["message"] == "step failed"
    assert "ValueError: boom" in entry["exception"]


def test_calling_setup_twice_does_not_duplicate_lines(tmp_path):
    setup_logging("first", tmp_path)
    setup_logging("second", tmp_path)

    LOGGER.info("once")

    entries = read_log(tmp_path)
    assert len(entries) == 1
    assert entries[0]["run_id"] == "second"


def test_debug_is_dropped_by_default(tmp_path):
    setup_logging("run-5", tmp_path)

    LOGGER.debug("noise")
    LOGGER.info("signal")

    assert [entry["message"] for entry in read_log(tmp_path)] == ["signal"]


def test_level_can_be_lowered(tmp_path):
    setup_logging("run-6", tmp_path, level=logging.DEBUG)

    LOGGER.debug("detail")

    assert [entry["message"] for entry in read_log(tmp_path)] == ["detail"]


def test_log_directory_is_created(tmp_path):
    target = tmp_path / "nested" / "logs"

    setup_logging("run-7", target)
    LOGGER.info("hello")
    teardown_logging()

    assert (target / "bpa.log").exists()


def test_unsafe_run_id_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="Unsafe run id"):
        setup_logging("bad id\nforged", tmp_path)
