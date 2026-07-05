#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${1:-../../outputs/fairai_mvp_run}"

cd "$ROOT_DIR"
docker compose -f docker-compose.ipfs.yml up -d
export FAIRAI_IPFS_API="${FAIRAI_IPFS_API:-http://127.0.0.1:5001}"

python3 scripts/fairai_mvp.py --output "$OUTPUT_DIR" --require-real-ipfs
