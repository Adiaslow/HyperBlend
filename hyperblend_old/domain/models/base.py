"""Base model classes for domain entities."""

from typing import Optional
from pydantic import BaseModel, Field


class BaseEntity(BaseModel):
    """Base class for all domain entities."""

    id: str = Field(..., description="Unique identifier")

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
        validate_assignment = True
        populate_by_name = True


class BaseNamedEntity(BaseEntity):
    """Base class for named entities."""

    name: str = Field(..., description="Entity name")
    description: str = Field("", description="Entity description")
