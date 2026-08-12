"""Tests for infra/azure Pulumi IaC configuration and module structure."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

INFRA_AZURE_DIR = Path(__file__).parent.parent / "infra" / "azure"


def test_pulumi_yaml_structure() -> None:
    """Verify infra/azure/Pulumi.yaml exists and has valid Pulumi project metadata."""
    pulumi_yaml_path = INFRA_AZURE_DIR / "Pulumi.yaml"
    assert pulumi_yaml_path.exists(), "Pulumi.yaml must exist in infra/azure/"

    content = pulumi_yaml_path.read_text(encoding="utf-8")
    assert "name: nomos-azure" in content
    assert "name: python" in content


def test_pulumi_dev_yaml_structure() -> None:
    """Verify infra/azure/Pulumi.dev.yaml exists and defines expected stack configs."""
    dev_yaml_path = INFRA_AZURE_DIR / "Pulumi.dev.yaml"
    assert dev_yaml_path.exists(), "Pulumi.dev.yaml must exist in infra/azure/"

    content = dev_yaml_path.read_text(encoding="utf-8")
    assert "azure-native:location: eastus" in content
    assert "nomos-azure:environment_name: dev" in content
    assert "nomos-azure:image_repository: ghcr.io/nomos-n4s/nomos" in content
    assert 'nomos-azure:image_tag: "0.11.1"' in content or "nomos-azure:image_tag: '0.11.1'" in content or "nomos-azure:image_tag: 0.11.1" in content


def test_requirements_txt() -> None:
    """Verify infra/azure/requirements.txt specifies required Pulumi packages."""
    req_path = INFRA_AZURE_DIR / "requirements.txt"
    assert req_path.exists(), "requirements.txt must exist in infra/azure/"

    content = req_path.read_text(encoding="utf-8")
    assert "pulumi>=" in content
    assert "pulumi-azure-native>=" in content


def test_config_module_import_and_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify infra/azure/config.py imports and initializes default values cleanly."""
    sys_path_orig = list(sys.path)
    try:
        sys.path.insert(0, str(INFRA_AZURE_DIR))
        config_path = INFRA_AZURE_DIR / "config.py"
        spec = importlib.util.spec_from_file_location("nomos_infra_config", config_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Instantiate configuration
        cfg = module.NomosAzureConfig()
        assert cfg.location == "eastus"
        assert cfg.environment_name == "dev"
        assert cfg.image_tag == "0.11.1"
        assert cfg.full_image == "ghcr.io/nomos-n4s/nomos:0.11.1"
        assert cfg.core_cpu == 0.5
        assert cfg.dashboard_cpu == 0.5
    finally:
        sys.path = sys_path_orig


def test_main_module_importable() -> None:
    """Verify infra/azure/__main__.py exists and defines main()."""
    main_path = INFRA_AZURE_DIR / "__main__.py"
    assert main_path.exists(), "__main__.py must exist in infra/azure/"

    content = main_path.read_text(encoding="utf-8")
    assert "def main()" in content
    assert "pulumi.export(" in content
