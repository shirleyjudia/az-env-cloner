output "vnet_id" {
  value = azurerm_virtual_network.this.id
}

output "vnet_name" {
  value = azurerm_virtual_network.this.name
}

output "subnet_ids" {
  value = { for k, v in azurerm_subnet.this : k => v.id }
}

output "subnet_names" {
  value = keys(azurerm_subnet.this)
}