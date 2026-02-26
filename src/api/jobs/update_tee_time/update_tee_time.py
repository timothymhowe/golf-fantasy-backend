from datetime import datetime, date, time
from flask import Flask
from utils.db_connector import db, init_db
from models import Tournament
import re


def get_upcoming_tournaments():
    """Fetch all tournaments with start_date >= today, ordered by start_date."""
    today = date.today()
    tournaments = Tournament.query.filter(
        Tournament.start_date >= today
    ).order_by(Tournament.start_date.asc()).all()
    return tournaments


def display_tournaments(tournaments):
    """Display upcoming tournaments in a numbered list."""
    print("\nUpcoming Tournaments:")
    print("=" * 70)
    for i, t in enumerate(tournaments, 1):
        default_marker = " [default]" if i == 1 else ""
        current_time = t.start_time.strftime("%H:%M:%S") if t.start_time else "not set"
        print(
            f"  {i}. {t.tournament_name} "
            f"({t.start_date.strftime('%Y-%m-%d')}) "
            f"- current start time: {current_time}"
            f"{default_marker}"
        )
    print("=" * 70)


def prompt_tournament_selection(tournaments):
    """Prompt user to select a tournament, defaulting to the first (soonest)."""
    while True:
        raw = input(f"\nSelect tournament [1-{len(tournaments)}] (default: 1): ").strip()
        if raw == "":
            return tournaments[0]

        try:
            choice = int(raw)
        except ValueError:
            print(f"Invalid input. Enter a number between 1 and {len(tournaments)}.")
            continue

        if 1 <= choice <= len(tournaments):
            return tournaments[choice - 1]
        else:
            print(f"Invalid choice. Enter a number between 1 and {len(tournaments)}.")


def validate_time_input(time_str):
    """Validate a time string in HH:MM:SS 24-hour format.

    Returns a time object on success, None on failure.
    """
    if not re.match(r'^\d{2}:\d{2}:\d{2}$', time_str):
        return None

    try:
        parts = time_str.split(":")
        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        return time(h, m, s)
    except (ValueError, IndexError):
        return None


def prompt_tee_time():
    """Prompt user for a tee time in HH:MM:SS format with validation."""
    while True:
        raw = input("\nEnter tee time in 24hr format (HH:MM:SS): ").strip()
        if raw == "":
            print("Time is required.")
            continue

        parsed = validate_time_input(raw)
        if parsed is None:
            print("Invalid time. Use HH:MM:SS in 24-hour format (e.g. 07:30:00).")
            continue

        return parsed


def update_tee_time():
    """Main workflow: select tournament, enter tee time, update DB."""
    tournaments = get_upcoming_tournaments()

    if not tournaments:
        print("No upcoming tournaments found.")
        return

    display_tournaments(tournaments)
    tournament = prompt_tournament_selection(tournaments)

    print(f"\nSelected: {tournament.tournament_name} ({tournament.start_date})")
    new_time = prompt_tee_time()

    # Confirm before writing
    print(f"\nUpdate {tournament.tournament_name} start_time to {new_time.strftime('%H:%M:%S')}?")
    confirm = input("Confirm (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    try:
        tournament.start_time = new_time
        db.session.commit()
        print(f"Updated start_time to {new_time.strftime('%H:%M:%S')} for {tournament.tournament_name}.")
    except Exception as e:
        db.session.rollback()
        print(f"Error updating tournament: {e}")


if __name__ == "__main__":
    app = Flask(__name__)
    init_db(app)

    with app.app_context():
        update_tee_time()
