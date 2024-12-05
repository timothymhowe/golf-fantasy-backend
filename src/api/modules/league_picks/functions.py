from models import League, LeagueMember, Pick, Tournament, Golfer, Schedule, ScheduleTournament, User
from utils.db_connector import db
from datetime import datetime
import pytz
import logging

logger = logging.getLogger(__name__)

def get_current_week_picks(league_id: int) -> dict:
    """
    Get all picks for the current week's tournament for a given league
    
    Args:
        league_id: ID of the league
        
    Returns:
        Dictionary containing:
        - tournament info
        - list of member picks
        {
            'tournament': {
                'id': int,
                'name': str,
                'start_date': str,
                'is_major': bool,
                'week_number': int
            },
            'picks': [
                {
                    'member': {
                        'id': int,
                        'name': str,
                        'first_name': str,
                        'last_name': str,
                        'photo_url': str
                    },
                    'pick': {
                        'golfer_id': int,
                        'golfer_name': str,
                        'datagolf_id': str,
                        'status': str,
                        'score_to_par': int,
                        'position': str
                    } or None if no pick
                }
            ]
        }
    """
    try:
        # Get league's schedule
        league = League.query.get(league_id)
        if not league:
            return None
            
        # Get current tournament from schedule
        utc_now = datetime.now(pytz.UTC)
        
        current_tournament = (
            db.session.query(Tournament, ScheduleTournament)
            .join(ScheduleTournament, Tournament.id == ScheduleTournament.tournament_id)
            .filter(
                ScheduleTournament.schedule_id == league.schedule_id,
                Tournament.start_date <= utc_now.date(),
                Tournament.end_date >= utc_now.date()  # Ensure tournament is ongoing
            )
            .order_by(Tournament.start_date.desc(), Tournament.start_time.desc())
            .first()
        )
        
        if not current_tournament:
            return None
            
        tournament, schedule_tournament = current_tournament
            
        # Get all league members and their picks
        picks_query = (
            db.session.query(
                LeagueMember,
                User,
                Pick,
                Golfer
            )
            .join(League, LeagueMember.league_id == League.id)
            .join(User, LeagueMember.user_id == User.id)
            .outerjoin(
                Pick,
                (Pick.league_member_id == LeagueMember.id) &
                (Pick.tournament_id == tournament.id) &
                (Pick.is_most_recent == True)
            )
            .outerjoin(Golfer, Pick.golfer_id == Golfer.id)
            .filter(League.id == league_id)
            .all()
        )
        
        picks_data = []
        for member, user, pick, golfer in picks_query:
            pick_data = None
            if pick and golfer:
                pick_data = {
                    'golfer_id': golfer.id,
                    'golfer_first_name': golfer.first_name,
                    'golfer_last_name': golfer.last_name,
                    'datagolf_id': golfer.datagolf_id,
                    'status': None,
                    'score_to_par': None,
                    'position': None
                }
                
            picks_data.append({
                'member': {
                    'id': member.id,
                    'name': user.display_name,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'photo_url': user.avatar_url
                },
                'pick': pick_data
            })
            
        return {
            'tournament': {
                'id': tournament.id,
                'name': tournament.tournament_name,
                'start_date': tournament.start_date.strftime('%Y-%m-%d'),
                'is_major': tournament.is_major,
                'week_number': schedule_tournament.week_number
            },
            'picks': picks_data
        }
        
    except Exception as e:
        logger.error(f"Error getting league picks: {e}", exc_info=True)
        return None 