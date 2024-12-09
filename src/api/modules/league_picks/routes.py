from flask import Blueprint, jsonify
from modules.authentication.auth import require_auth
from .functions import get_current_week_picks
import logging

logger = logging.getLogger(__name__)

league_picks_bp = Blueprint('league_picks', __name__)

@league_picks_bp.route('/<int:league_id>', methods=['GET'])
@require_auth
def get_league_current_picks(uid, league_id):
    """
    Get the current picks for a league

    Args:
        uid (str): The Firebase UID of the authenticated user
        league_id (int): The ID of the league

    Returns:
        dict: A dictionary containing the week's picks for the most recent tournament.
    """
    try:
        picks = get_current_week_picks(league_id)
        if picks is None:
            return jsonify({
                'success': False,
                'error': 'Failed to get league picks'
            }), 400
            
        return jsonify({
            'success': True,
            'data': picks
        })
        
    except Exception as e:
        logger.error(f"Error in league picks endpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500