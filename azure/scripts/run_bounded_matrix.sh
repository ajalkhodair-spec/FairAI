#!/usr/bin/env bash
set -euo pipefail

: "${AZURE_RESOURCE_GROUP:?Set AZURE_RESOURCE_GROUP}"
: "${FAIRAI_SSH_PRIVATE_KEY:?Set FAIRAI_SSH_PRIVATE_KEY}"
DEPLOYMENT_NAME="${FAIRAI_DEPLOYMENT_NAME:-fairai}"
ADMIN_USERNAME="${FAIRAI_ADMIN_USERNAME:-fairaiadmin}"
LOCAL_RESULTS_DIR="${FAIRAI_LOCAL_RESULTS_DIR:-azure-results}"
controller_vm="$DEPLOYMENT_NAME-controller"
controller_ip="$(az vm list-ip-addresses --resource-group "$AZURE_RESOURCE_GROUP" --name "$controller_vm" --query '[0].virtualMachine.network.publicIpAddresses[0].ipAddress' -o tsv)"
SSH=(ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i "$FAIRAI_SSH_PRIVATE_KEY")

run_id="azure-$(date -u +%Y%m%dT%H%M%SZ)"
"${SSH[@]}" "$ADMIN_USERNAME@$controller_ip" "
  set -euo pipefail
  cd /opt/fairai
  .venv/bin/python -m fairai_revision.datasets adult
  .venv/bin/python -m fairai_revision.datasets compas
  mkdir -p /var/lib/fairai-results/$run_id
  .venv/bin/python -m fairai_revision.run --config configs/revision/azure_adult.yaml --output-root /var/lib/fairai-results/$run_id
  .venv/bin/python -m fairai_revision.run --config configs/revision/azure_compas.yaml --output-root /var/lib/fairai-results/$run_id
  tar -C /var/lib/fairai-results -czf /tmp/$run_id.tar.gz $run_id
"

mkdir -p "$LOCAL_RESULTS_DIR"
scp -o BatchMode=yes -o StrictHostKeyChecking=accept-new -i "$FAIRAI_SSH_PRIVATE_KEY" \
  "$ADMIN_USERNAME@$controller_ip:/tmp/$run_id.tar.gz" "$LOCAL_RESULTS_DIR/$run_id.tar.gz"
shasum -a 256 "$LOCAL_RESULTS_DIR/$run_id.tar.gz" > "$LOCAL_RESULTS_DIR/$run_id.tar.gz.sha256"

storage_account="$(az storage account list --resource-group "$AZURE_RESOURCE_GROUP" --query '[0].name' -o tsv)"
az storage blob upload \
  --auth-mode login \
  --account-name "$storage_account" \
  --container-name results \
  --name "$run_id.tar.gz" \
  --file "$LOCAL_RESULTS_DIR/$run_id.tar.gz" \
  --overwrite false
printf 'run_id=%s\narchive=%s\n' "$run_id" "$LOCAL_RESULTS_DIR/$run_id.tar.gz"
