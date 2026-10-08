import logging
from dataclasses import dataclass
from pathlib import Path

from bpa.compare import match_records_to_contracts
from bpa.config import RulesConfig
from bpa.extract.api_client import fetch_contracts
from bpa.extract.files import read_attendance_file
from bpa.models import RuleViolation, Severity
from bpa.report import generate_report, result_label
from bpa.rules import apply_rules
from bpa.validate import RejectedRow, validate_attendance_rows

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    run_id: str
    report_path: Path
    valid_count: int
    violations: list[RuleViolation]
    rejected: list[RejectedRow]

    @property
    def lines_read(self) -> int:
        return self.valid_count + len(self.rejected)

    @property
    def blocking_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.BLOCKING)

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.WARNING)

    @property
    def verdict(self) -> str:
        return result_label(self.blocking_count, self.warning_count, len(self.rejected))


def run_pipeline(
    input_path: Path,
    *,
    base_url: str,
    api_key: str,
    output_dir: Path,
    run_id: str,
    rules_config: RulesConfig | None = None,
) -> PipelineResult:
    validation = validate_attendance_rows(read_attendance_file(input_path))
    logger.info(
        "Read %s: %d valid rows, %d rejected",
        input_path.name,
        len(validation.valid),
        len(validation.rejected),
    )
    for rejected in validation.rejected:
        logger.warning("Rejected row %d: %s", rejected.row_number, rejected.reason)

    contracts = fetch_contracts(base_url, api_key)
    logger.info("Fetched %d contracts", len(contracts))

    matched = match_records_to_contracts(validation.valid, contracts)
    violations = apply_rules(matched, rules_config)
    logger.info("Rules applied: %d exceptions", len(violations))

    report_path = generate_report(
        output_dir,
        run_id=run_id,
        source_name=input_path.name,
        valid_count=len(validation.valid),
        violations=violations,
        rejected=validation.rejected,
    )
    logger.info("Report written: %s", report_path)

    result = PipelineResult(
        run_id=run_id,
        report_path=report_path,
        valid_count=len(validation.valid),
        violations=violations,
        rejected=validation.rejected,
    )
    logger.info("Run finished: %s", result.verdict)
    return result
