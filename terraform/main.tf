terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
  client_id       = var.client_id
  client_secret   = var.client_secret
  tenant_id       = var.tenant_id
  subscription_id = var.subscription_id
}

locals {
  plan = try(jsondecode(file("${path.module}/../outputs/preview_plan.json")), null)
  tags = try(local.plan.tags, {})
}

# ─────────────────────────────────────────
# Resource Group
# ─────────────────────────────────────────

module "resource_group" {
  source   = "./modules/resource_group"
  name     = local.plan.target_rg
  location = local.plan.location
  tags     = local.tags
}

# ─────────────────────────────────────────
# Networking
# ─────────────────────────────────────────

module "vnet" {
  for_each = { for vnet in local.plan.resources.vnets : vnet.name => vnet }

  source              = "./modules/vnet"
  name                = each.value.name
  location            = local.plan.location
  resource_group_name = module.resource_group.name
  address_space       = each.value.address_space
  dns_servers         = each.value.dns_servers
  subnets             = each.value.subnets
  tags                = local.tags

  depends_on = [module.resource_group]
}

module "nsg" {
  for_each = { for nsg in local.plan.resources.nsgs : nsg.name => nsg }

  source              = "./modules/nsg"
  name                = each.value.name
  location            = local.plan.location
  resource_group_name = module.resource_group.name
  security_rules      = each.value.security_rules
  tags                = local.tags

  depends_on = [module.resource_group]
}

# ─────────────────────────────────────────
# Compute
# ─────────────────────────────────────────

module "vm" {
  for_each = { for vm in local.plan.resources.vms : vm.name => vm }

  source               = "./modules/vm"
  source_vm_name       = each.value.source_name
  dest_vm_name         = each.value.name
  location             = local.plan.location
  resource_group_name  = module.resource_group.name
  vm_size              = each.value.vm_size
  os_type              = each.value.os_type
  source_os_disk_id    = each.value.source_os_disk_id
  os_disk_name         = each.value.os_disk_name
  storage_account_type = "Standard_LRS"
  data_disks           = each.value.data_disks
  subnet_id            = length(module.vnet) > 0 ? values(module.vnet)[0].subnet_ids[keys(values(module.vnet)[0].subnet_ids)[0]] : ""
  nsg_id               = length(module.nsg) > 0 ? values(module.nsg)[0].nsg_id : ""
  create_public_ip     = false
  tags                 = local.tags

  depends_on = [module.vnet, module.nsg]
}

# ─────────────────────────────────────────
# Data Layer
# ─────────────────────────────────────────

module "storage_account" {
  for_each = { for sa in local.plan.resources.storage_accounts : sa.name => sa }

  source                   = "./modules/storage_account"
  name                     = each.value.name
  location                 = local.plan.location
  resource_group_name      = module.resource_group.name
  account_tier             = split("_", each.value.sku)[0]
  account_replication_type = split("_", each.value.sku)[1]
  account_kind             = each.value.kind
  access_tier              = each.value.access_tier
  https_only               = each.value.https_only
  containers               = []
  tags                     = local.tags

  depends_on = [module.resource_group]
}

module "cosmosdb" {
  for_each = { for db in local.plan.resources.cosmosdb_accounts : db.name => db }

  source              = "./modules/cosmosdb"
  name                = each.value.name
  location            = local.plan.location
  resource_group_name = module.resource_group.name
  kind                = each.value.kind
  consistency_level   = each.value.consistency_level
  databases           = each.value.databases
  tags                = local.tags

  depends_on = [module.resource_group]
}

module "eventhub" {
  for_each = { for ns in local.plan.resources.eventhub_namespaces : ns.name => ns }

  source              = "./modules/eventhub"
  name                = each.value.name
  location            = local.plan.location
  resource_group_name = module.resource_group.name
  sku                 = each.value.sku
  capacity            = each.value.capacity
  hubs                = each.value.hubs
  tags                = local.tags

  depends_on = [module.resource_group]
}

# ─────────────────────────────────────────
# App Layer
# ─────────────────────────────────────────

module "log_analytics" {
  source              = "./modules/log_analytics"
  name                = "${local.plan.target_rg}-law"
  location            = local.plan.location
  resource_group_name = module.resource_group.name
  tags                = local.tags

  depends_on = [module.resource_group]
}

module "app_service" {
  for_each = { for app in local.plan.resources.app_services : app.name => app }

  source                     = "./modules/app_service"
  name                       = each.value.name
  location                   = local.plan.location
  resource_group_name        = module.resource_group.name
  os_type                    = "Windows"
  sku_name                   = "B1"
  https_only                 = each.value.https_only
  app_settings               = each.value.app_settings
  log_analytics_workspace_id = module.log_analytics.workspace_id
  tags                       = local.tags

  depends_on = [module.resource_group, module.log_analytics]
}

module "function_app" {
  for_each = { for app in local.plan.resources.function_apps : app.name => app }

  source                     = "./modules/function_app"
  name                       = each.value.name
  location                   = local.plan.location
  resource_group_name        = module.resource_group.name
  os_type                    = "Windows"
  sku_name                   = "Y1"
  https_only                 = each.value.https_only
  storage_account_name       = length(module.storage_account) > 0 ? values(module.storage_account)[0].storage_account_name : var.fallback_storage_account_name
  storage_account_access_key = length(module.storage_account) > 0 ? values(module.storage_account)[0].primary_access_key : var.fallback_storage_account_key
  app_settings               = each.value.app_settings
  log_analytics_workspace_id = module.log_analytics.workspace_id
  tags                       = local.tags

  depends_on = [module.resource_group, module.storage_account, module.log_analytics]
}

# ─────────────────────────────────────────
# Integration Layer
# ─────────────────────────────────────────

module "private_endpoint" {
  for_each = { for pe in local.plan.resources.private_endpoints : pe.name => pe }

  source                  = "./modules/private_endpoint"
  name                    = each.value.name
  location                = local.plan.location
  resource_group_name     = module.resource_group.name
  subnet_id               = each.value.subnet_id
  private_link_service_id = each.value.private_link_service_id
  group_ids               = each.value.group_ids
  vnet_id                 = length(module.vnet) > 0 ? values(module.vnet)[0].vnet_id : ""
  dns_zones               = []
  tags                    = local.tags

  depends_on = [
    module.vnet, module.app_service,
    module.function_app, module.storage_account,
    module.cosmosdb, module.eventhub,
  ]
}