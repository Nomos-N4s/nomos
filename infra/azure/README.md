# Nomos — Azure Container Apps IaC (Pulumi)

Infrastructure as Code program in Python for deploying the Nomos modular monolith topology ([ADR 0001](../../docs/adr/0001-modular-monolith-and-atomic-governance-gate.md)) to Azure Container Apps (ACA).

Part of GitHub Issue [#221](https://github.com/Nomos-N4s/nomos/issues/221) (Track J-F2, epic [#214](https://github.com/Nomos-N4s/nomos/issues/214)).

## Architecture Overview

- **Resource Group:** Dedicated resource group for Nomos services.
- **Key Vault:** Secure store for Neo4j credentials and API keys with Managed Identity access.
- **Log Analytics Workspace:** Centralized JSON log aggregation (#161).
- **Managed Identity:** User-assigned managed identity attached to Container Apps.
- **Core App:** Nomos Speaker & server process exposing port 8000 (`/healthz` and `/readyz` probes).
- **Dashboard App:** Nomos Streamlit visualizer exposing port 8501.

## Prerequisites

- [Azure CLI (`az`)](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) logged in via `az login`
- [Pulumi CLI](https://www.pulumi.com/docs/install/) logged in via `pulumi login`
- Python 3.10+ & `uv` installed

## Quickstart

```bash
# 1. Navigate to IaC directory
cd infra/azure

# 2. Set up Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Select or create Pulumi stack
pulumi stack init dev

# 4. Set optional configuration values (secrets are encrypted)
pulumi config set azure-native:location eastus
pulumi config set --secret neo4j_uri "neo4j+s://<instance>.databases.neo4j.io"
pulumi config set --secret neo4j_user "neo4j"
pulumi config set --secret neo4j_password "<password>"
pulumi config set --secret openrouter_api_key "sk-or-v1-<key>"

# 5. Preview & Deploy
pulumi preview
pulumi up
```

## Stack Outputs

After a successful `pulumi up`, Pulumi outputs the endpoints and resource identifiers:

- `core_url`: `https://nomos-core-dev.<region>.azurecontainerapps.io`
- `dashboard_url`: `https://nomos-dashboard-dev.<region>.azurecontainerapps.io`
- `key_vault_uri`: Key Vault URI
- `log_analytics_workspace_id`: Log Analytics Workspace Customer ID

## Clean Up

To tear down all Azure resources created by this stack:

```bash
pulumi destroy
```
