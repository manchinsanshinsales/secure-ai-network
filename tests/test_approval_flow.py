import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# アプリケーションのパスを追加してインポート可能にする
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from approval_flow import run_command, check_for_approval, send_approval_request, extract_reply_content

def test_run_command_success():
    """正常終了するコマンドの実行テスト"""
    result = run_command("echo 'test run'")
    assert result is True

def test_run_command_fail():
    """異常終了するコマンドの実行テスト"""
    # 存在しないコマンドや exit 1 を返すコマンド
    result = run_command("false")
    assert result is False

@patch("smtplib.SMTP")
def test_send_approval_request(mock_smtp):
    """SMTPメール送信のモックテスト"""
    # モックの設定
    instance = mock_smtp.return_value
    
    # テスト対象関数の呼び出し
    result = send_approval_request(
        task_name="Test Task",
        task_id="test1234",
        approver="test@example.com",
        sender_email="bot@example.com",
        sender_password="password",
        smtp_server="smtp.example.com",
        smtp_port=587
    )
    
    # アサーション
    assert result is True
    mock_smtp.assert_called_with("smtp.example.com", 587)
    instance.starttls.assert_called_once()
    instance.login.assert_called_with("bot@example.com", "password")
    instance.sendmail.assert_called_once()
    instance.quit.assert_called_once()

@patch("imaplib.IMAP4_SSL")
def test_check_for_approval_approve(mock_imap):
    """IMAPでの『承認』返信検知テスト"""
    # モックのセットアップ
    instance = mock_imap.return_value
    instance.select.return_value = ("OK", [b"1"])
    instance.search.return_value = ("OK", [b"101"])
    
    # ダミーのRFC822メールデータを作成 (承認者からの返信メール)
    # 本文に APPROVE と Task ID 'test1234' が含まれるように設定
    raw_email_data = b"""From: makoto.insidesales@gmail.com
Subject: Re: [APPROVAL REQUIRED] Task: Test Task (ID: test1234)

APPROVE. This looks good to deploy.
"""
    instance.fetch.return_value = ("OK", [(b"101 (RFC822 {150}", raw_email_data), b")"])
    
    status, comment = check_for_approval(
        task_id="test1234",
        approver="makoto.insidesales@gmail.com",
        sender_email="bot@example.com",
        sender_password="password",
        imap_server="imap.example.com",
        imap_port=993
    )
    
    assert status == "APPROVE"
    assert "APPROVE" in comment
    instance.login.assert_called_with("bot@example.com", "password")
    instance.store.assert_called_with(b"101", "+FLAGS", "\\Seen")

@patch("imaplib.IMAP4_SSL")
def test_check_for_approval_reject(mock_imap):
    """IMAPでの『却下』返信検知テスト"""
    instance = mock_imap.return_value
    instance.select.return_value = ("OK", [b"1"])
    instance.search.return_value = ("OK", [b"101"])
    
    raw_email_data = b"""From: makoto.insidesales@gmail.com
Subject: Re: [APPROVAL REQUIRED] Task: Test Task (ID: test1234)

REJECT. Do not run this yet.
"""
    instance.fetch.return_value = ("OK", [(b"101 (RFC822 {150}", raw_email_data), b")"])
    
    status, comment = check_for_approval(
        task_id="test1234",
        approver="makoto.insidesales@gmail.com",
        sender_email="bot@example.com",
        sender_password="password",
        imap_server="imap.example.com",
        imap_port=993
    )
    
    assert status == "REJECT"
    assert "REJECT" in comment
    instance.store.assert_called_with(b"101", "+FLAGS", "\\Seen")

def test_extract_reply_content():
    """メール本文から引用部を除いた返信コンテンツ抽出テスト"""
    # 1. 正常な返信メール（引用あり）
    body_with_quote = """Yes, let's approve.
On 2026-07-04 12:00, bot@example.com wrote:
> This is a request. Please reply APPROVE.
"""
    assert extract_reply_content(body_with_quote) == "Yes, let's approve."

    # 2. 引用行のみのメール（実質的な返信なし）
    body_only_quote = """> This is a request. Please reply APPROVE."""
    assert extract_reply_content(body_only_quote) == ""

    # 3. 複数のヘッダー形式がある場合
    body_with_original = """Please proceed.
-----Original Message-----
From: bot@example.com
Subject: Task Approval
"""
    assert extract_reply_content(body_with_original) == "Please proceed."

@patch("imaplib.IMAP4_SSL")
def test_check_for_approval_with_quoted_key(mock_imap):
    """引用部分に『APPROVE』が含まれているが、返信自体は承認でない場合の検知テスト"""
    instance = mock_imap.return_value
    instance.select.return_value = ("OK", [b"1"])
    instance.search.return_value = ("OK", [b"101"])
    
    # 承認者は「まだ確認中」と返信したが、引用部に「APPROVE」が入っているケース
    raw_email_data = b"""From: makoto.insidesales@gmail.com
Subject: Re: [APPROVAL REQUIRED] Task: Test Task (ID: test1234)

I am still reviewing. Please wait.
On 2026-07-04 12:00, bot wrote:
> Reply with APPROVE to run the command.
"""
    instance.fetch.return_value = ("OK", [(b"101 (RFC822 {250}", raw_email_data), b")"])
    
    status, comment = check_for_approval(
        task_id="test1234",
        approver="makoto.insidesales@gmail.com",
        sender_email="bot@example.com",
        sender_password="password",
        imap_server="imap.example.com",
        imap_port=993
    )
    
    # 引用文の中の「APPROVE」には反応せず、返信（I am still reviewing）を見て None になるべき
    assert status is None
    assert comment is None

@patch("smtplib.SMTP")
@patch("imaplib.IMAP4_SSL")
def test_test_connection_success(mock_imap, mock_smtp):
    """SMTP & IMAPの接続テスト成功のモックテスト"""
    # approval_flowのtest_connectionをインポート
    from approval_flow import test_connection
    
    # モックのセットアップ
    smtp_instance = mock_smtp.return_value
    imap_instance = mock_imap.return_value
    
    result = test_connection(
        sender_email="bot@example.com",
        sender_password="password",
        smtp_server="smtp.example.com",
        smtp_port=587,
        imap_server="imap.example.com",
        imap_port=993
    )
    
    assert result is True
    mock_smtp.assert_called_once_with("smtp.example.com", 587)
    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with("bot@example.com", "password")
    
    mock_imap.assert_called_once_with("imap.example.com", 993)
    imap_instance.login.assert_called_once_with("bot@example.com", "password")

@patch("smtplib.SMTP")
@patch("imaplib.IMAP4_SSL")
def test_test_connection_fail(mock_imap, mock_smtp):
    """SMTP or IMAPの接続テスト失敗のモックテスト"""
    from approval_flow import test_connection
    
    # SMTPログイン失敗をシミュレート
    smtp_instance = mock_smtp.return_value
    smtp_instance.login.side_effect = Exception("SMTP login failed")
    
    result = test_connection(
        sender_email="bot@example.com",
        sender_password="password",
        smtp_server="smtp.example.com",
        smtp_port=587,
        imap_server="imap.example.com",
        imap_port=993
    )
    
    assert result is False


