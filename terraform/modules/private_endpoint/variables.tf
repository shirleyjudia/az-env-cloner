variable "name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "subnet_id" {
  type = string
}

variable "private_link_service_id" {
  type = string
}

variable "group_ids" {
  type    = list(string)
  default = []
}

variable "private_dns_zone_ids" {
  type    = list(string)
  default = []
}

variable "dns_zones" {
  type = list(object({
    name = string
  }))
  default = []
}

variable "vnet_id" {
  type    = string
  default = ""
}

variable "is_external_subnet" {
  type    = bool
  default = false
}

variable "tags" {
  type    = map(string)
  default = {}
}