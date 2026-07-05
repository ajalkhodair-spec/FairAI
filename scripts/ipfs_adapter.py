import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

def stable_json(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(data):
    return __import__("hashlib").sha256(data).hexdigest()


class IPFSAdapter:
    """Stores JSON artifacts through Kubo IPFS when available, else a deterministic local store."""

    def __init__(self, storage_dir, prefer_real_ipfs=False):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.ipfs_api = os.environ.get("FAIRAI_IPFS_API") if prefer_real_ipfs else None
        self.ipfs_binary = shutil.which("ipfs") if prefer_real_ipfs else None

    @property
    def mode(self):
        if self.ipfs_api:
            return "kubo-http"
        return "kubo" if self.ipfs_binary else "local-content-addressed"

    def add_json(self, name, payload):
        encoded = stable_json(payload)
        local_cid = f"sha256-{sha256_bytes(encoded)}"
        local_path = self.storage_dir / f"{local_cid}.json"
        local_path.write_bytes(encoded)

        if self.ipfs_api:
            started = __import__("time").time()
            result = self._add_with_http_api(name, encoded, local_cid, local_path)
            if result:
                result["upload_ms"] = round((__import__("time").time() - started) * 1000, 3)
                return result

        if not self.ipfs_binary:
            return {"cid": local_cid, "mode": self.mode, "path": str(local_path)}

        staged_path = self.storage_dir / name
        staged_path.write_bytes(encoded)
        completed = subprocess.run(
            [self.ipfs_binary, "add", "-Q", str(staged_path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode != 0:
            return {
                "cid": local_cid,
                "mode": "local-content-addressed",
                "path": str(local_path),
                "ipfs_error": completed.stderr.strip(),
            }
        kubo_cid = completed.stdout.strip()
        (self.storage_dir / f"{kubo_cid}.json").write_bytes(encoded)
        return {
            "cid": kubo_cid,
            "mode": self.mode,
            "path": str(local_path),
            "local_cid": local_cid,
        }

    def _add_with_http_api(self, name, encoded, local_cid, local_path):
        boundary = "----fairai-mvp-boundary"
        body = b"".join([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'.encode(),
            b"Content-Type: application/json\r\n\r\n",
            encoded,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ])
        url = self.ipfs_api.rstrip("/") + "/api/v0/add?pin=true&cid-version=1"
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

        kubo_cid = payload.get("Hash")
        if not kubo_cid:
            return None
        (self.storage_dir / f"{kubo_cid}.json").write_bytes(encoded)
        return {
            "cid": kubo_cid,
            "mode": "kubo-http",
            "path": str(local_path),
            "local_cid": local_cid,
        }

    def put_json(self, name, payload):
        return self.add_json(name, payload)["cid"]

    def get_json(self, cid):
        if self.ipfs_api and not cid.startswith("sha256-"):
            payload = self._cat_with_http_api(cid)
            if payload is not None:
                return payload
        return self.read_local_json(cid)

    def validate_json(self, cid, required_keys=None):
        started = __import__("time").time()
        payload = self.get_json(cid)
        if required_keys:
            missing = [key for key in required_keys if key not in payload]
            if missing:
                raise ValueError(f"CID {cid} is missing required keys: {missing}")
        return {
            "cid": cid,
            "mode": self.mode,
            "valid": True,
            "retrieval_ms": round((__import__("time").time() - started) * 1000, 3),
        }

    def pin(self, cid):
        if not self.ipfs_api or cid.startswith("sha256-"):
            return {"cid": cid, "pinned": self.mode != "kubo-http", "mode": self.mode}
        url = self.ipfs_api.rstrip("/") + "/api/v0/pin/add?arg=" + cid
        request = urllib.request.Request(url, data=b"", method="POST")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return {"cid": cid, "pinned": False, "mode": self.mode, "error": str(exc)}
        return {"cid": cid, "pinned": cid in payload.get("Pins", []), "mode": self.mode}

    def _cat_with_http_api(self, cid):
        url = self.ipfs_api.rstrip("/") + "/api/v0/cat?arg=" + cid
        request = urllib.request.Request(url, data=b"", method="POST")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

    def read_local_json(self, cid):
        matches = list(self.storage_dir.glob(f"{cid}*"))
        if not matches:
            raise FileNotFoundError(cid)
        return json.loads(matches[0].read_text())
