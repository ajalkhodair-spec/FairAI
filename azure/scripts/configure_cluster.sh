#!/usr/bin/env bash
set -euo pipefail

: "${AZURE_RESOURCE_GROUP:?Set AZURE_RESOURCE_GROUP}"
: "${FAIRAI_SSH_PRIVATE_KEY:?Set FAIRAI_SSH_PRIVATE_KEY}"
DEPLOYMENT_NAME="${FAIRAI_DEPLOYMENT_NAME:-fairai}"
ADMIN_USERNAME="${FAIRAI_ADMIN_USERNAME:-fairaiadmin}"
SSH=(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i "$FAIRAI_SSH_PRIVATE_KEY")

public_ip() {
  az vm list-ip-addresses --resource-group "$AZURE_RESOURCE_GROUP" --name "$1" \
    --query '[0].virtualMachine.network.publicIpAddresses[0].ipAddress' -o tsv
}

private_ip() {
  az vm list-ip-addresses --resource-group "$AZURE_RESOURCE_GROUP" --name "$1" \
    --query '[0].virtualMachine.network.privateIpAddresses[0]' -o tsv
}

controller_vm="$DEPLOYMENT_NAME-controller"
worker1_vm="$DEPLOYMENT_NAME-worker1"
worker2_vm="$DEPLOYMENT_NAME-worker2"
controller_public="$(public_ip "$controller_vm")"
worker1_public="$(public_ip "$worker1_vm")"
worker2_public="$(public_ip "$worker2_vm")"
worker1_private="$(private_ip "$worker1_vm")"
worker2_private="$(private_ip "$worker2_vm")"

for ip in "$controller_public" "$worker1_public" "$worker2_public"; do
  "${SSH[@]}" "$ADMIN_USERNAME@$ip" \
    'cloud-init status --wait && cd /opt/fairai && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-lock.txt'
done
"${SSH[@]}" "$ADMIN_USERNAME@$controller_public" \
  'cd /opt/fairai/hardhat && npm ci && npx hardhat compile'

cluster_public_key="$("${SSH[@]}" "$ADMIN_USERNAME@$controller_public" \
  'test -f ~/.ssh/fairai_cluster || ssh-keygen -q -t ed25519 -N "" -f ~/.ssh/fairai_cluster; cat ~/.ssh/fairai_cluster.pub')"
for ip in "$worker1_public" "$worker2_public"; do
  printf '%s\n' "$cluster_public_key" | "${SSH[@]}" "$ADMIN_USERNAME@$ip" \
    'umask 077; mkdir -p ~/.ssh; touch ~/.ssh/authorized_keys; key=$(cat); grep -qxF "$key" ~/.ssh/authorized_keys || printf "%s\n" "$key" >> ~/.ssh/authorized_keys'
done

"${SSH[@]}" "$ADMIN_USERNAME@$controller_public" \
  "ssh-keyscan -H '$worker1_private' '$worker2_private' >> ~/.ssh/known_hosts 2>/dev/null"

for ip in "$worker1_public" "$worker2_public"; do
  "${SSH[@]}" "$ADMIN_USERNAME@$ip" \
    'sudo docker pull ipfs/kubo:v0.29.0 && (sudo docker inspect fairai-ipfs >/dev/null 2>&1 || sudo docker run -d --restart unless-stopped --name fairai-ipfs -p 4001:4001 -p 5001:5001 ipfs/kubo:v0.29.0)'
done

topology="$(mktemp -t fairai-topology.XXXXXX.json)"
trap 'rm -f "$topology"' EXIT
jq -n \
  --arg user "$ADMIN_USERNAME" \
  --arg worker1 "$worker1_private" \
  --arg worker2 "$worker2_private" \
  '{
    schema_version: "fairai.azure_topology.v1",
    ssh_user: $user,
    ssh_key: ("/home/" + $user + "/.ssh/fairai_cluster"),
    remote_root: "/opt/fairai",
    python: "/opt/fairai/.venv/bin/python",
    kubo_publisher_api: ("http://" + $worker1 + ":5001"),
    kubo_consumer_api: ("http://" + $worker2 + ":5001"),
    kubo_publisher_swarm_host: $worker1,
    workers: [
      {name: "worker1", host: $worker1},
      {name: "worker2", host: $worker2}
    ]
  }' > "$topology"
scp -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i "$FAIRAI_SSH_PRIVATE_KEY" \
  "$topology" "$ADMIN_USERNAME@$controller_public:/opt/fairai/azure/runtime_topology.json"

"${SSH[@]}" "$ADMIN_USERNAME@$controller_public" \
  "curl -fsS -X POST 'http://$worker1_private:5001/api/v0/version' && curl -fsS -X POST 'http://$worker2_private:5001/api/v0/version'"

printf 'controller_public_ip=%s\nworker1_private_ip=%s\nworker2_private_ip=%s\n' \
  "$controller_public" "$worker1_private" "$worker2_private"
