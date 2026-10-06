
from dataclasses import dataclass
from collections import defaultdict

from bpa.models import AttendanceRecord, Contract

@dataclass(frozen = True)
class MatchRecord :

    record : AttendanceRecord
    contracts : tuple[Contract, ...]

def match_records_to_contracts(
    records: list[AttendanceRecord],
    contracts: list[Contract],
) -> list[MatchRecord]:
    contracts_by_employee : dict[ str, list[Contract]] = defaultdict(list)

    for contract in contracts :
        contracts_by_employee[contract.employee_id].append(contract)

    result = []

    for record in records:
        matched = MatchRecord(
            record= record, 
            contracts= tuple(contracts_by_employee.get(record.employee_id, []))
        )

        result.append(matched)

    return result