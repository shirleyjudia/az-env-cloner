"""
migrate_blobs.py
Migrates blob data from source to destination Storage Account.
Called by orchestrate.py if migrate_data: true in clone_selection.yaml
"""

from azure.storage.blob import BlobServiceClient


def migrate_storage_account(clients: dict, source_rg: str, source_sa_name: str, dest_sa_name: str):
    print(f"\n  Migrating blobs: {source_sa_name} → {dest_sa_name}")
    try:
        source_keys = clients["storage"].storage_accounts.list_keys(source_rg, source_sa_name)
        source_key = source_keys.keys[0].value
        source_client = BlobServiceClient(
            account_url=f"https://{source_sa_name}.blob.core.windows.net",
            credential=source_key
        )
        dest_keys = clients["storage"].storage_accounts.list_keys(source_rg, dest_sa_name)
        dest_key = dest_keys.keys[0].value
        dest_client = BlobServiceClient(
            account_url=f"https://{dest_sa_name}.blob.core.windows.net",
            credential=dest_key
        )
        for container in source_client.list_containers():
            container_name = container["name"]
            print(f"    Copying container: {container_name}")
            source_container = source_client.get_container_client(container_name)
            dest_container = dest_client.get_container_client(container_name)
            try:
                dest_container.create_container()
            except Exception:
                pass
            for blob in source_container.list_blobs():
                source_blob = source_container.get_blob_client(blob.name)
                dest_blob = dest_container.get_blob_client(blob.name)
                dest_blob.start_copy_from_url(source_blob.url)
                print(f"      ✓ {blob.name}")
        print(f"  ✓ Migration complete: {source_sa_name} → {dest_sa_name}")
    except Exception as e:
        print(f"  ✗ Migration failed: {e}")
        raise