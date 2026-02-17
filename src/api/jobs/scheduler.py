from flask import Flask
from pytz import timezone
from utils.db_connector import db, init_db
import logging

from jobs.update_field.update_field import update_tournament_entries
from jobs.score_tournaments.score_tournaments import run as score_tournaments

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

    # Schedule results and points calculation for all active leagues
    scheduler.add_job(
        score_all_tournaments,
        "cron",
        day_of_week="mon",
        hour=8,
        timezone=timezone("America/New_York")
    )

def score_all_tournaments():
    """Fetch results and calculate scores for all unscored tournaments."""
    logger.info("Running consolidated tournament scoring.")
    with app.app_context():
        score_tournaments()

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

        logger.info("Running consolidated tournament scoring...")
        score_tournaments()

if __name__ == "__main__":
    force_update()
