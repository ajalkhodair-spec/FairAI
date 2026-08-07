import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd


def describe(values, stage, source, status="measured"):
    values = pd.Series(values, dtype=float).dropna()
    if values.empty:
        return {
            "stage": stage, "status": status,
            "evidence_type": "unavailable" if status != "measured" else "measured",
            "n": 0, "mean_ms": None, "std_ms": None, "median_ms": None,
            "p95_ms": None, "minimum_ms": None, "maximum_ms": None,
            "source": source,
        }
    return {
        "stage": stage, "status": status, "evidence_type": "measured",
        "n": len(values), "mean_ms": values.mean(),
        "std_ms": values.std(ddof=1) if len(values) > 1 else 0.0,
        "median_ms": values.median(), "p95_ms": values.quantile(0.95),
        "minimum_ms": values.min(), "maximum_ms": values.max(),
        "source": source,
    }


def add_values(collection, stage, values, source):
    entry = collection.setdefault(stage, {"values": [], "sources": set()})
    entry["values"].extend(pd.Series(values, dtype=float).dropna().tolist())
    entry["sources"].add(str(source))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--federated-run", action="append", required=True)
    parser.add_argument("--strict-run", action="append", required=True)
    parser.add_argument("--proof-run")
    args = parser.parse_args()
    collected = {}
    for value in args.federated_run:
        directory = Path(value)
        timing_path = directory / "metrics" / "stage_timings.csv"
        timings = pd.read_csv(timing_path)
        for stage, group in timings.groupby("stage", sort=True):
            add_values(collected, stage, group["duration_ms"], timing_path)
        test_path = directory / "metrics" / "test_metrics.csv"
        add_values(
            collected, "end_to_end_method",
            pd.read_csv(test_path)["runtime_ms"], test_path,
        )
    for value in args.strict_run:
        for evidence_path in sorted(Path(value).rglob("contract_result.json")):
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            retrieval = pd.DataFrame(evidence["retrieval_rows"])
            initial = retrieval[retrieval["artifact_type"] != "approved_model_master_retrieval"]
            approved = retrieval[retrieval["artifact_type"] == "approved_model_master_retrieval"]
            add_values(collected, "kubo_add", initial["upload_ms"], evidence_path)
            add_values(collected, "consumer_retrieval", initial["retrieval_ms"], evidence_path)
            if "pin_ms" in initial:
                add_values(collected, "consumer_pin", initial["pin_ms"], evidence_path)
            add_values(collected, "approved_model_retrieval", approved["retrieval_ms"], evidence_path)
            serialization = pd.DataFrame(evidence.get("serialization_rows", []))
            if not serialization.empty:
                add_values(collected, "artifact_serialization", serialization["serialization_ms"], evidence_path)
            records = pd.DataFrame([record for rnd in evidence["rounds"] for record in rnd["records"]])
            if "signature_ms" in records:
                add_values(collected, "eip712_decision_signing", records["signature_ms"], evidence_path)
            if "contract_submission_ms" in records:
                add_values(collected, "contract_submission", records["contract_submission_ms"], evidence_path)
            contract = pd.DataFrame(evidence.get("contract_timing_rows", []))
            if not contract.empty:
                for stage, group in contract.groupby("stage", sort=True):
                    add_values(collected, stage, group["duration_ms"], evidence_path)
            if args.proof_run is None:
                proof = pd.DataFrame(evidence["proof_rows"])
                proof = proof[proof["approved"]]
                for field, stage in (("witness_ms", "witness_generation"), ("proof_ms", "proof_generation"), ("verify_ms", "off_chain_proof_verification")):
                    add_values(collected, stage, proof[field], evidence_path)
    if args.proof_run:
        proof_path = Path(args.proof_run) / "raw" / "v2_proof_timings.csv"
        proof = pd.read_csv(proof_path)
        for field, stage in (("witness_ms", "witness_generation"), ("proof_ms", "proof_generation"), ("verify_ms", "off_chain_proof_verification")):
            add_values(collected, stage, proof[field], proof_path)
    rows = [
        describe(item["values"], stage, ";".join(sorted(item["sources"])))
        for stage, item in sorted(collected.items())
    ]
    rows.append(describe([], "direct_solidity_verification_latency", "Gas measured separately; wall-clock latency was not instrumented", status="unavailable"))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)
    manifest = {
        "schema_version": "fairai.stage_timing_analysis.v1",
        "evidence_type": "derived_from_independent_measured_timers",
        "analysis_git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip(),
        "federated_runs": args.federated_run,
        "strict_runs": args.strict_run,
        "proof_run": args.proof_run,
        "unavailable_stages_are_not_imputed": True,
        "stage_timing_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    (output.parent / "analysis_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
