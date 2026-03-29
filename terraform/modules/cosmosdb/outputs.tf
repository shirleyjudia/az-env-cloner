output "cosmosdb_id" {
  value = azurerm_cosmosdb_account.this.id
}

output "cosmosdb_name" {
  value = azurerm_cosmosdb_account.this.name
}

output "endpoint" {
  value = azurerm_cosmosdb_account.this.endpoint
}

output "primary_key" {
  value     = azurerm_cosmosdb_account.this.primary_key
  sensitive = true
}

output "primary_connection_string" {
  value     = azurerm_cosmosdb_account.this.primary_sql_connection_string
  sensitive = true
}