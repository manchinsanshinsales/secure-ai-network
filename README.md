# Multi-Cloud Secure AI Network & DLP Dashboard 🛡️

マルチクラウド（Azure & GCP）環境におけるセキュアな生成AI利用を目的とした、ネットワーク設計、キーレス認証、およびデータ流出防止（DLP）の実証デモアプリケーションです。

---

## 🚀 ポートフォリオとしてのアピールポイント（履歴書向け）

本リポジトリは、マルチクラウドのネットワーク、セキュリティ、およびAIインテグレーションの実践力を証明するためのポートフォリオです。以下の技術スキルを実証しています。

1. **マルチクラウド閉域ネットワーク設計（IaC）**:
   - GCP VPC と Azure VNet 間を **IPsec VPN** で相互接続するインフラ設計。
   - Azure OpenAI に対する **Private Endpoint**（プライベートエンドポイント）の敷設とプライベートDNSによる名前解決。
   - 上記すべてを **Terraform (IaC)** によりコード化し、再現可能なインフラ構成を保証。

2. **静的APIキーを排除したキーレス認証**:
   - GCP のサービスアカウントと Azure Entra ID アプリケーション間で **Workload Identity Federation / OIDC** 連携を設定。
   - 環境変数に固定のAPI秘密鍵を持たせず、一時的なトークン交換によって安全にクラウド間のAPI認可を実行する設計。

3. **水際でのデータ流出防止 (DLP)**:
   - **Microsoft Presidio** を活用した、日本語および機密情報（電話番号、メール、マイナンバー、APIキーなど）のローカル検知・マスキングエンジンを Python で実装。
   - 送信データに含まれる機密情報を自動マスキングした上でAIに送信するデータガバナンスの仕組み。

4. **採用担当者が即座に確認できる「シミュレーションモード」**:
   - 実際のクラウド環境を起動（課金が発生）させなくても、ローカル環境でDLPの動作やネットワーク設計情報の確認ができるモックモードを搭載。

---

## 🌐 システム構成図

```mermaid
graph TD
    subgraph GCP ["GCP (Google Cloud Platform)"]
        subgraph GCP_VPC ["VPC (10.0.0.0/16)"]
            subgraph CloudRun_Subnet ["Cloud Run Subnet"]
                CR["Streamlit App (Cloud Run / Serverless VPC Access)"]
            end
            GW_GCP["Cloud VPN Gateway"]
        end
        VertexAI["Vertex AI API (Private Service Connect)"]
        WIF["Workload Identity Federation"]
    end

    subgraph Azure ["Microsoft Azure"]
        subgraph Azure_VNet ["VNet (172.16.0.0/16)"]
            subgraph App_Subnet ["App/Private Endpoint Subnet"]
                PE_AOAI["Private Endpoint (Azure OpenAI)"]
            end
            GW_Azure["VPN Gateway"]
        end
        AOAI["Azure OpenAI Service"]
        Entra["Microsoft Entra ID (App Registration)"]
    end

    %% Network Connection
    GW_GCP <--> |IPsec VPN Tunnel / 閉域通信| GW_Azure
    CR -.-> |VPN経由でプライベートアクセス| PE_AOAI
    PE_AOAI --> AOAI

    %% Identity Federation
    WIF <--> |OIDC / キーレス認証| Entra
    CR -.-> |Access Tokenの取得| Entra
```

---

## 📂 プロジェクト構成

```text
├── app/
│   ├── app.py             # Streamlit ダッシュボード & チャット UI
│   ├── dlp.py             # Microsoft Presidio を用いたDLPマスキングモジュール
│   ├── ai_client.py       # Azure OpenAI / GCP Vertex AI クライアント（モック機能付き）
│   └── requirements.txt   # 依存関係定義ファイル
├── terraform/
│   ├── variables.tf       # 共通変数定義
│   ├── gcp/
│   │   └── main.tf        # VPC, Cloud VPN, WIF, Cloud Run 構築定義
│   └── azure/
│       └── main.tf        # VNet, VPN Gateway, Azure OpenAI, PE 構築定義
├── docs/
│   └── comparison_and_design.md  # 3つのセキュリティ境界モデルの技術比較と設計解説
└── README.md              # プロジェクト概要（本ファイル）
```

---

## 🛠️ クイックスタート（ローカルデモ起動手順）

クラウド環境をデプロイせずに、ローカル環境でDLPのマスキング機能やモック応答の動作を確認できます。

### 1. 依存ライブラリのインストール

```bash
# 必要なライブラリのインストール
pip install -r app/requirements.txt

# Microsoft Presidio用NLPモデルのダウンロード (約12MB)
python -m spacy download en_core_web_sm
```

### 2. デモアプリの起動

```bash
streamlit run app/app.py
```

起動後、自動的にブラウザが開きます（デフォルト: `http://localhost:8501`）。

### 3. デモの確認手順
1. 左側のサイドバーで**「シミュレーション（モックモード）」**が選択されていることを確認します。
2. チャットの入力欄に、個人情報やAPIキーを含むテキストを入力します。
   - *入力例: 「佐藤さんの電話番号は 090-1234-5678 です。Azureのキーは AIzaSy... です。」*
3. **「セキュア送信」** をクリックします。
4. 画面右側の **「リアルタイム DLP 監査ログ」** にて、生データとマスキング後（`[PHONE_NUMBER]`などに置換されたデータ）の比較、および検出されたエンティティの詳細が美しく表示されます。
5. チャット欄には、マスキング済みの安全なデータを使ってAIが応答したシミュレーションメッセージが返却されます。
