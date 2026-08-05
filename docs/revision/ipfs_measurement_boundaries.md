# IPFS Measurement Boundaries

## Admissible evidence

An IPFS result is admissible only when two independent Kubo 0.29.0 repositories
run as publisher and consumer, both APIs report the expected version, the peers
connect, and the consumer retrieves and byte-verifies content by the publisher
CID. The peers may be started by `docker-compose.ipfs.yml` or by the
checksum-verified native Kubo binary. The revision runner is fail-closed: it
does not replace Kubo with the deterministic local content store.

## Measurement definitions

- Add latency: publisher `/api/v0/add` request through receipt of the CID.
- Pin latency: consumer `/api/v0/pin/add` request through successful response;
  this is defined but not separately timed in the current evidence.
- Cold retrieval: consumer `/api/v0/cat` for a uniquely seeded payload that the
  consumer has not previously requested.
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

The clean run `ipfs-native-cold-30rep-4fbec7a` contains 150 sequential and 120
concurrent measurements from two native Kubo 0.29.0 peers. Payload namespaces
are disjoint between sequential and each concurrency level, and all retrievals
are byte-verified. The bounded B2/B4/B7 suite contains 2,688 additional verified
artifact retrievals. Separate pin latency, process outage/recovery, filesystem
comparison, WAN, and multi-host measurements remain unavailable; no local hash
timing is substituted for them.

Derived tables and source hashes are under
`outputs/revision_audit/infrastructure-analysis/`.
