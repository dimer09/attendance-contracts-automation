

from dataclasses import dataclass

from pydantic import ValidationError

from bpa.models import AttendanceRecord

@dataclass(frozen=True)
class RejectedRow:
    row_number : int
    raw:  dict [str, str]
    reason: str

@dataclass(frozen=True)
class ValidationResult :
    valid: list[AttendanceRecord]
    rejected :list[RejectedRow]

def _format_errors(error : ValidationError) -> str:
    return "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in error.errors()])

def validate_attendance_rows(rows : list[dict[str, str]]) -> ValidationResult:
    valid_records : list[AttendanceRecord] = []
    rejected_rows : list[RejectedRow] = []

    for index, row in enumerate(rows):
        try:
            record = AttendanceRecord(**row)
            valid_records.append(record)
        except ValidationError as e:
            rejected_rows.append(RejectedRow(row_number=index + 1, raw=row, reason=_format_errors(e)))

    return ValidationResult(valid=valid_records, rejected=rejected_rows)