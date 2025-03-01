"""SQLAlchemy repository for managing external compound data."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime

from .sqlalchemy_models import ExternalCompoundData


class SQLAlchemyExternalCompoundDataRepository:
    """Repository for managing external compound data from ChEMBL and PubChem."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session

    async def get_by_compound_id(self, compound_id: str) -> Optional[Dict[str, Any]]:
        """Get external data for a compound by its ID."""
        stmt = select(ExternalCompoundData).where(
            ExternalCompoundData.compound_id == compound_id
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return model and {
            key: getattr(model, key)
            for key in model.__dict__
            if not key.startswith("_")
        }

    async def get_by_chembl_id(self, chembl_id: str) -> Optional[Dict[str, Any]]:
        """Get external data by ChEMBL ID."""
        stmt = select(ExternalCompoundData).where(
            ExternalCompoundData.chembl_id == chembl_id
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return model and {
            key: getattr(model, key)
            for key in model.__dict__
            if not key.startswith("_")
        }

    async def get_by_pubchem_id(self, pubchem_id: str) -> Optional[Dict[str, Any]]:
        """Get external data by PubChem ID."""
        stmt = select(ExternalCompoundData).where(
            ExternalCompoundData.pubchem_id == pubchem_id
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return model and {
            key: getattr(model, key)
            for key in model.__dict__
            if not key.startswith("_")
        }

    async def upsert(self, compound_id: str, data: Dict[str, Any]) -> str:
        """Create or update external data for a compound."""
        stmt = select(ExternalCompoundData).where(
            ExternalCompoundData.compound_id == compound_id
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            # Update existing record
            for key, value in data.items():
                if hasattr(model, key):
                    setattr(model, key, value)
            model.last_updated = datetime.utcnow()
        else:
            # Create new record
            data["compound_id"] = compound_id
            model = ExternalCompoundData(**data)
            self.session.add(model)

        await self.session.commit()
        return model.id

    async def delete(self, compound_id: str) -> bool:
        """Delete external data for a compound."""
        stmt = delete(ExternalCompoundData).where(
            ExternalCompoundData.compound_id == compound_id
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
