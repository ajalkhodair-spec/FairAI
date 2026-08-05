import hashlib
import ipaddress
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor


class StrictIPFSError(RuntimeError):
    pass


def deterministic_payload(seed, size_bytes, repetition):
    prefix = f"fairai:{seed}:{size_bytes}:{repetition}:".encode("ascii")
    digest = hashlib.sha256(prefix).digest()
    return (prefix + digest * ((size_bytes // len(digest)) + 1))[:size_bytes]


def concurrency_payload_seed(seed, concurrency, worker):
    if concurrency < 1 or worker < 0 or worker >= concurrency:
        raise ValueError("Invalid concurrency worker index")
    return seed + 1_000_000 + concurrency * 1_000 + worker


class KuboClient:
    def __init__(self, api_url, timeout_seconds=60):
        self.api_url = api_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _post(self, command, query=None, body=None, headers=None):
        query_string = urllib.parse.urlencode(query or {}, doseq=True)
        url = f"{self.api_url}/api/v0/{command}"
        if query_string:
            url = f"{url}?{query_string}"
        request = urllib.request.Request(
            url,
            data=b"" if body is None else body,
            headers=headers or {},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            raise StrictIPFSError(
                f"Kubo request failed for {command} at {self.api_url}: {exc}"
            ) from exc

    def json_command(self, command, query=None):
        return json.loads(self._post(command, query=query))

    def version(self):
        return self.json_command("version")

    def identity(self):
        return self.json_command("id")

    def connect(self, multiaddress):
        return self.json_command("swarm/connect", {"arg": multiaddress})

    def add(self, payload, filename="artifact.bin"):
        boundary = f"fairai-{uuid.uuid4().hex}"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode("ascii") + payload + f"\r\n--{boundary}--\r\n".encode("ascii")
        response = self._post(
            "add",
            {"pin": "true", "cid-version": 1},
            body=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        result = json.loads(response.strip().splitlines()[-1])
        cid = result.get("Hash")
        if not cid:
            raise StrictIPFSError("Kubo add response did not contain a CID")
        return cid

    def cat(self, cid):
        return self._post("cat", {"arg": cid})

    def pin(self, cid):
        return self.json_command("pin/add", {"arg": cid})


def verify_payload(expected, observed, cid):
    if observed != expected:
        raise StrictIPFSError(
            f"CID {cid} returned bytes that differ from the published payload"
        )


def connect_two_peers(publisher, consumer, publisher_host="ipfs-publisher"):
    publisher_id = publisher.identity()["ID"]
    try:
        protocol = "ip4" if ipaddress.ip_address(publisher_host).version == 4 else "ip6"
    except ValueError:
        protocol = "dns4"
    address = f"/{protocol}/{publisher_host}/tcp/4001/p2p/{publisher_id}"
    consumer.connect(address)
    return publisher_id, consumer.identity()["ID"]


def benchmark_two_peer_kubo(config):
    publisher = KuboClient(
        config.get("publisher_api", "http://127.0.0.1:5001")
    )
    consumer = KuboClient(
        config.get("consumer_api", "http://127.0.0.1:5002")
    )
    publisher_version = publisher.version()["Version"]
    consumer_version = consumer.version()["Version"]
    expected_version = config.get("kubo_version", "0.29.0")
    if publisher_version != expected_version or consumer_version != expected_version:
        raise StrictIPFSError(
            "Kubo version mismatch: "
            f"publisher={publisher_version}, consumer={consumer_version}, "
            f"expected={expected_version}"
        )
    publisher_id, consumer_id = connect_two_peers(
        publisher, consumer, config.get("publisher_swarm_host", "ipfs-publisher")
    )
    rows = []
    for size_bytes in config["payload_bytes"]:
        for repetition in range(1, config["repetitions"] + 1):
            payload = deterministic_payload(
                config["seed"], size_bytes, repetition
            )
            started = time.perf_counter()
            cid = publisher.add(payload)
            upload_ms = (time.perf_counter() - started) * 1000
            started = time.perf_counter()
            cold = consumer.cat(cid)
            cold_ms = (time.perf_counter() - started) * 1000
            verify_payload(payload, cold, cid)
            started = time.perf_counter()
            warm = consumer.cat(cid)
            warm_ms = (time.perf_counter() - started) * 1000
            verify_payload(payload, warm, cid)
            consumer.pin(cid)
            rows.append(
                {
                    "mode": "sequential",
                    "repetition": repetition,
                    "payload_bytes": size_bytes,
                    "concurrency": 1,
                    "cid": cid,
                    "upload_ms": upload_ms,
                    "cold_retrieval_ms": cold_ms,
                    "warm_retrieval_ms": warm_ms,
                    "verified": True,
                }
            )

    concurrency_payload_size = config.get(
        "concurrency_payload_bytes", 1048576
    )
    for concurrency in config["concurrency"]:
        for repetition in range(1, config["repetitions"] + 1):
            payloads = [
                deterministic_payload(
                    concurrency_payload_seed(
                        config["seed"], concurrency, worker
                    ),
                    concurrency_payload_size,
                    repetition,
                )
                for worker in range(concurrency)
            ]
            cids = [publisher.add(payload) for payload in payloads]
            started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                observed = list(pool.map(consumer.cat, cids))
            elapsed_ms = (time.perf_counter() - started) * 1000
            for payload, value, cid in zip(payloads, observed, cids):
                verify_payload(payload, value, cid)
            rows.append(
                {
                    "mode": "concurrent",
                    "repetition": repetition,
                    "payload_bytes": concurrency_payload_size,
                    "concurrency": concurrency,
                    "cid": "",
                    "upload_ms": "",
                    "cold_retrieval_ms": elapsed_ms,
                    "warm_retrieval_ms": "",
                    "verified": True,
                }
            )
    return {
        "publisher_id": publisher_id,
        "consumer_id": consumer_id,
        "kubo_version": publisher_version,
        "rows": rows,
    }
