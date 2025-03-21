from flask import Blueprint, jsonify, request
from modules.authentication.auth import require_auth
from modules.pick.functions import submit_pick, get_most_recent_pick, get_field_stats
import logging

pick_bp = Blueprint('pick', __name__)

@pick_bp.route('/submit', methods=['POST'])
@require_auth
def submit_my_pick(uid):
    data = request.get_json()
    league_member_id = data.get('league_member_id')
    tournament_id = data.get('tournament_id')
    golfer_id = data.get('golfer_id')
    print("Request params")
    print("Tournament ID: ", tournament_id)
    print("Golfer ID: ", golfer_id)
    print("League Member ID: ", league_member_id)
    
    pick = submit_pick(uid, tournament_id, golfer_id,league_member_id)
    if pick is None:
        return jsonify({'error': 'Failed to submit pick'}), 500
    
    return jsonify(pick.to_dict()), 201


@pick_bp.route('/current/<int:league_member_id>', methods=['GET'])
@require_auth
def get_current_pick(uid, league_member_id):
    tournament_id = request.args.get('tournament_id')
    if not tournament_id:
        return jsonify({'error': 'tournament_id is required'}), 400

    try:
        pick = get_most_recent_pick(uid, tournament_id, league_member_id)
        if not pick:
            # Return 200 with a clear "no pick" state
            return jsonify({
                'status': 'success',
                'has_pick': False,
                'message': 'No pick found for this tournament'
            }), 200
            
        return jsonify(pick), 200

    except Exception as e:
        logging.error(f"Error getting current pick: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
    
@pick_bp.route('/field_stats/<int:tournament_id>', methods=['GET'])
def field_stats(tournament_id):
    stats = get_field_stats(tournament_id)
    return jsonify(stats), 200