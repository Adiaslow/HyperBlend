# hyperblend/scripts/init_db.py

from hyperblend.db.neo4j import Neo4jConnection
from hyperblend.models.domain import Compound


def init_database():
    """Initialize the Neo4j database with sample data."""
    db = Neo4jConnection()

    # Create constraints
    constraints = [
        "CREATE CONSTRAINT compound_id IF NOT EXISTS FOR (c:Compound) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT source_id IF NOT EXISTS FOR (s:Source) REQUIRE s.id IS UNIQUE",
        "CREATE CONSTRAINT target_id IF NOT EXISTS FOR (t:Target) REQUIRE t.id IS UNIQUE",
    ]

    for constraint in constraints:
        db.run(constraint)

    # Sample compounds
    sample_compounds = [
        {
            "id": "C001",
            "name": "Mescaline",
            "formula": "C11H17NO3",
            "molecular_weight": 211.26,
            "smiles": "CC1=CC(=CC(=C1)CCN)C(=O)O",
            "inchi": "InChI=1S/C11H17NO3/c1-7-4-8(2)10(12-3)5-9(7)6-11(13)14/h4-5,12H,3,6H2,1-2H3,(H,13,14)",
            "source": "Lophophora williamsii",
            "description": "A naturally occurring psychedelic alkaloid",
        },
        {
            "id": "C002",
            "name": "Psilocybin",
            "formula": "C12H17N2O4P",
            "molecular_weight": 284.25,
            "smiles": "CC1=CC(=CC(=C1)CCN)C(=O)O",
            "inchi": "InChI=1S/C12H17N2O4P/c1-7-4-8(2)10(12-3)5-9(7)6-11(13)14/h4-5,12H,3,6H2,1-2H3,(H,13,14)",
            "source": "Psilocybe cubensis",
            "description": "A naturally occurring psychedelic compound",
        },
    ]

    # Insert sample compounds
    for compound_data in sample_compounds:
        compound = Compound(**compound_data)
        query = """
        MERGE (c:Compound {id: $id})
        SET c += $compound_data
        """
        db.run(query, id=compound.id, compound_data=compound.model_dump())

    print("Database initialized successfully!")


if __name__ == "__main__":
    init_database()
