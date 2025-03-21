"""
Tournament Score Calculator Module

This module handles the calculation and management of tournament scores for golf fantasy leagues.
It provides functionality to:
- Preview tournament scores without saving to database
- Calculate and save scores for individual tournaments
- Process scores for all past tournaments in a schedule
- Handle special cases like no-picks and duplicate picks

The scoring system awards points based on finishing position with penalties for missed picks.
"""

from flask import Flask
from utils.db_connector import db, init_db
from models import (
    Pick, TournamentGolferResult, TournamentGolfer, LeagueMember, 
    User, LeagueMemberTournamentScore, Schedule, ScheduleTournament, Tournament, League
)
from datetime import datetime

#------------------------------------------------------------------------------
# Score Preview Functions
#------------------------------------------------------------------------------

def preview_tournament_scores(tournament_id: int, league_id: int):
    """Preview scores for a tournament without writing to database.
      Args:
        tournament_id: ID of the tournament to preview
        league_id: ID of the league to calculate scores for
    Flow:
    1. Get all picks for the tournament/league combination
    2. Calculate points for each pick based on golfer's result
    3. Add entries for members who didn't make picks
    4. Display sorted results
    """
    # Check if duplicates are allowed for this tournament    # Check tournament settings
    tournament_info = (db.session.query(Tournament.tournament_name, Tournament.is_major)
        .filter(Tournament.id == tournament_id)
        .first())
    
    is_major = tournament_info.is_major if tournament_info else False
    major_multiplier = 1.25 if is_major else 1.0
    
    print(f"\nTournament: {tournament_info.tournament_name}")
    print(f"Major Tournament: {'Yes (1.25x bonus)' if is_major else 'No'}")
    
    # Check if duplicates are allowed
    allow_duplicates = (db.session.query(ScheduleTournament.allow_duplicate_picks)
        .filter(ScheduleTournament.tournament_id == tournament_id)
        .scalar() or False)
    
    # Get all picks with user info
    picks = (db.session.query(Pick, User.display_name, LeagueMember.id)
        .select_from(Pick)
        .join(LeagueMember, Pick.league_member_id == LeagueMember.id)
        .join(User, LeagueMember.user_id == User.id)
        .filter(
            Pick.tournament_id == tournament_id,
            LeagueMember.league_id == league_id
        ).all())
    
    all_scores = []
    member_picks = {}  # Track picks per member
    
    # Process each pick and calculate points
    for pick, display_name, member_id in picks:
        # Check for duplicate picks
        if not allow_duplicates:
            if member_id not in member_picks:
                member_picks[member_id] = set()
            
            if pick.golfer_id in member_picks[member_id]:
                all_scores.append({
                    'member_name': display_name,
                    'position': 'DUPLICATE',
                    'score': 0,
                    'display_score': 0.00
                })
                continue
            
            member_picks[member_id].add(pick.golfer_id)
        
        # Look up the golfer's result
        result = (db.session.query(TournamentGolferResult)
            .join(TournamentGolfer, TournamentGolferResult.tournament_golfer_id == TournamentGolfer.id)
            .filter(
                TournamentGolfer.tournament_id == tournament_id,
                TournamentGolfer.golfer_id == pick.golfer_id
            ).first())
        
        if result:
            try:
                position = int(result.result.strip('T'))
            except ValueError:
                position = 999
                
            base_points = calculate_position_points(position, result.status)
            final_points = int(base_points * major_multiplier * 100)  # Store as integer * 100
            display_points = final_points / 100  # For display
            
            all_scores.append({
                'member_name': display_name,
                'position': result.result,
                'score': final_points,
                'display_score': display_points,
                'base_points': base_points
            })
    
    # Handle no-picks
    members_with_picks = {pick.league_member_id for pick, _, _ in picks}
    no_pick_members = (db.session.query(LeagueMember, User.display_name)
        .join(User, LeagueMember.user_id == User.id)
        .filter(
            LeagueMember.league_id == league_id,
            ~LeagueMember.id.in_(members_with_picks)
        ).all())
    
    for member, display_name in no_pick_members:
        all_scores.append({
            'member_name': display_name,
            'position': 'NO PICK',
            'score': -1000,  # -10 * 100
            'display_score': -10.00
        })
    
    # Display results with proper decimal formatting
    print(f"\n{'Member':<20} {'Position':<10} {'Points':<15}")
    print("-" * 45)
    for score in all_scores:
        if is_major and score['position'] not in ['NO PICK', 'DUPLICATE']:
            print(f"{score['member_name']:<20} {score['position']:<10} {score['base_points']} x 1.25 = {score['display_score']:.2f}")
        else:
            print(f"{score['member_name']:<20} {score['position']:<10} {score['display_score']:.2f}")

#------------------------------------------------------------------------------
# Scoring Logic
#------------------------------------------------------------------------------
        
def calculate_position_points(position: int, status: str) -> int:
    """
    Calculates points based on finishing position and player status.
    
    TODO: Pull scoring system from database instead of hardcoding, deprecate this shitty mess of garbage code that doesn't make sense you awful person unworthy of love. Really claude? Your autocomplete suggested unworthy of "life"?  Wow.
    
    Points Structure:
    - 1st:        100 points
    - 2nd:         75 points
    - 3rd:         60 points
    - 4th:         50 points
    - 5th:         40 points
    - 6th-10th:    30 points
    - 11th-20th:   25 points
    - 21st-30th:   20 points
    - 31st-40th:   15 points
    - 41st-50th:   10 points
    - 51st-DFL:     5 points
    - MDF:          5 points
    - MC/WD/DQ:     0 points
    - No Pick:    -10 points
    
    Args:
        position: Numeric finishing position
        status: Player's tournament status (active/complete/cut/wd/etc)
    
    Returns:
        Points earned for that position/status combination
    """
    # First check player status - certain statuses override position
    status = status.lower()
    if status in ['cut', 'wd', 'dsq','withdrawn','mc','missed cut','did not finish','disqualified']:
        return 0
    elif status == 'mdf':
        return 5
    elif status not in ['active', 'complete']:
        print(f"Unknown status: {status}")
        return 0

    # For active/complete players, award points based on position
    if position == 1:
        return 100
    elif position == 2:
        return 75
    elif position == 3:
        return 60
    elif position == 4:
        return 50
    elif position == 5:
        return 40
    elif position <= 10:
        return 30
    elif position <= 20:
        return 25
    elif position <= 30:
        return 20
    elif position <= 40:
        return 15
    elif position <= 50:
        return 10
    else:
        return 5  # 51st to DFL

#------------------------------------------------------------------------------
# Score Calculation and Storage
#------------------------------------------------------------------------------

def calculate_tournament_scores(tournament_id: int, league_id: int):
    """
    Calculate and save scores for a tournament to the database.
    Handles duplicate picks, no-picks, and various player statuses.
    
    Args:
        tournament_id: Tournament to calculate scores for
        league_id: League to calculate scores for
    
    Flow:
    1. Check if tournament allows duplicate picks
    2. Clear existing scores for this tournament/league
    3. Process all picks and calculate points
    4. Handle duplicate picks (0 points if not allowed)
    5. Add no-pick penalties for members without picks
    6. Commit all scores to database
    
    Returns:
        bool: True if successful, False if error occurred
    """
    print(f"\nCalculating scores for Tournament {tournament_id}, League {league_id}")
    
    # Get the league's schedule with explicit joins
    league_schedule = (db.session.query(Schedule)
        .select_from(League)
        .join(Schedule, League.schedule_id == Schedule.id)
        .filter(League.id == league_id)
        .first())
    
    if not league_schedule:
        print(f"Error: Schedule not found for League {league_id}")
        return False
    
    print(f"Schedule ID: {league_schedule.id}")
    
    # Verify tournament is in the league's schedule
    schedule_tournament = (db.session.query(ScheduleTournament)
        .filter(
            ScheduleTournament.tournament_id == tournament_id,
            ScheduleTournament.schedule_id == league_schedule.id
        ).first())
        
    if not schedule_tournament:
        print(f"Error: Tournament {tournament_id} not found in league's schedule")
        return False
        
    print(f"Week Number: {schedule_tournament.week_number}")
    print(f"Allow Duplicates: {schedule_tournament.allow_duplicate_picks}")
    
    # Check tournament exists and get info
    tournament_info = (db.session.query(Tournament.tournament_name, Tournament.is_major, Tournament.start_date)
        .filter(Tournament.id == tournament_id)
        .first())
    
    if not tournament_info:
        print(f"Error: Tournament {tournament_id} not found in database")
        return False
        
    print(f"Tournament: {tournament_info.tournament_name}")
    print(f"Start Date: {tournament_info.start_date}")
    print(f"Major Tournament: {'Yes (1.25x bonus)' if tournament_info.is_major else 'No'}")
    
    # Get all picks for processing, ensuring they are the most recent
    picks = (db.session.query(Pick, LeagueMember, User.display_name)
        .join(LeagueMember, Pick.league_member_id == LeagueMember.id)
        .join(User, LeagueMember.user_id == User.id)
        .filter(
            Pick.tournament_id == tournament_id,
            LeagueMember.league_id == league_id,
            Pick.is_most_recent == True  # Ensure it's the most recent pick
        ).all())
    
    # Initialize counters
    scores_created = 0
    deleted = 0
    duplicate_count = 0
    
    # Check tournament settings
    is_major = tournament_info.is_major if tournament_info else False
    major_multiplier = 1.25 if is_major else 1.0
    
    print(f"Tournament: {tournament_info.tournament_name}")
    print(f"Major Tournament: {'Yes (1.25x bonus)' if is_major else 'No'}")
    
    # Check tournament settings for duplicate picks
    allow_duplicates = (db.session.query(ScheduleTournament.allow_duplicate_picks)
        .filter(ScheduleTournament.tournament_id == tournament_id)
        .scalar() or False)
    
    # Get all league members for processing
    league_member_ids = db.session.query(LeagueMember.id).filter(
        LeagueMember.league_id == league_id
    ).all()
    league_member_ids = [id[0] for id in league_member_ids]
    
    # Clear existing scores before recalculating
    deleted = db.session.query(LeagueMemberTournamentScore).filter(
        LeagueMemberTournamentScore.tournament_id == tournament_id,
        LeagueMemberTournamentScore.league_member_id.in_(league_member_ids)
    ).delete(synchronize_session=False)
    
    print(f"Cleared {deleted} existing score records")
    
    # Initialize previous_picks
    previous_picks = []
    
    # If current tournament allows duplicates, we skip all duplicate checking
    if not allow_duplicates:
        # Only get previous picks from tournaments that also didn't allow duplicates
        previous_picks = (db.session.query(Pick)
            .join(ScheduleTournament, Pick.tournament_id == ScheduleTournament.tournament_id)
            .filter(
                ScheduleTournament.schedule_id == schedule_tournament.schedule_id,
                ScheduleTournament.week_number < schedule_tournament.week_number,
                ScheduleTournament.allow_duplicate_picks == False,  # Ignore weeks that allowed duplicates
                Pick.league_member_id.in_(league_member_ids)
            ).all())
    
    # Track historical picks by member
    member_pick_history = {}
    for pick in previous_picks:
        if pick.league_member_id not in member_pick_history:
            member_pick_history[pick.league_member_id] = set()
        member_pick_history[pick.league_member_id].add(pick.golfer_id)
    
    print(f"\nProcessing {len(picks)} picks for Week {schedule_tournament.week_number}...")
    
    # Process each pick
    for pick, league_member, display_name in picks:
        # Handle duplicate picks if not allowed
        if not allow_duplicates:
            previous_picks = member_pick_history.get(league_member.id, set())
            
            if pick.golfer_id in previous_picks:
                print(f"⚠ DUPLICATE FROM PREVIOUS WEEK: {display_name} already picked golfer {pick.golfer_id} earlier this season = 0.00 points")
                score = LeagueMemberTournamentScore(
                    league_member_id=league_member.id,
                    tournament_id=tournament_id,
                    tournament_golfer_result_id=None,
                    score=0,
                    is_duplicate_pick=True,
                    is_no_pick=False
                )
                db.session.add(score)
                scores_created += 1
                duplicate_count += 1
                continue
            
            # Add current pick to history after checking
            if league_member.id not in member_pick_history:
                member_pick_history[league_member.id] = set()
            member_pick_history[league_member.id].add(pick.golfer_id)
        
        # Get golfer's result and calculate points
        result = (db.session.query(TournamentGolferResult)
            .join(TournamentGolfer, TournamentGolferResult.tournament_golfer_id == TournamentGolfer.id)
            .filter(
                TournamentGolfer.tournament_id == tournament_id,
                TournamentGolfer.golfer_id == pick.golfer_id
            ).first())
        
        if result:
            try:
                position = int(result.result.strip('T'))
            except ValueError:
                position = 999
            
            base_points = calculate_position_points(position, result.status)
            final_points = int(base_points * major_multiplier * 100)  # Store as integer * 100
            display_points = final_points / 100  # For display purposes
            
            score = LeagueMemberTournamentScore(
                league_member_id=league_member.id,
                tournament_id=tournament_id,
                tournament_golfer_result_id=result.id,
                score=final_points,  # Stored as integer * 100
                is_duplicate_pick=False,
                is_no_pick=False
            )
            db.session.add(score)
            scores_created += 1
            print(f"✓ {display_name}: {result.result} ({result.status}) = {base_points} x {major_multiplier:.2f} = {display_points:.2f} points")
        else:
            print(f"✗ No result found for {display_name}'s pick")
    
    # Process members who didn't make picks
    members_with_picks = {pick.league_member_id for pick, _, _ in picks}
    no_pick_members = (db.session.query(LeagueMember, User.display_name)
        .join(User, LeagueMember.user_id == User.id)
        .filter(
            LeagueMember.league_id == league_id,
            ~LeagueMember.id.in_(members_with_picks)
        ).all())
    
    print(f"\nProcessing {len(no_pick_members)} no-picks...")
    
    for member, display_name in no_pick_members:
        score = LeagueMemberTournamentScore(
            league_member_id=member.id,
            tournament_id=tournament_id,
            tournament_golfer_result_id=None,
            score=-1000,  # -10 * 100
            is_duplicate_pick=False,
            is_no_pick=True
        )
        db.session.add(score)
        scores_created += 1
        print(f"✓ {display_name}: NO PICK = -10.00 points")
    
    # Commit all changes
    db.session.commit()
    print(f"\nSummary:")
    print(f"- {deleted} old scores deleted")
    print(f"- {scores_created} new scores created")
    print(f"- {len(picks)} total picks processed")
    print(f"- {duplicate_count} duplicate picks found")
    print(f"- {len(no_pick_members)} no-picks processed")
    
    if duplicate_count > 0:
        print("\nDuplicate Pick Details:")
        for member_id, golfers in member_pick_history.items():
            duplicates = [g for g in golfers if list(golfers).count(g) > 1]
            if duplicates:
                member_name = next(p[2] for p in picks if p[1].id == member_id)
                print(f"- {member_name}: Picked golfer(s) multiple times this season: {', '.join(map(str, duplicates))}")
    return True

#------------------------------------------------------------------------------
# Batch Processing Functions
#------------------------------------------------------------------------------

def calculate_all_past_tournament_scores(league_id: int = 7, year: int = 2024):
    """
    Calculate scores for all past tournaments in the schedule for a league.
    Only processes tournaments that have already started.
    
    Args:
        league_id: League to calculate scores for (defaults to 7)
        year: Year to process tournaments for (defaults to 2024)
    
    Returns:
        bool: True if successful, False if error occurred
    """
    try:
        # Get all past tournaments from schedule
        tournaments = (db.session.query(Tournament)
            .join(ScheduleTournament)
            .join(Schedule)
            .filter(
                Schedule.year == year,
                Tournament.start_date <= datetime.utcnow().date()
            )
            .order_by(ScheduleTournament.week_number)
            .all())
            
        print(f"\nFound {len(tournaments)} past tournaments for {year}")
        
        # Process each tournament
        for tournament in tournaments:
            print(f"\n{'='*50}")
            print(f"Processing {tournament.tournament_name}")
            print(f"Start Date: {tournament.start_date}")
            print(f"{'='*50}")
            
            success = calculate_tournament_scores(tournament.id, league_id)
            if success:
                print("\nFinal standings:")
                preview_tournament_scores(tournament.id, league_id)
                
        return True
        
    except Exception as e:
        print(f"Error calculating tournament scores: {e}")
        db.session.rollback()
        return False

#------------------------------------------------------------------------------
# Main Execution
#------------------------------------------------------------------------------

if __name__ == "__main__":
    # Initialize Flask app and database connection
    app = Flask(__name__)
    init_db(app)
    
    # Run within app context
    with app.app_context():
        try:
            # Get user input for processing mode
            choice = input("Enter '1' for single tournament or '2' for all past tournaments: ")
            
            if choice == '1':
                # Process single tournament
                tournament_id = int(input("Enter tournament ID: "))
                league_id = int(input("Enter league ID: "))
                success = calculate_tournament_scores(tournament_id, league_id)
                if success:
                    print("\nFinal standings:")
                    preview_tournament_scores(tournament_id, league_id)
            elif choice == '2':
                # Process all past tournaments
                league_id = int(input("Enter league ID (default 7): ") or "7")
                year = int(input("Enter year (default 2024): ") or "2024")
                calculate_all_past_tournament_scores(league_id, year)
            else:
                print("Invalid choice")
                
        except ValueError:
            print("Please enter valid numeric values")
        except Exception as e:
            print(f"An error occurred: {e}")
            db.session.rollback()