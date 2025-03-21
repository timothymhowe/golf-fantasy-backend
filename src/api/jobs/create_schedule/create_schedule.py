"""
Schedule Population Script

Creates a schedule by reading tournament IDs, week numbers, and duplicate pick settings
from a CSV file. Links to existing tournament records in the database.
"""

import os
import csv
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
    Creates schedule entries from CSV file.
    Links to existing tournament records.
    
    Args:
        file_path (str): Path to CSV file containing tournament IDs and settings
        schedule_name (str): Name of the schedule
        year (int): Year for the schedule
    """
    schedule_items = read_schedule_csv(file_path)
    if not schedule_items:
        print("Failed to read schedule data from CSV")
        return
    
    print(f"\nProcessing {len(schedule_items)} schedule entries for '{schedule_name}' {year}...")

    try:
        # Create the schedule
        schedule = Schedule(
            schedule_name=schedule_name,
            year=year,
        )
        db.session.add(schedule)
        db.session.flush()  # Get the schedule ID
        
        for item in schedule_items:
            # Verify tournament exists
            tournament = Tournament.query.get(item['tournament_id'])
            if not tournament:
                print(f"Tournament ID {item['tournament_id']} not found in database")
                continue
            
            # Create schedule entry
            schedule_tournament_data = {
                "schedule_id": schedule.id,
                "tournament_id": item['tournament_id'],
                "week_number": item['week_number'],
                "allow_duplicate_picks": item['allow_duplicate_picks']
            }

            new_schedule_tournament = ScheduleTournament(**schedule_tournament_data)
            db.session.add(new_schedule_tournament)

            try:
                db.session.commit()
                print(f"Added Week {item['week_number']}: Tournament {item['tournament_id']} "
                      f"(Duplicates: {'Allowed' if item['allow_duplicate_picks'] else 'Not Allowed'})")
            except Exception as e:
                db.session.rollback()
                print(f"Error adding tournament {item['tournament_id']}: {str(e)}")
                continue

    except Exception as e:
        db.session.rollback()
        print(f"Fatal error in populate_schedule_from_csv: {str(e)}")
        raise

    print(f"\nSchedule '{schedule_name}' for {year} has been created successfully!")

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
        populate_schedule_from_csv(csv_path, schedule_name, year)
