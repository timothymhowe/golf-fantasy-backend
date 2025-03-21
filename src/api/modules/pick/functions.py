from models import Pick, Tournament, Golfer
from sqlalchemy import desc, select, text
from datetime import datetime
import pytz
from utils.db_connector import db

from modules.user.functions import get_league_member_ids
from data_aggregator.datagolf.rankings.aggregator import get_aggregated_stats
from flask import jsonify
import logging

logger = logging.getLogger(__name__)

def submit_pick(uid, tournament_id, golfer_id, league_member_id):
    league_member_ids = get_league_member_ids(uid)

    # TODO: URGENT LETS NOT DO HARDCODING
    # tournament_id = 124
    tournament = Tournament.query.get(tournament_id)

    # Combine date and time into a single datetime object
    local_start_datetime = datetime.combine(
        tournament.start_date, tournament.start_time
    )

    # Convert local datetime to UTC
    local_tz = pytz.timezone(tournament.time_zone)
    local_start_datetime = local_tz.localize(local_start_datetime)
    utc_start_datetime = local_start_datetime.astimezone(pytz.utc)

    # TODO: implement functionality for multiple leagues, for now just search the first league the user is in.
    # league_member_id = league_member_ids[0][0]

    if utc_start_datetime <= datetime.utcnow().replace(tzinfo=pytz.utc):
        raise ValueError("Tournament has already started")

    new_pick = Pick(
        league_member_id=league_member_id,
        tournament_id=tournament_id,
        golfer_id=golfer_id,
        year=utc_start_datetime.year,
    )

    # Find the previous most recent pick and update its is_most_recent flag
    previous_pick = Pick.query.filter_by(
        league_member_id=new_pick.league_member_id,
        tournament_id=new_pick.tournament_id,
        is_most_recent=True,
    ).first()

    if previous_pick is not None:
        previous_pick.is_most_recent = False

    # commit the session, save the pick
    db.session.add(new_pick)
    db.session.commit()

    # Query the database for the new pick
    saved_pick = Pick.query.filter_by(
        league_member_id=new_pick.league_member_id,
        tournament_id=new_pick.tournament_id,
        golfer_id=new_pick.golfer_id,
        is_most_recent=True,
    ).first()
    if saved_pick is None:
        raise Exception("Failed to save pick to database, could not find saved pick.")

    elif previous_pick is not None:
        if previous_pick.timestamp_utc == saved_pick.timestamp_utc:
            raise Exception("Failed to update previous pick, timestamp did not change.")

    return saved_pick

# Query for the most recent pick for the week by a user with a given UID
def get_most_recent_pick(uid, tournament_id, league_member_id):
    """
    Retrieves the most recent pick for a user in a specific tournament.
    Joins with the Golfer table to get complete golfer information.
    
    Args:
        uid (str): Firebase user ID
        tournament_id (int): ID of the tournament
        
    Returns:
        dict: Pick data including golfer details, or None if no pick exists
        Keys:
            - first_name: Golfer's first name
            - last_name: Golfer's last name
            - full_name: Golfer's full name
            - photo_url: URL to golfer's photo
            - golfer_id: Internal golfer ID
            - tournament_id: Tournament ID
            - datagolf_id: DataGolf's ID for the golfer
    """
    try:
        # league_member_ids = get_league_member_ids(uid)
        # league_member_id = league_member_ids[0][0]

        stmt = (
            select(Pick, Golfer)
            .select_from(Pick)
            .join(Golfer, Pick.golfer_id == Golfer.id)
            .where(
                Pick.league_member_id == league_member_id,
                Pick.tournament_id == tournament_id,
                Pick.is_most_recent == True
            )
        )

        result = db.session.execute(stmt)
        row = result.fetchone()
        
        if row is None:
            return None
            
        the_pick, the_golfer = row

        return {
            "status": "success",
            "has_pick": True,
            "first_name": the_golfer.first_name,
            "last_name": the_golfer.last_name,
            "full_name": the_golfer.full_name,
            "photo_url": the_golfer.photo_url,
            "golfer_id": the_pick.golfer_id,
            "tournament_id": the_pick.tournament_id,
            "datagolf_id": the_golfer.datagolf_id
        }

    except Exception as e:
        print(f"Error in get_most_recent_pick: {str(e)}")
        raise

def get_field_stats(tournament_id: int):
    """
    Get detailed stats for all players in the tournament field
    
    Args:
        tournament_id: ID of the tournament to get stats for
        
    Returns:
        dict: Tournament and player stats or error response
    """
    try:
        # Get aggregated stats from DataGolf
        stats = get_aggregated_stats()
        if not stats:
            return {
                'success': False,
                'error': 'Failed to fetch tournament stats'
            }
            
        return {
            'success': True,
            'data': stats
        }
        
    except Exception as e:
        logger.error(f"Error getting field stats: {e}")
        return {
            'success': False,
            'error': str(e)
        }