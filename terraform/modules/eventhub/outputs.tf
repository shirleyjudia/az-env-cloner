output "namespace_id" {
  value = azurerm_eventhub_namespace.this.id
}

output "namespace_name" {
  value = azurerm_eventhub_namespace.this.name
}

output "primary_connection_string" {
  value     = azurerm_eventhub_namespace_authorization_rule.this.primary_connection_string
  sensitive = true
}

output "secondary_connection_string" {
  value     = azurerm_eventhub_namespace_authorization_rule.this.secondary_connection_string
  sensitive = true
}

output "hub_names" {
  value = keys(azurerm_eventhub.this)
}