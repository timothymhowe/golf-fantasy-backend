from flask import Blueprint, jsonify, request
from modules.authentication.auth import require_auth
from .functions import (get_golfers_with_roster_and_picks, get_upcoming_roster,
    get_upcoming_tournament, get_most_recent_tournament)

tournament_bp = Blueprint('tournament', __name__)

@tournament_bp.route('/most-recent', methods=['GET'])
def most_recent_tournament():
    tournament = get_most_recent_tournament()
    if tournament is None:
        return jsonify({'error': 'No recent tournament found'}), 404

    return jsonify(tournament), 200

@tournament_bp.route('/upcoming', methods=['GET'])
def upcoming_tournament():
    tournament = get_upcoming_tournament()
    if tournament is None:
        return jsonify({'error': 'No upcoming tournament found'}), 404

    return jsonify(tournament), 200

@tournament_bp.route('/roster', methods=['GET'])
def upcoming_roster():
    roster = get_upcoming_roster()
    if roster is None:
        return jsonify({'error': 'No upcoming roster found'}), 404

    return roster, 200

@tournament_bp.route('/dd', methods=['GET'])
@require_auth
def get_dd_data(uid):
    """
    Endpoint to get dropdown data for golfer selection.
    
    Args:
        uid (str): User ID from auth decorator
        
    Returns:
        JSON response with golfer data and tournament IDs
    """
    tournament_id = request.args.get('tournament_id')
    # print("\n=== DD Endpoint Debug ===")
    # print(f"UID: {uid}")
    # print(f"Tournament ID: {tournament_id}")
    
    dd = get_golfers_with_roster_and_picks(tournament_id, uid)
    # print(f"DD Result: {dd}")
    
    if dd is None:
        return jsonify({'error': 'No upcoming roster found'}), 404

    return dd, 200