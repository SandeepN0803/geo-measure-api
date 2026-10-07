from pydantic import BaseModel, ConfigDict
from typing import Optional


class HealthResponse(BaseModel):
    status: str
    message: str


class FileInfoResponse(BaseModel):
    id: Optional[int] = None
    filename: str
    feature_count: int
    crs: Optional[str] = None
    status: str

    model_config = ConfigDict(from_attributes=True)
