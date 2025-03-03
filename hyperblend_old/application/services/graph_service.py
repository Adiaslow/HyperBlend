# hyperblend/application/services/graph_service.py

"""Service layer for managing the graph operations in HyperBlend."""

from typing import List, Dict, Set, Optional, Tuple
import networkx as nx
from pydantic import BaseModel
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

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

    async def visualize_network(
        self,
        k: float = 1.0,
        iterations: int = 50,
        scale: int = 1,
        node_size: int = 1000,
        font_size: int = 8,
        with_labels: bool = True,
        seed: Optional[int] = None,
    ) -> Figure:
        """Visualize the compound-target network using a spring layout.

        Args:
            k: Optimal distance between nodes
            iterations: Number of iterations to compute layout
            scale: Scale factor for positions (integer)
            node_size: Size of nodes in visualization
            font_size: Size of node labels
            with_labels: Whether to show node labels
            seed: Random seed for reproducible layouts

        Returns:
            matplotlib.figure.Figure: The generated plot figure
        """
        # Create a combined graph for visualization
        G = nx.Graph()

        # Add nodes with type information
        for node, data in self.compound_graph.nodes(data=True):
            G.add_node(node, node_type="compound", **data)

        for node, data in self.target_graph.nodes(data=True):
            G.add_node(node, node_type="target", **data)

        # Add edges from target graph
        G.add_edges_from(self.target_graph.edges())

        # Compute spring layout
        pos = nx.spring_layout(G, k=k, iterations=iterations, scale=scale, seed=seed)

        # Draw the network
        fig = plt.figure(figsize=(12, 8))

        # Draw compound nodes
        compound_nodes = [
            n for n, d in G.nodes(data=True) if d.get("node_type") == "compound"
        ]
        if compound_nodes:
            nx.draw_networkx_nodes(
                G,
                pos,
                nodelist=compound_nodes,
                node_color="skyblue",
                node_size=node_size,
            )

        # Draw target nodes
        target_nodes = [
            n for n, d in G.nodes(data=True) if d.get("node_type") == "target"
        ]
        if target_nodes:
            nx.draw_networkx_nodes(
                G,
                pos,
                nodelist=target_nodes,
                node_color="lightcoral",
                node_size=node_size,
            )

        # Draw edges
        nx.draw_networkx_edges(G, pos, alpha=0.5)

        # Add labels if requested
        if with_labels:
            labels = {
                node: G.nodes[node].get("data", {}).get("name", node)
                for node in G.nodes()
            }
            nx.draw_networkx_labels(G, pos, labels=labels, font_size=font_size)

        plt.title("Compound-Target Interaction Network")
        plt.axis("off")
        plt.tight_layout()

        return fig
