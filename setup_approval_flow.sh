#!/bin/bash

# ==============================================================================
# Mail Approval Flow: Interactive Setup Script 🚀
# ==============================================================================

echo "=================================================="
echo "🛡️  Mail Approval Flow セットアップを開始します"
echo "=================================================="
echo ""
echo "このスクリプトは、メール送受信による承認フローに必要な資格情報を設定し、"
echo "SMTP / IMAP サーバーへのログインテストを実行します。"
echo ""

# 1. 既存の .env ファイルの確認
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
    echo "[!] 警告: すでに .env ファイルが存在します。"
    read -p "上書きして新しく設定しますか？ (y/N): " OVERWRITE
    if [[ ! "$OVERWRITE" =~ ^[yY]$ ]]; then
        echo "[*] セットアップをキャンセルしました。"
        exit 0
    fi
    # バックアップの作成
    cp "$ENV_FILE" "${ENV_FILE}.backup"
    echo "[+] 既存のファイルを ${ENV_FILE}.backup にバックアップしました。"
fi

# 2. 対話形式での設定値の入力
echo ""
echo "--- 📧 1. ボット用メールアドレスの設定 ---"
echo "※ 承認依頼メールを送信し、返信を受信するボット専用のアカウントを使用してください。"
echo "※ Gmailを使用する場合、事前に『2段階認証』を有効にし、『アプリパスワード』を発行する必要があります。"
echo ""

read -p "ボットのメールアドレス (SENDER_EMAIL): " SENDER_EMAIL
while [ -z "$SENDER_EMAIL" ]; do
    echo "[-] エラー: メールアドレスは必須です。"
    read -p "ボットのメールアドレス (SENDER_EMAIL): " SENDER_EMAIL
done

read -s -p "ボットのアプリパスワード (SENDER_PASSWORD): " SENDER_PASSWORD
echo ""
while [ -z "$SENDER_PASSWORD" ]; do
    echo "[-] エラー: パスワードは必須です。"
    read -s -p "ボットのアプリパスワード (SENDER_PASSWORD): " SENDER_PASSWORD
    echo ""
done

echo ""
echo "--- ⚙️  2. メールサーバーの詳細設定 ---"
read -p "SMTP サーバー (デフォルト: smtp.gmail.com): " SMTP_SERVER
SMTP_SERVER=${SMTP_SERVER:-"smtp.gmail.com"}

read -p "SMTP ポート (デフォルト: 587): " SMTP_PORT
SMTP_PORT=${SMTP_PORT:-"587"}

read -p "IMAP サーバー (デフォルト: imap.gmail.com): " IMAP_SERVER
IMAP_SERVER=${IMAP_SERVER:-"imap.gmail.com"}

read -p "IMAP ポート (デフォルト: 993): " IMAP_PORT
IMAP_PORT=${IMAP_PORT:-"993"}

echo ""
echo "--- 👥 3. 承認者の設定 ---"
read -p "承認者のメールアドレス (デフォルト: makoto.insidesales@gmail.com): " APPROVER_EMAIL
APPROVER_EMAIL=${APPROVER_EMAIL:-"makoto.insidesales@gmail.com"}

# 3. .env ファイルの生成
echo ""
echo "[*] .env ファイルを作成しています..."
cat <<EOF > "$ENV_FILE"
# メール承認フロー用設定ファイル (自動生成)
SENDER_EMAIL=$SENDER_EMAIL
SENDER_PASSWORD=$SENDER_PASSWORD
SMTP_SERVER=$SMTP_SERVER
SMTP_PORT=$SMTP_PORT
IMAP_SERVER=$IMAP_SERVER
IMAP_PORT=$IMAP_PORT
APPROVER_EMAIL=$APPROVER_EMAIL
EOF

echo "[+] $ENV_FILE を正常に作成しました。"

# 4. 接続テストの実行
echo ""
echo "=================================================="
echo "📧 メールサーバーへの接続確認テストを実行します..."
echo "=================================================="
echo ""

# venvのpythonがある場合はそれを優先的に使用
if [ -f "./venv/bin/python" ]; then
    PYTHON_CMD="./venv/bin/python"
elif [ -f "./venv/bin/python3" ]; then
    PYTHON_CMD="./venv/bin/python3"
else
    PYTHON_CMD="python3"
fi

$PYTHON_CMD app/approval_flow.py --test-connection

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "=================================================="
    echo "🎉 セットアップと接続テストに成功しました！"
    echo "=================================================="
    echo "これで、本物のメール送受信による承認フローが利用可能です。"
    echo ""
    echo "👉 以下のコマンドで、Terraformの承認付き適用をテストできます："
    echo "   ./deploy_with_approval.sh --cloud azure"
    echo ""
    echo "👉 任意のコマンドを承認付きで実行するには以下を使用します："
    echo "   ./run_with_approval.sh \"My Task\" \"echo 'Task Executed!'\""
    echo "=================================================="
else
    echo "=================================================="
    echo "❌ 接続テストに失敗しました。"
    echo "=================================================="
    echo "メールアドレス、アプリパスワード、またはサーバー設定が正しいか再度確認してください。"
    echo "必要に応じて、再度 ./setup_approval_flow.sh を実行してください。"
    echo "=================================================="
fi
