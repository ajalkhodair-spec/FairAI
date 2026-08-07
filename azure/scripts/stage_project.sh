#!/usr/bin/env bash
set -euo pipefail

: "${AZURE_RESOURCE_GROUP:?Set AZURE_RESOURCE_GROUP}"
: "${FAIRAI_SSH_PRIVATE_KEY:?Set FAIRAI_SSH_PRIVATE_KEY}"
ADMIN_USERNAME="${FAIRAI_ADMIN_USERNAME:-fairaiadmin}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ARCHIVE="$(mktemp -t fairai-source.XXXXXX.tar.gz)"
trap 'rm -f "$ARCHIVE"' EXIT

tar -C "$ROOT" -czf "$ARCHIVE" \
  --exclude=.git --exclude=.venv --exclude=.tools --exclude=node_modules \
  --exclude=hardhat/node_modules --exclude=data/raw --exclude=outputs .

for role in controller worker1 worker2; do
  vm="fairai-$role"
  ip="$(az vm list-ip-addresses --resource-group "$AZURE_RESOURCE_GROUP" --name "$vm" --query '[0].virtualMachine.network.publicIpAddresses[0].ipAddress' -o tsv)"
  scp -o StrictHostKeyChecking=accept-new -i "$FAIRAI_SSH_PRIVATE_KEY" "$ARCHIVE" "$ADMIN_USERNAME@$ip:/tmp/fairai-source.tar.gz"
  ssh -i "$FAIRAI_SSH_PRIVATE_KEY" "$ADMIN_USERNAME@$ip" \
    'sudo find /opt/fairai -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + && sudo tar -xzf /tmp/fairai-source.tar.gz -C /opt/fairai && sudo chown -R '"$ADMIN_USERNAME"':'"$ADMIN_USERNAME"' /opt/fairai'
done
