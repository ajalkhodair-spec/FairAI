import argparse
import hashlib
import subprocess
from pathlib import Path


ROOT = Path("outputs/major_revision")
CHECKSUM_FILE = ROOT / "release_checksums.sha256"
PUBLICATION_EXTRAS = (
    ROOT / "figure_data/ipfs_overhead.csv",
    ROOT / "figures_independent/ipfs_overhead.png",
    ROOT / "figures_independent/ipfs_overhead.svg",
    ROOT / "primary_csv/Representation_Fairness.csv",
    ROOT / "primary_csv/Paired_Inference.csv",
    ROOT / "primary_csv/Policy_Approval.csv",
    ROOT / "primary_csv/Scaling_Summary.csv",
    ROOT / "primary_csv/Stage_Timing.csv",
    ROOT / "primary_csv/Trust_Boundary.csv",
    ROOT / "representation_fairness.csv",
    ROOT / "trust_boundary.csv",
)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def publication_files():
    tracked = subprocess.run(
        ["git", "ls-files", "-z", str(ROOT)],
        check=True,
        capture_output=True,
    ).stdout.decode().split("\0")
    paths = {Path(value) for value in tracked if value}
    paths.update(path for path in PUBLICATION_EXTRAS if path.exists())
    paths.discard(CHECKSUM_FILE)
    return sorted(path for path in paths if path.is_file())


def render():
    return "".join(
        f"{sha256_file(path)}  {path.as_posix()}\n"
        for path in publication_files()
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.verify:
        if not CHECKSUM_FILE.exists() or CHECKSUM_FILE.read_text() != expected:
            raise SystemExit("release checksum manifest is stale")
        return
    temporary = CHECKSUM_FILE.with_suffix(".sha256.tmp")
    temporary.write_text(expected, encoding="utf-8")
    temporary.replace(CHECKSUM_FILE)


if __name__ == "__main__":
    main()
