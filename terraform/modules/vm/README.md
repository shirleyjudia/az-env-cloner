# Module: vm
Clones Azure VM using snapshot approach. Tested in production environment.

## How it works
```
Source OS Disk → Snapshot → New OS Disk → Attach to VM
Source Data Disks → Snapshots → New Data Disks → Attach to VM
```

## Important notes
- Domain join must be done manually after provisioning
- NSG association optional — only if source had NSG
- Public IP optional — only if source had public IP