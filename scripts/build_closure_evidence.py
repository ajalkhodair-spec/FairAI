import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(".")
OUTPUT_ROOT = ROOT / "outputs" / "revision_audit"
CHECKSUM_FILE = OUTPUT_ROOT / "closure_checksums.sha256"
FREEZE_FILE = OUTPUT_ROOT / "closure_evidence_freeze.json"
SOURCE_BASELINE_COMMIT = "434ab67f067c8ab26f1908369f62d2e2b4ec3fe3"
FIXED_TARGETS = (
    ROOT / "BLOCKERS.md",
    ROOT / "README.md",
    ROOT / "RELEASE_CHECKLIST.md",
    ROOT / "audits/prechange/evidence_discrepancy_report.md",
    ROOT / "docs/revision/STATUS.md",
    ROOT / "docs/revision/REVIEWER_EVIDENCE_MAP.md",
    ROOT / "docs/revision/REVIEWER_GAP_MATRIX.csv",
    ROOT / "docs/revision/circom_version_reconciliation.md",
    ROOT / "docs/revision/direct_verifier_evidence_boundary.md",
    ROOT / "docs/revision/closure_verification_status.md",
    ROOT / "outputs/major_revision/FairAI_Major_Revision_Results.xlsx",
    ROOT / "outputs/major_revision/release_checksums.sha256",
    ROOT / "outputs/major_revision/reviewer_evidence_map.json",
    ROOT / "outputs/major_revision/primary_csv/Reviewer_Evidence_Map.csv",
    ROOT / "outputs/major_revision/primary_csv/Missing_Data.csv",
    ROOT / "outputs/major_revision/primary_csv/Paired_Inference.csv",
    ROOT / "outputs/major_revision/primary_csv/Policy_Approval.csv",
    ROOT / "outputs/major_revision/primary_csv/Scaling_Summary.csv",
)
MANUSCRIPT_BUILD_SUFFIXES = {
    ".aux",
    ".fdb_latexmk",
    ".fls",
    ".log",
    ".out",
    ".synctex",
    ".gz",
}


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def manuscript_targets():
    manuscript = ROOT / "manuscript"
    return {
        path
        for path in manuscript.rglob("*")
        if path.is_file()
        and path.name != ".DS_Store"
        and path != manuscript / "FairAI.pdf"
        and path.suffix not in MANUSCRIPT_BUILD_SUFFIXES
        and "synctex" not in path.name
    }


def closure_targets():
    targets = set(FIXED_TARGETS) | manuscript_targets()
    missing = sorted(path.as_posix() for path in targets if not path.is_file())
    if missing:
        raise FileNotFoundError("missing closure targets: " + ", ".join(missing))
    return sorted(targets)


def render_checksums():
    return "".join(
        f"{sha256_file(path)}  {path.as_posix()}\n" for path in closure_targets()
    )


def render_freeze(checksum_text):
    targets = closure_targets()
    hashes = {path.as_posix(): sha256_file(path) for path in targets}
    payload = {
        "schema_version": "fairai.closure_evidence_freeze.v1",
        "status": "closed_with_documented_limitations",
        "source_baseline_commit": SOURCE_BASELINE_COMMIT,
        "release_lineage": {
            "published_tag": "v0.3.0",
            "published_commit": "6c064d0d3e01d0b6493b6650cb781379c7044fcd",
            "zenodo_version_doi": "10.5281/zenodo.21864931",
            "zenodo_concept_doi": "10.5281/zenodo.21838694",
        },
        "target_count": len(targets),
        "closure_checksum_manifest": CHECKSUM_FILE.as_posix(),
        "closure_checksum_manifest_sha256": hashlib.sha256(
            checksum_text.encode("utf-8")
        ).hexdigest(),
        "canonical_target_sha256": hashes,
        "historical_freeze_preserved": (
            "outputs/revision_audit/current_evidence_freeze.json"
        ),
        "workbook_rebuild": {
            "status": "completed_and_visually_verified",
            "sheet_count": 43,
            "source": "outputs/major_revision/primary_csv/*.csv",
            "command": (
                "python -m scripts.prepare_results_package --primary-csv-only "
                "&& node scripts/build_results_workbook.mjs"
            ),
            "formula_error_scan_matches": 0,
        },
        "closure_test_runs": {
            "python_compatibility": {
                "status": "passed",
                "tests": 84,
                "exact_requirements_lock": True,
            },
            "solidity_lockfile_matching": {
                "status": "passed",
                "tests": 22,
                "hardhat": "2.28.6",
                "snarkjs": "0.7.5",
            },
            "two_peer_kubo_compose": {
                "status": "passed",
                "kubo": "0.29.0",
                "purpose": "functional_integration",
                "repetitions": 3,
            },
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_atomic(path, content):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    checksum_text = render_checksums()
    freeze_text = render_freeze(checksum_text)
    if args.verify:
        if not CHECKSUM_FILE.exists() or CHECKSUM_FILE.read_text() != checksum_text:
            raise SystemExit("closure checksum manifest is stale")
        if not FREEZE_FILE.exists() or FREEZE_FILE.read_text() != freeze_text:
            raise SystemExit("closure evidence freeze is stale")
        return
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_atomic(CHECKSUM_FILE, checksum_text)
    write_atomic(FREEZE_FILE, freeze_text)


if __name__ == "__main__":
    main()
