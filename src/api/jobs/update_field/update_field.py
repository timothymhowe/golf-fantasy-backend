from datetime import datetime
from os import getenv
from dotenv import load_dotenv
from flask import Flask
from utils.db_connector import db, init_db
from models import TournamentGolfer, Golfer
from modules.tournament.functions import get_upcoming_tournament
from utils.functions.golf_id import generate_golfer_id
from sqlalchemy import and_
import requests

load_dotenv()
DATAGOLF_KEY = getenv('DATAGOLFAPI_KEY')
DATAGOLF_FIELD_URL = "https://feeds.datagolf.com/field-updates"

def update_tournament_entries():
    """Update tournament entries for upcoming tournament, keeping database clean"""
    upcoming_tournament = get_upcoming_tournament()
    if upcoming_tournament is None:
        print("No upcoming tournament!")
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
                    id=generate_golfer_id(first_name, last_name, set()),
                    datagolf_id=dg_id,
                    first_name=first_name,
                    last_name=last_name,
                    full_name=full_name,
                )
                db.session.add(new_golfer)
                db.session.commit()
                existing_golfer = new_golfer
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
        
    except Exception as e:
        print(f"Error updating tournament entries: {repr(e)}")
        db.session.rollback()
        return None

if __name__ == "__main__":
    app = Flask(__name__)
    init_db(app)
    
    with app.app_context():
        update_tournament_entries()
