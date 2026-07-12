# Azure AI-103 カリキュラム & マルチクラウドデータ転送設計ガイド

本ドキュメントは、Microsoft最新のAI開発者認定資格 **AI-103 (Developing AI Apps and Agents on Azure)** の試験範囲と、マルチクラウドRAG構築に向けた **GCP BigQuery ➔ Azure AI Search** のデータ同期設計をまとめたガイドです。

---

## 1. Microsoft AI-103 試験シラバスの構造

AI-102の廃止（2026年6月30日）に伴い、新設された **AI-103** は「生成AIとAIエージェントの構築」に特化しています。

| 試験ドメイン | 配点比率 | PoCとのシナジー |
| :--- | :--- | :--- |
| **1. Plan and Manage an Azure AI Solution** | 25–30% | セキュアAIゲートウェイの設計、APIセキュリティ。 |
| **2. Implement Generative AI and Agentic Solutions** | 30–35% | **【RAGの核】** Azure OpenAI、RAGの構築、評価、プロンプト管理。 |
| **3. Implement Computer Vision Solutions** | 10–15% | 画像認識・OCRとの連携（本PoCではオプション）。 |
| **4. Implement Text Analysis Solutions** | 10–15% | テキスト処理、翻訳、感情分析等。 |
| **5. Implement Information Extraction Solutions** | 10–15% | **【検索の核】** Azure AI Search、ベクトル/ハイブリッド検索。 |

---

## 2. BigQuery ➔ Azure AI Search データ転送の設計比較

GCP BigQuery に蓄積された社内データを、Azure AI Search のベクトル・ハイブリッド検索用にインジェスト（同期）する設計として、以下の2案を比較評価します。

### 案A: Python（Push型・サーバーレス） ★PoC推奨
GCP側でPythonスクリプトを実行し、BigQueryクライアントでデータを取得、Azure AI Search SDKでインデックスへ直接書き込む方式。

- **メリット**: 追加の有償インフラ（ADF等）が不要で、すぐに実装可能。ローカルやGCP Cloud Run等に手軽にデプロイできる。
- **デメリット**: 大容量データの同期時にメモリ管理やエラーハンドリングをPython側で実装する必要がある。

### 案B: Azure Data Factory（Pull型・マネージド）
Azure側に ADF を配置し、BigQueryの外部データソースコネクタ経由でデータを読み込み、Azure AI Search をシンク（出力先）として同期する方式。

- **メリット**: スケジューリング、リトライ、ログがビルトインされており、大規模エンタープライズで標準的な構成。
- **デメリット**: ADFのランニングコストとネットワーク（閉域VPN等）の事前設定が必要。

---

## 3. 実機検証用 Python 転送スクリプト (設計テンプレート)

検証PoC向けに、案Aを採用した Python のインジェスト設計コードを示します。

```python
# scripts/sync_bigquery_to_azure_search.py のプロトタイプ設計
import os
from google.cloud import bigquery
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

def fetch_data_from_bigquery(project_id, dataset_id, table_id):
    """GCP BigQueryからデータを取得します"""
    client = bigquery.Client()
    query = f"SELECT id, title, content, last_updated FROM `{project_id}.{dataset_id}.{table_id}`"
    query_job = client.query(query)
    results = query_job.result()
    
    documents = []
    for row in results:
        documents.append({
            "id": str(row.id),
            "title": row.title,
            "content": row.content,
            "last_updated": str(row.last_updated)
        })
    return documents

def upload_to_azure_search(endpoint, index_name, api_key, documents):
    """Azure AI Searchのインデックスにドキュメントをアップロードします"""
    credential = AzureKeyCredential(api_key)
    client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
    
    # バッチアップロードの実行
    result = client.upload_documents(documents=documents)
    print(f"アップロード結果: {len(result)} 件のドキュメントをインジェストしました。")

def main():
    # 各種環境変数
    gcp_project = os.environ.get("GCP_PROJECT_ID")
    bq_dataset = os.environ.get("BQ_DATASET_ID")
    bq_table = os.environ.get("BQ_TABLE_ID")
    
    azure_endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    azure_index = os.environ.get("AZURE_SEARCH_INDEX_NAME")
    azure_key = os.environ.get("AZURE_SEARCH_API_KEY")
    
    # 処理の実行
    print("GCP BigQuery からのデータ抽出を開始...")
    docs = fetch_data_from_bigquery(gcp_project, bq_dataset, bq_table)
    
    print(f"Azure AI Search ({azure_index}) へのインジェストを開始...")
    upload_to_azure_search(azure_endpoint, azure_index, azure_key, docs)

if __name__ == "__main__":
    main()
```

### 次の検証課題：ベクトル化のハイブリッド評価
同期するデータ（`content` フィールド）は、Azure AI Search 内のベクトルインデックスに格納される必要があります。
このベクトル変換時に、**`EmbeddingGemma`** をローカル環境（Ollama）で回してベクトルを生成してインジェストする（ローカル完結）か、それとも Azure AI Search のビルトインインデクサーで Azure OpenAI を呼び出して自動ベクトル化するか、そのレイテンシと適合度の実機比較を「第2フェーズ」で実行します。
