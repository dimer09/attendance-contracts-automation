import argparse
import logging
import sys
from pathlib import Path
from typing import NoReturn

from dotenv import load_dotenv

from bpa.config import ConfigError, load_settings
from bpa.extract.api_client import ApiError
from bpa.extract.files import FileReaderError
from bpa.logging_setup import generate_run_id, setup_logging, teardown_logging
from bpa.pipeline import PipelineResult, run_pipeline

EXIT_OK = 0
EXIT_INPUT_ERROR = 1  
EXIT_API_ERROR = 2    
EXIT_UNEXPECTED = 3 

logger = logging.getLogger(__name__)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
       
        self.print_usage(sys.stderr)
        self.exit(EXIT_INPUT_ERROR, f"{self.prog}: error: {message}\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="bpa",
        description="Reconcile client timesheets with employee contracts and write an Excel report.",
    )
    parser.add_argument("--input", required=True, type=Path, help="timesheet file (.csv or .xlsx)")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("reports"),
        help="folder for the Excel report (default: reports)",
    )
    parser.add_argument(
        "--log-dir", type=Path, default=Path("logs"),
        help="folder for the log file (default: logs)",
    )
    return parser


def _print_summary(result: PipelineResult) -> None:
    print(f"Run ID: {result.run_id}")
    print(f"Report: {result.report_path}")
    print(
        f"Lines read: {result.lines_read} "
        f"(valid: {result.valid_count}, rejected: {len(result.rejected)})"
    )
    print(
        f"Exceptions: {len(result.violations)} "
        f"(blocking: {result.blocking_count}, warnings: {result.warning_count})"
    )
    print(f"Result: {result.verdict}")


def _run(args: argparse.Namespace, run_id: str) -> int:
    try:
        settings = load_settings()
        result = run_pipeline(
            args.input,
            base_url=settings.api_base_url,
            api_key=settings.api_key,
            output_dir=args.output_dir,
            run_id=run_id,
        )
    except (FileReaderError, ConfigError) as exc:
        logger.error("Input problem: %s", exc)
        return EXIT_INPUT_ERROR
    except ApiError as exc:
        message = str(exc)

        if message.startswith("HTTP "):
            message = message.removeprefix("HTTP ")

        logger.error("Contracts API problem: status %s", message)
        return EXIT_API_ERROR
    except Exception:
        logger.exception("Unexpected error")
        return EXIT_UNEXPECTED

    _print_summary(result)
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Run the program and return the exit code."""
    args = _build_parser().parse_args(argv)

    load_dotenv(".env")

    run_id = generate_run_id()
    try:
        setup_logging(run_id, args.log_dir)
    except OSError as exc:
        
        print(f"Cannot set up logging in {args.log_dir}: {exc}", file=sys.stderr)
        return EXIT_UNEXPECTED

    try:
        return _run(args, run_id)
    finally:
        teardown_logging()  