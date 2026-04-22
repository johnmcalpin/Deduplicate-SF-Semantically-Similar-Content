import csv
import sys
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration — edit these if your files live elsewhere
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent

# Each report accepts multiple possible filenames; the first one found wins.
NEAR_DUPES_FILENAMES = [
    "near_duplicates_report.csv",
    "content_near_duplicates.csv",
]
SEM_SIM_FILENAMES = [
    "semantically_similar_report.csv",
    "content_semantically_similar.csv",
]

# Column names as exported by Screaming Frog (case-sensitive)
NEAR_DUPES_ADDRESS_COL = "Address"
NEAR_DUPES_PAIR_COL = "Near Duplicate Address"
NEAR_DUPES_SCORE_COL = "Closest Similarity Match"
NEAR_DUPES_COUNT_COL = "No. Near Duplicates"

SEM_SIM_ADDRESS_COL = "Address"
SEM_SIM_PAIR_COL = "Closest Semantically Similar Address"
SEM_SIM_SCORE_COL = "Semantic Similarity Score"
SEM_SIM_COUNT_COL = "No. Semantically Similar"


# ---------------------------------------------------------------------------
# Clustering logic
# ---------------------------------------------------------------------------

def cluster_pairs(
    rows: list[dict],
    address_col: str,
    pair_col: str,
    score_col: str,
) -> tuple[list[tuple], dict[str, dict]]:
    edge_data: dict[frozenset, tuple] = {}
    first_seen_idx: dict[str, int] = {}
    primary_side_row: dict[str, dict] = {}

    for i, row in enumerate(rows):
        a = row.get(address_col, "")
        b = row.get(pair_col, "")
        if not a or not b or a == b:
            continue

        score_str = row.get(score_col, "") if score_col else ""
        try:
            score_float = float(score_str) if score_str else 0.0
        except ValueError:
            score_float = 0.0

        pair = frozenset([a, b])
        if pair not in edge_data:
            edge_data[pair] = (score_str, score_float, row)

        if a not in first_seen_idx:
            first_seen_idx[a] = i
        if b not in first_seen_idx:
            first_seen_idx[b] = i
        if a not in primary_side_row:
            primary_side_row[a] = row

    remaining = set(edge_data.keys())
    groups: list[tuple] = []

    while remaining:
        degree: dict[str, int] = defaultdict(int)
        for edge in remaining:
            for u in edge:
                degree[u] += 1

        # Highest degree first; earliest-seen wins ties for deterministic output.
        primary = max(
            degree.keys(),
            key=lambda u: (degree[u], -first_seen_idx.get(u, 10**9)),
        )

        neighbors = []
        for edge in list(remaining):
            if primary in edge:
                other = next(iter(edge - {primary}))
                score_str, score_float, source_row = edge_data[edge]
                neighbors.append((other, score_str, score_float, source_row))
                remaining.discard(edge)

        neighbors.sort(key=lambda x: -x[2])
        groups.append((primary, neighbors))

    return groups, primary_side_row


def build_output_rows(
    groups: list[tuple],
    primary_side_row: dict[str, dict],
    fieldnames: list[str],
    address_col: str,
    pair_col: str,
    score_col: str,
    count_col: str,
) -> tuple[list[dict], list[str]]:
    max_similar = max((len(n) for _, n in groups), default=0)

    replaced = {address_col, pair_col, score_col, count_col}
    replaced.discard("")
    dropped = {"Indexability", "Indexability Status"}
    passthrough_cols = [c for c in fieldnames if c not in replaced and c not in dropped]

    new_fieldnames: list[str] = [address_col, "Total Similar"]
    for i in range(1, max_similar + 1):
        new_fieldnames.append(f"Similar URL {i}")
        if score_col:
            new_fieldnames.append(f"Similarity Score {i}")
    new_fieldnames.extend(passthrough_cols)

    output_rows: list[dict] = []
    for primary, neighbors in groups:
        if not neighbors:
            continue
        base_meta = primary_side_row.get(primary) or neighbors[0][3]

        row = {
            address_col: primary,
            "Total Similar": str(len(neighbors)),
        }
        for col in passthrough_cols:
            row[col] = base_meta.get(col, "")

        for i, (other, score_str, _, _) in enumerate(neighbors, start=1):
            row[f"Similar URL {i}"] = other
            if score_col:
                row[f"Similarity Score {i}"] = score_str

        for f in new_fieldnames:
            row.setdefault(f, "")

        output_rows.append(row)

    return output_rows, new_fieldnames
def process_file(
    filepath: Path,
    address_col: str,
    pair_col: str,
    score_col: str,
    count_col: str,
    label: str,
) -> None:
    if not filepath.exists():
        print(f"  [skip] {filepath.name} not found.")
        return

    with open(filepath, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    original_count = len(rows)

    missing = [c for c in (address_col, pair_col) if c not in fieldnames]
    if missing:
        print(
            f"  [error] {filepath.name}: expected columns not found: {missing}\n"
            f"          Found columns: {fieldnames}"
        )
        return

    resolved_score_col = score_col if score_col in fieldnames else ""
    resolved_count_col = count_col if count_col in fieldnames else ""

    groups, primary_side_row = cluster_pairs(
        rows, address_col, pair_col, resolved_score_col
    )
    out_rows, out_fieldnames = build_output_rows(
        groups,
        primary_side_row,
        fieldnames,
        address_col,
        pair_col,
        resolved_score_col,
        resolved_count_col,
    )

    out_path = filepath.with_stem(filepath.stem + "_deduped")
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=out_fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    total_edges = sum(len(n) for _, n in groups)
    multi_clusters = sum(1 for _, n in groups if len(n) > 1)
    print(
        f"  [{label}] {filepath.name}\n"
        f"    Original rows          : {original_count}\n"
        f"    Unique pairs           : {total_edges}\n"
        f"    Output rows (clusters) : {len(out_rows)}\n"
        f"    Rows with >1 similar   : {multi_clusters}\n"
        f"    Output : {out_path.name}"
    )

def find_first_existing(filenames: list[str]) -> Path | None:
    for name in filenames:
        candidate = SCRIPT_DIR / name
        if candidate.exists():
            return candidate
    return None


def main() -> None:
    print("Screaming Frog Report Deduplicator (clustered)")
    print("=" * 48)

    found_any = False

    near_dupes_path = find_first_existing(NEAR_DUPES_FILENAMES)
    if near_dupes_path is not None:
        found_any = True
        process_file(
            filepath=near_dupes_path,
            address_col=NEAR_DUPES_ADDRESS_COL,
            pair_col=NEAR_DUPES_PAIR_COL,
            score_col=NEAR_DUPES_SCORE_COL,
            count_col=NEAR_DUPES_COUNT_COL,
            label="Near Duplicates",
        )
        print()

    sem_sim_path = find_first_existing(SEM_SIM_FILENAMES)
    if sem_sim_path is not None:
        found_any = True
        process_file(
            filepath=sem_sim_path,
            address_col=SEM_SIM_ADDRESS_COL,
            pair_col=SEM_SIM_PAIR_COL,
            score_col=SEM_SIM_SCORE_COL,
            count_col=SEM_SIM_COUNT_COL,
            label="Semantically Similar",
        )
        print()

    if not found_any:
        all_names = NEAR_DUPES_FILENAMES + SEM_SIM_FILENAMES
        expected_list = "\n".join(f"  {SCRIPT_DIR / name}" for name in all_names)
        print(
            "No input files found.\n"
            f"Expected one of:\n"
            f"{expected_list}\n\n"
            "Place this script in the same folder as your CSV exports and re-run."
        )
        sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()
