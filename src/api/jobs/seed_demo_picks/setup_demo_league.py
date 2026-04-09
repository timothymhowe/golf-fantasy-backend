"""
One-time setup script for the demo league.

Creates bot users, demo league, league members, and backfills picks
for all past tournaments on the schedule. After running this, run
the scoring pipeline (calculate_points + calculate_week_scores) to
populate the leaderboard.

Usage:
    cd ~/repos/golf-fantasy-backend
    source venv/bin/activate
    PYTHONPATH=src/api python src/api/jobs/seed_demo_picks/setup_demo_league.py
"""

import random
from datetime import datetime
from flask import Flask
from utils.db_connector import db, init_db
from models import (
    User, League, LeagueMember, Role, Pick,
    Tournament, TournamentGolfer, TournamentGolferResult,
    Schedule, ScheduleTournament,
)
import pytz

SCHEDULE_ID = 7
DEMO_VISITOR_FIREBASE_ID = 'unF8WmS8KUgHwNHvpOAfKrIxQuE2'

BOT_USERS = [
    {'first_name': 'Birdie',    'last_name': 'Sanders',    'display_name': 'Birdie Sanders',    'email': 'birdie.sanders@demo.ailette.io'},
    {'first_name': 'Tiger',     'last_name': 'Woulds',     'display_name': 'Tiger Woulds',      'email': 'tiger.woulds@demo.ailette.io'},
    {'first_name': 'Chip',      'last_name': 'Kelly',      'display_name': 'Chip Kelly',        'email': 'chip.kelly@demo.ailette.io'},
    {'first_name': 'Bunker',    'last_name': 'Bob',        'display_name': 'Bunker Bob',        'email': 'bunker.bob@demo.ailette.io'},
    {'first_name': 'Humphrey',  'last_name': 'Bogey',      'display_name': 'Humphrey Bogey',    'email': 'humphrey.bogey@demo.ailette.io',
     'avatar_url': None},  # TODO: set Humphrey's cat pic URL
    {'first_name': 'Wedge',     'last_name': 'Wellington',  'display_name': 'Wedge Wellington',  'email': 'wedge.wellington@demo.ailette.io'},
]

# --- backfill config ---
NUM_WINS = 4       # total wins spread across all bots and past tournaments
NUM_NO_PICKS = 6   # total no-picks spread across all bots and past tournaments


def create_bot_users():
    """Create the bot users with fake firebase IDs."""
    users = []
    for i, bot in enumerate(BOT_USERS):
        firebase_id = f'demo-bot-{i+1}-{bot["first_name"].lower()}'

        existing = User.query.filter_by(firebase_id=firebase_id).first()
        if existing:
            print(f"  bot already exists: {bot['display_name']} (id={existing.id})")
            users.append(existing)
            continue

        user = User(
            firebase_id=firebase_id,
            display_name=bot['display_name'],
            first_name=bot['first_name'],
            last_name=bot['last_name'],
            email=bot['email'],
            avatar_url=bot.get('avatar_url'),
        )
        db.session.add(user)
        db.session.flush()
        print(f"  created bot: {bot['display_name']} (id={user.id})")
        users.append(user)

    db.session.commit()
    return users


def create_demo_league(schedule_id):
    """Create the demo league linked to the given schedule."""
    existing = League.query.filter_by(name='Demo League').first()
    if existing:
        print(f"  demo league already exists (id={existing.id})")
        return existing

    league = League(
        name='Demo League',
        scoring_format='STANDARD',
        is_active=True,
        schedule_id=schedule_id,
    )
    db.session.add(league)
    db.session.commit()
    print(f"  created demo league (id={league.id})")
    return league


def create_league_members(league, bot_users):
    """Add bot users to the demo league as members."""
    member_role = Role.query.filter_by(name='MEMBER').first()
    if not member_role:
        member_role = Role.query.get(3)  # fallback to role id 3
    if not member_role:
        member_role = Role(id=3, name='Member')
        db.session.add(member_role)
        db.session.flush()

    members = []
    for user in bot_users:
        existing = LeagueMember.query.filter_by(
            league_id=league.id, user_id=user.id
        ).first()
        if existing:
            print(f"  already a member: {user.display_name} (member_id={existing.id})")
            members.append(existing)
            continue

        member = LeagueMember(
            league_id=league.id,
            user_id=user.id,
            role_id=member_role.id,
        )
        db.session.add(member)
        db.session.flush()
        print(f"  added member: {user.display_name} (member_id={member.id})")
        members.append(member)

    db.session.commit()
    return members


def add_visitor_to_league(league):
    """Add the demo visitor user to the league if they exist."""
    visitor = User.query.filter_by(firebase_id=DEMO_VISITOR_FIREBASE_ID).first()
    if not visitor:
        print(f"  visitor user not found (firebase_id={DEMO_VISITOR_FIREBASE_ID})")
        print("  create the demo account and run this again, or add them manually")
        return None

    existing = LeagueMember.query.filter_by(
        league_id=league.id, user_id=visitor.id
    ).first()
    if existing:
        print(f"  visitor already in league: {visitor.display_name} (member_id={existing.id})")
        return existing

    member_role = Role.query.filter_by(name='MEMBER').first() or Role.query.get(3)
    member = LeagueMember(
        league_id=league.id,
        user_id=visitor.id,
        role_id=member_role.id,
    )
    db.session.add(member)
    db.session.commit()
    print(f"  added visitor: {visitor.display_name} (member_id={member.id})")
    return member


def get_past_tournaments(schedule_id):
    """Get all tournaments on the schedule that have already started."""
    utc_now = datetime.now(pytz.UTC)

    tournaments = (
        db.session.query(Tournament, ScheduleTournament.week_number)
        .join(ScheduleTournament, Tournament.id == ScheduleTournament.tournament_id)
        .filter(
            ScheduleTournament.schedule_id == schedule_id,
            Tournament.start_date < utc_now.date(),
        )
        .order_by(Tournament.start_date)
        .all()
    )
    return tournaments


def get_tournament_winner(tournament_id):
    """Get the golfer_id of the tournament winner, if results exist."""
    winner = (
        db.session.query(TournamentGolferResult, TournamentGolfer)
        .join(TournamentGolfer, TournamentGolferResult.tournament_golfer_id == TournamentGolfer.id)
        .filter(
            TournamentGolfer.tournament_id == tournament_id,
            TournamentGolferResult.result == '1',
        )
        .first()
    )
    if winner:
        return winner.TournamentGolfer.golfer_id
    return None


def get_tournament_field_golfer_ids(tournament_id):
    """Get all active golfer IDs in a tournament's field."""
    field = (
        TournamentGolfer.query
        .filter(
            TournamentGolfer.tournament_id == tournament_id,
            TournamentGolfer.is_most_recent == True,
        )
        .all()
    )
    return [tg.golfer_id for tg in field]


def backfill_picks(members, schedule_id):
    """Backfill random picks for all past tournaments.

    Distributes NUM_WINS wins and NUM_NO_PICKS no-picks randomly across
    all (member, tournament) slots. Everything else gets a random pick.
    """
    past_tournaments = get_past_tournaments(schedule_id)
    if not past_tournaments:
        print("  no past tournaments found, nothing to backfill")
        return

    print(f"  found {len(past_tournaments)} past tournaments")

    # Build all possible (member, tournament) slots
    slots = []
    for tournament, week_number in past_tournaments:
        for member in members:
            slots.append((member, tournament, week_number))

    total_slots = len(slots)
    print(f"  total slots: {total_slots} ({len(members)} bots x {len(past_tournaments)} tournaments)")

    if total_slots < NUM_WINS + NUM_NO_PICKS:
        print(f"  warning: not enough slots for {NUM_WINS} wins + {NUM_NO_PICKS} no-picks")

    # Shuffle and assign special slots
    random.shuffle(slots)

    win_slots = {}
    no_pick_slots = set()

    # Assign wins - only to tournaments that have a winner
    # Cache winners so we don't query the same tournament twice
    winner_cache = {}
    win_candidates = []
    for i, (member, tournament, week) in enumerate(slots):
        if tournament.id not in winner_cache:
            winner_cache[tournament.id] = get_tournament_winner(tournament.id)
        winner_id = winner_cache[tournament.id]
        if winner_id:
            win_candidates.append((i, winner_id))

    random.shuffle(win_candidates)
    for idx, winner_id in win_candidates[:NUM_WINS]:
        win_slots[idx] = winner_id

    # Assign no-picks from remaining slots
    remaining_indices = [i for i in range(total_slots) if i not in win_slots]
    random.shuffle(remaining_indices)
    for idx in remaining_indices[:NUM_NO_PICKS]:
        no_pick_slots.add(idx)

    # Create picks
    picks_created = 0
    wins_assigned = 0
    no_picks_assigned = 0

    for i, (member, tournament, week_number) in enumerate(slots):
        # Skip no-pick slots
        if i in no_pick_slots:
            no_picks_assigned += 1
            continue

        # Get the field
        field_ids = get_tournament_field_golfer_ids(tournament.id)
        if not field_ids:
            continue

        # Determine golfer
        if i in win_slots:
            golfer_id = win_slots[i]
            wins_assigned += 1
        else:
            golfer_id = random.choice(field_ids)

        year = tournament.start_date.year

        pick = Pick(
            league_member_id=member.id,
            tournament_id=tournament.id,
            golfer_id=golfer_id,
            year=year,
            is_most_recent=True,
        )
        db.session.add(pick)
        picks_created += 1

    db.session.commit()
    print(f"  backfill complete: {picks_created} picks, {wins_assigned} wins, {no_picks_assigned} no-picks")


def run_setup():
    print("=== demo league setup ===\n")

    print("1. creating bot users...")
    bot_users = create_bot_users()

    print("\n2. creating demo league...")
    league = create_demo_league(SCHEDULE_ID)

    print("\n3. adding bots to league...")
    members = create_league_members(league, bot_users)

    print("\n4. adding visitor to league...")
    add_visitor_to_league(league)

    print("\n5. backfilling picks for past tournaments...")
    backfill_picks(members, SCHEDULE_ID)

    print("\n=== setup complete ===")
    print(f"demo league id: {league.id}")
    print(f"schedule id: {SCHEDULE_ID}")
    print(f"\nnext steps:")
    print(f"  1. update DEMO_LEAGUE_ID in seed_demo_picks.py to {league.id}")
    print(f"  2. run scoring pipeline: calculate_points + calculate_week_scores")
    print(f"  3. set humphrey bogey's avatar_url to the cat pic")


if __name__ == "__main__":
    app = Flask(__name__)
    init_db(app)

    with app.app_context():
        try:
            run_setup()
        except Exception as e:
            print(f"\nerror: {e}")
            db.session.rollback()
            raise
