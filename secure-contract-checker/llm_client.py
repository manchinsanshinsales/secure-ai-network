from abc import ABC, abstractmethod
import os
import google.generativeai as genai

class BaseLLMClient(ABC):
    """
    LLMへの接続を抽象化する基底クラス（インターフェース）。
    将来的にGemini以外のLLM（Azure OpenAIやローカルLLMなど）に移行しやすくします。
    """
    @abstractmethod
    def generate_response(self, prompt: str) -> str:
        """
        プロンプトを送信し、LLMからの応答文字列を取得します。
        
        Args:
            prompt (str): LLMに送信するプロンプトテキスト
            
        Returns:
            str: LLMからの回答テキスト
        """
        pass

class MockLLMClient(BaseLLMClient):
    """
    オフラインテストおよびデモ用のモックLLMクライアント。
    APIキーなしで動作し、プレースホルダーを含んだ模擬的なレビュー回答を返します。
    """
    def generate_response(self, prompt: str) -> str:
        # デモ用に、契約書内のプレースホルダーを検出して動的に回答に組み込む
        import re
        org_matches = re.findall(r'\[ORGANIZATION_\d+\]', prompt)
        per_matches = re.findall(r'\[PERSON_\d+\]', prompt)
        money_matches = re.findall(r'\[MONEY_\d+\]', prompt)
        date_matches = re.findall(r'\[DATE_\d+\]', prompt)

        org1 = org_matches[0] if len(org_matches) > 0 else "[ORGANIZATION_1]"
        org2 = org_matches[1] if len(org_matches) > 1 else "[ORGANIZATION_2]"
        per1 = per_matches[0] if len(per_matches) > 0 else "[PERSON_1]"
        money1 = money_matches[0] if len(money_matches) > 0 else "[MONEY_1]"
        date1 = date_matches[0] if len(date_matches) > 0 else "[DATE_1]"

        mock_response = f"""### 📄 契約書レビューレポート (デモモード)

ご提示いただいた契約書（匿名化データ）の簡易リーガルチェック結果は以下の通りです。

#### 1. 契約当事者および基本合意
- 本契約は、甲である **{org1}** と、乙である **{org2}** との間で合意されています。当事者の表記に矛盾はありません。
- 代表者として **{per1}** の記載が確認されています。

#### 2. 金額および支払条件について
- 契約金額として **{money1}** が設定されています。
- 支払期日は **{date1}** と規定されていますが、**遅延損害金（遅延利息）に関する規定が明記されていません**。実務上、遅延時の対応を明確にするため、「年率◯%の遅延利息を支払う」旨の条項を追加することを推奨します。

#### 3. 秘密保持および権利義務
- 乙（**{org2}**）側の秘密保持義務の範囲が非常に広く設定されています。甲（**{org1}**）の機密情報開示の範囲が適切か、また例外規定（公知の情報など）が正しく設定されているか、再確認が必要です。
"""
        return mock_response

class GeminiClient(BaseLLMClient):
    """
    Google Gemini API を使用して応答を生成する実クライアント。
    """
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        """
        Gemini APIクライアントを初期化します。
        
        Args:
            api_key (str): GeminiのAPIキー
            model_name (str): 使用するGeminiモデル名（デフォルトは軽量高速な gemini-1.5-flash）
        """
        self.api_key = api_key
        self.model_name = model_name
        
        # APIの構成
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def generate_response(self, prompt: str) -> str:
        """
        Gemini APIを呼び出して応答を生成します。
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Gemini APIの呼び出し中にエラーが発生しました:\n{str(e)}"
