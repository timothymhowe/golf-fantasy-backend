from flask import Blueprint, jsonify
from modules.authentication.auth import require_auth
from modules.user.functions import get_most_recent_pick, pick_history, submit_pick, get_league_member_ids, get_user_profile
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


# TODO: check to make sure user is actually a member of the league before doing this, right now any member of any league could be authenticated and get the league info i think.  
@user_bp.route('/history/<int:league_id>', methods=['GET'])
@require_auth
def get_my_history(uid, league_id):
    """Get pick history for the authenticated user's specified league"""
    try:        
        # Get user's league memberships
        league_memberships = get_league_member_ids(uid)
        
        if not league_memberships:
            return jsonify({
                'error': 'User not found in any leagues'
            }), 404
            
        # Check if the user is a member of the specified league
        league_member = next(
            (league for league in league_memberships if league['league_id'] == league_id), 
            None
        )
        
        if not league_member:
            return jsonify({
                'error': 'User is not a member of the specified league'
            }), 404
            
        # Get pick history for the specified league
        picks = get_league_member_pick_history(league_member['league_member_id'])
        
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
# TODO: refactor to include the "has_tournament_started" check
@user_bp.route('/submit', methods=['POST'])
@require_auth
def submit_my_pick(uid,tournament_id, golfer_id):
    """Submit a pick for the authenticated user

    Args:
        uid (str): Firebase ID of the authenticated user
        tournament_id (int): ID of the tournament to submit a pick for
        golfer_id (int): ID of the golfer to submit a pick for

    Returns:
        _type_: _description_
    """
    pick = submit_pick(uid, tournament_id, golfer_id)
    if pick is None:
        return jsonify({'error': 'Failed to submit pick'}), 500
    
    return jsonify(pick.to_dict()), 201

    
    
@user_bp.route('/leagues', methods=['GET'])
@require_auth
def get_my_leagues(uid):
    """
    Get all leagues for the authenticated user
    
    Returns:
        200 (OK): List of user's leagues
        {
            'success': True,
            'data': [
                {
                    'league_member_id': int,
                    'league_id': int,
                    'league_name': str,
                    'is_active': bool
                },
                ...
            ]
        }
        
        404 (Not Found): User has no leagues
        500 (Server Error): Unexpected error
    """
    try:
        # Get user's league memberships
        leagues = get_league_member_ids(uid)
        
        if leagues is None:
            logger.error(f"Failed to fetch leagues for user {uid}")
            return jsonify({
                'success': False,
                'error': 'Failed to fetch user leagues'
            }), 500
            
        if not leagues:
            return jsonify({
                'success': True,
                'data': []
            }), 200
            
        return jsonify({
            'success': True,
            'data': leagues
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user leagues: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@user_bp.route('/profile', methods=['GET'])
@require_auth
def get_profile(uid):
    """
    Get the authenticated user's profile
    
    Returns:
        200 (OK): User profile data
        {
            'success': True,
            'data': {
                'id': int,
                'display_name': str,
                'first_name': str,
                'last_name': str,
                'email': str,
                'avatar_url': str,
                'leagues': [
                    {
                        'league_member_id': int,
                        'league_id': int,
                        'league_name': str,
                        'role_id': int,
                        'role_name': str,
                        'is_active': bool
                    },
                    ...
                ]
            }
        }
        
        500 (Server Error): Database error or user not found
    """
    try:
        profile = get_user_profile(uid)
        
        if profile is None:
            logger.error(f"Authenticated user {uid} not found in database")
            return jsonify({
                'success': False,
                'error': 'User profile not found in database'
            }), 500  # Changed from 404 to 500
            
        return jsonify(profile), 200
        
    except Exception as e:
        logger.error(f"Error getting user profile: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
