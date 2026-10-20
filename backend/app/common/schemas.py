from typing import Any, Dict, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class APIResponse(BaseModel, Generic[DataT]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[DataT] = None
    correlation_id: Optional[str] = None


class ErrorDetail(BaseModel):
    message: str
    code: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    correlation_id: Optional[str] = None


class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Service status: healthy or degraded")
    timestamp: str
    database: str = Field(..., description="Database connectivity status")
    version: str = "1.0.0"
    environment: str
