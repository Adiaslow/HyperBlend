from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BaseEntity(BaseModel):
    """Base model for all entities in the system."""

    id: str = Field(..., description="Unique identifier for the entity")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(
        ..., description="Source database where the data was retrieved from"
    )
    external_id: Optional[str] = Field(
        None, description="External ID from the source database"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for the data"
    )

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {datetime: lambda v: v.isoformat()}
