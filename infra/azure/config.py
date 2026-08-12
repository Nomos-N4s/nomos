"""Configuration module for Nomos Azure Container Apps Pulumi stack."""

from __future__ import annotations

try:
    import pulumi
except ImportError:
    pulumi = None  # type: ignore[assignment]


class NomosAzureConfig:
    """Strongly-typed wrapper around Pulumi config settings for nomos-azure."""

    def __init__(self) -> None:
        if pulumi is not None:
            cfg = pulumi.Config()
            azure_cfg = pulumi.Config("azure-native")

            self.location: str = azure_cfg.get("location") or "eastus"
            self.environment_name: str = cfg.get("environment_name") or "dev"
            self.resource_group_name: str = (
                cfg.get("resource_group_name") or f"nomos-rg-{self.environment_name}"
            )

            self.image_repository: str = (
                cfg.get("image_repository") or "ghcr.io/nomos-n4s/nomos"
            )
            self.image_tag: str = cfg.get("image_tag") or "0.11.1"

            # Container compute allocations
            self.core_cpu: float = float(cfg.get("core_cpu") or "0.5")
            self.core_memory: str = cfg.get("core_memory") or "1.0Gi"

            self.dashboard_cpu: float = float(cfg.get("dashboard_cpu") or "0.5")
            self.dashboard_memory: str = cfg.get("dashboard_memory") or "1.0Gi"

            # Secret values (optional Pulumi secrets)
            self.neo4j_uri: pulumi.Output[str] | str = (
                cfg.get_secret("neo4j_uri") or "neo4j+s://placeholder.databases.neo4j.io"
            )
            self.neo4j_user: pulumi.Output[str] | str = (
                cfg.get_secret("neo4j_user") or "neo4j"
            )
            self.neo4j_password: pulumi.Output[str] | str = (
                cfg.get_secret("neo4j_password") or "placeholder-password-change-me"
            )
            self.openrouter_api_key: pulumi.Output[str] | str = (
                cfg.get_secret("openrouter_api_key") or "sk-or-v1-placeholder-key"
            )
        else:
            self.location = "eastus"
            self.environment_name = "dev"
            self.resource_group_name = "nomos-rg-dev"
            self.image_repository = "ghcr.io/nomos-n4s/nomos"
            self.image_tag = "0.11.1"
            self.core_cpu = 0.5
            self.core_memory = "1.0Gi"
            self.dashboard_cpu = 0.5
            self.dashboard_memory = "1.0Gi"
            self.neo4j_uri = "neo4j+s://placeholder.databases.neo4j.io"
            self.neo4j_user = "neo4j"
            self.neo4j_password = "placeholder-password-change-me"
            self.openrouter_api_key = "sk-or-v1-placeholder-key"

    @property
    def full_image(self) -> str:
        """Full container image specifier."""
        return f"{self.image_repository}:{self.image_tag}"
