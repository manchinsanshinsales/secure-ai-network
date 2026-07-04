#!/bin/bash

# ==============================================================================
# Terraform Deploy with Mail Approval Flow
#
# このスクリプトは、Terraform の変更計画 (plan) を実行し、
# 承認メール (makoto.insidesales@gmail.com 宛て) を送信して、
# 承認が得られた場合のみ自動的に適用 (apply) を実行する実用的なデプロイフローです。
# ==============================================================================

# .env ファイルがあれば読み込む
if [ -f .env ]; then
    # コメント行を除外してエクスポート
    export $(grep -v '^#' .env | xargs)
fi

# デフォルト設定
APPROVER=${APPROVER_EMAIL:-"makoto.insidesales@gmail.com"}
SIMULATE_FLAG=""
TARGET_CLOUD="azure" # "azure" または "gcp"

# ヘルプ表示
show_help() {
    echo "Usage: ./deploy_with_approval.sh [options]"
    echo ""
    echo "Options:"
    echo "  --cloud <azure|gcp>  ターゲットとするクラウド環境 (デフォルト: azure)"
    echo "  --simulate           実際のメール送受信をせず、コンソール上で承認を模擬する"
    echo "  --help               このヘルプを表示する"
    echo ""
    echo "Examples:"
    echo "  # シミュレーションモードでAzureのデプロイをテスト"
    echo "  ./deploy_with_approval.sh --cloud azure --simulate"
    echo ""
    echo "  # 本物のメール送信でGCPのデプロイをテスト（.envの設定が必要）"
    echo "  ./deploy_with_approval.sh --cloud gcp"
}

# 引数解析
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --cloud) TARGET_CLOUD="$2"; shift ;;
        --simulate) SIMULATE_FLAG="--simulate" ;;
        --help) show_help; exit 0 ;;
        *) echo "Unknown parameter: $1"; show_help; exit 1 ;;
    esac
    shift
done

# クラウド名のバリデーション
if [ "$TARGET_CLOUD" != "azure" ] && [ "$TARGET_CLOUD" != "gcp" ]; then
    echo "[-] Error: --cloud には azure または gcp を指定してください。"
    exit 1
fi

TF_DIR="terraform/$TARGET_CLOUD"
echo "[*] 対象インフラ: $TARGET_CLOUD (ディレクトリ: $TF_DIR)"

# 1. Terraform Planの実行
echo "[*] Terraform Plan を実行して変更点を確認しています..."

# 実際の実機で動かす場合は、terraform init & plan が必要ですが、
# ポートフォリオ/デモ環境での実行を想定し、Terraformが無い場合や初期化未済の場合はモックのplanを生成します。
if command -v terraform &> /dev/null && [ -f "$TF_DIR/main.tf" ]; then
    # 実環境での実行
    cd "$TF_DIR" || exit 1
    terraform init -backend=false > /dev/null 2>&1
    PLAN_OUTPUT=$(terraform plan -no-color 2>&1)
    cd - > /dev/null || exit 1
else
    # モック/シミュレーション環境での実行
    echo "[!] 本格的なTerraform実行環境が検出されなかったため、デモ用の変更計画(Plan)を生成します。"
    if [ "$TARGET_CLOUD" == "azure" ]; then
        PLAN_OUTPUT=$(cat <<EOF
Terraform will perform the following actions:

  # azurerm_virtual_network.vnet will be created
  + resource "azurerm_virtual_network" "vnet" {
      + address_space       = [ "172.16.0.0/16" ]
      + id                  = (known after apply)
      + location            = "eastus"
      + name                = "secure-ai-vnet"
    }

  # azurerm_cognitive_account.openai will be created
  + resource "azurerm_cognitive_account" "openai" {
      + custom_subdomain_name         = (known after apply)
      + id                            = (known after apply)
      + kind                          = "OpenAI"
      + name                          = "secure-ai-openai-service"
      + public_network_access_enabled = false
    }

Plan: 2 to add, 0 to change, 0 to destroy.
EOF
)
    else
        PLAN_OUTPUT=$(cat <<EOF
Terraform will perform the following actions:

  # google_compute_network.gcp_vpc will be created
  + resource "google_compute_network" "gcp_vpc" {
      + auto_create_subnetworks = false
      + id                      = (known after apply)
      + name                    = "secure-ai-vpc"
    }

  # google_service_account.ai_runner_sa will be created
  + resource "google_service_account" "ai_runner_sa" {
      + account_id   = "ai-runner-sa"
      + display_name = "AI Application Runner Service Account"
    }

Plan: 2 to add, 0 to change, 0 to destroy.
EOF
)
    fi
fi

# Plan結果の表示
echo "----------------------------------------"
echo "$PLAN_OUTPUT"
echo "----------------------------------------"

# 2. 承認プロセスのトリガー
TASK_NAME="Terraform Apply ($TARGET_CLOUD)"
APPLY_CMD="echo '[+] Terraform Apply ($TARGET_CLOUD) が正常に適用されました。'"

# 実際のTerraform実行環境があれば、本物のapplyコマンドにする
if command -v terraform &> /dev/null && [ -f "$TF_DIR/main.tf" ]; then
    APPLY_CMD="cd $TF_DIR && terraform apply -auto-approve"
fi

echo "[*] 承認依頼を開始します。"
echo "[*] 承認宛先: $APPROVER"
echo ""

# メール本文に含めるためにPlanの出力を整形（長すぎる場合は末尾をカット）
PLAN_SUMMARY=$(echo "$PLAN_OUTPUT" | tail -n 25)

# run_with_approval.sh を呼び出す
./run_with_approval.sh "$TASK_NAME" "$APPLY_CMD" --details "$PLAN_SUMMARY" $SIMULATE_FLAG
