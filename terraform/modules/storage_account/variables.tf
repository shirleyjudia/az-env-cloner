variable "name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "account_tier" {
  type    = string
  default = "Standard"
}

variable "account_replication_type" {
  type    = string
  default = "LRS"
}

variable "account_kind" {
  type    = string
  default = "StorageV2"
}

variable "access_tier" {
  type    = string
  default = "Hot"
}

variable "https_only" {
  type    = bool
  default = true
}

variable "containers" {
  type = list(object({
    name        = string
    access_type = string
  }))
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}