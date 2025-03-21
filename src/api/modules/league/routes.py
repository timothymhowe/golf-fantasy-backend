from flask import Blueprint, jsonify
from modules.authentication.auth import require_auth
from modules.user.functions import get_league_member_ids
from .functions import calculate_leaderboard, get_league_member_pick_history
import logging

logger = logging.getLogger(__name__)

league_bp = Blueprint('league', __name__)

# TODO: make sure that user is a member of the league before doing this.  future feature bby. 
@league_bp.route('/scoreboard/<int:league_id>', methods=['GET'])
@require_auth
def scoreboard(uid, league_id):
    """
    Get the scoreboard for a specific league
    
    Args:
        uid (str): Firebase user ID from auth token
        league_id (int): ID of the league to get scoreboard for
        
    Returns:
        200 (OK): League scoreboard data
        {
            "status": "success",
            "data": {
                "leaderboard": [
                    {
                        "rank": int,
                        "name": str,
                        "score": int,
                        "leagueMemberId": int,
                        "wins": int,
                        "missedPicks": int
                    },
                    ...
                ]
            }
        }
        
        404 (Not Found): League not found or user not a member
        500 (Server Error): Unexpected error
    """
    try:
        logging.info(f"Fetching scoreboard for league {league_id}")
        
        # Get user's league memberships to verify access
        league_memberships = get_league_member_ids(uid)
        
        if not league_memberships:
            logging.warning(f"No leagues found for user {uid}")
            return jsonify({
                "status": "error",
                "message": "User not found in any leagues"
            }), 404
            
        # Verify user is a member of the requested league
        is_member = any(
            league['league_id'] == league_id 
            for league in league_memberships
        )
        
        if not is_member:
            logging.warning(f"User {uid} attempted to access unauthorized league {league_id}")
            return jsonify({
                "status": "error",
                "message": "Not authorized to view this league"
            }), 403
            
        # Get leaderboard data
        logging.info(f"Calculating leaderboard for league {league_id}")
        leaderboard_data = calculate_leaderboard(league_id)
        logging.info(f"Leaderboard data: {leaderboard_data}")
        
        if not leaderboard_data:
            return jsonify({
                "status": "error",
                "message": "No leaderboard data found"
            }), 404
        
        # Format response
        formatted_leaderboard = []
        for rank, entry in enumerate(leaderboard_data, 1):
            formatted_leaderboard.append({
                "rank": rank,
                "name": entry["username"],
                "first_name": entry["first_name"],
                "last_name": entry["last_name"],
                "avatar_url": entry["avatar_url"],
                "score": entry["total_points"],
                "leagueMemberId": entry["league_member_id"],
                "wins": entry["wins"],
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
       

# TODO: Deprecate this route, migrate to user module
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
        
