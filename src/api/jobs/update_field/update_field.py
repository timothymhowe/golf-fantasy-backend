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
    """Returns a Golfer to use, None to create a new entry, or False to skip."""
    print(f"No exact match found for {first_name} {last_name}.")
    if not similar_golfers:
        print("No similar golfers found.")
        create_new = input("Would you like to create a new entry? (y/n): ")
        return None if create_new.lower() == 'y' else False

    print("Similar golfers found:")
    for golfer in similar_golfers:
        print(f"ID: {golfer.id}, Name: {golfer.first_name} {golfer.last_name}")

    while True:
        selected_id = input("Enter the ID of the correct golfer, 'new' to create a new entry, or 'skip': ")
        if selected_id.lower() == 'new':
            return None
        if selected_id.lower() == 'skip':
            return False
        golfer = db.session.get(Golfer, selected_id)
        if golfer:
            return golfer
        print(f"No golfer found with ID '{selected_id}'. Try again.")

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
            raw_name = player["player_name"]
            try:
                last_name, first_name = raw_name.split(", ", 1)
            except ValueError:
                print(f"⚠ Skipping player with unparseable name: '{raw_name}'")
                continue
            display_name = f"{first_name} {last_name}"

            # Try to find golfer by DataGolf ID first, then by name
            existing_golfer = Golfer.query.filter(
                db.or_(
                    Golfer.datagolf_id == dg_id,
                    Golfer.full_name == display_name
                )
            ).first()

            if not existing_golfer:
                similar_golfers = find_similar_golfers(first_name, last_name)
                existing_golfer = prompt_user_for_golfer(similar_golfers, first_name, last_name)

                if existing_golfer is False:
                    print("No action taken.")
                    continue

                if existing_golfer is None:
                    # Create a new golfer entry
                    new_golfer = Golfer(
                        id=generate_golfer_id(first_name, last_name, existing_golfer_ids),
                        datagolf_id=dg_id,
                        first_name=first_name,
                        last_name=last_name,
                        full_name=display_name,
                    )
                    db.session.add(new_golfer)
                    existing_golfer = new_golfer
                    print(f"+ New golfer: {display_name} ({new_golfer.id}, dg_id={dg_id})")

            # Backfill the DataGolf ID on every path (auto match, manual match,
            # or new) so the same golfer never re-prompts next week
            if dg_id and not existing_golfer.datagolf_id:
                existing_golfer.datagolf_id = dg_id
                print(f"~ Assigned dg_id={dg_id} to {existing_golfer.full_name} ({existing_golfer.id})")
            elif dg_id and existing_golfer.datagolf_id != dg_id:
                print(f"⚠ {display_name}: DataGolf ID mismatch (db={existing_golfer.datagolf_id}, api={dg_id}) — leaving as-is")

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
