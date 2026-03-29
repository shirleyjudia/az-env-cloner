# Module: vnet
Creates Azure VNet and Subnets. Address space is always new — never copied from source.

## Usage
```hcl
module "vnet" {
  source              = "./modules/vnet"
  name                = "target-vnet"
  location            = "canadacentral"
  resource_group_name = "target-rg"
  address_space       = ["10.1.0.0/16"]
  subnets = [
    { name = "subnet1", address_prefix = "10.1.1.0/24" }
  ]
  tags = {}
}
```