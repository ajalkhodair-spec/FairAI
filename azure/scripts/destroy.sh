#!/usr/bin/env bash
set -euo pipefail

: "${AZURE_RESOURCE_GROUP:?Set AZURE_RESOURCE_GROUP}"
if [[ "${FAIRAI_CONFIRM_DESTROY:-}" != "$AZURE_RESOURCE_GROUP" ]]; then
  echo "Set FAIRAI_CONFIRM_DESTROY=$AZURE_RESOURCE_GROUP to delete the experiment resource group." >&2
  exit 2
fi
az group delete --name "$AZURE_RESOURCE_GROUP" --yes --no-wait
