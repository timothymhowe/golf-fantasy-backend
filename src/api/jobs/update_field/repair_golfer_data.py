"""
Golfer Data Repair Script

Fixes damage caused by the old update_field.py:
1. Flips 'Last, First' full_names to 'First Last' (rebuilt from the
   first_name / last_name columns)
2. Reports golfers with no datagolf_id (manual review — the fixed
   update_field.py will backfill these as they appear in fields)
3. Reports duplicate golfers (same normalized name, different ids) with
   how many picks / tournament_golfer rows point at each, so merges can
   be decided by a human. Does NOT merge anything.

Dry run by default — prints every change it WOULD make. Nothing is
written without --apply.

Usage:
    PYTHONPATH=src/api python src/api/jobs/update_field/repair_golfer_data.py           # dry run
    PYTHONPATH=src/api python src/api/jobs/update_field/repair_golfer_data.py --apply   # write changes
"""

import argparse

from flask import Flask
from sqlalchemy import text

from models import Golfer
from utils.db_connector import db, init_db


def flip_backwards_names(apply_changes):
    print("\n" + "=" * 70)
    print("  1. BACKWARDS FULL NAMES ('Last, First' -> 'First Last')")
    print("=" * 70)

    golfers = Golfer.query.filter(Golfer.full_name.like('%,%')).order_by(Golfer.id).all()

    if not golfers:
        print("  None found — all full_names are clean.")
        return

    suspicious = []
    for g in golfers:
        rebuilt = f"{g.first_name} {g.last_name}"
        # Sanity check: the rebuilt name should be a reshuffle of the broken
        # one. If not, first/last are probably swapped in the columns too —
        # flag for manual review instead of "fixing" it wrong.
        broken_parts = sorted(g.full_name.replace(',', ' ').split())
        rebuilt_parts = sorted(rebuilt.split())
        if broken_parts != rebuilt_parts:
            suspicious.append(g)
            print(f"  ?? {g.id:<10} '{g.full_name}' vs first/last '{rebuilt}' — MISMATCH, skipping (review manually)")
            continue

        print(f"  {g.id:<10} '{g.full_name}'  ->  '{rebuilt}'")
        if apply_changes:
            g.full_name = rebuilt

    print(f"\n  {len(golfers) - len(suspicious)} names {'fixed' if apply_changes else 'would be fixed'}")
    if suspicious:
        print(f"  {len(suspicious)} skipped as suspicious (first/last columns may be swapped):")
        for g in suspicious:
            print(f"    - {g.id}: full_name='{g.full_name}', first='{g.first_name}', last='{g.last_name}'")


def report_missing_datagolf_ids():
    print("\n" + "=" * 70)
    print("  2. GOLFERS WITH NO DATAGOLF ID (report only)")
    print("=" * 70)

    golfers = Golfer.query.filter(Golfer.datagolf_id.is_(None)).order_by(Golfer.last_name).all()
    if not golfers:
        print("  None — every golfer has a datagolf_id.")
        return

    for g in golfers:
        print(f"  {g.id:<10} {g.first_name} {g.last_name}")
    print(f"\n  {len(golfers)} golfers with NULL datagolf_id.")
    print("  No action taken — the fixed update_field.py backfills these when they next appear in a field.")


def report_duplicate_golfers():
    print("\n" + "=" * 70)
    print("  3. DUPLICATE GOLFERS (report only — merge by hand)")
    print("=" * 70)

    rows = db.session.execute(text("""
        SELECT LOWER(CONCAT(g.first_name, ' ', g.last_name)) AS norm,
               g.id, g.full_name, g.datagolf_id,
               (SELECT COUNT(*) FROM pick p WHERE p.golfer_id = g.id) AS pick_refs,
               (SELECT COUNT(*) FROM tournament_golfer tg WHERE tg.golfer_id = g.id) AS tg_refs
        FROM golfer g
        WHERE LOWER(CONCAT(g.first_name, ' ', g.last_name)) IN (
            SELECT norm FROM (
                SELECT LOWER(CONCAT(first_name, ' ', last_name)) AS norm
                FROM golfer GROUP BY norm HAVING COUNT(*) > 1
            ) AS dupes
        )
        ORDER BY norm, g.id
    """)).fetchall()

    if not rows:
        print("  None found.")
        return

    current = None
    for r in rows:
        if r.norm != current:
            current = r.norm
            print(f"\n  {r.norm}:")
        print(f"    {r.id:<10} full_name='{r.full_name}'  dg_id={r.datagolf_id}  picks={r.pick_refs}  tournament_golfer_rows={r.tg_refs}")

    print("\n  To merge a pair: repoint pick + tournament_golfer rows at the keeper, then delete the orphan.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Repair golfer data damaged by old update_field.py")
    parser.add_argument("--apply", action="store_true", help="Write changes (default is dry run)")
    args = parser.parse_args()

    app = Flask(__name__)
    init_db(app)

    with app.app_context():
        mode = "APPLY — WRITING CHANGES" if args.apply else "DRY RUN — nothing will be written"
        print(f"\n### Golfer Data Repair ({mode}) ###")

        flip_backwards_names(args.apply)
        report_missing_datagolf_ids()
        report_duplicate_golfers()

        if args.apply:
            db.session.commit()
            print("\nChanges committed.")
        else:
            db.session.rollback()
            print("\nDry run complete — run again with --apply to write the name fixes.")
