"""
Tournament Schedule Population Script

Fetches and updates the tournament schedule from the DataGolf API.
Handles both creation of new tournaments and updates to existing ones,
with special handling for major championships.
"""

import os
import sys
from pathlib import Path
import requests  # type: ignore
from datetime import datetime, timedelta
from flask import Flask
from dotenv import load_dotenv

# Add the src directory to the Python path
src_path = str(Path(__file__).parent.parent.parent.parent.parent)
if src_path not in sys.path:
    sys.path.append(src_path)

from api.models import Tournament
from utils.db_connector import db, init_db

# Load environment variables
load_dotenv()

# Constants for tournament identification and API configuration
MAJOR_NAMES = ["US OPEN", "MASTERS", "PGA CHAMPIONSHIP", "OPEN CHAMPIONSHIP"]

def parse_location(location_str):
    """
    Parses location string (e.g., "Honolulu, HI") to extract city and state.
    
    Returns:
        tuple: (city, state) or (None, None) if parsing fails
    """
    if not location_str:
        return None, None
    
    parts = location_str.split(',')
    if len(parts) >= 2:
        city = parts[0].strip()
        state = parts[1].strip()
        return city, state
    return location_str, None

def fetch_schedule_from_api(year=None):
    """
    Fetches tournament schedule from DataGolf API for PGA tour.

    Args:
        year (int, optional): Year/season to fetch. Defaults to current year.

    Returns:
        list: List of tournament dictionaries from the schedule
        None: If API request fails

    Raises:
        RequestException: If API request fails (caught and logged)
    """
    api_key = os.getenv('DATAGOLFAPI_KEY')
    if not api_key:
        raise ValueError("DATAGOLFAPI_KEY not found in environment variables")
    
    if year is None:
        year = datetime.now().year
    
    url = f"https://feeds.datagolf.com/get-schedule?tour=pga&season={year}&file_format=json&key={api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        print(f"Fetched schedule for {year}: {len(data.get('schedule', []))} tournaments")
        return data.get('schedule', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching schedule from DataGolf API: {e}")
        return None

def populate_tournaments(year=None):
    """
    Updates the tournament database with PGA Tour schedule.

    Fetches tournament data from DataGolf API and either creates new
    tournament records or updates existing ones. Identifies major championships
    and preserves tournament formats.
    
    Args:
        year (int, optional): Year/season to populate. Defaults to current year.
    """
    schedule_data = fetch_schedule_from_api(year)
    if not schedule_data:
        print("Failed to fetch schedule data")
        return
    
    print(f"Processing {len(schedule_data)} tournaments...")

    # Start a new transaction
    try:
        for item in schedule_data:
            # Skip tournaments with TBD event_id
            if item.get("event_id") == "TBD" or not item.get("event_id"):
                print(f"Skipping tournament '{item.get('event_name', 'Unknown')}' - event_id is TBD or missing")
                continue
            
            clean_name = item["event_name"].replace(".", "").upper()
            
            is_a_major = any(major_name in clean_name for major_name in MAJOR_NAMES)
            # Additional validation for Masters
            if "MASTERS" in clean_name and "AUGUSTA" not in item.get("course", "").upper():
                is_a_major = False

            # Parse start date
            start_date = datetime.strptime(item["start_date"], "%Y-%m-%d").date()
            # Tournaments typically run 4 days (Thursday-Sunday)
            end_date = start_date + timedelta(days=3)
            
            # Parse location
            city, state = parse_location(item.get("location", ""))
            
            tournament_year = item.get("season", start_date.year)
            event_id = int(item["event_id"])
            
            tournament_data = {
                "tournament_name": item["event_name"],
                "tournament_format": "stroke",  # Default format, can be updated manually if needed
                "year": tournament_year,
                "start_date": start_date,
                "end_date": end_date,
                "time_zone": "America/New_York",  # Default, may need manual adjustment
                "course_name": item.get("course", ""),
                "location_raw": item.get("location", ""),
                "city": city,
                "state": state,
                "latitude": str(item.get("latitude", "")) if item.get("latitude") else None,
                "longitude": str(item.get("longitude", "")) if item.get("longitude") else None,
                "datagolf_id": event_id,
                "is_major": is_a_major,
            }

            # Try to find existing tournament by datagolf_id AND year (datagolf_ids are reused across years)
            existing = Tournament.query.filter_by(
                datagolf_id=event_id,
                year=tournament_year
            ).first()

            if existing:
                print(f"Found existing tournament: {tournament_data['tournament_name']}")
                # Update fields individually
                for key, value in tournament_data.items():
                    setattr(existing, key, value)
            else:
                print(f"Creating new tournament: {tournament_data['tournament_name']}")
                new_tournament = Tournament(**tournament_data)
                db.session.add(new_tournament)

            # Commit after each tournament to avoid batch issues
            try:
                db.session.commit()
                print(f"Successfully {'updated' if existing else 'added'}: {tournament_data['tournament_name']}")
            except Exception as e:
                db.session.rollback()
                print(f"Error processing tournament {tournament_data['tournament_name']}: {str(e)}")
                continue

    except Exception as e:
        db.session.rollback()
        print(f"Fatal error in populate_tournaments: {str(e)}")
        raise

    print("Tournament population completed")

if __name__ == "__main__":
    # Initialize Flask app and database connection
    app = Flask(__name__)
    init_db(app)
    
    # Optional: Allow year to be passed as command line argument
    import sys
    year = None
    if len(sys.argv) > 1:
        try:
            year = int(sys.argv[1])
        except ValueError:
            print(f"Invalid year argument: {sys.argv[1]}. Using current year.")
    
    # Execute population within app context
    with app.app_context():
        populate_tournaments(year=year)
    print("Done populating tournaments.")
