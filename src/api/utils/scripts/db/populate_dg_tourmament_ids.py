# utils/scripts/populate_datagolf_ids.py

import os
from typing import Dict, Any, List, Tuple
import requests  # type: ignore
from datetime import datetime
import sys
from pathlib import Path
from difflib import SequenceMatcher
from tabulate import tabulate
import argparse
from flask import Flask
from utils.db_connector import init_db

# Add the src directory to the Python path
src_path = str(Path(__file__).parent.parent.parent.parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from api.models import Tournament
from utils.db_connector import db
from dotenv import load_dotenv

load_dotenv()

def get_datagolf_schedule() -> List[Dict[str, Any]]:
    """Fetches the PGA Tour schedule from DataGolf API"""
    api_key = os.getenv('DATAGOLFAPI_KEY')
    if not api_key:
        raise ValueError("DATAGOLFAPI_KEY not found in environment variables")
        
    url = f"https://feeds.datagolf.com/get-schedule?tour=pga&file_format=json&key={api_key}"
    
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch DataGolf schedule: {response.status_code}")
    
    data = response.json()
    return data['schedule']  # Return just the schedule list

def get_similarity_score(name1: str, name2: str) -> float:
    """Returns a similarity score between 0 and 1 for two tournament names"""
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()

def find_potential_matches(
    db_tournament: Tournament, 
    dg_tournaments: List[Dict[str, Any]]
) -> List[Tuple[Dict[str, Any], float]]:
    """Finds potential matches for a tournament in the DataGolf schedule"""
    matches = []
    
    for dg_tournament in dg_tournaments:
        # Check if dates are close (within 2 days)
        dg_start = datetime.strptime(dg_tournament['start_date'], '%Y-%m-%d').date()
        if abs((dg_start - db_tournament.start_date).days) > 2:
            continue
            
        # Calculate name similarity
        similarity = get_similarity_score(db_tournament.tournament_name, dg_tournament['event_name'])
        if similarity > 0.6:  # Only include reasonably similar names
            matches.append((dg_tournament, similarity))
    
    # Sort by similarity score
    return sorted(matches, key=lambda x: x[1], reverse=True)

def display_match_options(db_tournament: Tournament, potential_matches: List[Tuple[Dict[str, Any], float]]) -> None:
    """Displays potential matches in a table format"""
    if not potential_matches:
        print(f"\nNo potential matches found for: {db_tournament.tournament_name}")
        return
        
    print(f"\nPotential matches for: {db_tournament.tournament_name}")
    print(f"DB Start Date: {db_tournament.start_date}")
    
    table_data = []
    for i, (dg_tournament, similarity) in enumerate(potential_matches, 1):
        table_data.append([
            i,
            dg_tournament['event_name'],
            dg_tournament['start_date'],
            dg_tournament['location'],
            f"{similarity:.2%}",
            dg_tournament['event_id']
        ])
    
    print(tabulate(
        table_data,
        headers=['#', 'DataGolf Name', 'Start Date', 'Location', 'Similarity', 'DataGolf ID'],
        tablefmt='grid'
    ))

def populate_datagolf_ids(dry_run: bool = False):
    """
    Interactive script to populate datagolf_ids and location data for tournaments.
    """
    try:
        # Get current year tournaments from our DB
        current_year = datetime.now().year
        db_tournaments = Tournament.query.filter_by(year=current_year).all()
        
        # Get DataGolf schedule
        dg_schedule = get_datagolf_schedule()
        
        if dry_run:
            print("\n=== DRY RUN MODE - No changes will be made to the database ===")
        
        # Process each tournament
        for db_tournament in db_tournaments:
            if db_tournament.datagolf_id is not None:
                print(f"\nSkipping {db_tournament.tournament_name} - already has datagolf_id: {db_tournament.datagolf_id}")
                continue
                
            potential_matches = find_potential_matches(db_tournament, dg_schedule)
            display_match_options(db_tournament, potential_matches)
            
            if potential_matches:
                while True:
                    choice = input("\nEnter number to select match, 's' to skip, or 'q' to quit: ").strip().lower()
                    
                    if choice == 'q':
                        print("Quitting...")
                        return
                    elif choice == 's':
                        print("Skipping...")
                        break
                    elif choice.isdigit() and 1 <= int(choice) <= len(potential_matches):
                        selected_match = potential_matches[int(choice) - 1][0]
                        if dry_run:
                            print(f"\n[DRY RUN] Would update {db_tournament.tournament_name} with:")
                            print(f"  datagolf_id: {selected_match['event_id']}")
                            print(f"  location_raw: {selected_match['location']}")
                            print(f"  latitude: {selected_match['latitude']}")
                            print(f"  longitude: {selected_match['longitude']}")
                            break
                        else:
                            print(f"\nWill update {db_tournament.tournament_name} with:")
                            print(f"  datagolf_id: {selected_match['event_id']}")
                            print(f"  location_raw: {selected_match['location']}")
                            print(f"  latitude: {selected_match['latitude']}")
                            print(f"  longitude: {selected_match['longitude']}")
                            
                            confirm = input("Confirm update? (y/n): ").strip().lower()
                            
                            if confirm == 'y':
                                db_tournament.datagolf_id = selected_match['event_id']
                                db_tournament.location_raw = selected_match['location']
                                db_tournament.latitude = str(selected_match['latitude'])  # Convert to string as per model
                                db_tournament.longitude = str(selected_match['longitude'])  # Convert to string as per model
                                db.session.commit()
                                print("Updated successfully!")
                                break
                            else:
                                print("Update cancelled.")
                    else:
                        print("Invalid choice. Please try again.")
        
        if dry_run:
            print("\n=== DRY RUN COMPLETE - No changes were made to the database ===")
        else:
            print("\nFinished processing tournaments!")
        
    except Exception as e:
        if not dry_run:
            db.session.rollback()
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    app = Flask(__name__)
    init_db(app)
    with app.app_context():
        parser = argparse.ArgumentParser(description='Populate DataGolf IDs for tournaments')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
        args = parser.parse_args()
        
        populate_datagolf_ids(dry_run=args.dry_run)