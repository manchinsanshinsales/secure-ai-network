import sys
from masking import mask_text, unmask_text
from llm_client import MockLLMClient

# テスト用契約書テキスト
TEST_CONTRACT = """
業務委託契約書
委託者：株式会社マコト商事（以下「甲」）
受託者：山田 太郎（以下「乙」）
代表者：戸塚 誠

第1条 本契約の金額は 1,000,000円 とする。
第2条 契約日は 2026年7月3日 とし、履行期限は 2026年8月31日 とする。
"""

def run_test():
    print("--- 1. マスキングテストの実行 ---")
    mask_options = {"ORG": True, "PER": True, "MONEY": True, "DATE": True}
    
    masked_text, mapping_dict = mask_text(TEST_CONTRACT, mask_options)
    
    print("\n[元のテキスト]")
    print(TEST_CONTRACT.strip())
    print("\n[マスキング後のテキスト]")
    print(masked_text.strip())
    print("\n[マッピングテーブル]")
    print(mapping_dict)
    
    # 検証：元のテキストの機密情報がマスクされているか
    assert "株式会社マコト商事" not in masked_text, "会社名がマスキングされていません"
    assert "山田 太郎" not in masked_text, "人名(乙)がマスキングされていません"
    assert "戸塚 誠" not in masked_text, "代表者名がマスキングされていません"
    assert "1,000,000円" not in masked_text, "金額がマスキングされていません"
    assert "2026年7月3日" not in masked_text, "契約日がマスキングされていません"
    assert "2026年8月31日" not in masked_text, "履行期限がマスキングされていません"
    
    print("\n✅ マスキング処理の検証OK")
    
    print("\n--- 2. MockLLM連携と復元（アンマスキング）テストの実行 ---")
    client = MockLLMClient()
    prompt = f"契約書をレビューして:\n{masked_text}"
    
    # 匿名化された状態でLLM（Mock）にリクエスト送信
    raw_response = client.generate_response(prompt)
    print("\n[LLM（Mock）からの生応答]")
    print(raw_response.strip())
    
    # 復元処理
    final_response = unmask_text(raw_response, mapping_dict)
    print("\n[復元後の最終応答]")
    print(final_response.strip())
    
    # 検証：復元されたテキストに実データが戻っているか
    assert "株式会社マコト商事" in final_response, "会社名が復元されていません"
    assert "1,000,000円" in final_response, "金額が復元されていません"
    
    print("\n✅ アンマスキング（復元）処理の検証OK")
    print("\n🎉 すべてのテストに成功しました！")

if __name__ == "__main__":
    run_test()
