from models import (
    League, LeagueMember, User, LeagueMemberTournamentScore, Tournament, Golfer, TournamentGolfer, TournamentGolferResult, Pick
)
from sqlalchemy import func,select
from sqlalchemy.sql import case
from utils.db_connector import db
import logging

logger = logging.getLogger(__name__)


def calculate_leaderboard(leagueID):
    """
    Calculates the leaderboard for a given league using tournament scores.
    Includes total points and count of missed picks (-5 point scores)
    """
    leaderboard = (db.session.query(
            User.id.label('user_id'),
            User.display_name,
            League.id.label('league_id'),
            League.name.label('league_name'),
            LeagueMember.id.label('league_member_id'),
            func.coalesce(func.sum(LeagueMemberTournamentScore.score), 0).label('total_points'),
            func.count(
                case(
                    (LeagueMemberTournamentScore.score < 0, 1),
                    else_=None
                )
            ).label('missed_picks')
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
        "league_id": row.league_id,
        "league_name": row.league_name,
        "league_member_id": row.league_member_id,
        "total_points": int(row.total_points),
        "missed_picks": int(row.missed_picks)
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
        logger.info(f"Getting pick history for league member {league_member_id}")
        
        # First verify league member exists
        member_query = (db.session.query(
                LeagueMember,
                User.display_name.label('user_name'),
                League.name.label('league_name')
            )
            .join(User, LeagueMember.user_id == User.id)
            .join(League, LeagueMember.league_id == League.id)
            .filter(LeagueMember.id == league_member_id)
            .first()
        )
        
        if not member_query:
            logger.warning(f"League member {league_member_id} not found")
            return None
            
        # Get all picks with tournament results
        picks_query = (db.session.query(
                Tournament.tournament_name,
                Tournament.start_date,
                Tournament.is_major,
                Golfer.first_name,
                Golfer.last_name,
                Golfer.id.label('golfer_id'),
                Golfer.datagolf_id.label('golfer_datagolf_id'),
                TournamentGolferResult.result,
                TournamentGolferResult.status,
                TournamentGolferResult.score_to_par,
                LeagueMemberTournamentScore.score.label('points'),
                LeagueMemberTournamentScore.is_no_pick,
                LeagueMemberTournamentScore.is_duplicate_pick
            )
            .join(LeagueMemberTournamentScore, 
                LeagueMemberTournamentScore.tournament_id == Tournament.id)
            .join(Pick, 
                (Pick.tournament_id == Tournament.id) & 
                (Pick.league_member_id == league_member_id))
            .join(Golfer, Pick.golfer_id == Golfer.id)
            .outerjoin(TournamentGolfer,
                (TournamentGolfer.tournament_id == Tournament.id) &
                (TournamentGolfer.golfer_id == Golfer.id))
            .outerjoin(TournamentGolferResult,
                TournamentGolferResult.tournament_golfer_id == TournamentGolfer.id)
            .filter(LeagueMemberTournamentScore.league_member_id == league_member_id)
            .order_by(Tournament.start_date.desc())
        )
        
        logger.debug(f"Generated SQL: {picks_query}")
        picks_results = picks_query.all()
        logger.info(f"Found {len(picks_results)} picks")
        
        picks_data = []
        total_points = 0
        
        for row in picks_results:
            # Convert points from cents to dollars
            points = row.points / 100 if row.points is not None else 0
            total_points += points
            
            pick_data = {
                'tournament': {
                    'name': row.tournament_name,
                    'date': row.start_date.strftime('%Y-%m-%d'),
                    'is_major': row.is_major
                },
                'golfer': {
                    'name': f"{row.first_name} {row.last_name}",
                    'id': row.golfer_id,
                    'datagolf_id': row.golfer_datagolf_id,
                },
                'result': {
                    'result': row.result,
                    'status': row.status,
                    'score_to_par': row.score_to_par,
                },
                'points': round(points, 2),
                'pick_status': {
                    'is_no_pick': row.is_no_pick,
                    'is_duplicate_pick': row.is_duplicate_pick
                }
            }
            picks_data.append(pick_data)
            
        return {
            'member': {
                'id': member_query.LeagueMember.id,
                'name': member_query.user_name,
                'league': member_query.league_name
            },
            'picks': picks_data,
            'summary': {
                'total_picks': len(picks_data),
                'total_points': round(total_points, 2),
                'majors_played': sum(1 for p in picks_data if p['tournament']['is_major']),
                'missed_picks': sum(1 for p in picks_data if p['pick_status']['is_no_pick']),
                'duplicate_picks': sum(1 for p in picks_data if p['pick_status']['is_duplicate_pick']),
                'wins':sum(1 for p in picks_data if p['result']['result'] == '1')
            }
        }
            
    except Exception as e:
        logger.error(f"Error getting pick history: {e}", exc_info=True)
        return None


