"""Service for managing compounds and their external data."""

from typing import Dict, List, Optional, Any, cast
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from hyperblend_old.domain.models.compounds import Compound
from hyperblend_old.domain.models.targets import BiologicalTarget
from hyperblend_old.domain.chemistry import chemistry_utils


class CompoundService:
    """Service for managing compounds and their external data."""

    def __init__(self, session: Session):
        """Initialize the compound service.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def get_compound_by_pubchem_id(self, pubchem_id: str) -> Optional[Compound]:
        """Get a compound by its PubChem ID, fetching and caching external data if needed.

        Args:
            pubchem_id: PubChem Compound ID (CID)

        Returns:
            Compound object if found, None otherwise
        """
        # Check if compound exists in database
        stmt = select(Compound).where(Compound.pubchem_id == pubchem_id)
        compound = self.session.execute(stmt).scalar_one_or_none()

        if compound:
            # Fetch data from external sources
            self._update_external_data(compound)
            return compound

        # Fetch data from external sources
        pubchem_data = chemistry_utils.get_pubchem_info(pubchem_id)
        if not pubchem_data:
            return None

        # Create new compound
        compound = Compound()
        setattr(compound, "id", f"CMP-{pubchem_id}")
        setattr(compound, "name", pubchem_data["name"])
        setattr(compound, "smiles", pubchem_data["smiles"])
        setattr(compound, "molecular_formula", pubchem_data["molecular_formula"])
        setattr(compound, "molecular_weight", pubchem_data["molecular_weight"])
        setattr(
            compound,
            "description",
            f"Compound imported from PubChem (CID: {pubchem_id})",
        )
        setattr(compound, "pubchem_id", pubchem_id)
        setattr(compound, "pubchem_data", pubchem_data)

        # Get ChEMBL data
        chembl_data = chemistry_utils.get_chembl_info(pubchem_id)
        if chembl_data:
            setattr(compound, "chembl_id", chembl_data["chembl_id"])
            setattr(compound, "chembl_data", chembl_data)

            # Process target interactions
            self._process_target_interactions(
                compound, chembl_data["target_interactions"]
            )

        self.session.add(compound)
        self.session.commit()
        return compound

    def _update_external_data(self, compound: Compound) -> None:
        """Update external data for a compound.

        Args:
            compound: Compound object to update
        """
        # Update PubChem data
        pubchem_id = getattr(compound, "pubchem_id", None)
        if pubchem_id:
            pubchem_data = chemistry_utils.get_pubchem_info(str(pubchem_id))
            if pubchem_data:
                setattr(compound, "pubchem_data", pubchem_data)
                setattr(compound, "name", pubchem_data["name"])
                setattr(compound, "smiles", pubchem_data["smiles"])
                setattr(
                    compound, "molecular_formula", pubchem_data["molecular_formula"]
                )
                setattr(compound, "molecular_weight", pubchem_data["molecular_weight"])

        # Update ChEMBL data
        if pubchem_id:
            chembl_data = chemistry_utils.get_chembl_info(str(pubchem_id))
            if chembl_data:
                setattr(compound, "chembl_id", chembl_data["chembl_id"])
                setattr(compound, "chembl_data", chembl_data)

                # Update target interactions
                self._process_target_interactions(
                    compound, chembl_data["target_interactions"]
                )

        self.session.commit()

    def _process_target_interactions(
        self, compound: Compound, interactions: List[Dict[str, Any]]
    ) -> None:
        """Process and store target interactions for a compound.

        Args:
            compound: Compound object to update
            interactions: List of target interaction data from ChEMBL
        """
        # Clear existing target associations
        compound.targets = []

        for interaction in interactions:
            # Get or create target
            stmt = select(BiologicalTarget).where(
                BiologicalTarget.chembl_id == interaction["target_chembl_id"]
            )
            target = self.session.execute(stmt).scalar_one_or_none()

            if not target:
                target = BiologicalTarget()
                setattr(target, "id", f"TGT-{interaction['target_chembl_id']}")
                setattr(target, "name", interaction["target_name"])
                setattr(target, "type", interaction["target_type"])
                setattr(target, "chembl_id", interaction["target_chembl_id"])
                self.session.add(target)

            # Add target association with activity data
            compound.targets.append(target)

            # Update the association table with activity data
            stmt = (
                update(compound.compound_targets)
                .where(
                    compound.compound_targets.c.compound_id == compound.id,
                    compound.compound_targets.c.target_id == target.id,
                )
                .values(
                    activity_type=interaction["activity_type"],
                    activity_value=interaction["activity_value"],
                    activity_unit=interaction["activity_unit"],
                )
            )
            self.session.execute(stmt)
