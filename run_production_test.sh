#!/bin/bash

# ==============================================================================
# Production Mail Approval Flow Tester 🚀
# ==============================================================================

echo "=================================================="
echo "📧 本番メール承認フローの接続テストを開始します"
echo "=================================================="
echo ""
echo "このスクリプトは、本物のメール（Gmail 等）を利用して、"
echo "makoto.insidesales@gmail.com 宛てに承認依頼を送信し、"
echo "返信を検知して実行するフローの動作確認を行います。"
echo ""

ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
    echo "[!] 警告: 既に .env ファイルが存在します。"
    echo "    既存の設定はバックアップされます。"
    cp "$ENV_FILE" "${ENV_FILE}.backup"
    echo "[+] 既存のファイルを ${ENV_FILE}.backup に退避しました。"
fi

# 1. 接続情報の入力
echo "--- 🔑 ボット用メールサーバーの資格情報を入力してください ---"
echo "※ Gmail を使用する場合、事前に「2段階認証」を有効にし、「アプリパスワード」を発行してください。"
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
echo "--- ⚙️  メールサーバーの詳細設定 ---"
read -p "SMTP サーバー (デフォルト: smtp.gmail.com): " SMTP_SERVER
SMTP_SERVER=${SMTP_SERVER:-"smtp.gmail.com"}

read -p "SMTP ポート (デフォルト: 587): " SMTP_PORT
SMTP_PORT=${SMTP_PORT:-"587"}

read -p "IMAP サーバー (デフォルト: imap.gmail.com): " IMAP_SERVER
IMAP_SERVER=${IMAP_SERVER:-"imap.gmail.com"}

read -p "IMAP ポート (デフォルト: 993): " IMAP_PORT
IMAP_PORT=${IMAP_PORT:-"993"}

APPROVER_EMAIL="makoto.insidesales@gmail.com"

# 2. .env ファイルの生成
cat <<EOF > "$ENV_FILE"
# メール承認フロー用設定ファイル (本番用)
SENDER_EMAIL=$SENDER_EMAIL
SENDER_PASSWORD=$SENDER_PASSWORD
SMTP_SERVER=$SMTP_SERVER
SMTP_PORT=$SMTP_PORT
IMAP_SERVER=$IMAP_SERVER
IMAP_PORT=$IMAP_PORT
APPROVER_EMAIL=$APPROVER_EMAIL
EOF

echo ""
echo "[+] $ENV_FILE を本番用の設定で作成しました。"
echo ""

# venvのpythonがある場合はそれを優先的に使用
if [ -f "./venv/bin/python" ]; then
    PYTHON_CMD="./venv/bin/python"
elif [ -f "./venv/bin/python3" ]; then
    PYTHON_CMD="./venv/bin/python3"
else
    PYTHON_CMD="python3"
fi

# 3. 接続テストの実行
echo "=================================================="
echo "📧 メールサーバーへの接続テストを実行します..."
echo "=================================================="
$PYTHON_CMD app/approval_flow.py --test-connection

TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ メールサーバーへの接続またはログインに失敗しました。"
    echo "   設定内容（特にアプリパスワード）を再確認し、再度実行してください。"
    exit 1
fi

echo ""
echo "🎉 接続テストに成功しました！"
echo "これより、実際に $APPROVER_EMAIL 宛に承認依頼メールを送信します。"
echo "メールを受信したら、本文の先頭に「APPROVE」または「承認」と書いて返信してください。"
echo "システムが自動で検知し、指定されたテストコマンドを実行します。"
echo "=================================================="
echo ""

# 4. 本番承認フローの実行
./run_with_approval.sh "本番メール接続確認タスク" "echo '[+] 承認メールの返信が正常に検知され、タスクが実行されました！'"
