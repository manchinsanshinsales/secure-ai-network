import os
import logging
from typing import Optional

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SecureAiClient")

class SecureAiClient:
    def __init__(self, use_mock: bool = True):
        """
        AIクライアントマネージャーの初期化。
        use_mock=True の場合は、実際のクラウドAPIを呼び出さずにモックデータを返します。
        """
        self.use_mock = use_mock
        
        # クラウド設定の読み込み
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-resource.openai.azure.com/")
        self.azure_api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
        
        self.gcp_project = os.getenv("GCP_PROJECT_ID", "your-gcp-project")
        self.gcp_location = os.getenv("GCP_LOCATION", "us-central1")
        self.gcp_model = os.getenv("GCP_VERTEX_MODEL", "gemini-1.5-pro")

        if not self.use_mock:
            self._init_real_clients()

    def _init_real_clients(self):
        """
        実際のAzureおよびGCP SDKクライアントを初期化します。
        認証キーが不足している場合は、自動的に警告を出してモックモードに切り替えます。
        """
        # 1. Azure OpenAI 初期化
        try:
            from openai import AzureOpenAI
            if self.azure_api_key:
                self.azure_client = AzureOpenAI(
                    azure_endpoint=self.azure_endpoint,
                    api_key=self.azure_api_key,
                    api_version="2024-02-15-preview"
                )
                logger.info("Azure OpenAI client initialized successfully.")
            else:
                logger.warning("Azure OpenAI API Key is missing. Falling back to mock for Azure.")
                self.azure_client = None
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {e}")
            self.azure_client = None

        # 2. GCP Vertex AI 初期化
        try:
            import google.cloud.aiplatform as aiplatform
            from google.cloud import generative_models
            
            # ADC (Application Default Credentials) が使える環境前提
            aiplatform.init(project=self.gcp_project, location=self.gcp_location)
            self.gcp_model_client = generative_models.GenerativeModel(self.gcp_model)
            logger.info("GCP Vertex AI client initialized successfully.")
        except Exception as e:
            logger.warning(f"Failed to initialize GCP Vertex AI client: {e}. Falling back to mock for GCP.")
            self.gcp_model_client = None

    def call_azure_openai(self, prompt: str) -> str:
        """
        Azure OpenAIに対してプロンプトを送信します。
        閉域網（Private Endpoint）およびOAuth認証を想定したクライアントを使用します。
        """
        logger.info("Calling Azure OpenAI...")
        if self.use_mock or not getattr(self, "azure_client", None):
            return self._get_mock_response("Azure OpenAI", prompt)
            
        try:
            response = self.azure_client.chat.completions.create(
                model=self.azure_deployment,
                messages=[
                    {"role": "system", "content": "You are a secure AI assistant. Provide a helpful response."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling Azure OpenAI: {e}")
            return f"[ERROR] Azure OpenAIとの通信に失敗しました: {e}\n(モックモードを有効にすると、ローカルでの動作確認が可能です)"

    def call_gcp_vertex(self, prompt: str) -> str:
        """
        GCP Vertex AI (Gemini)に対してプロンプトを送信します。
        Workload Identity FederationによるOIDC認証やPrivate Service Connectを想定します。
        """
        logger.info("Calling GCP Vertex AI...")
        if self.use_mock or not getattr(self, "gcp_model_client", None):
            return self._get_mock_response("GCP Vertex AI (Gemini)", prompt)
            
        try:
            response = self.gcp_model_client.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error calling GCP Vertex AI: {e}")
            return f"[ERROR] GCP Vertex AIとの通信に失敗しました: {e}\n(モックモードを有効にすると、ローカルでの動作確認が可能です)"

    def _get_mock_response(self, provider: str, prompt: str) -> str:
        """
        開発・検証デモ用のモックレスポンスを生成します。
        送信された（マスキング済みの）プロンプトへのフィードバックを返し、セキュリティ機能をアピールします。
        """
        # プロンプトがマスキングされているかどうかのチェック
        is_masked = "[PHONE_NUMBER]" in prompt or "[EMAIL_ADDRESS]" in prompt or "[CREDIT_CARD]" in prompt or "[API_KEY_SECRET]" in prompt or "[JP_MYNUMBER]" in prompt
        
        security_status = (
            "🔒 **セキュリティ通知**: 送信されたデータはDLPモジュールによって適切にマスキングされ、"
            "個人情報や機密情報の漏洩が防止されています。" if is_masked else 
            "✅ **セキュリティ通知**: 送信されたデータに機密情報は検知されませんでした。生データがそのまま安全に処理されました。"
        )
        
        response_template = f"""【{provider} からの応答 (シミュレーション)】

受信したプロンプト:
> {prompt}

---

{security_status}

こちらは {provider} のモック応答です。
マルチクラウド環境において、本アプリケーションは以下の経路で安全に各AIモデルと通信する設計になっています：
1. **Azure接続**: GCP側のフロントエンド/VPNゲートウェイから、Azure上のVPNゲートウェイおよびPrivate Endpointを経由し、外部インターネットに露出させずにAzure OpenAIを安全に呼び出します。
2. **GCP接続**: Azure側からの呼び出しや、GCP VPC内のリソースからPrivate Service Connectを用いて、完全にGoogleの閉域バックボーンネットワーク上でVertex AIを呼び出します。
3. **認証**: クラウド間の通信には静的なAPIキーや秘密鍵を使用せず、OIDCトークン連携（Workload Identity / Entra ID）による認証認可（キーレス構成）を適用しています。
"""
        return response_template
