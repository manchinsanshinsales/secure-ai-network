provider "azurerm" {
  features {}
}

# 1. リソースグループの作成
resource "azurerm_resource_group" "rg" {
  name     = var.azure_resource_group_name
  location = var.azure_location;
}

# 2. VNet & Subnet
resource "azurerm_virtual_network" "vnet" {
  name                = "secure-ai-vnet"
  address_space       = [var.azure_vnet_cidr]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "ai_subnet" {
  name                 = "secure-ai-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = [var.azure_subnet_cidr]
}

# VPN Gateway用のサブネット（Azureの命名規則「GatewaySubnet」が必須）
resource "azurerm_subnet" "gw_subnet" {
  name                 = "GatewaySubnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["172.16.2.0/24"]
}

# 3. Azure VPN Gateway
resource "azurerm_public_ip" "vpn_gw_ip" {
  name                = "vpn-gw-ip"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_virtual_network_gateway" "vpn_gw" {
  name                = "azure-to-gcp-vpn-gw"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  type     = "Vpn"
  vpn_type = "RouteBased"

  active_active = false
  enable_bgp    = false
  sku           = "VpnGw1"

  ip_configuration {
    name                          = "vnetGatewayConfig"
    public_ip_address_id          = azurerm_public_ip.vpn_gw_ip.id
    private_ip_address_allocation = "Dynamic"
    subnet_id                     = azurerm_subnet.gw_subnet.id
  }
}

# 対向（GCP）VPNゲートウェイの定義
resource "azurerm_local_network_gateway" "gcp_local_gw" {
  name                = "gcp-local-gw"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  gateway_address     = "35.xx.xx.xx" # 本来はGCPのVPNゲートウェイ静的IPが入る
  address_space       = [var.gcp_subnet_cidr]
}

# VPN接続設定
resource "azurerm_virtual_network_gateway_connection" "conn" {
  name                = "azure-to-gcp-connection"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  type                            = "IPsec"
  virtual_network_gateway_id      = azurerm_virtual_network_gateway.vpn_gw.id
  local_network_gateway_id        = azurerm_local_network_gateway.gcp_local_gw.id
  shared_key                      = var.vpn_shared_secret
  connection_protocol             = "IKEv2"
}

# 4. Azure OpenAI Service 構築
resource "azurerm_cognitive_account" "openai" {
  name                  = "secure-ai-openai-service"
  location              = azurerm_resource_group.rg.location
  resource_group_name   = azurerm_resource_group.rg.name
  kind                  = "OpenAI"
  sku_name              = "S0"
  
  # パブリックネットワークアクセスを無効化（閉域エンドポイント経由のみを許可）
  public_network_access_enabled = false
}

# OpenAI モデル（GPT-4）のデプロイ
resource "azurerm_cognitive_deployment" "gpt4" {
  name                 = "gpt-4"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "gpt-4"
    version = "1106-Preview"
  }
  scale {
    type = "Standard"
  }
}

# 5. Private Endpoint (OpenAI を VNet 内にプライベートIPで公開)
resource "azurerm_private_endpoint" "openai_pe" {
  name                = "openai-private-endpoint"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.ai_subnet.id

  private_service_connection {
    name                           = "openai-privatelink"
    private_connection_resource_id = azurerm_cognitive_account.openai.id
    sub_resource_names              = ["account"]
    is_manual_connection           = false
  }
}

# プライベートDNSゾーンの設定（VNet内での名前解決）
resource "azurerm_private_dns_zone" "openai_dns" {
  name                = "privatelink.openai.azure.com"
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "dns_link" {
  name                  = "openai-dns-vnet-link"
  resource_group_name   = azurerm_resource_group.rg.name
  private_dns_zone_name = azurerm_private_dns_zone.openai_dns.name
  virtual_network_id    = azurerm_virtual_network.vnet.id
}

# Private Endpoint のIPをプライベートDNSに登録
resource "azurerm_private_dns_a_record" "openai_dns_a" {
  name                = "secure-ai-openai"
  zone_name           = azurerm_private_dns_zone.openai_dns.name
  resource_group_name = azurerm_resource_group.rg.name
  ttl                 = 300
  records             = [azurerm_private_endpoint.openai_pe.private_service_connection[0].private_ip_address]
}
