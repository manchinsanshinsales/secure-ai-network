variable "gcp_project_id" {
  type        = string
  description = "GCP Project ID"
  default     = "your-gcp-project-id"
}

variable "gcp_region" {
  type        = string
  description = "GCP Region for resources"
  default     = "us-central1"
}

variable "azure_location" {
  type        = string
  description = "Azure Location for resources"
  default     = "eastus"
}

variable "azure_resource_group_name" {
  type        = string
  description = "Azure Resource Group Name"
  default     = "rg-secure-ai-network"
}

# ネットワークCIDRブロックの定義
variable "gcp_vpc_cidr" {
  type        = string
  description = "CIDR block for GCP VPC"
  default     = "10.0.0.0/16"
}

variable "gcp_subnet_cidr" {
  type        = string
  description = "CIDR block for GCP Cloud Run subnet"
  default     = "10.0.1.0/24"
}

variable "azure_vnet_cidr" {
  type        = string
  description = "CIDR block for Azure VNet"
  default     = "172.16.0.0/16"
}

variable "azure_subnet_cidr" {
  type        = string
  description = "CIDR block for Azure OpenAI Private Endpoint Subnet"
  default     = "172.16.1.0/24"
}

variable "vpn_shared_secret" {
  type        = string
  description = "Shared secret key for IPsec VPN Tunnel"
  default     = "SuperSecretVPNTunnelKey2026!"
  sensitive   = true
}
