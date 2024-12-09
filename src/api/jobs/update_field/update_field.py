from datetime import datetime
from os import getenv
from dotenv import load_dotenv
from flask import Flask
from utils.db_connector import db, init_db
from models import TournamentGolfer, Golfer, Schedule, League
from modules.tournament.functions import get_upcoming_tournament
from utils.functions.golf_id import generate_golfer_id
from sqlalchemy import and_
import requests

load_dotenv()
DATAGOLF_KEY = getenv('DATAGOLFAPI_KEY')
DATAGOLF_FIELD_URL = "https://feeds.datagolf.com/field-updates"

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
                print(f"Adding golfer {full_name} to database")
                
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

if __name__ == "__main__":
    app = Flask(__name__)
    init_db(app)
    
    with app.app_context():
        try:
            # Get league ID from user
            league_id = int(input("Enter league ID (default 7): ") or "7")
            print(f"Updating field for league {league_id}")
            
           
                
            success = update_tournament_entries(league_id)
            
            if success:
                print("Field update completed successfully")
            else:
                print("Field update failed")
                
        except ValueError:
            print("Please enter a valid numeric league ID")
        except Exception as e:
            print(f"An error occurred: {e}")
            db.session.rollback()
