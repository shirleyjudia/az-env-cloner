resource "azurerm_service_plan" "this" {
  name                = "${var.name}-asp"
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = var.os_type
  sku_name            = var.sku_name
  tags                = var.tags
}

resource "azurerm_windows_web_app" "this" {
  count               = var.os_type == "Windows" ? 1 : 0
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  service_plan_id     = azurerm_service_plan.this.id
  https_only          = var.https_only

  site_config {
    always_on = var.sku_name == "F1" ? false : true
  }

  app_settings = var.app_settings
  tags         = var.tags
}

resource "azurerm_linux_web_app" "this" {
  count               = var.os_type == "Linux" ? 1 : 0
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  service_plan_id     = azurerm_service_plan.this.id
  https_only          = var.https_only

  site_config {
    always_on = var.sku_name == "F1" ? false : true
  }

  app_settings = var.app_settings
  tags         = var.tags
}

resource "azurerm_application_insights" "this" {
  name                = "${var.name}-ai"
  location            = var.location
  resource_group_name = var.resource_group_name
  application_type    = "web"
  workspace_id        = var.log_analytics_workspace_id
  tags                = var.tags
}