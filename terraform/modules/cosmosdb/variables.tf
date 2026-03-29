variable "name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "kind" {
  type    = string
  default = "GlobalDocumentDB"
}

variable "consistency_level" {
  type    = string
  default = "Session"
}

variable "autoscale_max_throughput" {
  type    = number
  default = 0
}

variable "databases" {
  type = list(object({
    name = string
    containers = list(object({
      name          = string
      partition_key = list(string)
      default_ttl   = optional(number, -1)
    }))
  }))
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}