resource "azurerm_snapshot" "os_snapshot" {
  name                = "${var.dest_vm_name}-os-snapshot"
  location            = var.location
  resource_group_name = var.resource_group_name
  create_option       = "Copy"
  source_uri          = var.source_os_disk_id

  tags = merge(var.tags, {
    snapshot-type = "os"
    source-vm     = var.source_vm_name
  })
}

resource "azurerm_managed_disk" "os_disk" {
  name                 = var.os_disk_name
  location             = var.location
  resource_group_name  = var.resource_group_name
  storage_account_type = var.storage_account_type
  create_option        = "Copy"
  source_resource_id   = azurerm_snapshot.os_snapshot.id

  tags = merge(var.tags, {
    disk-type = "os"
    source-vm = var.source_vm_name
  })
}

resource "azurerm_snapshot" "data_snapshots" {
  for_each = { for disk in var.data_disks : disk.name => disk }

  name                = "${var.dest_vm_name}-data-snapshot-${each.value.lun}"
  location            = var.location
  resource_group_name = var.resource_group_name
  create_option       = "Copy"
  source_uri          = each.value.source_disk_id

  tags = merge(var.tags, {
    snapshot-type = "data"
    source-vm     = var.source_vm_name
    lun           = tostring(each.value.lun)
  })
}

resource "azurerm_managed_disk" "data_disks" {
  for_each = { for disk in var.data_disks : disk.name => disk }

  name                 = each.value.name
  location             = var.location
  resource_group_name  = var.resource_group_name
  storage_account_type = var.storage_account_type
  create_option        = "Copy"
  source_resource_id   = azurerm_snapshot.data_snapshots[each.key].id

  tags = merge(var.tags, {
    disk-type = "data"
    source-vm = var.source_vm_name
    lun       = tostring(each.value.lun)
  })
}

resource "azurerm_network_interface" "this" {
  name                = "${var.dest_vm_name}-nic"
  location            = var.location
  resource_group_name = var.resource_group_name

  ip_configuration {
    name                          = "ipconfig1"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = var.create_public_ip ? azurerm_public_ip.this[0].id : null
  }

  tags = var.tags
}

resource "azurerm_public_ip" "this" {
  count               = var.create_public_ip ? 1 : 0
  name                = "${var.dest_vm_name}-pip"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags
}

resource "azurerm_network_interface_security_group_association" "this" {
  count                     = var.nsg_id != "" ? 1 : 0
  network_interface_id      = azurerm_network_interface.this.id
  network_security_group_id = var.nsg_id
}

resource "azurerm_virtual_machine" "this" {
  name                  = var.dest_vm_name
  location              = var.location
  resource_group_name   = var.resource_group_name
  network_interface_ids = [azurerm_network_interface.this.id]
  vm_size               = var.vm_size

  storage_os_disk {
    name            = azurerm_managed_disk.os_disk.name
    managed_disk_id = azurerm_managed_disk.os_disk.id
    caching         = "ReadWrite"
    create_option   = "Attach"
    os_type         = var.os_type
  }

  dynamic "storage_data_disk" {
    for_each = { for disk in var.data_disks : disk.name => disk }
    content {
      name            = azurerm_managed_disk.data_disks[storage_data_disk.key].name
      managed_disk_id = azurerm_managed_disk.data_disks[storage_data_disk.key].id
      lun             = storage_data_disk.value.lun
      caching         = "None"
      create_option   = "Attach"
    }
  }

  tags = var.tags

  depends_on = [
    azurerm_managed_disk.os_disk,
    azurerm_managed_disk.data_disks,
    azurerm_network_interface.this,
    azurerm_network_interface_security_group_association.this,
  ]
}