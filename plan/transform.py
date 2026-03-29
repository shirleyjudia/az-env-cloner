"""
transform.py
Reads raw_spec.json + localize.yaml → generates preview_plan.json
"""

import json
import yaml
import os
import sys
import re
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))


def load_raw_spec(path: str = "outputs/raw_spec.json") -> dict:
    if not os.path.exists(path):
        print(f"✗ raw_spec.json not found — run discover/discover.py first!")
        sys.exit(1)
    with open(path, "r") as f:
        return json.load(f)


def load_localize_config(path: str = "config/localize.yaml") -> dict:
    if not os.path.exists(path):
        print(f"✗ localize.yaml not found — creating sample...")
        create_sample_localize(path)
        print(f"  → Open config/localize.yaml, fill in values, then run again.")
        sys.exit(0)
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_clone_selection(path: str = "config/clone_selection.yaml") -> dict:
    if not os.path.exists(path):
        print(f"✗ clone_selection.yaml not found — run discover/discover.py first!")
        sys.exit(1)
    with open(path, "r") as f:
        return yaml.safe_load(f)


def create_sample_localize(path: str):
    sample = {
        "instructions": "Fill in values to control naming transformation.",
        "naming": {
            "change_type": "env_only",
            "source_env": "dev",
            "target_env": "pat",
            "source_project": "",
            "target_project": "",
            "custom_rg_name": "",
        },
        "target": {"location": "", "subscription_id": ""},
        "vnet": {"new_address_space": "10.1.0.0/16", "new_subnet_prefix": "10.1.1.0/24"},
        "tags": {"requested_by": "", "project_name": "", "env": ""}
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(sample, f, default_flow_style=False, sort_keys=False)


def transform_name(name: str, config: dict) -> str:
    change_type = config["naming"]["change_type"]
    source_env = config["naming"].get("source_env", "")
    target_env = config["naming"].get("target_env", "")
    source_project = config["naming"].get("source_project", "")
    target_project = config["naming"].get("target_project", "")

    def replace_preserve_case(match, replacement):
        matched = match.group()
        if matched.isupper():
            return replacement.upper()
        elif matched.islower():
            return replacement.lower()
        elif matched[0].isupper():
            return replacement.capitalize()
        return replacement

    new_name = name

    if change_type in ("env_only", "both"):
        if source_env and target_env:
            pattern = re.compile(re.escape(source_env), re.IGNORECASE)
            new_name = pattern.sub(lambda m: replace_preserve_case(m, target_env), new_name)

    if change_type in ("project_only", "both"):
        if source_project and target_project:
            pattern = re.compile(re.escape(source_project), re.IGNORECASE)
            new_name = pattern.sub(lambda m: replace_preserve_case(m, target_project), new_name)

    return new_name


def transform_rg_name(source_rg: str, config: dict) -> str:
    custom = config["naming"].get("custom_rg_name", "")
    if custom:
        return custom
    return transform_name(source_rg, config)


def update_connection_strings(app_settings: dict, name_map: dict) -> tuple:
    updated = {}
    changes = []
    reserved_settings = [
        "DIAGNOSTICS_AZUREBLOBRETENTIONINDAYS",
        "WEBSITE_HTTPLOGGING_RETENTION_DAYS",
        "WEBSITE_SITE_NAME",
        "WEBSITE_SLOT_NAME",
    ]
    for key, value in app_settings.items():
        if key in reserved_settings:
            continue
        new_value = value
        if isinstance(value, str):
            for source_name, target_name in name_map.items():
                if source_name.lower() in value.lower():
                    pattern = re.compile(re.escape(source_name), re.IGNORECASE)
                    new_value = pattern.sub(target_name, new_value)
                    if new_value != value:
                        changes.append({"setting": key, "source": source_name, "target": target_name})
        updated[key] = new_value
    return updated, changes


def is_selected(name: str, resource_type: str, selected: dict) -> bool:
    resources = selected.get(resource_type, [])
    for r in resources:
        if r["name"] == name:
            return r.get("clone", True)
    return True


def transform_spec(raw_spec: dict, config: dict, selection: dict) -> dict:
    source_rg = raw_spec["source_rg"]
    target_rg = transform_rg_name(source_rg, config)
    location = config["target"].get("location") or (raw_spec["resources"]["vnets"][0]["location"] if raw_spec["resources"]["vnets"] else "canadacentral")

    print(f"\n🔄 Transforming spec...")
    print(f"  Source RG : {source_rg}")
    print(f"  Target RG : {target_rg}")
    print(f"  Location  : {location}")
    print("━" * 50)

    name_map = {}
    plan = {
        "source_rg": source_rg, "target_rg": target_rg,
        "location": location,
        "transformed_at": datetime.utcnow().isoformat(),
        "tags": {
            "cloned-from": source_rg,
            "cloned-date": datetime.utcnow().strftime("%Y-%m-%d"),
            "env": config["tags"].get("env", ""),
            "project-name": config["tags"].get("project_name", ""),
            "requested-by": config["tags"].get("requested_by", ""),
            "created-by": "az-env-cloner",
            "clone-tool": "az-env-cloner",
        },
        "resources": {
            "vnets": [], "nsgs": [], "vms": [],
            "app_services": [], "function_apps": [],
            "storage_accounts": [], "cosmosdb_accounts": [],
            "eventhub_namespaces": [], "private_endpoints": [],
        },
        "connection_string_updates": [],
        "warnings": [],
    }

    selected = selection.get("resources", {})

    # VNets
    print("\n📡 Transforming VNets...")
    for vnet in raw_spec["resources"]["vnets"]:
        if not is_selected(vnet["name"], "vnets", selected):
            print(f"  ⏭ Skipped: {vnet['name']}")
            continue
        new_name = transform_name(vnet["name"], config)
        name_map[vnet["name"]] = new_name
        new_subnets = []
        for subnet in vnet.get("subnets", []):
            new_subnets.append({
                "name": transform_name(subnet["name"], config),
                "address_prefix": config["vnet"].get("new_subnet_prefix") or subnet["address_prefix"],
            })
        plan["resources"]["vnets"].append({
            "source_name": vnet["name"], "name": new_name,
            "location": location,
            "address_space": [config["vnet"].get("new_address_space") or vnet["address_space"][0]],
            "dns_servers": vnet.get("dns_servers", []),
            "subnets": new_subnets, "tags": plan["tags"],
        })
        print(f"  ✓ {vnet['name']} → {new_name}")

    # NSGs
    print("\n🔒 Transforming NSGs...")
    for nsg in raw_spec["resources"]["nsgs"]:
        if not is_selected(nsg["name"], "nsgs", selected):
            print(f"  ⏭ Skipped: {nsg['name']}")
            continue
        new_name = transform_name(nsg["name"], config)
        name_map[nsg["name"]] = new_name
        plan["resources"]["nsgs"].append({
            "source_name": nsg["name"], "name": new_name,
            "location": location,
            "security_rules": nsg.get("security_rules", []),
            "tags": plan["tags"],
        })
        print(f"  ✓ {nsg['name']} → {new_name}")

    # VMs
    print("\n💻 Transforming VMs...")
    for vm in raw_spec["resources"]["vms"]:
        if not is_selected(vm["name"], "vms", selected):
            print(f"  ⏭ Skipped: {vm['name']}")
            continue
        new_name = transform_name(vm["name"], config)
        name_map[vm["name"]] = new_name
        new_disks = []
        for disk in vm.get("data_disks", []):
            new_disks.append({
                "source_name": disk["name"],
                "name": transform_name(disk["name"], config),
                "lun": disk["lun"], "disk_size_gb": disk["disk_size_gb"],
                "source_disk_id": disk["managed_disk_id"], "caching": disk["caching"],
            })
        plan["resources"]["vms"].append({
            "source_name": vm["name"], "name": new_name,
            "location": location, "vm_size": vm["vm_size"],
            "os_type": vm["os_type"],
            "source_os_disk_id": vm["os_disk_id"],
            "os_disk_name": transform_name(vm["os_disk_name"], config),
            "data_disks": new_disks, "tags": plan["tags"],
        })
        print(f"  ✓ {vm['name']} → {new_name}")

    # App Services
    print("\n🌐 Transforming App Services...")
    for app in raw_spec["resources"]["app_services"]:
        if not is_selected(app["name"], "app_services", selected):
            print(f"  ⏭ Skipped: {app['name']}")
            continue
        new_name = transform_name(app["name"], config)
        name_map[app["name"]] = new_name
        updated_settings, changes = update_connection_strings(app.get("app_settings", {}), name_map)
        plan["connection_string_updates"].extend([{"resource": new_name, **c} for c in changes])
        plan["resources"]["app_services"].append({
            "source_name": app["name"], "name": new_name,
            "location": location, "kind": app.get("kind"),
            "runtime": app.get("runtime"),
            "app_service_plan_id": app.get("app_service_plan_id"),
            "https_only": app.get("https_only", True),
            "app_settings": updated_settings, "tags": plan["tags"],
        })
        print(f"  ✓ {app['name']} → {new_name}")

    # Function Apps
    print("\n⚡ Transforming Function Apps...")
    for app in raw_spec["resources"]["function_apps"]:
        if not is_selected(app["name"], "function_apps", selected):
            print(f"  ⏭ Skipped: {app['name']}")
            continue
        new_name = transform_name(app["name"], config)
        name_map[app["name"]] = new_name
        updated_settings, changes = update_connection_strings(app.get("app_settings", {}), name_map)
        plan["connection_string_updates"].extend([{"resource": new_name, **c} for c in changes])
        plan["resources"]["function_apps"].append({
            "source_name": app["name"], "name": new_name,
            "location": location, "kind": app.get("kind"),
            "runtime": app.get("runtime"),
            "app_service_plan_id": app.get("app_service_plan_id"),
            "https_only": app.get("https_only", True),
            "app_settings": updated_settings, "tags": plan["tags"],
        })
        print(f"  ✓ {app['name']} → {new_name}")

    # Storage Accounts
    print("\n💾 Transforming Storage Accounts...")
    for sa in raw_spec["resources"]["storage_accounts"]:
        if not is_selected(sa["name"], "storage_accounts", selected):
            print(f"  ⏭ Skipped: {sa['name']}")
            continue
        new_name = transform_name(sa["name"], config)
        name_map[sa["name"]] = new_name
        plan["resources"]["storage_accounts"].append({
            "source_name": sa["name"], "name": new_name,
            "location": location, "sku": sa.get("sku", "Standard_LRS"),
            "kind": sa.get("kind", "StorageV2"),
            "access_tier": sa.get("access_tier", "Hot"),
            "https_only": sa.get("https_only", True), "tags": plan["tags"],
        })
        print(f"  ✓ {sa['name']} → {new_name}")

    # CosmosDB
    print("\n🌍 Transforming CosmosDB...")
    for cosmos in raw_spec["resources"]["cosmosdb_accounts"]:
        if not is_selected(cosmos["name"], "cosmosdb_accounts", selected):
            print(f"  ⏭ Skipped: {cosmos['name']}")
            continue
        new_name = transform_name(cosmos["name"], config)
        name_map[cosmos["name"]] = new_name
        plan["resources"]["cosmosdb_accounts"].append({
            "source_name": cosmos["name"], "name": new_name,
            "location": location, "kind": cosmos.get("kind", "GlobalDocumentDB"),
            "consistency_level": cosmos.get("consistency_level", "Session"),
            "databases": cosmos.get("databases", []), "tags": plan["tags"],
        })
        print(f"  ✓ {cosmos['name']} → {new_name}")

    # EventHub
    print("\n📨 Transforming EventHub...")
    for ns in raw_spec["resources"]["eventhub_namespaces"]:
        if not is_selected(ns["name"], "eventhub_namespaces", selected):
            print(f"  ⏭ Skipped: {ns['name']}")
            continue
        new_name = transform_name(ns["name"], config)
        name_map[ns["name"]] = new_name
        plan["resources"]["eventhub_namespaces"].append({
            "source_name": ns["name"], "name": new_name,
            "location": location, "sku": ns.get("sku", "Standard"),
            "capacity": ns.get("capacity", 1),
            "hubs": ns.get("hubs", []), "tags": plan["tags"],
        })
        print(f"  ✓ {ns['name']} → {new_name}")

    # Private Endpoints
    print("\n🔗 Transforming Private Endpoints...")
    for pe in raw_spec["resources"]["private_endpoints"]:
        if not is_selected(pe["name"], "private_endpoints", selected):
            print(f"  ⏭ Skipped: {pe['name']}")
            continue
        new_name = transform_name(pe["name"], config)
        name_map[pe["name"]] = new_name
        subnet_id = pe.get("subnet_id", "")
        if source_rg.lower() in subnet_id.lower():
            new_subnet_id = subnet_id.replace(source_rg, target_rg)
        else:
            new_subnet_id = subnet_id
            plan["warnings"].append(f"Private Endpoint {new_name} connects to external subnet: {subnet_id}")
        plan["resources"]["private_endpoints"].append({
            "source_name": pe["name"], "name": new_name,
            "location": location, "subnet_id": new_subnet_id,
            "private_link_service_id": pe.get("private_link_service_id"),
            "group_ids": pe.get("group_ids", []), "tags": plan["tags"],
        })
        print(f"  ✓ {pe['name']} → {new_name}")

    return plan


def save_preview_plan(plan: dict, output_path: str = "outputs/preview_plan.json"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(plan, f, indent=2, default=str)
    print(f"\n✓ Preview plan saved: {output_path}")


def print_summary(plan: dict):
    print("\n" + "━" * 50)
    print("📋 TRANSFORMATION SUMMARY")
    print("━" * 50)
    print(f"  {plan['source_rg']} → {plan['target_rg']}")
    total = 0
    for rtype, resources in plan["resources"].items():
        if resources:
            print(f"  {rtype:25} {len(resources)} resource(s)")
            total += len(resources)
    print(f"\n  Total resources : {total}")
    if plan["connection_string_updates"]:
        print(f"  🔄 Connection string updates: {len(plan['connection_string_updates'])}")
    if plan["warnings"]:
        print(f"  ⚠️  Warnings: {len(plan['warnings'])}")
    print("━" * 50)


if __name__ == "__main__":
    raw_spec = load_raw_spec()
    config = load_localize_config()
    selection = load_clone_selection()
    plan = transform_spec(raw_spec, config, selection)
    save_preview_plan(plan)
    print_summary(plan)
    print("\n✓ Transform complete!")