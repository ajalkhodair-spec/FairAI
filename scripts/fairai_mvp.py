#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.ipfs_adapter import IPFSAdapter
except ModuleNotFoundError:
    from ipfs_adapter import IPFSAdapter


ROOT = Path(__file__).resolve().parents[1]
CIRCUIT = ROOT / "circuits" / "FairnessEligibility.circom"
BUILD_DIR = ROOT / "build"
DEFAULT_PTAU = Path(os.environ.get("FAIRAI_PTAU_PATH", ROOT / "zk" / "powersoftau_final.ptau"))

ROUND_ID = 1
NUM_NODES = 3
SAMPLES_PER_NODE = 80
VALIDATION_SAMPLES = 180
MIN_ACCURACY = 0.62
MAX_FAIRNESS_GAP = 0.28
SCALE = 1000


@dataclass
class Example:
    x1: float
    x2: float
    group: int
    label: int


def stable_json(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def now_ms():
    return int(time.time() * 1000)


def sigmoid(value):
    if value < -40:
        return 0.0
    if value > 40:
        return 1.0
    return 1.0 / (1.0 + math.exp(-value))


class ContentStore:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put_json(self, name, payload):
        encoded = stable_json(payload)
        digest = sha256_bytes(encoded)
        cid = f"sha256-{digest}"
        suffix = Path(name).suffix or ".json"
        target = self.root / f"{cid}{suffix}"
        target.write_bytes(encoded)
        return cid

    def get_json(self, cid):
        matches = list(self.root.glob(f"{cid}*"))
        if not matches:
            raise FileNotFoundError(f"CID not found in content store: {cid}")
        return json.loads(matches[0].read_text())


class EthicalLedger:
    def __init__(self):
        self.nodes = {}
        self.records = []
        self.audit_events = []
        self.seen = set()

    def register_node(self, node_id):
        self.nodes[str(node_id)] = {
            "node_id": node_id,
            "registered_at_ms": now_ms(),
            "status": "Registered",
        }

    def register_local_model(self, request):
        key = (request["node_id"], request["round_id"])
        conditions = [
            str(request["node_id"]) in self.nodes,
            request["round_id"] == ROUND_ID,
            key not in self.seen,
            all(str(request["cids"][field]).startswith("sha256-") for field in ["model", "metrics", "metadata", "proof", "public"]),
            request["proof_verified"] is True,
        ]

        verification_status = "Valid" if all(conditions) else "Invalid"
        approval_status = "Approved" if verification_status == "Valid" else "Rejected"
        tx_hash = sha256_bytes(stable_json({"request": request, "ts": now_ms()}))
        record = {
            **request,
            "verification_status": verification_status,
            "approval_status": approval_status,
            "tx_hash": f"0x{tx_hash}",
            "block_number": len(self.audit_events) + 1,
            "timestamp_ms": now_ms(),
        }

        self.seen.add(key)
        self.records.append(record)
        self.audit_events.append({
            "event": "AuditLogged",
            "node_id": request["node_id"],
            "round_id": request["round_id"],
            "verification_status": verification_status,
            "approval_status": approval_status,
            "tx_hash": record["tx_hash"],
        })
        return record

    def eligible_models(self, round_id):
        return [
            record for record in self.records
            if record["round_id"] == round_id and record["approval_status"] == "Approved"
        ]

    def log_global_model(self, round_id, global_model_cid, report_cid, participant_nodes):
        tx_hash = sha256_bytes(stable_json({
            "round_id": round_id,
            "global_model_cid": global_model_cid,
            "report_cid": report_cid,
            "participants": participant_nodes,
            "ts": now_ms(),
        }))
        event = {
            "event": "GlobalModelPublished",
            "round_id": round_id,
            "global_model_cid": global_model_cid,
            "report_cid": report_cid,
            "participant_nodes": participant_nodes,
            "tx_hash": f"0x{tx_hash}",
            "block_number": len(self.audit_events) + 1,
            "timestamp_ms": now_ms(),
        }
        self.audit_events.append(event)
        return event

    def to_dict(self):
        return {
            "nodes": self.nodes,
            "records": self.records,
            "audit_events": self.audit_events,
        }


def generate_partition(node_id, size):
    rng = random.Random(1000 + node_id)
    data = []
    for _ in range(size):
        group = 1 if rng.random() < (0.50 if node_id != 3 else 0.70) else 0
        shift = 0.10 * group
        if node_id == 3:
            shift = 0.95 * group
        x1 = rng.gauss(0.0 + shift, 1.0)
        x2 = rng.gauss(0.0, 1.0)
        latent = -0.20 + 1.35 * x1 - 0.85 * x2 + rng.gauss(0, 0.35)
        label = 1 if sigmoid(latent) >= 0.5 else 0
        data.append(Example(x1=x1, x2=x2, group=group, label=label))
    return data


def generate_validation(size):
    rng = random.Random(4242)
    data = []
    for _ in range(size):
        group = 1 if rng.random() < 0.50 else 0
        x1 = rng.gauss(0.10 * group, 1.0)
        x2 = rng.gauss(0.0, 1.0)
        latent = -0.20 + 1.35 * x1 - 0.85 * x2 + rng.gauss(0, 0.35)
        label = 1 if sigmoid(latent) >= 0.5 else 0
        data.append(Example(x1=x1, x2=x2, group=group, label=label))
    return data


def train_logistic(data, epochs=240, learning_rate=0.10):
    weights = [0.0, 0.0, 0.0]
    n = len(data)
    for _ in range(epochs):
        grad = [0.0, 0.0, 0.0]
        for row in data:
            features = [1.0, row.x1, row.x2]
            pred = sigmoid(sum(w * x for w, x in zip(weights, features)))
            err = pred - row.label
            for i in range(3):
                grad[i] += err * features[i]
        for i in range(3):
            weights[i] -= learning_rate * grad[i] / n
    return [round(w, 6) for w in weights]


def predict(weights, row):
    return 1 if sigmoid(weights[0] + weights[1] * row.x1 + weights[2] * row.x2) >= 0.5 else 0


def evaluate(weights, data):
    correct = 0
    by_group = {0: {"pred_pos": 0, "count": 0, "tp": 0, "actual_pos": 0}, 1: {"pred_pos": 0, "count": 0, "tp": 0, "actual_pos": 0}}

    for row in data:
        pred = predict(weights, row)
        correct += 1 if pred == row.label else 0
        group_stats = by_group[row.group]
        group_stats["count"] += 1
        group_stats["pred_pos"] += pred
        group_stats["actual_pos"] += row.label
        group_stats["tp"] += 1 if pred == 1 and row.label == 1 else 0

    pos_rates = {
        group: stats["pred_pos"] / stats["count"] if stats["count"] else 0.0
        for group, stats in by_group.items()
    }
    tpr = {
        group: stats["tp"] / stats["actual_pos"] if stats["actual_pos"] else 0.0
        for group, stats in by_group.items()
    }
    return {
        "accuracy": round(correct / len(data), 6),
        "demographic_parity_gap": round(abs(pos_rates[0] - pos_rates[1]), 6),
        "equal_opportunity_gap": round(abs(tpr[0] - tpr[1]), 6),
        "positive_rate_group_0": round(pos_rates[0], 6),
        "positive_rate_group_1": round(pos_rates[1], 6),
        "correct": correct,
        "group_0_pred_positive": by_group[0]["pred_pos"],
        "group_0_count": by_group[0]["count"],
        "group_1_pred_positive": by_group[1]["pred_pos"],
        "group_1_count": by_group[1]["count"],
        "samples": len(data),
    }


def require_tool(name):
    if not shutil.which(name):
        raise RuntimeError(f"Required tool not found on PATH: {name}")


def run_command(args, cwd=ROOT, env=None):
    completed = subprocess.run(args, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(args)}\n{completed.stdout}")
    return completed.stdout


def run_contract_round(output_dir, submissions, global_publication=None, verifier_mode="groth16"):
    hardhat_dir = ROOT / "hardhat"
    input_path = output_dir / "contract_input.json"
    output_path = output_dir / "contract_result.json"
    contract_input = {
        "round_id": ROUND_ID,
        "verifier_mode": verifier_mode,
        "submissions": submissions,
    }
    if global_publication:
        contract_input["global_publication"] = global_publication
    input_path.write_text(json.dumps(contract_input, indent=2, sort_keys=True))

    env = {
        **__import__("os").environ,
        "FAIRAI_CONTRACT_INPUT": str(input_path),
        "FAIRAI_CONTRACT_OUTPUT": str(output_path),
    }
    run_command(["npx", "hardhat", "run", "scripts/run_round.js"], cwd=hardhat_dir, env=env)
    return json.loads(output_path.read_text())


def setup_zk(force=False):
    require_tool("circom")
    require_tool("snarkjs")
    if not DEFAULT_PTAU.exists():
        raise FileNotFoundError(f"Missing Powers of Tau file: {DEFAULT_PTAU}")

    r1cs = BUILD_DIR / "FairnessEligibility.r1cs"
    zkey = BUILD_DIR / "FairnessEligibility_final.zkey"
    vkey = BUILD_DIR / "FairnessEligibility_vkey.json"

    if force and BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    if force:
        for stray in [ROOT / "FairnessEligibility.r1cs", ROOT / "FairnessEligibility.wasm", ROOT / "FairnessEligibility.sym"]:
            if stray.exists():
                stray.unlink()
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    def find_wasm():
        candidates = [
            BUILD_DIR / "FairnessEligibility.wasm",
            BUILD_DIR / "FairnessEligibility_js" / "FairnessEligibility.wasm",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    wasm = find_wasm()
    if not wasm.exists() or not r1cs.exists():
        run_command(["circom", str(CIRCUIT), "--r1cs", "--wasm", "--sym"], cwd=BUILD_DIR)
        wasm = find_wasm()

    if not zkey.exists() or not vkey.exists():
        initial = BUILD_DIR / "FairnessEligibility_0000.zkey"
        run_command(["snarkjs", "groth16", "setup", str(r1cs), str(DEFAULT_PTAU), str(initial)])
        run_command([
            "snarkjs", "zkey", "contribute", str(initial), str(zkey),
            "--name=FairAI MVP", "-v", "-e=fairai-mvp-deterministic-demo",
        ])
        run_command(["snarkjs", "zkey", "export", "verificationkey", str(zkey), str(vkey)])

    return {"wasm": wasm, "zkey": zkey, "vkey": vkey}


def prove_eligibility(node_dir, metrics, node_id, zk_paths):
    input_payload = {
        "accuracy_in": int(round(metrics["accuracy"] * SCALE)),
        "fairness_gap_in": int(round(metrics["demographic_parity_gap"] * SCALE)),
        "min_accuracy_in": int(round(MIN_ACCURACY * SCALE)),
        "max_gap_in": int(round(MAX_FAIRNESS_GAP * SCALE)),
        "node_id_in": node_id,
        "round_id_in": ROUND_ID,
    }
    input_file = node_dir / "proof_input.json"
    witness_file = node_dir / "witness.wtns"
    proof_file = node_dir / "proof.json"
    public_file = node_dir / "public.json"
    input_file.write_text(json.dumps(input_payload, indent=2, sort_keys=True))

    try:
        run_command(["snarkjs", "wtns", "calculate", str(zk_paths["wasm"]), str(input_file), str(witness_file)])
        run_command(["snarkjs", "wtns", "check", str(BUILD_DIR / "FairnessEligibility.r1cs"), str(witness_file)])
        run_command(["snarkjs", "groth16", "prove", str(zk_paths["zkey"]), str(witness_file), str(proof_file), str(public_file)])
        verify_output = run_command(["snarkjs", "groth16", "verify", str(zk_paths["vkey"]), str(public_file), str(proof_file)])
        verified = "OK" in verify_output.upper()
    except RuntimeError as exc:
        (node_dir / "proof_error.txt").write_text(str(exc))
        proof_file.write_text(json.dumps({"error": "eligibility constraints not satisfied"}, indent=2))
        public_file.write_text(json.dumps([], indent=2))
        verified = False

    return {
        "input": input_payload,
        "proof_path": proof_file,
        "public_path": public_file,
        "verified": verified,
    }


def mock_contract_public_signals(metrics, proof_payload, node_id):
    proof_digest = int(sha256_bytes(stable_json(proof_payload)), 16)
    return [str(value) for value in [
        int(round(metrics["accuracy"] * SCALE)),
        int(round(metrics["demographic_parity_gap"] * SCALE)),
        int(round(MIN_ACCURACY * SCALE)),
        int(round(MAX_FAIRNESS_GAP * SCALE)),
        int(metrics["correct"]),
        int(metrics["samples"]),
        int(metrics["group_0_pred_positive"]),
        int(metrics["group_0_count"]),
        int(metrics["group_1_pred_positive"]),
        int(metrics["group_1_count"]),
        int(node_id),
        int(ROUND_ID),
        proof_digest,
    ]]


def groth16_contract_proof(proof_payload):
    if not all(key in proof_payload for key in ["pi_a", "pi_b", "pi_c"]):
        return None
    return {
        "pA": [proof_payload["pi_a"][0], proof_payload["pi_a"][1]],
        "pB": [
            [proof_payload["pi_b"][0][1], proof_payload["pi_b"][0][0]],
            [proof_payload["pi_b"][1][1], proof_payload["pi_b"][1][0]],
        ],
        "pC": [proof_payload["pi_c"][0], proof_payload["pi_c"][1]],
    }


def groth16_public_signals(public_payload):
    if len(public_payload) != 12:
        return ["0"] * 12
    return [str(value) for value in public_payload]


def aggregate_models(models):
    total = sum(model["samples"] for model in models)
    if total == 0:
        raise ValueError("Cannot aggregate zero models")
    weights = [0.0, 0.0, 0.0]
    for model in models:
        for i, value in enumerate(model["weights"]):
            weights[i] += value * model["samples"] / total
    return [round(value, 6) for value in weights]


def write_report(output_dir, summary):
    lines = [
        "# FairAI MVP Run Report",
        "",
        f"- round_id: {summary['round_id']}",
        f"- nodes: {summary['nodes_total']}",
        f"- approved_nodes: {summary['approved_nodes']}",
        f"- rejected_nodes: {summary['rejected_nodes']}",
        f"- contract_network: {summary['contract_network']}",
        f"- contract_address: `{summary['contract_address']}`",
        f"- global_model_cid: `{summary['global_model_cid']}`",
        f"- global_publication_tx: `{summary['global_publication']['tx_hash']}`",
        f"- final_round_state: {summary['final_round_state']}",
        f"- ledger_events: {summary['ledger_events']}",
        f"- ipfs_mode: {summary['ipfs_mode']}",
        "",
        "## Policy",
        "",
        f"- minimum local accuracy: {MIN_ACCURACY:.2f}",
        f"- maximum demographic parity gap: {MAX_FAIRNESS_GAP:.2f}",
        "",
        "## Local Results",
        "",
        "| Node | Accuracy | DP Gap | ZK Verified | Approval | Model CID |",
        "|---:|---:|---:|:---:|:---:|---|",
    ]
    for node in summary["node_results"]:
        lines.append(
            f"| {node['node_id']} | {node['accuracy']:.3f} | {node['demographic_parity_gap']:.3f} | "
            f"{node['proof_verified']} | {node['approval_status']} | `{node['model_cid']}` |"
        )
    lines.extend([
        "",
        "## Global Model",
        "",
        f"- participants: {summary['global_model']['participant_nodes']}",
        f"- validation accuracy: {summary['global_model']['validation_metrics']['accuracy']:.3f}",
        f"- validation demographic parity gap: {summary['global_model']['validation_metrics']['demographic_parity_gap']:.3f}",
        f"- report CID: `{summary['report_cid']}`",
    ])
    (output_dir / "report.md").write_text("\n".join(lines) + "\n")


def run_pipeline(output_dir, force_zk=False, require_real_ipfs=False):
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    zk_paths = setup_zk(force=force_zk)
    store = IPFSAdapter(output_dir / "ipfs", prefer_real_ipfs=True)
    if require_real_ipfs and store.mode == "local-content-addressed":
        raise RuntimeError(
            "Real IPFS was required, but Kubo HTTP/API or ipfs CLI was unavailable. "
            "Start Docker Kubo and set FAIRAI_IPFS_API=http://127.0.0.1:5001."
        )
    node_results = []
    metrics_csv_rows = []
    contract_submissions = []
    instrumentation = {
        "proof_generation_ms": [],
        "ipfs_retrieval_checks": [],
        "ipfs_pin_results": [],
    }
    for node_id in range(1, NUM_NODES + 1):
        node_dir = output_dir / f"node_{node_id}"
        node_dir.mkdir(parents=True, exist_ok=True)
        data = generate_partition(node_id, SAMPLES_PER_NODE)
        weights = train_logistic(data)
        metrics = evaluate(weights, data)
        model_payload = {
            "node_id": node_id,
            "round_id": ROUND_ID,
            "type": "logistic_regression",
            "features": ["bias", "x1", "x2"],
            "weights": weights,
            "samples": len(data),
        }
        metadata_payload = {
            "node_id": node_id,
            "round_id": ROUND_ID,
            "samples": len(data),
            "policy": {
                "min_accuracy": MIN_ACCURACY,
                "max_demographic_parity_gap": MAX_FAIRNESS_GAP,
            },
            "privacy_note": "raw records remain local; only model, metrics, proof, and metadata artifacts are published",
        }

        (node_dir / "local_model.json").write_text(json.dumps(model_payload, indent=2, sort_keys=True))
        (node_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True))
        (node_dir / "metadata.json").write_text(json.dumps(metadata_payload, indent=2, sort_keys=True))
        proof_started = time.time()
        proof = prove_eligibility(node_dir, metrics, node_id, zk_paths)
        instrumentation["proof_generation_ms"].append(round((time.time() - proof_started) * 1000, 3))

        proof_payload = json.loads(proof["proof_path"].read_text())
        public_payload = json.loads(proof["public_path"].read_text())
        cids = {
            "model": store.put_json("local_model.json", model_payload),
            "metrics": store.put_json("metrics.json", metrics),
            "metadata": store.put_json("metadata.json", metadata_payload),
            "proof": store.put_json("proof.json", proof_payload),
            "public": store.put_json("public.json", public_payload),
        }
        manifest_payload = {
            "schema_version": "fairai.node_manifest.v1",
            "node_id": node_id,
            "round_id": ROUND_ID,
            "artifacts": cids,
            "proof_verified_locally": proof["verified"],
            "metrics_summary": {
                "accuracy": metrics["accuracy"],
                "demographic_parity_gap": metrics["demographic_parity_gap"],
                "equal_opportunity_gap": metrics["equal_opportunity_gap"],
            },
            "policy": {
                "min_accuracy": MIN_ACCURACY,
                "max_demographic_parity_gap": MAX_FAIRNESS_GAP,
            },
        }
        (node_dir / "manifest.json").write_text(json.dumps(manifest_payload, indent=2, sort_keys=True))
        cids["manifest"] = store.put_json("manifest.json", manifest_payload)
        instrumentation["ipfs_retrieval_checks"].append(
            store.validate_json(cids["manifest"], required_keys=["schema_version", "artifacts", "node_id", "round_id"])
        )
        instrumentation["ipfs_pin_results"].append(store.pin(cids["manifest"]))
        submission = {
            "node_id": node_id,
            "round_id": ROUND_ID,
            "cids": cids,
            "metrics": metrics,
            "proof_verified": proof["verified"],
            "zk_public_inputs": proof["input"],
            "contract_proof": stable_json(proof_payload).hex(),
            "contract_public_signals": groth16_public_signals(public_payload),
            "mock_contract_public_signals": mock_contract_public_signals(metrics, proof_payload, node_id),
            "groth16_proof": groth16_contract_proof(proof_payload),
        }
        contract_submissions.append(submission)

        node_summary = {
            "node_id": node_id,
            "accuracy": metrics["accuracy"],
            "demographic_parity_gap": metrics["demographic_parity_gap"],
            "equal_opportunity_gap": metrics["equal_opportunity_gap"],
            "proof_verified": proof["verified"],
            "approval_status": "PendingContract",
            "model_cid": cids["model"],
            "proof_cid": cids["proof"],
            "public_cid": cids["public"],
            "manifest_cid": cids["manifest"],
            "tx_hash": "",
        }
        node_results.append(node_summary)
        metrics_csv_rows.append(node_summary)

    expected_eligible_model_cids = [
        submission["cids"]["model"]
        for submission in contract_submissions
        if submission["proof_verified"]
    ]
    for cid in expected_eligible_model_cids:
        instrumentation["ipfs_retrieval_checks"].append(
            store.validate_json(cid, required_keys=["node_id", "round_id", "weights", "samples"])
        )
        instrumentation["ipfs_pin_results"].append(store.pin(cid))
    approved_models = [store.get_json(cid) for cid in expected_eligible_model_cids]
    global_weights = aggregate_models(approved_models)
    validation_metrics = evaluate(global_weights, generate_validation(VALIDATION_SAMPLES))
    global_model = {
        "round_id": ROUND_ID,
        "type": "logistic_regression",
        "aggregation": "FedAvg weighted by local sample count",
        "participant_nodes": [model["node_id"] for model in approved_models],
        "participant_model_cids": expected_eligible_model_cids,
        "weights": global_weights,
        "validation_metrics": validation_metrics,
    }
    global_model_cid = store.put_json("global_model.json", global_model)
    instrumentation["ipfs_retrieval_checks"].append(
        store.validate_json(global_model_cid, required_keys=["round_id", "weights", "validation_metrics"])
    )
    instrumentation["ipfs_pin_results"].append(store.pin(global_model_cid))

    result_table = {
        "schema_version": "fairai.round_report.v1",
        "round_id": ROUND_ID,
        "policy": {
            "min_accuracy": MIN_ACCURACY,
            "max_demographic_parity_gap": MAX_FAIRNESS_GAP,
        },
        "node_results": node_results,
        "global_model": global_model,
    }
    report_cid = store.put_json("audit_report.json", result_table)
    instrumentation["ipfs_retrieval_checks"].append(
        store.validate_json(report_cid, required_keys=["schema_version", "round_id", "node_results", "global_model"])
    )
    instrumentation["ipfs_pin_results"].append(store.pin(report_cid))
    contract_result = run_contract_round(
        output_dir,
        contract_submissions,
        {
            "global_model_cid": global_model_cid,
            "report_cid": report_cid,
            "participant_model_cids": expected_eligible_model_cids,
        },
        verifier_mode="signed",
    )
    records_by_node = {record["node_id"]: record for record in contract_result["records"]}
    for node_summary in node_results:
        record = records_by_node[node_summary["node_id"]]
        node_summary["approval_status"] = record["approval_status"]
        node_summary["verification_status"] = record["verification_status"]
        node_summary["tx_hash"] = record["tx_hash"]
        node_summary["block_number"] = record["block_number"]
        node_summary["gas_used"] = record["gas_used"]

    metrics_csv_rows = node_results
    if sorted(contract_result["eligible_model_cids"]) != sorted(expected_eligible_model_cids):
        raise RuntimeError("Contract eligible CIDs diverged from local eligibility inputs")
    summary = {
        "round_id": ROUND_ID,
        "nodes_total": NUM_NODES,
        "approved_nodes": len(approved_models),
        "rejected_nodes": NUM_NODES - len(approved_models),
        "node_results": node_results,
        "global_model": global_model,
        "global_model_cid": global_model_cid,
        "report_cid": report_cid,
        "contract_address": contract_result["contract_address"],
        "contract_network": contract_result["network"],
        "global_publication": contract_result["global_publication"],
        "final_round_state": contract_result["final_round_state"],
        "round_events": contract_result["round_events"],
        "ledger_events": len(contract_result["audit_events"]),
        "ipfs_mode": store.mode,
        "instrumentation": instrumentation,
    }

    (output_dir / "ledger.json").write_text(json.dumps(contract_result, indent=2, sort_keys=True))
    (output_dir / "run_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    (output_dir / "global_model.json").write_text(json.dumps(global_model, indent=2, sort_keys=True))

    with (output_dir / "metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "node_id", "accuracy", "demographic_parity_gap", "equal_opportunity_gap",
            "proof_verified", "verification_status", "approval_status", "model_cid", "proof_cid",
            "public_cid", "manifest_cid", "tx_hash", "block_number", "gas_used",
        ])
        writer.writeheader()
        writer.writerows(metrics_csv_rows)

    write_report(output_dir, summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description="Run a small end-to-end FairAI MVP.")
    parser.add_argument("--output", default=str(ROOT / "runs" / "latest"), help="Output directory for artifacts and results.")
    parser.add_argument("--force-zk", action="store_true", help="Rebuild circuit artifacts and proving keys.")
    parser.add_argument("--require-real-ipfs", action="store_true", help="Fail if Kubo/IPFS is unavailable instead of using local SHA-256 fallback.")
    args = parser.parse_args()
    summary = run_pipeline(Path(args.output), force_zk=args.force_zk, require_real_ipfs=args.require_real_ipfs)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
