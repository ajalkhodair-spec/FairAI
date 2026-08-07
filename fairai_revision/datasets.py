import argparse
import csv
import hashlib
import json
import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path


DATASETS = {
    "adult": {
        "url": "https://archive.ics.uci.edu/static/public/2/adult.zip",
        "sha256": "7537312dd56c2b98035880805ce99e68183a30ee468aa5329d6df0fbb3cc21bb",
        "filename": "adult.zip",
        "source": "UCI Machine Learning Repository",
        "license": "CC-BY-4.0",
    },
    "compas": {
        "url": (
            "https://raw.githubusercontent.com/propublica/compas-analysis/"
            "bafff5da3f2e45eca6c2d5055faad269defd135a/"
            "compas-scores-two-years.csv"
        ),
        "sha256": "c451db85908b2f7fef1d83203bedf6b71ecda0d5af468d82ae62178f91d0cc7d",
        "filename": "compas-scores-two-years.csv",
        "source": "ProPublica compas-analysis",
        "license": "ProPublica data terms; raw redistribution prohibited",
    },
}


ADULT_COLUMNS = [
    "age",
    "workclass",
    "fnlwgt",
    "education",
    "education_num",
    "marital_status",
    "occupation",
    "relationship",
    "race",
    "sex",
    "capital_gain",
    "capital_loss",
    "hours_per_week",
    "native_country",
    "income",
]


@dataclass(frozen=True)
class DatasetPaths:
    raw_dir: Path
    processed_dir: Path
    manifest_path: Path


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_dataset(name, data_root="data", force=False):
    if name not in DATASETS:
        raise ValueError(f"Unsupported dataset: {name}")
    spec = DATASETS[name]
    root = Path(data_root)
    raw_dir = root / "raw" / name
    processed_dir = root / "processed" / name
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    target = raw_dir / spec["filename"]

    if force or not target.exists():
        temporary = raw_dir / f".{spec['filename']}.download"
        try:
            with urllib.request.urlopen(spec["url"], timeout=60) as response:
                with temporary.open("wb") as handle:
                    shutil.copyfileobj(response, handle)
            observed = sha256_file(temporary)
            if observed != spec["sha256"]:
                raise ValueError(
                    f"Checksum mismatch for {name}: expected {spec['sha256']}, got {observed}"
                )
            temporary.replace(target)
        finally:
            if temporary.exists():
                temporary.unlink()

    observed = sha256_file(target)
    if observed != spec["sha256"]:
        raise ValueError(
            f"Checksum mismatch for existing {name}: expected {spec['sha256']}, got {observed}"
        )

    extracted = []
    if name == "adult":
        with zipfile.ZipFile(target) as archive:
            required = {"adult.data", "adult.test", "adult.names"}
            missing = required - set(archive.namelist())
            if missing:
                raise ValueError(f"Adult archive is missing files: {sorted(missing)}")
            for member in sorted(required):
                destination = raw_dir / member
                with archive.open(member) as source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
                extracted.append(
                    {
                        "file": member,
                        "sha256": sha256_file(destination),
                        "bytes": destination.stat().st_size,
                    }
                )

    manifest = {
        "schema_version": "fairai.dataset_download.v1",
        "dataset": name,
        "source": spec["source"],
        "source_url": spec["url"],
        "license_or_terms": spec["license"],
        "archive_file": spec["filename"],
        "archive_sha256": observed,
        "archive_bytes": target.stat().st_size,
        "extracted_files": extracted,
        "raw_data_committed": False,
    }
    manifest_path = raw_dir / "download_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return DatasetPaths(raw_dir, processed_dir, manifest_path)


def read_adult_rows(path, test_file=False):
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for raw in handle:
            if not raw.strip() or raw.startswith("|"):
                continue
            values = [value.strip() for value in next(csv.reader([raw]))]
            if len(values) != len(ADULT_COLUMNS):
                raise ValueError(f"Unexpected Adult row width in {path}")
            record = dict(zip(ADULT_COLUMNS, values))
            if test_file:
                record["income"] = record["income"].rstrip(".")
            rows.append(record)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description="Download checksum-pinned fairness datasets")
    parser.add_argument("dataset", choices=sorted(DATASETS))
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    paths = download_dataset(args.dataset, args.data_root, force=args.force)
    print(
        json.dumps(
            {
                "dataset": args.dataset,
                "manifest": str(paths.manifest_path),
                "status": "verified",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

