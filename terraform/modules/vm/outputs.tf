output "vm_id" {
  value = azurerm_virtual_machine.this.id
}

output "vm_name" {
  value = azurerm_virtual_machine.this.name
}

output "nic_id" {
  value = azurerm_network_interface.this.id
}

output "private_ip" {
  value = azurerm_network_interface.this.private_ip_address
}

output "public_ip" {
  value = var.create_public_ip ? azurerm_public_ip.this[0].ip_address : null
}

output "os_disk_id" {
  value = azurerm_managed_disk.os_disk.id
}