import datetime as dt
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

from bpa.compare import MatchRecord
from bpa.config import RulesConfig
from bpa.models import Contract, ContractStatus, RuleViolation


@dataclass(frozen=True)
class RunContext:
    lines_per_employee_day: Counter[tuple[str, dt.date]]


Check = Callable[[MatchRecord, RunContext], str | None]


@dataclass(frozen=True)
class Rule:
    code: str
    check: Check


def _same_client(first: str, second: str) -> bool:
    return first.casefold() == second.casefold()


def _contracts_for_client(matched: MatchRecord) -> list[Contract]:
    client = matched.record.client
    return [c for c in matched.contracts if _same_client(c.client, client)]


def _is_active_on(contract: Contract, day: dt.date) -> bool:
    return (
        contract.status == ContractStatus.ACTIVE and contract.start_date <= day <= contract.end_date
    )


def check_unknown_employee(matched: MatchRecord, context: RunContext) -> str | None:
    if matched.contracts:
        return None
    return f"No contract found for employee {matched.record.employee_id}"


def check_inactive_contract(matched: MatchRecord, context: RunContext) -> str | None:
    client_contracts = _contracts_for_client(matched)
    if not client_contracts:
        return None
    day = matched.record.date
    if any(_is_active_on(contract, day) for contract in client_contracts):
        return None
    return f"No active contract for client '{matched.record.client}' on {day.isoformat()}"


def check_hours_over_limit(matched: MatchRecord, context: RunContext) -> str | None:
    day = matched.record.date
    active = [c for c in _contracts_for_client(matched) if _is_active_on(c, day)]
    if not active:
        return None
    limit = max(contract.max_daily_hours for contract in active)
    hours = matched.record.hours
    if hours <= limit:
        return None
    return f"{hours:g} hours exceed the daily limit of {limit:g} hours"


def check_duplicate_line(matched: MatchRecord, context: RunContext) -> str | None:
    key = (matched.record.employee_id, matched.record.date)
    count = context.lines_per_employee_day[key]
    if count <= 1:
        return None
    return f"{count} lines for employee {key[0]} on {key[1].isoformat()}"


def check_client_mismatch(matched: MatchRecord, context: RunContext) -> str | None:
    if not matched.contracts:
        return None
    if _contracts_for_client(matched):
        return None
    clients = ", ".join(sorted({contract.client for contract in matched.contracts}))
    return f"Timesheet client '{matched.record.client}' differs from contract client(s): {clients}"


RULES: tuple[Rule, ...] = (
    Rule("R1", check_unknown_employee),
    Rule("R2", check_inactive_contract),
    Rule("R3", check_hours_over_limit),
    Rule("R4", check_duplicate_line),
    Rule("R5", check_client_mismatch),
)


def apply_rules(
    matched_records: list[MatchRecord],
    config: RulesConfig | None = None,
) -> list[RuleViolation]:
    if config is None:
        config = RulesConfig()

    context = RunContext(
        lines_per_employee_day=Counter(
            (matched.record.employee_id, matched.record.date) for matched in matched_records
        )
    )

    violations: list[RuleViolation] = []
    for matched in matched_records:
        for rule in RULES:
            setting = config.setting_for(rule.code)
            if not setting.enabled:
                continue
            message = rule.check(matched, context)
            if message is not None:
                violations.append(
                    RuleViolation(rule.code, setting.severity, matched.record, message)
                )
    return violations
