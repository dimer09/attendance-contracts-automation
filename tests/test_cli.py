import json
import os
import runpy
import sys
from pathlib import Path

import pytest
import responses

from bpa import cli
from bpa.cli import main
from bpa.extract import api_client
from bpa.logging_setup import teardown_logging

SAMPLE_DIR = Path(__file__).parent.parent / "data" / "sample"
ATTENDANCE = SAMPLE_DIR / "attendance.csv"
BASE_URL = "http://api.test"
CONTRACTS_URL = f"{BASE_URL}/contracts"
CONTRACTS = json.loads((SAMPLE_DIR / "contracts.json").read_text())


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
  
    monkeypatch.chdir(tmp_path)
   
    clean = {k: v for k, v in os.environ.items() if not k.startswith("BPA_")}
    monkeypatch.setattr(os, "environ", clean)
    monkeypatch.setattr(api_client.time, "sleep", lambda seconds: None)  
    yield
    teardown_logging()


def configure(monkeypatch, key="key"):
    monkeypatch.setenv("BPA_API_URL", BASE_URL)
    monkeypatch.setenv("BPA_API_KEY", key)


def serve_contracts():
    responses.add(responses.GET, CONTRACTS_URL, json=CONTRACTS, status=200)


def run_cli(tmp_path, input_path=ATTENDANCE, log_dir=None):
    return main([
        "--input", str(input_path),
        "--output-dir", str(tmp_path / "reports"),
        "--log-dir", str(log_dir or tmp_path / "logs"),
    ])


@responses.activate
def test_successful_run_prints_summary_and_exits_0(tmp_path, monkeypatch, capsys):
    configure(monkeypatch)
    serve_contracts()

    code = run_cli(tmp_path)

    out = capsys.readouterr().out
    assert code == 0  
    assert "Exceptions: 6" in out
    assert "Result: ACTION REQUIRED" in out
    assert len(list((tmp_path / "reports").glob("report_*.xlsx"))) == 1


@responses.activate
def test_log_file_holds_the_run_events_with_one_run_id(tmp_path, monkeypatch):
    configure(monkeypatch)
    serve_contracts()

    run_cli(tmp_path)

    lines = (tmp_path / "logs" / "bpa.log").read_text(encoding="utf-8").splitlines()
    entries = [json.loads(line) for line in lines]
    assert len({entry["run_id"] for entry in entries}) == 1
    assert any("Report written" in entry["message"] for entry in entries)
    assert any(entry["level"] == "WARNING" for entry in entries)  

def test_missing_input_file_exits_1(tmp_path, monkeypatch, capsys):
    configure(monkeypatch)

    code = run_cli(tmp_path, input_path=tmp_path / "nope.csv")

    assert code == 1
    assert "File not found" in capsys.readouterr().err


def test_missing_configuration_exits_1(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BPA_API_URL", BASE_URL)  

    code = run_cli(tmp_path)

    err = capsys.readouterr().err
    assert code == 1
    assert "BPA_API_KEY" in err
    assert "BPA_API_URL" not in err  


@responses.activate
def test_api_unavailable_exits_2(tmp_path, monkeypatch, capsys):
    configure(monkeypatch)
    for _ in range(3):
        responses.add(responses.GET, CONTRACTS_URL, status=503)

    code = run_cli(tmp_path)

    assert code == 2
    assert "unavailable after 3 attempts" in capsys.readouterr().err


@responses.activate
def test_api_rejecting_the_key_exits_2(tmp_path, monkeypatch, capsys):
    configure(monkeypatch)
    responses.add(responses.GET, CONTRACTS_URL, status=401)

    code = run_cli(tmp_path)

    assert code == 2
    assert "status 401" in capsys.readouterr().err


def test_unexpected_error_exits_3_and_traceback_is_logged(tmp_path, monkeypatch, capsys):
    configure(monkeypatch)

    def explode(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "run_pipeline", explode)  

    code = run_cli(tmp_path)

    assert code == 3
    assert "Unexpected error" in capsys.readouterr().err
    log_text = (tmp_path / "logs" / "bpa.log").read_text(encoding="utf-8")
    assert "RuntimeError: boom" in log_text


def test_invalid_arguments_exit_1_not_2(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main([])  

    assert exit_info.value.code == 1  
    assert "--input" in capsys.readouterr().err


def test_unusable_log_directory_exits_3(tmp_path, monkeypatch, capsys):
    configure(monkeypatch)
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a folder")

    code = run_cli(tmp_path, log_dir=blocker)

    assert code == 3
    assert "Cannot set up logging" in capsys.readouterr().err


@responses.activate
def test_settings_are_read_from_dotenv_file(tmp_path):
    (tmp_path / ".env").write_text(f"BPA_API_URL={BASE_URL}\nBPA_API_KEY=from-dotenv\n")
    serve_contracts()

    code = run_cli(tmp_path)

    assert code == 0
    assert responses.calls[0].request.headers["X-API-Key"] == "from-dotenv"


@responses.activate
def test_api_key_never_appears_in_output_or_logs(tmp_path, monkeypatch, capsys):
    configure(monkeypatch, key="super-secret-key")
    for _ in range(3):
        responses.add(responses.GET, CONTRACTS_URL, status=503)  

    run_cli(tmp_path)

    captured = capsys.readouterr()
    log_text = (tmp_path / "logs" / "bpa.log").read_text(encoding="utf-8")
    assert "super-secret-key" not in captured.out
    assert "super-secret-key" not in captured.err
    assert "super-secret-key" not in log_text

def test_module_entry_point_exits_with_the_cli_code(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["bpa"])  

    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("bpa", run_name="__main__")

    assert exit_info.value.code == 1
    assert "--input" in capsys.readouterr().err