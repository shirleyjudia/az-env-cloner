"""
discover.py
Reads all resources from source Resource Group using Azure SDK.
Outputs:
  - outputs/raw_spec.json
  - config/clone_selection.yaml
"""

import json
import yaml
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from auth.auth import get_azure_clients


def discover_resource_group(clients: dict, source_rg: str) -> dict:
    print(f"\n🔍 Discovering resources in: {source_rg}")
    print("━" * 50)

    spec = {
        "source_rg": source_rg,
        "discovered_at": datetime.utcnow().isoformat(),
        "resources": {
            "vnets": [], "nsgs": [], "vms": [],
            "app_services": [], "function_apps": [],
            "storage_accounts": [], "cosmosdb_accounts": [],
            "eventhub_namespaces": [], "private_endpoints": [],
        }
    }

    # VNets
    print("\n📡 Discovering VNets...")
    try:
        for vnet in clients["network"].virtual_networks.list(source_rg):
            subnets = []
            for subnet in vnet.subnets or []:
                subnets.append({
                    "name": subnet.name,
                    "address_prefix": subnet.address_prefix,
                    "nsg_id": subnet.network_security_group.id if subnet.network_security_group else None,
                })
            spec["resources"]["vnets"].append({
                "name": vnet.name, "location": vnet.location,
                "address_space": vnet.address_space.address_prefixes,
                "dns_servers": vnet.dhcp_options.dns_servers if vnet.dhcp_options else [],
                "tags": dict(vnet.tags) if vnet.tags else {},
                "subnets": subnets,
            })
            print(f"  ✓ VNet: {vnet.name}")
    except Exception as e:
        print(f"  ⚠ VNet discovery failed: {e}")

    # NSGs
    print("\n🔒 Discovering NSGs...")
    try:
        for nsg in clients["network"].network_security_groups.list(source_rg):
            rules = []
            for rule in nsg.security_rules or []:
                rules.append({
                    "name": rule.name, "priority": rule.priority,
                    "direction": rule.direction, "access": rule.access,
                    "protocol": rule.protocol,
                    "source_port_range": rule.source_port_range,
                    "destination_port_range": rule.destination_port_range,
                    "source_address_prefix": rule.source_address_prefix,
                    "destination_address_prefix": rule.destination_address_prefix,
                })
            spec["resources"]["nsgs"].append({
                "name": nsg.name, "location": nsg.location,
                "tags": dict(nsg.tags) if nsg.tags else {},
                "security_rules": rules,
            })
            print(f"  ✓ NSG: {nsg.name}")
    except Exception as e:
        print(f"  ⚠ NSG discovery failed: {e}")

    # VMs
    print("\n💻 Discovering VMs...")
    try:
        for vm in clients["compute"].virtual_machines.list(source_rg):
            data_disks = []
            for disk in vm.storage_profile.data_disks or []:
                data_disks.append({
                    "name": disk.name, "lun": disk.lun,
                    "disk_size_gb": disk.disk_size_gb,
                    "managed_disk_id": disk.managed_disk.id if disk.managed_disk else None,
                    "caching": disk.caching,
                })
            spec["resources"]["vms"].append({
                "name": vm.name, "location": vm.location,
                "vm_size": vm.hardware_profile.vm_size,
                "os_type": vm.storage_profile.os_disk.os_type,
                "os_disk_name": vm.storage_profile.os_disk.name,
                "os_disk_id": vm.storage_profile.os_disk.managed_disk.id if vm.storage_profile.os_disk.managed_disk else None,
                "os_disk_size_gb": vm.storage_profile.os_disk.disk_size_gb,
                "data_disks": data_disks,
                "tags": dict(vm.tags) if vm.tags else {},
            })
            print(f"  ✓ VM: {vm.name}")
    except Exception as e:
        print(f"  ⚠ VM discovery failed: {e}")

    # App Services + Function Apps
    print("\n🌐 Discovering App Services and Function Apps...")
    try:
        for app in clients["web"].web_apps.list_by_resource_group(source_rg):
            try:
                settings = clients["web"].web_apps.list_application_settings(source_rg, app.name)
                app_settings = dict(settings.properties) if settings.properties else {}
            except Exception:
                app_settings = {}

            resource = {
                "name": app.name, "location": app.location,
                "kind": app.kind,
                "runtime": app.site_config.linux_fx_version if app.site_config else None,
                "app_service_plan_id": app.server_farm_id,
                "https_only": app.https_only,
                "app_settings": app_settings,
                "tags": dict(app.tags) if app.tags else {},
            }

            if app.kind and "functionapp" in app.kind.lower():
                spec["resources"]["function_apps"].append(resource)
                print(f"  ✓ Function App: {app.name}")
            else:
                spec["resources"]["app_services"].append(resource)
                print(f"  ✓ App Service: {app.name}")
    except Exception as e:
        print(f"  ⚠ App Service discovery failed: {e}")

    # Storage Accounts
    print("\n💾 Discovering Storage Accounts...")
    try:
        for sa in clients["storage"].storage_accounts.list_by_resource_group(source_rg):
            spec["resources"]["storage_accounts"].append({
                "name": sa.name, "location": sa.location,
                "sku": sa.sku.name, "kind": sa.kind,
                "access_tier": sa.access_tier,
                "https_only": sa.enable_https_traffic_only,
                "tags": dict(sa.tags) if sa.tags else {},
            })
            print(f"  ✓ Storage Account: {sa.name}")
    except Exception as e:
        print(f"  ⚠ Storage Account discovery failed: {e}")

    # CosmosDB
    print("\n🌍 Discovering CosmosDB Accounts...")
    try:
        for cosmos in clients["cosmosdb"].database_accounts.list_by_resource_group(source_rg):
            databases = []
            try:
                for db in clients["cosmosdb"].sql_resources.list_sql_databases(source_rg, cosmos.name):
                    containers = []
                    try:
                        for cont in clients["cosmosdb"].sql_resources.list_sql_containers(source_rg, cosmos.name, db.name):
                            containers.append({
                                "name": cont.name,
                                "partition_key": cont.resource.partition_key.paths if cont.resource.partition_key else [],
                                "default_ttl": cont.resource.default_ttl,
                            })
                    except Exception:
                        pass
                    databases.append({"name": db.name, "containers": containers})
            except Exception:
                pass
            spec["resources"]["cosmosdb_accounts"].append({
                "name": cosmos.name, "location": cosmos.location,
                "kind": cosmos.kind,
                "consistency_level": cosmos.consistency_policy.default_consistency_level if cosmos.consistency_policy else None,
                "databases": databases,
                "tags": dict(cosmos.tags) if cosmos.tags else {},
            })
            print(f"  ✓ CosmosDB: {cosmos.name}")
    except Exception as e:
        print(f"  ⚠ CosmosDB discovery failed: {e}")

    # EventHub
    print("\n📨 Discovering EventHub Namespaces...")
    try:
        for ns in clients["eventhub"].namespaces.list_by_resource_group(source_rg):
            hubs = []
            try:
                for hub in clients["eventhub"].event_hubs.list_by_namespace(source_rg, ns.name):
                    consumer_groups = []
                    try:
                        cgs = clients["eventhub"].consumer_groups.list_by_event_hub(source_rg, ns.name, hub.name)
                        consumer_groups = [cg.name for cg in cgs if cg.name != "$Default"]
                    except Exception:
                        pass
                    hubs.append({
                        "name": hub.name,
                        "partition_count": hub.partition_count,
                        "message_retention": hub.message_retention_in_days,
                        "consumer_groups": consumer_groups,
                    })
            except Exception:
                pass
            spec["resources"]["eventhub_namespaces"].append({
                "name": ns.name, "location": ns.location,
                "sku": ns.sku.name, "capacity": ns.sku.capacity,
                "hubs": hubs,
                "tags": dict(ns.tags) if ns.tags else {},
            })
            print(f"  ✓ EventHub: {ns.name}")
    except Exception as e:
        print(f"  ⚠ EventHub discovery failed: {e}")

    # Private Endpoints
    print("\n🔗 Discovering Private Endpoints...")
    try:
        for pe in clients["network"].private_endpoints.list(source_rg):
            spec["resources"]["private_endpoints"].append({
                "name": pe.name, "location": pe.location,
                "subnet_id": pe.subnet.id if pe.subnet else None,
                "private_link_service_id": pe.private_link_service_connections[0].private_link_service_id if pe.private_link_service_connections else None,
                "group_ids": pe.private_link_service_connections[0].group_ids if pe.private_link_service_connections else [],
                "tags": dict(pe.tags) if pe.tags else {},
            })
            print(f"  ✓ Private Endpoint: {pe.name}")
    except Exception as e:
        print(f"  ⚠ Private Endpoint discovery failed: {e}")

    return spec


def save_raw_spec(spec: dict, output_path: str = "outputs/raw_spec.json"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(spec, f, indent=2, default=str)
    print(f"\n✓ Raw spec saved: {output_path}")


def generate_clone_selection(spec: dict, output_path: str = "config/clone_selection.yaml"):
    selection = {
        "instructions": "Set clone to true to include, false to skip.",
        "resources": {}
    }
    for resource_type, resources in spec["resources"].items():
        if resources:
            selection["resources"][resource_type] = []
            for resource in resources:
                selection["resources"][resource_type].append({
                    "name": resource["name"],
                    "clone": True,
                    "migrate_data": False,
                })
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        yaml.dump(selection, f, default_flow_style=False, sort_keys=False)
    print(f"✓ Clone selection saved: {output_path}")


if __name__ == "__main__":
    keyvault_name = input("Enter Key Vault name: ").strip()
    source_rg = input("Enter source Resource Group name: ").strip()
    clients = get_azure_clients(keyvault_name)
    spec = discover_resource_group(clients, source_rg)
    save_raw_spec(spec)
    generate_clone_selection(spec)
    print("\n✓ Discovery complete!")