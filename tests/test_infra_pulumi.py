"""Tests for infra/azure Pulumi IaC configuration and module structure."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
INFRA_AZURE_DIR = REPO_ROOT / "infra" / "azure"
MANIFEST_PATH = REPO_ROOT / ".release-please-manifest.json"


def _manifest_version() -> str:
    """Return the release-please manifest version (the deploy tag's source of truth)."""
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["."]


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
    # image_tag is intentionally absent: it derives from the release manifest
    # (see config._default_image_tag) so it can never drift from the release.
    assert "nomos-azure:image_tag" not in content


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
        version = _manifest_version()
        assert cfg.image_tag == version
        assert cfg.full_image == f"ghcr.io/nomos-n4s/nomos:{version}"
        assert cfg.core_cpu == 0.5
        assert cfg.dashboard_cpu == 0.5
    finally:
        sys.path = sys_path_orig


def test_image_tag_tracks_release_manifest() -> None:
    """The derived default image tag must equal the release-please manifest version.

    Guards against reintroducing a hardcoded literal that would silently
    deploy a stale image (the drift this module was created to prevent).
    """
    sys_path_orig = list(sys.path)
    try:
        sys.path.insert(0, str(INFRA_AZURE_DIR))
        config_path = INFRA_AZURE_DIR / "config.py"
        spec = importlib.util.spec_from_file_location("nomos_infra_config", config_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert module._default_image_tag() == _manifest_version()
    finally:
        sys.path = sys_path_orig


def test_default_image_tag_raises_actionable_error_when_manifest_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing/unreadable manifest must raise a clear RuntimeError, not a bare
    FileNotFoundError, and must not silently fall back to a hardcoded tag."""
    sys_path_orig = list(sys.path)
    try:
        sys.path.insert(0, str(INFRA_AZURE_DIR))
        config_path = INFRA_AZURE_DIR / "config.py"
        spec = importlib.util.spec_from_file_location("nomos_infra_config", config_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        monkeypatch.setattr(
            module, "_MANIFEST_PATH", INFRA_AZURE_DIR / "does-not-exist.json"
        )
        with pytest.raises(RuntimeError, match="image_tag"):
            module._default_image_tag()
    finally:
        sys.path = sys_path_orig


def test_main_module_importable() -> None:
    """Verify infra/azure/__main__.py exists and defines main()."""
    main_path = INFRA_AZURE_DIR / "__main__.py"
    assert main_path.exists(), "__main__.py must exist in infra/azure/"

    content = main_path.read_text(encoding="utf-8")
    assert "def main()" in content
    assert "pulumi.export(" in content
