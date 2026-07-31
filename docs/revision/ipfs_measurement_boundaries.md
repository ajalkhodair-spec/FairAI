# IPFS Measurement Boundaries

## Admissible evidence

An IPFS result is admissible only when `docker-compose.ipfs.yml` starts the
pinned `ipfs/kubo:v0.29.0` publisher and consumer services, both APIs report
the expected version, the peers connect, and the consumer retrieves and
byte-verifies content by the publisher CID. The revision runner is fail-closed:
it does not replace Kubo with the deterministic local content store.

## Measurement definitions

- Add latency: publisher `/api/v0/add` request through receipt of the CID.
- Pin latency: consumer `/api/v0/pin/add` request through successful response.
- Cold retrieval: consumer `/api/v0/cat` after confirming that the consumer
  does not retain the block.
- Warm retrieval: a second consumer retrieval without cache removal.
- Integrity: retrieved bytes equal the exact generated or FairAI artifact.
- Filesystem baseline: local write/read of the same byte payload.
- Concurrent throughput: verified retrievals divided by wall-clock interval
  for concurrency levels 1, 5, 10, and 20.
- Recovery latency: time from retry initiation after publisher restoration or
  replica selection until verified retrieval.

Payload sizes are 1 KB, 10 KB, 100 KB, 1 MB, and 10 MB. Every measurement
records repetition, payload bytes, CID, peer identities, success, retries, and
failure status. Cold-cache reset and node restart operations belong to the
Docker orchestration boundary and cannot be inferred from a fast request.

## Current evidence status

The benchmark implementation and strict-failure tests exist, but this task's
process is denied access to the Docker socket at
`$HOME/.docker/run/docker.sock`. Docker Compose is installed and Docker Desktop
may be running; the operating-system denial still prevents container control.
Therefore add, pin, cold, warm, availability, recovery, concurrency, and
filesystem-comparison result files are marked `evidence_type=missing` with
blocker `BLK-002`. No local hash timings are substituted.

The exact external execution procedure is documented in
`docs/revision/EXECUTION_RUNBOOK.md`.
