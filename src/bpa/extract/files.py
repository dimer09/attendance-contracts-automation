
from pathlib import Path
import datetime as dt

import pandas as pd

ALLOWED_EXTENSIONS = { ".csv", ".xlsx"}
MAX_FILE_SIZE_MB = 5 * 1024 * 1024  
REQUIRED_COLUMNS = [
    "employee_id",
    "name",
    "client",
    "date",
    "hours"
]

class FileReaderError(Exception):
    """Custom exception for file reading errors."""


def _check_file(path : Path) -> None:

    if not path.is_file():
        raise FileReaderError(f"File not found: {path}")
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise FileReaderError(f"Unsupported file extension: {path.suffix}. Allowed extensions are: {ALLOWED_EXTENSIONS}")
    if path.stat().st_size > MAX_FILE_SIZE_MB:
        raise FileReaderError(f"File size exceeds the maximum limit of {MAX_FILE_SIZE_MB / (1024 * 1024)} MB")

def normalize_cell(value) -> str:
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    return str(value)

def read_attendance_file(path: Path) -> list[dict[str, str]]:
    _check_file(path)
    try:
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
        elif path.suffix.lower() == ".xlsx":
            df = pd.read_excel(path, dtype=object, keep_default_na=False)
    except(pd.errors.EmptyDataError, pd.errors.ParserError, ValueError) as e:
        raise FileReaderError(f"Error reading file {path}: {e}")

    df.columns = [str(col).strip().lower() for col in df.columns]

    missing_columns = [ col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise FileReaderError(f"Missing required columns: {missing_columns}")


    records = df[REQUIRED_COLUMNS].to_dict(orient="records")
    return [{k: normalize_cell(v) for k, v in record.items()} for record in records]