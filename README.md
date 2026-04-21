# Screaming Frog Duplicate Pair Remover

Screaming Frog's Near Duplicates and Semantically Similar exports list every pair twice -- once in each direction. This script removes the mirror rows so each pair appears only once.

## The Problem

When you export these reports from Screaming Frog, you get:

| Address | Near Duplicate Address |
|---------|------------------------|
| url-a   | url-b                  |
| url-b   | url-a                  |

This script reduces that to a single row per pair, making the reports usable for audits without manual cleanup.

## Requirements

- Python 3.9 or later
- No third-party libraries required

## Usage

1. Place `deduplicate_sf_reports.py` in the same folder as your CSV exports.
2. Run it:

```bash
python deduplicate_sf_reports.py
```

The script looks for the Screaming Frog default export filenames:

- `near_duplicates_report.csv`
- `semantically_similar_report.csv`

It will process whichever files are present. At least one must exist. Output files are written to the same folder with `_deduped` appended to the filename.

## Output

```
near_duplicates_report_deduped.csv
semantically_similar_report_deduped.csv
```

All original columns and values are preserved. Only mirror rows are removed.

## Notes

- The script is non-destructive. It never modifies the original files.
- If a URL pair appears in both directions, the first occurrence is kept and the second is dropped.
- Compatible with exports from Screaming Frog SEO Spider.
