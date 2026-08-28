from flask import Blueprint, jsonify, request
from modules.authentication.auth import require_auth
from modules.authentication.access import require_own_league_member, user_owns_league_member
from modules.pick.functions import submit_pick, get_most_recent_pick, get_field_stats
import logging

logger = logging.getLogger(__name__)

pick_bp = Blueprint('pick', __name__)

@pick_bp.route('/submit', methods=['POST'])
@require_auth
def submit_my_pick(uid):
    data = request.get_json() or {}
    league_member_id = data.get('league_member_id')
    tournament_id = data.get('tournament_id')
    golfer_id = data.get('golfer_id')
    logger.info("Pick submit - tournament: %s, golfer: %s, member: %s", tournament_id, golfer_id, league_member_id)

    # league_member_id arrives in the request body, so the URL-based decorators
    # do not apply here. Without this check any authenticated user could submit
    # a pick on behalf of any other member in any league.
    if not user_owns_league_member(uid, league_member_id):
        logger.warning("User %s attempted to submit a pick for member %s", uid, league_member_id)
        return jsonify({'error': 'Not authorized'}), 403

    try:
        pick = submit_pick(uid, tournament_id, golfer_id, league_member_id)
    except ValueError as e:
        # Something the caller can fix: unknown tournament or golfer, or the
        # tournament has already started. 400 (Bad Request), not 500.
        logger.info("Rejected pick from user %s: %s", uid, e)
        return jsonify({'error': str(e)}), 400
    except Exception:
        logger.error("Error submitting pick for user %s", uid, exc_info=True)
        return jsonify({'error': 'Failed to submit pick'}), 500

    return jsonify(pick.to_dict()), 201


@pick_bp.route('/current/<int:league_member_id>', methods=['GET'])
@require_auth
@require_own_league_member
def get_current_pick(uid, league_member_id):
    try:
        tournament_id = int(request.args.get('tournament_id'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Valid tournament_id is required'}), 400

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
        logger.error("Error getting current pick: %s", e, exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    
    
@pick_bp.route('/field_stats/<int:tournament_id>', methods=['GET'])
@require_auth
def field_stats(uid, tournament_id):
    stats = get_field_stats(tournament_id)
    return jsonify(stats), 200