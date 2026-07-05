import re
from typing import Tuple, Dict

def mask_text(text: str, mask_options: Dict[str, bool]) -> Tuple[str, Dict[str, str]]:
    """
    テキスト内の機密情報（会社名、人名、金額、日付）を検知し、ダミー文字列に置換（マスキング）します。
    
    Args:
        text (str): マスキング対象のテキスト
        mask_options (dict): マスキング項目の有効/無効設定。
                             例: {'ORG': True, 'PER': True, 'MONEY': True, 'DATE': True}
                             
    Returns:
        Tuple[str, Dict[str, str]]: (マスキング済みのテキスト, ダミー文字列から元の文字列へのマッピング辞書)
    """
    mapping_dict = {}
    masked_text = text

    # 各カテゴリの正規表現パターン定義
    patterns = {}
    
    # 組織名（株式会社、合同会社など）
    if mask_options.get("ORG", True):
        patterns["ORGANIZATION"] = r'(?:株式会社|合同会社|有限会社|合資会社)[A-Za-z0-9一-龠ぁ-んァ-ヶ々\-\s・]+|[A-Za-z0-9一-龠ぁ-んァ-ヶ々\-\s・]+(?:株式会社|合同会社|有限会社|合資会社)'
    
    # 人名（契約当事者の「甲：〇〇」や、「代表取締役 〇〇」の後ろ、あるいは「山田 太郎」などの特定パターン）
    if mask_options.get("PER", True):
        # 契約当当事者パターン（甲：山田 太郎、乙：鈴木 花子）
        # 代表者パターン（代表取締役 山田 太郎、代表者 鈴木 花子）
        # ※「株式会社」などの組織キーワードを含まない場合のみ人名として抽出し、改行は含めない
        patterns["PERSON"] = r'(?:甲|乙|丙|丁|委託者|受託者|代表取締役|代表者)\s*[:：\s]\s*(?!(?:株式会社|合同会社|有限会社|合資会社|代表者|代表取締役))([A-Za-z0-9一-龠ぁ-んァ-ヶ々 　]{2,10})'

    # 金額・通貨（例: 1,000,000円、50万円、10,000ドル）
    if mask_options.get("MONEY", True):
        patterns["MONEY"] = r'\d{1,3}(?:,\d{3})*\s*(?:円|ドル|元|万円|億円)'

    # 日付（例: 2026年7月3日、2026/07/03）
    if mask_options.get("DATE", True):
        patterns["DATE"] = r'(?:\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日|\d{4}[-/]\d{1,2}[-/]\d{1,2})'

    # 各カテゴリごとにマッチする文字列を抽出
    for category, pattern in patterns.items():
        matches = []
        # PERSONパターンのようにグループ(1)がある場合はそれを抽出し、そうでない場合は全体を抽出
        for m in re.finditer(pattern, masked_text):
            if category == "PERSON" and m.lastindex is not None and m.lastindex >= 1:
                # プレースホルダーに置換するのは名前の部分だけにする
                name = m.group(1).strip()
                # 役職名（代表取締役など）や記号自体は残し、名前のみをダミー化するための準備
                if len(name) >= 2: # 最低2文字以上の名前を対象にする
                    matches.append((name, category))
            else:
                matches.append((m.group(0).strip(), category))
        
        # 重複を排除し、文字列の長さが長い順にソート（部分一致での誤置換を防ぐため）
        unique_matches = list(set([m[0] for m in matches]))
        unique_matches.sort(key=len, reverse=True)
        
        # プレースホルダーの生成と置換
        for idx, original_str in enumerate(unique_matches, 1):
            placeholder = f"[{category}_{idx}]"
            mapping_dict[placeholder] = original_str
            
            # テキスト内の該当箇所をプレースホルダーに置換
            # re.escapeを使用して特殊文字のエスケープを行う
            masked_text = re.sub(re.escape(original_str), placeholder, masked_text)

    return masked_text, mapping_dict

def unmask_text(text: str, mapping_dict: Dict[str, str]) -> str:
    """
    LLMから返ってきたテキスト内のダミー文字列を、対応表に基づいて元の実データに復元（アンマスキング）します。
    
    Args:
        text (str): 復元対象のテキスト（プレースホルダーを含む）
        mapping_dict (dict): ダミー文字列から元の文字列へのマッピング辞書
        
    Returns:
        str: 復元されたテキスト
    """
    if not mapping_dict:
        return text
        
    unmasked_text = text
    # 置換キーの長さが長い順にソートして置換（誤置換防止。例: [PERSON_10] が [PERSON_1] に部分マッチするのを防ぐ）
    sorted_placeholders = sorted(mapping_dict.keys(), key=len, reverse=True)
    
    for placeholder in sorted_placeholders:
        original_value = mapping_dict[placeholder]
        unmasked_text = unmasked_text.replace(placeholder, original_value)
        
    return unmasked_text
