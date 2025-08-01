from typing import List, Dict, Optional
from pydantic import BaseModel, Field, conint, confloat, ConfigDict

MAX_LOAD = 2000
MAX_REPS = 100

class PlanItem(BaseModel):
    exercise: str
    order: conint(ge=1)
    reps: conint(ge=1, le=MAX_REPS)
    load: confloat(ge=0, le=MAX_LOAD)

    model_config = ConfigDict(extra="forbid")

class LogCompletedInput(BaseModel):
    exercise: str
    reps: conint(ge=1, le=MAX_REPS)
    load: confloat(ge=0, le=MAX_LOAD)

    model_config = ConfigDict(extra="forbid")

class RunSQLInput(BaseModel):
    query: str
    params: Optional[Dict] = None
    confirm: bool = False

    model_config = ConfigDict(extra="forbid")

