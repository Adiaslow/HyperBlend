# hyperblend/infrastructure/repositories/sqlalchemy_repositories.py

"""SQLAlchemy implementations of the repository interfaces."""

from typing import List, Optional, Dict, Any, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, Column
from sqlalchemy.orm import selectinload
from sqlalchemy import inspect

from ...domain.interfaces.repositories import (
    CompoundRepository,
    SourceRepository,
    TargetRepository,
)
from ...domain.models import Compound, Source, BiologicalTarget
from ..repositories.models import (
    Compound as CompoundModel,
    Source as SourceModel,
    BiologicalTarget as TargetModel,
)


def convert_to_dict(model: Any) -> Dict[str, Any]:
    """Convert SQLAlchemy model to dictionary, handling Column types."""
    return {
        key: getattr(model, key) for key in model.__dict__ if not key.startswith("_")
    }


def get_column_value(column: Column[Any]) -> Any:
    """Extract the value from a SQLAlchemy Column."""
    return column.name if isinstance(column, Column) else column


def _to_domain_source(db_source: SourceModel) -> Source:
    """Convert a database source model to a domain model."""
    attrs = inspect(db_source).dict
    return Source(
        id=str(attrs["id"]),
        name=str(attrs["name"]),
        type=str(attrs["type"]),
        common_names=cast(Optional[List[str]], attrs.get("common_names")),
        description=str(attrs["description"]) if attrs.get("description") else None,
        native_regions=cast(Optional[List[str]], attrs.get("native_regions")),
        traditional_uses=cast(Optional[List[str]], attrs.get("traditional_uses")),
        compounds=(
            [_to_domain_compound(c) for c in db_source.compounds]
            if db_source.compounds
            else []
        ),
    )


def _to_domain_target(db_target: TargetModel) -> BiologicalTarget:
    """Convert a database target model to a domain model."""
    attrs = inspect(db_target).dict
    return BiologicalTarget(
        id=str(attrs["id"]),
        name=str(attrs["name"]),
        type=str(attrs["type"]),
        organism=str(attrs["organism"]),
        description=str(attrs["description"]) if attrs.get("description") else None,
        uniprot_id=str(attrs["uniprot_id"]) if attrs.get("uniprot_id") else None,
        chembl_id=str(attrs["chembl_id"]) if attrs.get("chembl_id") else None,
        compounds=[],  # Avoid circular dependency
    )


def _to_domain_compound(db_compound: CompoundModel) -> Compound:
    """Convert a database compound model to a domain model."""
    attrs = inspect(db_compound).dict
    return Compound(
        id=str(attrs["id"]),
        name=str(attrs["name"]),
        smiles=str(attrs["smiles"]) if attrs.get("smiles") else None,
        molecular_formula=(
            str(attrs["molecular_formula"]) if attrs.get("molecular_formula") else None
        ),
        molecular_weight=(
            float(attrs["molecular_weight"]) if attrs.get("molecular_weight") else None
        ),
        description=str(attrs["description"]) if attrs.get("description") else None,
        pubchem_id=str(attrs["pubchem_id"]) if attrs.get("pubchem_id") else None,
        chembl_id=str(attrs["chembl_id"]) if attrs.get("chembl_id") else None,
        pubchem_data=attrs.get("pubchem_data"),
        chembl_data=attrs.get("chembl_data"),
        last_updated=attrs["last_updated"],
        sources=[],  # Avoid circular dependency
        targets=(
            [_to_domain_target(t) for t in db_compound.targets]
            if db_compound.targets
            else []
        ),
    )


def _to_db_compound(entity: Compound) -> CompoundModel:
    """Convert a domain compound model to a database model."""
    return CompoundModel(
        id=entity.id,
        name=entity.name,
        smiles=entity.smiles,
        molecular_formula=entity.molecular_formula,
        molecular_weight=entity.molecular_weight,
        description=entity.description,
        pubchem_id=entity.pubchem_id,
        chembl_id=entity.chembl_id,
        pubchem_data=entity.pubchem_data,
        chembl_data=entity.chembl_data,
        last_updated=entity.last_updated,
    )


def _to_db_source(entity: Source) -> SourceModel:
    """Convert a domain source model to a database model."""
    return SourceModel(
        id=entity.id,
        name=entity.name,
        type=entity.type,
        common_names=entity.common_names,
        description=entity.description,
        native_regions=entity.native_regions,
        traditional_uses=entity.traditional_uses,
    )


def _to_db_target(entity: BiologicalTarget) -> TargetModel:
    """Convert a domain target model to a database model."""
    return TargetModel(
        id=entity.id,
        name=entity.name,
        type=entity.type,
        organism=entity.organism,
        description=entity.description,
        uniprot_id=entity.uniprot_id,
        chembl_id=entity.chembl_id,
    )


class SQLAlchemyCompoundRepository(CompoundRepository):
    """SQLAlchemy implementation of the CompoundRepository interface."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session

    async def get(self, id: str) -> Optional[Compound]:
        """Retrieve a compound by ID."""
        try:
            stmt = (
                select(CompoundModel)
                .options(
                    selectinload(CompoundModel.sources),
                    selectinload(CompoundModel.targets),
                )
                .where(CompoundModel.id == id)
            )
            result = await self.session.execute(stmt)
            db_compound = result.scalar_one_or_none()
            if not db_compound:
                return None
            return _to_domain_compound(db_compound)
        except Exception as e:
            print(f"Error in get: {e}")
            return None

    async def list(self, filters: Optional[Dict[str, Any]] = None) -> List[Compound]:
        """List all compounds, optionally filtered."""
        stmt = select(CompoundModel).options(
            selectinload(CompoundModel.sources), selectinload(CompoundModel.targets)
        )

        if filters:
            for key, value in filters.items():
                stmt = stmt.where(getattr(CompoundModel, key) == value)

        result = await self.session.execute(stmt)
        return list(_to_domain_compound(c) for c in result.scalars())

    async def add(self, entity: Compound) -> str:
        """Add a new compound."""
        db_compound = _to_db_compound(entity)
        self.session.add(db_compound)
        await self.session.commit()
        return str(db_compound.id)

    async def update(self, id: str, entity: Compound) -> bool:
        """Update an existing compound."""
        stmt = select(CompoundModel).where(CompoundModel.id == id)
        result = await self.session.execute(stmt)
        db_compound = result.scalar_one_or_none()

        if not db_compound:
            return False

        for key, value in vars(entity).items():
            if not key.startswith("_"):
                setattr(db_compound, key, value)

        await self.session.commit()
        return True

    async def delete(self, id: str) -> bool:
        """Delete a compound by ID."""
        stmt = delete(CompoundModel).where(CompoundModel.id == id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def get_by_pubchem_id(self, pubchem_id: str) -> Optional[Compound]:
        """Retrieve a compound by PubChem ID."""
        stmt = (
            select(CompoundModel)
            .options(
                selectinload(CompoundModel.sources), selectinload(CompoundModel.targets)
            )
            .where(CompoundModel.pubchem_id == pubchem_id)
        )
        result = await self.session.execute(stmt)
        db_compound = result.scalar_one_or_none()
        return _to_domain_compound(db_compound) if db_compound else None

    async def get_by_chembl_id(self, chembl_id: str) -> Optional[Compound]:
        """Retrieve a compound by ChEMBL ID."""
        stmt = (
            select(CompoundModel)
            .options(
                selectinload(CompoundModel.sources), selectinload(CompoundModel.targets)
            )
            .where(CompoundModel.chembl_id == chembl_id)
        )
        result = await self.session.execute(stmt)
        db_compound = result.scalar_one_or_none()
        return _to_domain_compound(db_compound) if db_compound else None


class SQLAlchemySourceRepository(SourceRepository):
    """SQLAlchemy implementation of the SourceRepository interface."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session

    async def get(self, id: str) -> Optional[Source]:
        """Retrieve a source by ID."""
        stmt = (
            select(SourceModel)
            .options(
                selectinload(SourceModel.compounds).selectinload(CompoundModel.targets)
            )
            .where(SourceModel.id == id)
        )
        result = await self.session.execute(stmt)
        db_source = result.scalar_one_or_none()
        return _to_domain_source(db_source) if db_source else None

    async def list(self, filters: Optional[Dict[str, Any]] = None) -> List[Source]:
        """List all sources, optionally filtered."""
        stmt = select(SourceModel).options(
            selectinload(SourceModel.compounds).selectinload(CompoundModel.targets)
        )

        if filters:
            for key, value in filters.items():
                stmt = stmt.where(getattr(SourceModel, key) == value)

        result = await self.session.execute(stmt)
        return list(_to_domain_source(s) for s in result.scalars())

    async def add(self, entity: Source) -> str:
        """Add a new source."""
        db_source = _to_db_source(entity)
        self.session.add(db_source)
        await self.session.commit()
        return str(db_source.id)

    async def update(self, id: str, entity: Source) -> bool:
        """Update an existing source."""
        stmt = (
            select(SourceModel)
            .options(selectinload(SourceModel.compounds))
            .where(SourceModel.id == id)
        )
        result = await self.session.execute(stmt)
        db_source = result.scalar_one_or_none()

        if not db_source:
            return False

        # Update scalar attributes
        for key, value in vars(entity).items():
            if not key.startswith("_") and key != "compounds":
                setattr(db_source, key, value)

        # Update compounds relationship
        if hasattr(entity, "compounds"):
            db_source.compounds = entity.compounds

        await self.session.commit()
        return True

    async def delete(self, id: str) -> bool:
        """Delete a source by ID."""
        stmt = delete(SourceModel).where(SourceModel.id == id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def get_by_name(self, name: str) -> Optional[Source]:
        """Retrieve a source by scientific name."""
        stmt = (
            select(SourceModel)
            .options(
                selectinload(SourceModel.compounds).selectinload(CompoundModel.targets)
            )
            .where(SourceModel.name == name)
        )
        result = await self.session.execute(stmt)
        db_source = result.scalar_one_or_none()
        return _to_domain_source(db_source) if db_source else None

    async def find_by_compound(self, compound_id: str) -> List[Source]:
        """Find all sources containing a specific compound."""
        stmt = (
            select(SourceModel)
            .join(SourceModel.compounds)
            .where(CompoundModel.id == compound_id)
            .options(
                selectinload(SourceModel.compounds).selectinload(CompoundModel.targets)
            )
        )
        result = await self.session.execute(stmt)
        return list(_to_domain_source(s) for s in result.scalars())


class SQLAlchemyTargetRepository(TargetRepository):
    """SQLAlchemy implementation of the TargetRepository interface."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session

    async def get(self, id: str) -> Optional[BiologicalTarget]:
        """Retrieve a target by ID."""
        stmt = (
            select(TargetModel)
            .options(selectinload(TargetModel.compounds))
            .where(TargetModel.id == id)
        )
        result = await self.session.execute(stmt)
        db_target = result.scalar_one_or_none()
        return _to_domain_target(db_target) if db_target else None

    async def list(
        self, filters: Optional[Dict[str, Any]] = None
    ) -> List[BiologicalTarget]:
        """List all targets, optionally filtered."""
        stmt = select(TargetModel).options(selectinload(TargetModel.compounds))

        if filters:
            for key, value in filters.items():
                stmt = stmt.where(getattr(TargetModel, key) == value)

        result = await self.session.execute(stmt)
        return list(_to_domain_target(t) for t in result.scalars())

    async def add(self, entity: BiologicalTarget) -> str:
        """Add a new target."""
        db_target = _to_db_target(entity)
        self.session.add(db_target)
        await self.session.commit()
        return str(db_target.id)

    async def update(self, id: str, entity: BiologicalTarget) -> bool:
        """Update an existing target."""
        stmt = select(TargetModel).where(TargetModel.id == id)
        result = await self.session.execute(stmt)
        db_target = result.scalar_one_or_none()

        if not db_target:
            return False

        for key, value in vars(entity).items():
            if not key.startswith("_"):
                setattr(db_target, key, value)

        await self.session.commit()
        return True

    async def delete(self, id: str) -> bool:
        """Delete a target by ID."""
        stmt = delete(TargetModel).where(TargetModel.id == id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def get_by_uniprot_id(self, uniprot_id: str) -> Optional[BiologicalTarget]:
        """Retrieve a target by UniProt ID."""
        stmt = (
            select(TargetModel)
            .options(selectinload(TargetModel.compounds))
            .where(TargetModel.uniprot_id == uniprot_id)
        )
        result = await self.session.execute(stmt)
        db_target = result.scalar_one_or_none()
        return _to_domain_target(db_target) if db_target else None

    async def get_by_chembl_id(self, chembl_id: str) -> Optional[BiologicalTarget]:
        """Retrieve a target by ChEMBL ID."""
        stmt = (
            select(TargetModel)
            .options(selectinload(TargetModel.compounds))
            .where(TargetModel.chembl_id == chembl_id)
        )
        result = await self.session.execute(stmt)
        db_target = result.scalar_one_or_none()
        return _to_domain_target(db_target) if db_target else None
