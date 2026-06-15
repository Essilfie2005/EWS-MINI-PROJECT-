import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SyntheticGenerateRequest(BaseModel):
    n_samples: int = Field(
        default=500,
        ge=1,
        le=100000,
        description="Number of synthetic student records to generate"
    )

    include_labels: bool = True

    overwrite_existing: bool = False


class SyntheticResponse(BaseModel):
    generated: int

    message: str

    generation_time_seconds: Optional[float] = None

    dataset_name: Optional[str] = None

    generated_at: datetime.datetime

    records_saved: bool = True
