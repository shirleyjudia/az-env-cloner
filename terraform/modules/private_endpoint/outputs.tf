output "private_endpoint_id" {
  value = azurerm_private_endpoint.this.id
}

output "private_endpoint_name" {
  value = azurerm_private_endpoint.this.name
}

output "private_ip_address" {
  value = azurerm_private_endpoint.this.private_service_connection[0].private_ip_address
}

output "dns_zone_ids" {
  value = { for k, v in azurerm_private_dns_zone.this : k => v.id }
}