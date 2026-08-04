#!/usr/bin/env bash
set -euo pipefail

: "${AZURE_RESOURCE_GROUP:?Set AZURE_RESOURCE_GROUP}"
: "${AZURE_LOCATION:?Set AZURE_LOCATION}"
: "${AZURE_PARAMETERS_FILE:?Set AZURE_PARAMETERS_FILE}"

command -v az >/dev/null || { echo "Azure CLI is required" >&2; exit 1; }
az account show >/dev/null
az group create \
  --name "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --tags project=FairAI environment=major-revision-experiment
az deployment group create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --template-file "$(dirname "$0")/../main.bicep" \
  --parameters "@$AZURE_PARAMETERS_FILE" \
  --name "fairai-$(date -u +%Y%m%dT%H%M%SZ)" \
  --query properties.outputs \
  --output json
