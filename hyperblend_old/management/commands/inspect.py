# hyperblend/management/commands/inspect.py

"""Inspect database contents."""

import argparse
from typing import List, Optional
from sqlalchemy.orm import Session

from hyperblend_old.management import register_command
from hyperblend_old.infrastructure.repositories.models import (
    Compound,
    BiologicalTarget,
    Source,
)
from hyperblend_old.infrastructure.database import get_db


def inspect_db(name: Optional[str] = None) -> None:
    """Inspect database contents."""
    session = next(get_db())
    try:
        if name:
            # Search for compound by name
            compound = (
                session.query(Compound).filter(Compound.name.ilike(f"%{name}%")).first()
            )
            if compound:
                print(f"\nCompound: {compound.name}")
                print(f"SMILES: {compound.smiles}")
                print(f"Molecular Formula: {compound.molecular_formula}")
                print(f"Molecular Weight: {compound.molecular_weight}")
                print(f"Description: {compound.description}")
                print(f"PubChem Data: {compound.pubchem_data}")
                print(f"ChEMBL Data: {compound.chembl_data}")

                # Get sources
                sources = (
                    session.query(Source)
                    .join(Source.compounds)
                    .filter(Compound.id == compound.id)
                    .all()
                )
                if sources:
                    print("\nSources:")
                    for source in sources:
                        print(f"- {source.name} ({source.type})")

                # Get targets
                targets = (
                    session.query(BiologicalTarget)
                    .join(Compound.targets)
                    .filter(Compound.id == compound.id)
                    .all()
                )
                if targets:
                    print("\nTargets:")
                    for target in targets:
                        print(f"- {target.name} ({target.type})")
                        if getattr(target, "standardized_name", None):
                            print(f"  Standardized Name: {target.standardized_name}")
                        if getattr(target, "uniprot_id", None):
                            print(f"  UniProt: {target.uniprot_id}")
                        if getattr(target, "chembl_id", None):
                            print(f"  ChEMBL: {target.chembl_id}")
            else:
                print(f"No compound found with name containing '{name}'")
        else:
            # Show summary statistics
            compound_count = session.query(Compound).count()
            target_count = session.query(BiologicalTarget).count()
            source_count = session.query(Source).count()

            print("\nDatabase Summary:")
            print(f"Compounds: {compound_count}")
            print(f"Targets: {target_count}")
            print(f"Sources: {source_count}")
    finally:
        session.close()


@register_command("inspect")
def command_inspect(args: List[str]) -> None:
    """Command handler for inspect."""
    parser = argparse.ArgumentParser(description="Inspect database contents")
    parser.add_argument("--name", type=str, help="Name of compound to inspect")

    parsed_args = parser.parse_args(args)
    inspect_db(parsed_args.name)
