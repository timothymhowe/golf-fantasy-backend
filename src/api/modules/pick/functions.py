from models import Pick, Tournament, Golfer
from sqlalchemy import desc, select, text
from datetime import datetime
import pytz
from utils.db_connector import db

from data_aggregator.datagolf.rankings.aggregator import get_aggregated_stats
from flask import jsonify
import logging

logger = logging.getLogger(__name__)

def submit_pick(uid, tournament_id, golfer_id, league_member_id):
    """Record a pick for a league member.

    Every reason to reject a pick is checked before anything is written, so a
    caller that sees an exception knows nothing was saved. Raises ValueError
    for anything the user can fix (unknown tournament or golfer, tournament
    already under way); the route maps that to 400 (Bad Request).

    Ownership of league_member_id is enforced by the route before this runs.
    """
    tournament = Tournament.query.get(tournament_id)
    if tournament is None:
        raise ValueError(f"Tournament {tournament_id} not found")

    if Golfer.query.get(golfer_id) is None:
        # Without this the bad id reaches the insert and surfaces as an
        # IntegrityError, i.e. 500 (Internal Server Error) for a user typo.
        raise ValueError(f"Golfer {golfer_id} not found")

    local_tz = pytz.timezone(tournament.time_zone)
    local_start_datetime = local_tz.localize(
        datetime.combine(tournament.start_date, tournament.start_time)
    )
    utc_start_datetime = local_start_datetime.astimezone(pytz.utc)

    if utc_start_datetime <= datetime.utcnow().replace(tzinfo=pytz.utc):
        raise ValueError("Tournament has already started")

    # Everything below writes. Nothing above it does.
    try:
        # Bulk UPDATE, not .first() + flip one object. A member who already has
        # two rows flagged is_most_recent -- from an earlier double-submit race
        # -- would otherwise stay at two forever: one gets demoted, one gets
        # inserted, and the count never comes down. Demoting all of them means
        # every submission heals the row set it touches.
        demoted = Pick.query.filter_by(
            league_member_id=league_member_id,
            tournament_id=tournament_id,
            is_most_recent=True,
        ).update({'is_most_recent': False}, synchronize_session=False)

        if demoted > 1:
            logger.warning(
                "Member %s had %s picks flagged most-recent for tournament %s; "
                "demoted all of them", league_member_id, demoted, tournament_id
            )

        new_pick = Pick(
            league_member_id=league_member_id,
            tournament_id=tournament_id,
            golfer_id=golfer_id,
            year=utc_start_datetime.year,
        )
        db.session.add(new_pick)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.error("Failed to save pick for member %s", league_member_id, exc_info=True)
        raise

    return new_pick

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
        logger.error("Error in get_most_recent_pick: %s", e)
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
        logger.error("Error getting field stats: %s", e, exc_info=True)
        return {
            'success': False,
            'error': 'Failed to retrieve field stats'
        }