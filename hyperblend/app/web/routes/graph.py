# hyperblend/app/web/routes/graph.py

from flask import Blueprint, jsonify, request
from hyperblend.app.web.core.decorators import handle_db_error, cors_enabled
from hyperblend.database import get_graph
import logging

logger = logging.getLogger(__name__)
graph = Blueprint('graph', __name__)

@graph.route('/api/graph/overview', methods=['GET'])
@cors_enabled
@handle_db_error
def get_graph_overview():
    """
    Get an overview of the graph database.
    Returns nodes and relationships for visualization.
    """
    try:
        # Get database connection
        db = get_graph()
        
        # Query to get all nodes and their relationships
        cypher_query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]->(m)
        WITH COLLECT(DISTINCT n) as nodes,
             COLLECT(DISTINCT {
                source: toString(elementId(startNode(r))),
                target: toString(elementId(endNode(r))),
                type: type(r),
                activity_type: r.activity_type,
                activity_value: r.activity_value,
                activity_unit: r.activity_unit,
                confidence_score: r.confidence_score
             }) as relationships
        RETURN {
            nodes: [node in nodes | {
                id: toString(elementId(node)),
                name: node.name,
                type: head(labels(node)),
                description: node.description,
                smiles: node.smiles,
                formula: node.formula,
                molecular_weight: node.molecular_weight
            }],
            links: [rel in relationships WHERE rel.source IS NOT NULL | rel],
            stats: {
                molecules: size([n in nodes WHERE 'Molecule' in labels(n)]),
                organisms: size([n in nodes WHERE 'Organism' in labels(n)]),
                targets: size([n in nodes WHERE 'Target' in labels(n)])
            }
        } as result
        """
        
        result = db.run(cypher_query).data()
        if not result:
            return jsonify({'nodes': [], 'links': [], 'stats': {'molecules': 0, 'organisms': 0, 'targets': 0}})
        
        return jsonify(result[0]['result'])
    except ConnectionError as e:
        logger.error(f"Database connection error: {str(e)}")
        return jsonify({'error': 'Database connection error', 'message': str(e)}), 503
    except Exception as e:
        logger.error(f"Error in get_graph_overview: {str(e)}")
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

@graph.route('/api/graph', methods=['GET'])
@cors_enabled
@handle_db_error
def search_graph():
    """
    Search the graph database.
    Query Parameters:
        q (str): Search query string
    """
    query = request.args.get('q', '').strip()
    if not query:
        return get_graph_overview()

    try:
        # Get database connection
        db = get_graph()
        
        # Query to search nodes and their relationships
        cypher_query = """
        MATCH (n)
        WHERE n.name =~ $pattern
           OR n.description =~ $pattern
           OR n.smiles =~ $pattern
           OR n.formula =~ $pattern
        WITH COLLECT(n) as matched_nodes
        UNWIND matched_nodes as n
        OPTIONAL MATCH (n)-[r]-(m)
        WITH COLLECT(DISTINCT n) + COLLECT(DISTINCT m) as nodes,
             COLLECT(DISTINCT {
                source: toString(elementId(startNode(r))),
                target: toString(elementId(endNode(r))),
                type: type(r),
                activity_type: r.activity_type,
                activity_value: r.activity_value,
                activity_unit: r.activity_unit,
                confidence_score: r.confidence_score
             }) as relationships
        RETURN {
            nodes: [node in nodes | {
                id: toString(elementId(node)),
                name: node.name,
                type: head(labels(node)),
                description: node.description,
                smiles: node.smiles,
                formula: node.formula,
                molecular_weight: node.molecular_weight
            }],
            links: [rel in relationships WHERE rel.source IS NOT NULL | rel],
            stats: {
                molecules: size([n in nodes WHERE 'Molecule' in labels(n)]),
                organisms: size([n in nodes WHERE 'Organism' in labels(n)]),
                targets: size([n in nodes WHERE 'Target' in labels(n)])
            }
        } as result
        """
        
        result = db.run(cypher_query, {"pattern": f"(?i).*{query}.*"}).data()
        if not result:
            return jsonify({'nodes': [], 'links': [], 'stats': {'molecules': 0, 'organisms': 0, 'targets': 0}})
        
        return jsonify(result[0]['result'])
    except ConnectionError as e:
        logger.error(f"Database connection error: {str(e)}")
        return jsonify({'error': 'Database connection error', 'message': str(e)}), 503
    except Exception as e:
        logger.error(f"Error in search_graph: {str(e)}")
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500 