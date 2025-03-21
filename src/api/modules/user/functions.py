from sqlalchemy import desc, select
from models import User, Pick, LeagueMember, Tournament, TournamentGolfer, TournamentGolferResult, Golfer, LeagueMemberTournamentScore, League, Role
from datetime import datetime
import pytz

from utils.db_connector import db
import logging

logger = logging.getLogger(__name__)

# TODO: Deprecate this function and fully migrate to the pick module
# Query for the most recent pick for the week by a user with a given UID
def get_most_recent_pick(uid,tournament_id):
    """Get the most recent pick for a user.
        TODO: Deprecate this function and fully migrate to the pick module
    Args:
        uid (int): The user ID.

    Returns:
        Pick: The most recent pick for the user, or None if no pick is found.
    """

    user_stmt = select(User).where(User.firebase_id == uid)
    user_result = db.session.execute(user_stmt)
    user = user_result.fetchone()
    
    # If the valid user session exists, query for the most recent pick
    if user:
        pick_stmt = select(Pick).where(Pick.user_id == user.id).order_by(desc(Pick.date))
        pick_result = db.session.execute(pick_stmt)
        pick = pick_result.scalars().first()
        return pick

    return None

def pick_history(uid):
    """Get the pick history for a user.

    Args:
        uid (int): The user ID.

    Returns:
        list: A list of the user's picks.
    """
    user_stmt = select(User).where(User.firebase_id == uid)
    user_result = db.session.execute(user_stmt)
    user = user_result.fetchone()
    
    # If the valid user session exists, query for the most recent pick
    if user:
        pick_stmt = select(Pick).where(Pick.user_id == user.id).order_by(desc(Pick.date))
        pick_result = db.session.execute(pick_stmt)
        picks = pick_result.scalars().all()
        return picks

    return None

def submit_pick(uid, tournament_id, golfer_id):
    """Submit a pick for a user in a tournament.

    Args:
        uid (str): The unique identifier of the user.
        tournament_id (int): The ID of the tournament.
        golfer_id (int): The ID of the golfer.

    Returns:
        Pick: The created pick object if successful, None otherwise.
    """
    user_stmt = select(User).where(User.firebase_id == uid)
    user_result = db.session.execute(user_stmt)
    user = user_result.fetchone()
    
    if user:
        pick = Pick(user_id=user.id, tournament_id=tournament_id, golfer_id=golfer_id)
        db.session.add(pick)
        db.session.commit()
        return pick
    return None

def get_league_member_ids(uid):
    """Get the list of league member IDs, league IDs, league names, and active status for a user.

    Args:
        uid (str): The unique identifier of the user.

    Returns:
        list[dict]: List of dictionaries containing league member ID, league ID, league name, and active status.
    """
    try:
        # Fetch the user by Firebase UID
        user = db.session.query(User).filter(User.firebase_id == uid).first()
        
        if not user:
            logger.error(f"User not found for UID: {uid}")
            return None
        
        # Query for league memberships
        league_member_stmt = (
            db.session.query(
                LeagueMember.id.label('league_member_id'),
                League.id.label('league_id'),
                League.name.label('league_name'),
                League.is_active
            )
            .join(League, LeagueMember.league_id == League.id)
            .filter(LeagueMember.user_id == user.id)
            .all()
        )
        
        league_member_ids = [{
            'league_member_id': lm.league_member_id,
            'league_id': lm.league_id,
            'league_name': lm.league_name,
            'is_active': lm.is_active
        } for lm in league_member_stmt]
        
        return league_member_ids
        
    except Exception as e:
        logger.error(f"Error getting league member IDs: {e}", exc_info=True)
        return None

def get_detailed_pick_history_by_member(league_member_id: int):
    """
    Get detailed pick history for a league member including tournament results and scoring.
    
    Args:
        league_member_id (int): ID of the league member
    
    Returns:
        dict: Summary of member's pick history with scoring details
    """
    # Get league member and associated user
    league_member = (db.session.query(LeagueMember, User)
        .join(User, LeagueMember.user_id == User.id)
        .filter(LeagueMember.id == league_member_id)
        .first())
    
    if not league_member:
        return None
        
    total_points = 0
    history = []
    
    # Get all picks for this league member
    picks = (db.session.query(
            Pick,
            Tournament.tournament_name,
            Tournament.is_major,
            Golfer.first_name,
            Golfer.last_name,
            TournamentGolferResult.result,
            LeagueMemberTournamentScore.score,
            LeagueMemberTournamentScore.is_no_pick,
            LeagueMemberTournamentScore.is_duplicate_pick
        )
        .join(Tournament, Pick.tournament_id == Tournament.id)
        .join(Golfer, Pick.golfer_id == Golfer.id)
        .outerjoin(TournamentGolfer, 
            (TournamentGolfer.tournament_id == Pick.tournament_id) & 
            (TournamentGolfer.golfer_id == Pick.golfer_id))
        .outerjoin(TournamentGolferResult, TournamentGolfer.id == TournamentGolferResult.tournament_golfer_id)
        .outerjoin(LeagueMemberTournamentScore,
            (LeagueMemberTournamentScore.tournament_id == Pick.tournament_id) &
            (LeagueMemberTournamentScore.league_member_id == league_member.id))
        .filter(Pick.league_member_id == league_member.id)
        .order_by(Tournament.start_date)
        .all())
    
    for pick in picks:
        points = pick.score / 100 if pick.score is not None else 0
        total_points += points
        
        entry = {
            'tournament': pick.tournament_name,
            'is_major': pick.is_major,
            'golfer': f"{pick.first_name} {pick.last_name}",
            'position': pick.result or 'N/A',
            'points': f"{points:.2f}",
            'no_pick': pick.is_no_pick,
            'duplicate_pick': pick.is_duplicate_pick
        }
        history.append(entry)
        
        # Print detailed information
        major_str = "(MAJOR)" if pick.is_major else ""
        status = "NO PICK" if pick.is_no_pick else "DUPLICATE" if pick.is_duplicate_pick else pick.result
        print(f"{pick.tournament_name} {major_str}")
        print(f"  Pick: {pick.first_name} {pick.last_name}")
        print(f"  Position: {status}")
        print(f"  Points: {points:.2f}")
        print("------------------")
    
    print(f"\nTotal Points: {total_points:.2f}")
    
    return {
        'user': league_member.User.display_name,
        'total_points': total_points,
        'pick_history': history
    }

def get_db_user_id(firebase_id: str) -> int:
    """Convert Firebase UID to database user ID"""
    logger.debug(f"Looking up database ID for Firebase UID: {firebase_id}")
    
    user = User.query.filter_by(firebase_id=firebase_id).first()
    if not user:
        logger.error(f"No database user found for Firebase UID: {firebase_id}")
        raise ValueError("User not found in database")
        
    logger.debug(f"Found database user ID: {user.id}")
    return user.id





# TODO: Move this to the tournament module
def has_tournament_started(tournament_id: int) -> bool:
    """
    Check if a tournament has started based on its start date and time in the tournament's timezone
    
    Args:
        tournament_id (int): The ID of the tournament to check
        
    Returns:
        bool: True if tournament has started, False if not yet started
        
    Raises:
        ValueError: If tournament_id is invalid or tournament not found
    """
    try:
        # Get tournament details
        tournament = (
            db.session.query(Tournament)
            .filter(Tournament.id == tournament_id)
            .first()
        )
        
        if not tournament:
            logger.error(f"Tournament not found: {tournament_id}")
            raise ValueError(f"Tournament not found: {tournament_id}")
            
        # Get current time in UTC
        now = datetime.now(pytz.UTC)
        
        # Get tournament timezone
        tournament_tz = pytz.timezone(tournament.time_zone or 'UTC')  # Default to UTC if no timezone specified
        
        # Combine tournament date and time in tournament's timezone
        local_start = datetime.combine(
            tournament.start_date,
            tournament.start_time or datetime.min.time(),  # Default to midnight if no time specified
        )
        
        # Localize the datetime to tournament's timezone
        tournament_start = tournament_tz.localize(local_start)
        
        # Convert tournament start to UTC for comparison
        tournament_start_utc = tournament_start.astimezone(pytz.UTC)
        
        # Return True if tournament has started
        return now >= tournament_start_utc
        
    except Exception as e:
        logger.error(f"Error checking tournament start: {e}", exc_info=True)
        raise

def get_user_profile(uid):
    """Get user profile including league memberships and roles.

    Args:
        uid (str): Firebase UID of the user

    Returns:
        dict: User profile information including leagues and roles
    """
    try:
        # Join query to get user data and their league memberships with roles
        user_data = (
            db.session.query(
                User,
                LeagueMember,
                League,
                Role
            )
            .join(LeagueMember, User.id == LeagueMember.user_id)
            .join(League, LeagueMember.league_id == League.id)
            .join(Role, LeagueMember.role_id == Role.id)
            .filter(User.firebase_id == uid)
            .all()
        )
        
        if not user_data:
            logger.error(f"User not found for UID: {uid}")
            return None
            
        # First row contains user info
        user = user_data[0][0]
        
        # Format league memberships
        leagues = [{
            'league_member_id': row[1].id,
            'league_id': row[2].id,
            'league_name': row[2].name,
            'role_id': row[3].id,
            'role_name': row[3].name,
            'is_active': row[2].is_active
        } for row in user_data]
           
        return {
            'success': True,
            'data': {
                'id': user.id,
                'display_name': user.display_name,
                'email': user.email,
                'avatar_url': user.avatar_url,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'leagues': leagues
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user profile: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    from flask import Flask
    from utils.db_connector import init_db
    
    # Initialize Flask app and database connection
    app = Flask(__name__)
    init_db(app)
    
    # Run within app context
    with app.app_context():
        try:
            # Get user input
            league_member_id = input("Enter League_member_id to check pick history: ")
            
            # Get and display history
            history = get_detailed_pick_history_by_member(int(league_member_id))
            
            if history is None:
                print(f"\nNo user found with UID: {league_member_id}")
            
        except Exception as e:
            print(f"An error occurred: {e}")
            db.session.rollback()