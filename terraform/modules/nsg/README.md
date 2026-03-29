# Module: nsg
Creates Azure NSG with all rules cloned from source.

## Usage
```hcl
module "nsg" {
  source              = "./modules/nsg"
  name                = "target-nsg"
  location            = "canadacentral"
  resource_group_name = "target-rg"
  security_rules      = []
  tags                = {}
}
```