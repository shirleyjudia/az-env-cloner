"""
orchestrate.py
Main entrypoint for az-env-cloner.
Usage: python orchestrate.py
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
import yaml
from colorama import Fore, Style, init
import platform

AZ_CMD = "az"

init(autoreset=True)

KEYVAULT_NAME = "your-keyvault-name"
INFRA_RG = "your-infra-rg"
OUTPUTS_DIR = "outputs"
CONFIG_DIR = "config"
TERRAFORM_DIR = "terraform"
SESSION_FILE = "outputs/session.json"


def banner():
    print(Fore.CYAN + """
╔══════════════════════════════════════════════╗
║           AZ-ENV-CLONER  v1.0               ║
║   Azure Resource Group Cloning Tool         ║
║   Python + Terraform + Azure SDK            ║
╚══════════════════════════════════════════════╝
""")

def section(title):
    print(Fore.CYAN + f"\n{'━' * 50}\n  {title}\n{'━' * 50}")

def success(msg):
    print(Fore.GREEN + f"  ✓ {msg}")

def warn(msg):
    print(Fore.YELLOW + f"  ⚠ {msg}")

def error(msg):
    print(Fore.RED + f"  ✗ {msg}")

def ask(prompt):
    return input(Fore.WHITE + f"\n  → {prompt}: ").strip()

def confirm(prompt):
    return input(Fore.YELLOW + f"\n  → {prompt} [y/n]: ").strip().lower() == "y"

def save_session(data):
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    return {}

def run_command(cmd, cwd=None):
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            cwd=cwd or os.getcwd(), shell=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def check_prerequisites(session):
    if session.get("prerequisites_passed"):
        success("Prerequisites already checked — skipping")
        return session

    section("STEP 1 — PREREQUISITES CHECK")

    checks = {
        "Python": ["python", "--version"],
        "Terraform": ["terraform", "--version"],
        "Azure CLI": ["az.cmd", "--version"],
        "Git": ["git", "--version"],
    }

    all_passed = True
    for name, cmd in checks.items():
        ok, out, _ = run_command(cmd)
        if ok:
            success(f"{name} found")
        else:
            error(f"{name} not found — please install it first")
            all_passed = False

    print()
    ok, out, err = run_command(["az.cmd", "group", "show", "--name", INFRA_RG])
    if ok:
        success(f"Infra RG found: {INFRA_RG}")
    else:
        error(f"Infra RG '{INFRA_RG}' not found — create it manually first")
        all_passed = False

    ok, out, err = run_command(["az.cmd", "keyvault", "show", "--name", KEYVAULT_NAME])
    if ok:
        success(f"Key Vault found: {KEYVAULT_NAME}")
    else:
        error(f"Key Vault '{KEYVAULT_NAME}' not found — create it manually first")
        all_passed = False

    if not all_passed:
        error("Prerequisites failed — fix the above and run again")
        sys.exit(1)

    success("All prerequisites passed!")
    session["prerequisites_passed"] = True
    save_session(session)
    return session


def collect_run_info(session):
    if session.get("run_info_collected"):
        success("Run info already collected — skipping")
        print(f"    Source RG  : {session['source_rg']}")
        print(f"    Target RG  : {session.get('target_rg', 'will be set during transform')}")
        return session

    section("STEP 2 — RUN INFORMATION")

    source_rg = ask("Enter SOURCE Resource Group name")
    env = ask("Target environment (dev / pat / prod)")
    project_name = ask("Project name (e.g. mssa, mfpa)")
    requested_by = ask("Requested by (PM name or enterprise ID)")
    created_by = ask("Created by (your enterprise ID)")

    print(f"""
  ┌─────────────────────────────────────────┐
  │  SOURCE RG    : {source_rg:<25}│
  │  ENVIRONMENT  : {env:<25}│
  │  PROJECT      : {project_name:<25}│
  │  REQUESTED BY : {requested_by:<25}│
  │  CREATED BY   : {created_by:<25}│
  └─────────────────────────────────────────┘""")

    if not confirm("Is this information correct?"):
        error("Please run again and enter correct information")
        sys.exit(0)

    session.update({
        "source_rg": source_rg, "env": env,
        "project_name": project_name,
        "requested_by": requested_by,
        "created_by": created_by,
        "run_info_collected": True,
        "started_at": datetime.now().isoformat(),
    })
    save_session(session)
    success("Run information saved!")
    return session


def authenticate(session):
    if session.get("authenticated"):
        success("Already authenticated — skipping")
        return session

    section("STEP 3 — AUTHENTICATION")
    sys.path.insert(0, str(Path(__file__).parent))
    from auth.auth import get_azure_clients

    try:
        clients = get_azure_clients(KEYVAULT_NAME)
        session["subscription_id"] = clients["subscription_id"]
        session["authenticated"] = True
        save_session(session)
        success(f"Authenticated — Subscription: {clients['subscription_id']}")
        return session
    except Exception as e:
        error(f"Authentication failed: {e}")
        sys.exit(1)


def discover(session):
    if session.get("discovery_complete"):
        success("Discovery already complete — skipping")
        return session

    section("STEP 4 — DISCOVERY")
    from auth.auth import get_azure_clients
    from discover.discover import discover_resource_group, save_raw_spec, generate_clone_selection

    clients = get_azure_clients(KEYVAULT_NAME)
    spec = discover_resource_group(clients, session["source_rg"])
    save_raw_spec(spec)
    generate_clone_selection(spec)

    session["discovery_complete"] = True
    save_session(session)
    success("Discovery complete!")
    return session


def clone_selection(session):
    if session.get("selection_complete"):
        success("Clone selection already done — skipping")
        return session

    section("STEP 5 — CLONE SELECTION")
    print("\n  Open config/clone_selection.yaml")
    print("  Set clone: true/false for each resource")
    print("  Set migrate_data: true for Storage Accounts if needed\n")
    warn("Edit clone_selection.yaml now")
    input(Fore.YELLOW + "\n  → Press ENTER when done editing...")

    session["selection_complete"] = True
    save_session(session)
    success("Clone selection confirmed!")
    return session


def transform(session):
    if session.get("transform_complete"):
        success("Transform already complete — skipping")
        return session

    section("STEP 6 — TRANSFORM + LOCALIZE")
    from plan.transform import load_raw_spec, load_localize_config, load_clone_selection, transform_spec, save_preview_plan, print_summary

    raw_spec = load_raw_spec()
    config = load_localize_config()
    selection = load_clone_selection()
    plan = transform_spec(raw_spec, config, selection)
    save_preview_plan(plan)
    print_summary(plan)

    session["transform_complete"] = True
    session["target_rg"] = plan["target_rg"]
    save_session(session)
    success("Transform complete!")
    return session


def preflight(session):
    if session.get("preflight_complete"):
        success("Pre-flight already complete — skipping")
        return session

    section("STEP 7 — PRE-FLIGHT CHECKLIST")

    with open(f"{OUTPUTS_DIR}/preview_plan.json", "r") as f:
        plan = json.load(f)

    print(f"""
  ┌─────────────────────────────────────────────┐
  │  SOURCE RG  : {plan['source_rg']:<30}│
  │  TARGET RG  : {plan['target_rg']:<30}│
  │  LOCATION   : {plan['location']:<30}│
  └─────────────────────────────────────────────┘""")

    if plan["resources"]["vnets"]:
        for vnet in plan["resources"]["vnets"]:
            print(f"\n  VNet: {vnet['name']}")
            print(f"  Address space: {vnet['address_space']}")
            if not confirm("  Keep this address space?"):
                new_space = ask("  Enter new address space (e.g. 10.2.0.0/16)")
                vnet["address_space"] = [new_space]
                new_subnet = ask("  Enter new subnet prefix (e.g. 10.2.1.0/24)")
                for subnet in vnet.get("subnets", []):
                    subnet["address_prefix"] = new_subnet
                success(f"Address space updated to {new_space}")

    if plan["resources"]["private_endpoints"]:
        warn("Private endpoints detected — ensure DNS zones don't conflict with source")

    if plan.get("warnings"):
        print(f"\n  ⚠️  {len(plan['warnings'])} warnings:")
        for w in plan["warnings"]:
            warn(w)

    if plan.get("connection_string_updates"):
        success(f"{len(plan['connection_string_updates'])} connection strings will be auto-updated")

    with open(f"{OUTPUTS_DIR}/preview_plan.json", "w") as f:
        json.dump(plan, f, indent=2)

    warn("Review outputs/preview_plan.json carefully")
    input(Fore.YELLOW + "\n  → Press ENTER when you have reviewed preview_plan.json...")

    if not confirm("Pre-flight checks passed — proceed to provisioning?"):
        error("Pre-flight cancelled")
        sys.exit(0)

    session["preflight_complete"] = True
    save_session(session)
    success("Pre-flight complete!")
    return session


def setup_state(session):
    if session.get("state_setup_complete"):
        success("State storage already set up — skipping")
        return session

    section("STEP 8 — TERRAFORM STATE SETUP")

    warn("This will create a storage account in your infra RG")
    if not confirm("Set up Terraform state storage now?"):
        warn("Skipping — terraform will use local state")
        session["state_setup_complete"] = True
        session["tfstate_storage_account"] = "local"
        save_session(session)
        return session

    suggested_name = f"{session['project_name']}tfstate".lower().replace("-", "")[:24]
    print(f"\n  Suggested name: {suggested_name}")
    sa_name = ask("Press ENTER to accept or type a new name")
    if not sa_name:
        sa_name = suggested_name

    ok, out, err = run_command([
        "az", "storage", "account", "create",
        "--name", sa_name, "--resource-group", INFRA_RG,
        "--sku", "Standard_LRS", "--kind", "StorageV2"
    ])

    if not ok:
        error(f"Failed to create storage account: {err}")
        sys.exit(1)

    run_command(["az", "storage", "container", "create", "--name", "tfstate", "--account-name", sa_name])

    session["tfstate_storage_account"] = sa_name
    session["state_setup_complete"] = True
    save_session(session)
    success(f"State storage created: {sa_name}")
    return session


def terraform_plan(session):
    if session.get("terraform_plan_complete"):
        success("Terraform plan already done — skipping")
        return session

    section("STEP 9 — TERRAFORM INIT + PLAN")

    from auth.auth import get_sp_credentials
    creds = get_sp_credentials(KEYVAULT_NAME)
    tfstate_sa = session.get("tfstate_storage_account", "local")

    print("\n  Running terraform init...")
    if tfstate_sa == "local":
        warn("Using local backend")
        ok, out, err = run_command(["terraform", "init", "-reconfigure"], cwd=TERRAFORM_DIR)
    else:
        ok, out, err = run_command([
            "terraform", "init", "-reconfigure",
            f"-backend-config=resource_group_name={INFRA_RG}",
            f"-backend-config=storage_account_name={tfstate_sa}",
            f"-backend-config=container_name=tfstate",
            f"-backend-config=key={session['target_rg']}.tfstate",
        ], cwd=TERRAFORM_DIR)

    if not ok:
        error(f"Terraform init failed: {err}")
        sys.exit(1)

    success("Terraform init complete!")

    print("\n  Running terraform plan...")
    plan_file = f"../{OUTPUTS_DIR}/tfplan"

    ok, out, err = run_command([
        "terraform", "plan",
        f"-var=client_id={creds['client_id']}",
        f"-var=client_secret={creds['client_secret']}",
        f"-var=tenant_id={creds['tenant_id']}",
        f"-var=subscription_id={creds['subscription_id']}",
        f"-var=tfstate_storage_account_name={tfstate_sa}",
        f"-out={plan_file}",
    ], cwd=TERRAFORM_DIR)

    print(out)

    if not ok:
        error(f"Terraform plan failed: {err}")
        print(err)
        sys.exit(1)

    success("Terraform plan complete!")
    warn("Review the plan output above carefully")

    if not confirm("Plan looks good — proceed with terraform apply?"):
        error("Apply cancelled")
        sys.exit(0)

    session["terraform_plan_complete"] = True
    save_session(session)
    return session


def terraform_apply(session):
    if session.get("terraform_apply_complete"):
        success("Terraform apply already complete — skipping")
        return session

    section("STEP 10 — TERRAFORM APPLY")
    warn("This will CREATE real Azure resources!")

    if not confirm("Final confirmation — apply now?"):
        error("Apply cancelled")
        sys.exit(0)

    from auth.auth import get_sp_credentials
    creds = get_sp_credentials(KEYVAULT_NAME)
    tfstate_sa = session.get("tfstate_storage_account", "local")
    plan_file = f"../{OUTPUTS_DIR}/tfplan"

    ok, out, err = run_command([
        "terraform", "apply",
        f"-var=client_id={creds['client_id']}",
        f"-var=client_secret={creds['client_secret']}",
        f"-var=tenant_id={creds['tenant_id']}",
        f"-var=subscription_id={creds['subscription_id']}",
        f"-var=tfstate_storage_account_name={tfstate_sa}",
        "-auto-approve", plan_file,
    ], cwd=TERRAFORM_DIR)

    print(out)

    if not ok:
        error(f"Terraform apply failed: {err}")
        print(err)
        sys.exit(1)

    session["terraform_apply_complete"] = True
    save_session(session)
    success("Terraform apply complete!")
    return session


def data_migration(session):
    if session.get("migration_complete"):
        success("Data migration already complete — skipping")
        return session

    section("STEP 11 — DATA MIGRATION")

    with open(f"{CONFIG_DIR}/clone_selection.yaml", "r") as f:
        selection = yaml.safe_load(f)

    storage_accounts = selection.get("resources", {}).get("storage_accounts", [])
    migrate_storage = [sa for sa in storage_accounts if sa.get("migrate_data")]

    if not migrate_storage:
        success("No data migration selected — skipping")
        session["migration_complete"] = True
        save_session(session)
        return session

    print(f"\n  Storage accounts to migrate: {len(migrate_storage)}")
    for sa in migrate_storage:
        print(f"    → {sa['name']}")

    if confirm("Run storage account data migration now?"):
        from migrate.migrate_blobs import migrate_storage_account
        from auth.auth import get_azure_clients

        clients = get_azure_clients(KEYVAULT_NAME)
        with open(f"{OUTPUTS_DIR}/preview_plan.json", "r") as f:
            plan = json.load(f)

        for sa in migrate_storage:
            source_name = sa["name"]
            target_sa = next(
                (r for r in plan["resources"]["storage_accounts"] if r["source_name"] == source_name), None
            )
            if target_sa:
                migrate_storage_account(clients, session["source_rg"], source_name, target_sa["name"])

    session["migration_complete"] = True
    save_session(session)
    success("Data migration complete!")
    return session


def health_checks(session):
    if session.get("health_checks_complete"):
        success("Health checks already complete — skipping")
        return session

    section("STEP 12 — HEALTH CHECKS + REPORT")
    print("\n  Running health checks on all provisioned resources...")

    from health.health_check import run
    run(KEYVAULT_NAME)

    session["health_checks_complete"] = True
    save_session(session)
    return session


def main():
    banner()
    session = load_session()

    if session:
        print(Fore.YELLOW + f"""
  ⚡ Existing session found!
     Started  : {session.get('started_at', 'unknown')}
     Source RG: {session.get('source_rg', 'unknown')}
     Target RG: {session.get('target_rg', 'unknown')}
        """)
        if confirm("Resume from where you left off?"):
            print(Fore.GREEN + "  ✓ Resuming session...")
        else:
            if confirm("Start fresh?"):
                os.remove(SESSION_FILE)
                session = {}
                success("Session cleared!")
            else:
                sys.exit(0)

    session = check_prerequisites(session)
    session = collect_run_info(session)
    session = authenticate(session)
    session = discover(session)
    session = clone_selection(session)
    session = transform(session)
    session = preflight(session)
    session = setup_state(session)
    session = terraform_plan(session)
    session = terraform_apply(session)
    session = data_migration(session)
    session = health_checks(session)

    print(Fore.GREEN + f"""
╔══════════════════════════════════════════════╗
║           CLONING COMPLETE! 🎉              ║
║                                              ║
║  Source : {session.get('source_rg', ''):<35}║
║  Target : {session.get('target_rg', ''):<35}║
║                                              ║
║  Review outputs/post_provisioning_report.md  ║
╚══════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()