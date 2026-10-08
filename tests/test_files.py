import datetime as dt
from pathlib import Path

import pandas as pd
import pytest

from bpa.extract.files import FileReaderError, read_attendance_file

CSV_CONTENT = """employee_id,name,client,date,hours
M001,Mbuyi,Acme,2026-10-05,8
M002,Smith,Acme,2026-10-05,8
M003,Johnson,Acme,2026-10-05,8
"""


def test_read_csv_as_raw_text(tmp_path):
    csv_file = tmp_path / "attendance.csv"
    csv_file.write_text(CSV_CONTENT)

    rows = read_attendance_file(csv_file)

    assert rows == [
        {
            "employee_id": "M001",
            "name": "Mbuyi",
            "client": "Acme",
            "date": "2026-10-05",
            "hours": "8",
        },
        {
            "employee_id": "M002",
            "name": "Smith",
            "client": "Acme",
            "date": "2026-10-05",
            "hours": "8",
        },
        {
            "employee_id": "M003",
            "name": "Johnson",
            "client": "Acme",
            "date": "2026-10-05",
            "hours": "8",
        },
    ]


def test_reads_excel_with_real_date_cells(tmp_path):
    excel_file = tmp_path / "attendance.xlsx"
    df = pd.DataFrame(
        {
            "employee_id": ["M001", "M002", "M003"],
            "name": ["Mbuyi", "Smith", "Johnson"],
            "client": ["Acme", "Acme", "Acme"],
            "date": [dt.datetime(2026, 10, 5), dt.datetime(2026, 10, 5), dt.datetime(2026, 10, 5)],
            "hours": [8, 8, 8],
        }
    )
    df.to_excel(excel_file, index=False)

    rows = read_attendance_file(excel_file)

    assert rows[0] == {
        "employee_id": "M001",
        "name": "Mbuyi",
        "client": "Acme",
        "date": "2026-10-05",
        "hours": "8",
    }
    assert rows[1] == {
        "employee_id": "M002",
        "name": "Smith",
        "client": "Acme",
        "date": "2026-10-05",
        "hours": "8",
    }
    assert rows[2] == {
        "employee_id": "M003",
        "name": "Johnson",
        "client": "Acme",
        "date": "2026-10-05",
        "hours": "8",
    }


def test_unsupported_file_extension(tmp_path):
    unsupported_file = tmp_path / "attendance.txt"
    unsupported_file.write_text("Some content")

    with pytest.raises(FileReaderError, match="Unsupported"):
        read_attendance_file(unsupported_file)


def test_missing_file_is_rejected(tmp_path):
    missing_file = tmp_path / "nonexistent.csv"

    with pytest.raises(FileReaderError, match="File not found"):
        read_attendance_file(missing_file)


def test_too_large_file_is_rejected(tmp_path):
    large_file = tmp_path / "large.csv"
    large_file.write_bytes(b"0" * (5 * 1024 * 1024 + 1))

    with pytest.raises(FileReaderError, match="File size exceeds the maximum limit"):
        read_attendance_file(large_file)


def test_missing_required_columns_is_rejected(tmp_path):
    incomplete_csv = tmp_path / "incomplete.csv"
    incomplete_csv.write_text("employee_id,name,date,hours\nM001,Mbuyi,2026-10-05,8")

    with pytest.raises(FileReaderError, match="client"):
        read_attendance_file(incomplete_csv)


def test_empty_csv_is_rejected(tmp_path):
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("")

    with pytest.raises(FileReaderError, match="Error reading file"):
        read_attendance_file(empty_csv)


def test_sample_file_keeps_invalid_rows():
    path = Path(__file__).parent.parent / "data" / "sample" / "attendance.csv"
    rows = read_attendance_file(path)

    assert len(rows) == 12
    assert rows[-1]["date"] == "not-a-date"


def test_corrupt_excel_file_is_rejected(tmp_path):
    path = tmp_path / "attendance.xlsx"
    path.write_bytes(b"this is not a real Excel file")

    with pytest.raises(FileReaderError, match="Error reading file"):
        read_attendance_file(path)
