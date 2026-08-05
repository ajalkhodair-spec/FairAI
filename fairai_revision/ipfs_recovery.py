import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

from .ipfs import (
    KuboClient,
    StrictIPFSError,
    connect_two_peers,
    deterministic_payload,
    verify_payload,
)


def sha512_file(path):
    digest = hashlib.sha512()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_kubo_binary(binary_path, lock_path):
    binary_path = Path(binary_path)
    if not binary_path.is_file():
        raise StrictIPFSError(f"Kubo binary does not exist: {binary_path}")
    lock = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    expected_hash = lock["native_distribution"]["binary_sha512"]
    observed_hash = sha512_file(binary_path)
    if observed_hash != expected_hash:
        raise StrictIPFSError("Kubo binary SHA-512 does not match the toolchain lock")
    completed = subprocess.run(
        [str(binary_path), "version", "--number"],
        check=True,
        capture_output=True,
        text=True,
    )
    version = completed.stdout.strip()
    if version != lock["measured_kubo_version"]:
        raise StrictIPFSError(
            f"Kubo binary version {version} does not match the toolchain lock"
        )
    return {"version": version, "sha512": observed_hash}


class NativeKuboNode:
    def __init__(self, binary, repo, api_port, swarm_port, gateway_port, log_path):
        self.binary = str(binary)
        self.repo = Path(repo)
        self.api_port = api_port
        self.swarm_port = swarm_port
        self.gateway_port = gateway_port
        self.log_path = Path(log_path)
        self.process = None
        self.log_handle = None

    @property
    def client(self):
        return KuboClient(f"http://127.0.0.1:{self.api_port}", timeout_seconds=3)

    def _run(self, *args):
        environment = {**os.environ, "IPFS_PATH": str(self.repo)}
        return subprocess.run(
            [self.binary, *args],
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )

    def initialize(self):
        self.repo.parent.mkdir(parents=True, exist_ok=True)
        self._run("init", "--profile=server")
        self._run("bootstrap", "rm", "--all")
        self._run("config", "Addresses.API", f"/ip4/127.0.0.1/tcp/{self.api_port}")
        self._run(
            "config",
            "Addresses.Gateway",
            f"/ip4/127.0.0.1/tcp/{self.gateway_port}",
        )
        self._run(
            "config",
            "--json",
            "Addresses.Swarm",
            json.dumps([f"/ip4/127.0.0.1/tcp/{self.swarm_port}"]),
        )

    def start(self, timeout_seconds=30):
        if self.process is not None:
            raise StrictIPFSError("Kubo node is already running")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_handle = self.log_path.open("ab")
        self.process = subprocess.Popen(
            [self.binary, "daemon"],
            env={**os.environ, "IPFS_PATH": str(self.repo)},
            stdout=self.log_handle,
            stderr=subprocess.STDOUT,
        )
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise StrictIPFSError(
                    f"Kubo daemon exited early; inspect {self.log_path}"
                )
            try:
                return self.client.version()
            except StrictIPFSError:
                time.sleep(0.1)
        self.stop()
        raise StrictIPFSError("Timed out waiting for Kubo daemon")

    def stop(self):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
            self.process = None
        if self.log_handle is not None:
            self.log_handle.close()
            self.log_handle = None


def benchmark_native_kubo_recovery(config, output_dir, repo_root):
    binary = os.environ.get("FAIRAI_KUBO_BINARY")
    if not binary:
        raise StrictIPFSError("FAIRAI_KUBO_BINARY is required")
    toolchain = verify_kubo_binary(
        binary, Path(repo_root) / "infrastructure" / "toolchain.lock.json"
    )
    runtime = Path(output_dir) / "raw" / "native_kubo_runtime"
    publisher = NativeKuboNode(
        binary,
        runtime / "publisher",
        config.get("publisher_api_port", 5201),
        config.get("publisher_swarm_port", 4201),
        config.get("publisher_gateway_port", 8280),
        Path(output_dir) / "logs" / "publisher.log",
    )
    consumer = NativeKuboNode(
        binary,
        runtime / "consumer",
        config.get("consumer_api_port", 5202),
        config.get("consumer_swarm_port", 4202),
        config.get("consumer_gateway_port", 8281),
        Path(output_dir) / "logs" / "consumer.log",
    )
    rows = []
    try:
        publisher.initialize()
        consumer.initialize()
        publisher.start()
        consumer.start()
        publisher_id, consumer_id = connect_two_peers(
            publisher.client,
            consumer.client,
            "127.0.0.1",
            publisher.swarm_port,
        )
        original_publisher_id = publisher_id
        for repetition in range(1, config["repetitions"] + 1):
            payload = deterministic_payload(
                config["seed"], config["payload_bytes"], repetition
            )
            cid = publisher.client.add(payload, f"outage-{repetition}.bin")
            verify_payload(payload, consumer.client.cat(cid), cid)
            started = time.perf_counter()
            consumer.client.pin(cid)
            pin_ms = (time.perf_counter() - started) * 1000

            publisher.stop()
            started = time.perf_counter()
            verify_payload(payload, consumer.client.cat(cid), cid)
            outage_retrieval_ms = (time.perf_counter() - started) * 1000

            recovery_started = time.perf_counter()
            publisher.start()
            restart_ready_ms = (time.perf_counter() - recovery_started) * 1000
            restarted_id, _ = connect_two_peers(
                publisher.client,
                consumer.client,
                "127.0.0.1",
                publisher.swarm_port,
            )
            if restarted_id != original_publisher_id:
                raise StrictIPFSError("Publisher identity changed after restart")
            recovery_payload = deterministic_payload(
                config["seed"] + 2_000_000,
                config["payload_bytes"],
                repetition,
            )
            recovery_cid = publisher.client.add(
                recovery_payload, f"recovery-{repetition}.bin"
            )
            verify_payload(
                recovery_payload,
                consumer.client.cat(recovery_cid),
                recovery_cid,
            )
            recovery_verified_ms = (time.perf_counter() - recovery_started) * 1000
            rows.append(
                {
                    "repetition": repetition,
                    "payload_bytes": config["payload_bytes"],
                    "pin_ms": pin_ms,
                    "outage_retrieval_ms": outage_retrieval_ms,
                    "restart_ready_ms": restart_ready_ms,
                    "recovery_verified_ms": recovery_verified_ms,
                    "publisher_identity_stable": True,
                    "verified": True,
                }
            )
        return {
            "kubo_version": toolchain["version"],
            "kubo_binary_sha512": toolchain["sha512"],
            "publisher_peer_id": original_publisher_id,
            "consumer_peer_id": consumer_id,
            "rows": rows,
        }
    finally:
        publisher.stop()
        consumer.stop()
