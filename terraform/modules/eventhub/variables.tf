variable "name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "sku" {
  type    = string
  default = "Standard"
}

variable "capacity" {
  type    = number
  default = 1
}

variable "hubs" {
  type = list(object({
    name              = string
    partition_count   = number
    message_retention = number
    consumer_groups   = list(string)
  }))
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}