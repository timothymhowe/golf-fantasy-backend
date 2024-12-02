from flask import Blueprint, jsonify
from modules.authentication.auth import require_auth
from modules.user.functions import get_most_recent_pick, pick_history, submit_pick, get_league_member_ids
from modules.authentication.auth import default_app
from modules.league.functions import get_league_member_pick_history
import logging

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)

@user_bp.route('/current', methods=['GET'])
@require_auth
def get_my_pick(uid):
    pick = get_most_recent_pick(uid)
    
    if pick is None:
        return jsonify({'error': 'No pick found'}), 404
    
     # Assuming the Pick model has a method to convert it to a dict for jsonify
    return jsonify(pick.to_dict()), 200



@user_bp.route('/history', methods=['GET'])
@require_auth
def get_my_history(uid):
    """Get pick history for the authenticated user's active league"""
    try:
        # Get user's league member IDs
        
        league_member_ids = get_league_member_ids(uid)
        
        if not league_member_ids:
            return jsonify({
                'error': 'User not found in any leagues'
            }), 404
            
        # For now, just use the first league member ID
        # TODO: Add support for selecting active league
        league_member_id = league_member_ids[0][0]
        
        picks = get_league_member_pick_history(league_member_id)
        
        if picks is None:
            return jsonify({
                'error': 'No pick history found'
            }), 404
            
        return jsonify(picks), 200
        
    except Exception as e:
        logger.error(f"Error getting user pick history: {e}", exc_info=True)
        return jsonify({
            'error': f'Internal server error: {str(e)}'
        }), 500


# TODO: Deprecate this route, migrate to pick module
@user_bp.route('/submit', methods=['POST'])
@require_auth
def submit_my_pick(uid,tournament_id, golfer_id):
    pick = submit_pick(uid, tournament_id, golfer_id)
    if pick is None:
        return jsonify({'error': 'Failed to submit pick'}), 500
    
    return jsonify(pick.to_dict()), 201

    