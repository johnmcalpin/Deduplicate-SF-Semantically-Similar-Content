"""
deduplicate_sf_reports.py

Removes bidirectional/redundant row pairs from Screaming Frog's
"Near Duplicates" and "Semantically Similar" export CSVs.

For near duplicates, each pair (A→B) and (B→A) appears twice.
For semantically similar, each pair (A→B) and (B→A) may also appear twice.
This script keeps only the first occurrence of each unordered pair.

Usage:
    python deduplicate_sf_reports.py

Place this script in the same folder as your CSV exports, or pass paths
via the constants below. The script will process whichever files it finds.

Expected filenames (Screaming Frog defaults):
    near_duplicates_report.csv
    semantically_similar_report.csv

Output files will be written alongside the originals with "_deduped" appended
to the filename stem, e.g.:
    near_duplicates_report_deduped.csv
    semantically_similar_report_deduped.csv
"""

import csv
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration — edit these if your files live elsewhere
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent

NEAR_DUPES_FILENAME = "near_duplicates_report.csv"
SEM_SIM_FILENAME = "semantically_similar_report.csv"

# Column names as exported by Screaming Frog (case-sensitive)
NEAR_DUPES_ADDRESS_COL = "Address"
NEAR_DUPES_PAIR_COL = "Near Duplicate Address"

SEM_SIM_ADDRESS_COL = "Address"
SEM_SIM_PAIR_COL = "Closest Semantically Similar Address"


# ---------------------------------------------------------------------------
# Core deduplication logic
# ---------------------------------------------------------------------------

def deduplicate_pairs(rows: list[dict], col_a: str, col_b: str) -> list[dict]:
    """
    Given a list of CSV row dicts, remove rows where the unordered pair
    (row[col_a], row[col_b]) has already been seen.

    The first occurrence of each pair is kept; its mirror is dropped.
    """
    seen: set[frozenset] = set()
    deduped: list[dict] = []

    for row in rows:
        pair = frozenset([row[col_a], row[col_b]])
        if pair not in seen:
            seen.add(pair)
            deduped.append(row)

    return deduped


def process_file(
    filepath: Path,
    address_col: str,
    pair_col: str,
    label: str,
) -> None:
    """Read a CSV, deduplicate bidirectional pairs, write *_deduped.csv."""

    if not filepath.exists():
        print(f"  [skip] {filepath.name} not found.")
        return

    with open(filepath, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    original_count = len(rows)

    # Validate expected columns exist
    missing = [c for c in (address_col, pair_col) if c not in fieldnames]
    if missing:
        print(
            f"  [error] {filepath.name}: expected columns not found: {missing}\n"
            f"          Found columns: {fieldnames}"
        )
        return

    deduped = deduplicate_pairs(rows, address_col, pair_col)
    removed = original_count - len(deduped)

    out_path = filepath.with_stem(filepath.stem + "_deduped")
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deduped)

    print(
        f"  [{label}] {filepath.name}\n"
        f"    Original rows : {original_count}\n"
        f"    Removed (mirror pairs) : {removed}\n"
        f"    Remaining rows : {len(deduped)}\n"
        f"    Output : {out_path.name}"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("Screaming Frog Report Deduplicator")
    print("=" * 40)

    found_any = False

    near_dupes_path = SCRIPT_DIR / NEAR_DUPES_FILENAME
    if near_dupes_path.exists():
        found_any = True
        process_file(
            filepath=near_dupes_path,
            address_col=NEAR_DUPES_ADDRESS_COL,
            pair_col=NEAR_DUPES_PAIR_COL,
            label="Near Duplicates",
        )
        print()

    sem_sim_path = SCRIPT_DIR / SEM_SIM_FILENAME
    if sem_sim_path.exists():
        found_any = True
        process_file(
            filepath=sem_sim_path,
            address_col=SEM_SIM_ADDRESS_COL,
            pair_col=SEM_SIM_PAIR_COL,
            label="Semantically Similar",
        )
        print()

    if not found_any:
        print(
            "No input files found.\n"
            f"Expected one or both of:\n"
            f"  {SCRIPT_DIR / NEAR_DUPES_FILENAME}\n"
            f"  {SCRIPT_DIR / SEM_SIM_FILENAME}\n\n"
            "Place this script in the same folder as your CSV exports and re-run."
        )
        sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()
