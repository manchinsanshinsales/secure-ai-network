import sys
import os
import pytest

# アプリケーションのパスを追加してインポート可能にする
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from dlp import SecureDlpManager

@pytest.fixture
def dlp_manager():
    return SecureDlpManager()

def test_no_sensitive_data(dlp_manager):
    text = "こんにちは、今日の天気は晴れです。よろしくお願いいたします。"
    masked, details = dlp_manager.process(text)
    assert masked == text
    assert len(details) == 0

def test_email_masking(dlp_manager):
    text = "私の連絡先は test.user@example.com です。"
    masked, details = dlp_manager.process(text)
    assert "[EMAIL_ADDRESS]" in masked
    assert "test.user@example.com" not in masked
    assert len(details) >= 1
    assert any(d["entity_type"] == "EMAIL_ADDRESS" for d in details)

def test_jp_phone_masking(dlp_manager):
    # 携帯電話
    text1 = "電話番号は090-1234-5678です。"
    masked1, details1 = dlp_manager.process(text1)
    assert "[PHONE_NUMBER]" in masked1
    assert "090-1234-5678" not in masked1
    
    # 固定電話
    text2 = "固定電話は03-5555-4444。"
    masked2, details2 = dlp_manager.process(text2)
    assert "[PHONE_NUMBER]" in masked2
    assert "03-5555-4444" not in masked2

def test_jp_mynumber_masking(dlp_manager):
    text = "マイナンバーは123456789012です。"
    masked, details = dlp_manager.process(text)
    assert "[JP_MYNUMBER]" in masked
    assert "123456789012" not in masked
    assert len(details) >= 1
    assert any(d["entity_type"] == "JP_MYNUMBER" for d in details)

def test_jp_zip_masking(dlp_manager):
    text = "郵便番号は123-4567です。"
    masked, details = dlp_manager.process(text)
    assert "[JP_ZIP]" in masked
    assert "123-4567" not in masked

def test_credit_card_masking(dlp_manager):
    text = "カード番号 4111-1111-1111-1111 を使用します。"
    masked, details = dlp_manager.process(text)
    assert "[CREDIT_CARD]" in masked
    assert "4111-1111-1111-1111" not in masked

def test_api_key_and_secrets(dlp_manager):
    # AWSアクセスキー
    text1 = "AWSアクセスキーはAKIAIOSFODNN7EXAMPLEです。"
    masked1, details1 = dlp_manager.process(text1)
    assert "[API_KEY_SECRET]" in masked1
    assert "AKIAIOSFODNN7EXAMPLE" not in masked1
    assert any(d["entity_type"] == "API_KEY_SECRET" for d in details1)

    # シークレット表記
    text2 = "秘密情報は password=\"supersecret123\" です。"
    masked2, details2 = dlp_manager.process(text2)
    assert "[API_KEY_SECRET]" in masked2
    assert "supersecret123" not in masked2
    assert any(d["entity_type"] == "API_KEY_SECRET" for d in details2)
