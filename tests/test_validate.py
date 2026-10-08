from pathlib import Path

from bpa.extract.files import read_attendance_file
from bpa.validate import validate_attendance_rows


def make_rows(**overrides):
    base = {
        "employee_id": "M001",
        "name": "Mbuyi",
        "client": "Acme",
        "date": "2026-10-05",
        "hours": "8",
    }

    return {**base, **overrides}


def test_all_valid_rows_are_accepted():
    result = validate_attendance_rows([make_rows(), make_rows(date="2026-10-06")])
    assert len(result.valid) == 2
    assert result.rejected == []


def test_rejected_row_keeps_row_number_and_reason():
    result = validate_attendance_rows([make_rows(), make_rows(hours="-3")])

    assert len(result.valid) == 1
    assert len(result.rejected) == 1
    rejected_row = result.rejected[0]
    assert rejected_row.row_number == 2
    assert rejected_row.raw["hours"] == "-3"
    assert "hours" in rejected_row.reason


def test_valid_rows_keep_their_order():
    rows = [
        make_rows(date="2026-10-05"),
        make_rows(date="2026-10-06"),
        make_rows(hours="-3"),
        make_rows(date="2026-10-07"),
    ]
    result = validate_attendance_rows(rows)

    assert [record.date.day for record in result.valid] == [5, 6, 7]


def test_all_errors_of_one_row_are_collected():
    result = validate_attendance_rows([make_rows(hours="-3", date="2026-13-05")])

    assert len(result.valid) == 0
    assert len(result.rejected) == 1
    rejected_row = result.rejected[0]
    assert rejected_row.row_number == 1
    assert "hours" in rejected_row.reason
    assert "date" in rejected_row.reason


def test_empty_input_gives_empty_result():
    result = validate_attendance_rows([])
    assert result.valid == []
    assert result.rejected == []


def test_sample_file_end_to_end():
    path = Path(__file__).parent.parent / "data" / "sample" / "attendance.csv"
    rows = read_attendance_file(path)
    result = validate_attendance_rows(rows)

    assert len(result.valid) == 10
    assert len(result.rejected) == 2
    rejected_row = result.rejected[0]
    assert rejected_row.row_number == 11
    assert rejected_row.raw["hours"] == "-3"
