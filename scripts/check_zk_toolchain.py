import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "zk" / "toolchain.lock.json"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def version(command):
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    match = re.search(r"\d+\.\d+\.\d+", result.stdout)
    return match.group(0) if match else None


def main():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    observed = {
        "circom_version": version(["circom", "--version"]),
        "snarkjs_version": version(["snarkjs", "--version"]),
    }
    errors = []
    for name in ("circom_version", "snarkjs_version"):
        if observed[name] != lock[name]:
            errors.append(
                f"{name}: expected {lock[name]}, observed {observed[name] or 'missing'}"
            )
    ptau_path = Path(
        os.environ.get(
            "FAIRAI_PTAU_PATH",
            ROOT / "zk" / lock["powers_of_tau"]["filename"],
        )
    )
    if not ptau_path.is_file():
        errors.append(f"Powers of Tau file is missing: {ptau_path}")
        observed["powers_of_tau_sha256"] = None
    else:
        observed["powers_of_tau_sha256"] = sha256_file(ptau_path)
        if observed["powers_of_tau_sha256"] != lock["powers_of_tau"]["sha256"]:
            errors.append("Powers of Tau checksum mismatch")
    print(
        json.dumps(
            {
                "schema_version": "fairai.zk_toolchain_check.v1",
                "compatible": not errors,
                "observed": observed,
                "errors": errors,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
