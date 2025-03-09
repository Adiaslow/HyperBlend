"""Database models for molecules and related entities using Neo4j."""

from typing import Set, List, Optional
from py2neo.ogm import GraphObject, Property, RelatedTo, RelatedFrom


class MoleculeDB(GraphObject):
    """
    Neo4j database model for molecules.
    """

    __primarylabel__ = "Molecule"

    # Properties
    name = Property()
    smiles = Property()
    inchi = Property()
    inchikey = Property()
    molecular_weight = Property()
    formula = Property()
    description = Property()
    pubchem_cid = Property()
    chembl_id = Property()
    coconut_id = Property()
    source = Property()

    # Relationships
    targets = RelatedTo("TargetDB", "BINDS_TO")

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def add_organism(self, organism_name):
        """Add an organism to this molecule."""
        org = OrganismDB()
        org.name = organism_name
        self.organisms.add(org)
        return org

    def __str__(self):
        return f"<MoleculeDB(name='{self.name}')>"


class OrganismDB(GraphObject):
    """
    Neo4j database model for organisms.
    """

    __primarylabel__ = "Organism"

    # Properties
    name = Property()
    type = Property()
    description = Property()
    taxonomy_id = Property()

    # Relationships
    molecules = RelatedFrom("MoleculeDB", "FROM_ORGANISM")

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return f"<OrganismDB(name='{self.name}')>"


class TargetDB(GraphObject):
    """
    Neo4j database model for targets.
    """

    __primarylabel__ = "Target"

    # Properties
    name = Property()
    type = Property()
    description = Property()
    uniprot_id = Property()
    pdb_id = Property()
    chembl_id = Property()

    # Relationships
    molecules = RelatedFrom("MoleculeDB", "BINDS_TO")
    organisms = RelatedTo("OrganismDB", "FROM_ORGANISM")

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def add_organism(self, organism_name):
        """Add an organism to this target."""
        org = OrganismDB()
        org.name = organism_name
        self.organisms.add(org)
        return org

    def __str__(self):
        return f"<TargetDB(name='{self.name}')>"
