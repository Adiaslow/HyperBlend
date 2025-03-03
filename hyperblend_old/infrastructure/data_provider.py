"""Data provider module that handles fallback to JSON files when database is empty."""

import json
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
import logging
import os
from neo4j import AsyncGraphDatabase

from ..domain.models import Compound, Source, Target, SourceType
from ..core.config import settings

logger = logging.getLogger(__name__)


class DataProvider:
    """Data provider that handles fallback to JSON files when database is empty."""

    def __init__(self):
        """Initialize the data provider."""
        self.data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        self._compounds_cache: Dict[str, Compound] = {}
        self._sources_cache: Dict[str, Source] = {}
        self._source_compounds: Dict[str, List[str]] = {}
        self._driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )

    async def load_plant_compounds(self) -> tuple[List[Compound], List[Source]]:
        """Load plant compounds from JSON file."""
        compounds: List[Compound] = []
        sources: List[Source] = []

        plant_compounds_file = self.data_dir / "plant-compounds.json"
        if not plant_compounds_file.exists():
            logger.error(f"Plant compounds file not found: {plant_compounds_file}")
            raise FileNotFoundError(
                f"Plant compounds file not found: {plant_compounds_file}"
            )

        try:
            with open(plant_compounds_file, "r") as f:
                data = json.load(f)

            logger.debug(f"Loaded {len(data)} plants from JSON file")

            async with self._driver.session() as session:
                for plant in data:
                    # Create source
                    source_id = f"S{len(sources) + 1:03d}"
                    taxonomy = plant["taxonomy"].copy()

                    # Handle array of species
                    if isinstance(taxonomy.get("species"), list):
                        taxonomy["species"] = ", ".join(taxonomy["species"])

                    # Convert taxonomy values to strings and remove prefixes
                    taxonomy = {
                        k: (
                            str(v).split()[-1]
                            if str(v).split()[-1] not in ["sp.", "spp."]
                            else ""
                        )
                        for k, v in taxonomy.items()
                    }

                    source = Source(
                        id=source_id,
                        name=plant["scientific_name"],
                        type=SourceType.PLANT,
                        common_names=[plant["name"]],
                        description="",
                        native_regions=[],  # Could be added to JSON
                        traditional_uses=[],  # Could be added to JSON
                        kingdom=taxonomy.get("kingdom", ""),
                        division=taxonomy.get("division", ""),
                        class_name=taxonomy.get("class", ""),
                        order=taxonomy.get("order", ""),
                        family=taxonomy.get("family", ""),
                        genus=taxonomy.get("genus", ""),
                        species=taxonomy.get("species", ""),
                    )
                    sources.append(source)
                    self._sources_cache[source_id] = source
                    self._source_compounds[source_id] = []

                    # Create source in Neo4j
                    await session.run(
                        """
                        MERGE (s:Source {id: $id})
                        SET s += $props
                        """,
                        {
                            "id": source_id,
                            "props": {
                                "name": source.name,
                                "type": source.type,
                                "common_names": source.common_names,
                                "description": source.description,
                                "native_regions": source.native_regions,
                                "traditional_uses": source.traditional_uses,
                                "kingdom": source.kingdom,
                                "division": source.division,
                                "class_name": source.class_name,
                                "order": source.order,
                                "family": source.family,
                                "genus": source.genus,
                                "species": source.species,
                            },
                        },
                    )

                    # Create compounds
                    for compound_data in plant["compounds"]:
                        compound_id = f"C{len(compounds) + 1:03d}"
                        compound = Compound(
                            id=compound_id,
                            name=compound_data["name"],
                            canonical_name=compound_data["name"].lower(),
                            description=compound_data.get("notes", ""),
                            smiles="",  # Could be added to JSON
                            molecular_formula="",  # Could be added to JSON
                            molecular_weight=None,  # Could be added to JSON
                            pubchem_id="",  # Could be added to JSON
                            chembl_id="",  # Could be added to JSON
                            coconut_id="",  # Could be added to JSON
                        )
                        compounds.append(compound)
                        self._compounds_cache[compound_id] = compound
                        self._source_compounds[source_id].append(compound_id)

                        # Create compound in Neo4j
                        await session.run(
                            """
                            MERGE (c:Compound {id: $id})
                            SET c += $props
                            """,
                            {
                                "id": compound_id,
                                "props": {
                                    "name": compound.name,
                                    "canonical_name": compound.canonical_name,
                                    "description": compound.description,
                                    "smiles": compound.smiles,
                                    "molecular_formula": compound.molecular_formula,
                                    "molecular_weight": compound.molecular_weight,
                                    "pubchem_id": compound.pubchem_id,
                                    "chembl_id": compound.chembl_id,
                                    "coconut_id": compound.coconut_id,
                                },
                            },
                        )

                        # Create relationship between source and compound
                        await session.run(
                            """
                            MATCH (s:Source {id: $source_id})
                            MATCH (c:Compound {id: $compound_id})
                            MERGE (s)-[:CONTAINS]->(c)
                            """,
                            {
                                "source_id": source_id,
                                "compound_id": compound_id,
                            },
                        )

            logger.info(
                f"Successfully loaded {len(compounds)} compounds and {len(sources)} sources"
            )
            return compounds, sources

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing plant compounds file: {str(e)}")
            raise
        except KeyError as e:
            logger.error(f"Missing required field in plant compounds file: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading plant compounds: {str(e)}")
            raise

    def _get_or_create_compound(
        self,
        name: str,
        compounds: List[Compound],
        description: str = "",
        category: str = "",
    ) -> str:
        """Get existing compound by name or create a new one."""
        # Check if compound already exists
        for compound_id, compound in self._compounds_cache.items():
            if compound.name.lower() == name.lower():
                return compound_id

        # Create new compound
        compound_id = f"C{len(compounds) + 1:03d}"

        compound = Compound(
            id=compound_id,
            name=name,
            canonical_name=name.lower(),
            description=(
                f"{description} ({category})"
                if description and category
                else description or category or ""
            ),
            smiles="",  # Could be added to JSON
            molecular_formula="",  # Could be added to JSON
            molecular_weight=None,  # Could be added to JSON
            pubchem_id="",  # Could be added to JSON
            chembl_id="",  # Could be added to JSON
            coconut_id="",  # Could be added to JSON
        )
        compounds.append(compound)
        self._compounds_cache[compound_id] = compound
        return compound_id

    def get_source_compounds(self, source_id: str) -> List[str]:
        """Get compound IDs for a source."""
        return self._source_compounds.get(source_id, [])
