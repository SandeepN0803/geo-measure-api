from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str
    message: str


class FeatureResponse(BaseModel):
    """Schema for individual feature measurements."""

    id: Optional[int] = None
    file_id: Optional[str] = None
    feature_index: int
    geometry_type: Optional[str] = None
    geometry: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None
    measurement_type: Optional[str] = None
    measurement_value: Optional[float] = None
    unit: Optional[str] = None
    crs_used: Optional[str] = None
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FileInfoResponse(BaseModel):
    """Schema for uploaded file metadata response."""

    id: str
    filename: str
    feature_count: int
    crs: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MeasurementsListResponse(BaseModel):
    """Schema for file info along with its complete list of feature measurements."""

    file: FileInfoResponse
    features: List[FeatureResponse] = []

    model_config = ConfigDict(from_attributes=True)
