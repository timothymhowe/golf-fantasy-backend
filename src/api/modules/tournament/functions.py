from models import Tournament, TournamentGolfer, Golfer, Pick, User, LeagueMember, Schedule, ScheduleTournament, League
from datetime import datetime, time, timedelta
from sqlalchemy import text, case, desc, and_
from utils.db_connector import db
import logging
import pytz

from modules.user.functions import get_league_member_ids


def get_most_recent_tournament(league_id):
    """
    Get the most recent tournament for a given league's schedule.

    Args:
        league_id (int): The ID of the league.

    Returns:
        dict: Details of the most recent tournament or None if not found.
    """
    try:
        utc_now = datetime.now(pytz.UTC)
        
        # Get the league
        league = League.query.get(league_id)
        if not league or not league.schedule_id:
            logging.warning(f"No schedule found for league {league_id}")
            return None

        # Get tournaments that might be current or recent
        potential_tournaments = (
            Tournament.query
            .join(ScheduleTournament, ScheduleTournament.tournament_id == Tournament.id)
            .filter(
                ScheduleTournament.schedule_id == league.schedule_id,
                Tournament.start_date <= utc_now.date()
            )
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


def get_upcoming_tournament(league_id):
    try:
        # Get current time in UTC
        utc_now = datetime.now(pytz.UTC)
        
        # Get the league first
        league = League.query.get(league_id)
        if not league:
            return {"status": "error", "message": f"League {league_id} not found"}
        if not league.schedule_id:
            return {"status": "error", "message": f"No schedule found for league {league_id}"}

        # Query the database for the next tournament in the league's schedule
        upcoming_tournament = (
            Tournament.query
            .join(ScheduleTournament, ScheduleTournament.tournament_id == Tournament.id)
            .filter(
                ScheduleTournament.schedule_id == league.schedule_id,
                Tournament.start_date >= utc_now.date()
            )
            .order_by(Tournament.start_date, Tournament.start_time)
            .first()
        )

        if upcoming_tournament is None:
            return {
                "status": "no_tournaments",
                "message": "No upcoming tournaments found for the league's schedule"
            }
            
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
                .join(ScheduleTournament, ScheduleTournament.tournament_id == Tournament.id)
                .filter(
                    ScheduleTournament.schedule_id == league.schedule_id,
                    Tournament.start_date > utc_now.date()
                )
                .order_by(Tournament.start_date, Tournament.start_time)
                .first()
            )
            
            if upcoming_tournament is None:
                return {
                    "status": "no_tournaments",
                    "message": "No upcoming tournaments found after current tournament"
                }

        # Return the tournament's details
        return {
            "status": "success",
            "data": {
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
        }
    except Exception as e:
        logging.error(f"Error in get_upcoming_tournament: {str(e)}")
        return {"status": "error", "message": str(e)}


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
def get_golfers_with_roster_and_picks(tournament_id: int, uid: str,league_member_id: int):
    """
    Retrieves golfers with roster and picks information for a specific tournament.
    """
    try:
        league_member_ids = get_league_member_ids(uid)
        if not league_member_ids:
            return None
            
        # league_member_id = league_member_ids[0][0]
        
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

def get_days_until_previous_monday(tournament_date):
    """
    Calculate days between a date and its previous Monday.
    Returns 0 if date is a Monday.
    """
    current_day = tournament_date.weekday()  # 0=Monday, 6=Sunday
    if current_day == 0:  # Already Monday
        return 0
    else:  # Tuesday-Sunday, count back to Monday
        return current_day

def get_current_or_next_tournament(league_id):
    """
    Get both recent and upcoming tournament data with timing information.
    
    TODO: Optimize database queries
    - Currently querying league schedule multiple times (in get_most_recent and get_upcoming)
    - Could refactor to get schedule once and pass to helper functions
    - Or create a single optimized query that gets both tournaments at once
    """
    try:
        # Get both tournaments
        recent = get_most_recent_tournament(league_id)
        upcoming_result = get_upcoming_tournament(league_id)
        
        if upcoming_result["status"] != "success":
            return {"status": "error", "message": "No upcoming tournament found"}
            
        upcoming = upcoming_result["data"]
        
        # Calculate pick window timing for upcoming tournament
        tournament_tz = pytz.timezone(upcoming["time_zone"] or 'America/New_York')
        current_time = datetime.now(tournament_tz)
        tournament_start = tournament_tz.localize(
            datetime.combine(
                datetime.strptime(upcoming["start_date"], "%Y-%m-%d").date(),
                datetime.strptime(upcoming["start_time"], "%H:%M:%S").time() if upcoming["start_time"] else time(0, 0)
            )
        )
        
        # Calculate Monday 5pm for upcoming tournament
        days_back = get_days_until_previous_monday(tournament_start)
        pick_window_open = tournament_start - timedelta(days=days_back)
        pick_window_open = pick_window_open.replace(hour=17, minute=0, second=0, microsecond=0)
        
        # Determine current state
        picks_open = current_time >= pick_window_open and current_time < tournament_start
        tournament_live = recent and datetime.strptime(recent["end_date"], "%Y-%m-%d").date() >= current_time.date()
        
        return {
            "status": "success",
            "recent_tournament": recent,
            "upcoming_tournament": upcoming,
            "timing": {
                "current_time": current_time.isoformat(),
                "pick_window_opens": pick_window_open.isoformat(),
                "tournament_start": tournament_start.isoformat(),
            },
            "state": {
                "picks_open": picks_open,
                "tournament_live": tournament_live
            }
        }
            
    except Exception as e:
        logging.error(f"Error in get_current_or_next_tournament: {str(e)}")
        return {"status": "error", "message": str(e)}


