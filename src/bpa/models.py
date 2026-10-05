
from pydantic import BaseModel, ConfigDict, Field
import datetime as dt

class AttendanceRecord(BaseModel):

    model_config = ConfigDict(str_strip_whitespace= True)

    employee_id : str = Field(min_length=1)
    name : str = Field(min_length=2, max_length=100)
    client : str = Field(min_length=2, max_length=100)
    date : dt.date
    hours : float = Field(gt=0, le=24)