resource "azurerm_eventhub_namespace" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = var.sku
  capacity            = var.capacity
  tags                = var.tags
}

resource "azurerm_eventhub" "this" {
  for_each = { for hub in var.hubs : hub.name => hub }

  name                = each.value.name
  namespace_name      = azurerm_eventhub_namespace.this.name
  resource_group_name = var.resource_group_name
  partition_count     = each.value.partition_count
  message_retention   = each.value.message_retention
}

resource "azurerm_eventhub_consumer_group" "this" {
  for_each = {
    for item in flatten([
      for hub in var.hubs : [
        for cg in hub.consumer_groups : {
          key      = "${hub.name}_${cg}"
          hub_name = hub.name
          cg_name  = cg
        }
      ]
    ]) : item.key => item
  }

  name                = each.value.cg_name
  namespace_name      = azurerm_eventhub_namespace.this.name
  eventhub_name       = azurerm_eventhub.this[each.value.hub_name].name
  resource_group_name = var.resource_group_name

  depends_on = [azurerm_eventhub.this]
}

resource "azurerm_eventhub_namespace_authorization_rule" "this" {
  name                = "${var.name}-auth-rule"
  namespace_name      = azurerm_eventhub_namespace.this.name
  resource_group_name = var.resource_group_name
  listen              = true
  send                = true
  manage              = false
}