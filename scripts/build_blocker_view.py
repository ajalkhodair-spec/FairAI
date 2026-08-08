import argparse
import csv
import json
from io import StringIO
from pathlib import Path


SOURCE = Path("BLOCKERS.md")
CSV_OUTPUT = Path("outputs/major_revision/primary_csv/Missing_Data.csv")
MISSING_JSON_OUTPUT = Path("outputs/major_revision/missing_measurements.json")
LIMITATIONS_JSON_OUTPUT = Path("outputs/major_revision/limitations_observed.json")
FIELDS = ("id", "status", "scope", "blocker", "effect")


def rows():
    result = []
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| BLK-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(FIELDS):
            raise ValueError(f"invalid blocker row: {line}")
        result.append(dict(zip(FIELDS, cells)))
    if not result:
        raise ValueError("no blocker rows found")
    return result


def render_csv(data):
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def render_json(data):
    return json.dumps(data, indent=2) + "\n"


def expected_outputs():
    data = rows()
    return {
        CSV_OUTPUT: render_csv(data),
        MISSING_JSON_OUTPUT: render_json(data),
        LIMITATIONS_JSON_OUTPUT: render_json(
            {
                "schema_version": "fairai.limitations.v1",
                "limitations": data,
            }
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    expected = expected_outputs()
    if args.verify:
        stale = [
            path.as_posix()
            for path, content in expected.items()
            if not path.exists() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            raise SystemExit("blocker views are stale: " + ", ".join(stale))
        return
    for path, content in expected.items():
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8", newline="")
        temporary.replace(path)


if __name__ == "__main__":
    main()
