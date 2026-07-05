import re
from typing import List, Dict, Tuple, Any
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

class SecureDlpManager:
    def __init__(self):
        """
        DLPマネージャーの初期化。
        Microsoft Presidioのアナライザーとアノニマイザーをセットアップし、
        日本語特有の個人情報およびクラウド機密情報（APIキー等）の検知パターンを追加します。
        """
        self.anonymizer = AnonymizerEngine()
        self.fallback_recognizers = []
        
        # アナライザーエンジンの初期化を試行
        try:
            self.analyzer = AnalyzerEngine()
        except (Exception, SystemExit):
            # NLPモデルがロードできない場合（spaCyのモデルダウンロード失敗時は
            # SystemExitが送出されるため、これも含めて捕捉する）は analyzer=None とし、
            # 自前のフォールバック認識ロジックを使用する
            self.analyzer = None

        self._setup_custom_recognizers()

    def _setup_custom_recognizers(self):
        """
        日本語の電話番号、郵便番号、マイナンバー、およびクラウドAPIキーのカスタム認識器をセットアップします。
        """
        # 1. 日本の電話番号 (携帯・固定)
        phone_pattern = Pattern(
            name="jp_phone_pattern",
            regex=r"0\d{1,4}-\d{1,4}-\d{4}|0\d{9,10}",
            score=0.85
        )
        phone_recognizer = PatternRecognizer(
            supported_entity="PHONE_NUMBER",
            patterns=[phone_pattern],
            context=["電話", "TEL", "tel", "phone", "連絡先"]
        )

        # 2. マイナンバー (12桁の数字)
        mynumber_pattern = Pattern(
            name="jp_mynumber_pattern",
            regex=r"(?<!\d)\d{12}(?!\d)",
            score=0.9
        )
        mynumber_recognizer = PatternRecognizer(
            supported_entity="JP_MYNUMBER",
            patterns=[mynumber_pattern],
            context=["マイナンバー", "個人番号", "My Number", "マイナ"]
        )

        # 3. 日本の郵便番号 (3桁-4桁、または7桁)
        zip_pattern = Pattern(
            name="jp_zip_pattern",
            regex=r"(?<!\d)\d{3}-\d{4}(?!\d)|(?<!\d)\d{7}(?!\d)",
            score=0.75
        )
        zip_recognizer = PatternRecognizer(
            supported_entity="JP_ZIP",
            patterns=[zip_pattern],
            context=["郵便番号", "〒", "zip", "postal", "住所"]
        )

        # 4. クラウドAPIキー / シークレット情報
        # AWSアクセスキー、AWSシークレット、GCP APIキー、汎用シークレット/パスワード
        api_patterns = [
            Pattern(name="aws_key_pattern", regex=r"(?<![A-Z0-9])(AKIA|ASIA)[0-9A-Z]{16}(?![A-Z0-9])", score=0.95),
            Pattern(name="aws_secret_pattern", regex=r"(?<![a-zA-Z0-9])[a-zA-Z0-9+/]{40}(?![a-zA-Z0-9])", score=0.8),
            Pattern(name="gcp_key_pattern", regex=r"(?<![a-zA-Z0-9])AIzaSy[a-zA-Z0-9-_]{33}(?![a-zA-Z0-9-_])", score=0.95),
            Pattern(name="general_secret_pattern", regex=r"(?i)(secret|password|passwd|token|api_key|apikey|private_key)\s*[:=]\s*['\"][a-zA-Z0-9_\-\.\+\/]{8,}['\"]", score=0.85)
        ]
        api_recognizer = PatternRecognizer(
            supported_entity="API_KEY_SECRET",
            patterns=api_patterns,
            context=["key", "secret", "token", "password", "aws", "gcp", "api", "アクセスキー", "パスワード"]
        )

        # アナライザーに追加、またはフォールバック用リストに格納
        custom_recognizers = [phone_recognizer, mynumber_recognizer, zip_recognizer, api_recognizer]
        
        if self.analyzer:
            for recognizer in custom_recognizers:
                self.analyzer.registry.add_recognizer(recognizer)
        else:
            self.fallback_recognizers.extend(custom_recognizers)

    def analyze_text(self, text: str, language: str = "en") -> List[Any]:
        """
        テキストを解析し、機密情報の位置と種類を特定します。
        """
        if not text:
            return []
            
        if self.analyzer:
            try:
                results = self.analyzer.analyze(text=text, language=language)
                return results
            except Exception:
                pass
                
        # フォールバック処理: 自前のルールベースでの解析
        return self._fallback_analyze(text)

    def _fallback_analyze(self, text: str) -> List[Any]:
        from presidio_analyzer import RecognizerResult
        results = []
        
        # 1. 簡易メールアドレス検知
        email_regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        for match in re.finditer(email_regex, text):
            results.append(RecognizerResult(
                entity_type="EMAIL_ADDRESS",
                start=match.start(),
                end=match.end(),
                score=0.9
            ))
            
        # 2. クレジットカード番号 (13〜16桁)
        cc_regex = r"\b(?:\d[ -]*?){13,16}\b"
        for match in re.finditer(cc_regex, text):
            results.append(RecognizerResult(
                entity_type="CREDIT_CARD",
                start=match.start(),
                end=match.end(),
                score=0.8
            ))

        # 3. 各種カスタム認識器の適用
        for recognizer in self.fallback_recognizers:
            for pattern in recognizer.patterns:
                for match in re.finditer(pattern.regex, text):
                    start = match.start()
                    end = match.end()
                    
                    # キー・値のペア（例：password="123456"）の場合、値の部分のみマスキングするよう調整
                    if pattern.name == "general_secret_pattern":
                        val_match = re.search(r"['\"][a-zA-Z0-9_\-\.\+\/]{8,}['\"]", match.group(0))
                        if val_match:
                            start = match.start() + val_match.start()
                            end = match.start() + val_match.end()

                    results.append(RecognizerResult(
                        entity_type=recognizer.supported_entities[0],
                        start=start,
                        end=end,
                        score=pattern.score
                    ))
                    
        # 重複・ネストの整理
        return self._deduplicate_results(results)

    def _deduplicate_results(self, results: List[Any]) -> List[Any]:
        # 位置順にソート (開始位置は昇順、終了位置は降順)
        sorted_res = sorted(results, key=lambda x: (x.start, -x.end))
        keep = []
        last_end = -1
        
        for res in sorted_res:
            if res.start >= last_end:
                keep.append(res)
                last_end = res.end
        return keep

    def anonymize_text(self, text: str, analyze_results: List[Any]) -> str:
        """
        解析結果に基づいて機密情報をマスキングします。
        """
        if not text:
            return ""
            
        # マスキング用の設定（各エンティティを [ENTITY_TYPE] 形式で置換）
        operators = {}
        for res in analyze_results:
            operators[res.entity_type] = OperatorConfig(
                "replace", 
                {"new_value": f"[{res.entity_type}]"}
            )
            
        try:
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=analyze_results,
                operators=operators
            )
            return anonymized_result.text
        except Exception:
            # エラー発生時は自前の置換ロジックにフォールバック
            return self._fallback_anonymize(text, analyze_results)

    def _fallback_anonymize(self, text: str, analyze_results: List[Any]) -> str:
        # インデックスのズレを防ぐため、文字列の後ろから順に置換
        sorted_results = sorted(analyze_results, key=lambda x: x.start, reverse=True)
        text_list = list(text)
        for res in sorted_results:
            mask = f"[{res.entity_type}]"
            text_list[res.start:res.end] = list(mask)
        return "".join(text_list)

    def process(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        テキストの解析とマスキングを一括実行し、マスキング結果と検知情報の詳細リストを返却します。
        """
        results = self.analyze_text(text, language="en")
        anonymized_text = self.anonymize_text(text, results)
        
        details = []
        for res in results:
            original_value = text[res.start:res.end]
            details.append({
                "entity_type": res.entity_type,
                "start": res.start,
                "end": res.end,
                "score": res.score,
                "original": original_value
            })
            
        return anonymized_text, details
