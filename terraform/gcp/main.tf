provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# 1. VPC & Subnet の構築
resource "google_compute_network" "gcp_vpc" {
  name                    = "secure-ai-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "gcp_subnet" {
  name          = "secure-ai-subnet"
  ip_cidr_range = var.gcp_subnet_cidr
  network       = google_compute_network.gcp_vpc.id
  region        = var.gcp_region
}

# 2. Serverless VPC Access Connector (Cloud Run が VPC 内のプライベートIP宛てに通信するために必要)
resource "google_vpc_access_connector" "connector" {
  name          = "run-vpc-connector"
  region        = var.gcp_region
  ip_cidr_range = "10.8.0.0/28" # コネクタ専用の重複しないCIDR
  network       = google_compute_network.gcp_vpc.name
}

# 3. Cloud VPN (Classic VPN または HA VPN - ここでは構成をシンプルに示すため Classic VPN ゲートウェイ)
resource "google_compute_vpn_gateway" "gcp_vpn_gw" {
  name    = "gcp-to-azure-vpn-gw"
  network = google_compute_network.gcp_vpc.id
  region  = var.gcp_region
}

# VPNゲートウェイに静的外部IPを付与
resource "google_compute_address" "vpn_ip" {
  name   = "gcp-vpn-static-ip"
  region = var.gcp_region
}

# 転送ルールの定義（IPsec用プロトコル）
resource "google_compute_forwarding_rule" "fr_esp" {
  name        = "fr-esp"
  region      = var.gcp_region
  ip_address  = google_compute_address.vpn_ip.address
  target      = google_compute_vpn_gateway.gcp_vpn_gw.id
  ip_protocol = "ESP"
}

# Azure VPN ゲートウェイへのVPNトンネル接続設定
resource "google_compute_vpn_tunnel" "tunnel_to_azure" {
  name               = "tunnel-to-azure"
  region             = var.gcp_region
  target_vpn_gateway = google_compute_vpn_gateway.gcp_vpn_gw.id
  shared_secret      = var.vpn_shared_secret
  peer_ip            = "13.xx.xx.xx" # 本来はAzure VPN GatewayのパブリックIPが入る

  ike_version = 2

  local_traffic_selector  = [var.gcp_subnet_cidr]
  remote_traffic_selector = [var.azure_subnet_cidr]

  depends_on = [
    google_compute_forwarding_rule.fr_esp
  ]
}

# 相手側（Azure VNet）への静的ルート
resource "google_compute_route" "route_to_azure" {
  name                = "route-to-azure"
  network             = google_compute_network.gcp_vpc.name
  dest_range          = var.azure_subnet_cidr
  next_hop_vpn_tunnel = google_compute_vpn_tunnel.tunnel_to_azure.id
  priority            = 1000
}

# 4. Workload Identity Federation (Azure Entra ID 連携用)
# これにより、Azure側のリソースがGCPのサービスアカウントトークンをキーレスで取得可能になる
resource "google_iam_workload_identity_pool" "azure_pool" {
  workload_identity_pool_id = "azure-oidc-pool"
  display_name              = "Azure Entra ID Trust Pool"
  description               = "Identity pool for Azure OIDC authentication"
}

resource "google_iam_workload_identity_pool_provider" "azure_provider" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.azure_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "azure-provider"
  display_name                       = "Azure Entra ID Provider"
  
  attribute_mapping = {
    "google.subject" = "assertion.sub"
    "attribute.aud"  = "assertion.aud"
    "attribute.tid"  = "assertion.tid" # Azure Tenant ID
  }
  
  oidc {
    issuer_uri = "https://sts.windows.net/YOUR_AZURE_TENANT_ID/" # 実際にはAzureのテナントIDが入る
  }
}

# 信頼するサービスアカウントと、認証されたAzure OIDC IDの紐付け
resource "google_service_account" "ai_runner_sa" {
  account_id   = "ai-runner-sa"
  display_name = "AI Application Runner Service Account"
}

resource "google_service_account_iam_binding" "wif_user_binding" {
  service_account_id = google_service_account.ai_runner_sa.name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    # 特定のAzure App Registrationからのアクセスのみを許可するよう制約
    "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.azure_pool.name}/attribute.tid/YOUR_AZURE_TENANT_ID"
  ]
}

# Cloud Run デプロイ定義（DLP搭載のStreamlitアプリ）
resource "google_cloud_run_service" "streamlit_app" {
  name     = "secure-ai-streamlit-app"
  location = var.gcp_region

  template {
    spec {
      containers {
        image = "gcr.io/${var.gcp_project_id}/streamlit-secure-app:latest"
        
        env {
          name  = "USE_MOCK_AI"
          value = "false"
        }
        env {
          name  = "AZURE_OPENAI_ENDPOINT"
          value = "https://secure-ai-openai.privatelink.openai.azure.com/" # Private Endpoint用エンドポイント
        }
      }
    }

    metadata {
      annotations = {
        # VPCアクセス接続を有効化し、VPN経由のAzure宛通信をルーティング
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.connector.name
        "run.googleapis.com/vpc-access-egress"    = "all-traffic"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}
