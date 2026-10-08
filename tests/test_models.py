import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bpa.models import AttendanceRecord, Contract, ContractStatus


def make_data(**overrides):
    base = {
        "employee_id": "M001",
        "name": "Mbuyi",
        "client": "Acme",
        "date": "2026-10-05",
        "hours": "8",
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


def make_contract_data(**overrides):
    base = {
        "employee_id": "M001",
        "client": "Acme",
        "start_date": "2026-09-01",
        "end_date": "2026-12-31",
        "status": "active",
        "max_daily_hours": 10,
    }

    return {**base, **overrides}


def test_valid_contract_is_converted_and_cleaned():
    contract = Contract(**make_contract_data(employee_id=" M001 "))
    assert contract.employee_id == "M001"
    assert contract.status == ContractStatus.ACTIVE
    assert contract.end_date.month == 12


def test_unknowsn_status_is_rejected():
    with pytest.raises(ValidationError):
        Contract(**make_contract_data(status="actif"))


def test_end_date_before_start_date_is_rejected():
    with pytest.raises(ValidationError):
        Contract(**make_contract_data(start_date="2026-10-01", end_date="2026-09-30"))


def test_sample_contract_file_is_valid():
    path = Path(__file__).parent.parent / "data" / "sample" / "contracts.json"
    raws_contracts = json.loads(path.read_text())
    contracts = [Contract(**item) for item in raws_contracts]
    assert len(contracts) == 4
