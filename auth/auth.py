"""
auth.py
Authenticates using Service Principal credentials stored in Azure Key Vault.
Returns authenticated Azure SDK clients for use across the tool.
"""

import sys
import platform
from azure.identity import ClientSecretCredential, AzureCliCredential
from azure.keyvault.secrets import SecretClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.eventhub import EventHubManagementClient
from azure.mgmt.cosmosdb import CosmosDBManagementClient
from azure.mgmt.web import WebSiteManagementClient


def get_sp_credentials(keyvault_name: str) -> dict:
    """
    Reads SP credentials from Key Vault using current az login session.
    Returns dict with client_id, client_secret, tenant_id, subscription_id.
    """
    print(f"\n🔐 Reading SP credentials from Key Vault: {keyvault_name}")

    try:
        credential = AzureCliCredential(process_timeout=120)
        vault_url = f"https://{keyvault_name}.vault.azure.net/"
        secret_client = SecretClient(vault_url=vault_url, credential=credential)

        secrets = {
            "client_id": secret_client.get_secret("sp-client-id").value,
            "client_secret": secret_client.get_secret("sp-client-secret").value,
            "tenant_id": secret_client.get_secret("sp-tenant-id").value,
            "subscription_id": secret_client.get_secret("sp-subscription-id").value,
        }

        print("✓ SP credentials retrieved successfully")
        return secrets

    except Exception as e:
        print(f"✗ Failed to retrieve credentials from Key Vault: {e}")
        raise


def get_azure_clients(keyvault_name: str) -> dict:
    """
    Main function called by all other modules.
    Returns all authenticated Azure SDK clients.
    """
    creds = get_sp_credentials(keyvault_name)

    credential = ClientSecretCredential(
        tenant_id=creds["tenant_id"],
        client_id=creds["client_id"],
        client_secret=creds["client_secret"]
    )

    subscription_id = creds["subscription_id"]

    print("🔄 Initializing Azure SDK clients...")

    clients = {
        "credential": credential,
        "subscription_id": subscription_id,
        "resource": ResourceManagementClient(credential, subscription_id),
        "compute": ComputeManagementClient(credential, subscription_id),
        "network": NetworkManagementClient(credential, subscription_id),
        "storage": StorageManagementClient(credential, subscription_id),
        "eventhub": EventHubManagementClient(credential, subscription_id),
        "cosmosdb": CosmosDBManagementClient(credential, subscription_id),
        "web": WebSiteManagementClient(credential, subscription_id),
    }

    print("✓ All Azure clients initialized successfully\n")
    return clients


if __name__ == "__main__":
    keyvault_name = input("Enter Key Vault name: ").strip()
    try:
        clients = get_azure_clients(keyvault_name)
        print(f"✓ Authentication successful!")
        print(f"✓ Subscription: {clients['subscription_id']}")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        sys.exit(1)