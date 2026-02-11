from flask import Blueprint, jsonify
from modules.authentication.auth import require_auth
from modules.live_tournament.functions import get_latest_tournament_state, a_big_fetch
import logging

logger = logging.getLogger(__name__)

live_tournament_bp = Blueprint('live_results', __name__)

@live_tournament_bp.route('/live', methods=['GET'])
@require_auth
def tournament_state(uid):
    """API endpoint to get the current tournament state."""
    try:
        tournament_state = get_latest_tournament_state()
        return jsonify(tournament_state), 200
    except Exception as e:
        logger.error("Error getting tournament state: %s", e, exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# TODO: P0 require auth and fully imlement
@live_tournament_bp.route('/big_fetch', methods=['GET'])
@require_auth
def the_big_fetch(uid):
    """API endpoint to get the current tournament state."""
    try:
        out = a_big_fetch()
        return jsonify(out), 200
    except Exception as e:
        logger.error("Error in big fetch: %s", e, exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500