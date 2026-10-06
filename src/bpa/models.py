
from pydantic import BaseModel, ConfigDict, Field, model_validator
from enum import Enum
import datetime as dt
from dataclasses import dataclass

class AttendanceRecord(BaseModel):

    model_config = ConfigDict(str_strip_whitespace= True)

    employee_id : str = Field(min_length=1)
    name : str = Field(min_length=2, max_length=100)
    client : str = Field(min_length=2, max_length=100)
    date : dt.date
    hours : float = Field(gt=0, le=24)

class ContractStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"

class Contract(BaseModel):
    model_config = ConfigDict(str_strip_whitespace= True)

    employee_id : str = Field(min_length=1)
    client : str = Field(min_length=2, max_length=100)
    start_date : dt.date
    end_date : dt.date | None = None
    status : ContractStatus

    @model_validator(mode="after")
    def check_dates_order(self) -> "Contract":
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be after start_date")
        return self

class Severity(str, Enum):
    BLOCKING = "blocking"  
    WARNING = "warning"    

@dataclass(frozen=True)
class RuleViolation:

    rule_code: str
    severity: Severity
    record: AttendanceRecord
    message: str

    
        
