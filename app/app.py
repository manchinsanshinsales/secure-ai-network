import streamlit as st
import os
import sys
import pandas as pd
import uuid
import time
import subprocess

# 同一ディレクトリのモジュールをインポートできるようにパスを追加
sys.path.append(os.path.dirname(__file__))

from dlp import SecureDlpManager
from ai_client import SecureAiClient
from approval_flow import send_approval_request, check_for_approval, DEFAULT_APPROVER

# ページ基本設定
st.set_page_config(
    page_title="Secure AI Network & Mail Approval Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# プレミアムなCSSスタイルの注入 (グラデーションヘッダー、ダークモード最適化、美しいカードスタイル)
st.markdown("""
<style>
    /* メインヘッダーのグラデーション */
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    
    .main-header h1 {
        margin: 0;
        font-family: 'Outfit', 'Inter', sans-serif;
        font-size: 2.5rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1.1rem;
    }
    
    /* 監査カードのスタイル */
    .audit-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }
    
    html[theme="dark"] .audit-card {
        background-color: #1e2430;
        border: 1px solid #2d3748;
    }
    
    .badge {
        padding: 0.25rem 0.6rem;
        border-radius: 50px;
        font-size: 0.8rem;
        font-weight: bold;
        color: white;
    }
    .badge-gcp { background-color: #4285F4; }
    .badge-azure { background-color: #0089D6; }
    
    /* チャットメッセージのスタイル */
    .chat-bubble {
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        line-height: 1.5;
    }
    .user-bubble {
        background-color: #e3f2fd;
        border-left: 5px solid #2196f3;
    }
    .ai-bubble {
        background-color: #f1f8e9;
        border-left: 5px solid #8bc34a;
    }
    html[theme="dark"] .user-bubble {
        background-color: #1a2c3d;
        border-left: 5px solid #2196f3;
    }
    html[theme="dark"] .ai-bubble {
        background-color: #1e2d1a;
        border-left: 5px solid #8bc34a;
    }
</style>
""", unsafe_allow_html=True)

# セッション状態の初期化
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "dlp_manager" not in st.session_state:
    st.session_state.dlp_manager = SecureDlpManager()

# メール承認デモ用のセッション初期化
if "approval_status" not in st.session_state:
    st.session_state.approval_status = "idle"  # idle, waiting, approved, rejected
if "approval_task_id" not in st.session_state:
    st.session_state.approval_task_id = ""
if "approval_task_name" not in st.session_state:
    st.session_state.approval_task_name = ""
if "approval_command" not in st.session_state:
    st.session_state.approval_command = ""
if "approval_logs" not in st.session_state:
    st.session_state.approval_logs = []
if "approval_start_time" not in st.session_state:
    st.session_state.approval_start_time = 0.0

# タイトルの表示
st.markdown("""
<div class="main-header">
    <h1>🛡️ Multi-Cloud Secure AI & Mail Approval</h1>
    <p>GCP & Azure 閉域連携 / DLP / メール返信型承認自動化デモ</p>
</div>
""", unsafe_allow_html=True)

# サイドバーの設定
st.sidebar.title("🛠️ 設定 & パラメータ")

# 1. 接続モードの選択
mode_selection = st.sidebar.radio(
    "動作モードを選択:",
    ["シミュレーション (モックモード)", "クラウド実機 API 接続"],
    help="実際のクラウドインフラが未構築、または停止している間は『シミュレーション』を選択してください。DLPの動作と接続フローが確認できます。"
)
use_mock = (mode_selection == "シミュレーション (モックモード)")

# 2. AIプロバイダーの選択
provider = st.sidebar.selectbox(
    "接続先 AI プロバイダー:",
    ["Azure OpenAI (VNet 閉域経由)", "GCP Vertex AI (Gemini / PSC経由)"]
)

# 3. クラウド環境変数の入力（実機モード時のみ）
if not use_mock:
    st.sidebar.subheader("🔑 クラウド認証資格情報")
    if "Azure" in provider:
        azure_key = st.sidebar.text_input("Azure OpenAI API Key:", type="password")
        azure_endpoint = st.sidebar.text_input("Azure Endpoint:", value="https://your-resource.openai.azure.com/")
        azure_deploy = st.sidebar.text_input("Deployment Name:", value="gpt-4")
        
        os.environ["AZURE_OPENAI_API_KEY"] = azure_key
        os.environ["AZURE_OPENAI_ENDPOINT"] = azure_endpoint
        os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = azure_deploy
    else:
        gcp_project = st.sidebar.text_input("GCP Project ID:", value="your-gcp-project")
        gcp_location = st.sidebar.text_input("GCP Location:", value="us-central1")
        gcp_model = st.sidebar.text_input("Vertex Model:", value="gemini-1.5-pro")
        
        os.environ["GCP_PROJECT_ID"] = gcp_project
        os.environ["GCP_LOCATION"] = gcp_location
        os.environ["GCP_VERTEX_MODEL"] = gcp_model

# 4. DLP検知対象のカスタマイズ
st.sidebar.subheader("🔒 DLP 検知フィルタ")
enable_phone = st.sidebar.checkbox("電話番号 (PHONE_NUMBER)", value=True)
enable_email = st.sidebar.checkbox("メールアドレス (EMAIL_ADDRESS)", value=True)
enable_cc = st.sidebar.checkbox("クレジットカード (CREDIT_CARD)", value=True)
enable_secret = st.sidebar.checkbox("APIキー / シークレット (API_KEY_SECRET)", value=True)
enable_mynumber = st.sidebar.checkbox("マイナンバー (JP_MYNUMBER)", value=True)
enable_zip = st.sidebar.checkbox("郵便番号 (JP_ZIP)", value=True)

# 5. クライアントの初期化
ai_client = SecureAiClient(use_mock=use_mock)

# タブ構成の定義
tab1, tab2, tab3 = st.tabs([
    "💬 セキュア AI チャット & DLP 監査",
    "📧 メール承認フロー (Mail Approval)",
    "📄 インフラ設計 & ドキュメント"
])

# ==========================================
# タブ1: チャット & DLP監査
# ==========================================
with tab1:
    col_chat, col_audit = st.columns([1, 1])
    
    with col_chat:
        st.subheader("💬 セキュア AI チャット")
        st.info("※ 入力されたプロンプトは自動的にDLPスキャンされ、個人情報・機密情報はマスキングした上で安全にクラウドAIへ送信されます。")
        
        # 履歴のクリアボタン
        if st.button("チャット履歴をクリア"):
            st.session_state.chat_history = []
            st.rerun()
        
        # チャット履歴表示
        chat_container = st.container(height=400)
        with chat_container:
            for chat in st.session_state.chat_history:
                role_label = "👤 ユーザー (送信データ)" if chat["role"] == "user" else "🤖 AI 応答"
                bubble_class = "user-bubble" if chat["role"] == "user" else "ai-bubble"
                st.markdown(f"**{role_label}**")
                st.markdown(f'<div class="chat-bubble {bubble_class}">{chat["content"]}</div>', unsafe_allow_html=True)
                if "provider" in chat:
                    badge_type = "badge-azure" if "Azure" in chat["provider"] else "badge-gcp"
                    st.markdown(f'<span class="badge {badge_type}">{chat["provider"]}</span>', unsafe_allow_html=True)
                    st.markdown("---")
        
        # 入力フォーム
        user_input = st.text_input("メッセージを入力してください...", placeholder="例: 担当の佐藤さんの電話番号は 090-1234-5678 です。APIキーは AIzaSyA1B2C3D4 です。")
        
        if st.button("セキュア送信", type="primary"):
            if user_input:
                # 1. DLP プロセッサによるマスキング処理
                anonymized_prompt, dlp_details = st.session_state.dlp_manager.process(user_input)
                
                # フィルタの選択状態に応じてマスキングを適用・除外するフィルタリング
                active_filters = []
                if enable_phone: active_filters.append("PHONE_NUMBER")
                if enable_email: active_filters.append("EMAIL_ADDRESS")
                if enable_cc: active_filters.append("CREDIT_CARD")
                if enable_secret: active_filters.append("API_KEY_SECRET")
                if enable_mynumber: active_filters.append("JP_MYNUMBER")
                if enable_zip: active_filters.append("JP_ZIP")
                
                # 有効になっていないフィルタのマスキングを元に戻す
                final_prompt = user_input
                filtered_details = []
                
                # 開始位置の降順で元に戻す（インデックスのずれ防止）
                sorted_details = sorted(dlp_details, key=lambda x: x["start"], reverse=True)
                for item in sorted_details:
                    if item["entity_type"] in active_filters:
                        # 有効なフィルタはマスキングした文字列に置換
                        final_prompt = final_prompt[:item["start"]] + f"[{item['entity_type']}]" + final_prompt[item["end"]:]
                        filtered_details.append(item)
                
                # メイン画面に履歴登録
                st.session_state.chat_history.append({"role": "user", "content": user_input, "provider": provider})
                
                # 最後のDLP結果をセッションに一時保存（監査用）
                st.session_state.last_raw_prompt = user_input
                st.session_state.last_masked_prompt = final_prompt
                st.session_state.last_dlp_details = filtered_details
                st.session_state.last_provider = provider
                
                # 2. AIモデル呼び出し
                with st.spinner("閉域通信を経由して AI から応答を取得中..."):
                    if "Azure" in provider:
                        response_text = ai_client.call_azure_openai(final_prompt)
                    else:
                        response_text = ai_client.call_gcp_vertex(final_prompt)
                
                st.session_state.chat_history.append({"role": "assistant", "content": response_text, "provider": provider})
                st.rerun()
                
    with col_audit:
        st.subheader("🛡️ リアルタイム DLP 監査ログ")
        st.write("最新の送信データにおけるDLP検出情報と、通信の暗号化・閉域経路のステータスを表示します。")
        
        # 監査ログデータの取得
        raw_prompt = getattr(st.session_state, "last_raw_prompt", None)
        masked_prompt = getattr(st.session_state, "last_masked_prompt", None)
        dlp_details = getattr(st.session_state, "last_dlp_details", [])
        target_prov = getattr(st.session_state, "last_provider", "未送信")
        
        # クラウド接続の設計情報表示
        st.markdown("### 🌐 ネットワーク接続情報")
        if "Azure" in target_prov:
            st.success("🟢 接続ステータス: アクティブ (閉域通信)")
            st.markdown(f"""
            - **送信先**: Azure OpenAI Service (`{st.session_state.get('last_provider', 'Azure')}`)
            - **ネットワーク経路**: `GCP VPC` ➔ `Cloud VPN` ➔ `Azure VPN Gateway` ➔ `Private Endpoint (Azure OpenAI)`
            - **セキュリティ**: インターネットを通過しない完全なプライベート接続。
            - **認証**: OAuth2 / Microsoft Entra ID キーレス連携
            """)
        elif "GCP" in target_prov:
            st.success("🟢 接続ステータス: アクティブ (閉域通信)")
            st.markdown(f"""
            - **送信先**: GCP Vertex AI (`{st.session_state.get('last_provider', 'GCP')}`)
            - **ネットワーク経路**: `Azure VNet` ➔ `VPN Gateway` ➔ `GCP Cloud VPN` ➔ `Private Service Connect (PSC)`
            - **セキュリティ**: Googleバックボーン回線を利用したセキュアなエンドポイント接続。
            - **認証**: Workload Identity Federation による一時的アクセストークン利用
            """)
        else:
            st.info("ℹ️ チャットにメッセージを送信すると、ネットワークと認証の設計情報がここに表示されます。")
            
        st.markdown("---")
        st.markdown("### 📊 DLP 監査結果")
        
        if raw_prompt is not None:
            st.markdown("**1. 生のデータ (ユーザー入力)**")
            st.error(raw_prompt)
            
            st.markdown("**2. マスキング後のデータ (AI送信データ)**")
            st.warning(masked_prompt)
            
            st.markdown("**3. 検出された機密情報の詳細**")
            if dlp_details:
                df_details = pd.DataFrame(dlp_details)
                df_display = df_details.rename(columns={
                    "entity_type": "検知カテゴリ",
                    "original": "オリジナル値",
                    "score": "検知確度 (スコア)",
                    "start": "開始位置",
                    "end": "終了位置"
                })
                df_display = df_display[["検知カテゴリ", "オリジナル値", "検知確度 (スコア)", "開始位置", "終了位置"]]
                st.dataframe(df_display, use_container_width=True)
            else:
                st.info("機密情報（個人情報・APIキーなど）は検出されませんでした。")
        else:
            st.info("チャットでメッセージを送信すると、リアルタイムのDLP解析ログが表示されます。")

# ==========================================
# タブ2: メール承認フロー
# ==========================================
with tab2:
    st.subheader("📧 メール返信によるコマンド承認実行システム")
    st.write("""
    本システムは、Terraformの実行（`terraform apply`）などの重要処理の前に指定のアドレスに承認依頼メールを送信し、
    その返信で `APPROVE` または `承認` を受け取ると自動的に処理を実行するゲートフローです。
    """)
    
    # 環境変数の読み込み状況
    env_sender = os.getenv("SENDER_EMAIL")
    env_passwd = os.getenv("SENDER_PASSWORD")
    
    is_mail_configured = bool(env_sender and env_passwd)
    
    if not is_mail_configured:
        st.warning("""
        ⚠️ **メール送受信環境変数が未設定です。**
        実際のメール送受信を行うには、プロジェクトのルートディレクトリに `.env` ファイルを作成し、以下を設定してください：
        - `SENDER_EMAIL`: 依頼を送受信するボット用の Gmail 等のアドレス
        - `SENDER_PASSWORD`: 上記アドレスのアプリパスワード
        
        ※現在は **「シミュレーションモード」** での動作確認が可能です。
        """)
    else:
        st.success(f"🟢 **メール連携が利用可能です**: ボット送信元: `{env_sender}`")
        
    st.markdown("---")
    
    # フォーム
    col_inputs, col_status = st.columns([1, 1])
    
    with col_inputs:
        st.markdown("### 📝 承認リクエストの作成")
        approver = st.text_input("承認者のメールアドレス (To):", value=DEFAULT_APPROVER)
        task_name = st.text_input("タスク名:", value="Terraform Apply (Azure & GCP VPN Connection)")
        command_to_run = st.text_input("承認後に実行するコマンド:", value="echo 'インフラ構成の適用が正常に完了しました。'")
        
        if st.session_state.approval_status == "idle":
            if st.button("🚀 承認フローを開始する", type="primary"):
                st.session_state.approval_task_id = str(uuid.uuid4())[:8]
                st.session_state.approval_task_name = task_name
                st.session_state.approval_command = command_to_run
                st.session_state.approval_start_time = time.time()
                st.session_state.approval_logs = ["[System] 承認フローのセットアップを開始しました。"]
                
                if is_mail_configured:
                    st.session_state.approval_logs.append(f"[System] {approver} 宛てに承認依頼メールを送信します...")
                    # 実際のメール送信
                    success = send_approval_request(
                        task_name=task_name,
                        task_id=st.session_state.approval_task_id,
                        approver=approver,
                        sender_email=env_sender,
                        sender_password=env_passwd,
                        smtp_server=os.getenv("SMTP_SERVER", "smtp.gmail.com"),
                        smtp_port=int(os.getenv("SMTP_PORT", "587"))
                    )
                    if success:
                        st.session_state.approval_status = "waiting"
                        st.session_state.approval_logs.append("[System] 承認依頼メールの送信に成功しました。返信の監視を開始します。")
                    else:
                        st.session_state.approval_status = "idle"
                        st.session_state.approval_logs.append("[Error] メール送信に失敗しました。認証情報やサーバー設定を確認してください。")
                else:
                    # シミュレーションモードでの開始
                    st.session_state.approval_status = "waiting"
                    st.session_state.approval_logs.append("[Simulation] シミュレーション承認依頼メールを作成しました。")
                    st.session_state.approval_logs.append(f"[Simulation] 送信先: {approver} | 件名: [APPROVAL REQUIRED] Task: {task_name}")
                    st.session_state.approval_logs.append("[Simulation] 承認者の意思決定を待っています。(画面右側のシミュレーションボタンを使用してください)")
                st.rerun()
        else:
            if st.button("❌ 承認フローをキャンセル・リセット"):
                st.session_state.approval_status = "idle"
                st.session_state.approval_task_id = ""
                st.session_state.approval_logs = []
                st.rerun()

    with col_status:
        st.markdown("### 📊 フロー実行ステータス")
        
        status_colors = {
            "idle": "⚪ 待機中 (Idle)",
            "waiting": "🟡 承認返信待ち (Waiting for Approval)",
            "approved": "🟢 承認済み・実行完了 (Approved & Executed)",
            "rejected": "🔴 却下 (Rejected)"
        }
        
        st.subheader(status_colors[st.session_state.approval_status])
        
        if st.session_state.approval_status == "waiting":
            st.warning(f"タスクID: `{st.session_state.approval_task_id}` の承認返信を待機しています。")
            
            # メール送信が設定されている場合は、自動/手動チェックボタン
            if is_mail_configured:
                st.info("承認者から 'APPROVE' または '承認' というキーワードを含む返信が届くまでポーリングします。")
                
                auto_poll = st.checkbox("自動チェックを有効化する (15秒おき)", value=True)
                
                col_btn, col_poll = st.columns([1, 2])
                with col_btn:
                    check_now = st.button("🔄 今すぐチェックする")
                
                should_check = check_now
                
                if auto_poll and not check_now:
                    # ユーザーが今すぐチェックを押していない場合、自動カウントダウン後にチェックを実行
                    poll_placeholder = col_poll.empty()
                    for seconds_left in range(15, 0, -1):
                        poll_placeholder.info(f"⏳ 次の自動チェックまで {seconds_left} 秒...")
                        time.sleep(1)
                    should_check = True
                
                if should_check:
                    with st.spinner("IMAP サーバーで返信メールを確認中..."):
                        status, comment = check_for_approval(
                            task_id=st.session_state.approval_task_id,
                            approver=approver,
                            sender_email=env_sender,
                            sender_password=env_passwd,
                            imap_server=os.getenv("IMAP_SERVER", "imap.gmail.com"),
                            imap_port=int(os.getenv("IMAP_PORT", "993"))
                        )
                        
                        if status == "APPROVE":
                            st.session_state.approval_status = "approved"
                            st.session_state.approval_logs.append(f"[Approved] 承認が確認されました！ 承認者コメント: {comment}")
                            st.session_state.approval_logs.append(f"[System] コマンドを実行します: {st.session_state.approval_command}")
                            # コマンド実行
                            try:
                                result = subprocess.run(st.session_state.approval_command, shell=True, capture_output=True, text=True)
                                st.session_state.approval_logs.append(f"[Stdout] {result.stdout}")
                                if result.stderr:
                                    st.session_state.approval_logs.append(f"[Stderr] {result.stderr}")
                                st.session_state.approval_logs.append(f"[System] 実行完了 (Exit Code: {result.returncode})")
                            except Exception as e:
                                st.session_state.approval_logs.append(f"[Error] コマンド実行中に例外が発生しました: {e}")
                        elif status == "REJECT":
                            st.session_state.approval_status = "rejected"
                            st.session_state.approval_logs.append(f"[Rejected] 承認者によって却下されました。 却下理由: {comment}")
                        else:
                            st.session_state.approval_logs.append(f"[System] 新しい承認メールは検出されませんでした。({time.strftime('%H:%M:%S')})")
                    st.rerun()
            else:
                # 環境変数が無い時の、シミュレーション用アクションボタン
                st.info("シミュレーションモード: 以下のボタンで承認者のアクションを模擬できます。")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("👍 承認をシミュレート (Approve)"):
                        st.session_state.approval_status = "approved"
                        st.session_state.approval_logs.append("[Approved] 承認されました (シミュレーション)")
                        st.session_state.approval_logs.append(f"[System] コマンドを実行します: {st.session_state.approval_command}")
                        try:
                            result = subprocess.run(st.session_state.approval_command, shell=True, capture_output=True, text=True)
                            st.session_state.approval_logs.append(f"[Stdout] {result.stdout}")
                            if result.stderr:
                                st.session_state.approval_logs.append(f"[Stderr] {result.stderr}")
                        except Exception as e:
                            st.session_state.approval_logs.append(f"[Error] {e}")
                        st.rerun()
                with col_no:
                    if st.button("👎 却下をシミュレート (Reject)"):
                        st.session_state.approval_status = "rejected"
                        st.session_state.approval_logs.append("[Rejected] 却下されました (シミュレーション)")
                        st.rerun()
                        
        # ログの表示
        if st.session_state.approval_logs:
            st.markdown("#### 🪵 実行・接続ログ")
            log_text = "\n".join(st.session_state.approval_logs)
            st.code(log_text, language="text")

# ==========================================
# タブ3: インフラ設計 & ドキュメント
# ==========================================
with tab3:
    st.subheader("📄 セキュリティ技術の比較とシステム設計解説 (Azure & GCP)")
    
    # docs/comparison_and_design.md を読み込んで表示
    doc_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "comparison_and_design.md")
    
    if os.path.exists(doc_path):
        try:
            with open(doc_path, "r", encoding="utf-8") as f:
                doc_content = f.read()
            st.markdown(doc_content)
        except Exception as e:
            st.error(f"ドキュメントの読み込み中にエラーが発生しました: {e}")
    else:
        st.info("設計解説ドキュメント (docs/comparison_and_design.md) が見つかりません。")
