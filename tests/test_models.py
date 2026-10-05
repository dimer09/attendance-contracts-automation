from bpa.models import AttendanceRecord

import pytest
from pydantic import ValidationError

def make_data(**overrides):
    base = {
        "employee_id": "M001",
        "name": "Mbuyi",
        "client": "Acme",
        "date": "2026-10-05",
        "hours": "8"
    }

    return {**base, **overrides}


def test_valid_record_is_converted_and_cleaned():
    record = AttendanceRecord(**make_data(employee_id=" M001 "))
    assert record.employee_id == "M001"
    assert record.hours == 8.0
    assert record.date.year == 2026

def test_negative_hours_are_rejected():
    with pytest.raises(ValidationError):
        AttendanceRecord(**make_data(hours=-1))

def test_invalidate_date_is_rejected():
    with pytest.raises(ValidationError):
        AttendanceRecord(**make_data(date="2026-13-05"))