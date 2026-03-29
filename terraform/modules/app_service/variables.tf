variable "name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "os_type" {
  type    = string
  default = "Windows"
}

variable "sku_name" {
  type    = string
  default = "B1"
}

variable "https_only" {
  type    = bool
  default = true
}

variable "app_settings" {
  type    = map(string)
  default = {}
}

variable "log_analytics_workspace_id" {
  type    = string
  default = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}