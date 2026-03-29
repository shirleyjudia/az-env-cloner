resource "azurerm_cosmosdb_account" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  offer_type          = "Standard"
  kind                = var.kind

  consistency_policy {
    consistency_level = var.consistency_level
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }

  tags = var.tags
}

resource "azurerm_cosmosdb_sql_database" "this" {
  for_each = { for db in var.databases : db.name => db }

  name                = each.value.name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
}

resource "azurerm_cosmosdb_sql_container" "this" {
  for_each = {
    for item in flatten([
      for db in var.databases : [
        for container in db.containers : {
          key           = "${db.name}_${container.name}"
          db_name       = db.name
          name          = container.name
          partition_key = container.partition_key
          default_ttl   = container.default_ttl
        }
      ]
    ]) : item.key => item
  }

  name                = each.value.name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  database_name       = each.value.db_name
  partition_key_paths = each.value.partition_key

  dynamic "autoscale_settings" {
    for_each = var.autoscale_max_throughput > 0 ? [1] : []
    content {
      max_throughput = var.autoscale_max_throughput
    }
  }

  default_ttl = each.value.default_ttl

  depends_on = [azurerm_cosmosdb_sql_database.this]
}