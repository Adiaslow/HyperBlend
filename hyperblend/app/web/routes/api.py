# hyperblend/app/web/routes/api.py

from flask import Blueprint, jsonify, request
from hyperblend.database import get_graph

api = Blueprint('api', __name__)

@api.route('/api/molecules', methods=['GET'])
def list_molecules():
    """Get all molecules or search for molecules."""
    try:
        db = get_graph()
        query = request.args.get('q', '').strip()
        search_pattern = f"(?i).*{query}.*" if query else None

        cypher_query = """
        MATCH (m:Molecule)
        WHERE m.name IS NOT NULL
        AND ($query = '' OR m.name =~ $search_pattern)
        RETURN {
            id: toString(elementId(m)),
            name: m.name,
            formula: m.formula,
            molecular_weight: m.molecular_weight,
            smiles: m.smiles,
            description: m.description
        } as molecule
        ORDER BY molecule.name
        """

        results = db.run(cypher_query, query=query or '', search_pattern=search_pattern)
        molecules = [dict(record["molecule"]) for record in results]
        return jsonify(molecules)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/api/molecules/<molecule_id>', methods=['GET'])
def get_molecule(molecule_id):
    """Get a specific molecule by ID."""
    try:
        db = get_graph()
        cypher_query = """
        MATCH (m:Molecule)
        WHERE toString(elementId(m)) = $molecule_id
        OPTIONAL MATCH (m)-[r]-(related)
        WHERE (related:Target OR related:Organism)
        WITH m, collect(DISTINCT {
            id: toString(elementId(related)),
            name: related.name,
            type: labels(related)[0],
            relationship_type: type(r),
            activity_type: r.activity_type,
            activity_value: r.activity_value,
            activity_unit: r.activity_unit,
            confidence_score: r.confidence_score
        }) as relationships
        RETURN {
            id: toString(elementId(m)),
            name: m.name,
            formula: m.formula,
            molecular_weight: m.molecular_weight,
            smiles: m.smiles,
            inchi: m.inchi,
            inchikey: m.inchikey,
            pubchem_cid: m.pubchem_cid,
            chembl_id: m.chembl_id,
            drugbank_id: m.drugbank_id,
            logp: m.logp,
            polar_surface_area: m.polar_surface_area,
            relationships: relationships
        } as molecule
        """

        result = db.run(cypher_query, molecule_id=molecule_id).data()
        if not result:
            return jsonify({"error": "Molecule not found"}), 404

        return jsonify(result[0]["molecule"])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/api/targets', methods=['GET'])
def list_targets():
    """Get all targets or search for targets."""
    try:
        db = get_graph()
        query = request.args.get('q', '').strip()
        search_pattern = f"(?i).*{query}.*" if query else None

        cypher_query = """
        MATCH (t:Target)
        WHERE t.name IS NOT NULL
        AND ($query = '' OR t.name =~ $search_pattern)
        OPTIONAL MATCH (t)-[r]-(m:Molecule)
        WITH t, count(DISTINCT m) as molecule_count
        RETURN {
            id: toString(elementId(t)),
            name: t.name,
            description: t.description,
            molecule_count: molecule_count
        } as target
        ORDER BY target.name
        """

        results = db.run(cypher_query, query=query or '', search_pattern=search_pattern)
        targets = [dict(record["target"]) for record in results]
        return jsonify(targets)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/api/targets/<target_id>', methods=['GET'])
def get_target(target_id):
    """Get a specific target by ID."""
    try:
        db = get_graph()
        cypher_query = """
        MATCH (t:Target)
        WHERE toString(elementId(t)) = $target_id
        OPTIONAL MATCH (t)-[r]-(m:Molecule)
        WITH t, collect(DISTINCT {
            id: toString(elementId(m)),
            name: m.name,
            smiles: m.smiles,
            relationship_type: type(r),
            activity_type: r.activity_type,
            activity_value: r.activity_value,
            activity_unit: r.activity_unit,
            confidence_score: r.confidence_score
        }) as molecules
        RETURN {
            id: toString(elementId(t)),
            name: t.name,
            description: t.description,
            type: t.type,
            organism: t.organism,
            external_id: t.external_id,
            molecule_count: size(molecules),
            molecules: molecules
        } as target
        """

        result = db.run(cypher_query, target_id=target_id).data()
        if not result:
            return jsonify({"error": "Target not found"}), 404

        return jsonify(result[0]["target"])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/api/organisms', methods=['GET'])
def list_organisms():
    """Get all organisms or search for organisms."""
    try:
        db = get_graph()
        query = request.args.get('q', '').strip()
        search_pattern = f"(?i).*{query}.*" if query else None

        cypher_query = """
        MATCH (o:Organism)
        WHERE o.name IS NOT NULL
        AND ($query = '' OR o.name =~ $search_pattern)
        OPTIONAL MATCH (o)-[r]-(m:Molecule)
        WITH o, count(DISTINCT m) as molecule_count
        RETURN {
            id: toString(elementId(o)),
            name: o.name,
            description: o.description,
            molecule_count: molecule_count
        } as organism
        ORDER BY organism.name
        """

        results = db.run(cypher_query, query=query or '', search_pattern=search_pattern)
        organisms = [dict(record["organism"]) for record in results]
        return jsonify(organisms)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/api/organisms/<organism_id>', methods=['GET'])
def get_organism(organism_id):
    """Get a specific organism by ID."""
    try:
        db = get_graph()
        cypher_query = """
        MATCH (o:Organism)
        WHERE toString(elementId(o)) = $organism_id
        OPTIONAL MATCH (o)-[r]-(m:Molecule)
        WITH o, collect(DISTINCT {
            id: toString(elementId(m)),
            name: m.name,
            smiles: m.smiles,
            relationship_type: type(r)
        }) as molecules
        RETURN {
            id: toString(elementId(o)),
            name: o.name,
            description: o.description,
            taxonomy: o.taxonomy,
            common_name: o.common_name,
            external_id: o.external_id,
            molecule_count: size(molecules),
            molecules: molecules
        } as organism
        """

        result = db.run(cypher_query, organism_id=organism_id).data()
        if not result:
            return jsonify({"error": "Organism not found"}), 404

        return jsonify(result[0]["organism"])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/api/effects', methods=['GET'])
def list_effects():
    """Get all effects or search for effects."""
    try:
        db = get_graph()
        query = request.args.get('q', '').strip()
        search_pattern = f"(?i).*{query}.*" if query else None

        cypher_query = """
        MATCH (e:Effect)
        WHERE e.name IS NOT NULL
        AND ($query = '' OR e.name =~ $search_pattern)
        OPTIONAL MATCH (e)-[r]-(m:Molecule)
        WITH e, count(DISTINCT m) as molecule_count
        RETURN {
            id: toString(elementId(e)),
            name: e.name,
            description: e.description,
            molecule_count: molecule_count
        } as effect
        ORDER BY effect.name
        """

        results = db.run(cypher_query, query=query or '', search_pattern=search_pattern)
        effects = [dict(record["effect"]) for record in results]
        return jsonify(effects)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/api/effects/<effect_id>', methods=['GET'])
def get_effect(effect_id):
    """Get a specific effect by ID."""
    try:
        db = get_graph()
        cypher_query = """
        MATCH (e:Effect)
        WHERE toString(elementId(e)) = $effect_id
        OPTIONAL MATCH (e)-[r]-(m:Molecule)
        WITH e, collect(DISTINCT {
            id: toString(elementId(m)),
            name: m.name,
            smiles: m.smiles,
            relationship_type: type(r)
        }) as molecules
        RETURN {
            id: toString(elementId(e)),
            name: e.name,
            description: e.description,
            molecule_count: size(molecules),
            molecules: molecules
        } as effect
        """

        result = db.run(cypher_query, effect_id=effect_id).data()
        if not result:
            return jsonify({"error": "Effect not found"}), 404

        return jsonify(result[0]["effect"])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Get counts of different node types."""
    try:
        db = get_graph()
        cypher_query = """
        MATCH (n)
        WHERE n:Molecule OR n:Target OR n:Organism OR n:Effect
        WITH labels(n) as labels
        UNWIND labels as label
        WITH label, count(*) as count
        WHERE label IN ['Molecule', 'Target', 'Organism', 'Effect']
        RETURN collect({label: label, count: count}) as stats
        """

        result = db.run(cypher_query).data()[0]
        stats = {item['label'].lower(): item['count'] for item in result['stats']}
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500 