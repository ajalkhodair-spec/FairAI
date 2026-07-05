#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


EXPECTED_STATES = ["Open", "SubmissionClosed", "AggregationStarted", "Published", "Archived"]


def check(condition, failures, message):
    if not condition:
        failures.append(message)


def main():
    parser = argparse.ArgumentParser(description="Validate a FairAI MVP run directory.")
    parser.add_argument("run_dir", help="Run output directory.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    summary = json.loads((run_dir / "run_summary.json").read_text())
    ledger = json.loads((run_dir / "ledger.json").read_text())
    failures = []

    check(summary["final_round_state"] == "Archived", failures, "round did not finish Archived")
    check(summary["ipfs_mode"] == "kubo-http", failures, "run did not use Kubo HTTP IPFS")
    check(
        [event["state"] for event in summary["round_events"]] == EXPECTED_STATES,
        failures,
        "round lifecycle events are incomplete or out of order",
    )
    check(
        summary["global_publication"]["participant_model_cids"] == summary["global_model"]["participant_model_cids"],
        failures,
        "published participant CIDs differ from global model participant CIDs",
    )
    check(
        sorted(ledger["eligible_model_cids"]) == sorted(summary["global_model"]["participant_model_cids"]),
        failures,
        "ledger eligible CIDs differ from aggregated participant CIDs",
    )
    check(
        len(ledger["audit_events"]) == summary["nodes_total"],
        failures,
        "audit event count does not match node count",
    )

    for item in summary["instrumentation"]["ipfs_retrieval_checks"]:
        check(item.get("valid") is True, failures, f"IPFS retrieval failed for {item.get('cid')}")
    for item in summary["instrumentation"]["ipfs_pin_results"]:
        check(item.get("pinned") is True, failures, f"IPFS pin failed for {item.get('cid')}")

    result = {
        "run_dir": str(run_dir),
        "status": "passed" if not failures else "failed",
        "failures": failures,
        "round_id": summary["round_id"],
        "approved_nodes": summary["approved_nodes"],
        "rejected_nodes": summary["rejected_nodes"],
        "global_model_cid": summary["global_model_cid"],
        "report_cid": summary["report_cid"],
        "global_publication_tx": summary["global_publication"]["tx_hash"],
        "verifier_mode": ledger.get("verifier_mode"),
    }
    output_path = run_dir / "monitoring_report.json"
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
