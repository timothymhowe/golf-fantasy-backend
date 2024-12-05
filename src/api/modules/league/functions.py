from models import (
    League, LeagueMember, User, LeagueMemberTournamentScore, Tournament, Golfer, TournamentGolfer, TournamentGolferResult, Pick, Schedule, ScheduleTournament
)
from sqlalchemy import func,select
from sqlalchemy.sql import case
from utils.db_connector import db
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)


def calculate_leaderboard(leagueID):
    """
    Calculates the leaderboard for a given league using tournament scores.
    Includes total points and count of missed picks (-5 point scores)
    """
    leaderboard = (db.session.query(
            User.id.label('user_id'),
            User.display_name,
            User.first_name,
            User.last_name,
            User.avatar_url,
            League.id.label('league_id'),
            League.name.label('league_name'),
            LeagueMember.id.label('league_member_id'),
            func.coalesce(func.sum(LeagueMemberTournamentScore.score), 0).label('total_points'),
            func.count(
                case(
                    (LeagueMemberTournamentScore.score < 0, 1),
                    else_=None
                )
            ).label('missed_picks'),
            func.count(
                case(
                    (LeagueMemberTournamentScore.score >= 10000, 1),
                    else_=None
                )
            ).label('wins')
        )
        .join(LeagueMember, User.id == LeagueMember.user_id)
        .join(League, LeagueMember.league_id == League.id)
        .outerjoin(LeagueMemberTournamentScore, LeagueMember.id == LeagueMemberTournamentScore.league_member_id)
        .filter(League.id == leagueID)
        .group_by(
            User.id, 
            User.display_name, 
            League.id, 
            League.name,
            LeagueMember.id
        )
        .order_by(func.coalesce(func.sum(LeagueMemberTournamentScore.score), 0).desc())
        .all()
    )

    return [{
        "user_id": row.user_id,
        "username": row.display_name,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "avatar_url": row.avatar_url,
        "league_id": row.league_id,
        "league_name": row.league_name,
        "league_member_id": row.league_member_id,
        "total_points": int(row.total_points),
        "missed_picks": int(row.missed_picks),
        "wins": int(row.wins)
        
    } for row in leaderboard]
 
# TODO: Add caching, using firebase firestore.
#TODO:  tests tests tests tests tests tests tests 
def get_league_member_pick_history(league_member_id: int) -> dict:
    """Get detailed pick history for a league member
    
    Args:
        league_member_id: ID of the league member
        
    Returns:
        Dictionary containing:
        - member info (name, league)
        - picks (tournament, golfer, result, points)
        - summary stats
    """
    try:
        # Get league member info in a single query
        member_query = (db.session.query(
                LeagueMember,
                User.display_name.label('user_name'),
                League.name.label('league_name'),
                League.schedule_id
            )
            .join(User, LeagueMember.user_id == User.id)
            .join(League, LeagueMember.league_id == League.id)
            .filter(LeagueMember.id == league_member_id)
            .first()
        )
        
        if not member_query:
            return None

        # Get all tournaments and their associated picks in a single query
        picks_query = (db.session.query(
                Tournament.id,
                Tournament.tournament_name,
                Tournament.start_date,
                Tournament.start_time,
                Tournament.time_zone,
                Tournament.is_major,
                ScheduleTournament.week_number,
                Pick,
                Golfer.first_name,
                Golfer.last_name,
                Golfer.id.label('golfer_id'),
                Golfer.datagolf_id,
                TournamentGolferResult.result,
                TournamentGolferResult.status,
                TournamentGolferResult.score_to_par,
                LeagueMemberTournamentScore.score,
                LeagueMemberTournamentScore.is_no_pick,
                LeagueMemberTournamentScore.is_duplicate_pick
            )
            .join(ScheduleTournament, Tournament.id == ScheduleTournament.tournament_id)
            .filter(ScheduleTournament.schedule_id == member_query.schedule_id)
            .outerjoin(Pick, 
                (Pick.tournament_id == Tournament.id) & 
                (Pick.league_member_id == league_member_id) &
                (Pick.is_most_recent == True)
            )
            .outerjoin(Golfer, Pick.golfer_id == Golfer.id)
            .outerjoin(TournamentGolfer,
                (TournamentGolfer.tournament_id == Tournament.id) &
                (TournamentGolfer.golfer_id == Golfer.id))
            .outerjoin(TournamentGolferResult,
                TournamentGolferResult.tournament_golfer_id == TournamentGolfer.id)
            .outerjoin(LeagueMemberTournamentScore,
                (LeagueMemberTournamentScore.tournament_id == Tournament.id) &
                (LeagueMemberTournamentScore.league_member_id == league_member_id)
            )
            .order_by(Tournament.start_date)
            .all()
        )

        picks_data = []
        total_points = 0
        utc_now = datetime.now(pytz.UTC)

        for tournament_data in picks_query:
            # Convert tournament start to UTC for comparison
            tournament_tz = pytz.timezone(tournament_data.time_zone or 'America/New_York')
            tournament_local = tournament_tz.localize(
                datetime.combine(tournament_data.start_date, tournament_data.start_time)
            )
            tournament_utc = tournament_local.astimezone(pytz.UTC)
            
            is_future = utc_now < tournament_utc
            
            if is_future:
                picks_data.append({
                    'tournament': {
                        'name': tournament_data.tournament_name,
                        'date': tournament_data.start_date.strftime('%Y-%m-%d'),
                        'is_major': tournament_data.is_major
                    },
                    'golfer': None,
                    'result': None,
                    'points': 0,
                    'pick_status': {
                        'is_no_pick': False,
                        'is_duplicate_pick': False
                    },
                    'is_future': True
                })
                continue

            points = tournament_data.score / 100 if tournament_data.score is not None else 0
            total_points += points

            picks_data.append({
                'tournament': {
                    'name': tournament_data.tournament_name,
                    'date': tournament_data.start_date.strftime('%Y-%m-%d'),
                    'is_major': tournament_data.is_major
                },
                'golfer': {
                    'name': f"{tournament_data.first_name} {tournament_data.last_name}" if tournament_data.first_name else None,
                    'id': tournament_data.golfer_id,
                    'datagolf_id': tournament_data.datagolf_id,
                },
                'result': {
                    'result': tournament_data.result,
                    'status': tournament_data.status,
                    'score_to_par': tournament_data.score_to_par,
                },
                'points': round(points, 2),
                'pick_status': {
                    'is_no_pick': tournament_data.is_no_pick,
                    'is_duplicate_pick': tournament_data.is_duplicate_pick
                },
                'is_future': False
            })

        return {
            'member': {
                'id': member_query.LeagueMember.id,
                'name': member_query.user_name,
                'league': member_query.league_name
            },
            'picks': picks_data,
            'summary': {
                'total_picks': len([p for p in picks_data if not p.get('is_future', False)]),
                'total_points': round(total_points, 2),
                'majors_played': sum(1 for p in picks_data if p['tournament']['is_major'] and not p.get('is_future', False)),
                'missed_picks': sum(1 for p in picks_data if p.get('pick_status', {}).get('is_no_pick', False)),
                'duplicate_picks': sum(1 for p in picks_data if p.get('pick_status', {}).get('is_duplicate_pick', False)),
                'wins': sum(1 for p in picks_data if not p.get('is_future', False) and p.get('result') is not None and p['result'].get('result') == '1')
            }
        }
            
    except Exception as e:
        logger.error(f"Error getting pick history: {e}", exc_info=True)
        return None


