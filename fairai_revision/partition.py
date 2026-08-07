import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .config import canonical_json_bytes
from .data import DatasetSplits, load_adult, load_compas


PARTITION_MODES = {"iid", "label_dirichlet", "joint_dirichlet"}


class PartitionError(ValueError):
    pass


def parse_partition_spec(spec):
    if spec == "iid":
        return "iid", None
    for mode in ("label_dirichlet", "joint_dirichlet"):
        prefix = f"{mode}_"
        if spec.startswith(prefix):
            try:
                alpha = float(spec[len(prefix) :])
            except ValueError as exc:
                raise PartitionError(f"Invalid Dirichlet alpha in {spec}") from exc
            if not np.isfinite(alpha) or alpha <= 0:
                raise PartitionError(f"Dirichlet alpha must be positive in {spec}")
            return mode, alpha
    raise PartitionError(f"Unsupported partition specification: {spec}")


@dataclass(frozen=True)
class PartitionResult:
    mode: str
    client_indices: tuple
    seed: int
    alpha: float | None
    minimum_samples: int
    checksum: str
    attempts: int

    @property
    def client_count(self):
        return len(self.client_indices)

    @property
    def sample_count(self):
        return sum(len(indices) for indices in self.client_indices)


def _validate_inputs(labels, protected, client_count, minimum_samples, mode, alpha):
    labels = np.asarray(labels)
    protected = np.asarray(protected)
    if labels.ndim != 1 or protected.ndim != 1:
        raise PartitionError("labels and protected values must be one-dimensional")
    if len(labels) != len(protected):
        raise PartitionError("labels and protected values must have equal length")
    if mode not in PARTITION_MODES:
        raise PartitionError(f"Unsupported partition mode: {mode}")
    if client_count < 1:
        raise PartitionError("client_count must be positive")
    if minimum_samples < 1:
        raise PartitionError("minimum_samples must be positive")
    if len(labels) < client_count * minimum_samples:
        raise PartitionError(
            "Dataset cannot satisfy client_count * minimum_samples "
            f"({len(labels)} < {client_count * minimum_samples})"
        )
    if mode != "iid" and (alpha is None or not np.isfinite(alpha) or alpha <= 0):
        raise PartitionError("Dirichlet modes require a finite alpha greater than zero")
    return labels, protected


def _canonical_checksum(mode, client_indices, seed, alpha, minimum_samples):
    payload = {
        "schema_version": "fairai.partition.v1",
        "mode": mode,
        "seed": seed,
        "alpha": alpha,
        "minimum_samples": minimum_samples,
        "clients": {
            str(client_id): sorted(int(index) for index in indices)
            for client_id, indices in enumerate(client_indices)
        },
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _validate_partition(client_indices, sample_count, minimum_samples):
    flat = np.concatenate(client_indices) if client_indices else np.array([], dtype=int)
    if len(flat) != sample_count:
        raise PartitionError("Partition does not cover every sample exactly once")
    if len(np.unique(flat)) != sample_count:
        raise PartitionError("Partition contains duplicate sample indices")
    if set(flat.tolist()) != set(range(sample_count)):
        raise PartitionError("Partition indices do not match the input sample range")
    if any(len(indices) < minimum_samples for indices in client_indices):
        raise PartitionError("Partition violates minimum_samples")


def _iid_partition(sample_count, client_count, rng):
    shuffled = rng.permutation(sample_count)
    return tuple(np.sort(indices).astype(int) for indices in np.array_split(shuffled, client_count))


def _dirichlet_partition(strata, client_count, alpha, rng):
    clients = [[] for _ in range(client_count)]
    for value in sorted(pd.unique(strata), key=str):
        stratum_indices = np.flatnonzero(strata == value)
        rng.shuffle(stratum_indices)
        proportions = rng.dirichlet(np.full(client_count, alpha, dtype=float))
        counts = rng.multinomial(len(stratum_indices), proportions)
        offset = 0
        for client_id, count in enumerate(counts):
            clients[client_id].extend(stratum_indices[offset : offset + count].tolist())
            offset += count
    return tuple(np.asarray(sorted(indices), dtype=int) for indices in clients)


def partition_clients(
    labels,
    protected,
    client_count,
    mode,
    seed,
    alpha=None,
    minimum_samples=1,
    max_attempts=1000,
):
    labels, protected = _validate_inputs(
        labels, protected, client_count, minimum_samples, mode, alpha
    )
    if max_attempts < 1:
        raise PartitionError("max_attempts must be positive")
    rng = np.random.default_rng(seed)
    if mode == "iid":
        client_indices = _iid_partition(len(labels), client_count, rng)
        attempts = 1
    else:
        strata = labels if mode == "label_dirichlet" else np.asarray(
            [f"{label}|{group}" for label, group in zip(labels, protected)]
        )
        for attempts in range(1, max_attempts + 1):
            candidate = _dirichlet_partition(strata, client_count, alpha, rng)
            if all(len(indices) >= minimum_samples for indices in candidate):
                client_indices = candidate
                break
        else:
            raise PartitionError(
                f"Could not satisfy minimum_samples={minimum_samples} after "
                f"{max_attempts} deterministic attempts"
            )
    _validate_partition(client_indices, len(labels), minimum_samples)
    checksum = _canonical_checksum(
        mode, client_indices, seed, alpha, minimum_samples
    )
    return PartitionResult(
        mode=mode,
        client_indices=client_indices,
        seed=seed,
        alpha=alpha,
        minimum_samples=minimum_samples,
        checksum=checksum,
        attempts=attempts,
    )


def normalized_entropy(values, categories=None):
    values = np.asarray(values)
    category_values = list(categories) if categories is not None else list(pd.unique(values))
    category_count = len(category_values)
    if category_count <= 1 or len(values) == 0:
        return 0.0
    counts = np.asarray([(values == category).sum() for category in category_values], dtype=float)
    probabilities = counts[counts > 0] / len(values)
    entropy = float(
        -(probabilities * np.log(probabilities)).sum() / math.log(category_count)
    )
    return max(0.0, entropy)


def source_entropy(client_indices):
    sizes = np.asarray([len(indices) for indices in client_indices], dtype=float)
    if len(sizes) <= 1 or sizes.sum() == 0:
        return 0.0
    probabilities = sizes[sizes > 0] / sizes.sum()
    return float(-(probabilities * np.log(probabilities)).sum() / math.log(len(sizes)))


def entropy_records(result, labels, protected):
    labels = np.asarray(labels)
    protected = np.asarray(protected)
    label_categories = sorted(pd.unique(labels).tolist(), key=str)
    group_categories = sorted(pd.unique(protected).tolist(), key=str)
    records = []
    for client_id, indices in enumerate(result.client_indices):
        local_labels = labels[indices]
        local_groups = protected[indices]
        label_counts = {
            str(category): int((local_labels == category).sum())
            for category in label_categories
        }
        group_counts = {
            str(category): int((local_groups == category).sum())
            for category in group_categories
        }
        joint_counts = {}
        for label, group in zip(local_labels, local_groups):
            key = f"{label}|{group}"
            joint_counts[key] = joint_counts.get(key, 0) + 1
        records.append(
            {
                "client_id": client_id,
                "sample_count": len(indices),
                "label_entropy": normalized_entropy(local_labels, label_categories),
                "group_entropy": normalized_entropy(local_groups, group_categories),
                "label_distribution": json.dumps(label_counts, sort_keys=True),
                "group_distribution": json.dumps(group_counts, sort_keys=True),
                "joint_distribution": json.dumps(joint_counts, sort_keys=True),
            }
        )
    return records


def _write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_partition_evidence(output_dir, result, labels, protected):
    output_dir = Path(output_dir)
    records = entropy_records(result, labels, protected)
    _write_csv(
        output_dir / "entropy_by_client.csv",
        list(records[0]),
        records,
    )
    entropy_summary = []
    for metric in ("label_entropy", "group_entropy"):
        values = np.asarray([record[metric] for record in records], dtype=float)
        entropy_summary.append(
            {
                "metric": metric,
                "mean": float(values.mean()),
                "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
                "minimum": float(values.min()),
                "maximum": float(values.max()),
            }
        )
    entropy_summary.append(
        {
            "metric": "source_entropy",
            "mean": source_entropy(result.client_indices),
            "std": "",
            "minimum": "",
            "maximum": "",
        }
    )
    _write_csv(
        output_dir / "entropy_summary.csv",
        ["metric", "mean", "std", "minimum", "maximum"],
        entropy_summary,
    )
    _write_csv(
        output_dir / "partition_summary.csv",
        [
            "mode",
            "alpha",
            "seed",
            "client_count",
            "sample_count",
            "minimum_samples",
            "attempts",
            "partition_checksum",
        ],
        [
            {
                "mode": result.mode,
                "alpha": "" if result.alpha is None else result.alpha,
                "seed": result.seed,
                "client_count": result.client_count,
                "sample_count": result.sample_count,
                "minimum_samples": result.minimum_samples,
                "attempts": result.attempts,
                "partition_checksum": result.checksum,
            }
        ],
    )
    correlation_rows = [
        {
            "entropy_metric": entropy_metric,
            "outcome": outcome,
            "status": "undefined",
            "coefficient": "",
            "reason": "outcome is produced by the later training and fairness experiment phase",
        }
        for entropy_metric in ("label_entropy", "group_entropy")
        for outcome in ("accuracy", "dp_gap", "eo_gap", "approval", "client_exclusion")
    ]
    _write_csv(
        output_dir / "entropy_correlations.csv",
        ["entropy_metric", "outcome", "status", "coefficient", "reason"],
        correlation_rows,
    )
    return {
        "partition_checksum": result.checksum,
        "source_entropy": source_entropy(result.client_indices),
        "files": sorted(path.name for path in output_dir.glob("*.csv")),
    }


def _load_dataset(name, raw_root, seed):
    raw_root = Path(raw_root)
    if name == "adult":
        return load_adult(raw_root / "adult", seed=seed)
    if name == "compas":
        return load_compas(raw_root / "compas" / "compas-scores-two-years.csv", seed=seed)
    raise PartitionError(f"Unsupported dataset: {name}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate deterministic client partitions")
    parser.add_argument("--dataset", choices=["adult", "compas"], required=True)
    parser.add_argument("--raw-root", default="data/raw")
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=sorted(PARTITION_MODES), required=True)
    parser.add_argument("--clients", type=int, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--alpha", type=float)
    parser.add_argument("--minimum-samples", type=int, default=50)
    args = parser.parse_args(argv)
    dataset: DatasetSplits = _load_dataset(args.dataset, args.raw_root, args.seed)
    protected = dataset.train.protected[dataset.primary_protected_attribute].to_numpy()
    result = partition_clients(
        dataset.train.labels,
        protected,
        client_count=args.clients,
        mode=args.mode,
        seed=args.seed,
        alpha=args.alpha,
        minimum_samples=args.minimum_samples,
    )
    summary = export_partition_evidence(
        args.output, result, dataset.train.labels, protected
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
