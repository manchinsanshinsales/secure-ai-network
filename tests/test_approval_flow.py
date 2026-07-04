import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# アプリケーションのパスを追加してインポート可能にする
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from approval_flow import run_command, check_for_approval, send_approval_request

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
