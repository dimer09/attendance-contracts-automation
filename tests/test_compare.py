import json
from pathlib import Path

from bpa.compare import match_records_to_contracts
from bpa.extract.files import read_attendance_file
from bpa.models import Contract
from bpa.validate import validate_attendance_rows
from tests.factories import make_contract, make_record

SAMPLE_DIR = Path(__file__).parent.parent / "data" / "sample"


def test_record_is_matched_with_its_contract():
    contract = make_contract()

    matched = match_records_to_contracts([make_record()], [contract])

    assert matched[0].contracts == (contract,)


def test_unknown_employee_has_no_contracts():
    matched = match_records_to_contracts([make_record(employee_id="M999")], [make_contract()])

    assert matched[0].contracts == ()


def test_employee_with_several_contracts_gets_all_of_them():
    first = make_contract(start_date="2026-01-01", end_date="2026-06-30")
    second = make_contract(start_date="2026-09-01", end_date="2026-12-31")

    matched = match_records_to_contracts([make_record()], [first, second])

    assert matched[0].contracts == (first, second)


def test_records_keep_their_order():
    records = [
        make_record(date="2026-10-07"),
        make_record(employee_id="M002", date="2026-10-05"),
        make_record(date="2026-10-06"),
    ]

    matched = match_records_to_contracts(records, [make_contract()])

    assert [item.record for item in matched] == records


def test_empty_inputs_give_empty_output():
    assert match_records_to_contracts([], [make_contract()]) == []
    assert match_records_to_contracts([make_record()], [])[0].contracts == ()


def test_sample_data_end_to_end():
    result = validate_attendance_rows(read_attendance_file(SAMPLE_DIR / "attendance.csv"))
    raw_contracts = json.loads((SAMPLE_DIR / "contracts.json").read_text())
    contracts = [Contract(**item) for item in raw_contracts]

    matched = match_records_to_contracts(result.valid, contracts)

    assert len(matched) == 10
    unknown = [item for item in matched if not item.contracts]
    assert [item.record.employee_id for item in unknown] == ["M999"]
    m001 = [item for item in matched if item.record.employee_id == "M001"]
    assert all(len(item.contracts) == 1 for item in m001)
