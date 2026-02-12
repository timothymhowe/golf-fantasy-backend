from models import Tournament
from datetime import datetime
from flask import Flask
from pytz import timezone
from utils.db_connector import db, init_db
import logging

from jobs.update_field.update_field import update_tournament_entries
from jobs.calculate_points.calculate_points import update_tournament_entries_and_results

logger = logging.getLogger(__name__)

app = Flask(__name__)
init_db(app)

def schedule_updates(scheduler):
    """Schedule all database updates"""
    
    # Schedule field updates (keeping existing schedule)
    scheduler.add_job(
        update_tournament_entries,
        "cron",
        day_of_week="wed",
        hour=8,
        timezone=timezone("America/New_York")
    )
    
    # Schedule results and points calculation
    scheduler.add_job(
        update_results_and_points,
        "cron",
        day_of_week="mon",
        hour=8,
        timezone=timezone("America/New_York")
    )

def update_results_and_points():
    """Update tournament results and calculate points"""
    logger.info("Updating tournament results and calculating points.")
    with app.app_context():
        tournament = get_upcoming_tournament()
        if tournament:
            success = update_tournament_entries_and_results(tournament['id'])
            if success:
                logger.info("Tournament results and points updated successfully")
            else:
                logger.error("Failed to update tournament results and points")

def get_upcoming_tournament():
    # Query the database for the tournament that has the closest start date in the future
    upcoming_tournament = (
        Tournament.query.filter(Tournament.start_date > datetime.utcnow())
        .order_by(Tournament.start_date)
        .first()
    )

    if upcoming_tournament is None:
        return None

    # Return the tournament's details
    return {
        "id": upcoming_tournament.id,
        "sportcontent_api_id": upcoming_tournament.sportcontent_api_id,
        "tournament_name": upcoming_tournament.tournament_name,
        "tournament_format": upcoming_tournament.tournament_format,
        "start_date": upcoming_tournament.start_date.strftime('%Y-%m-%d'),
        "start_time": upcoming_tournament.start_time.strftime('%H:%M:%S'),
        "time_zone": upcoming_tournament.time_zone,
        "course_name": upcoming_tournament.course_name,
        "location_raw": upcoming_tournament.location_raw,
    }
    
    
def update_database():
    logger.info("Updating tournament entries.")
    with app.app_context():
        update_tournament_entries()

def force_update():
    """Force immediate update of tournament entries and results"""
    logger.info("Forcing immediate update of tournament entries and results.")
    with app.app_context():
        logger.info("Updating tournament entries...")
        update_tournament_entries()

        logger.info("Updating tournament results and points...")
        tournament = get_upcoming_tournament()
        if tournament:
            success = update_tournament_entries_and_results(tournament['id'])
            if success:
                logger.info("Tournament results and points updated successfully")
            else:
                logger.error("Failed to update tournament results and points")
        else:
            logger.warning("No upcoming tournament found")

if __name__ == "__main__":
    force_update()
