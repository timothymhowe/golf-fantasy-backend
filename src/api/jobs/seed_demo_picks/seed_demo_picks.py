"""
Seed demo league picks for the upcoming tournament.

Grabs the active field for the upcoming tournament and randomly assigns
one golfer per bot league member. Skips members who already have a pick
for the tournament. Designed to run after update_field in the weekly pipeline.

Usage:
    cd ~/repos/golf-fantasy-backend
    source venv/bin/activate
    PYTHONPATH=src/api python src/api/jobs/seed_demo_picks/seed_demo_picks.py
"""

import random
from datetime import datetime
from flask import Flask
from utils.db_connector import db, init_db
from models import (
    LeagueMember, Pick, TournamentGolfer, Golfer, User
)
from modules.tournament.functions import get_upcoming_tournament


# The demo league ID — will be printed by setup_demo_league.py after first run
DEMO_LEAGUE_ID = 11

# Firebase UID of the demo visitor user — their picks are controlled by the visitor
DEMO_VISITOR_FIREBASE_ID = 'unF8WmS8KUgHwNHvpOAfKrIxQuE2'


def get_demo_bot_members(league_id, visitor_firebase_id):
    """Get all league members except the visitor-controlled one."""
    bot_members = (
        db.session.query(LeagueMember)
        .join(User, LeagueMember.user_id == User.id)
        .filter(
            LeagueMember.league_id == league_id,
            User.firebase_id != visitor_firebase_id
        )
        .all()
    )
    return bot_members


def get_active_field(tournament_id):
    """Get all active golfers in the tournament field."""
    field = (
        db.session.query(TournamentGolfer, Golfer)
        .join(Golfer, TournamentGolfer.golfer_id == Golfer.id)
        .filter(
            TournamentGolfer.tournament_id == tournament_id,
            TournamentGolfer.is_most_recent == True,
            TournamentGolfer.is_active == True,
        )
        .all()
    )
    return field


def get_existing_picks(league_id, tournament_id):
    """Get set of league_member_ids that already have picks for this tournament."""
    existing = (
        db.session.query(Pick.league_member_id)
        .join(LeagueMember, Pick.league_member_id == LeagueMember.id)
        .filter(
            LeagueMember.league_id == league_id,
            Pick.tournament_id == tournament_id,
            Pick.is_most_recent == True,
        )
        .all()
    )
    return {row.league_member_id for row in existing}


def seed_picks(league_id, visitor_firebase_id, dry_run=False):
    """Seed random picks for bot members in the demo league.

    Args:
        league_id: the demo league ID
        visitor_firebase_id: firebase UID of the visitor user (skipped)
        dry_run: if True, print what would happen without committing
    """
    # Get upcoming tournament for the league
    result = get_upcoming_tournament(league_id)
    if result.get('status') != 'success':
        print(f"no upcoming tournament found: {result.get('message', 'unknown')}")
        return False

    tournament_data = result['data']
    tournament_id = tournament_data['id']
    tournament_name = tournament_data['tournament_name']
    year = int(tournament_data['start_date'][:4])

    print(f"tournament: {tournament_name} (id={tournament_id})")

    # Get the active field
    field = get_active_field(tournament_id)
    if not field:
        print("no active golfers in the field, run update_field first")
        return False

    golfer_ids = [tg.golfer_id for tg, golfer in field]
    golfer_names = {tg.golfer_id: golfer.full_name for tg, golfer in field}
    print(f"field size: {len(golfer_ids)} golfers")

    # Get bot members (exclude visitor)
    bot_members = get_demo_bot_members(league_id, visitor_firebase_id)
    if not bot_members:
        print("no bot members found in the demo league")
        return False

    print(f"bot members: {len(bot_members)}")

    # Check who already has picks
    existing = get_existing_picks(league_id, tournament_id)

    # Assign random picks
    picks_created = 0
    for member in bot_members:
        if member.id in existing:
            print(f"  {member.id}: already has a pick, skipping")
            continue

        golfer_id = random.choice(golfer_ids)

        if dry_run:
            print(f"  {member.id}: would pick {golfer_names[golfer_id]} ({golfer_id})")
            continue

        pick = Pick(
            league_member_id=member.id,
            tournament_id=tournament_id,
            golfer_id=golfer_id,
            year=year,
            is_most_recent=True,
        )
        db.session.add(pick)
        picks_created += 1
        print(f"  {member.id}: picked {golfer_names[golfer_id]} ({golfer_id})")

    if not dry_run and picks_created > 0:
        db.session.commit()
        print(f"\n{picks_created} picks created")
    elif dry_run:
        print(f"\ndry run - {len(bot_members) - len(existing)} picks would be created")
    else:
        print("\nno new picks needed")

    return True


if __name__ == "__main__":
    if DEMO_LEAGUE_ID is None or DEMO_VISITOR_FIREBASE_ID is None:
        print("ERROR: set DEMO_LEAGUE_ID and DEMO_VISITOR_FIREBASE_ID at the top of this file")
        print("create the demo league and users first, then update the constants")
        exit(1)

    app = Flask(__name__)
    init_db(app)

    with app.app_context():
        try:
            mode = input("dry run? (y/n, default y): ").strip().lower() or 'y'
            dry_run = mode == 'y'

            success = seed_picks(DEMO_LEAGUE_ID, DEMO_VISITOR_FIREBASE_ID, dry_run=dry_run)

            if not success:
                print("seed failed")
        except Exception as e:
            print(f"error: {e}")
            db.session.rollback()
