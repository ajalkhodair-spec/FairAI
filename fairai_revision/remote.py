import json
import shlex
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np


class RemoteTrainingError(RuntimeError):
    pass


def validate_remote_topology(topology, require_kubo=True):
    if topology.get("schema_version") != "fairai.azure_topology.v1":
        raise RemoteTrainingError("Unsupported remote topology schema")
    for field in ("ssh_user", "ssh_key"):
        if not isinstance(topology.get(field), str) or not topology[field].strip():
            raise RemoteTrainingError(f"Remote topology requires {field}")
    workers = topology.get("workers")
    if not isinstance(workers, list) or len(workers) < 2:
        raise RemoteTrainingError("Remote topology requires at least two workers")
    names = []
    hosts = []
    for worker in workers:
        if not isinstance(worker, dict):
            raise RemoteTrainingError("Each remote worker must be an object")
        name = worker.get("name")
        host = worker.get("host")
        if not isinstance(name, str) or not name.strip():
            raise RemoteTrainingError("Each remote worker requires a name")
        if not isinstance(host, str) or not host.strip():
            raise RemoteTrainingError("Each remote worker requires a host")
        if any(character.isspace() for character in host):
            raise RemoteTrainingError("Remote worker hosts cannot contain whitespace")
        names.append(name)
        hosts.append(host)
    if len(set(names)) != len(names) or len(set(hosts)) != len(hosts):
        raise RemoteTrainingError("Remote worker names and hosts must be unique")
    if require_kubo:
        for field in ("kubo_publisher_api", "kubo_consumer_api"):
            value = topology.get(field)
            if not isinstance(value, str) or not value.startswith("http://"):
                raise RemoteTrainingError(
                    f"Remote topology requires a private HTTP {field} endpoint"
                )
        if topology["kubo_publisher_api"] == topology["kubo_consumer_api"]:
            raise RemoteTrainingError("Kubo publisher and consumer endpoints must differ")
    return topology


def balanced_client_assignment(client_count, workers):
    workers = list(workers)
    if client_count < 1 or len(workers) < 2:
        raise RemoteTrainingError("Remote execution requires clients and at least two workers")
    return {str(client_id): workers[client_id % len(workers)] for client_id in range(client_count)}


class SSHRemoteTrainer:
    def __init__(self, topology, output_dir):
        self.topology = validate_remote_topology(topology)
        self.output_dir = Path(output_dir)
        self.workers = self.topology["workers"]
        self.assignment = {}
        self.communication_rows = []
        self.remote_root = self.topology.get("remote_root", "/opt/fairai")
        self.python = self.topology.get("python", "/opt/fairai/.venv/bin/python")
        self.ssh_user = self.topology["ssh_user"]
        self.ssh_key = self.topology["ssh_key"]
        if not Path(self.ssh_key).is_file():
            raise RemoteTrainingError(f"SSH key does not exist: {self.ssh_key}")

    def _target(self, worker_name):
        worker = next(item for item in self.workers if item["name"] == worker_name)
        return f"{self.ssh_user}@{worker['host']}"

    def _ssh_base(self):
        return [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-i",
            self.ssh_key,
        ]

    def prepare(self, prepared, local_splits):
        self.assignment = balanced_client_assignment(len(local_splits), [item["name"] for item in self.workers])
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for client_id, (train_indices, evaluation_indices) in enumerate(local_splits):
                worker_name = self.assignment[str(client_id)]
                target = self._target(worker_name)
                remote_dir = f"{self.remote_root}/runtime/clients"
                subprocess.run(
                    [
                        *self._ssh_base(),
                        target,
                        f"mkdir -p -- {shlex.quote(remote_dir)}",
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                bundle = tmp / f"client_{client_id}.npz"
                np.savez_compressed(
                    bundle,
                    train_features=prepared.train_features[train_indices],
                    train_labels=prepared.train_labels[train_indices],
                    evaluation_features=prepared.train_features[evaluation_indices],
                    evaluation_labels=prepared.train_labels[evaluation_indices],
                    evaluation_protected=prepared.train_protected[evaluation_indices].astype(str),
                )
                started = time.perf_counter()
                completed = subprocess.run(
                    [
                        "scp",
                        "-o",
                        "BatchMode=yes",
                        "-o",
                        "StrictHostKeyChecking=yes",
                        "-i",
                        self.ssh_key,
                        str(bundle),
                        f"{target}:{remote_dir}/client_{client_id}.npz",
                    ],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                if completed.returncode != 0:
                    raise RemoteTrainingError(completed.stdout)
                self.communication_rows.append(
                    {
                        "operation": "stage_partition",
                        "client_id": client_id,
                        "worker": worker_name,
                        "bytes": bundle.stat().st_size,
                        "runtime_ms": (time.perf_counter() - started) * 1000,
                    }
                )

    def train(
        self,
        client_id,
        round_id,
        global_parameters,
        model_type,
        seed,
        local_epochs,
        dataset,
        minimum_group_samples,
        label_flip,
        operation="train",
    ):
        worker_name = self.assignment[str(client_id)]
        target = self._target(worker_name)
        request = {
            "schema_version": "fairai.remote_training_request.v1",
            "client_id": client_id,
            "round_id": round_id,
            "global_parameters": [np.asarray(value).tolist() for value in global_parameters],
            "model_type": model_type,
            "seed": seed,
            "local_epochs": local_epochs,
            "privileged_value": str(dataset.privileged_value),
            "unprivileged_value": str(dataset.unprivileged_value),
            "favorable_label": int(dataset.favorable_label),
            "minimum_group_samples": minimum_group_samples,
            "label_flip": label_flip,
            "operation": operation,
        }
        payload = json.dumps(request, sort_keys=True, separators=(",", ":"))
        command = [
            *self._ssh_base(),
            target,
            f"cd {shlex.quote(self.remote_root)} && "
            f"{shlex.quote(self.python)} -m fairai_revision.remote_worker "
            f"--bundle {shlex.quote(f'{self.remote_root}/runtime/clients/client_{client_id}.npz')}",
        ]
        started = time.perf_counter()
        completed = subprocess.run(
            command,
            input=payload,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        if completed.returncode != 0:
            raise RemoteTrainingError(
                f"Remote client {client_id} failed on {worker_name}: {completed.stderr or completed.stdout}"
            )
        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RemoteTrainingError("Remote worker returned invalid JSON") from exc
        self.communication_rows.append(
            {
                "operation": f"{operation}_round",
                "round": round_id,
                "client_id": client_id,
                "worker": worker_name,
                "request_bytes": len(payload.encode("utf-8")),
                "response_bytes": len(completed.stdout.encode("utf-8")),
                "runtime_ms": elapsed_ms,
                "worker_runtime_ms": response["worker_runtime_ms"],
            }
        )
        return {
            "parameters": tuple(
                np.asarray(value, dtype=float) for value in response["parameters"]
            ),
            "metrics": response["metrics"],
        }

    def evaluate(
        self,
        client_id,
        round_id,
        global_parameters,
        model_type,
        seed,
        dataset,
        minimum_group_samples,
    ):
        return self.train(
            client_id=client_id,
            round_id=round_id,
            global_parameters=global_parameters,
            model_type=model_type,
            seed=seed,
            local_epochs=0,
            dataset=dataset,
            minimum_group_samples=minimum_group_samples,
            label_flip=False,
            operation="evaluate",
        )["metrics"]

    def evidence(self):
        return {
            "schema_version": "fairai.remote_training_evidence.v1",
            "physical_workers": len(self.workers),
            "client_assignment": self.assignment,
            "communication_rows": self.communication_rows,
        }
