from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from models import (
    League, ScoringRuleset, ScoringRule, Tournament, 
    Golfer, TournamentGolfer, TournamentGolferResult
)
from data_aggregator.sportcontentapi.leaderboard import get_tournament_leaderboard_clean
from utils.db_connector import db, init_db
from flask import Flask
import json
import os
import requests

STATUS_MAP_PATH = os.path.join(os.path.dirname(__file__), 'status_map.json')

def load_status_map():
    """Load status mappings from JSON file, creating if doesn't exist"""
    if os.path.exists(STATUS_MAP_PATH):
        with open(STATUS_MAP_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_status_map(mappings):
    """Save status mappings to JSON file"""
    with open(STATUS_MAP_PATH, 'w') as f:
        json.dump(mappings, f, indent=4)

def get_tournament_results(tournament_id: int):
    """
    Gets tournament results from DataGolf API using the historical rounds endpoint
    
    Args:
        tournament_id (int): Database ID of the tournament

    Returns:
        list: Cleaned leaderboard results with just position and score to par
    """
    # Get the tournament to find its DataGolf ID
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        print(f"Tournament {tournament_id} not found in database")
        return None
        
    if not tournament.datagolf_id:
        print(f"Tournament {tournament_id} has no DataGolf ID")
        return None

    api_key = os.getenv('DATAGOLFAPI_KEY')
    if not api_key:
        raise ValueError("DATAGOLFAPI_KEY not found in environment variables")

    # DataGolf API endpoint for historical rounds
    current_year = datetime.now().year
    url = f"https://feeds.datagolf.com/historical-raw-data/rounds?tour=pga&event_id={tournament.datagolf_id}&year={current_year}&file_format=json&key={api_key}"
    
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch DataGolf results: {response.status_code}")
        return None

    data = response.json()
    
    # Process and aggregate round data
    player_results = {}
    for round_data in data.get('scores', []):
        dg_id = round_data.get('dg_id')
        if dg_id not in player_results:
            # Get the finish text and determine status
            fin_text = round_data.get('fin_text', '')
            
            # Determine status and result
            if fin_text.upper() in ['CUT', 'MC']:
                status = 'cut'
                result = 'CUT'
            elif fin_text.upper() in ['WD']:
                status = 'wd'
                result = 'WD'
            elif fin_text.upper() in ['DQ']:
                status = 'dq'
                result = 'DQ'
            else:
                status = 'active'  # Default to active for now
                result = fin_text  # Keep original position text (e.g., "T1", "T2", etc.)
            
            player_results[dg_id] = {
                'player_id': str(dg_id),
                'first_name': '',
                'last_name': '',
                'result': result,
                'status': status,
                'score_to_par': 0 if not tournament.is_team_event else None  # Set to None for team events
            }
            
            # Split player name into first and last
            if ',' in round_data.get('player_name', ''):
                last_name, first_name = round_data['player_name'].split(',', 1)
                player_results[dg_id]['last_name'] = last_name.strip()
                player_results[dg_id]['first_name'] = first_name.strip()
        
        # Only calculate score_to_par for non-team events
        if not tournament.is_team_event:
            for key in round_data:
                if key.startswith('round_'):
                    round_info = round_data[key]
                    score = round_info.get('score', 0)
                    course_par = round_info.get('course_par', 0)
                    player_results[dg_id]['score_to_par'] += (score - course_par)

    return list(player_results.values())

def process_team_event(tournament_id: int, result: dict, year: str):
    """
    Process results for team events where names are stored with slashes
    
    Args:
        tournament_id (int): Tournament ID
        result (dict): Result data from API
        year (str): Tournament year
    
    Returns:
        tuple: (tournament_golfer_id, cleaned_position, status)
    """
    # Extract last names from the slash-formatted name
    first_name = result.get('first_name', '').strip()
    if not first_name.endswith('/'):
        return None
        
    last_name = result.get('last_name', '').strip()
    team_last_names = [
        first_name.rstrip('/'),  # First player's last name
        last_name  # Second player's last name
    ]
    
    print(f"\nProcessing team entry with last names: {team_last_names}")
    
    # Find matching golfers from tournament entries
    matching_entries = (db.session.query(TournamentGolfer, Golfer)
        .join(Golfer)
        .filter(
            TournamentGolfer.tournament_id == tournament_id,
            TournamentGolfer.year == year,
            Golfer.last_name.in_(team_last_names)
        ).all())
    
    if not matching_entries:
        print(f"No matching entries found for team: {team_last_names}")
        return None
        
    # Group entries by last name
    entries_by_lastname = {}
    for tg, golfer in matching_entries:
        if golfer.last_name not in entries_by_lastname:
            entries_by_lastname[golfer.last_name] = []
        entries_by_lastname[golfer.last_name].append((tg, golfer))
    
    selected_tournament_golfers = []
    
    # Process each team member
    for last_name in team_last_names:
        matching = entries_by_lastname.get(last_name, [])
        
        if not matching:
            print(f"No entries found for last name: {last_name}")
            continue
            
        if len(matching) == 1:
            # Single match - use it
            tg, golfer = matching[0]
            selected_tournament_golfers.append(tg)
            print(f"Found unique match for {last_name}: {golfer.first_name} {golfer.last_name}")
        else:
            # Multiple matches - need user disambiguation
            print(f"\nMultiple golfers found with last name '{last_name}':")
            for i, (tg, golfer) in enumerate(matching, 1):
                print(f"{i}. {golfer.first_name} {golfer.last_name}")
            
            while True:
                try:
                    choice = int(input("Enter number of correct golfer: "))
                    if 1 <= choice <= len(matching):
                        selected_tournament_golfers.append(matching[choice-1][0])
                        print(f"Selected: {matching[choice-1][1].first_name} {matching[choice-1][1].last_name}")
                        break
                    print("Invalid selection. Please try again.")
                except ValueError:
                    print("Please enter a number.")
    
    return selected_tournament_golfers

def process_tour_championship_results(results: list) -> list:
    """
    Process TOUR Championship results to use actual scoring instead of 
    starting strokes adjusted scoring.
    
    Args:
        results (list): List of player result dictionaries
        
    Returns:
        list: Modified results with recalculated scores and positions
    """
    try:
        
        # Sort players by actual strokes
        sorted_results = sorted(results, key=lambda x: x.get('strokes', float('inf')))
        print(f"\nSorted {len(sorted_results)} TOUR Championship results by their strokes.")
        # Track position and ties
        current_position = 1
        current_strokes = None
        course_par = 71 * 4  # Par 71 * 4 rounds
        
        # Process each player
        for i, player in enumerate(sorted_results):
            strokes = player.get('strokes')
            if strokes is None:
                continue
                
            # Calculate actual score to par
            total_score = int(strokes)
            score_to_par = total_score - course_par
            player['total_to_par'] = score_to_par
            
            # Handle position and ties
            if current_strokes is None:
                current_strokes = strokes
                player['position'] = str(current_position)
            elif strokes == current_strokes:
                # Tied with previous player(s)
                player['position'] = str(current_position)
            else:
                # New position, accounting for ties
                current_position = i + 1
                current_strokes = strokes
                player['position'] = str(current_position)
        
        print(f"\nProcessed {len(sorted_results)} TOUR Championship results")
        return sorted_results
        
    except Exception as e:
        print(f"Error processing TOUR Championship results: {e}")
        return results

def update_tournament_entries_and_results(tournament_id: int, interactive: bool = False):
    """
    Updates tournament entries and results from the API
    """
    try:
        # Get fresh results from API
        results = get_tournament_results(tournament_id)
        if not results:
            print("No results available")
            return False

        year = str(datetime.now().year)
        
        for result in results:
            player_id = result.get('player_id')
            if not player_id:
                print(f"Missing player_id in result: {result}")
                continue

            # Find golfer entry
            golfer = Golfer.query.filter_by(datagolf_id=player_id).first()
            if not golfer:
                print(f"No golfer found for DataGolf ID: {player_id}")
                continue

            # Get or create tournament_golfer entry
            tournament_golfer = TournamentGolfer.query.filter_by(
                tournament_id=tournament_id,
                golfer_id=golfer.id,
                year=year
            ).first()

            if not tournament_golfer:
                print(f"Creating tournament entry for {golfer.full_name}")
                tournament_golfer = TournamentGolfer(
                    tournament_id=tournament_id,
                    golfer_id=golfer.id,
                    year=year,
                    is_most_recent=True,
                    is_active=True
                )
                db.session.add(tournament_golfer)
                db.session.flush()

            # Get or create result record
            tournament_result = TournamentGolferResult.query.filter_by(
                tournament_golfer_id=tournament_golfer.id
            ).first()

            if tournament_result:
                # Update existing result
                tournament_result.result = result['result']
                tournament_result.status = result['status']
                tournament_result.score_to_par = result['score_to_par']
            else:
                # Create new result if none exists
                tournament_result = TournamentGolferResult(
                    tournament_golfer_id=tournament_golfer.id,
                    result=result['result'],
                    status=result['status'],
                    score_to_par=result['score_to_par']
                )
                db.session.add(tournament_result)

        db.session.commit()
        print("Tournament results updated successfully")
        return True

    except Exception as e:
        print(f"Error updating tournament results: {e}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    app = Flask(__name__)
    init_db(app)
    
    with app.app_context():
        try:
            # Get all tournaments
            tournaments = Tournament.query.all()
            print(f"\nFound {len(tournaments)} tournaments")
            
            # Ask user for update preference
            print("\nWould you like to:")
            print("1. Update a specific tournament")
            print("2. Update all tournaments")
            choice = input("Enter your choice (1 or 2): ").strip()
            
            if choice == "1":
                # Show available tournaments
                print("\nAvailable tournaments:")
                for t in tournaments:
                    print(f"ID: {t.id} - {t.tournament_name}")
                
                # Get tournament ID from user
                tournament_id = input("\nEnter tournament ID to update: ").strip()
                try:
                    tournament_id = int(tournament_id)
                    tournament = Tournament.query.get(tournament_id)
                    if tournament:
                        print(f"\nProcessing {tournament.tournament_name}...")
                        success = update_tournament_entries_and_results(tournament.id, interactive=True)
                        if success:
                            print(f"✓ Results updated successfully for {tournament.tournament_name}")
                        else:
                            print(f"✗ Failed to update results for {tournament.tournament_name}")
                    else:
                        print(f"Tournament with ID {tournament_id} not found")
                except ValueError:
                    print("Invalid tournament ID. Please enter a number.")
                
            elif choice == "2":
                # Original logic for updating all tournaments
                for tournament in tournaments:
                    print(f"\nProcessing {tournament.tournament_name}...")
                    success = update_tournament_entries_and_results(tournament.id, interactive=True)
                    if success:
                        print(f"✓ Results updated successfully for {tournament.tournament_name}")
                    else:
                        print(f"✗ Failed to update results for {tournament.tournament_name}")
                    
                    if input("\nContinue to next tournament? (y/n): ").lower() != 'y':
                        print("Stopping...")
                        break
            
            else:
                print("Invalid choice. Please run the script again and enter 1 or 2.")
                    
        except Exception as e:
            print(f"An error occurred: {e}")
