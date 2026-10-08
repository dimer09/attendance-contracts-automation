# Attendance Contracts Automation

[![CI](https://github.com/dimer09/attendance-contracts-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/dimer09/attendance-contracts-automation/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-%203.12-blue)](https://www.python.org/)

Automated reconciliation of employee timesheets against employment contracts for temporary staffing agencies.

The pipeline validates attendance files, retrieves contracts through a REST API, applies business rules, generates an Excel report and produces structured audit logs for each execution.

## Problem

Reconciling client timesheets with employee contracts is often done manually in Excel. This can lead to:

* expired or inactive contracts;
* excessive working hours;
* duplicate attendance records;
* incorrect client assignments;
* missing employees;
* poorly formatted input data.

This project automates these checks and clearly separates invalid data from business exceptions.

## Features

* CSV and XLSX input.
* Strict data validation with Pydantic.
* REST API integration with timeout and retry handling.
* Contract-to-timesheet reconciliation.
* Five configurable business rules.
* Excel report with `Summary`, `Exceptions` and `Rejected rows` sheets.
* Structured JSON logs with a unique execution ID.
* Optional email notification.
* Distinct CLI exit codes for automation and monitoring.
* Unit, integration and end-to-end tests.
* GitHub Actions CI on Python 3.11 and 3.12.

## Business Rules

| Code | Rule                              | Severity |
| ---- | --------------------------------- | -------- |
| R1   | Employee not found in contracts   | Blocking |
| R2   | Contract inactive or expired      | Blocking |
| R3   | Hours exceed daily contract limit | Warning  |
| R4   | Duplicate employee/date           | Blocking |
| R5   | Client differs from contract      | Blocking |

## Example

```text
$ python -m bpa --input data/sample/attendance.csv

Run ID: 20261006-143000-a1b2c3d4
Report: reports/report_20261006-143000-a1b2c3d4.xlsx
Lines read: 12 (valid: 10, rejected: 2)
Exceptions: 6 (blocking: 5, warnings: 1)
Result: ACTION REQUIRED
```

Sample data is fictional and designed to trigger the business rules.

## Quick Start

Requires Python 3.11+.

```bash
git clone https://github.com/dimer09/attendance-contracts-automation.git
cd attendance-contracts-automation

python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
pip install -e .
```

Create the environment file:

```bash
# Linux/macOS
cp .env.example .env

# Windows
copy .env.example .env
```

Start the mock contracts API:

```bash
python -m uvicorn mock_api.main:app --port 8000
```

Run the pipeline:

```bash
python -m bpa --input data/sample/attendance.csv
```

The report is generated in `reports/` and logs in `logs/bpa.log`.

## Input

The attendance file must contain:

```text
employee_id
name
client
date
hours
```

Supported formats: `.csv` and `.xlsx`.

## Exit Codes

| Code | Meaning                        |
| ---- | ------------------------------ |
| `0`  | Processing completed           |
| `1`  | Invalid input or configuration |
| `2`  | Contracts API error            |
| `3`  | Unexpected error               |

## Quality

```bash
pytest --cov=bpa
ruff check .
ruff format --check .
```

The project uses unit, integration and end-to-end tests with a minimum coverage threshold of 70%.

```

## Limitations

This is an MVP. The contracts API is simulated, the input format is currently fixed, and there is no Docker deployment yet.


