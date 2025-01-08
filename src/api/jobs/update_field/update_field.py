from datetime import datetime
from os import getenv
from dotenv import load_dotenv
from flask import Flask
from utils.db_connector import db, init_db
from models import TournamentGolfer, Golfer, Schedule, League
from modules.tournament.functions import get_upcoming_tournament
from utils.functions.golf_id import generate_golfer_id
from sqlalchemy import and_, or_
import requests

load_dotenv()
DATAGOLF_KEY = getenv('DATAGOLFAPI_KEY')
DATAGOLF_FIELD_URL = "https://feeds.datagolf.com/field-updates"

def find_similar_golfers(first_name, last_name):
    # Query for golfers with similar first or last names
    similar_golfers = Golfer.query.filter(
        or_(
            Golfer.first_name.ilike(f"%{first_name}%"),
            Golfer.last_name.ilike(f"%{last_name}%")
        )
    ).all()
    return similar_golfers

def prompt_user_for_golfer(similar_golfers, first_name, last_name):
    print(f"No exact match found for {first_name} {last_name}.")
    if similar_golfers:
        print("Similar golfers found:")
        for golfer in similar_golfers:
            print(f"ID: {golfer.id}, Name: {golfer.first_name} {golfer.last_name}")
        
        selected_id = input("Enter the ID of the correct golfer, or type 'new' to create a new entry: ")
        
        if selected_id.lower() == 'new':
            return None  # Indicate to create a new entry
        else:
            return Golfer.query.get(selected_id)
    else:
        print("No similar golfers found.")
        create_new = input("Would you like to create a new entry? (y/n): ")
        return None if create_new.lower() == 'y' else False

def update_tournament_entries(league_id: int):
    """Update tournament entries for upcoming tournament, keeping database clean"""
    upcoming_tournament = get_upcoming_tournament(league_id)['data']
    
    # Debugging: Print the upcoming_tournament to see its structure
    print(f"Upcoming tournament data: {upcoming_tournament}")
    
    if upcoming_tournament is None or "id" not in upcoming_tournament:
        print("No upcoming tournament or missing 'id' key!")
        return None

    try:
        # Make DataGolf API request
        response = requests.get(
            DATAGOLF_FIELD_URL,
            params={
                "tour": "pga",
                "file_format": "json",
                "key": DATAGOLF_KEY
            }
        )
        response.raise_for_status()  # Raise exception for bad status codes
        data = response.json()
        
        if not data.get("field"):
            print("No field data available")
            return None

        year = str(datetime.now().year)
        current_time = datetime.utcnow()

        # First, mark all existing entries as not most recent
        TournamentGolfer.query.filter(
            and_(
                TournamentGolfer.tournament_id == upcoming_tournament["id"],
                TournamentGolfer.year == year,
            )
        ).update({
            TournamentGolfer.is_most_recent: False,
            TournamentGolfer.timestamp_utc: current_time
        })

        # Fetch all existing golfer IDs
        existing_golfer_ids = {golfer.id for golfer in Golfer.query.all()}

        # Process each player in the field
        for player in data["field"]:
            dg_id = player.get("dg_id")
            full_name = player["player_name"]
            last_name, first_name = full_name.split(", ", 1)

            # Try to find golfer by DataGolf ID first, then by name
            existing_golfer = Golfer.query.filter(
                db.or_(
                    Golfer.datagolf_id == dg_id,
                    Golfer.full_name == f"{first_name} {last_name}"
                )
            ).first()
            
            if not existing_golfer:
                similar_golfers = find_similar_golfers(first_name, last_name)
                existing_golfer = prompt_user_for_golfer(similar_golfers, first_name, last_name)

                if existing_golfer is None:
                    # Create a new golfer entry
                    new_golfer = Golfer(
                        id=generate_golfer_id(first_name, last_name, existing_golfer_ids),
                        datagolf_id=dg_id,
                        first_name=first_name,
                        last_name=last_name,
                        full_name=full_name,
                    )
                    db.session.add(new_golfer)
                    db.session.commit()
                    existing_golfer = new_golfer
                    existing_golfer_ids.add(new_golfer.id)  # Add new ID to the set
                elif existing_golfer is False:
                    print("No action taken.")
                    continue

            elif not existing_golfer.datagolf_id and dg_id:
                existing_golfer.datagolf_id = dg_id
                db.session.add(existing_golfer)
                db.session.commit()

            # Create new tournament golfer entry
            tg = TournamentGolfer(
                tournament_id=upcoming_tournament["id"],
                golfer_id=existing_golfer.id,
                year=year,
                is_most_recent=True,
                is_active=True,
                is_alternate=False,  # Could potentially get this from DataGolf
                is_injured=False,    # Could potentially get this from DataGolf
                timestamp_utc=current_time
            )
            db.session.add(tg)

        db.session.commit()
        print("Tournament entries updated successfully")
        return True
        
    except Exception as e:
        print(f"Error updating tournament entries: {repr(e)}")
        db.session.rollback()
        return None

def log_field_changes(tournament_id, before_update, after_update):
    """Log changes in the tournament field before and after the update."""
    before_set = set(entry.golfer_id for entry in before_update)
    after_set = set(entry.golfer_id for entry in after_update)

    new_entrants = after_set - before_set
    withdrawals = before_set - after_set
    total_entrants = len(after_set)

    print("\nField Changes for Tournament ID:", tournament_id)
    print("=" * 40)
    
    if new_entrants:
        print("New Entrants:")
        for golfer_id in new_entrants:
            print(f"Golfer ID: {golfer_id}")
    else:
        print("No new entrants.")

    if withdrawals:
        print("\nWithdrawals:")
        for golfer_id in withdrawals:
            print(f"Golfer ID: {golfer_id}")
    else:
        print("No withdrawals.")

    print(f"\nTotal Number of Entrants in Field: {total_entrants}")
    print("=" * 40)

def update_tournament_entries_with_logging(league_id: int):
    """Update tournament entries and log changes."""
    upcoming_tournament = get_upcoming_tournament(league_id)['data']
    
    if upcoming_tournament is None or "id" not in upcoming_tournament:
        print("No upcoming tournament or missing 'id' key!")
        return None

    tournament_id = upcoming_tournament["id"]

    # Fetch the current field before the update
    before_update = TournamentGolfer.query.filter(
        TournamentGolfer.tournament_id == tournament_id
    ).all()

    # Perform the update
    success = update_tournament_entries(league_id)

    if success:
        # Fetch the field after the update
        after_update = TournamentGolfer.query.filter(
            TournamentGolfer.tournament_id == tournament_id
        ).all()

        # Log the changes
        log_field_changes(tournament_id, before_update, after_update)

    return success

if __name__ == "__main__":
    app = Flask(__name__)
    init_db(app)
    
    with app.app_context():
        try:
            # Get league ID from user
            league_id = int(input("Enter league ID (default 7): ") or "7")
            print(f"Updating field for league {league_id}")
            
            success = update_tournament_entries_with_logging(league_id)
            
            if success:
                print("Field update completed successfully")
            else:
                print("Field update failed")
                
        except ValueError:
            print("Please enter a valid numeric league ID")
        except Exception as e:
            print(f"An error occurred: {e}")
            db.session.rollback()
