"""
health_check.py
Runs post-provisioning health checks on all cloned resources.
Generates post_provisioning_report.md
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from auth.auth import get_azure_clients


def check_resource_group(clients, rg_name):
    try:
        rg = clients["resource"].resource_groups.get(rg_name)
        return {"name": rg_name, "type": "Resource Group", "status": "✅ Healthy", "notes": f"State: {rg.properties.provisioning_state}"}
    except Exception as e:
        return {"name": rg_name, "type": "Resource Group", "status": "❌ Failed", "notes": str(e)}


def check_vnet(clients, rg_name, vnet_name):
    try:
        vnet = clients["network"].virtual_networks.get(rg_name, vnet_name)
        return {"name": vnet_name, "type": "VNet", "status": "✅ Healthy" if vnet.provisioning_state == "Succeeded" else "⚠️ Degraded", "notes": f"State: {vnet.provisioning_state}"}
    except Exception as e:
        return {"name": vnet_name, "type": "VNet", "status": "❌ Failed", "notes": str(e)}


def check_vm(clients, rg_name, vm_name):
    try:
        vm = clients["compute"].virtual_machines.get(rg_name, vm_name, expand="instanceView")
        statuses = vm.instance_view.statuses if vm.instance_view else []
        power_state = next((s.display_status for s in statuses if "PowerState" in s.code), "Unknown")
        return {"name": vm_name, "type": "VM", "status": "✅ Running" if power_state == "VM running" else "⚠️ Not Running", "notes": f"Power state: {power_state}"}
    except Exception as e:
        return {"name": vm_name, "type": "VM", "status": "❌ Failed", "notes": str(e)}


def check_storage_account(clients, rg_name, sa_name):
    try:
        sa = clients["storage"].storage_accounts.get_properties(rg_name, sa_name)
        return {"name": sa_name, "type": "Storage Account", "status": "✅ Healthy" if sa.provisioning_state == "Succeeded" else "⚠️ Degraded", "notes": f"State: {sa.provisioning_state}"}
    except Exception as e:
        return {"name": sa_name, "type": "Storage Account", "status": "❌ Failed", "notes": str(e)}


def check_app_service(clients, rg_name, app_name):
    try:
        app = clients["web"].web_apps.get(rg_name, app_name)
        return {"name": app_name, "type": "App Service", "status": "✅ Running" if app.state == "Running" else "⚠️ Not Running", "notes": f"State: {app.state}"}
    except Exception as e:
        return {"name": app_name, "type": "App Service", "status": "❌ Failed", "notes": str(e)}


def check_function_app(clients, rg_name, app_name):
    try:
        app = clients["web"].web_apps.get(rg_name, app_name)
        return {"name": app_name, "type": "Function App", "status": "✅ Running" if app.state == "Running" else "⚠️ Not Running", "notes": f"State: {app.state}"}
    except Exception as e:
        return {"name": app_name, "type": "Function App", "status": "❌ Failed", "notes": str(e)}


def check_cosmosdb(clients, rg_name, cosmos_name):
    try:
        cosmos = clients["cosmosdb"].database_accounts.get(rg_name, cosmos_name)
        return {"name": cosmos_name, "type": "CosmosDB", "status": "✅ Healthy" if cosmos.provisioning_state == "Succeeded" else "⚠️ Degraded", "notes": f"State: {cosmos.provisioning_state}"}
    except Exception as e:
        return {"name": cosmos_name, "type": "CosmosDB", "status": "❌ Failed", "notes": str(e)}


def check_eventhub(clients, rg_name, ns_name):
    try:
        ns = clients["eventhub"].namespaces.get(rg_name, ns_name)
        return {"name": ns_name, "type": "EventHub", "status": "✅ Healthy" if ns.provisioning_state == "Succeeded" else "⚠️ Degraded", "notes": f"State: {ns.provisioning_state}"}
    except Exception as e:
        return {"name": ns_name, "type": "EventHub", "status": "❌ Failed", "notes": str(e)}


def check_private_endpoint(clients, rg_name, pe_name):
    try:
        pe = clients["network"].private_endpoints.get(rg_name, pe_name)
        connections = pe.private_link_service_connections or []
        state = connections[0].private_link_service_connection_state.status if connections else "Unknown"
        return {"name": pe_name, "type": "Private Endpoint", "status": "✅ Approved" if state == "Approved" else f"⚠️ {state}", "notes": f"Connection state: {state}"}
    except Exception as e:
        return {"name": pe_name, "type": "Private Endpoint", "status": "❌ Failed", "notes": str(e)}


def run_health_checks(clients: dict, plan: dict) -> dict:
    target_rg = plan["target_rg"]
    results = []

    print(f"\n🏥 Running health checks on: {target_rg}")
    print("━" * 50)

    print("\n📦 Checking Resource Group...")
    r = check_resource_group(clients, target_rg)
    results.append(r)
    print(f"  {r['status']} {r['name']}")

    print("\n📡 Checking VNets...")
    for vnet in plan["resources"].get("vnets", []):
        r = check_vnet(clients, target_rg, vnet["name"])
        results.append(r)
        print(f"  {r['status']} {r['name']}")

    print("\n💻 Checking VMs...")
    for vm in plan["resources"].get("vms", []):
        r = check_vm(clients, target_rg, vm["name"])
        results.append(r)
        print(f"  {r['status']} {r['name']}")

    print("\n🌐 Checking App Services...")
    for app in plan["resources"].get("app_services", []):
        r = check_app_service(clients, target_rg, app["name"])
        results.append(r)
        print(f"  {r['status']} {r['name']}")

    print("\n⚡ Checking Function Apps...")
    for app in plan["resources"].get("function_apps", []):
        r = check_function_app(clients, target_rg, app["name"])
        results.append(r)
        print(f"  {r['status']} {r['name']}")

    print("\n💾 Checking Storage Accounts...")
    for sa in plan["resources"].get("storage_accounts", []):
        r = check_storage_account(clients, target_rg, sa["name"])
        results.append(r)
        print(f"  {r['status']} {r['name']}")

    print("\n🌍 Checking CosmosDB...")
    for cosmos in plan["resources"].get("cosmosdb_accounts", []):
        r = check_cosmosdb(clients, target_rg, cosmos["name"])
        results.append(r)
        print(f"  {r['status']} {r['name']}")

    print("\n📨 Checking EventHub...")
    for ns in plan["resources"].get("eventhub_namespaces", []):
        r = check_eventhub(clients, target_rg, ns["name"])
        results.append(r)
        print(f"  {r['status']} {r['name']}")

    print("\n🔗 Checking Private Endpoints...")
    for pe in plan["resources"].get("private_endpoints", []):
        r = check_private_endpoint(clients, target_rg, pe["name"])
        results.append(r)
        print(f"  {r['status']} {r['name']}")

    return {
        "target_rg": target_rg,
        "source_rg": plan["source_rg"],
        "checked_at": datetime.now().isoformat(),
        "results": results,
        "warnings": plan.get("warnings", []),
        "connection_string_updates": plan.get("connection_string_updates", []),
    }


def generate_report(health_data: dict, output_path: str = "outputs/post_provisioning_report.md"):
    results = health_data["results"]
    healthy = [r for r in results if "✅" in r["status"]]
    degraded = [r for r in results if "⚠️" in r["status"]]
    failed = [r for r in results if "❌" in r["status"]]

    report = f"""# Post Provisioning Report
Generated: {health_data['checked_at']}

## Clone Summary
| Field | Value |
|-------|-------|
| Source RG | {health_data['source_rg']} |
| Target RG | {health_data['target_rg']} |
| Total Resources | {len(results)} |
| Healthy | {len(healthy)} |
| Degraded | {len(degraded)} |
| Failed | {len(failed)} |

## Health Check Results
| Resource | Type | Status | Notes |
|----------|------|--------|-------|
"""
    for r in results:
        report += f"| {r['name']} | {r['type']} | {r['status']} | {r['notes']} |\n"

    if health_data.get("connection_string_updates"):
        report += "\n## Connection String Updates Applied\n| Resource | Setting | Updated |\n|----------|---------|----------|\n"
        for update in health_data["connection_string_updates"]:
            report += f"| {update['resource']} | {update['setting']} | ✅ Auto-updated |\n"

    if health_data.get("warnings"):
        report += "\n## Warnings — Manual Action Required\n"
        for i, warning in enumerate(health_data["warnings"], 1):
            report += f"{i}. ⚠️ {warning}\n"

    report += """
## Manual Actions Checklist
- [ ] Domain join VMs to active directory
- [ ] Verify external private endpoint connectivity
- [ ] Update any external secrets not auto-updated
- [ ] Test end to end connectivity between resources
- [ ] Review all warnings above and take action

## Tool Information
- **Tool**: az-env-cloner
- **GitHub**: github.com/shirleyjudia/az-env-cloner
- **Generated by**: az-env-cloner v1.0
"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n✓ Report saved: {output_path}")


def run(keyvault_name: str, plan_path: str = "outputs/preview_plan.json"):
    with open(plan_path, "r") as f:
        plan = json.load(f)
    clients = get_azure_clients(keyvault_name)
    health_data = run_health_checks(clients, plan)
    generate_report(health_data)
    results = health_data["results"]
    healthy = len([r for r in results if "✅" in r["status"]])
    degraded = len([r for r in results if "⚠️" in r["status"]])
    failed = len([r for r in results if "❌" in r["status"]])
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 HEALTH CHECK SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ Healthy   : {healthy}
  ⚠️  Degraded  : {degraded}
  ❌ Failed    : {failed}
  Total        : {len(results)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)


if __name__ == "__main__":
    KEYVAULT_NAME = "your-keyvault-name"

    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("\n🧪 TEST MODE — Running against source RG")
        clients = get_azure_clients(KEYVAULT_NAME)
        test_plan = {
            "source_rg": "source-rg-name",
            "target_rg": "source-rg-name",
            "resources": {
                "vnets": [{"name": "dev-vnet"}],
                "vms": [{"name": "dev-vm01"}],
                "app_services": [{"name": "dev-webapp"}],
                "function_apps": [{"name": "dev-funcapp"}],
                "storage_accounts": [{"name": "devstorageaccount"}],
                "cosmosdb_accounts": [{"name": "dev-cosmos-db"}],
                "eventhub_namespaces": [{"name": "dev-eventhub-ns"}],
                "private_endpoints": [{"name": "dev-pe"}],
            },
            "warnings": [],
            "connection_string_updates": []
        }
        health_data = run_health_checks(clients, test_plan)
        generate_report(health_data)
        results = health_data["results"]
        healthy = len([r for r in results if "✅" in r["status"]])
        degraded = len([r for r in results if "⚠️" in r["status"]])
        failed = len([r for r in results if "❌" in r["status"]])
        print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 HEALTH CHECK SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ Healthy   : {healthy}
  ⚠️  Degraded  : {degraded}
  ❌ Failed    : {failed}
  Total        : {len(results)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)
        input("\n  → Press ENTER to exit...")
    else:
        run(KEYVAULT_NAME)