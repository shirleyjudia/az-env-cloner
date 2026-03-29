resource "azurerm_private_endpoint" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id

  private_service_connection {
    name                           = "${var.name}-psc"
    private_connection_resource_id = var.private_link_service_id
    is_manual_connection           = false
    subresource_names              = var.group_ids
  }

  dynamic "private_dns_zone_group" {
    for_each = length(var.private_dns_zone_ids) > 0 ? [1] : []
    content {
      name                 = "${var.name}-dzg"
      private_dns_zone_ids = var.private_dns_zone_ids
    }
  }

  tags = var.tags
}

resource "azurerm_private_dns_zone" "this" {
  for_each            = { for zone in var.dns_zones : zone.name => zone }
  name                = each.value.name
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "this" {
  for_each              = { for zone in var.dns_zones : zone.name => zone }
  name                  = "${each.value.name}-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.this[each.key].name
  virtual_network_id    = var.vnet_id
  registration_enabled  = false
  tags                  = var.tags
}