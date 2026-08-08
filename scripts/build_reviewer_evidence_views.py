import argparse
import csv
import json
from pathlib import Path


SOURCE = Path("docs/revision/REVIEWER_GAP_MATRIX.csv")
JSON_OUTPUT = Path("outputs/major_revision/reviewer_evidence_map.json")
CSV_OUTPUT = Path("outputs/major_revision/primary_csv/Reviewer_Evidence_Map.csv")
FIELDS = (
    "reviewer",
    "comment_id",
    "concern",
    "current_evidence",
    "gap",
    "planned_phase",
    "status",
    "evidence_type",
    "source_file",
)


def rows():
    with SOURCE.open(newline="", encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))
    result = []
    for row in source_rows:
        row["evidence_type"] = "evidence_map"
        row["source_file"] = "docs/revision/REVIEWER_EVIDENCE_MAP.md"
        result.append({field: row[field] for field in FIELDS})
    return result


def render_json(data):
    return json.dumps(data, indent=2, ensure_ascii=True) + "\n"


def render_csv(data):
    from io import StringIO

    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def write_atomic(path, content):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    data = rows()
    expected_json = render_json(data)
    expected_csv = render_csv(data)
    if args.verify:
        if JSON_OUTPUT.read_text(encoding="utf-8") != expected_json:
            raise SystemExit("reviewer JSON view is stale")
        if CSV_OUTPUT.read_text(encoding="utf-8") != expected_csv:
            raise SystemExit("reviewer CSV view is stale")
        return
    write_atomic(JSON_OUTPUT, expected_json)
    write_atomic(CSV_OUTPUT, expected_csv)


if __name__ == "__main__":
    main()
