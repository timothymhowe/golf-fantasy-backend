"""
Schedule Population Script

Creates a schedule by reading tournament IDs, week numbers, and duplicate pick settings
from a CSV file. Links to existing tournament records in the database.
"""

import os
import csv
from collections import Counter
from datetime import datetime
from dotenv import load_dotenv
from models import Tournament, Schedule, ScheduleTournament
from utils.db_connector import db, init_db
from flask import Flask

# Load environment variables
load_dotenv()

# Constants
DEFAULT_CSV_PATH = "schedule.csv"  # Will look for this file in the same directory as the script

def read_schedule_csv(file_path):
    """
    Reads schedule information from CSV file.
    Expected CSV format: tournament_id,week_number,allow_duplicate_picks
    
    Args:
        file_path (str): Path to CSV file
        
    Returns:
        list: List of dictionaries containing schedule information
    """
    schedule_items = []
    try:
        with open(file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Convert allow_duplicate_picks to boolean
                allow_dupes = row['allow_duplicate_picks'].lower() in ['true', '1', 't', 'y', 'yes']
                
                schedule_items.append({
                    'tournament_id': int(row['tournament_id']),
                    'week_number': int(row['week_number']),
                    'allow_duplicate_picks': allow_dupes
                })
        return schedule_items
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return None

def populate_schedule_from_csv(file_path, schedule_name, year):
    """
    Creates schedule entries from a CSV file, linking to existing tournaments.

    Every row is checked before anything is written, and the whole schedule is
    committed in one transaction. A schedule missing a week is not a valid
    schedule -- calculate_week_scores resolves ScheduleTournament by
    tournament_id to find the week number and the allow_duplicate_picks flag,
    so a tournament with no row silently cannot be scored for that league.
    That makes a partial write never the right outcome: if any row is bad,
    nothing is written.

    Args:
        file_path (str): Path to CSV file containing tournament IDs and settings
        schedule_name (str): Name of the schedule
        year (int): Year for the schedule

    Returns:
        bool: True if the schedule was committed, False otherwise.
    """
    schedule_items = read_schedule_csv(file_path)
    if not schedule_items:
        print("Failed to read schedule data from CSV")
        return False

    print(f"\nProcessing {len(schedule_items)} schedule entries for '{schedule_name}' {year}...")

    # ---- validate the whole CSV before touching the database -----------

    tournament_ids = [item['tournament_id'] for item in schedule_items]

    duplicates = sorted(tid for tid, n in Counter(tournament_ids).items() if n > 1)
    if duplicates:
        print("\nAborting: the CSV lists the same tournament more than once:")
        for tid in duplicates:
            print(f"  - tournament {tid}")
        print("Nothing was written. Fix the CSV and re-run.")
        return False

    # One query rather than one per row.
    found_ids = {t.id for t in Tournament.query.filter(Tournament.id.in_(tournament_ids)).all()}
    missing = [tid for tid in tournament_ids if tid not in found_ids]
    if missing:
        print(f"\nAborting: {len(missing)} tournament ID(s) are not in the database:")
        for tid in missing:
            print(f"  - tournament {tid}")
        print("Nothing was written. Fix the CSV and re-run.")
        return False

    # ---- one transaction: the whole schedule, or none of it ------------

    try:
        schedule = Schedule(schedule_name=schedule_name, year=year)
        db.session.add(schedule)
        db.session.flush()  # assigns schedule.id for the rows below

        for item in schedule_items:
            db.session.add(ScheduleTournament(
                schedule_id=schedule.id,
                tournament_id=item['tournament_id'],
                week_number=item['week_number'],
                allow_duplicate_picks=item['allow_duplicate_picks'],
            ))

        db.session.commit()
    except Exception as e:
        # Without this rollback the flushed Schedule row stays in a failed
        # transaction and schedule.id becomes a stale pointer to a row that
        # was never committed.
        db.session.rollback()
        print(f"\nError creating schedule: {e}")
        print("Nothing was written.")
        return False

    print(f"\nSchedule '{schedule_name}' for {year} created with {len(schedule_items)} tournaments:")
    for item in schedule_items:
        dupes = 'Allowed' if item['allow_duplicate_picks'] else 'Not Allowed'
        print(f"  Week {item['week_number']}: Tournament {item['tournament_id']} (Duplicates: {dupes})")
    return True

if __name__ == "__main__":
    print("\nSchedule Population Tool")
    print("----------------------")
    
    # Get schedule name
    while True:
        schedule_name = input("\nEnter schedule name: ").strip()
        if schedule_name:
            break
        print("Schedule name cannot be empty.")
    
    # Get year
    current_year = datetime.now().year
    while True:
        try:
            year = input(f"\nEnter year ({current_year}-{current_year + 1}): ").strip()
            year = int(year)
            if current_year <= year <= current_year + 1:
                break
            print(f"Please enter a year between {current_year} and {current_year + 1}")
        except ValueError:
            print("Please enter a valid year")
    
    # Check for CSV file in script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, DEFAULT_CSV_PATH)
    
    if not os.path.exists(csv_path):
        print(f"\nError: Could not find {DEFAULT_CSV_PATH} in the script directory.")
        print(f"Please place your CSV file at: {csv_path}")
        print("\nThe CSV should have the following format:")
        print("tournament_id,week_number,allow_duplicate_picks")
        print("1,1,true")
        print("2,1,false")
        print("3,2,true")
        exit(1)

    # Initialize Flask app and database connection
    app = Flask(__name__)
    init_db(app)
    
    # Execute population within app context
    with app.app_context():
        succeeded = populate_schedule_from_csv(csv_path, schedule_name, year)

    exit(0 if succeeded else 1)
