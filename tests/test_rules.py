import json
from pathlib import Path

import pytest

from bpa.compare import MatchRecord, match_records_to_contracts
from bpa.config import RulesConfig, RuleSetting
from bpa.extract.files import read_attendance_file
from bpa.models import Contract, Severity
from bpa.rules import apply_rules
from bpa.validate import validate_attendance_rows
from tests.factories import make_contract, make_record

SAMPLE_DIR = Path(__file__).parent.parent / "data" / "sample"


def run(record, *contracts, config=None):
    matched = MatchRecord(record=record, contracts=tuple(contracts))
    return apply_rules([matched], config)


def codes(violations):
    return [violation.rule_code for violation in violations]


def test_unknown_employee_is_flagged_r1():
    violations = run(make_record(employee_id="M999"))

    assert codes(violations) == ["R1"]  
    assert violations[0].severity == Severity.BLOCKING  
    assert "M999" in violations[0].message


def test_valid_contract_gives_no_violation():
    assert run(make_record(), make_contract()) == []


def test_expired_contract_is_flagged_r2():
    contract = make_contract(end_date="2026-09-30")
    assert codes(run(make_record(date="2026-10-05"), contract)) == ["R2"]


@pytest.mark.parametrize("status", ["suspended", "terminated"])
def test_non_active_status_is_flagged_r2(status):
    assert codes(run(make_record(), make_contract(status=status))) == ["R2"]


def test_record_before_contract_start_is_flagged_r2():
    contract = make_contract(start_date="2026-11-01", end_date="2026-12-31")
    assert codes(run(make_record(date="2026-10-05"), contract)) == ["R2"]


def test_contract_boundaries_are_inclusive():
    contract = make_contract(start_date="2026-10-05", end_date="2026-10-07")
    assert run(make_record(date="2026-10-05"), contract) == [] 
    assert run(make_record(date="2026-10-07"), contract) == []  


def test_other_client_contract_is_flagged_r5_only():
    contract = make_contract(client="Beta Corp")
    assert codes(run(make_record(client="Acme"), contract)) == ["R5"]


def test_client_comparison_ignores_case():
    assert run(make_record(client="acme"), make_contract(client="ACME")) == []


def test_active_contract_of_another_client_does_not_hide_expired_one():
    expired_acme = make_contract(client="Acme", end_date="2026-09-30")
    active_beta = make_contract(client="Beta Corp")

    violations = run(make_record(client="Acme"), expired_acme, active_beta)

    assert codes(violations) == ["R2"]


def test_disabled_rule_produces_nothing():
    config = RulesConfig(settings={"R1": RuleSetting(enabled=False)})
    assert run(make_record(employee_id="M999"), config=config) == []


def test_severity_comes_from_config():
    config = RulesConfig(settings={"R1": RuleSetting(severity=Severity.WARNING)})

    violations = run(make_record(employee_id="M999"), config=config)

    assert violations[0].severity == Severity.WARNING


def test_violations_follow_record_order():
    records = [
        make_record(employee_id="M888", date="2026-10-07"),
        make_record(employee_id="M999", date="2026-10-05"),
    ]

    violations = apply_rules(match_records_to_contracts(records, []))

    assert [v.record.employee_id for v in violations] == ["M888", "M999"]


def test_sample_data_end_to_end():
    result = validate_attendance_rows(read_attendance_file(SAMPLE_DIR / "attendance.csv"))
    raw_contracts = json.loads((SAMPLE_DIR / "contracts.json").read_text())
    contracts = [Contract(**item) for item in raw_contracts]

    violations = apply_rules(match_records_to_contracts(result.valid, contracts))

    found = {
        (v.record.employee_id, v.record.date.isoformat(), v.rule_code) for v in violations
    }
    assert found == {
        ("M001", "2026-10-06", "R4"),  
        ("M002", "2026-10-05", "R2"),  
        ("M003", "2026-10-05", "R5"),  
        ("M003", "2026-10-06", "R3"),  
        ("M999", "2026-10-05", "R1"),  
    }
    assert len(violations) == 6 

def run_many(records, contracts):
    return apply_rules(match_records_to_contracts(records, contracts))

def test_hours_over_limit_is_flagged_r3_as_warning():
    violations = run(make_record(hours="11"), make_contract(max_daily_hours=8))

    assert codes(violations) == ["R3"]
    assert violations[0].severity == Severity.WARNING  
    assert "11" in violations[0].message and "8" in violations[0].message


def test_hours_equal_to_limit_are_accepted():
    assert run(make_record(hours="8"), make_contract(max_daily_hours=8)) == []


def test_r3_is_silent_without_applicable_contract():
    expired = make_contract(end_date="2026-09-30", max_daily_hours=8)


    assert codes(run(make_record(hours="20"), expired)) == ["R2"]


def test_most_generous_active_contract_applies():
    strict = make_contract(max_daily_hours=8)
    generous = make_contract(max_daily_hours=12)

    assert run(make_record(hours="10"), strict, generous) == []


def test_limit_of_inactive_contract_is_ignored():
    expired = make_contract(end_date="2026-09-30", max_daily_hours=12)
    active = make_contract(start_date="2026-10-01", max_daily_hours=8)

    violations = run(make_record(hours="10", date="2026-10-05"), expired, active)

    assert codes(violations) == ["R3"] 


def test_duplicate_lines_are_flagged_r4_on_each_occurrence():
    violations = run_many([make_record(), make_record()], [make_contract()])

    assert codes(violations) == ["R4", "R4"]
    assert violations[0].severity == Severity.BLOCKING
    assert "2 lines" in violations[0].message


def test_same_employee_on_different_days_is_not_duplicate():
    records = [make_record(date="2026-10-05"), make_record(date="2026-10-06")]
    assert run_many(records, [make_contract()]) == []


def test_different_employees_on_same_day_are_not_duplicates():
    records = [make_record(employee_id="M001"), make_record(employee_id="M002")]
    contracts = [make_contract(employee_id="M001"), make_contract(employee_id="M002")]
    assert run_many(records, contracts) == []


def test_duplicate_is_flagged_even_without_contract():
    records = [make_record(employee_id="M999"), make_record(employee_id="M999")]

    violations = run_many(records, [])

    assert codes(violations) == ["R1", "R4", "R1", "R4"]  