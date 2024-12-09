from models import League, LeagueMember, Pick, Tournament, Golfer, Schedule, ScheduleTournament, User, TournamentGolferResult, LeagueMemberTournamentScore, TournamentGolfer
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
                        'avatar_url': str
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
            logger.debug(f"No league found with ID: {league_id}")
            return None
            
        # Get current tournament from schedule
        utc_now = datetime.now(pytz.UTC)
        
        # Get most recent tournament
        most_recent_tournament = (
            db.session.query(Tournament, ScheduleTournament)
            .join(ScheduleTournament, Tournament.id == ScheduleTournament.tournament_id)
            .filter(
                ScheduleTournament.schedule_id == league.schedule_id,
                Tournament.start_date <= utc_now.date(),
            )
            .order_by(Tournament.start_date.desc(), Tournament.start_time.desc())
            .first()
        )
        
        if not most_recent_tournament:
            logger.debug("No recent tournament found for the league's schedule.")
            return None
            
        tournament, schedule_tournament = most_recent_tournament
        is_ongoing = tournament.end_date >= utc_now.date()
        logger.debug(f"Most recent tournament: {tournament.tournament_name} (ID: {tournament.id}, Ongoing: {is_ongoing})")
            
        # Get all league members, their picks, and scores
        picks_query = (
            db.session.query(
                LeagueMember,
                User,
                Pick,
                Golfer,
                TournamentGolferResult,
                LeagueMemberTournamentScore
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
            .outerjoin(TournamentGolfer,
                (TournamentGolfer.tournament_id == tournament.id) &
                (TournamentGolfer.golfer_id == Golfer.id))
            .outerjoin(TournamentGolferResult,
                TournamentGolferResult.tournament_golfer_id == TournamentGolfer.id)
            .outerjoin(LeagueMemberTournamentScore,
                (LeagueMemberTournamentScore.tournament_id == tournament.id) &
                (LeagueMemberTournamentScore.league_member_id == LeagueMember.id))
            .filter(League.id == league_id)
            .all()
        )

        # Create a dictionary to store unique member picks
        member_picks = {}
        for member, user, pick, golfer, result, score in picks_query:
            # If we haven't seen this member or this entry has a score and the previous didn't
            if member.id not in member_picks or (
                score and score.score is not None and 
                (not member_picks[member.id][5] or member_picks[member.id][5].score is None)
            ):
                member_picks[member.id] = (member, user, pick, golfer, result, score)

        # Format the deduplicated data
        picks_data = []
        for member_id, (member, user, pick, golfer, result, score) in member_picks.items():
            pick_data = None
            if pick and golfer:
                pick_data = {
                    'golfer_id': golfer.id,
                    'golfer_first_name': golfer.first_name,
                    'golfer_last_name': golfer.last_name,
                    'datagolf_id': golfer.datagolf_id,
                    'status': result.status if result else None,
                    'score_to_par': result.score_to_par if result else None,
                    'position': result.result if result else None,
                    'points': round(score.score / 100, 2) if score and score.score is not None else None,
                    'is_duplicate': score.is_duplicate_pick if score else False
                }
                
            picks_data.append({
                'member': {
                    'id': member.id,
                    'name': user.display_name,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'avatar_url': user.avatar_url
                },
                'pick': pick_data
            })

        response = {
            'tournament': {
                'id': tournament.id,
                'name': tournament.tournament_name,
                'start_date': tournament.start_date.strftime('%Y-%m-%d'),
                'is_major': tournament.is_major,
                'week_number': schedule_tournament.week_number,
                'is_ongoing': is_ongoing
            },
            'picks': picks_data
        }
        
        # Pretty print the response
        print("\nCurrent Week Picks Response:")
        print("=" * 80)
        print("Tournament Info:")
        print(f"  Name: {response['tournament']['name']}")
        print(f"  Date: {response['tournament']['start_date']}")
        print(f"  Major: {response['tournament']['is_major']}")
        print(f"  Week: {response['tournament']['week_number']}")
        print(f"  Ongoing: {response['tournament']['is_ongoing']}")
        print("\nPicks:")
        for pick in response['picks']:
            print("-" * 60)
            print(f"  Member: {pick['member']['name']}")
            if pick['pick']:
                print(f"  Golfer: {pick['pick']['golfer_first_name']} {pick['pick']['golfer_last_name']}")
                print(f"  Status: {pick['pick']['status']}")
                print(f"  Score: {pick['pick']['score_to_par']}")
                print(f"  Position: {pick['pick']['position']}")
                print(f"  Points: {pick['pick']['points']}")
            else:
                print("  No pick made")
        print("=" * 80)
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting league picks: {e}", exc_info=True)
        return None
        return None 