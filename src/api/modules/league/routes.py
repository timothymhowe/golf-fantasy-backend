from flask import Blueprint, jsonify
from modules.authentication.auth import require_auth
from modules.user.functions import get_league_member_ids
from .functions import calculate_leaderboard, get_league_member_pick_history
import logging

logger = logging.getLogger(__name__)

league_bp = Blueprint('league', __name__)

@league_bp.route('/scoreboard')
@require_auth
def scoreboard(uid):
    try:
        logging.info(f"Fetching scoreboard for user {uid}")
        
        # Get user's league ID
        league_member_ids = get_league_member_ids(uid)
        logging.info(f"Found league member IDs: {league_member_ids}")
        
        if not league_member_ids:
            logging.warning(f"No leagues found for user {uid}")
            return jsonify({
                "status": "error",
                "message": "User not found in any leagues"
            }), 404
            
        # Get first league ID
        # league_id = league_member_ids[0][1]  # Gets league_id from tuple
        
        league_id = 7
        logging.info(f"Using league ID: {league_id}")
        
        # Get leaderboard data
        logging.info(f"Calculating leaderboard for league {league_id}")
        leaderboard_data = calculate_leaderboard(league_id)
        logging.info(f"Leaderboard data: {leaderboard_data}")
        
        # Format response
        formatted_leaderboard = []
        for rank, entry in enumerate(leaderboard_data, 1):
            formatted_leaderboard.append({
                "rank": rank,
                "name": entry["username"],
                "score": entry["total_points"],
                "leagueMemberId": entry["league_member_id"],
                "wins":entry["wins"],
                "missedPicks": entry["missed_picks"]
            })
        
        logging.info(f"Formatted leaderboard: {formatted_leaderboard}")
        
        return jsonify({
            "status": "success",
            "data": {
                "leaderboard": formatted_leaderboard
            },
            "message": "Retrieved leaderboard successfully."
        })
        
    except Exception as e:
        logging.error(f"Error in scoreboard route: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500

@league_bp.route('/membership', methods=['GET'])
@require_auth
def check_membership(uid):
    try:
        logging.info(f"Checking league membership for user {uid}")
        league_member_ids = get_league_member_ids(uid)
        
        has_league = bool(league_member_ids)  # Convert to boolean
        logging.info(f"User {uid} has league: {has_league}")
        
        return jsonify({
            "hasLeague": has_league
        })
        
    except Exception as e:
        logging.error(f"Error checking league membership: {str(e)}", exc_info=True)
        return jsonify({
            "message": "Error checking league membership",
            "error": str(e)
        }), 500

@league_bp.route('/member/<int:league_member_id>/pick-history', methods=['GET'])
def get_member_picks(league_member_id):
    """Get pick history for a specific league member
    
    Args:
        league_member_id: ID of the league member to get history for
        
    Returns:
        JSON response with pick history or error
    """
    try:
        print('Getting pick history for league member', league_member_id)
        picks = get_league_member_pick_history(league_member_id)
        
        if picks is None:
            return jsonify({
                'error': 'No pick history found or invalid league member'
            }), 404
            
        return jsonify(picks), 200
        
    except Exception as e:
        logger.error(f"Error getting pick history: {e}")
        return jsonify({
            'error': f'Internal server error fetching pick history: {str(e)}'
        }), 500