import json
import subprocess
from pathlib import Path


class LedgerBridgeError(RuntimeError):
    pass


class HardhatV2LedgerBridge:
    PREFIX = "FAIRAI_JSON:"

    def __init__(self, repo_root, output_dir):
        self.repo_root = Path(repo_root)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.output_dir / "ledger_bridge.log"
        self.log_handle = self.log_path.open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            ["npx", "hardhat", "run", "scripts/v2_ledger_bridge.js"],
            cwd=self.repo_root / "hardhat",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.startup = self._read_response()
        if self.startup.get("status") != "ready":
            self.close(force=True)
            raise LedgerBridgeError(f"Ledger bridge failed to start: {self.startup}")

    def _read_response(self):
        if self.process.stdout is None:
            raise LedgerBridgeError("Ledger bridge stdout is unavailable")
        while True:
            line = self.process.stdout.readline()
            if line == "":
                code = self.process.poll()
                raise LedgerBridgeError(
                    f"Ledger bridge terminated before responding (exit={code})"
                )
            self.log_handle.write(line)
            self.log_handle.flush()
            if line.startswith(self.PREFIX):
                return json.loads(line[len(self.PREFIX) :])

    def request(self, command):
        if self.process.poll() is not None or self.process.stdin is None:
            raise LedgerBridgeError("Ledger bridge is not running")
        self.process.stdin.write(json.dumps(command, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        response = self._read_response()
        if response.get("status") != "ok":
            raise LedgerBridgeError(response.get("error", str(response)))
        return response["result"]

    def close(self, force=False):
        if getattr(self, "process", None) is None:
            return
        try:
            if not force and self.process.poll() is None and self.process.stdin is not None:
                self.process.stdin.write('{"action":"close"}\n')
                self.process.stdin.flush()
                self._read_response()
        finally:
            if self.process.poll() is None:
                self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
            if not self.log_handle.closed:
                self.log_handle.close()

    def __del__(self):
        try:
            self.close(force=True)
        except Exception:
            pass
