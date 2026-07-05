# 📄 Secure Contract Checker (セキュア契約書リーガルチェック PoC)

士業（弁護士・税理士など）や老舗企業向けに、機密データを外部に送信することなく安全に生成AIを活用できる「セキュア・ゲートウェイ」の実証アプリケーション（PoC）です。

---

## 🏗️ システムアーキテクチャ

本アプリケーションは、**「ローカルでの機密情報マスキング」**と**「外部APIとのセキュア連携」**を組み合わせたハイブリッド設計となっています。

### データフロー＆コンポーネント構成

```mermaid
graph TD
    subgraph Local Environment (Client Side - Secure)
        User[ユーザー / ブラウザ] -->|1. 契約書テキスト入力| StreamlitApp[app.py Streamlit UI]
        StreamlitApp -->|2. 未加工テキスト| MaskingEngine[masking.py マスキングエンジン]
        
        subgraph Local Memory (No Outbound)
            MapTable[(Mapping Table)]
        end
        
        MaskingEngine -->|3. 機密情報を抽出 & ダミー置換| MapTable
        MaskingEngine -->|4. マスキング済テキスト| StreamlitApp
        StreamlitApp -->|5. 安全なテキストを送信| LLMClient[llm_client.py 抽象クライアント]
    end

    subgraph External Network (Google Cloud - API)
        LLMClient -->|6. APIリクエスト (安全なデータのみ)| GeminiAPI[Gemini 1.5 Flash API]
        GeminiAPI -->|7. レビュー応答 (ダミーのまま)| LLMClient
    end

    subgraph Local Environment (Client Side - Unmasking)
        LLMClient -->|8. 生のレビュー結果| StreamlitApp
        StreamlitApp -->|9. レビュー結果 + Mapping Table| MaskingEngine
        MaskingEngine -->|10. プレースホルダーを実データに復元| StreamlitApp
        StreamlitApp -->|11. 最終レビューレポート表示| User
    end

    style MapTable fill:#f9f,stroke:#333,stroke-width:2px
    style GeminiAPI fill:#ff9,stroke:#333,stroke-width:2px
    style Local Environment (Client Side - Secure) fill:#e1f5fe,stroke:#01579b,stroke-width:2px
```

### アーキテクチャのキーポイント

1. **ゼロトラストデータ送信 (No Data Leak)**:
   - 会社名、人名、金額、日付などの機密情報は、外部のLLM APIに送信される前にローカル環境で自動的に `[ORGANIZATION_1]` などのプレースホルダーに置換されます。
   - API側には、実際の顧客データや金額データは一切届きません。
2. **ローカルマッピング管理 (Local State)**:
   - 置換されたダミー文字列と元の文字列の対応表（マッピングテーブル）は、アプリケーションのメモリ内（Streamlitセッション）にのみ一時保存され、データベースなどの外部ディスクには永続化されません。
3. **抽象化されたLLM接続 (Client Abstraction)**:
   - `llm_client.py` 内で LLM との接続が抽象化（インターフェース化）されており、設定切り替えのみで「Gemini API」「Azure OpenAI API（閉域網）」、さらにはインターネットに一切繋がない「完全ローカルLLM（Ollama等）」に容易に差し替え可能な設計となっています。

---

## 🚀 起動方法

### 1. 前提条件
- Python 3.9 以上
- Google Gemini API キー (本番モードで実行する場合。デモモードでは不要です)

### 2. 環境構築とインストール
プロジェクトディレクトリにて、仮想環境を作成しパッケージをインストールします。

```bash
# プロジェクトディレクトリへ移動
cd secure-contract-checker

# 仮想環境の作成
python3 -m venv .venv
source .venv/bin/activate

# 依存パッケージのインストール (Macでのコンパイルを避けるため wheel のみを強制)
pip install --only-binary :all: -r requirements.txt
```

### 3. アプリケーションの実行
Streamlitサーバーを起動します。

```bash
streamlit run app.py
```
起動完了後、自動的にブラウザで `http://localhost:8501` が開きます。

---

## 📂 ファイル構成

- **`app.py`**: Streamlitを用いたフロントエンドUIおよび全体の処理フローの統合。
- **`masking.py`**: 正規表現を用いた機密表現の抽出・ダミー化・復元エンジン。
- **`llm_client.py`**: 抽象LLMクライアント、デモ用Mockクライアント、Gemini API用クライアントの実装。
- **`test_masking.py`**: データフローが完璧に動作するかを自動検証するアサーションテスト。
- **`requirements.txt`**: 依存ライブラリ一覧。
