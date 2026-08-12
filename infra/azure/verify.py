"""Automated operational verification script for Nomos Azure Container Apps deployment (#222).

Executes the verification checklist:
1. Fetch stack outputs from Pulumi.
2. Test Core Liveness (/healthz).
3. Test Core Readiness (/readyz).
4. Test Dashboard Accessibility.
5. Verify Container App & Azure Resource status via Azure CLI.
6. Generate verification_report.md.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime
import requests


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    """Run a shell command and return (exit_code, stdout, stderr)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def main() -> None:
    print("=== Nomos Azure Deployment Verification (#222) ===")
    report_lines = [
        "# Azure Container Apps Verification Report",
        f"",
        f"**Timestamp:** {datetime.utcnow().isoformat()}Z",
        f"**Issue:** #222 (Operational Verification Run)",
        f"",
        "## 1. Pulumi Stack Outputs",
    ]

    # 1. Get Stack Outputs
    code, stdout, stderr = run_cmd(["pulumi", "stack", "output", "--json"])
    if code != 0:
        print(f"Error fetching Pulumi stack outputs: {stderr}")
        print("Ensure you are in infra/azure/ and the stack has been provisioned (pulumi up).")
        sys.exit(1)

    try:
        outputs = json.loads(stdout)
    except json.JSONDecodeError as e:
        print(f"Failed to parse Pulumi outputs as JSON: {e}")
        sys.exit(1)

    core_url = outputs.get("core_url", {}).get("value", "")
    dashboard_url = outputs.get("dashboard_url", {}).get("value", "")
    rg_name = outputs.get("resource_group_name", {}).get("value", "")
    kv_name = outputs.get("key_vault_name", {}).get("value", "")

    print(f"  - Resource Group: {rg_name}")
    print(f"  - Key Vault: {kv_name}")
    print(f"  - Core URL: {core_url}")
    print(f"  - Dashboard URL: {dashboard_url}")

    report_lines.extend([
        f"- **Resource Group:** `{rg_name}`",
        f"- **Key Vault:** `{kv_name}`",
        f"- **Core URL:** `{core_url}`",
        f"- **Dashboard URL:** `{dashboard_url}`",
        "",
        "## 2. Endpoint Probes Verification",
    ])

    verification_passed = True

    # 2. Test /healthz (Liveness)
    healthz_url = f"{core_url.rstrip('/')}/healthz"
    print(f"\nTesting Liveness Probe: {healthz_url}")
    try:
        resp = requests.get(healthz_url, timeout=10)
        print(f"  Status: {resp.status_code}")
        print(f"  Body: {resp.text}")
        if resp.status_code == 200:
            report_lines.append(f"- **Liveness (`/healthz`):** ✅ PASSED (HTTP {resp.status_code})")
        else:
            report_lines.append(f"- **Liveness (`/healthz`):** ❌ FAILED (HTTP {resp.status_code})")
            verification_passed = False
    except Exception as e:
        print(f"  Error: {e}")
        report_lines.append(f"- **Liveness (`/healthz`):** ❌ FAILED (Exception: `{e}`)")
        verification_passed = False

    # 3. Test /readyz (Readiness)
    readyz_url = f"{core_url.rstrip('/')}/readyz"
    print(f"\nTesting Readiness Probe: {readyz_url}")
    try:
        resp = requests.get(readyz_url, timeout=10)
        print(f"  Status: {resp.status_code}")
        print(f"  Body: {resp.text}")
        if resp.status_code == 200:
            report_lines.append(f"- **Readiness (`/readyz`):** ✅ PASSED (HTTP {resp.status_code})")
        else:
            report_lines.append(f"- **Readiness (`/readyz`):** ❌ FAILED (HTTP {resp.status_code})")
            verification_passed = False
    except Exception as e:
        print(f"  Error: {e}")
        report_lines.append(f"- **Readiness (`/readyz`):** ❌ FAILED (Exception: `{e}`)")
        verification_passed = False

    # 4. Test Dashboard Accessibility
    print(f"\nTesting Dashboard Accessibility: {dashboard_url}")
    try:
        resp = requests.get(dashboard_url, timeout=10)
        print(f"  Status: {resp.status_code}")
        if resp.status_code in [200, 302, 401]:
            report_lines.append(f"- **Dashboard UI:** ✅ PASSED (HTTP {resp.status_code})")
        else:
            report_lines.append(f"- **Dashboard UI:** ⚠️ WARNING (HTTP {resp.status_code})")
    except Exception as e:
        print(f"  Error: {e}")
        report_lines.append(f"- **Dashboard UI:** ❌ FAILED (Exception: `{e}`)")
        verification_passed = False

    # 5. Azure CLI Resource Health Check
    report_lines.extend([
        "",
        "## 3. Azure Container Apps Runtime Status",
    ])
    print(f"\nChecking Container App status via Azure CLI in RG {rg_name}...")
    code, stdout, stderr = run_cmd([
        "az", "containerapp", "list",
        "--resource-group", rg_name,
        "--output", "json"
    ])
    if code == 0:
        try:
            apps = json.loads(stdout)
            for app in apps:
                name = app.get("name")
                provisioning_state = app.get("properties", {}).get("provisioningState")
                running_status = app.get("properties", {}).get("runningStatus", "Running")
                print(f"  - App '{name}': Provisioning={provisioning_state}, Status={running_status}")
                report_lines.append(f"- **App `{name}`:** Provisioning: `{provisioning_state}`")
        except json.JSONDecodeError:
            report_lines.append("- **Azure CLI App Status:** ⚠️ Could not parse JSON output.")
    else:
        print(f"  Warning: Could not fetch container apps via az cli: {stderr}")
        report_lines.append(f"- **Azure CLI App Status:** ⚠️ Skipped or failed (`{stderr}`)")

    # Conclusion
    report_lines.extend([
        "",
        "## 4. Conclusion & Cost-Safety Action",
    ])
    if verification_passed:
        report_lines.append("**Result:** ✅ All core operational verification checks PASSED successfully.")
        print("\n✅ Verification completed successfully!")
    else:
        report_lines.append("**Result:** ❌ Some verification checks failed. Review logs above.")
        print("\n❌ Verification encountered failures.")

    report_lines.append("\n*Remember the Hard Rule:* Execute `pulumi destroy` immediately after verification concludes to stop billing.")

    report_path = "verification_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"\nReport written to {report_path}")


if __name__ == "__main__":
    main()
