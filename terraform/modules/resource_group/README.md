# Module: resource_group
Creates an Azure Resource Group.

## Usage
```hcl
module "resource_group" {
  source   = "./modules/resource_group"
  name     = "target-rg"
  location = "canadacentral"
  tags     = {}
}
```