# hyperblend/application/services/graph_service.py

"""Service layer for managing the graph operations in HyperBlend."""

from typing import List, Dict, Set, Optional, Tuple
import networkx as nx
from pydantic import BaseModel

from ...domain.models.compounds import Compound
from ...domain.models.sources import Source
from ...domain.models.targets import BiologicalTarget
from ...domain.interfaces.repositories import (
    CompoundRepository,
    SourceRepository,
    TargetRepository,
)


class GraphAnalysisResult(BaseModel):
    """Model for representing graph analysis results."""

    compound_id: str
    source_interactions: List[Dict[str, float]]
    target_interactions: List[Dict[str, float]]
    total_activity_score: float
    confidence_score: float


class GraphService:
    """Service for managing and analyzing the compound-source-target graph."""

    def __init__(
        self,
        compound_repo: CompoundRepository,
        source_repo: SourceRepository,
        target_repo: TargetRepository,
    ):
        """Initialize the graph service with repositories."""
        self.compound_repo = compound_repo
        self.source_repo = source_repo
        self.target_repo = target_repo

        # Initialize graph structures
        self.compound_graph = nx.Graph()
        self.source_graph = nx.DiGraph()
        self.target_graph = nx.DiGraph()

    async def build_graphs(self):
        """Build all graph structures from repository data."""
        # Load all entities
        compounds = await self.compound_repo.list()
        sources = await self.source_repo.list()
        targets = await self.target_repo.list()

        # Build compound graph
        for compound in compounds:
            self.compound_graph.add_node(compound.id, data=compound.display_data)

        # Build source graph
        for source in sources:
            self.source_graph.add_node(source.id, data=source.display_data)
            for compound in source.compounds:
                self.source_graph.add_edge(source.id, compound.id)

        # Build target graph
        for target in targets:
            self.target_graph.add_node(target.id, data=target.display_data)
            for compound in target.compounds:
                self.target_graph.add_edge(compound.id, target.id)

    async def analyze_compound(self, compound_id: str) -> GraphAnalysisResult:
        """Analyze a compound's relationships in the graph.

        Args:
            compound_id: ID of the compound to analyze

        Returns:
            Analysis results including source and target interactions
        """
        compound = await self.compound_repo.get(compound_id)
        if not compound:
            raise ValueError(f"Compound {compound_id} not found")

        # Analyze source relationships
        source_interactions = []
        for source in compound.sources:
            source_interactions.append(
                {
                    "source_id": source.id,
                    "source_name": source.name,
                    "interaction_score": 1.0,  # Default score, could be based on concentration
                }
            )

        # Analyze target relationships
        target_interactions = []
        for target in compound.targets:
            target_interactions.append(
                {
                    "target_id": target.id,
                    "target_name": target.name,
                    "activity_score": 1.0,  # Default score, could be based on binding affinity
                }
            )

        return GraphAnalysisResult(
            compound_id=compound_id,
            source_interactions=source_interactions,
            target_interactions=target_interactions,
            total_activity_score=len(target_interactions),  # Simple scoring for now
            confidence_score=1.0 if target_interactions else 0.0,
        )
