from models import LeagueInviteCode, LeagueMember, InviteCodeUsage, User, Tournament, Golfer, League, ScheduleTournament, Pick
from utils.db_connector import db
from datetime import datetime, timedelta
import logging
from firebase_admin import firestore

logger = logging.getLogger(__name__)

def validate_and_use_invite_code(code: str, firebase_id: str):
    """
    Validates and processes a league invite code
    
    Args:
        code (str): The invite code to validate
        firebase_uid (str): Firebase UID of the user
    """
    logger.info(f"Validating invite code: {code} for Firebase user: {firebase_id}")
    
    try:
        # Convert Firebase UID to database user ID
        user = User.query.filter_by(firebase_id=firebase_id).first()
        if not user:
            logger.error(f"No database user found for Firebase UID: {firebase_id}")
            return False, "User not found in database", 404
            
        user_id = user.id
        logger.debug(f"Found database user ID: {user_id}")

        # Find and validate invite code
        invite = LeagueInviteCode.query.filter_by(code=code).first()
        logger.debug(f"Found invite code: {invite}")
        
        if not invite:
            logger.warning(f"Invalid invite code: {code}")
            return False, "Invalid invite code", 404

        # Check expiration
        if invite.expires_at and invite.expires_at < datetime.utcnow():
            logger.warning(f"Expired invite code: {code}")
            return False, "Invite code has expired", 400

        # Check max uses
        if invite.max_uses:
            usage_count = InviteCodeUsage.query.filter_by(invite_code_id=invite.id).count()
            logger.debug(f"Current usage count: {usage_count} of {invite.max_uses}")
            if usage_count >= invite.max_uses:
                return False, "Invite code has reached maximum uses", 400

        # Check if user is already in the league
        existing_member = LeagueMember.query.filter_by(
            user_id=user_id,
            league_id=invite.league_id
        ).first()
        
        if existing_member:
            logger.warning(f"User {user_id} is already a member of league {invite.league_id}")
            return False, "You are already a member of this league", 400

        try:
            # Create league membership
            new_member = LeagueMember(
                user_id=user_id,
                league_id=invite.league_id,
                role_id=invite.role_id
            )
            db.session.add(new_member)

            # Record invite code usage
            usage = InviteCodeUsage(
                invite_code_id=invite.id,
                user_id=user_id
            )
            db.session.add(usage)
            
            db.session.commit()
            logger.info(f"Successfully added user {user_id} to league {invite.league_id}")
            return True, {"league_id": invite.league_id}, 200

        except Exception as e:
            logger.error(f"Database error while processing invite: {str(e)}", exc_info=True)
            db.session.rollback()
            return False, "Failed to join league", 500

    except Exception as e:
        logger.error(f"Error validating invite code: {str(e)}", exc_info=True)
        return False, f"Internal server error: {str(e)}", 500

def get_manual_pick_data(league_id: int):
    """Get all data needed for manual pick entry by commissioner.

    This function retrieves the necessary data for commissioners to manually enter picks
    for league members. It returns three lists of data:
    
    1. League Members: All members in the specified league
    2. Tournaments: All upcoming tournaments
    3. Golfers: All active golfers in the system

    Args:
        league_id (int): The ID of the league to get members from

    Returns:
        dict: A dictionary containing three lists with the following structure:
        {
            'league_members': [
                {
                    'id': int,       # league_member_id from LeagueMember
                    'name': str      # Concatenated User.first_name + User.last_name
                },
                ...
            ],
            'tournaments': [
                {
                    'id': int,           # Tournament.id
                    'name': str,         # Tournament.tournament_name
                    'start_date': str    # Tournament.start_date in YYYY-MM-DD format
                },
                ...
            ],
            'golfers': [
                {
                    'id': str,       # Golfer.id (Note: this is a STRING in the model)
                    'name': str      # Concatenated Golfer.first_name + Golfer.last_name
                },
                ...
            ]
        }

    Raises:
        Exception: If there's any error accessing the database
    """
    try:
        # Get league members with user info
        members = db.session.query(
            LeagueMember.id.label('league_member_id'),
            User.first_name,
            User.last_name
        ).join(
            User, LeagueMember.user_id == User.id
        ).filter(
            LeagueMember.league_id == league_id
        ).order_by(
            User.last_name, User.first_name
        ).all()

        # Get league's schedule_id
        league = db.session.query(League.schedule_id).filter(
            League.id == league_id
        ).first()

        if not league or not league.schedule_id:
            raise ValueError(f"League {league_id} has no schedule assigned")

        # Get upcoming tournaments from league's schedule
        tournaments = db.session.query(
            Tournament.id,
            Tournament.tournament_name,
            Tournament.start_date,
            Tournament.start_time,
            Tournament.time_zone
        ).join(
            ScheduleTournament, Tournament.id == ScheduleTournament.tournament_id
        ).filter(
            ScheduleTournament.schedule_id == league.schedule_id,
        ).order_by(
            Tournament.start_date
        ).all()

        # Get golfers
        golfers = db.session.query(
            Golfer.id,
            Golfer.first_name,
            Golfer.last_name
        ).order_by(
            Golfer.last_name, Golfer.first_name
        ).all()

        return {
            'league_members': [
                {
                    'id': m.league_member_id,
                    'name': f"{m.first_name} {m.last_name}"
                } for m in members
            ],
            'tournaments': [
                {
                    'id': t.id,
                    'name': t.tournament_name,
                    'start_date': t.start_date.strftime('%Y-%m-%d')
                } for t in tournaments
            ],
            'golfers': [
                {
                    'id': g.id,
                    'name': f"{g.first_name} {g.last_name}"
                } for g in golfers
            ]
        }

    except Exception as e:
        logger.error(f"Error getting manual pick data: {str(e)}", exc_info=True)
        return None


def create_manual_pick(league_member_id: int, tournament_id: int, golfer_id: str, commissioner_uid: str):
    """Create a manual pick entry for a league member and log the action to Firebase.
    
    Args:
        league_member_id (int): ID of the league member
        tournament_id (int): ID of the tournament
        golfer_id (str): ID of the selected golfer
        commissioner_uid (str): Firebase UID of the commissioner making the change
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get all the necessary information first
        tournament = Tournament.query.get(tournament_id)
        if not tournament:
            logger.error(f"Tournament {tournament_id} not found")
            return False

        league_member = db.session.query(
            LeagueMember, User
        ).join(
            User, LeagueMember.user_id == User.id
        ).filter(
            LeagueMember.id == league_member_id
        ).first()

        if not league_member:
            logger.error(f"League member {league_member_id} not found")
            return False

        golfer = Golfer.query.get(golfer_id)
        if not golfer:
            logger.error(f"Golfer {golfer_id} not found")
            return False

        pick_timestamp = datetime.combine(
            tournament.start_date - timedelta(days=1),
            datetime.min.time()
        )

        # Get previous pick if it exists
        previous_pick = Pick.query.filter_by(
            league_member_id=league_member_id,
            tournament_id=tournament_id,
            is_most_recent=True
        ).first()

        # Log the change to Firebase first
        firestore_db = firestore.client()
        audit_ref = firestore_db.collection('manual_pick_audit').document()
        
        audit_data = {
            'timestamp': firestore.SERVER_TIMESTAMP,
            'commissioner_uid': commissioner_uid,
            'league_id': league_member.LeagueMember.league_id,
            'league_member': {
                'id': league_member_id,
                'name': f"{league_member.User.first_name} {league_member.User.last_name}",
                'email': league_member.User.email
            },
            'tournament': {
                'id': tournament.id,
                'name': tournament.tournament_name,
                'start_date': tournament.start_date.isoformat()
            },
            'pick': {
                'old_golfer': {
                    'id': previous_pick.golfer_id if previous_pick else None,
                    'name': Golfer.query.get(previous_pick.golfer_id).full_name if previous_pick else None
                } if previous_pick else None,
                'new_golfer': {
                    'id': golfer.id,
                    'name': golfer.full_name
                }
            },
            'pick_timestamp': pick_timestamp.isoformat()
        }

        # Write to Firebase
        audit_ref.set(audit_data)
        logger.info(f"Audit log created with ID: {audit_ref.id}")

        # Now make database changes
        if previous_pick:
            Pick.query.filter_by(
                league_member_id=league_member_id,
                tournament_id=tournament_id,
                is_most_recent=True
            ).update({'is_most_recent': False})

        # Create new pick
        new_pick = Pick(
            league_member_id=league_member_id,
            tournament_id=tournament_id,
            golfer_id=golfer_id,
            year=tournament.year,
            timestamp_utc=pick_timestamp,
            is_most_recent=True
        )
        
        db.session.add(new_pick)
        db.session.commit()
        
        logger.info(f"Successfully created pick for member {league_member_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating manual pick: {str(e)}", exc_info=True)
        db.session.rollback()
        return False