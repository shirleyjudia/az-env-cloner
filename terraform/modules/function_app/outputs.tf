output "function_app_id" {
  value = var.os_type == "Windows" ? azurerm_windows_function_app.this[0].id : azurerm_linux_function_app.this[0].id
}

output "function_app_name" {
  value = var.name
}

output "default_hostname" {
  value = var.os_type == "Windows" ? azurerm_windows_function_app.this[0].default_hostname : azurerm_linux_function_app.this[0].default_hostname
}

output "app_insights_instrumentation_key" {
  value     = azurerm_application_insights.this.instrumentation_key
  sensitive = true
}

output "app_insights_id" {
  value = azurerm_application_insights.this.id
}

output "service_plan_id" {
  value = azurerm_service_plan.this.id
}