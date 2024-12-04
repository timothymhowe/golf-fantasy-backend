from sqlalchemy import desc, select
from models import User, Pick, LeagueMember, Tournament, TournamentGolfer, TournamentGolferResult, Golfer, LeagueMemberTournamentScore

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
    """Get the list of league member IDs and their associated league IDs for a user.

    Args:
        uid (str): The unique identifier of the user.

    Returns:
        list[tuple]: List of tuples containing (league_member_id, league_id) pairs.
    """
    user_stmt = select(User).where(User.firebase_id == uid)
    user_result = db.session.execute(user_stmt)
    user = user_result.fetchone()[0]
    
    if user:
        league_member_stmt = select(LeagueMember.id, LeagueMember.league_id).where(LeagueMember.user_id == user.id)
        league_member_result = db.session.execute(league_member_stmt)
        league_member_ids = league_member_result.fetchall()
        return league_member_ids
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
    
    user = User.query.filter_by(firebase_uid=firebase_id).first()
    if not user:
        logger.error(f"No database user found for Firebase UID: {firebase_id}")
        raise ValueError("User not found in database")
        
    logger.debug(f"Found database user ID: {user.id}")
    return user.id


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