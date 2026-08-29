"""
Full-Season Rescore Script

Re-runs scoring for every ended tournament in a league's schedule, in week
order. Use after a scoring-logic fix (e.g. the duplicate-pick check) to
repair historical scores — calculate_tournament_scores wipes and recalcs
each tournament, so duplicate picks get correctly zeroed and flagged with
is_duplicate_pick=True, which the frontend displays as DUPLICATE.

Does NOT refetch results from DataGolf — it rescores from results already
in the database.

Usage:
    PYTHONPATH=src/api python src/api/jobs/score_tournaments/rescore_season.py --league-id 10
"""

import argparse
import sys
from datetime import date

from flask import Flask

from models import League, ScheduleTournament, Tournament
from utils.db_connector import db, init_db

from jobs.calculate_week_scores.calculate_week_scores import calculate_tournament_scores


def run(league_id):
    league = db.session.get(League, league_id)
    if league is None:
        print(f"League {league_id} not found. Exiting.")
        return False  # bad argument -- a real failure
    if league.schedule_id is None:
        print(f"League {league.name} (ID {league_id}) has no schedule. Exiting.")
        return False  # misconfigured league -- a real failure

    print("\n" + "=" * 60)
    print(f"  RESCORE SEASON — {league.name} (ID {league_id})")
    print("=" * 60)

    rows = (
        db.session.query(ScheduleTournament, Tournament)
        .join(Tournament, ScheduleTournament.tournament_id == Tournament.id)
        .filter(
            ScheduleTournament.schedule_id == league.schedule_id,
            Tournament.end_date < date.today()
        )
        .order_by(ScheduleTournament.week_number)
        .all()
    )

    if not rows:
        print("  No ended tournaments in this league's schedule. Exiting.\n")
        return True   # nothing to rescore is not a failure

    print(f"  Found {len(rows)} ended tournament(s) to rescore:\n")
    for st, t in rows:
        print(f"  - Week {st.week_number}: {t.tournament_name}")

    succeeded = 0
    failed = []

    for i, (st, t) in enumerate(rows, 1):
        print("\n" + "-" * 60)
        print(f"  [{i}/{len(rows)}] Week {st.week_number}: {t.tournament_name}")
        print("-" * 60)

        if calculate_tournament_scores(t.id, league_id):
            succeeded += 1
        else:
            failed.append(t.tournament_name)

    print("\n" + "=" * 60)
    print(f"  COMPLETE: {succeeded} rescored, {len(failed)} failed")
    for name in failed:
        print(f"  FAILED: {name}")
    print("=" * 60)
    print()

    return not failed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Rescore all ended tournaments in a league's schedule"
    )
    parser.add_argument(
        "--league-id", type=int, required=True,
        help="League to rescore (e.g. 10)"
    )
    args = parser.parse_args()

    app = Flask(__name__)
    init_db(app)

    with app.app_context():
        all_rescored = run(league_id=args.league_id)

    sys.exit(0 if all_rescored else 1)
