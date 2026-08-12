"""Pulumi IaC entry point for Azure Container Apps deployment of Nomos.

Deploys the Nomos modular monolith topology (ADR 0001):
- Azure Resource Group
- Azure Log Analytics Workspace (structured JSON logs)
- Azure Key Vault (secrets management)
- Azure Managed Identity (User-Assigned Identity)
- Azure Container Apps Environment
- ACA Core Container App (runner serve, HTTP GET /healthz & /readyz probes)
- ACA Dashboard Container App (Streamlit dashboard)
"""

from __future__ import annotations

import pulumi
import pulumi_azure_native as azure_native
from config import NomosAzureConfig


def main() -> None:
    config = NomosAzureConfig()
    env = config.environment_name

    # 1. Resource Group
    resource_group = azure_native.resources.ResourceGroup(
        f"nomos-rg-{env}",
        resource_group_name=config.resource_group_name,
        location=config.location,
        tags={
            "Environment": env,
            "Project": "Nomos",
            "ManagedBy": "Pulumi",
        },
    )

    # 2. Log Analytics Workspace (structured JSON logs, #161)
    workspace = azure_native.operationalinsights.Workspace(
        f"nomos-logs-{env}",
        resource_group_name=resource_group.name,
        location=resource_group.location,
        sku=azure_native.operationalinsights.WorkspaceSkuArgs(
            name="PerGB2018",
        ),
        retention_in_days=30,
        tags=resource_group.tags,
    )

    # 3. User-Assigned Managed Identity
    identity = azure_native.managedidentity.UserAssignedIdentity(
        f"nomos-identity-{env}",
        resource_group_name=resource_group.name,
        location=resource_group.location,
        tags=resource_group.tags,
    )

    # Fetch Azure Client / Tenant Info
    client_config = azure_native.authorization.get_client_config()

    # 4. Key Vault for Secrets
    vault = azure_native.keyvault.Vault(
        f"nomos-kv-{env}",
        resource_group_name=resource_group.name,
        location=resource_group.location,
        properties=azure_native.keyvault.VaultPropertiesArgs(
            tenant_id=client_config.tenant_id,
            sku=azure_native.keyvault.SkuArgs(
                family="A",
                name=azure_native.keyvault.SkuName.STANDARD,
            ),
            access_policies=[
                # Deployment / Admin access
                azure_native.keyvault.AccessPolicyEntryArgs(
                    tenant_id=client_config.tenant_id,
                    object_id=client_config.object_id,
                    permissions=azure_native.keyvault.PermissionsArgs(
                        secrets=[
                            azure_native.keyvault.SecretPermissions.GET,
                            azure_native.keyvault.SecretPermissions.LIST,
                            azure_native.keyvault.SecretPermissions.SET,
                            azure_native.keyvault.SecretPermissions.DELETE,
                        ],
                    ),
                ),
                # Container App Managed Identity access
                azure_native.keyvault.AccessPolicyEntryArgs(
                    tenant_id=client_config.tenant_id,
                    object_id=identity.principal_id,
                    permissions=azure_native.keyvault.PermissionsArgs(
                        secrets=[
                            azure_native.keyvault.SecretPermissions.GET,
                            azure_native.keyvault.SecretPermissions.LIST,
                        ],
                    ),
                ),
            ],
            enable_soft_delete=True,
            soft_delete_retention_in_days=7,
        ),
        tags=resource_group.tags,
    )

    # Secrets stored in Key Vault
    secret_neo4j_uri = azure_native.keyvault.Secret(
        "neo4j-uri",
        resource_group_name=resource_group.name,
        vault_name=vault.name,
        secret_name="neo4j-uri",
        properties=azure_native.keyvault.SecretPropertiesArgs(
            value=config.neo4j_uri,
        ),
    )

    secret_neo4j_user = azure_native.keyvault.Secret(
        "neo4j-user",
        resource_group_name=resource_group.name,
        vault_name=vault.name,
        secret_name="neo4j-user",
        properties=azure_native.keyvault.SecretPropertiesArgs(
            value=config.neo4j_user,
        ),
    )

    secret_neo4j_password = azure_native.keyvault.Secret(
        "neo4j-password",
        resource_group_name=resource_group.name,
        vault_name=vault.name,
        secret_name="neo4j-password",
        properties=azure_native.keyvault.SecretPropertiesArgs(
            value=config.neo4j_password,
        ),
    )

    secret_openrouter = azure_native.keyvault.Secret(
        "openrouter-api-key",
        resource_group_name=resource_group.name,
        vault_name=vault.name,
        secret_name="openrouter-api-key",
        properties=azure_native.keyvault.SecretPropertiesArgs(
            value=config.openrouter_api_key,
        ),
    )

    # Fetch Shared Keys for Log Analytics Workspace
    shared_keys = azure_native.operationalinsights.get_shared_keys_output(
        resource_group_name=resource_group.name,
        workspace_name=workspace.name,
    )

    # 5. Container Apps Managed Environment
    aca_environment = azure_native.app.ManagedEnvironment(
        f"nomos-env-{env}",
        resource_group_name=resource_group.name,
        location=resource_group.location,
        app_logs_configuration=azure_native.app.ManagedEnvironmentAppLogsConfigurationArgs(
            destination="log-analytics",
            log_analytics_configuration=azure_native.app.LogAnalyticsConfigurationArgs(
                customer_id=workspace.customer_id,
                shared_key=shared_keys.primary_shared_key,
            ),
        ),
        tags=resource_group.tags,
    )

    # 6. Core Container App (Nomos Speaker & Server)
    core_app = azure_native.app.ContainerApp(
        f"nomos-core-{env}",
        resource_group_name=resource_group.name,
        environment_id=aca_environment.id,
        identity=azure_native.app.ManagedServiceIdentityArgs(
            type=azure_native.app.ManagedServiceIdentityType.USER_ASSIGNED,
            user_assigned_identities=[identity.id],
        ),
        configuration=azure_native.app.ConfigurationArgs(
            ingress=azure_native.app.IngressArgs(
                external=True,
                target_port=8000,
                transport=azure_native.app.IngressTransportMethod.AUTO,
            ),
            secrets=[
                azure_native.app.SecretArgs(
                    name="neo4j-uri",
                    value=secret_neo4j_uri.properties.value,
                ),
                azure_native.app.SecretArgs(
                    name="neo4j-user",
                    value=secret_neo4j_user.properties.value,
                ),
                azure_native.app.SecretArgs(
                    name="neo4j-password",
                    value=secret_neo4j_password.properties.value,
                ),
                azure_native.app.SecretArgs(
                    name="openrouter-api-key",
                    value=secret_openrouter.properties.value,
                ),
            ],
        ),
        template=azure_native.app.TemplateArgs(
            containers=[
                azure_native.app.ContainerArgs(
                    name="core",
                    image=config.full_image,
                    command=[
                        "python",
                        "-m",
                        "nomos.runner",
                        "serve",
                        "--host",
                        "0.0.0.0",
                        "--port",
                        "8000",
                    ],
                    env=[
                        azure_native.app.EnvironmentVarArgs(
                            name="LOG_FORMAT", value="json"
                        ),
                        azure_native.app.EnvironmentVarArgs(
                            name="NEO4J_URI", secret_ref="neo4j-uri"
                        ),
                        azure_native.app.EnvironmentVarArgs(
                            name="NEO4J_USER", secret_ref="neo4j-user"
                        ),
                        azure_native.app.EnvironmentVarArgs(
                            name="NEO4J_PASSWORD", secret_ref="neo4j-password"
                        ),
                        azure_native.app.EnvironmentVarArgs(
                            name="OPENROUTER_API_KEY", secret_ref="openrouter-api-key"
                        ),
                    ],
                    resources=azure_native.app.ContainerResourcesArgs(
                        cpu=config.core_cpu,
                        memory=config.core_memory,
                    ),
                    probes=[
                        # Liveness Probe (#182 /healthz)
                        azure_native.app.ContainerAppProbeArgs(
                            type=azure_native.app.Type.LIVENESS,
                            http_get=azure_native.app.ContainerAppProbeHttpGetArgs(
                                path="/healthz",
                                port=8000,
                            ),
                            initial_delay_seconds=10,
                            period_seconds=15,
                            failure_threshold=3,
                        ),
                        # Readiness Probe (#182 /readyz)
                        azure_native.app.ContainerAppProbeArgs(
                            type=azure_native.app.Type.READINESS,
                            http_get=azure_native.app.ContainerAppProbeHttpGetArgs(
                                path="/readyz",
                                port=8000,
                            ),
                            initial_delay_seconds=15,
                            period_seconds=15,
                            failure_threshold=3,
                        ),
                    ],
                )
            ],
            scale=azure_native.app.ScaleArgs(
                min_replicas=1,
                max_replicas=3,
            ),
        ),
        tags=resource_group.tags,
    )

    # 7. Dashboard Container App (Streamlit)
    dashboard_app = azure_native.app.ContainerApp(
        f"nomos-dashboard-{env}",
        resource_group_name=resource_group.name,
        environment_id=aca_environment.id,
        identity=azure_native.app.ManagedServiceIdentityArgs(
            type=azure_native.app.ManagedServiceIdentityType.USER_ASSIGNED,
            user_assigned_identities=[identity.id],
        ),
        configuration=azure_native.app.ConfigurationArgs(
            ingress=azure_native.app.IngressArgs(
                external=True,
                target_port=8501,
                transport=azure_native.app.IngressTransportMethod.AUTO,
            ),
            secrets=[
                azure_native.app.SecretArgs(
                    name="neo4j-uri",
                    value=secret_neo4j_uri.properties.value,
                ),
                azure_native.app.SecretArgs(
                    name="neo4j-user",
                    value=secret_neo4j_user.properties.value,
                ),
                azure_native.app.SecretArgs(
                    name="neo4j-password",
                    value=secret_neo4j_password.properties.value,
                ),
                azure_native.app.SecretArgs(
                    name="openrouter-api-key",
                    value=secret_openrouter.properties.value,
                ),
            ],
        ),
        template=azure_native.app.TemplateArgs(
            containers=[
                azure_native.app.ContainerArgs(
                    name="dashboard",
                    image=config.full_image,
                    command=[
                        "streamlit",
                        "run",
                        "src/nomos/dashboard/app.py",
                        "--server.port=8501",
                        "--server.address=0.0.0.0",
                    ],
                    env=[
                        azure_native.app.EnvironmentVarArgs(
                            name="LOG_FORMAT", value="json"
                        ),
                        azure_native.app.EnvironmentVarArgs(
                            name="NEO4J_URI", secret_ref="neo4j-uri"
                        ),
                        azure_native.app.EnvironmentVarArgs(
                            name="NEO4J_USER", secret_ref="neo4j-user"
                        ),
                        azure_native.app.EnvironmentVarArgs(
                            name="NEO4J_PASSWORD", secret_ref="neo4j-password"
                        ),
                        azure_native.app.EnvironmentVarArgs(
                            name="OPENROUTER_API_KEY", secret_ref="openrouter-api-key"
                        ),
                        azure_native.app.EnvironmentVarArgs(
                            name="NOMOS_CORE_URL",
                            value=pulumi.Output.concat(
                                "https://",
                                core_app.configuration.apply(
                                    lambda c: c.ingress.fqdn if c and c.ingress else ""
                                ),
                            ),
                        ),
                    ],
                    resources=azure_native.app.ContainerResourcesArgs(
                        cpu=config.dashboard_cpu,
                        memory=config.dashboard_memory,
                    ),
                    probes=[
                        azure_native.app.ContainerAppProbeArgs(
                            type=azure_native.app.Type.LIVENESS,
                            http_get=azure_native.app.ContainerAppProbeHttpGetArgs(
                                path="/_stcore/health",
                                port=8501,
                            ),
                            initial_delay_seconds=15,
                            period_seconds=20,
                            failure_threshold=3,
                        ),
                    ],
                )
            ],
            scale=azure_native.app.ScaleArgs(
                min_replicas=1,
                max_replicas=2,
            ),
        ),
        tags=resource_group.tags,
    )

    # 8. Stack Outputs
    pulumi.export("resource_group_name", resource_group.name)
    pulumi.export("key_vault_name", vault.name)
    pulumi.export("key_vault_uri", vault.properties.vault_uri)
    pulumi.export("log_analytics_workspace_id", workspace.customer_id)
    pulumi.export(
        "core_fqdn",
        core_app.configuration.apply(
            lambda c: c.ingress.fqdn if c and c.ingress else ""
        ),
    )
    pulumi.export(
        "core_url",
        pulumi.Output.concat(
            "https://",
            core_app.configuration.apply(
                lambda c: c.ingress.fqdn if c and c.ingress else ""
            ),
        ),
    )
    pulumi.export(
        "dashboard_fqdn",
        dashboard_app.configuration.apply(
            lambda c: c.ingress.fqdn if c and c.ingress else ""
        ),
    )
    pulumi.export(
        "dashboard_url",
        pulumi.Output.concat(
            "https://",
            dashboard_app.configuration.apply(
                lambda c: c.ingress.fqdn if c and c.ingress else ""
            ),
        ),
    )


if __name__ == "__main__":
    main()
