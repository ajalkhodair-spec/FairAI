# Azure Experiment Deployment

This deployment creates three temporary Ubuntu 22.04 hosts: one controller and
two workers. Logical FL client counts (5, 10, or 20) are distinct from the three
physical hosts. The topology is designed for bounded multi-host measurements,
not production validation.

The separate local scaling scenario evaluates 3, 5, 10, 20, and 50 logical
clients. No result should describe a logical client count as a VM count.

Security defaults:

- SSH keys only, restricted to one administrator CIDR;
- experiment traffic accepted only inside the VNet;
- system-assigned managed identities;
- private result container with Microsoft Entra authorization;
- automatic OS patch assessment and daily VM shutdown;
- no public Kubo, RPC, or application ports.

The public IPs exist only for temporary administrator SSH. Remove them or use
Azure Bastion/private access for a longer-lived deployment.

## Deploy

1. Install Azure CLI and Bicep, then authenticate with `az login`.
2. Copy `main.parameters.example.json` outside the repository and replace the
   SSH key and trusted `/32` CIDR placeholders.
3. Select a subscription and inspect regional D2s_v5 quota and pricing.
4. Run:

```bash
export AZURE_RESOURCE_GROUP=fairai-revision
export AZURE_LOCATION=uksouth
export AZURE_PARAMETERS_FILE="$HOME/.config/fairai/azure.parameters.json"
azure/scripts/deploy.sh > azure-deployment-outputs.json
```

5. Stage the exact checked-out source:

```bash
export FAIRAI_SSH_PRIVATE_KEY="$HOME/.ssh/id_ed25519"
azure/scripts/stage_project.sh
```

6. Configure the controller-to-worker SSH key, pinned Kubo peers, Python
   environments, and Hardhat build:

```bash
azure/scripts/configure_cluster.sh
```

7. Run the bounded Adult and COMPAS matrix and upload its checksum-addressed
   archive to the private result container:

```bash
azure/scripts/run_bounded_matrix.sh
```

The deployment script deliberately does not create a subscription budget
because budget contacts and subscription policy are owner-controlled. Create a
monthly budget and alerts before execution, then verify the daily shutdown
schedules in the Azure portal.

## Teardown

Download evidence first. Resource-group deletion is asynchronous and requires
an exact confirmation value:

```bash
export FAIRAI_CONFIRM_DESTROY="$AZURE_RESOURCE_GROUP"
azure/scripts/destroy.sh
```

Do not claim Azure results until manifests contain the subscription-neutral
topology, VM SKU, region, image, logical-client count, physical-host count,
network measurements, and output checksums.
