variable "client_id" {
  description = "Service Principal client ID"
  type        = string
  sensitive   = true
}

variable "client_secret" {
  description = "Service Principal client secret"
  type        = string
  sensitive   = true
}

variable "tenant_id" {
  description = "Azure tenant ID"
  type        = string
  sensitive   = true
}

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "tfstate_storage_account_name" {
  description = "Storage account name for Terraform state"
  type        = string
}

variable "fallback_storage_account_name" {
  description = "Fallback storage account name for function apps"
  type        = string
  default     = ""
}

variable "fallback_storage_account_key" {
  description = "Fallback storage account key for function apps"
  type        = string
  sensitive   = true
  default     = ""
}