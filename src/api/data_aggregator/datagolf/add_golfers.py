"""
Golfer Addition Script

This script fetches golfer data from the DataGolf API and adds them to the database.
It handles:
- Fetching current OWGR rankings and player details
- Adding new golfers to the database
- Updating existing golfer information
"""

from flask import Flask
from utils.db_connector import db, init_db
from utils.functions.golf_id import generate_golfer_id
from models import Golfer
import requests
import os
from datetime import datetime

DATAGOLF_API_KEY = os.getenv('DATAGOLFAPI_KEY')
DATAGOLF_BASE_URL = "https://api.datagolf.com/api/v1"

def fetch_golfers_from_datagolf():
    """
    Fetches current OWGR rankings and player details from DataGolf API
    
    Returns:
        list: List of golfer dictionaries with relevant information
    """
    endpoint = f"https://feeds.datagolf.com/get-player-list?file_format=json&key={DATAGOLF_API_KEY}"
    
    try:
        response = requests.get(endpoint)
        response.raise_for_status()
        
        golfers_data = response.json()
        return golfers_data
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from DataGolf API: {e}")
        return []

def prompt_user_choice():
    while True:
        choice = input("\nDo you want to:\n1. Update existing golfers only\n2. Update and add new golfers\nEnter 1 or 2: ").strip()
        if choice in ['1', '2']:
            
            if choice == '2':
                choice2 = input("Confirm that you want to add new golfers: (y/n)").strip()
                if choice2 == 'y':
                    return True
                else:
                    print("You have chosen to not add new golfers. Exiting...")
                    exit()
            return choice == '2'  # Returns True if user wants to add new golfers
        print("Invalid choice. Please enter 1 or 2.")

def add_or_update_golfers():
    """
    Adds new golfers to database or updates existing ones based on DataGolf data
    """
    golfers = fetch_golfers_from_datagolf()
    
    if not golfers:
        print("No golfer data received from API")
        return
    
    added_count = 0
    updated_count = 0
    error_count = 0
    skipped_count = 0
    
    print(f"\nProcessing {len(golfers)} golfers...")
    
    # Get user preference
    add_new_golfers = prompt_user_choice()

    # Get existing golfer IDs
    existing_ids = {g.id for g in db.session.query(Golfer.id).all()}

    for golfer_data in golfers:
        try:
            # Extract relevant data
            dg_id = golfer_data['dg_id']
            full_name = golfer_data['player_name']
            country_name = golfer_data['country']
            country_code = golfer_data['country_code']
            is_amateur = bool(golfer_data.get('amateur', 0))
            
            # Skip if missing essential data
            if not all([dg_id, full_name]):
                print(f"Skipping incomplete golfer data: {golfer_data}")
                error_count += 1
                continue
            
            # Split name into last_name and first_name
            try:
                last_name, first_name = map(str.strip, full_name.split(',', 1))
            except ValueError:
                print(f"Warning: Could not split name properly for {full_name}")
                last_name = full_name
                first_name = ""
            
            # Check if golfer already exists
            existing_golfer = db.session.query(Golfer).filter(
                Golfer.datagolf_id == dg_id
            ).first()
            
            if existing_golfer:
                # Update existing golfer
                existing_golfer.first_name = first_name
                existing_golfer.last_name = last_name
                existing_golfer.country_name = country_name
                existing_golfer.country_code = country_code
                existing_golfer.is_amateur = is_amateur
                updated_count += 1
                print(f"✓ Updated: {last_name}, {first_name} ({country_code}){' (Amateur)' if is_amateur else ''}")
            elif add_new_golfers:
                # Generate new golfer ID
                golfer_id = generate_golfer_id(first_name, last_name, existing_ids)
                
                # Create new golfer
                new_golfer = Golfer(
                    id=golfer_id,
                    datagolf_id=dg_id,
                    first_name=first_name,
                    last_name=last_name,
                    country_name=country_name,
                    country_code=country_code,
                    is_amateur=is_amateur
                )
                db.session.add(new_golfer)
                added_count += 1
                print(f"+ Added: {last_name}, {first_name} ({country_code}) [{golfer_id}]{' (Amateur)' if is_amateur else ''}")
            else:
                # Skip adding new golfers if user chose update-only
                skipped_count += 1
                print(f"- Skipped new golfer: {last_name}, {first_name}")
            
        except Exception as e:
            print(f"Error processing golfer {golfer_data.get('player_name', 'Unknown')}: {e}")
            error_count += 1
    
    # Commit changes
    try:
        db.session.commit()
        print(f"\nSummary:")
        print(f"Updated: {updated_count}")
        if add_new_golfers:
            print(f"Added: {added_count}")
        else:
            print(f"Skipped: {skipped_count}")
        print(f"Errors: {error_count}")
        
    except Exception as e:
        print(f"Error committing changes to database: {e}")
        db.session.rollback()

if __name__ == "__main__":
    # Initialize Flask app and database connection
    app = Flask(__name__)
    init_db(app)
    
    # Run within app context
    with app.app_context():
        try:
            add_or_update_golfers()
        except Exception as e:
            print(f"An error occurred: {e}")
            db.session.rollback()
