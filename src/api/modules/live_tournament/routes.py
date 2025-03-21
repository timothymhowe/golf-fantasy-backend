from flask import Blueprint, jsonify
from modules.live_tournament.functions import get_latest_tournament_state
from modules.authentication.auth import require_auth


from modules.live_tournament.functions import get_latest_tournament_state, a_big_fetch

live_tournament_bp = Blueprint('live_results', __name__)

# TODO: P0 require auth!!!!!!
@live_tournament_bp.route('/live', methods=['GET'])
def tournament_state():
    """API endpoint to get the current tournament state."""
    try:
        tournament_state = get_latest_tournament_state()
        return jsonify(tournament_state), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    
# TODO: P0 require auth and fully imlement
@live_tournament_bp.route('/big_fetch', methods=['GET'])
@require_auth
def the_big_fetch(uid):
    """API endpoint to get the current tournament state."""
    try:
        print("Starting big fetch")
        out = a_big_fetch()
        print("Big fetch complete")
        return jsonify(out), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500