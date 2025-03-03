"""Enriched data provider that handles data enrichment and validation."""

import logging
from typing import List, Dict, Tuple, Optional, Any

from ..domain.models import Compound, Source, Target, TargetType
from .data_provider import DataProvider
from .enrichment import DataEnrichmentService

logger = logging.getLogger(__name__)


class EnrichedDataProvider:
    """Enriched data provider that handles data enrichment and validation."""

    def __init__(self):
        """Initialize the enriched data provider."""
        self.base_provider = DataProvider()
        self._compound_targets: Dict[str, List[str]] = {}
        self._source_compounds: Dict[str, List[str]] = {}
        self._enriched_compounds: Dict[str, Compound] = {}
        self._targets: Dict[str, Target] = {}
        self._target_synonyms: Dict[str, List[str]] = {}

    async def load_enriched_data(
        self,
    ) -> Tuple[List[Compound], List[Source], List[Target]]:
        """Load and enrich data from external sources."""
        logger.info("Starting to load enriched data...")

        # Load base data from JSON files
        logger.info("Loading base data from JSON files...")
        compounds, sources = await self.base_provider.load_plant_compounds()
        logger.info(
            f"Loaded {len(compounds)} compounds and {len(sources)} sources from JSON"
        )

        # Initialize source-compound relationships
        self._source_compounds = self.base_provider._source_compounds.copy()

        # Start data enrichment process
        logger.info("Starting data enrichment process...")
        enriched_compounds = []

        # Create enrichment service
        async with DataEnrichmentService() as enricher:
            # Enrich each compound with additional data
            for compound in compounds:
                try:
                    # First validate and standardize
                    if not self._validate_compound(compound):
                        logger.warning(f"Compound {compound.id} failed validation")
                        continue

                    standardized = self._standardize_compound(compound)
                    if not standardized:
                        logger.warning(f"Could not standardize compound {compound.id}")
                        continue

                    # Then enrich with external data
                    enriched = await enricher.enrich_compound(standardized)
                    if enriched:
                        self._enriched_compounds[enriched.id] = enriched
                        enriched_compounds.append(enriched)

                        # Get targets for enriched compound
                        targets = await enricher.get_compound_targets(enriched)
                        if targets:
                            # Store targets and relationships
                            for target in targets:
                                self._targets[target.id] = target
                                if enriched.id not in self._compound_targets:
                                    self._compound_targets[enriched.id] = []
                                self._compound_targets[enriched.id].append(target.id)

                except Exception as e:
                    logger.error(f"Error enriching compound {compound.id}: {str(e)}")
                    continue

        # Store target synonyms for better matching
        logger.info(f"Storing synonyms for {len(self._targets)} targets...")
        for target in self._targets.values():
            self._target_synonyms[target.id] = self._get_target_synonyms(target)

        logger.info(
            f"Data enrichment complete. Enriched {len(enriched_compounds)} compounds, "
            f"found {len(self._targets)} targets"
        )

        # Create compound-target relationships
        relationship_count = sum(
            len(targets) for targets in self._compound_targets.values()
        )
        logger.info(f"Created {relationship_count} compound-target relationships")

        return (
            list(self._enriched_compounds.values()),
            sources,
            list(self._targets.values()),
        )

    def _validate_compound(self, compound: Compound) -> bool:
        """Validate compound data."""
        if not compound.name:
            return False
        if not compound.id:
            return False
        return True

    def _standardize_compound(self, compound: Compound) -> Optional[Compound]:
        """Standardize compound data."""
        try:
            # Create a new compound with standardized data
            return Compound(
                id=compound.id,
                name=compound.name.strip(),
                canonical_name=compound.name.lower().strip(),
                description=(
                    compound.description.strip() if compound.description else ""
                ),
                smiles=compound.smiles.strip() if compound.smiles else "",
                molecular_formula=(
                    compound.molecular_formula.strip()
                    if compound.molecular_formula
                    else ""
                ),
                molecular_weight=compound.molecular_weight,
                pubchem_id=compound.pubchem_id.strip() if compound.pubchem_id else "",
                chembl_id=compound.chembl_id.strip() if compound.chembl_id else "",
                coconut_id=compound.coconut_id.strip() if compound.coconut_id else "",
            )
        except Exception as e:
            logger.error(f"Error standardizing compound {compound.id}: {str(e)}")
            return None

    def _get_target_synonyms(self, target: Target) -> List[str]:
        """Get synonyms for a target."""
        synonyms = [target.name, target.standardized_name]
        if target.gene_name:
            synonyms.append(target.gene_name)
        return list(set(syn.lower() for syn in synonyms if syn))

    def get_source_compounds(self, source_id: str) -> List[str]:
        """Get compound IDs for a source."""
        return self._source_compounds.get(source_id, [])
