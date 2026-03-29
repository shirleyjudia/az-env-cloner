output "workspace_id" {
  value = azurerm_log_analytics_workspace.this.id
}

output "workspace_name" {
  value = azurerm_log_analytics_workspace.this.name
}

output "primary_shared_key" {
  value     = azurerm_log_analytics_workspace.this.primary_shared_key
  sensitive = true
}