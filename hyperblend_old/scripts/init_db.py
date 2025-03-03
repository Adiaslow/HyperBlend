"""Script to initialize the Neo4j database with sample data."""

import asyncio
import json
from datetime import datetime
from typing import Optional
from neo4j import AsyncGraphDatabase

from hyperblend_old.core.config import settings
from hyperblend_old.domain.models import (
    Compound,
    Source,
    Target,
    TargetType,
    SourceType,
)


def create_compound(
    id: str,
    name: str,
    description: str = "",
    smiles: str = "",
    molecular_formula: str = "",
    molecular_weight: Optional[float] = None,
    pubchem_id: str = "",
    chembl_id: str = "",
    coconut_id: str = "",
) -> Compound:
    """Helper function to create a compound with default values."""
    return Compound(
        id=id,
        name=name,
        canonical_name=name.lower(),
        description=description,
        smiles=smiles,
        molecular_formula=molecular_formula,
        molecular_weight=molecular_weight,
        pubchem_id=pubchem_id,
        chembl_id=chembl_id,
        coconut_id=coconut_id,
        created_at=datetime.now(),
        last_updated=datetime.now(),
    )


async def init_db():
    """Initialize the database with sample data."""
    driver = AsyncGraphDatabase.driver(settings.NEO4J_URI, auth=None)

    try:
        # Clear existing data
        async with driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")

        # Create compounds by plant
        compounds = {
            # Blue Lotus compounds
            "blue_lotus": [
                create_compound("C001", "Nuciferine", "Primary alkaloid of Blue Lotus"),
                create_compound("C002", "Aporphine"),
                create_compound("C003", "Nornuciferine"),
                create_compound("C004", "N-methylasimilobine"),
                create_compound("C005", "Roemerine"),
                create_compound(
                    "C006", "Quercetin", "A flavonoid found in many plants"
                ),
                create_compound("C007", "Kaempferol", "A flavonoid compound"),
            ],
            # San Pedro Cactus compounds
            "san_pedro": [
                create_compound("C008", "Mescaline", "Primary phenethylamine alkaloid"),
                create_compound("C009", "3,4-Dimethoxyphenethylamine"),
                create_compound("C010", "3,4,5-Trimethoxyphenethylamine"),
                create_compound("C011", "Tyramine"),
                create_compound("C012", "Hordenine"),
                create_compound("C013", "3-Methoxytyramine"),
                create_compound("C014", "Anhalinine"),
                create_compound("C015", "Anhalonidine"),
            ],
            # Morning Glory compounds
            "morning_glory": [
                create_compound("C016", "LSA", "Lysergic acid amide"),
                create_compound("C017", "Ergine"),
                create_compound("C018", "Isoergine", "Isomer of ergine"),
                create_compound("C019", "Lysergol"),
                create_compound("C020", "Elymoclavine"),
                create_compound("C021", "Chanoclavine"),
                create_compound("C022", "Ergometrine"),
                create_compound("C023", "Penniclavine"),
            ],
            # Kava compounds
            "kava": [
                create_compound("C024", "Kavain", "A kavalactone"),
                create_compound("C025", "Dihydrokavain", "A kavalactone"),
                create_compound("C026", "Methysticin", "A kavalactone"),
                create_compound("C027", "Dihydromethysticin", "A kavalactone"),
                create_compound("C028", "Yangonin", "A kavalactone"),
                create_compound("C029", "Desmethoxyyangonin", "A kavalactone"),
                create_compound("C030", "Flavokavain A"),
                create_compound("C031", "Flavokavain B"),
                create_compound("C032", "Flavokavain C"),
                create_compound("C033", "Pipermethystine"),
            ],
            # Damiana compounds
            "damiana": [
                create_compound("C034", "Damianin", "Primary active compound"),
                create_compound("C035", "Arbutin"),
                create_compound("C036", "Gonzalitosin"),
                create_compound("C037", "Tetraphyllin B"),
                create_compound("C038", "α-pinene", "Essential oil component"),
                create_compound("C039", "β-pinene", "Essential oil component"),
                create_compound("C040", "Thymol", "Essential oil component"),
                create_compound("C041", "Cineol", "Essential oil component"),
                create_compound("C042", "Cymene", "Essential oil component"),
            ],
            # Wild Dagga compounds
            "wild_dagga": [
                create_compound("C043", "Leonurine", "Primary compound"),
                create_compound("C044", "Marrubiin"),
                create_compound("C045", "Leonotinin"),
                create_compound("C046", "Leoheterin"),
                create_compound("C047", "Leosibirin"),
                create_compound("C048", "Caryophyllene", "Terpene"),
                create_compound("C049", "Limonene", "Terpene"),
            ],
            # Syrian Rue compounds
            "syrian_rue": [
                create_compound("C050", "Harmine", "Primary β-carboline alkaloid"),
                create_compound("C051", "Harmaline", "β-carboline alkaloid"),
                create_compound("C052", "Tetrahydroharmine", "β-carboline alkaloid"),
                create_compound("C053", "Harmol", "β-carboline alkaloid"),
                create_compound("C054", "Harmalol", "β-carboline alkaloid"),
                create_compound("C055", "Vasicine", "Quinazoline alkaloid"),
                create_compound("C056", "Vasicinone", "Quinazoline alkaloid"),
                create_compound("C057", "Deoxyvasicinone", "Quinazoline alkaloid"),
                create_compound("C058", "Peganine"),
            ],
            # Dream Herb compounds
            "dream_herb": [
                create_compound("C059", "Caleicin I", "Germacranolide"),
                create_compound("C060", "Caleicin II", "Germacranolide"),
                create_compound("C061", "Caleochromene A"),
                create_compound("C062", "Caleochromene B"),
                create_compound("C063", "Calein A", "Sesquiterpene lactone"),
                create_compound("C064", "Calein B", "Sesquiterpene lactone"),
                create_compound("C065", "Acacetin", "Flavonoid"),
                create_compound("C066", "O-methylacacetin", "Flavonoid"),
            ],
            # Passionflower compounds
            "passionflower": [
                create_compound("C067", "Harmine", "Harmala alkaloid"),
                create_compound("C068", "Harmaline", "Harmala alkaloid"),
                create_compound("C069", "Harmalol", "Harmala alkaloid"),
                create_compound("C070", "Chrysin", "Flavonoid"),
                create_compound("C071", "Apigenin", "Flavonoid"),
                create_compound("C072", "Luteolin", "Flavonoid"),
                create_compound("C073", "Maltol"),
                create_compound("C074", "Vitexin", "C-glycosyl flavone"),
                create_compound("C075", "Isovitexin", "C-glycosyl flavone"),
                create_compound("C076", "Orientin", "C-glycosyl flavone"),
                create_compound("C077", "Isoorientin", "C-glycosyl flavone"),
                create_compound("C078", "GABA", "Gamma-aminobutyric acid"),
            ],
            # Kratom compounds
            "kratom": [
                create_compound("C079", "Mitragynine", "Primary indole alkaloid"),
                create_compound("C080", "7-hydroxymitragynine", "Indole alkaloid"),
                create_compound("C081", "Speciogynine", "Indole alkaloid"),
                create_compound("C082", "Paynantheine", "Indole alkaloid"),
                create_compound("C083", "Speciociliatine", "Indole alkaloid"),
                create_compound("C084", "Mitraphylline", "Indole alkaloid"),
                create_compound("C085", "Ajmalicine", "Indole alkaloid"),
                create_compound("C086", "Corynantheidine", "Indole alkaloid"),
                create_compound("C087", "Mitraciliatine", "Indole alkaloid"),
                create_compound("C088", "Isomitraphylline", "Indole alkaloid"),
            ],
            # Wormwood compounds
            "wormwood": [
                create_compound("C089", "α-Thujone", "Primary active compound"),
                create_compound("C090", "β-Thujone"),
                create_compound("C091", "Absinthin"),
                create_compound("C092", "Anabsinthin"),
                create_compound("C093", "Artabsin"),
                create_compound("C094", "Artemisetin"),
                create_compound("C095", "Artemisinin"),
                create_compound("C096", "Chamazulene", "Essential oil component"),
                create_compound("C097", "Sabinene", "Essential oil component"),
                create_compound(
                    "C098", "trans-Sabinyl acetate", "Essential oil component"
                ),
            ],
            # California Poppy compounds
            "california_poppy": [
                create_compound("C099", "Californidine", "Isoquinoline alkaloid"),
                create_compound("C100", "Escholtzine", "Isoquinoline alkaloid"),
                create_compound("C101", "Protopine", "Isoquinoline alkaloid"),
                create_compound("C102", "Allocryptopine", "Isoquinoline alkaloid"),
                create_compound("C103", "Sanguinarine", "Isoquinoline alkaloid"),
                create_compound("C104", "Chelirubine", "Isoquinoline alkaloid"),
                create_compound("C105", "Macarpine", "Isoquinoline alkaloid"),
                create_compound("C106", "Chelerythrine", "Isoquinoline alkaloid"),
                create_compound("C107", "Berberine", "Isoquinoline alkaloid"),
                create_compound("C108", "Coptisine", "Isoquinoline alkaloid"),
                create_compound("C109", "Isorhamnetin", "Flavonoid glycoside"),
                create_compound("C110", "Rutin", "Flavonoid glycoside"),
            ],
        }

        # Create sources (plants)
        current_time = datetime.now().isoformat()
        sources = [
            Source(
                id="S001",
                name="Salvia divinorum",
                type=SourceType.PLANT,
                common_names=["Diviner's Sage", "Seer's Sage"],
                description="A psychoactive plant native to Mexico",
                native_regions=["Mexico"],
                traditional_uses=["Medicine", "Divination", "Ritual"],
                kingdom="Plantae",
                family="Lamiaceae",
                genus="Salvia",
                species="divinorum",
                created_at=current_time,
                last_updated=current_time,
            ),
            Source(
                id="S002",
                name="Trichocereus pachanoi",
                type=SourceType.PLANT,
                common_names=["San Pedro Cactus"],
                description="A columnar cactus native to the Andes Mountains",
                native_regions=["Peru", "Ecuador", "Bolivia"],
                traditional_uses=["Medicine", "Ritual", "Spiritual"],
                kingdom="Plantae",
                family="Cactaceae",
                genus="Trichocereus",
                species="pachanoi",
                created_at=current_time,
                last_updated=current_time,
            ),
            Source(
                id="S003",
                name="Ipomoea tricolor",
                type=SourceType.PLANT,
                common_names=["Morning Glory", "Mexican Morning Glory"],
                description="A flowering plant known for its seeds containing LSA",
                native_regions=["Mexico", "Central America"],
                traditional_uses=["Medicine", "Ritual"],
                kingdom="Plantae",
                family="Convolvulaceae",
                genus="Ipomoea",
                species="tricolor",
                created_at=current_time,
                last_updated=current_time,
            ),
            Source(
                id="S004",
                name="Piper methysticum",
                type=SourceType.PLANT,
                common_names=["Kava", "Kava Kava"],
                description="A plant species native to the Pacific Islands",
                native_regions=["Pacific Islands", "Polynesia"],
                traditional_uses=["Medicine", "Social", "Ritual"],
                kingdom="Plantae",
                family="Piperaceae",
                genus="Piper",
                species="methysticum",
                created_at=current_time,
                last_updated=current_time,
            ),
            Source(
                id="S005",
                name="Turnera diffusa",
                type=SourceType.PLANT,
                common_names=["Damiana"],
                description="A shrub traditionally used as an aphrodisiac",
                native_regions=["Mexico", "Central America", "South America"],
                traditional_uses=["Medicine", "Aphrodisiac"],
                kingdom="Plantae",
                family="Passifloraceae",
                genus="Turnera",
                species="diffusa",
                created_at=current_time,
                last_updated=current_time,
            ),
            Source(
                id="S006",
                name="Leonotis leonurus",
                type=SourceType.PLANT,
                common_names=["Wild Dagga", "Lion's Tail"],
                description="A shrub native to southern Africa with mild psychoactive properties",
                native_regions=["South Africa"],
                traditional_uses=["Medicine", "Ritual", "Smoking"],
                kingdom="Plantae",
                family="Lamiaceae",
                genus="Leonotis",
                species="leonurus",
                created_at=current_time,
                last_updated=current_time,
            ),
            Source(
                id="S007",
                name="Peganum harmala",
                type=SourceType.PLANT,
                common_names=["Syrian Rue", "Harmal"],
                description="A plant known for its MAO-inhibiting properties",
                native_regions=["Middle East", "North Africa", "Central Asia"],
                traditional_uses=["Medicine", "Ritual", "Dye"],
                kingdom="Plantae",
                family="Nitrariaceae",
                genus="Peganum",
                species="harmala",
                created_at=current_time,
                last_updated=current_time,
            ),
            Source(
                id="S008",
                name="Calea zacatechichi",
                type=SourceType.PLANT,
                common_names=["Dream Herb", "Bitter Grass"],
                description="A plant traditionally used to promote lucid dreaming",
                native_regions=["Mexico", "Central America"],
                traditional_uses=["Medicine", "Divination", "Dream Enhancement"],
                kingdom="Plantae",
                family="Asteraceae",
                genus="Calea",
                species="zacatechichi",
                created_at=current_time,
                last_updated=current_time,
            ),
            Source(
                id="S009",
                name="Passiflora incarnata",
                type=SourceType.PLANT,
                common_names=["Passionflower", "Maypop"],
                description="A climbing vine with calming properties",
                native_regions=["North America", "South America"],
                traditional_uses=["Medicine", "Anxiety Relief", "Sleep Aid"],
                kingdom="Plantae",
                family="Passifloraceae",
                genus="Passiflora",
                species="incarnata",
                created_at=current_time,
                last_updated=current_time,
            ),
            Source(
                id="S010",
                name="Mitragyna speciosa",
                type=SourceType.PLANT,
                common_names=["Kratom"],
                description="A tropical tree known for its unique alkaloids",
                native_regions=["Southeast Asia", "Thailand", "Indonesia"],
                traditional_uses=["Medicine", "Stimulant", "Pain Relief"],
                kingdom="Plantae",
                family="Rubiaceae",
                genus="Mitragyna",
                species="speciosa",
                created_at=current_time,
                last_updated=current_time,
            ),
            Source(
                id="S011",
                name="Artemisia absinthium",
                type=SourceType.PLANT,
                common_names=["Wormwood", "Absinthe Wormwood"],
                description="A plant known for its use in absinthe production",
                native_regions=["Europe", "Asia", "North Africa"],
                traditional_uses=["Medicine", "Spirit Production", "Vermifuge"],
                kingdom="Plantae",
                family="Asteraceae",
                genus="Artemisia",
                species="absinthium",
                created_at=current_time,
                last_updated=current_time,
            ),
            Source(
                id="S012",
                name="Eschscholzia californica",
                type=SourceType.PLANT,
                common_names=["California Poppy", "Golden Poppy"],
                description="A flowering plant with mild sedative properties",
                native_regions=["United States", "Mexico"],
                traditional_uses=["Medicine", "Sleep Aid", "Anxiety Relief"],
                kingdom="Plantae",
                family="Papaveraceae",
                genus="Eschscholzia",
                species="californica",
                created_at=current_time,
                last_updated=current_time,
            ),
        ]

        # Create nodes in Neo4j
        async with driver.session() as session:
            # Create compounds
            for plant_compounds in compounds.values():
                for compound in plant_compounds:
                    props = compound.model_dump()
                    props["created_at"] = props["created_at"].isoformat()
                    props["last_updated"] = props["last_updated"].isoformat()
                    await session.run(
                        """
                        CREATE (c:Compound)
                        SET c = $props
                        """,
                        {"props": props},
                    )

            # Create sources
            for source in sources:
                props = source.model_dump()
                props["created_at"] = props["created_at"].isoformat()
                props["last_updated"] = props["last_updated"].isoformat()
                props["taxonomy"] = json.dumps(props["taxonomy"])
                await session.run(
                    """
                    CREATE (s:Source)
                    SET s = $props
                    """,
                    {"props": props},
                )

            # Create relationships for each plant's compounds
            relationships = {
                "S001": compounds["blue_lotus"],  # Blue Lotus
                "S002": compounds["san_pedro"],  # San Pedro
                "S003": compounds["morning_glory"],  # Morning Glory
                "S004": compounds["kava"],  # Kava
                "S005": compounds["damiana"],  # Damiana
                "S006": compounds["wild_dagga"],  # Wild Dagga
                "S007": compounds["syrian_rue"],  # Syrian Rue
                "S008": compounds["dream_herb"],  # Dream Herb
                "S009": compounds["passionflower"],  # Passionflower
                "S010": compounds["kratom"],  # Kratom
                "S011": compounds["wormwood"],  # Wormwood
                "S012": compounds["california_poppy"],  # California Poppy
            }

            for source_id, source_compounds in relationships.items():
                for compound in source_compounds:
                    await session.run(
                        """
                        MATCH (c:Compound {id: $compound_id}), (s:Source {id: $source_id})
                        CREATE (s)-[:CONTAINS]->(c)
                        """,
                        {"compound_id": compound.id, "source_id": source_id},
                    )

        print("Database initialized successfully!")

    except Exception as e:
        print(f"Error initializing database: {str(e)}")
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(init_db())
