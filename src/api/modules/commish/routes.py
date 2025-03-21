import logging
from flask import Blueprint, jsonify, request
from modules.authentication.auth import require_auth
from modules.user.functions import get_db_user_id
from modules.commish.functions import validate_and_use_invite_code, get_manual_pick_data, create_manual_pick
from models import LeagueMember

logger = logging.getLogger(__name__)

commish_bp = Blueprint('commish', __name__)

def check_league_access(firebase_uid: str, league_id: int) -> bool:
    """Check if user has commissioner or admin access to the league"""
    try:
        # Convert Firebase UID to database user ID
        user_id = get_db_user_id(firebase_uid)
        if not user_id:
            logger.warning(f"No database user found for Firebase UID: {firebase_uid}")
            return False
            
        member = LeagueMember.query.filter_by(
            user_id=user_id,
            league_id=league_id
        ).first()
        
        if not member:
            return False
            
        # Check if user is commissioner or admin
        return member.role_id in [1, 2]  # ROLE_COMMISSIONER = 1, ROLE_ADMIN = 2
        
    except Exception as e:
        logger.error(f"Error checking league access: {str(e)}", exc_info=True)
        return False

@commish_bp.route('/join', methods=['POST'])
@require_auth
def join_league(uid):
    """Handle league invite code submission"""
    logger.info(f"Received join request for user {uid}")
    
    try:
        data = request.get_json()
        logger.debug(f"Request data: {data}")
        
        user_id = uid
        code = data.get('code')
        
        logger.info(f"Processing invite code: {code} for user: {user_id}")

        if not code:
            logger.warning("No invite code provided")
            return jsonify({'message': 'Invite code is required'}), 400

        success, result, status_code = validate_and_use_invite_code(code, user_id)
        logger.info(f"Validation result: success={success}, status={status_code}, result={result}")
        
        if success:
            return jsonify(result), status_code
        else:
            return jsonify({'message': result}), status_code
            
    except Exception as e:
        logger.error(f"Error processing join request: {str(e)}", exc_info=True)
        return jsonify({'message': 'Internal server error', 'error': str(e)}), 500

@commish_bp.route('/manual-pick-data/<int:league_id>', methods=['GET'])
@require_auth
def get_pick_data(uid, league_id):
    """Get data needed for manual pick entry"""
    logger.info(f"Fetching manual pick data for league {league_id}")
    
    try:
        # Check if user has appropriate access
        # if not check_league_access(uid, league_id):
        #     logger.warning(f"Unauthorized access attempt by user {uid} for league {league_id}. Notifying admin.")
        #     return jsonify({'message': 'Unauthorized access'}), 403
            
        data = get_manual_pick_data(league_id)
        if data is None:
            logger.error("Failed to fetch manual pick data")
            return jsonify({'message': 'Failed to fetch data'}), 500
            
        return jsonify(data), 200
            
    except Exception as e:
        logger.error(f"Error fetching manual pick data: {str(e)}", exc_info=True)
        return jsonify({'message': 'Internal server error', 'error': str(e)}), 500

@commish_bp.route('/manual-pick', methods=['POST'])
@require_auth
def submit_manual_pick(uid):
    """Submit a manual pick for a league member"""
    logger.info(f"Submitting manual pick by commissioner {uid}")
    
    try:
        data = request.get_json()
        logger.info(f"Received data: {data}")
        
        league_member_id = data.get('league_member_id')
        tournament_id = data.get('tournament_id')
        golfer_id = data.get('golfer_id')
        
        logger.info(f"Processing pick - Member: {league_member_id}, Tournament: {tournament_id}, Golfer: {golfer_id}")
        
        # Validate required fields
        if not all([league_member_id, tournament_id, golfer_id]):
            logger.warning("Missing required fields in manual pick submission")
            return jsonify({'message': 'Missing required fields'}), 400
            
        # Check if user has commissioner access
        league_id = LeagueMember.query.get(league_member_id).league_id
        if not check_league_access(uid, league_id):
            logger.warning(f"Unauthorized manual pick attempt by user {uid}")
            return jsonify({'message': 'Unauthorized access'}), 403
            
        # Call function to process the pick
        success = create_manual_pick(league_member_id, tournament_id, golfer_id, uid)
        
        if success:
            logger.info("Pick submitted successfully")
            return jsonify({'message': 'Pick submitted successfully'}), 200
        else:
            logger.error("Failed to submit pick")
            return jsonify({'message': 'Failed to submit pick'}), 500
            
    except Exception as e:
        logger.error(f"Error submitting manual pick: {str(e)}", exc_info=True)
        return jsonify({'message': 'Internal server error', 'error': str(e)}), 500