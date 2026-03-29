variable "source_vm_name" {
  type = string
}

variable "dest_vm_name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "vm_size" {
  type = string
}

variable "os_type" {
  type    = string
  default = "Windows"
}

variable "source_os_disk_id" {
  type = string
}

variable "os_disk_name" {
  type = string
}

variable "storage_account_type" {
  type    = string
  default = "Standard_LRS"
}

variable "data_disks" {
  type = list(object({
    name           = string
    source_name    = string
    source_disk_id = string
    lun            = number
    disk_size_gb   = number
    caching        = string
  }))
  default = []
}

variable "subnet_id" {
  type = string
}

variable "nsg_id" {
  type    = string
  default = ""
}

variable "create_public_ip" {
  type    = bool
  default = false
}

variable "tags" {
  type    = map(string)
  default = {}
}