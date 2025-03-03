from typing import List, Optional
from hyperblend.models.domain import Compound
from hyperblend.db.neo4j import Neo4jConnection


class CompoundService:
    """Service class for managing compounds in the HyperBlend system."""

    def __init__(self):
        """Initialize the CompoundService with a Neo4j connection."""
        self.db = Neo4jConnection()

    def get_compound(self, compound_id: str) -> Optional[Compound]:
        """
        Retrieve a compound by its ID.

        Args:
            compound_id: The unique identifier of the compound.

        Returns:
            Optional[Compound]: The compound if found, None otherwise.
        """
        query = """
        MATCH (c:Compound {id: $compound_id})
        RETURN c
        """
        result = self.db.run(query, compound_id=compound_id)
        if result:
            return Compound(**result[0]["c"])
        return None

    def search_compounds(self, query: str) -> List[Compound]:
        """
        Search for compounds by name or identifier.

        Args:
            query: The search query string.

        Returns:
            List[Compound]: List of matching compounds.
        """
        search_query = """
        MATCH (c:Compound)
        WHERE c.name CONTAINS $query OR c.id CONTAINS $query
        RETURN c
        LIMIT 10
        """
        results = self.db.run(search_query, query=query)
        return [Compound(**record["c"]) for record in results]

    def create_compound(self, compound: Compound) -> Compound:
        """
        Create a new compound in the database.

        Args:
            compound: The compound to create.

        Returns:
            Compound: The created compound.
        """
        query = """
        CREATE (c:Compound {
            id: $id,
            name: $name,
            formula: $formula,
            molecular_weight: $molecular_weight,
            smiles: $smiles,
            inchi: $inchi,
            source: $source,
            description: $description
        })
        RETURN c
        """
        result = self.db.run(query, **compound.model_dump())
        return Compound(**result[0]["c"])

    def update_compound(
        self, compound_id: str, compound: Compound
    ) -> Optional[Compound]:
        """
        Update an existing compound.

        Args:
            compound_id: The ID of the compound to update.
            compound: The updated compound data.

        Returns:
            Optional[Compound]: The updated compound if found, None otherwise.
        """
        query = """
        MATCH (c:Compound {id: $compound_id})
        SET c += $compound_data
        RETURN c
        """
        result = self.db.run(
            query, compound_id=compound_id, compound_data=compound.model_dump()
        )
        if result:
            return Compound(**result[0]["c"])
        return None

    def delete_compound(self, compound_id: str) -> bool:
        """
        Delete a compound by its ID.

        Args:
            compound_id: The ID of the compound to delete.

        Returns:
            bool: True if the compound was deleted, False otherwise.
        """
        query = """
        MATCH (c:Compound {id: $compound_id})
        DELETE c
        RETURN count(c) as deleted
        """
        result = self.db.run(query, compound_id=compound_id)
        return result[0]["deleted"] > 0
