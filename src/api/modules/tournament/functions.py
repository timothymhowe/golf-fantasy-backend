from models import Tournament, TournamentGolfer, Golfer, Pick, User, LeagueMember
from datetime import datetime
from sqlalchemy import text, case, desc, and_
from utils.db_connector import db
import logging
import pytz

from modules.user.functions import get_league_member_ids


def get_most_recent_tournament():
    """
    Get the most recent tournament that has started or is currently happening.

    Returns:
        _type_: _description_
    """
    try:
        utc_now = datetime.now(pytz.UTC)
        
        # Get tournaments that might be current or recent
        potential_tournaments = (
            Tournament.query
            .filter(Tournament.start_date <= utc_now.date())
            .order_by(Tournament.start_date.desc(), Tournament.start_time.desc())
            .limit(2)  # Get a couple to check times
            .all()
        )
        
        for tournament in potential_tournaments:
            # Convert tournament time to UTC for comparison
            tournament_tz = pytz.timezone(tournament.time_zone or 'America/New_York')
            tournament_local = tournament_tz.localize(
                datetime.combine(tournament.start_date, tournament.start_time)
            )
            tournament_utc = tournament_local.astimezone(pytz.UTC)
            
            # If this tournament hasn't started yet, skip to next one
            if utc_now < tournament_utc:
                continue
                
            return {
                "id": tournament.id,
                "sportcontent_api_id": tournament.sportcontent_api_id,
                "tournament_name": tournament.tournament_name,
                "tournament_format": tournament.tournament_format,
                "start_date": tournament.start_date.strftime("%Y-%m-%d"),
                "end_date": tournament.end_date.strftime("%Y-%m-%d"),
                "start_time": tournament.start_time.strftime("%H:%M:%S") if tournament.start_time else None,
                "time_zone": tournament.time_zone,
                "course_name": tournament.course_name,
                "location_raw": tournament.location_raw,
            }
            
        logging.warning("No recent tournaments found")
        return None
        
    except Exception as e:
        logging.error(f"Error in get_most_recent_tournament: {str(e)}")
        raise


def get_upcoming_tournament():
    try:
        # Get current time in UTC
        utc_now = datetime.now(pytz.UTC)
        
        # Query the database for the tournament that hasn't started yet
        upcoming_tournament = (
            Tournament.query
            .filter(Tournament.start_date >= utc_now.date())  # Get today and future tournaments
            .order_by(Tournament.start_date, Tournament.start_time)
            .first()
        )

        if upcoming_tournament is None:
            logging.warning("No upcoming tournaments found")
            return None
            
        # Convert tournament time to UTC for comparison
        tournament_tz = pytz.timezone(upcoming_tournament.time_zone or 'America/New_York')
        tournament_local = tournament_tz.localize(
            datetime.combine(upcoming_tournament.start_date, upcoming_tournament.start_time)
        )
        tournament_utc = tournament_local.astimezone(pytz.UTC)
        
        # If tournament has already started, get next one
        if utc_now >= tournament_utc:
            upcoming_tournament = (
                Tournament.query
                .filter(Tournament.start_date > utc_now.date())
                .order_by(Tournament.start_date, Tournament.start_time)
                .first()
            )
            
            if upcoming_tournament is None:
                logging.warning("No upcoming tournaments found after current tournament")
                return None

        # Return the tournament's details
        return {
            "id": upcoming_tournament.id,
            "sportcontent_api_id": upcoming_tournament.sportcontent_api_id,
            "tournament_name": upcoming_tournament.tournament_name,
            "tournament_format": upcoming_tournament.tournament_format,
            "start_date": upcoming_tournament.start_date.strftime("%Y-%m-%d"),
            "start_time": upcoming_tournament.start_time.strftime("%H:%M:%S") if upcoming_tournament.start_time else None,
            "time_zone": upcoming_tournament.time_zone,
            "course_name": upcoming_tournament.course_name,
            "location_raw": upcoming_tournament.location_raw,
        }
    except Exception as e:
        logging.error(f"Error in get_upcoming_tournament: {str(e)}")
        raise


def get_upcoming_roster():
    """
    Retrieves the upcoming roster for a tournament.

    Returns:
        dict: A dictionary containing the tournament ID, tournament name, start date, and roster.
    """

    upcoming_tournament = get_upcoming_tournament()
    tournament_id = upcoming_tournament["id"]
    # upcoming_roster = TournamentGolfer.query.filter_by(tournament_id=tournament_id,is_most_recent=True).all()

    upcoming_roster_with_owgr = (
        TournamentGolfer.query.join(Golfer, TournamentGolfer.golfer_id == Golfer.id)
        .filter(
            TournamentGolfer.tournament_id == tournament_id,
            TournamentGolfer.is_most_recent == True,
        )
        .with_entities(TournamentGolfer.id, Golfer.full_name)
        .all()
    )

    final_roster = [str(tg) for tg in upcoming_roster_with_owgr]

    return {
        "tournament_id": upcoming_tournament["id"],
        "tournament_name": upcoming_tournament["tournament_name"],
        "tournament_start_date": upcoming_tournament["start_date"],
        "tournament_roster": final_roster,
    }


def populate_drop_down(uid):
    upcoming_tournament = get_upcoming_tournament()
    tournament_id = upcoming_tournament["id"]
    upcoming_roster = TournamentGolfer.query.filter_by(
        tournament_id=tournament_id, is_most_recent=True
    ).all()
    
    
    return upcoming_roster


# TODO: Ger rid of shortcut for first league_member_id
        # TODO: Implement lazy loading for the golfers not on the upcoming roster
def get_golfers_with_roster_and_picks(tournament_id: int, uid: str):
    """
    Retrieves golfers with roster and picks information for a specific tournament.
    """
    try:
        league_member_ids = get_league_member_ids(uid)
        if not league_member_ids:
            return None
            
        league_member_id = league_member_ids[0][0]
        
        # Get all golfers with their tournament and pick status
        golfers = (Golfer.query
            .outerjoin(
                TournamentGolfer,
                and_(
                    Golfer.id == TournamentGolfer.golfer_id,
                    TournamentGolfer.tournament_id == tournament_id,
                    TournamentGolfer.is_most_recent == True
                )
            )
            .outerjoin(
                Pick,
                and_(
                    Golfer.id == Pick.golfer_id,
                    Pick.league_member_id == league_member_id,
                    Pick.is_most_recent == True,
                    Pick.tournament_id != tournament_id
                )
            )
            .add_columns(
                TournamentGolfer.tournament_id.isnot(None).label('is_playing_in_tournament'),
                Pick.id.isnot(None).label('has_been_picked')
            )
            .order_by(
                desc('is_playing_in_tournament'),
                Golfer.full_name
            )
            .all())
        
        return {
            "ids": {"tournament_id": tournament_id},
            "golfers": [{
                'id': golfer.id,
                'full_name': golfer.full_name,
                'first_name': golfer.first_name,
                'last_name': golfer.last_name,
                'photo_url': golfer.photo_url,
                'datagolf_id': golfer.datagolf_id,
                'has_been_picked': bool(has_been_picked),
                'is_playing_in_tournament': bool(is_playing_in_tournament)
            } for golfer, is_playing_in_tournament, has_been_picked in golfers]
        }
        
    except Exception as e:
        print(f"Error fetching golfer data: {str(e)}")
        return None

