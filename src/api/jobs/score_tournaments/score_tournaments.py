"""
Consolidated Tournament Scoring Script

Automatically finds and scores all unscored, completed tournaments
across active leagues. Can also be run with --tournament-id and/or
--league-id for targeted re-runs.

Usage:
    # Auto mode: score all unscored tournaments for all active leagues
    PYTHONPATH=src/api python src/api/jobs/score_tournaments/score_tournaments.py

    # Override: specific tournament for all active leagues
    PYTHONPATH=src/api python src/api/jobs/score_tournaments/score_tournaments.py --tournament-id 42

    # Override: specific tournament + specific league
    PYTHONPATH=src/api python src/api/jobs/score_tournaments/score_tournaments.py --tournament-id 42 --league-id 7
"""

import argparse
import logging
from datetime import date

from flask import Flask

from models import (
    League, LeagueMember, LeagueMemberTournamentScore,
    Schedule, ScheduleTournament, Tournament
)
from utils.db_connector import db, init_db

from jobs.calculate_points.calculate_points import update_tournament_entries_and_results
from jobs.calculate_week_scores.calculate_week_scores import calculate_tournament_scores

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def get_unscored_tournaments(league):
    """
    Find tournaments in a league's schedule that have ended but have
    no LeagueMemberTournamentScore rows for this league.

    Args:
        league: League model instance (must have schedule_id set)

    Returns:
        list[int]: Tournament IDs that need scoring
    """
    # Get all league member IDs for this league
    member_ids = [
        mid for (mid,) in
        db.session.query(LeagueMember.id)
        .filter(LeagueMember.league_id == league.id)
        .all()
    ]

    if not member_ids:
        logger.warning("League %s (%s) has no members, skipping", league.id, league.name)
        return []

    # Get tournament IDs from the schedule that have ended
    schedule_rows = (
        db.session.query(ScheduleTournament.tournament_id)
        .join(Tournament, ScheduleTournament.tournament_id == Tournament.id)
        .filter(
            ScheduleTournament.schedule_id == league.schedule_id,
            Tournament.end_date < date.today()
        )
        .all()
    )
    ended_tournament_ids = [tid for (tid,) in schedule_rows]

    if not ended_tournament_ids:
        return []

    # Find which of those already have scores for this league
    scored_tournament_ids = set(
        tid for (tid,) in
        db.session.query(LeagueMemberTournamentScore.tournament_id)
        .filter(
            LeagueMemberTournamentScore.tournament_id.in_(ended_tournament_ids),
            LeagueMemberTournamentScore.league_member_id.in_(member_ids)
        )
        .distinct()
        .all()
    )

    unscored = [tid for tid in ended_tournament_ids if tid not in scored_tournament_ids]
    return unscored


def _tournament_name(tid):
    """Look up a tournament name by ID, with fallback."""
    t = Tournament.query.get(tid)
    return t.tournament_name if t else f"Tournament #{tid}"


def run(tournament_id=None, league_id=None):
    """
    Main orchestrator.

    1. Determine which leagues to process
    2. Find unscored tournaments (or use override)
    3. Fetch results for each unique tournament
    4. Calculate member scores for each (league, tournament) pair

    Args:
        tournament_id: If set, skip auto-detection and process this tournament
        league_id: If set, narrow to this single league
    """
    print("\n" + "=" * 60)
    print("  SCORE TOURNAMENTS")
    print("=" * 60)

    if tournament_id is not None or league_id is not None:
        mode_parts = []
        if tournament_id is not None:
            mode_parts.append(f"tournament={tournament_id}")
        if league_id is not None:
            mode_parts.append(f"league={league_id}")
        print(f"  Mode: override ({', '.join(mode_parts)})")
    else:
        print("  Mode: auto (find all unscored tournaments)")
    print()

    # ── Step 1: Find active leagues ──────────────────────────────
    print("Step 1: Finding active leagues...")
    query = League.query.filter(
        League.is_active == True,
        League.schedule_id.isnot(None)
    )
    if league_id is not None:
        query = query.filter(League.id == league_id)

    leagues = query.all()

    if not leagues:
        print("  No active leagues with schedules found. Exiting.\n")
        return

    for league in leagues:
        print(f"  - {league.name} (ID {league.id})")
    print()

    # ── Step 2: Identify tournaments to score ────────────────────
    print("Step 2: Identifying tournaments to score...")
    pairs = []  # list of (League, tournament_id)

    if tournament_id is not None:
        # Override mode
        for league in leagues:
            in_schedule = (
                db.session.query(ScheduleTournament.id)
                .filter(
                    ScheduleTournament.schedule_id == league.schedule_id,
                    ScheduleTournament.tournament_id == tournament_id
                )
                .first()
            )
            if in_schedule:
                pairs.append((league, tournament_id))
                print(f"  - {_tournament_name(tournament_id)} -> {league.name}")
            else:
                print(f"  - {_tournament_name(tournament_id)} not in {league.name}'s schedule, skipping")
    else:
        # Auto mode
        for league in leagues:
            unscored = get_unscored_tournaments(league)
            if unscored:
                for tid in unscored:
                    pairs.append((league, tid))
                    print(f"  - {_tournament_name(tid)} -> {league.name}")
            else:
                print(f"  - {league.name}: all tournaments scored")

    if not pairs:
        print("\n  Nothing to score — all tournaments are up to date.\n")
        return
    print()

    # ── Step 3: Fetch results from DataGolf ──────────────────────
    unique_tournament_ids = list({tid for _, tid in pairs})
    print(f"Step 3: Fetching results for {len(unique_tournament_ids)} tournament(s)...")
    print("-" * 60)

    results_fetched = set()
    for i, tid in enumerate(unique_tournament_ids, 1):
        t_name = _tournament_name(tid)
        print(f"  [{i}/{len(unique_tournament_ids)}] Getting results for {t_name}...")

        success = update_tournament_entries_and_results(tid)
        if success:
            results_fetched.add(tid)
            print(f"         Done.")
        else:
            print(f"         FAILED — will skip scoring for this tournament")
    print()

    # ── Step 4: Calculate league scores ──────────────────────────
    print(f"Step 4: Calculating scores for {len(pairs)} league-tournament pair(s)...")
    print("-" * 60)

    scored_count = 0
    skipped_count = 0

    for i, (league, tid) in enumerate(pairs, 1):
        t_name = _tournament_name(tid)

        if tid not in results_fetched:
            print(f"  [{i}/{len(pairs)}] {t_name} / {league.name} — SKIPPED (no results)")
            skipped_count += 1
            continue

        print(f"  [{i}/{len(pairs)}] Calculating points: {t_name} / {league.name}")

        success = calculate_tournament_scores(tid, league.id)
        if success:
            scored_count += 1
            print(f"         Done.")
        else:
            print(f"         FAILED")
            skipped_count += 1

    # ── Summary ──────────────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"  COMPLETE: {scored_count} scored, {skipped_count} skipped")
    print("=" * 60)
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Score completed tournaments for active leagues"
    )
    parser.add_argument(
        "--tournament-id", type=int, default=None,
        help="Process a specific tournament (skip auto-detection)"
    )
    parser.add_argument(
        "--league-id", type=int, default=None,
        help="Narrow to a specific league"
    )
    args = parser.parse_args()

    app = Flask(__name__)
    init_db(app)

    with app.app_context():
        run(tournament_id=args.tournament_id, league_id=args.league_id)
