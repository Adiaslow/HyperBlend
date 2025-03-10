from flask import Blueprint, jsonify
from hyperblend.database import get_graph
import logging

logger = logging.getLogger(__name__)
db = Blueprint('db', __name__)

@db.route('/api/db/cleanup', methods=['POST'])
def cleanup_database():
    """
    Cleans up the database by:
    1. Removing nodes with null or 'Unknown' names
    2. Deleting nodes with disease-like descriptions
    3. Keeping only Molecule, Organism, and Target nodes
    4. Keeping only relationships with specified activity types
    5. Returning counts of remaining nodes by type
    """
    try:
        db = get_graph()

        # Delete nodes with null or 'Unknown' names
        db.run("""
            MATCH (n)
            WHERE n.name IS NULL OR n.name = 'Unknown' OR n.name = ''
            DETACH DELETE n
        """)

        # Delete nodes with disease-like descriptions
        db.run("""
            MATCH (n)
            WHERE n.description CONTAINS 'disease' OR 
                  n.description CONTAINS 'disorder' OR
                  n.name CONTAINS 'disease' OR
                  n.name CONTAINS 'disorder'
            DETACH DELETE n
        """)

        # Delete nodes that are not Molecule, Organism, or Target
        db.run("""
            MATCH (n)
            WHERE NOT (n:Molecule OR n:Organism OR n:Target)
            DETACH DELETE n
        """)

        # Delete relationships that don't have specified activity types
        db.run("""
            MATCH ()-[r]-()
            WHERE NOT (r.activity_type IS NOT NULL AND 
                      toLower(r.activity_type) IN ['agonist', 'antagonist', 'inhibitor', 'activator', 'substrate', 'unknown'])
            DELETE r
        """)

        # Get counts of remaining nodes by type
        result = db.run("""
            MATCH (n)
            WHERE n:Molecule OR n:Organism OR n:Target
            WITH labels(n) as labels
            UNWIND labels as label
            WITH label, count(*) as count
            WHERE label IN ['Molecule', 'Organism', 'Target']
            RETURN label, count
            ORDER BY label
        """)

        # Build counts dictionary
        counts = {}
        for record in result:
            counts[record['label']] = record['count']

        return jsonify({
            'status': 'success',
            'nodes': counts
        })

    except Exception as e:
        logger.error(f"Error during database cleanup: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 