from bpa.models import AttendanceRecord, Contract


def make_record(**overrides) -> AttendanceRecord:
    base = {
        "employee_id": "M001",
        "name": "Mbuyi",
        "client": "Acme",
        "date": "2026-10-05",
        "hours": "8",
    }
    return AttendanceRecord(**{**base, **overrides})


def make_contract(**overrides) -> Contract:
    base = {
        "employee_id": "M001",
        "client": "Acme",
        "start_date": "2026-09-01",
        "end_date": "2026-12-31",
        "status": "active",
        "max_daily_hours": 10,
    }
    return Contract(**{**base, **overrides})
